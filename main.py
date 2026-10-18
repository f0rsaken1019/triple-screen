#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import _conf
import concurrent.futures
import lib_indicators
import lib_plottings
import lib_strategies
import lib_universe_builders
import lib_utils
import multiprocessing
import os
import re
import shutil
import sys
import tomllib

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

GLOBAL_PRECISION = _conf.PRECISION

try:
    GLOBAL_PRECISION = int(GLOBAL_PRECISION)
except (TypeError, ValueError) as e:
    GLOBAL_PRECISION = 2
else:
    if GLOBAL_PRECISION <= 1:
        GLOBAL_PRECISION = 2

MAX_WORKERS = min(max((cpu_count if (cpu_count := os.cpu_count()) is not None else 1) - 1, 1), 61)

def main() -> None:
    # 获取自选列表成分股
    if len(sys.argv) == 1:
        try:
            with open(BASE_DIR.joinpath('_watchlist.toml'), 'rb') as f:
                data = tomllib.load(f)
        except OSError as e:
            print("[-] Cannot open the '_watchlist.toml' file!")
            return None
        except tomllib.TOMLDecodeError as e:
            print("[-] The '_watchlist.toml' is an invalid TOML document!")
            return None
        else:
            watchlist = data['watchlist']

        sub_dir = 'watchlist'.capitalize()

        stocks = lib_universe_builders.get_watchlist_members(watchlist)

    elif len(sys.argv) == 2:
        toml_doc_name = sys.argv[1].strip()

        if not re.fullmatch(r'[\w.-]+', toml_doc_name, flags=re.ASCII):
            print('[-] The value of argument <toml_doc_name> only supports the following characters: [a-zA-Z0-9_.-]')
            return None

        try:
            with open(BASE_DIR.joinpath(toml_doc_name), 'rb') as f:
                data = tomllib.load(f)
        except OSError as e:
            print(f"[-] Cannot open the '{toml_doc_name}' file!")
            return None
        except tomllib.TOMLDecodeError as e:
            print(f"[-] The '{toml_doc_name}' is an invalid TOML document!")
            return None
        else:
            watchlist = data['watchlist']

        sub_dir = toml_doc_name.split('.')[0].replace('-', '_').upper()

        stocks = lib_universe_builders.get_watchlist_members(watchlist)

    elif len(sys.argv) == 4:
        (function, params) = (sys.argv[1].strip().capitalize(), (sys.argv[2].strip().upper(), sys.argv[3].strip().upper()))

        # 获取指数成分股
        if function == 'index'.capitalize():
            (market, index) = (params[0], params[1])
            sub_dir = f'{market}_{index}'
            stocks = lib_universe_builders.get_index_members(market, index)

        # 占位符
        elif function == '_':
            return None

        else:
            print(f"[-] The <function> '{function}' is not supported!")
            return None

    else:
        print('[-] The parameters are incorrect!')
        return None

    if stocks is None:
        print('[-] Failed to get stock list!')
        return None

    # 获取周频 OHLCV 数据
    weekly_ohlcv_data = lib_utils.get_ohlcv_data(stocks, timeframe='W')
    if weekly_ohlcv_data is None:
        print('[-] Failed to get weekly OHLCV data!')
        return None

    # 获取日频 OHLCV 数据
    daily_ohlcv_data = lib_utils.get_ohlcv_data(stocks, timeframe='D')
    if daily_ohlcv_data is None:
        print('[-] Failed to get daily OHLCV data!')
        return None

    # 存储周频和日频 OHLCV 数据
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        stock['weekly_ohlcv'] = weekly_ohlcv_data[stock_identifier]
        stock['daily_ohlcv'] = daily_ohlcv_data[stock_identifier]

        # 将中国 A 股市场证券的 '成交量' 数据单位由 '手' 转换为 '股' 以与港股市场和美股市场对齐。
        if stock['market'] in ('A', 'AF'):
            stock['weekly_ohlcv']['volume'] = stock['weekly_ohlcv']['volume'].mul(100)
            stock['daily_ohlcv']['volume'] = stock['daily_ohlcv']['volume'].mul(100)

    # 排除新股
    if _conf.EXCLUDE_NEWLY_LISTED_STOCKS:
        min_daily_kline_num = _conf.STOCK_MIN_DAILY_KLINE_NUM

        try:
            min_daily_kline_num = int(min_daily_kline_num)
        except (TypeError, ValueError) as e:
            min_daily_kline_num = 252
        else:
            if min_daily_kline_num < 252:
                min_daily_kline_num = 252

        stocks = [stock for stock in stocks if len(stock['daily_ohlcv']) >= min_daily_kline_num]

    # 计算 Triple Screen 系统所需指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        weekly_triple_screen_indicators = lib_indicators.get_triple_screen_indicators(stock['weekly_ohlcv'], timeframe='W')

        if weekly_triple_screen_indicators is None:
            print(f'[-] Failed to get stock <{stock_identifier}> weekly <Triple Screen> indicators data!')
            return None

        for (indicator_name, indicator_df) in weekly_triple_screen_indicators.items():
            if indicator_name == 'MACD':
                indicator_df = indicator_df.add_prefix(f'{indicator_name}_')
            stock['weekly_ohlcv'] = stock['weekly_ohlcv'].join(indicator_df)

        daily_triple_screen_indicators = lib_indicators.get_triple_screen_indicators(stock['daily_ohlcv'], timeframe='D')

        if daily_triple_screen_indicators is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <Triple Screen> indicators data!')
            return None

        for (indicator_name, indicator_df) in daily_triple_screen_indicators.items():
            if indicator_name == 'MACD':
                indicator_df = indicator_df.add_prefix(f'{indicator_name}_')
            stock['daily_ohlcv'] = stock['daily_ohlcv'].join(indicator_df)

    # 计算周内 OHLCV 和指标数据
    intraweek_weekly_list = list()
    intraweek_daily_list = list()

    for stock in stocks:
        weekly_df = stock['weekly_ohlcv'][['open', 'high', 'low', 'close', 'volume', f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}", 'MACD_histogram', 'elder_impulse']].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}": 'fast_ema',
                'MACD_histogram': 'macd_histogram',
            },
            errors='raise'
        )

        daily_df = stock['daily_ohlcv'][['open', 'high', 'low', 'close', 'volume', f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}", 'MACD_histogram', 'elder_impulse']].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}": 'fast_ema',
                'MACD_histogram': 'macd_histogram',
            },
            errors='raise'
        )

        intraweek_weekly_list.append(weekly_df)
        intraweek_daily_list.append(daily_df)

    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS, mp_context=multiprocessing.get_context(method='spawn')) as executor:
        intraweek_results_list = list(executor.map(lib_utils.get_intraweek_ohlcv_and_indicators, intraweek_weekly_list, intraweek_daily_list))

    for (index, intraweek_ohlcv_and_indicators) in enumerate(intraweek_results_list):
        stock_identifier = stocks[index]['name'] if stocks[index]['match_name'] else stocks[index]['symbol']

        if intraweek_ohlcv_and_indicators is None:
            print(f'[-] Failed to get stock <{stock_identifier}> intraweek OHLCV and indicators data!')
            return None

        stocks[index]['intraweek_ohlcv_and_indicators'] = intraweek_ohlcv_and_indicators

    # 计算 Elder Impulse Release 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Elder Impulse Release'

        intraweek_df = stock['intraweek_ohlcv_and_indicators'][['elder_impulse']]

        daily_df = stock['daily_ohlcv'][['elder_impulse']]

        elder_impulse_release_df = lib_indicators.get_elder_impulse_release(intraweek_df, daily_df)

        if elder_impulse_release_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(elder_impulse_release_df)

    # 删除周内 OHLCV 和指标数据
    for stock in stocks:
        del stock['intraweek_ohlcv_and_indicators']

    # 计算 Volume SMA 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        volume_sma_indicators = lib_indicators.get_volume_sma_indicators(stock['daily_ohlcv'])

        if volume_sma_indicators is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <Volume SMA> indicators data!')
            return None

        for (indicator_name, indicator_df) in volume_sma_indicators.items():
            stock['daily_ohlcv'] = stock['daily_ohlcv'].join(indicator_df)

    # 计算 ATR 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'ATR'

        daily_ohlcv = stock['daily_ohlcv'][['open', 'high', 'low', 'close', 'volume']]

        atr_df = lib_indicators.get_atr(daily_ohlcv)

        if atr_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(atr_df)

    # 构建 Keltner 通道
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Keltner'

        daily_df = stock['daily_ohlcv'][[f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}", f'atr_{lib_indicators.ATR_PERIODS}']].rename(
            columns={
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}": 'slow_ema',
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        keltner_df = lib_indicators.get_keltner(daily_df)

        if keltner_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        keltner_df = keltner_df.add_prefix(f'{indicator_name.lower()}_')
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(keltner_df)

    # 计算 Pullback Entry 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Pullback Entry'

        daily_df = stock['daily_ohlcv'][['high', 'low', 'close', f'atr_{lib_indicators.ATR_PERIODS}']].rename(
            columns={
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        pullback_entry_df = lib_indicators.get_pullback_entry(daily_df)

        if pullback_entry_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        pullback_entry_df = pullback_entry_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(pullback_entry_df)

    # 计算 ATR Initial Stop 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'ATR Initial Stop'

        daily_df = stock['daily_ohlcv'][['high', 'low', f'atr_{lib_indicators.ATR_PERIODS}']].rename(
            columns={
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        atr_initial_stop_df = lib_indicators.get_atr_initial_stop(daily_df)

        if atr_initial_stop_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        atr_initial_stop_df = atr_initial_stop_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(atr_initial_stop_df)

    # 计算 ATR Trailing Stop 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'ATR Trailing Stop'

        daily_df = stock['daily_ohlcv'][['high', 'low', f'atr_{lib_indicators.ATR_PERIODS}']].rename(
            columns={
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        atr_trailing_stop_df = lib_indicators.get_atr_trailing_stop(daily_df)

        if atr_trailing_stop_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        atr_trailing_stop_df = atr_trailing_stop_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(atr_trailing_stop_df)

    # 计算 Keltner Target 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Keltner Target'

        daily_df = stock['daily_ohlcv'][[f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}", f'atr_{lib_indicators.ATR_PERIODS}']].rename(
            columns={
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}": 'slow_ema',
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        keltner_target_df = lib_indicators.get_keltner_target(daily_df)

        if keltner_target_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        keltner_target_df = keltner_target_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(keltner_target_df)

    # 计算 Breakeven 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Breakeven'

        daily_df = stock['daily_ohlcv'][['pullback_entry_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'keltner_target_seller']]

        tick = 0.001 if stock['market'] == 'AF' else 0.01

        breakeven_df = lib_indicators.get_breakeven(daily_df, tick=tick)

        if breakeven_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        breakeven_df = breakeven_df.add_prefix(f'{indicator_name.lower()}_')
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(breakeven_df)

    # 计算 Protect Profit 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Protect Profit'

        daily_df = stock['daily_ohlcv'][['pullback_entry_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'keltner_target_seller']]

        tick = 0.001 if stock['market'] == 'AF' else 0.01

        protect_profit_df = lib_indicators.get_protect_profit(daily_df, tick=tick)

        if protect_profit_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        protect_profit_df = protect_profit_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(protect_profit_df)

    # 计算 Reward Risk Ratio 指标
    for stock in stocks:
        stock_identifier = stock['name'] if stock['match_name'] else stock['symbol']

        indicator_name = 'Reward Risk Ratio'

        daily_df = stock['daily_ohlcv'][['pullback_entry_buyer', 'atr_initial_stop_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'atr_initial_stop_seller', 'keltner_target_seller']]

        reward_risk_ratio_df = lib_indicators.get_reward_risk_ratio(daily_df)

        if reward_risk_ratio_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        reward_risk_ratio_df = reward_risk_ratio_df.add_prefix(f"{indicator_name.lower().replace(' ', '_')}_")
        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(reward_risk_ratio_df)

    # 绘制分析图表
    for stock in stocks:
        (symbol, name, market, match_name) = (stock['symbol'], stock['name'], stock['market'], stock['match_name'])

        weekly_df = stock['weekly_ohlcv'].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}": 'fast_ema',
                f"slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}": 'slow_ema',
                f'rsi_{lib_indicators.RSI_PERIODS_W}': 'rsi',
                f'efi_{lib_indicators.EFI_PERIODS_W}': 'efi',
                f'quarter_volume_sma_{lib_indicators.QUARTER_VOLUME_SMA_PERIODS_W}': 'quarter_volume_sma',
            },
            errors='raise'
        )

        daily_df = stock['daily_ohlcv'].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}": 'fast_ema',
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}": 'slow_ema',
                f'rsi_{lib_indicators.RSI_PERIODS_D}': 'rsi',
                f'efi_{lib_indicators.EFI_PERIODS_D}': 'efi',
                f'quarter_volume_sma_{lib_indicators.QUARTER_VOLUME_SMA_PERIODS_D}': 'quarter_volume_sma',
                f"slow_volume_sma_{lib_indicators.VOLUME_SMA_PERIODS_DAILY['slow']}": 'slow_volume_sma',
                f"fast_volume_sma_{lib_indicators.VOLUME_SMA_PERIODS_DAILY['fast']}": 'fast_volume_sma',
                f"week_volume_sma_{lib_indicators.VOLUME_SMA_PERIODS_DAILY['week']}": 'week_volume_sma',
                f'atr_{lib_indicators.ATR_PERIODS}': 'atr',
            },
            errors='raise'
        )

        stock_identifier = name if match_name else symbol

        # 绘制周频分析图表
        weekly_analysis_figure = lib_plottings.get_weekly_analysis_figure(weekly_df, symbol, name, market)

        if weekly_analysis_figure is None:
            print(f'[-] Failed to get stock <{stock_identifier}> weekly analysis figure!')
            return None

        stock['weekly_analysis_figure'] = weekly_analysis_figure

        # 绘制日频分析图表
        daily_analysis_figure = lib_plottings.get_daily_analysis_figure(daily_df, symbol, name, market)

        if daily_analysis_figure is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily analysis figure!')
            return None

        stock['daily_analysis_figure'] = daily_analysis_figure

    # 计算 Triple Screen 系统交易信号
    signals = {
        'buy': list(),
        'wait_or_raise_stop': list(),
        'sell': list(),
        'wait_or_lower_stop': list(),
        'stand_aside': list(),
        'trades_prohibited': list(),
    }

    for stock in stocks:
        (symbol, name, market, match_name) = (stock['symbol'], stock['name'], stock['market'], stock['match_name'])

        daily_df = stock['daily_ohlcv'][['elder_impulse_release', 'elder_impulse', 'close', f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}", f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}", 'keltner_upper_band_p1_atr', 'keltner_lower_band_n1_atr', f'rsi_{lib_indicators.RSI_PERIODS_D}', f'efi_{lib_indicators.EFI_PERIODS_D}']].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}": 'fast_ema',
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}": 'slow_ema',
                'keltner_upper_band_p1_atr': 'keltner_upper_band',
                'keltner_lower_band_n1_atr': 'keltner_lower_band',
                f'rsi_{lib_indicators.RSI_PERIODS_D}': 'rsi',
                f'efi_{lib_indicators.EFI_PERIODS_D}': 'efi',
            },
            errors='raise'
        )

        weekly_df = stock['weekly_ohlcv'][['elder_impulse', 'close', f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}", f"slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}", f'rsi_{lib_indicators.RSI_PERIODS_W}', f'efi_{lib_indicators.EFI_PERIODS_W}']].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}": 'fast_ema',
                f"slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}": 'slow_ema',
                f'rsi_{lib_indicators.RSI_PERIODS_W}': 'rsi',
                f'efi_{lib_indicators.EFI_PERIODS_W}': 'efi',
            },
            errors='raise'
        )

        stock_identifier = name if match_name else symbol

        signal = lib_strategies.get_triple_screen_signals(daily_df[['elder_impulse_release', 'elder_impulse', 'close', 'slow_ema', 'keltner_upper_band', 'keltner_lower_band', 'rsi', 'efi']], weekly_df[['elder_impulse', 'slow_ema', 'rsi', 'efi']])

        if signal is None:
            print(f'[-] Failed to get stock <{stock_identifier}> <Triple Screen Signals> signal info!')
            return None

        stock['signal'] = signal

        precision = GLOBAL_PRECISION
        if (market == 'AF') and (precision < 3):
            precision = 3

        score = 0

        if signal == 'buy':
            if weekly_df['fast_ema'].iloc[-1] > weekly_df['slow_ema'].iloc[-1]:
                score += 2
            elif weekly_df['fast_ema'].iloc[-1] == weekly_df['slow_ema'].iloc[-1]:
                score += 1
            elif weekly_df['fast_ema'].iloc[-1] < weekly_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if daily_df['fast_ema'].iloc[-1] > daily_df['slow_ema'].iloc[-1]:
                score += 2
            elif daily_df['fast_ema'].iloc[-1] == daily_df['slow_ema'].iloc[-1]:
                score += 1
            elif daily_df['fast_ema'].iloc[-1] < daily_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if weekly_df['close'].iloc[-1] > weekly_df['slow_ema'].iloc[-1]:
                score += 2
            elif weekly_df['close'].iloc[-1] == weekly_df['slow_ema'].iloc[-1]:
                score += 1
            elif weekly_df['close'].iloc[-1] < weekly_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if daily_df['close'].iloc[-1] > daily_df['slow_ema'].iloc[-1]:
                score += 2
            elif daily_df['close'].iloc[-1] == daily_df['slow_ema'].iloc[-1]:
                score += 1
            elif daily_df['close'].iloc[-1] < daily_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            reward_risk_ratio = stock['daily_ohlcv']['reward_risk_ratio_buyer'].iloc[-1]
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['pullback_entry_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_initial_stop_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['breakeven_price_buyer'].iloc[-1]:.{precision}f} &vert; {stock['daily_ohlcv']['breakeven_stop_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['protect_profit_price_buyer'].iloc[-1]:.{precision}f} &vert; {stock['daily_ohlcv']['protect_profit_stop_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['keltner_target_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['reward_risk_ratio_buyer'].iloc[-1]:.2f}|{score}|"
            signals[signal].append({'market': market, 'score': score, 'reward_risk_ratio': reward_risk_ratio, 'symbol': symbol, 'content': content})

        elif signal == 'wait_or_raise_stop':
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_buyer'].iloc[-1]:.{precision}f}|"
            signals[signal].append({'market': market, 'symbol': symbol, 'content': content})

        elif signal == 'sell':
            if weekly_df['fast_ema'].iloc[-1] < weekly_df['slow_ema'].iloc[-1]:
                score += 2
            elif weekly_df['fast_ema'].iloc[-1] == weekly_df['slow_ema'].iloc[-1]:
                score += 1
            elif weekly_df['fast_ema'].iloc[-1] > weekly_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if daily_df['fast_ema'].iloc[-1] < daily_df['slow_ema'].iloc[-1]:
                score += 2
            elif daily_df['fast_ema'].iloc[-1] == daily_df['slow_ema'].iloc[-1]:
                score += 1
            elif daily_df['fast_ema'].iloc[-1] > daily_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if weekly_df['close'].iloc[-1] < weekly_df['slow_ema'].iloc[-1]:
                score += 2
            elif weekly_df['close'].iloc[-1] == weekly_df['slow_ema'].iloc[-1]:
                score += 1
            elif weekly_df['close'].iloc[-1] > weekly_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            if daily_df['close'].iloc[-1] < daily_df['slow_ema'].iloc[-1]:
                score += 2
            elif daily_df['close'].iloc[-1] == daily_df['slow_ema'].iloc[-1]:
                score += 1
            elif daily_df['close'].iloc[-1] > daily_df['slow_ema'].iloc[-1]:
                score += 0
            else:
                pass

            reward_risk_ratio = stock['daily_ohlcv']['reward_risk_ratio_seller'].iloc[-1]
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['pullback_entry_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_initial_stop_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['breakeven_price_seller'].iloc[-1]:.{precision}f} &vert; {stock['daily_ohlcv']['breakeven_stop_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['protect_profit_price_seller'].iloc[-1]:.{precision}f} &vert; {stock['daily_ohlcv']['protect_profit_stop_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['keltner_target_seller'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['reward_risk_ratio_seller'].iloc[-1]:.2f}|{score}|"
            signals[signal].append({'market': market, 'score': score, 'reward_risk_ratio': reward_risk_ratio, 'symbol': symbol, 'content': content})

        elif signal == 'wait_or_lower_stop':
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_seller'].iloc[-1]:.{precision}f}|"
            signals[signal].append({'market': market, 'symbol': symbol, 'content': content})

        elif signal == 'stand_aside':
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_buyer'].iloc[-1]:.{precision}f}|{stock['daily_ohlcv']['atr_trailing_stop_seller'].iloc[-1]:.{precision}f}|"
            signals[signal].append({'market': market, 'symbol': symbol, 'content': content})

        elif signal == 'trades_prohibited':
            content = f"|{market}|{symbol}|{name}|{stock['daily_ohlcv']['close'].iloc[-1]:.{precision}f}|"
            signals[signal].append({'market': market, 'symbol': symbol, 'content': content})

        else:
            pass

    # 对于交易信号进行排序
    for (signal, item) in signals.items():
        if signal in ('buy', 'sell'):
            item.sort(key=lambda x: (x['market'], -x['score'], -x['reward_risk_ratio'], x['symbol']))
        else:
            item.sort(key=lambda x: (x['market'], x['symbol']))
        signals[signal] = [sub_item['content'] for sub_item in item]

    # 初始化数据目录
    data_dir = BASE_DIR.joinpath('data').joinpath(sub_dir)

    try:
        if data_dir.is_file() or data_dir.is_symlink():
            data_dir.unlink()
        if data_dir.is_dir():
            shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True)
    except PermissionError as e:
        print('[-] Failed to initialize the data directory!')
        return None

    # 导出 OHLCV 和指标数据至 CSV 文件
    for stock in stocks:
        (signal, symbol, name, market) = (stock['signal'], stock['symbol'], stock['name'], stock['market'])
        (weekly_ohlcv, daily_ohlcv) = (stock['weekly_ohlcv'], stock['daily_ohlcv'])

        stock_data_dir = data_dir.joinpath(signal.title().replace('Or', 'or'))
        stock_data_dir.mkdir(exist_ok=True)

        # 导出周频 OHLCV 和指标数据
        weekly_csv_path = stock_data_dir.joinpath(f'{market}_{symbol}_{name}_Weekly' + '.csv')
        weekly_ohlcv.to_csv(weekly_csv_path)

        # 导出日频 OHLCV 和指标数据
        daily_csv_path = stock_data_dir.joinpath(f'{market}_{symbol}_{name}_Daily' + '.csv')
        daily_ohlcv.to_csv(daily_csv_path)

    # 初始化图表目录
    charts_dir = BASE_DIR.joinpath('charts').joinpath(sub_dir)

    try:
        if charts_dir.is_file() or charts_dir.is_symlink():
            charts_dir.unlink()
        if charts_dir.is_dir():
            shutil.rmtree(charts_dir)
        charts_dir.mkdir(parents=True)
    except PermissionError as e:
        print('[-] Failed to initialize the charts directory!')
        return None

    # 导出分析图表至 HTML 文件
    layout_percentage = _conf.FIGURE_LAYOUT_PERCENTAGE

    try:
        layout_percentage = int(layout_percentage)
    except (TypeError, ValueError) as e:
        layout_percentage = 100
    else:
        if layout_percentage < 100:
            layout_percentage = 100

    for stock in stocks:
        (signal, symbol, name, market) = (stock['signal'], stock['symbol'], stock['name'], stock['market'])
        (weekly_analysis_figure, daily_analysis_figure) = (stock['weekly_analysis_figure'], stock['daily_analysis_figure'])

        stock_charts_dir = charts_dir.joinpath(signal.title().replace('Or', 'or'))
        stock_charts_dir.mkdir(exist_ok=True)

        # 导出周频分析图表
        weekly_html_path = stock_charts_dir.joinpath(f'{market}_{symbol}_{name}_Weekly' + '.html')
        weekly_analysis_figure.write_html(weekly_html_path, default_width=f'{layout_percentage}%', default_height=f'{layout_percentage}%')

        # 导出日频分析图表
        daily_html_path = stock_charts_dir.joinpath(f'{market}_{symbol}_{name}_Daily' + '.html')
        daily_analysis_figure.write_html(daily_html_path, default_width=f'{layout_percentage}%', default_height=f'{layout_percentage}%')

    # 初始化交易信号目录
    signals_dir = BASE_DIR.joinpath('signals').joinpath(sub_dir)

    try:
        if signals_dir.is_file() or signals_dir.is_symlink():
            signals_dir.unlink()
        if signals_dir.is_dir():
            shutil.rmtree(signals_dir)
        signals_dir.mkdir(parents=True)
    except PermissionError as e:
        print('[-] Failed to initialize the signals directory!')
        return None

    # 导出交易信号至 Markdown 文件
    for (signal, stocks) in signals.items():
        if not stocks:
            continue

        signal_md_path = signals_dir.joinpath(signal.title().replace('Or', 'or')).with_suffix('.md')

        content = f"### {signal.title().replace('_', ' ').replace('Or', 'or')}" + '\n\n'

        if signal == 'buy':
            content += '|Market|Symbol|Name|Close|Buy Entry|Buy Initial Stop|Buy Trailing Stop|Buy Breakeven|Buy Protect Profit|Buy Profit Target|Reward Risk Ratio|Score|' + '\n'
            content += '|---|---|---|---|---|---|---|---|---|---|---|---|' + '\n'

        elif signal == 'wait_or_raise_stop':
            content += '|Market|Symbol|Name|Close|Buy Trailing Stop|' + '\n'
            content += '|---|---|---|---|---|' + '\n'

        elif signal == 'sell':
            content += '|Market|Symbol|Name|Close|Sell Entry|Sell Initial Stop|Sell Trailing Stop|Sell Breakeven|Sell Protect Profit|Sell Profit Target|Reward Risk Ratio|Score|' + '\n'
            content += '|---|---|---|---|---|---|---|---|---|---|---|---|' + '\n'

        elif signal == 'wait_or_lower_stop':
            content += '|Market|Symbol|Name|Close|Sell Trailing Stop|' + '\n'
            content += '|---|---|---|---|---|' + '\n'

        elif signal == 'stand_aside':
            content += '|Market|Symbol|Name|Close|Buy Trailing Stop|Sell Trailing Stop|' + '\n'
            content += '|---|---|---|---|---|---|' + '\n'

        elif signal == 'trades_prohibited':
            content += '|Market|Symbol|Name|Close|' + '\n'
            content += '|---|---|---|---|' + '\n'

        else:
            pass

        content += '\n'.join(stocks) + '\n'

        try:
            with open(signal_md_path, mode='w', encoding='utf-8') as f:
                f.write(content)
        except OSError as e:
            print(f"[-] Failed to export the <{signal.title().replace('Or', 'or')}> signal file!")

        # 发送企业微信消息
        lib_utils.send_wechat_work_message(content)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
