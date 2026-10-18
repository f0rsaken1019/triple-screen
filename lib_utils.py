#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import _conf
import efinance as ef
import lib_indicators
import pandas as pd
import requests
import sys
import time

from datetime import date, datetime, timedelta
from efinance.utils import MarketType
from talib import abstract

efinance_market_type = {
    'A': MarketType.A_stock,
    'AF': None,
    'HK': MarketType.Hongkong,
    'US': MarketType.US_stock,
}

def main() -> None:
    print('[!] This is a library.')

# 获取给定证券列表的 OHLCV 数据
def get_ohlcv_data(stocks: list[dict[str, str | bool]], timeframe: str = 'D', lookback_years: int = _conf.LOOKBACK_YEARS, between_stocks_delay: int | float = _conf.BETWEEN_STOCKS_DELAY, max_retries: int = _conf.MAX_RETRIES, retry_delay: int | float = _conf.RETRY_DELAY) -> dict[str, pd.DataFrame] | None:
    if not isinstance(stocks, list):
        print(f'[-] [function:{get_ohlcv_data.__name__}] The argument <stocks> should be a {type(list())} instead of a {type(stocks)}!')
        return None

    validation_stocks_errors = list()

    for (index, stock) in enumerate(stocks):
        if not isinstance(stock, dict):
            validation_stocks_errors.append(f'[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]> should be a {type(dict())} instead of a {type(stock)}!')
            continue

        if 'symbol' not in stock:
            validation_stocks_errors.append(f'[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]> is missing the <symbol> key!')
        else:
            if not isinstance(stock['symbol'], str):
                validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['symbol']> should be a {type(str())} instead of a {type(stock['symbol'])}!")
            else:
                stock['symbol'] = stock['symbol'].strip().upper()

        if 'name' not in stock:
            validation_stocks_errors.append(f'[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]> is missing the <name> key!')
        else:
            if not isinstance(stock['name'], str):
                validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['name']> should be a {type(str())} instead of a {type(stock['name'])}!")
            else:
                stock['name'] = stock['name'].strip().upper()

        if 'market' not in stock:
            validation_stocks_errors.append(f'[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]> is missing the <market> key!')
        else:
            if not isinstance(stock['market'], str):
                validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['market']> should be a {type(str())} instead of a {type(stock['market'])}!")
            else:
                stock['market'] = stock['market'].strip().upper()

        if 'match_name' not in stock:
            validation_stocks_errors.append(f'[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]> is missing the <match_name> key!')
        else:
            if not isinstance(stock['match_name'], bool):
                validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['match_name']> should be a {type(bool())} instead of a {type(stock['match_name'])}!")

        if not stock['symbol']:
            validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['symbol']> cannot be an empty string!")
        if not stock['name']:
            validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['name']> cannot be an empty string!")
        if not stock['market']:
            validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The <stocks[{index}]['market']> cannot be an empty string!")

        if stock['market'] not in ('A', 'AF', 'HK', 'US'):
            validation_stocks_errors.append(f"[-] [function:{get_ohlcv_data.__name__}] The value of <stocks[{index}]['market']> is incorrect!")

    if validation_stocks_errors:
        for error in validation_stocks_errors:
            print(error)
        return None

    if not isinstance(timeframe, str):
        print(f'[-] [function:{get_ohlcv_data.__name__}] The argument <timeframe> should be a {type(str())} instead of a {type(timeframe)}!')
        return None

    timeframe = timeframe.strip().upper()

    if not timeframe:
        print(f'[-] [function:{get_ohlcv_data.__name__}] The value of argument <timeframe> cannot be an empty string!')
        return None

    if timeframe not in ('D', 'W'):
        print(f'[-] [function:{get_ohlcv_data.__name__}] The value of argument <timeframe> is incorrect!')
        return None

    if timeframe == 'D':
        klt = 101
    elif timeframe == 'W':
        klt = 102
    else:
        pass

    try:
        lookback_years = int(lookback_years)
    except (TypeError, ValueError) as e:
        lookback_years = 6
    else:
        if lookback_years <= 0:
            lookback_years = 6

    try:
        between_stocks_delay = float(between_stocks_delay)
    except (TypeError, ValueError) as e:
        between_stocks_delay = 1.0
    else:
        if between_stocks_delay < 0.0:
            between_stocks_delay = 1.0

    try:
        max_retries = int(max_retries)
    except (TypeError, ValueError) as e:
        max_retries = 5
    else:
        if max_retries < 0:
            max_retries = 5

    try:
        retry_delay = float(retry_delay)
    except (TypeError, ValueError) as e:
        retry_delay = 1.0
    else:
        if retry_delay < 0.0:
            retry_delay = 1.0

    begin_date = (date.today() - timedelta(days=365 * lookback_years)).strftime('%Y%m%d')
    end_date = (date.today() + timedelta(days=2)).strftime('%Y%m%d')

    ohlcv_data = dict()

    for stock in stocks:
        (stock_identifier, market, match_name) = ((stock['name'] if stock['match_name'] else stock['symbol']), stock['market'], stock['match_name'])

        for _ in range(1 + max_retries):
            try:
                if (stock['market'] == 'A') and (stock['symbol'].startswith('688')):
                    df = ef.stock.get_quote_history(stock_identifier, beg=begin_date, end=end_date, klt=klt, fqt=1, market_type=None, use_id_cache=False, quote_symbol_mode=not match_name)
                else:
                    df = ef.stock.get_quote_history(stock_identifier, beg=begin_date, end=end_date, klt=klt, fqt=1, market_type=efinance_market_type[market], use_id_cache=False, quote_symbol_mode=not match_name)
            except requests.RequestException as e:
                print(f'[-] [function:{get_ohlcv_data.__name__}] Failed to get stock <{stock_identifier}> OHLCV data!')
                time.sleep(retry_delay)
                continue
            else:
                break
        else:
            print(f'[-] [function:{get_ohlcv_data.__name__}] Failed to get stock <{stock_identifier}> OHLCV data!')
            time.sleep(between_stocks_delay)
            continue

        ohlcv = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']].rename(
            columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
            },
            errors='raise'
        )

        ohlcv['volume'] = ohlcv['volume'].astype('uint64')

        ohlcv['date'] = pd.to_datetime(ohlcv['date'], format='%Y-%m-%d')
        ohlcv = ohlcv.set_index('date')

        ohlcv_data[stock_identifier] = ohlcv

        time.sleep(between_stocks_delay)

    if not ohlcv_data:
        return None
    else:
        return ohlcv_data

# 计算周内 OHLCV 和指标数据
def get_intraweek_ohlcv_and_indicators(weekly_df: pd.DataFrame, daily_df: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(weekly_df, pd.DataFrame):
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The argument <weekly_df> should be a {type(pd.DataFrame())} instead of a {type(weekly_df)}!')
        return None

    if weekly_df.empty:
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The value of argument <weekly_df> cannot be an empty DataFrame!')
        return None

    if weekly_df.index.name != 'date':
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The DataFrame <weekly_df> is missing the <date> index!')
        return None

    missing_columns = {'open', 'high', 'low', 'close', 'volume', 'fast_ema', 'macd_histogram', 'elder_impulse'}.difference(weekly_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The DataFrame <weekly_df> is missing the <{missing_columns}> column!')
        return None

    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'open', 'high', 'low', 'close', 'volume', 'fast_ema', 'macd_histogram', 'elder_impulse'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    intraweek_ohlcv_and_indicators = weekly_df.reindex(daily_df.index)

    is_original_row = intraweek_ohlcv_and_indicators.index.isin(weekly_df.index)
    is_new_row = ~is_original_row

    trading_week_end_dates = pd.Series(data=intraweek_ohlcv_and_indicators.index, index=intraweek_ohlcv_and_indicators.index).where(is_original_row).bfill()

    group = daily_df.groupby(trading_week_end_dates)

    open_values = group['open'].transform('first')
    high_values = group['high'].cummax()
    low_values = group['low'].cummin()
    close_values = daily_df['close']
    volume_values = group['volume'].cumsum()

    intraweek_ohlcv_and_indicators.loc[is_new_row, 'open'] = open_values[is_new_row]
    intraweek_ohlcv_and_indicators.loc[is_new_row, 'high'] = high_values[is_new_row]
    intraweek_ohlcv_and_indicators.loc[is_new_row, 'low'] = low_values[is_new_row]
    intraweek_ohlcv_and_indicators.loc[is_new_row, 'close'] = close_values[is_new_row]
    intraweek_ohlcv_and_indicators.loc[is_new_row, 'volume'] = volume_values[is_new_row]

    intraweek_ohlcv_and_indicators['volume'] = intraweek_ohlcv_and_indicators['volume'].astype('uint64')

    base_df = weekly_df[['open', 'high', 'low', 'close', 'volume']]

    for current_date in intraweek_ohlcv_and_indicators.index[is_new_row]:
        temp_index = base_df.index[base_df.index < current_date].union([current_date])
        temp_df = intraweek_ohlcv_and_indicators.loc[temp_index, base_df.columns]

        # 计算指标开始

        # 计算 Fast EMA 指标
        fast_ema_talib_output = abstract.EMA(temp_df, timeperiod=lib_indicators.EMA_PARAMS_W['fast'])
        intraweek_ohlcv_and_indicators.at[current_date, 'fast_ema'] = fast_ema_talib_output.iloc[-1]

        # 计算 MACD 指标
        macd_talib_output = abstract.MACD(temp_df, fastperiod=lib_indicators.MACD_PARAMS['fast'], slowperiod=lib_indicators.MACD_PARAMS['slow'], signalperiod=lib_indicators.MACD_PARAMS['signal'])
        intraweek_ohlcv_and_indicators.at[current_date, 'macd_histogram'] = macd_talib_output['macdhist'].iloc[-1]

        # 计算 Elder Impulse 指标
        indicator_name = 'Elder Impulse'
        elder_impulse_df = pd.DataFrame(data={'fast_ema': intraweek_ohlcv_and_indicators.loc[temp_index, 'fast_ema'], 'macd_histogram': intraweek_ohlcv_and_indicators.loc[temp_index, 'macd_histogram']}, index=temp_index)

        elder_impulse_df = lib_indicators.get_elder_impulse(elder_impulse_df)
        if elder_impulse_df is None:
            print(f'[-] [function:{get_intraweek_ohlcv_and_indicators.__name__}] Failed to get <{indicator_name}> indicator data!')
            return None

        intraweek_ohlcv_and_indicators.at[current_date, 'elder_impulse'] = elder_impulse_df.loc[current_date, 'elder_impulse']

        # 计算指标结束

    return intraweek_ohlcv_and_indicators

# 发送企业微信消息
def send_wechat_work_message(content: str, wechat_webhook_url: str = _conf.wechat_webhook_url, max_retries: int = _conf.MAX_RETRIES, retry_delay: int | float = _conf.RETRY_DELAY, timeout: int | float = _conf.TIMEOUT) -> bool:
    if not isinstance(content, str):
        print(f'[-] [function:{send_wechat_work_message.__name__}] The argument <content> should be a {type(str())} instead of a {type(content)}!')
        return False

    content = content.strip()

    if not content:
        print(f'[-] [function:{send_wechat_work_message.__name__}] The value of argument <content> cannot be an empty string!')
        return False

    if not isinstance(wechat_webhook_url, str):
        print(f'[-] [function:{send_wechat_work_message.__name__}] The argument <wechat_webhook_url> should be a {type(str())} instead of a {type(wechat_webhook_url)}!')
        return False

    wechat_webhook_url = wechat_webhook_url.strip()

    if not wechat_webhook_url:
        print(f'[-] [function:{send_wechat_work_message.__name__}] The value of argument <wechat_webhook_url> cannot be an empty string!')
        return False

    if not wechat_webhook_url.startswith('https://qyapi.weixin.qq.com/cgi-bin/webhook/'):
        print(f'[-] [function:{send_wechat_work_message.__name__}] The value of argument <wechat_webhook_url> is incorrect!')
        return False

    try:
        max_retries = int(max_retries)
    except (TypeError, ValueError) as e:
        max_retries = 5
    else:
        if max_retries < 0:
            max_retries = 5

    try:
        retry_delay = float(retry_delay)
    except (TypeError, ValueError) as e:
        retry_delay = 1.0
    else:
        if retry_delay < 0.0:
            retry_delay = 1.0

    try:
        timeout = float(timeout)
    except (TypeError, ValueError) as e:
        timeout = 180.0
    else:
        if timeout <= 0.0:
            timeout = 180.0

    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = f'{current_datetime}\n\n{content}\n\n{current_datetime}'
    payload = {'msgtype': 'markdown_v2', 'markdown_v2': {'content': content}}

    for _ in range(1 + max_retries):
        try:
            response = requests.post(wechat_webhook_url, json=payload, headers={'Content-Type': 'application/json; charset=utf-8'}, timeout=timeout)
        except requests.RequestException as e:
            print(f'[-] [function:{send_wechat_work_message.__name__}] {e}')
            time.sleep(retry_delay)
            continue
        else:
            if response.status_code != 200:
                print(f'[-] [function:{send_wechat_work_message.__name__}] {response.status_code} {response.reason}')
                time.sleep(retry_delay)
                continue

            try:
                (errcode, errmsg) = (response.json()['errcode'], response.json()['errmsg'])
            except (requests.JSONDecodeError, KeyError) as e:
                print(f'[-] [function:{send_wechat_work_message.__name__}] {e}')
                time.sleep(retry_delay)
                continue

            if errcode != 0:
                print(f'[-] [function:{send_wechat_work_message.__name__}] errcode:{errcode} errmsg:{errmsg}')
                time.sleep(retry_delay)
                continue
            else:
                return True
    else:
        print(f'[-] [function:{send_wechat_work_message.__name__}] Failed to send Wechat Work message!')
        return False

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
