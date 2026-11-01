#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import _conf
import concurrent.futures
import lib_indicators
import lib_universe_builders
import lib_utils
import multiprocessing
import os
import pandas as pd
import re
import shutil
import sys
import tomllib

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MAX_WORKERS = min(max((cpu_count if (cpu_count := os.cpu_count()) is not None else 1) - 1, 1), 61)

def main() -> None:
    # 获取自选列表成分股
    if len(sys.argv) == 1:
        try:
            with open(BASE_DIR.joinpath('_backtesting.toml'), 'rb') as f:
                data = tomllib.load(f)
        except (FileNotFoundError, PermissionError) as e:
            print("[-] Cannot open the '_backtesting.toml' file!")
            return None
        except tomllib.TOMLDecodeError as e:
            print("[-] The '_backtesting.toml' is an invalid TOML document!")
            return None
        else:
            watchlist = data['watchlist']

        sub_dir = 'backtesting'.capitalize()

        stocks = lib_universe_builders.get_watchlist_members(watchlist)

    elif len(sys.argv) == 2:
        toml_doc_name = sys.argv[1].strip()

        if not re.fullmatch(r'[\w.-]+', toml_doc_name, flags=re.ASCII):
            print('[-] The value of argument <toml_doc_name> only supports the following characters: [a-zA-Z0-9_.-]')
            return None

        try:
            with open(BASE_DIR.joinpath(toml_doc_name), 'rb') as f:
                data = tomllib.load(f)
        except (FileNotFoundError, PermissionError) as e:
            print(f"[-] Cannot open the '{toml_doc_name}' file!")
            return None
        except tomllib.TOMLDecodeError as e:
            print(f"[-] The '{toml_doc_name}' is an invalid TOML document!")
            return None
        else:
            watchlist = data['watchlist']

        sub_dir = toml_doc_name.split('.')[0].replace('-', '_').upper()

        stocks = lib_universe_builders.get_watchlist_members(watchlist)

    # elif len(sys.argv) == 4:
    #     (function, params) = (sys.argv[1].strip().capitalize(), (sys.argv[2].strip().upper(), sys.argv[3].strip().upper()))

    #     # 获取指数成分股
    #     if function == 'index'.capitalize():
    #         (market, index) = (params[0], params[1])

    #         sub_dir = f'{market}_{index}'

    #         stocks = lib_universe_builders.get_index_members(market, index)

    #     # 占位符
    #     elif function == '_':
    #         return None

    #     else:
    #         print(f"[-] The <function> '{function}' is not supported!")
    #         return None

    else:
        print('[-] The parameters are incorrect!')
        return None

    if stocks is None:
        print('[-] Failed to get stock list!')
        return None

    backtesting_data_begin_date = _conf.BACKTESTING_DATA_BEGIN_DATE
    backtesting_data_end_date = _conf.BACKTESTING_DATA_END_DATE

    # 获取周频 OHLCV 数据
    weekly_ohlcv_data = lib_utils.get_ohlcv_data(stocks, timeframe='W', begin_date=backtesting_data_begin_date, end_date=backtesting_data_end_date)

    if weekly_ohlcv_data is None:
        print('[-] Failed to get weekly OHLCV data!')
        return None

    # 获取日频 OHLCV 数据
    daily_ohlcv_data = lib_utils.get_ohlcv_data(stocks, timeframe='D', begin_date=backtesting_data_begin_date, end_date=backtesting_data_end_date)

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

    # # 排除新股
    # if _conf.EXCLUDE_NEWLY_LISTED_STOCKS:
    #     min_daily_kline_num = _conf.STOCK_MIN_DAILY_KLINE_NUM

    #     try:
    #         min_daily_kline_num = int(min_daily_kline_num)
    #     except (TypeError, ValueError) as e:
    #         min_daily_kline_num = 252
    #     else:
    #         if min_daily_kline_num < 252:
    #             min_daily_kline_num = 252

    #     stocks = [stock for stock in stocks if len(stock['daily_ohlcv']) >= min_daily_kline_num]

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
        weekly_df = stock['weekly_ohlcv'][['open', 'high', 'low', 'close', 'volume', f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}", 'MACD_histogram', 'elder_impulse', f'rsi_{lib_indicators.RSI_PERIODS_W}', f'efi_{lib_indicators.EFI_PERIODS_W}', f"slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}"]].rename(
            columns={
                f"fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}": 'fast_ema',
                'MACD_histogram': 'macd_histogram',
                f'rsi_{lib_indicators.RSI_PERIODS_W}': 'rsi',
                f'efi_{lib_indicators.EFI_PERIODS_W}': 'efi',
                f"slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}": 'slow_ema',
            },
            errors='raise'
        )

        daily_df = stock['daily_ohlcv'][['open', 'high', 'low', 'close', 'volume']]

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

        intraweek_df = stock['intraweek_ohlcv_and_indicators'][['intraweek_elder_impulse']].rename(columns={'intraweek_elder_impulse': 'elder_impulse'}, errors='raise')

        daily_df = stock['daily_ohlcv'][['elder_impulse']]

        elder_impulse_release_df = lib_indicators.get_elder_impulse_release(intraweek_df, daily_df)

        if elder_impulse_release_df is None:
            print(f'[-] Failed to get stock <{stock_identifier}> daily <{indicator_name}> indicator data!')
            return None

        stock['daily_ohlcv'] = stock['daily_ohlcv'].join(elder_impulse_release_df)

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

    # 生成回测数据
    for stock in stocks:
        (symbol, name, market) = (stock['symbol'], stock['name'], stock['market'])

        daily_df = stock['daily_ohlcv']
        intraweek_df = stock['intraweek_ohlcv_and_indicators']

        daily_columns = [
            'open', 'high', 'low', 'close', 'volume',
            f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}",
            f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}",
            f'rsi_{lib_indicators.RSI_PERIODS_D}', f'efi_{lib_indicators.EFI_PERIODS_D}',
            'elder_impulse', 'elder_impulse_release',
            'keltner_upper_band_p1_atr', 'keltner_lower_band_n1_atr',
            'pullback_entry_buyer', 'pullback_entry_seller',
            'atr_initial_stop_buyer', 'atr_initial_stop_seller',
            'atr_trailing_stop_buyer', 'atr_trailing_stop_seller',
            'keltner_target_buyer', 'keltner_target_seller',
            'breakeven_price_buyer', 'breakeven_stop_buyer',
            'breakeven_price_seller', 'breakeven_stop_seller',
            'protect_profit_price_buyer', 'protect_profit_stop_buyer',
            'protect_profit_price_seller', 'protect_profit_stop_seller',
            'reward_risk_ratio_buyer', 'reward_risk_ratio_seller',
        ]

        intraweek_columns = [
            'intraweek_elder_impulse',
            f'intraweek_rsi_{lib_indicators.RSI_PERIODS_W}',
            f'intraweek_efi_{lib_indicators.EFI_PERIODS_W}',
            f"intraweek_fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}",
            f"intraweek_slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}",
            f"weekly_previous_fast_ema_{lib_indicators.EMA_PARAMS_W['fast']}",
            f"weekly_previous_slow_ema_{lib_indicators.EMA_PARAMS_W['slow']}",
        ]

        backtesting_data_df = pd.concat(
            [
                daily_df[daily_columns].rename(
                    columns={
                        'keltner_upper_band_p1_atr': 'keltner_upper_band',
                        'keltner_lower_band_n1_atr': 'keltner_lower_band',
                        },
                    errors='raise'),
                intraweek_df[intraweek_columns],
            ],
            axis='columns',
            sort=True
        )

        backtesting_data_df.insert(
            backtesting_data_df.columns.get_loc(
                f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}"
            ) + 1,
            f"previous_fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}",
            backtesting_data_df[
                f"fast_ema_{lib_indicators.EMA_PARAMS_D['fast']}"
            ].shift(periods=1, axis='index')
        )

        backtesting_data_df.insert(
            backtesting_data_df.columns.get_loc(
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}"
            ) + 1,
            f"previous_slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}",
            backtesting_data_df[
                f"slow_ema_{lib_indicators.EMA_PARAMS_D['slow']}"
            ].shift(periods=1, axis='index')
        )

        backtesting_data_df.insert(
            backtesting_data_df.columns.get_loc(
                f'rsi_{lib_indicators.RSI_PERIODS_D}'
            ) + 1,
            f'previous_rsi_{lib_indicators.RSI_PERIODS_D}',
            backtesting_data_df[
                f'rsi_{lib_indicators.RSI_PERIODS_D}'
            ].shift(periods=1, axis='index')
        )

        backtesting_data_df.insert(
            backtesting_data_df.columns.get_loc(
                f'efi_{lib_indicators.EFI_PERIODS_D}'
            ) + 1,
            f'previous_efi_{lib_indicators.EFI_PERIODS_D}',
            backtesting_data_df[
                f'efi_{lib_indicators.EFI_PERIODS_D}'
            ].shift(periods=1, axis='index')
        )

        backtesting_data_df.insert(0, 'name', name)
        backtesting_data_df.insert(0, 'symbol', symbol)
        backtesting_data_df.insert(0, 'market', market)

        stock['backtesting_data'] = backtesting_data_df

    # 初始化回测数据目录
    backtesting_data_dir = BASE_DIR.joinpath('backtesting_data').joinpath(sub_dir)

    try:
        if backtesting_data_dir.is_file() or backtesting_data_dir.is_symlink():
            backtesting_data_dir.unlink()
        if backtesting_data_dir.is_dir():
            shutil.rmtree(backtesting_data_dir)
        backtesting_data_dir.mkdir(parents=True)
    except PermissionError as e:
        print('[-] Failed to initialize the backtesting data directory!')
        return None

    # 导出回测数据至 CSV 文件
    market_backtesting_data_frames = dict()

    for stock in stocks:
        (symbol, name, market, backtesting_data) = (stock['symbol'], stock['name'], stock['market'], stock['backtesting_data'])

        market = 'A' if market == 'AF' else market

        stock_backtesting_data_dir = backtesting_data_dir.joinpath(market)
        stock_backtesting_data_dir.mkdir(exist_ok=True)

        backtesting_data_csv_path = stock_backtesting_data_dir.joinpath(f'{market}_{symbol}_{name}_Backtesting' + '.csv')
        backtesting_data.to_csv(backtesting_data_csv_path)

        market_backtesting_data_frames.setdefault(market, list()).append(backtesting_data)

    for (market, backtesting_data_frames) in market_backtesting_data_frames.items():
        if len(backtesting_data_frames) < 2:
            continue

        market_backtesting_data_dir = backtesting_data_dir.joinpath(market)
        market_backtesting_data_dir.mkdir(exist_ok=True)

        market_backtesting_data = pd.concat(backtesting_data_frames, axis='index', sort=False)

        market_backtesting_data_csv_path = market_backtesting_data_dir.joinpath(f'{market}_Multi_Stock_Backtesting' + '.csv')
        market_backtesting_data.to_csv(market_backtesting_data_csv_path)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
