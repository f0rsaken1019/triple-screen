#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import numpy as np
import pandas as pd
import sys

from talib import abstract

# 定义指标计算参数开始

# Exponential Moving Average (EMA)
EMA_PARAMS_D = {'fast': 13, 'slow': 26}
EMA_PARAMS_W = {'fast': 13, 'slow': 26}

# Moving Average Convergence Divergence (MACD)
MACD_PARAMS = {'fast': 12, 'slow': 26, 'signal': 9}

# Relative Strength Index (RSI)
RSI_PERIODS_D = 4    # 2 | 3 | 4 #
RSI_PERIODS_W = 13

# Elder Force Index (EFI)
EFI_PERIODS_D = 4    # 2 | 3 | 4 #
EFI_PERIODS_W = 13

# Quarter Volume SMA
QUARTER_VOLUME_SMA_PERIODS_D = 63
QUARTER_VOLUME_SMA_PERIODS_W = 13

# Volume SMA
VOLUME_SMA_PERIODS_DAILY = {'slow': 21, 'fast': 10, 'week': 5}

# Average True Range (ATR)
ATR_PERIODS = 21

# Pullback Entry
PULLBACK_ENTRY_STYLE = 'MAX'    # 'MAX' | 'MEAN' | 'MIN' #
PULLBACK_ENTRY_ATR_MULTIPLIER = {'buyer': 0.00, 'seller': 0.00}

# ATR Initial Stop
ATR_INITIAL_STOP_MULTIPLIER = {'buyer': 1.30, 'seller': 1.30}

# ATR Trailing Stop
ATR_TRAILING_STOP_MULTIPLIER = {'buyer': 1.50, 'seller': 1.50}

# Keltner Target
KELTNER_TARGET_BREAKOUT_PCT = {'buyer': 0.00, 'seller': 0.00}

# Breakeven
BREAKEVEN_OPEN_PROFIT_PCT = {'buyer': 0.30, 'seller': 0.30}

# 定义指标计算参数结束

def main() -> None:
    print('[!] This is a library.')

# 计算 Elder Impulse 指标
def get_elder_impulse(original_df: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(original_df, pd.DataFrame):
        print(f'[-] [function:{get_elder_impulse.__name__}] The argument <original_df> should be a {type(pd.DataFrame())} instead of a {type(original_df)}!')
        return None

    if original_df.empty:
        print(f'[-] [function:{get_elder_impulse.__name__}] The value of argument <original_df> cannot be an empty DataFrame!')
        return None

    if original_df.index.name != 'date':
        print(f'[-] [function:{get_elder_impulse.__name__}] The DataFrame <original_df> is missing the <date> index!')
        return None

    missing_columns = {'fast_ema', 'macd_histogram'}.difference(original_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_elder_impulse.__name__}] The DataFrame <original_df> is missing the <{missing_columns}> column!')
        return None

    elder_impulse_df = pd.DataFrame(data={'elder_impulse': pd.NA}, index=original_df.index, dtype='string')

    fast_ema_diff = original_df['fast_ema'].diff(periods=1)
    macd_histogram_diff = original_df['macd_histogram'].diff(periods=1)

    are_both_notna = fast_ema_diff.notna() & macd_histogram_diff.notna()

    are_both_rising = are_both_notna & fast_ema_diff.gt(0.0) & macd_histogram_diff.gt(0.0)
    are_both_falling = are_both_notna & fast_ema_diff.lt(0.0) & macd_histogram_diff.lt(0.0)
    against_one_another = are_both_notna & ~(are_both_rising | are_both_falling)

    elder_impulse_df.loc[are_both_rising, 'elder_impulse'] = 'up'    # It can be displayed as 'lime'. #
    elder_impulse_df.loc[are_both_falling, 'elder_impulse'] = 'down'    # It can be displayed as 'red'. #
    elder_impulse_df.loc[against_one_another, 'elder_impulse'] = 'neutral'    # It can be displayed as 'cyan'. #

    return elder_impulse_df

# 计算 Triple Screen 系统所需指标
def get_triple_screen_indicators(ohlcv: pd.DataFrame, timeframe: str) -> dict[str, pd.DataFrame] | None:
    if not isinstance(ohlcv, pd.DataFrame):
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The argument <ohlcv> should be a {type(pd.DataFrame())} instead of a {type(ohlcv)}!')
        return None

    if ohlcv.empty:
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The value of argument <ohlcv> cannot be an empty DataFrame!')
        return None

    if ohlcv.index.name != 'date':
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The DataFrame <ohlcv> is missing the <date> index!')
        return None

    missing_columns = {'open', 'high', 'low', 'close', 'volume'}.difference(ohlcv.columns)

    if missing_columns:
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The DataFrame <ohlcv> is missing the <{missing_columns}> column!')
        return None

    if not isinstance(timeframe, str):
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The argument <timeframe> should be a {type(str())} instead of a {type(timeframe)}!')
        return None

    timeframe = timeframe.strip().upper()

    if not timeframe:
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The value of argument <timeframe> cannot be an empty string!')
        return None

    if timeframe not in ('D', 'W'):
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] The value of argument <timeframe> is incorrect!')
        return None

    if timeframe == 'D':
        (ema_params, rsi_periods, efi_periods, quarter_volume_sma_periods) = (EMA_PARAMS_D, RSI_PERIODS_D, EFI_PERIODS_D, QUARTER_VOLUME_SMA_PERIODS_D)
    elif timeframe == 'W':
        (ema_params, rsi_periods, efi_periods, quarter_volume_sma_periods) = (EMA_PARAMS_W, RSI_PERIODS_W, EFI_PERIODS_W, QUARTER_VOLUME_SMA_PERIODS_W)
    else:
        pass

    triple_screen_indicators = dict()

    # 计算指标开始

    # 计算 Volume Direction 指标
    indicator_name = 'Volume Direction'

    volume_direction_df = pd.DataFrame(data={'volume_direction': pd.NA}, index=ohlcv.index, dtype='string')

    is_rising = ohlcv['close'].gt(ohlcv['open'])
    is_falling = ohlcv['close'].lt(ohlcv['open'])
    is_flat = ohlcv['close'].eq(ohlcv['open'])

    volume_direction_df.loc[is_rising, 'volume_direction'] = 'up'    # It can be displayed as 'lime'. #
    volume_direction_df.loc[is_falling, 'volume_direction'] = 'down'    # It can be displayed as 'red'. #
    volume_direction_df.loc[is_flat, 'volume_direction'] = 'neutral'    # It can be displayed as 'cyan'. #

    triple_screen_indicators[indicator_name] = volume_direction_df

    # 计算 Fast EMA 指标
    indicator_name = 'Fast EMA'
    fast_ema_talib_output = abstract.EMA(ohlcv, timeperiod=ema_params['fast'])
    fast_ema_df = pd.DataFrame(data={f"fast_ema_{ema_params['fast']}": fast_ema_talib_output}, index=ohlcv.index, dtype='float64')
    triple_screen_indicators[indicator_name] = fast_ema_df

    # 计算 Slow EMA 指标
    indicator_name = 'Slow EMA'
    slow_ema_talib_output = abstract.EMA(ohlcv, timeperiod=ema_params['slow'])
    slow_ema_df = pd.DataFrame(data={f"slow_ema_{ema_params['slow']}": slow_ema_talib_output}, index=ohlcv.index, dtype='float64')
    triple_screen_indicators[indicator_name] = slow_ema_df

    # 计算 MACD 指标
    indicator_name = 'MACD'
    macd_talib_output = abstract.MACD(ohlcv, fastperiod=MACD_PARAMS['fast'], slowperiod=MACD_PARAMS['slow'], signalperiod=MACD_PARAMS['signal'])
    macd_df = pd.DataFrame(data={'macd': macd_talib_output['macd'], 'signal': macd_talib_output['macdsignal'], 'histogram': macd_talib_output['macdhist']}, index=ohlcv.index, dtype='float64')

    macd_df['histogram_direction'] = pd.NA
    macd_df['histogram_direction'] = macd_df['histogram_direction'].astype('string')

    macd_histogram_diff = macd_df['histogram'].diff(periods=1)

    is_rising = macd_histogram_diff.notna() & macd_histogram_diff.gt(0.0)
    is_falling = macd_histogram_diff.notna() & macd_histogram_diff.lt(0.0)
    is_flat = macd_histogram_diff.notna() & macd_histogram_diff.eq(0.0)

    macd_df.loc[is_rising, 'histogram_direction'] = 'up'    # It can be displayed as 'lime'. #
    macd_df.loc[is_falling, 'histogram_direction'] = 'down'    # It can be displayed as 'red'. #
    macd_df.loc[is_flat, 'histogram_direction'] = 'neutral'    # It can be displayed as 'cyan'. #

    triple_screen_indicators[indicator_name] = macd_df

    # 计算 RSI 指标
    indicator_name = 'RSI'
    rsi_talib_output = abstract.RSI(ohlcv, timeperiod=rsi_periods)
    rsi_df = pd.DataFrame(data={f'rsi_{rsi_periods}': rsi_talib_output}, index=ohlcv.index, dtype='float64')
    triple_screen_indicators[indicator_name] = rsi_df

    # 计算 EFI 指标
    indicator_name = 'EFI'
    efi_talib_output = abstract.EFI(ohlcv['close'], ohlcv['volume'], timeperiod=efi_periods)
    efi_df = pd.DataFrame(data={f'efi_{efi_periods}': efi_talib_output}, index=ohlcv.index, dtype='float64')
    triple_screen_indicators[indicator_name] = efi_df

    # 计算 Quarter Volume SMA 指标
    indicator_name = 'Quarter Volume SMA'
    quarter_volume_sma_talib_output = abstract.SMA(ohlcv, price='volume', timeperiod=quarter_volume_sma_periods)
    quarter_volume_sma_df = pd.DataFrame(data={f"quarter_volume_sma_{quarter_volume_sma_periods}": quarter_volume_sma_talib_output.round(0).astype('UInt64')}, index=ohlcv.index, dtype='UInt64')
    triple_screen_indicators[indicator_name] = quarter_volume_sma_df

    # 计算 Elder Impulse 指标
    indicator_name = 'Elder Impulse'
    elder_impulse_df = pd.DataFrame(data={'fast_ema': fast_ema_df[f"fast_ema_{ema_params['fast']}"], 'macd_histogram': macd_df['histogram']}, index=ohlcv.index)
    elder_impulse_df = get_elder_impulse(elder_impulse_df)
    if elder_impulse_df is None:
        print(f'[-] [function:{get_triple_screen_indicators.__name__}] Failed to get <{indicator_name}> indicator data!')
        return None
    triple_screen_indicators[indicator_name] = elder_impulse_df

    # 计算指标结束

    return triple_screen_indicators

# 计算 Elder Impulse Release 指标
def get_elder_impulse_release(intraweek_df: pd.DataFrame, daily_df: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(intraweek_df, pd.DataFrame):
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The argument <intraweek_df> should be a {type(pd.DataFrame())} instead of a {type(intraweek_df)}!')
        return None

    if intraweek_df.empty:
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The value of argument <intraweek_df> cannot be an empty DataFrame!')
        return None

    if intraweek_df.index.name != 'date':
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The DataFrame <intraweek_df> is missing the <date> index!')
        return None

    if 'elder_impulse' not in intraweek_df.columns:
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The DataFrame <intraweek_df> is missing the <elder_impulse> column!')
        return None

    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    if 'elder_impulse' not in daily_df.columns:
        print(f'[-] [function:{get_elder_impulse_release.__name__}] The DataFrame <daily_df> is missing the <elder_impulse> column!')
        return None

    elder_impulse_release_df = pd.DataFrame(data={'elder_impulse_release': pd.NA}, index=daily_df.index, dtype='string')

    are_both_notna = intraweek_df['elder_impulse'].notna() & daily_df['elder_impulse'].notna()

    no_trades_allowed = are_both_notna & ((intraweek_df['elder_impulse'].eq('up') & daily_df['elder_impulse'].eq('down')) | (intraweek_df['elder_impulse'].eq('down') & daily_df['elder_impulse'].eq('up')))
    both_are_allowed = are_both_notna & (intraweek_df['elder_impulse'].eq('neutral') & daily_df['elder_impulse'].eq('neutral'))
    bullish = are_both_notna & ((intraweek_df['elder_impulse'].eq('up') & daily_df['elder_impulse'].isin(('up', 'neutral'))) | (daily_df['elder_impulse'].eq('up') & intraweek_df['elder_impulse'].isin(('up', 'neutral'))))
    bearish = are_both_notna & ((intraweek_df['elder_impulse'].eq('down') & daily_df['elder_impulse'].isin(('down', 'neutral'))) | (daily_df['elder_impulse'].eq('down') & intraweek_df['elder_impulse'].isin(('down', 'neutral'))))

    elder_impulse_release_df.loc[no_trades_allowed, 'elder_impulse_release'] = 'no_trades'    # It can be displayed as 'gray'. #
    elder_impulse_release_df.loc[both_are_allowed, 'elder_impulse_release'] = 'neutral'    # It can be displayed as 'cyan'. #
    elder_impulse_release_df.loc[bullish, 'elder_impulse_release'] = 'bullish'    # It can be displayed as 'lime'. #
    elder_impulse_release_df.loc[bearish, 'elder_impulse_release'] = 'bearish'    # It can be displayed as 'red'. #

    return elder_impulse_release_df

# 计算 Volume SMA 指标
def get_volume_sma_indicators(daily_ohlcv: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(daily_ohlcv, pd.DataFrame):
        print(f'[-] [function:{get_volume_sma_indicators.__name__}] The argument <daily_ohlcv> should be a {type(pd.DataFrame())} instead of a {type(daily_ohlcv)}!')
        return None

    if daily_ohlcv.empty:
        print(f'[-] [function:{get_volume_sma_indicators.__name__}] The value of argument <daily_ohlcv> cannot be an empty DataFrame!')
        return None

    if daily_ohlcv.index.name != 'date':
        print(f'[-] [function:{get_volume_sma_indicators.__name__}] The DataFrame <daily_ohlcv> is missing the <date> index!')
        return None

    missing_columns = {'open', 'high', 'low', 'close', 'volume'}.difference(daily_ohlcv.columns)

    if missing_columns:
        print(f'[-] [function:{get_volume_sma_indicators.__name__}] The DataFrame <daily_ohlcv> is missing the <{missing_columns}> column!')
        return None

    volume_sma_periods = VOLUME_SMA_PERIODS_DAILY

    volume_sma_indicators = dict()

    # 计算指标开始

    # 计算 Slow Volume SMA 指标
    indicator_name = 'Slow Volume SMA'
    slow_volume_sma_talib_output = abstract.SMA(daily_ohlcv, price='volume', timeperiod=volume_sma_periods['slow'])
    slow_volume_sma_df = pd.DataFrame(data={f"slow_volume_sma_{volume_sma_periods['slow']}": slow_volume_sma_talib_output.round(0).astype('UInt64')}, index=daily_ohlcv.index, dtype='UInt64')
    volume_sma_indicators[indicator_name] = slow_volume_sma_df

    # 计算 Fast Volume SMA 指标
    indicator_name = 'Fast Volume SMA'
    fast_volume_sma_talib_output = abstract.SMA(daily_ohlcv, price='volume', timeperiod=volume_sma_periods['fast'])
    fast_volume_sma_df = pd.DataFrame(data={f"fast_volume_sma_{volume_sma_periods['fast']}": fast_volume_sma_talib_output.round(0).astype('UInt64')}, index=daily_ohlcv.index, dtype='UInt64')
    volume_sma_indicators[indicator_name] = fast_volume_sma_df

    # 计算 Week Volume SMA 指标
    indicator_name = 'Week Volume SMA'
    week_volume_sma_talib_output = abstract.SMA(daily_ohlcv, price='volume', timeperiod=volume_sma_periods['week'])
    week_volume_sma_df = pd.DataFrame(data={f"week_volume_sma_{volume_sma_periods['week']}": week_volume_sma_talib_output.round(0).astype('UInt64')}, index=daily_ohlcv.index, dtype='UInt64')
    volume_sma_indicators[indicator_name] = week_volume_sma_df

    # 计算指标结束

    return volume_sma_indicators

# 计算 ATR 指标
def get_atr(daily_ohlcv: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(daily_ohlcv, pd.DataFrame):
        print(f'[-] [function:{get_atr.__name__}] The argument <daily_ohlcv> should be a {type(pd.DataFrame())} instead of a {type(daily_ohlcv)}!')
        return None

    if daily_ohlcv.empty:
        print(f'[-] [function:{get_atr.__name__}] The value of argument <daily_ohlcv> cannot be an empty DataFrame!')
        return None

    if daily_ohlcv.index.name != 'date':
        print(f'[-] [function:{get_atr.__name__}] The DataFrame <daily_ohlcv> is missing the <date> index!')
        return None

    missing_columns = {'open', 'high', 'low', 'close', 'volume'}.difference(daily_ohlcv.columns)

    if missing_columns:
        print(f'[-] [function:{get_atr.__name__}] The DataFrame <daily_ohlcv> is missing the <{missing_columns}> column!')
        return None

    # 计算 ATR 指标
    atr_talib_output = abstract.ATR(daily_ohlcv, timeperiod=ATR_PERIODS)
    atr_df = pd.DataFrame(data={f'atr_{ATR_PERIODS}': atr_talib_output}, index=daily_ohlcv.index, dtype='float64')

    return atr_df

# 构建 Keltner 通道
def get_keltner(daily_df: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_keltner.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_keltner.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_keltner.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'slow_ema', 'atr'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_keltner.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    columns = [f'{band}{atr_multiplier}_atr' for (atr_multiplier, _) in enumerate(range(3), start=1) for band in ('upper_band_p', 'lower_band_n')]

    keltner_df = pd.DataFrame(data=np.nan, index=daily_df.index, columns=columns, dtype='float64')

    for (atr_multiplier, _) in enumerate(range(3), start=1):
        keltner_df[f'upper_band_p{atr_multiplier}_atr'] = daily_df['slow_ema'].add(daily_df['atr'].mul(atr_multiplier))
        keltner_df[f'lower_band_n{atr_multiplier}_atr'] = daily_df['slow_ema'].sub(daily_df['atr'].mul(atr_multiplier))

    return keltner_df

# 计算 Pullback Entry 指标
def get_pullback_entry(daily_df: pd.DataFrame, style: str = PULLBACK_ENTRY_STYLE, atr_multiplier: dict[str, int | float] = PULLBACK_ENTRY_ATR_MULTIPLIER) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_pullback_entry.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_pullback_entry.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_pullback_entry.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'high', 'low', 'close', 'atr'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_pullback_entry.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    if not isinstance(style, str):
        print(f'[-] [function:{get_pullback_entry.__name__}] The argument <style> should be a {type(str())} instead of a {type(style)}!')
        return None

    style = style.strip().upper()

    if not style:
        print(f'[-] [function:{get_pullback_entry.__name__}] The value of argument <style> cannot be an empty string!')
        return None

    if style not in ('MAX', 'MEAN', 'MIN'):
        print(f'[-] [function:{get_pullback_entry.__name__}] The value of argument <style> is incorrect!')
        return None

    validation_atr_multiplier_errors = list()

    if not isinstance(atr_multiplier, dict):
        validation_atr_multiplier_errors.append(f'[-] [function:{get_pullback_entry.__name__}] The argument <atr_multiplier> should be a {type(dict())} instead of a {type(atr_multiplier)}!')
        return None

    if 'buyer' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_pullback_entry.__name__}] The <atr_multiplier> is missing the <buyer> key!')
    else:
        if not isinstance(atr_multiplier['buyer'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_pullback_entry.__name__}] The <atr_multiplier['buyer']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['buyer'])}!")

    if 'seller' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_pullback_entry.__name__}] The <atr_multiplier> is missing the <seller> key!')
    else:
        if not isinstance(atr_multiplier['seller'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_pullback_entry.__name__}] The <atr_multiplier['seller']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['seller'])}!")

    if (atr_multiplier['buyer'] < 0.00) or (atr_multiplier['buyer'] > 0.20):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_pullback_entry.__name__}] The value of <atr_multiplier['buyer']> is incorrect!")
    if (atr_multiplier['seller'] < 0.00) or (atr_multiplier['seller'] > 0.20):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_pullback_entry.__name__}] The value of <atr_multiplier['seller']> is incorrect!")

    if validation_atr_multiplier_errors:
        for error in validation_atr_multiplier_errors:
            print(error)
        return None

    # 计算 Typical Price 指标
    typical_price_talib_output = abstract.TYPPRICE(daily_df)

    # 计算 Weighted Close Price 指标
    weighted_close_price_talib_output = abstract.WCLPRICE(daily_df)

    price_df = pd.DataFrame(data={'typical_price': typical_price_talib_output, 'weighted_close_price': weighted_close_price_talib_output}, index=daily_df.index, dtype='float64')

    pullback_entry_df = pd.DataFrame(data={'buyer': np.nan, 'seller': np.nan}, index=daily_df.index, dtype='float64')

    if style == 'MAX':
        pullback_entry_df['buyer'] = price_df.max(axis=1).add(daily_df['atr'].mul(atr_multiplier['buyer']))
        pullback_entry_df['seller'] = price_df.min(axis=1).sub(daily_df['atr'].mul(atr_multiplier['seller']))
    elif style == 'MEAN':
        pullback_entry_df['buyer'] = price_df.mean(axis=1)
        pullback_entry_df['seller'] = price_df.mean(axis=1)
    elif style == 'MIN':
        pullback_entry_df['buyer'] = price_df.min(axis=1).sub(daily_df['atr'].mul(atr_multiplier['buyer']))
        pullback_entry_df['seller'] = price_df.max(axis=1).add(daily_df['atr'].mul(atr_multiplier['seller']))
    else:
        pass

    return pullback_entry_df

# 计算 ATR Initial Stop 指标
def get_atr_initial_stop(daily_df: pd.DataFrame, atr_multiplier: dict[str, int | float] = ATR_INITIAL_STOP_MULTIPLIER) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_atr_initial_stop.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_atr_initial_stop.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_atr_initial_stop.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'high', 'low', 'atr'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_atr_initial_stop.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    validation_atr_multiplier_errors = list()

    if not isinstance(atr_multiplier, dict):
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_initial_stop.__name__}] The argument <atr_multiplier> should be a {type(dict())} instead of a {type(atr_multiplier)}!')
        return None

    if 'buyer' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_initial_stop.__name__}] The <atr_multiplier> is missing the <buyer> key!')
    else:
        if not isinstance(atr_multiplier['buyer'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_initial_stop.__name__}] The <atr_multiplier['buyer']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['buyer'])}!")

    if 'seller' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_initial_stop.__name__}] The <atr_multiplier> is missing the <seller> key!')
    else:
        if not isinstance(atr_multiplier['seller'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_initial_stop.__name__}] The <atr_multiplier['seller']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['seller'])}!")

    if (atr_multiplier['buyer'] < 1.0) or (atr_multiplier['buyer'] > 1.5):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_initial_stop.__name__}] The value of <atr_multiplier['buyer']> is incorrect!")
    if (atr_multiplier['seller'] < 1.0) or (atr_multiplier['seller'] > 1.5):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_initial_stop.__name__}] The value of <atr_multiplier['seller']> is incorrect!")

    if validation_atr_multiplier_errors:
        for error in validation_atr_multiplier_errors:
            print(error)
        return None

    atr_initial_stop_df = pd.DataFrame(data={'buyer': np.nan, 'seller': np.nan}, index=daily_df.index, dtype='float64')

    atr_initial_stop_df['buyer'] = daily_df['low'].sub(daily_df['atr'].mul(atr_multiplier['buyer']))
    atr_initial_stop_df['seller'] = daily_df['high'].add(daily_df['atr'].mul(atr_multiplier['seller']))

    return atr_initial_stop_df

# 计算 ATR Trailing Stop 指标
def get_atr_trailing_stop(daily_df: pd.DataFrame, atr_multiplier: dict[str, int | float] = ATR_TRAILING_STOP_MULTIPLIER) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_atr_trailing_stop.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_atr_trailing_stop.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_atr_trailing_stop.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'high', 'low', 'atr'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_atr_trailing_stop.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    validation_atr_multiplier_errors = list()

    if not isinstance(atr_multiplier, dict):
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_trailing_stop.__name__}] The argument <atr_multiplier> should be a {type(dict())} instead of a {type(atr_multiplier)}!')
        return None

    if 'buyer' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_trailing_stop.__name__}] The <atr_multiplier> is missing the <buyer> key!')
    else:
        if not isinstance(atr_multiplier['buyer'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_trailing_stop.__name__}] The <atr_multiplier['buyer']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['buyer'])}!")

    if 'seller' not in atr_multiplier:
        validation_atr_multiplier_errors.append(f'[-] [function:{get_atr_trailing_stop.__name__}] The <atr_multiplier> is missing the <seller> key!')
    else:
        if not isinstance(atr_multiplier['seller'], (int, float)):
            validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_trailing_stop.__name__}] The <atr_multiplier['seller']> should be a {type(int())} or {type(float())} instead of a {type(atr_multiplier['seller'])}!")

    if (atr_multiplier['buyer'] < 1.5) or (atr_multiplier['buyer'] > 2.0):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_trailing_stop.__name__}] The value of <atr_multiplier['buyer']> is incorrect!")
    if (atr_multiplier['seller'] < 1.5) or (atr_multiplier['seller'] > 2.0):
        validation_atr_multiplier_errors.append(f"[-] [function:{get_atr_trailing_stop.__name__}] The value of <atr_multiplier['seller']> is incorrect!")

    if validation_atr_multiplier_errors:
        for error in validation_atr_multiplier_errors:
            print(error)
        return None

    atr_trailing_stop_df = pd.DataFrame(data={'buyer': np.nan, 'seller': np.nan}, index=daily_df.index, dtype='float64')

    atr_trailing_stop_df['buyer'] = daily_df['low'].sub(daily_df['atr'].mul(atr_multiplier['buyer']))
    atr_trailing_stop_df['seller'] = daily_df['high'].add(daily_df['atr'].mul(atr_multiplier['seller']))

    return atr_trailing_stop_df

# 计算 Keltner Target 指标
def get_keltner_target(daily_df: pd.DataFrame, breakout_pct: dict[str, int | float] = KELTNER_TARGET_BREAKOUT_PCT) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_keltner_target.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_keltner_target.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_keltner_target.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'slow_ema', 'atr'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_keltner_target.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    validation_breakout_pct_errors = list()

    if not isinstance(breakout_pct, dict):
        validation_breakout_pct_errors.append(f'[-] [function:{get_keltner_target.__name__}] The argument <breakout_pct> should be a {type(dict())} instead of a {type(breakout_pct)}!')
        return None

    if 'buyer' not in breakout_pct:
        validation_breakout_pct_errors.append(f'[-] [function:{get_keltner_target.__name__}] The <breakout_pct> is missing the <buyer> key!')
    else:
        if not isinstance(breakout_pct['buyer'], (int, float)):
            validation_breakout_pct_errors.append(f"[-] [function:{get_keltner_target.__name__}] The <breakout_pct['buyer']> should be a {type(int())} or {type(float())} instead of a {type(breakout_pct['buyer'])}!")

    if 'seller' not in breakout_pct:
        validation_breakout_pct_errors.append(f'[-] [function:{get_keltner_target.__name__}] The <breakout_pct> is missing the <seller> key!')
    else:
        if not isinstance(breakout_pct['seller'], (int, float)):
            validation_breakout_pct_errors.append(f"[-] [function:{get_keltner_target.__name__}] The <breakout_pct['seller']> should be a {type(int())} or {type(float())} instead of a {type(breakout_pct['seller'])}!")

    if (breakout_pct['buyer'] < 0.00) or (breakout_pct['buyer'] > 0.05):
        validation_breakout_pct_errors.append(f"[-] [function:{get_keltner_target.__name__}] The value of <breakout_pct['buyer']> is incorrect!")
    if (breakout_pct['seller'] < 0.00) or (breakout_pct['seller'] > 0.05):
        validation_breakout_pct_errors.append(f"[-] [function:{get_keltner_target.__name__}] The value of <breakout_pct['seller']> is incorrect!")

    if validation_breakout_pct_errors:
        for error in validation_breakout_pct_errors:
            print(error)
        return None

    atr_multiplier = 3.0

    keltner_target_df = pd.DataFrame(data={'buyer': np.nan, 'seller': np.nan}, index=daily_df.index, dtype='float64')

    keltner_target_df['buyer'] = daily_df['slow_ema'].add(daily_df['atr'].mul(atr_multiplier)).mul(1.00 + breakout_pct['buyer'])
    keltner_target_df['seller'] = daily_df['slow_ema'].sub(daily_df['atr'].mul(atr_multiplier)).mul(1.00 - breakout_pct['seller'])

    return keltner_target_df

# 计算 Breakeven 指标
def get_breakeven(daily_df: pd.DataFrame, open_profit_pct: dict[str, float] = BREAKEVEN_OPEN_PROFIT_PCT, tick: float = 0.01) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_breakeven.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_breakeven.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_breakeven.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'pullback_entry_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'keltner_target_seller'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_breakeven.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    validation_open_profit_pct_errors = list()

    if not isinstance(open_profit_pct, dict):
        validation_open_profit_pct_errors.append(f'[-] [function:{get_breakeven.__name__}] The argument <open_profit_pct> should be a {type(dict())} instead of a {type(open_profit_pct)}!')
        return None

    if 'buyer' not in open_profit_pct:
        validation_open_profit_pct_errors.append(f'[-] [function:{get_breakeven.__name__}] The <open_profit_pct> is missing the <buyer> key!')
    else:
        if not isinstance(open_profit_pct['buyer'], float):
            validation_open_profit_pct_errors.append(f"[-] [function:{get_breakeven.__name__}] The <open_profit_pct['buyer']> should be a {type(float())} instead of a {type(open_profit_pct['buyer'])}!")

    if 'seller' not in open_profit_pct:
        validation_open_profit_pct_errors.append(f'[-] [function:{get_breakeven.__name__}] The <open_profit_pct> is missing the <seller> key!')
    else:
        if not isinstance(open_profit_pct['seller'], float):
            validation_open_profit_pct_errors.append(f"[-] [function:{get_breakeven.__name__}] The <open_profit_pct['seller']> should be a {type(float())} instead of a {type(open_profit_pct['seller'])}!")

    if (open_profit_pct['buyer'] < 0.30) or (open_profit_pct['buyer'] > 0.33):
        validation_open_profit_pct_errors.append(f"[-] [function:{get_breakeven.__name__}] The value of <open_profit_pct['buyer']> is incorrect!")
    if (open_profit_pct['seller'] < 0.30) or (open_profit_pct['seller'] > 0.33):
        validation_open_profit_pct_errors.append(f"[-] [function:{get_breakeven.__name__}] The value of <open_profit_pct['seller']> is incorrect!")

    if validation_open_profit_pct_errors:
        for error in validation_open_profit_pct_errors:
            print(error)
        return None

    if not isinstance(tick, float):
        print(f'[-] [function:{get_breakeven.__name__}] The argument <tick> should be a {type(float())} instead of a {type(tick)}!')
        return None

    if tick not in (0.01, 0.001):
        print(f'[-] [function:{get_breakeven.__name__}] The value of argument <tick> is incorrect!')
        return None

    breakeven_df = pd.DataFrame(data={'price_buyer': np.nan, 'stop_buyer': np.nan, 'price_seller': np.nan, 'stop_seller': np.nan}, index=daily_df.index, dtype='float64')

    breakeven_df['price_buyer'] = daily_df['pullback_entry_buyer'].add(daily_df['keltner_target_buyer'].sub(daily_df['pullback_entry_buyer']).mul(open_profit_pct['buyer']))
    breakeven_df['stop_buyer'] = daily_df['pullback_entry_buyer'].add(tick * 16)

    breakeven_df['price_seller'] = daily_df['pullback_entry_seller'].sub(daily_df['pullback_entry_seller'].sub(daily_df['keltner_target_seller']).mul(open_profit_pct['seller']))
    breakeven_df['stop_seller'] = daily_df['pullback_entry_seller'].sub(tick * 16)

    return breakeven_df

# 计算 Protect Profit 指标
def get_protect_profit(daily_df: pd.DataFrame, open_profit_pct: dict[str, float] = BREAKEVEN_OPEN_PROFIT_PCT, tick: float = 0.01) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_protect_profit.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_protect_profit.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_protect_profit.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'pullback_entry_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'keltner_target_seller'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_protect_profit.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    validation_open_profit_pct_errors = list()

    if not isinstance(open_profit_pct, dict):
        validation_open_profit_pct_errors.append(f'[-] [function:{get_protect_profit.__name__}] The argument <open_profit_pct> should be a {type(dict())} instead of a {type(open_profit_pct)}!')
        return None

    if 'buyer' not in open_profit_pct:
        validation_open_profit_pct_errors.append(f'[-] [function:{get_protect_profit.__name__}] The <open_profit_pct> is missing the <buyer> key!')
    else:
        if not isinstance(open_profit_pct['buyer'], float):
            validation_open_profit_pct_errors.append(f"[-] [function:{get_protect_profit.__name__}] The <open_profit_pct['buyer']> should be a {type(float())} instead of a {type(open_profit_pct['buyer'])}!")

    if 'seller' not in open_profit_pct:
        validation_open_profit_pct_errors.append(f'[-] [function:{get_protect_profit.__name__}] The <open_profit_pct> is missing the <seller> key!')
    else:
        if not isinstance(open_profit_pct['seller'], float):
            validation_open_profit_pct_errors.append(f"[-] [function:{get_protect_profit.__name__}] The <open_profit_pct['seller']> should be a {type(float())} instead of a {type(open_profit_pct['seller'])}!")

    if (open_profit_pct['buyer'] < 0.25) or (open_profit_pct['buyer'] > 0.32):
        validation_open_profit_pct_errors.append(f"[-] [function:{get_protect_profit.__name__}] The value of <open_profit_pct['buyer']> is incorrect!")
    if (open_profit_pct['seller'] < 0.25) or (open_profit_pct['seller'] > 0.32):
        validation_open_profit_pct_errors.append(f"[-] [function:{get_protect_profit.__name__}] The value of <open_profit_pct['seller']> is incorrect!")

    if validation_open_profit_pct_errors:
        for error in validation_open_profit_pct_errors:
            print(error)
        return None

    if not isinstance(tick, float):
        print(f'[-] [function:{get_protect_profit.__name__}] The argument <tick> should be a {type(float())} instead of a {type(tick)}!')
        return None

    if tick not in (0.01, 0.001):
        print(f'[-] [function:{get_protect_profit.__name__}] The value of argument <tick> is incorrect!')
        return None

    protect_profit_df = pd.DataFrame(data={'price_buyer': np.nan, 'stop_buyer': np.nan, 'price_seller': np.nan, 'stop_seller': np.nan}, index=daily_df.index, dtype='float64')

    protect_profit_df['price_buyer'] = daily_df['pullback_entry_buyer'].add(daily_df['keltner_target_buyer'].sub(daily_df['pullback_entry_buyer']).mul(open_profit_pct['buyer'] * 2))
    protect_profit_df['stop_buyer'] = daily_df['pullback_entry_buyer'].add(daily_df['keltner_target_buyer'].sub(daily_df['pullback_entry_buyer']).mul(open_profit_pct['buyer'])).add(tick * 16)

    protect_profit_df['price_seller'] = daily_df['pullback_entry_seller'].sub(daily_df['pullback_entry_seller'].sub(daily_df['keltner_target_seller']).mul(open_profit_pct['seller'] * 2))
    protect_profit_df['stop_seller'] = daily_df['pullback_entry_seller'].sub(daily_df['pullback_entry_seller'].sub(daily_df['keltner_target_seller']).mul(open_profit_pct['seller'])).sub(tick * 16)

    return protect_profit_df

# 计算 Reward Risk Ratio 指标
def get_reward_risk_ratio(daily_df: pd.DataFrame) -> pd.DataFrame | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_reward_risk_ratio.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_reward_risk_ratio.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_reward_risk_ratio.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    missing_columns = {'pullback_entry_buyer', 'atr_initial_stop_buyer', 'keltner_target_buyer', 'pullback_entry_seller', 'atr_initial_stop_seller', 'keltner_target_seller'}.difference(daily_df.columns)

    if missing_columns:
        print(f'[-] [function:{get_reward_risk_ratio.__name__}] The DataFrame <daily_df> is missing the <{missing_columns}> column!')
        return None

    reward_risk_ratio_df = pd.DataFrame(data={'buyer': np.nan, 'seller': np.nan}, index=daily_df.index, dtype='float64')

    reward_risk_ratio_df['buyer'] = daily_df['keltner_target_buyer'].sub(daily_df['pullback_entry_buyer']).div(daily_df['pullback_entry_buyer'].sub(daily_df['atr_initial_stop_buyer']))
    reward_risk_ratio_df['seller'] = daily_df['pullback_entry_seller'].sub(daily_df['keltner_target_seller']).div(daily_df['atr_initial_stop_seller'].sub(daily_df['pullback_entry_seller']))

    return reward_risk_ratio_df

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
