#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import pandas as pd
import sys

# Second Screen Oscillator
SECOND_SCREEN_OSCILLATOR = 'EFI'    # 'RSI' | 'EFI' #

# RSI Level
RSI_LEVEL = {'oversold': 30, 'overbought': 70}

def main() -> None:
    print('[!] This is a library.')

# 计算 Triple Screen 系统交易信号
def get_triple_screen_signals(daily_df: pd.DataFrame, weekly_df: pd.DataFrame, second_screen_oscillator: str = SECOND_SCREEN_OSCILLATOR, rsi_level: dict[str, int | float] = RSI_LEVEL) -> str | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'elder_impulse_release', 'elder_impulse', 'close', 'slow_ema', 'keltner_upper_band', 'keltner_lower_band', 'rsi', 'efi'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    if not isinstance(weekly_df, pd.DataFrame):
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The argument <weekly_df> should be a {type(pd.DataFrame())} instead of a {type(weekly_df)}!')
        return None

    if weekly_df.empty:
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The value of argument <weekly_df> cannot be an empty DataFrame!')
        return None

    if weekly_df.index.name != 'date':
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The DataFrame <weekly_df> is missing the <date> index!')
        return None

    missing_columns = {'elder_impulse', 'slow_ema', 'rsi', 'efi'}.difference(weekly_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The DataFrame <weekly_df> is missing the <{missing_columns}> column!')
        return None

    if not isinstance(second_screen_oscillator, str):
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The argument <second_screen_oscillator> should be a {type(str())} instead of a {type(second_screen_oscillator)}!')
        return None

    second_screen_oscillator = second_screen_oscillator.strip().upper()

    if second_screen_oscillator not in ('RSI', 'EFI'):
        print(f'[-] [function:{get_triple_screen_signals.__name__}] The value of argument <second_screen_oscillator> is incorrect!')
        return None

    validation_rsi_level_errors = list()

    if not isinstance(rsi_level, dict):
        validation_rsi_level_errors.append(f'[-] [function:{get_triple_screen_signals.__name__}] The argument <rsi_level> should be a {type(dict())} instead of a {type(rsi_level)}!')
        return None

    if 'oversold' not in rsi_level:
        validation_rsi_level_errors.append(f'[-] [function:{get_triple_screen_signals.__name__}] The <rsi_level> is missing the <oversold> key!')
    else:
        if not isinstance(rsi_level['oversold'], (int, float)):
            validation_rsi_level_errors.append(f"[-] [function:{get_triple_screen_signals.__name__}] The <rsi_level['oversold']> should be a {type(int())} or {type(float())} instead of a {type(rsi_level['oversold'])}!")

    if 'overbought' not in rsi_level:
        validation_rsi_level_errors.append(f'[-] [function:{get_triple_screen_signals.__name__}] The <rsi_level> is missing the <overbought> key!')
    else:
        if not isinstance(rsi_level['overbought'], (int, float)):
            validation_rsi_level_errors.append(f"[-] [function:{get_triple_screen_signals.__name__}] The <rsi_level['overbought']> should be a {type(int())} or {type(float())} instead of a {type(rsi_level['overbought'])}!")

    if (rsi_level['oversold'] < 20.0) or (rsi_level['oversold'] > 40.0):
        validation_rsi_level_errors.append(f"[-] [function:{get_triple_screen_signals.__name__}] The value of <rsi_level['oversold']> is incorrect!")
    if (rsi_level['overbought'] < 60.0) or (rsi_level['overbought'] > 80.0):
        validation_rsi_level_errors.append(f"[-] [function:{get_triple_screen_signals.__name__}] The value of <rsi_level['overbought']> is incorrect!")

    if validation_rsi_level_errors:
        for error in validation_rsi_level_errors:
            print(error)
        return None

    daily_df = daily_df.dropna()
    weekly_df = weekly_df.dropna()

    signals = {
        'bullish': 'wait_or_raise_stop',
        'bearish': 'wait_or_lower_stop',
        'neutral': 'stand_aside',
        'no_trades': 'trades_prohibited',
    }

    latest_release = daily_df['elder_impulse_release'].iloc[-1]

    weekly_latest_impulse = weekly_df['elder_impulse'].iloc[-1]
    daily_latest_impulse = daily_df['elder_impulse'].iloc[-1]

    latest_rsi = daily_df['rsi'].iloc[-1]
    second_latest_rsi = daily_df['rsi'].iloc[-2]

    latest_efi = daily_df['efi'].iloc[-1]
    second_latest_efi = daily_df['efi'].iloc[-2]

    weekly_latest_rsi = weekly_df['rsi'].iloc[-1]
    weekly_latest_efi = weekly_df['efi'].iloc[-1]

    if second_screen_oscillator == 'RSI':
        if (latest_release == 'bullish') and (weekly_latest_impulse == 'up') and (daily_latest_impulse == 'up') and (weekly_latest_rsi < rsi_level['overbought']) and (second_latest_rsi < rsi_level['oversold']) and (latest_rsi >= rsi_level['oversold']) and (weekly_latest_efi > 0.0) and (weekly_df['slow_ema'].iloc[-1] > weekly_df['slow_ema'].iloc[-2]) and (daily_df['slow_ema'].iloc[-1] > daily_df['slow_ema'].iloc[-2]) and (daily_df['close'].iloc[-1] <= daily_df['keltner_upper_band'].iloc[-1]):
            return 'buy'
        elif (latest_release == 'bearish') and (weekly_latest_impulse == 'down') and (daily_latest_impulse == 'down') and (weekly_latest_rsi > rsi_level['oversold']) and (second_latest_rsi > rsi_level['overbought']) and (latest_rsi <= rsi_level['overbought']) and (weekly_latest_efi < 0.0) and (weekly_df['slow_ema'].iloc[-1] < weekly_df['slow_ema'].iloc[-2]) and (daily_df['slow_ema'].iloc[-1] < daily_df['slow_ema'].iloc[-2]) and (daily_df['close'].iloc[-1] >= daily_df['keltner_lower_band'].iloc[-1]):
            return 'sell'
        else:
            return signals[latest_release]
    elif second_screen_oscillator == 'EFI':
        if (latest_release == 'bullish') and (weekly_latest_impulse == 'up') and (daily_latest_impulse == 'up') and (weekly_latest_efi > 0.0) and (second_latest_efi < 0.0) and (latest_efi >= 0.0) and (weekly_latest_rsi < rsi_level['overbought']) and (weekly_df['slow_ema'].iloc[-1] > weekly_df['slow_ema'].iloc[-2]) and (daily_df['slow_ema'].iloc[-1] > daily_df['slow_ema'].iloc[-2]) and (daily_df['close'].iloc[-1] <= daily_df['keltner_upper_band'].iloc[-1]):
            return 'buy'
        elif (latest_release == 'bearish') and (weekly_latest_impulse == 'down') and (daily_latest_impulse == 'down') and (weekly_latest_efi < 0.0) and (second_latest_efi > 0.0) and (latest_efi <= 0.0) and (weekly_latest_rsi > rsi_level['oversold']) and (weekly_df['slow_ema'].iloc[-1] < weekly_df['slow_ema'].iloc[-2]) and (daily_df['slow_ema'].iloc[-1] < daily_df['slow_ema'].iloc[-2]) and (daily_df['close'].iloc[-1] >= daily_df['keltner_lower_band'].iloc[-1]):
            return 'sell'
        else:
            return signals[latest_release]
    else:
        pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
