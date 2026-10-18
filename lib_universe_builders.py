#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import _conf
import efinance as ef
import pandas as pd
import requests
import sys
import time

def main() -> None:
    print('[!] This is a library.')

# 获取自选列表成分股
def get_watchlist_members(watchlist: list[dict[str, str | bool]]) -> list[dict[str, str | bool]] | None:
    if not isinstance(watchlist, list):
        print(f'[-] [function:{get_watchlist_members.__name__}] The argument <watchlist> should be a {type(list())} instead of a {type(watchlist)}!')
        return None

    validation_watchlist_errors = list()

    for (index, stock) in enumerate(watchlist):
        if not isinstance(stock, dict):
            validation_watchlist_errors.append(f'[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]> should be a {type(dict())} instead of a {type(stock)}!')
            continue

        if 'symbol' not in stock:
            validation_watchlist_errors.append(f'[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]> is missing the <symbol> key!')
        else:
            if not isinstance(stock['symbol'], str):
                validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['symbol']> should be a {type(str())} instead of a {type(stock['symbol'])}!")
            else:
                stock['symbol'] = stock['symbol'].strip().upper()

        if 'name' not in stock:
            validation_watchlist_errors.append(f'[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]> is missing the <name> key!')
        else:
            if not isinstance(stock['name'], str):
                validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['name']> should be a {type(str())} instead of a {type(stock['name'])}!")
            else:
                stock['name'] = stock['name'].strip().upper()

        if 'market' not in stock:
            validation_watchlist_errors.append(f'[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]> is missing the <market> key!')
        else:
            if not isinstance(stock['market'], str):
                validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['market']> should be a {type(str())} instead of a {type(stock['market'])}!")
            else:
                stock['market'] = stock['market'].strip().upper()

        if 'match_name' not in stock:
            validation_watchlist_errors.append(f'[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]> is missing the <match_name> key!')
        else:
            if not isinstance(stock['match_name'], bool):
                validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['match_name']> should be a {type(bool())} instead of a {type(stock['match_name'])}!")

        if not stock['symbol']:
            validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['symbol']> cannot be an empty string!")
        if not stock['name']:
            validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['name']> cannot be an empty string!")
        if not stock['market']:
            validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The <watchlist[{index}]['market']> cannot be an empty string!")

        if stock['market'] not in ('A', 'AF', 'HK', 'US'):
            validation_watchlist_errors.append(f"[-] [function:{get_watchlist_members.__name__}] The value of <watchlist[{index}]['market']> is incorrect!")

    if validation_watchlist_errors:
        for error in validation_watchlist_errors:
            print(error)
        return None

    return watchlist

# 获取指数成分股
def get_index_members(market: str, index: str, max_retries: int = _conf.MAX_RETRIES, retry_delay: int | float = _conf.RETRY_DELAY) -> list[dict[str, str | bool]] | None:
    if not isinstance(market, str):
        print(f'[-] [function:{get_index_members.__name__}] The argument <market> should be a {type(str())} instead of a {type(market)}!')
        return None

    market = market.strip().upper()

    if not market:
        print(f'[-] [function:{get_index_members.__name__}] The value of argument <market> cannot be an empty string!')
        return None

    if market not in ('A', 'HK', 'US'):
        print(f'[-] [function:{get_index_members.__name__}] The value of argument <market> is incorrect!')
        return None

    if not isinstance(index, str):
        print(f'[-] [function:{get_index_members.__name__}] The argument <index> should be a {type(str())} instead of a {type(index)}!')
        return None

    index = index.strip().upper()

    if not index:
        print(f'[-] [function:{get_index_members.__name__}] The value of argument <index> cannot be an empty string!')
        return None

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

    df = pd.DataFrame()

    for _ in range(1 + max_retries):
        try:
            df = ef.stock.get_members(index)
        except requests.RequestException as e:
            print(f'[-] [function:{get_index_members.__name__}] Failed to get index <{index}> members!')
            time.sleep(retry_delay)
            continue
        else:
            break
    else:
        print(f'[-] [function:{get_index_members.__name__}] Failed to get index <{index}> members!')
        return None

    if df.empty:
        return None
    else:
        df = df[['股票代码', '股票名称']].rename(columns={'股票代码': 'symbol', '股票名称': 'name'}, errors='raise')
        stocks = df[['symbol', 'name']].to_dict(orient='records')

        # 美股市场股票代码变更映射
        us_stock_symbol_renames = {'BK': 'BNY', 'EQR': 'VMRK', 'FI': 'FISV', 'MMC': 'MRSH', 'SATS': 'ECHO'}

        for stock in stocks:
            if market == 'US':
                stock['symbol'] = us_stock_symbol_renames.get(stock['symbol'], stock['symbol'])
            stock['market'] = market
            stock['match_name'] = False

        return stocks

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
