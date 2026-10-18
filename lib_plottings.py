#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import _conf
import lib_indicators
import lib_strategies
import pandas as pd
import plotly.graph_objects as go
import sys

from plotly.subplots import make_subplots

GLOBAL_PRECISION = _conf.PRECISION

try:
    GLOBAL_PRECISION = int(GLOBAL_PRECISION)
except (TypeError, ValueError) as e:
    GLOBAL_PRECISION = 2
else:
    if GLOBAL_PRECISION <= 1:
        GLOBAL_PRECISION = 2

# 定义 Elder Paint Bar 映射
elder_paint_bar = {
    'up': 'lime',
    'down': 'red',
    'neutral': 'cyan',
    'bullish': 'lime',
    'bearish': 'red',
    'no_trades': 'gray',
}

def main() -> None:
    print('[!] This is a library.')

# 绘制周频分析图表
def get_weekly_analysis_figure(weekly_df: pd.DataFrame, symbol: str, name: str, market: str) -> go.Figure | None:
    if not isinstance(weekly_df, pd.DataFrame):
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The argument <weekly_df> should be a {type(pd.DataFrame())} instead of a {type(weekly_df)}!')
        return None

    if weekly_df.empty:
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The value of argument <weekly_df> cannot be an empty DataFrame!')
        return None

    if weekly_df.index.name != 'date':
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The DataFrame <weekly_df> is missing the <date> index!')
        return None

    if not isinstance(symbol, str):
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The argument <symbol> should be a {type(str())} instead of a {type(symbol)}!')
        return None
    symbol = symbol.strip().upper()
    if not symbol:
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The value of argument <symbol> cannot be an empty string!')
        return None

    if not isinstance(name, str):
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The argument <name> should be a {type(str())} instead of a {type(name)}!')
        return None
    name = name.strip().upper()
    if not name:
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The value of argument <name> cannot be an empty string!')
        return None

    if not isinstance(market, str):
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The argument <market> should be a {type(str())} instead of a {type(market)}!')
        return None
    market = market.strip().upper()
    if not market:
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The value of argument <market> cannot be an empty string!')
        return None
    if market not in ('A', 'AF', 'HK', 'US'):
        print(f'[-] [function:{get_weekly_analysis_figure.__name__}] The value of argument <market> is incorrect!')
        return None

    precision = GLOBAL_PRECISION
    if (market == 'AF') and (precision < 3):
        precision = 3

    # 绘制最近三年的周频数据
    weekly_df = weekly_df.dropna().tail(156)
    missing_dates = pd.date_range(start=weekly_df.index.min(), end=weekly_df.index.max(), freq='D', inclusive='both').difference(weekly_df.index, sort=True)

    # 定义图表布局
    weekly_analysis_figure = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.075,
        subplot_titles=(
            f"Open: {weekly_df['open'].iloc[-1]:.{precision}f} | High: {weekly_df['high'].iloc[-1]:.{precision}f} | Low: {weekly_df['low'].iloc[-1]:.{precision}f} | Close: {weekly_df['close'].iloc[-1]:.{precision}f} | Fast EMA ({lib_indicators.EMA_PARAMS_W['fast']}): {weekly_df['fast_ema'].iloc[-1]:.{precision}f} | Slow EMA ({lib_indicators.EMA_PARAMS_W['slow']}): {weekly_df['slow_ema'].iloc[-1]:.{precision}f} | Impulse: {weekly_df['elder_impulse'].iloc[-1].capitalize()}",
            f"MACD ({lib_indicators.MACD_PARAMS['fast']}, {lib_indicators.MACD_PARAMS['slow']}, {lib_indicators.MACD_PARAMS['signal']}) | Histogram: {weekly_df['MACD_histogram'].iloc[-1]:.{precision}f} | MACD aka DIF: {weekly_df['MACD_macd'].iloc[-1]:.{precision}f} | Signal aka DEA: {weekly_df['MACD_signal'].iloc[-1]:.{precision}f}",
            f"RSI ({lib_indicators.RSI_PERIODS_W}): {weekly_df['rsi'].iloc[-1]:.{precision}f} | EFI ({lib_indicators.EFI_PERIODS_W}): {weekly_df['efi'].iloc[-1]:.{precision}f}",
            f"Vol: {weekly_df['volume'].iloc[-1]} | Vol SMA ({lib_indicators.QUARTER_VOLUME_SMA_PERIODS_W}): {weekly_df['quarter_volume_sma'].iloc[-1]}",
        ),
        specs=[[{}], [{}], [{'secondary_y': True}], [{}]],
        row_heights=(0.52, 0.22, 0.10, 0.16),
    )

    # 绘制 Candlestick 子图
    elder_impulse_groups = weekly_df.groupby('elder_impulse')
    for (elder_impulse, group_df) in elder_impulse_groups:
        weekly_analysis_figure.add_candlestick(
            row=1, col=1,
            x=group_df.index,
            open=group_df['open'],
            high=group_df['high'],
            low=group_df['low'],
            close=group_df['close'],
            name=elder_impulse.capitalize(),
            hoverinfo='x+y+z',
            line_width=1,
            increasing_fillcolor='rgba(0, 0, 0, 0)',
            increasing_line_color=elder_paint_bar[elder_impulse],
            decreasing_fillcolor=elder_paint_bar[elder_impulse],
            decreasing_line_color=elder_paint_bar[elder_impulse],
        )

    # 添加 Fast EMA 参考线
    weekly_analysis_figure.add_scatter(
        row=1, col=1,
        x=weekly_df.index,
        y=weekly_df['fast_ema'],
        name=f"Fast EMA ({lib_indicators.EMA_PARAMS_W['fast']})",
        mode='lines',
        line_color='red',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Slow EMA 参考线
    weekly_analysis_figure.add_scatter(
        row=1, col=1,
        x=weekly_df.index,
        y=weekly_df['slow_ema'],
        name=f"Slow EMA ({lib_indicators.EMA_PARAMS_W['slow']})",
        mode='lines',
        line_color='yellow',
        line_dash='solid',
        line_width=1,
    )

    # 绘制 MACD 子图
    macd_histogram_direction_groups = weekly_df.groupby('MACD_histogram_direction')
    for (macd_histogram_direction, group_df) in macd_histogram_direction_groups:
        weekly_analysis_figure.add_bar(
            row=2, col=1,
            x=group_df.index,
            y=group_df['MACD_histogram'],
            name=macd_histogram_direction.capitalize(),
            marker_color=elder_paint_bar[macd_histogram_direction],
        )

    # 添加 MACD aka DIF 参考线
    weekly_analysis_figure.add_scatter(
        row=2, col=1,
        x=weekly_df.index,
        y=weekly_df['MACD_macd'],
        name='MACD aka DIF',
        mode='lines',
        line_color='red',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Signal aka DEA 参考线
    weekly_analysis_figure.add_scatter(
        row=2, col=1,
        x=weekly_df.index,
        y=weekly_df['MACD_signal'],
        name='Signal aka DEA',
        mode='lines',
        line_color='lime',
        line_dash='solid',
        line_width=1,
    )

    # 绘制 RSI 和 EFI 子图

    # 添加 RSI 参考线
    weekly_analysis_figure.add_scatter(
        row=3, col=1,
        x=weekly_df.index,
        y=weekly_df['rsi'],
        name=f'RSI ({lib_indicators.RSI_PERIODS_W})',
        legendgroup='RSI',
        mode='lines',
        line_color='lime',
        line_dash='solid',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Oversold 参考线
    weekly_analysis_figure.add_hline(
        row=3, col=1,
        y=lib_strategies.RSI_LEVEL['oversold'],
        name='RSI Oversold',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Median 参考线
    weekly_analysis_figure.add_hline(
        row=3, col=1,
        y=50,
        name='RSI Median',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dashdot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Overbought 参考线
    weekly_analysis_figure.add_hline(
        row=3, col=1,
        y=lib_strategies.RSI_LEVEL['overbought'],
        name='RSI Overbought',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 EFI 参考线
    weekly_analysis_figure.add_scatter(
        row=3, col=1,
        x=weekly_df.index,
        y=weekly_df['efi'],
        name=f'EFI ({lib_indicators.EFI_PERIODS_W})',
        legendgroup='EFI',
        mode='lines',
        line_color='cyan',
        line_dash='solid',
        line_width=1,
        secondary_y=True,
    )

    # 添加 EFI Zero 参考线
    weekly_analysis_figure.add_hline(
        row=3, col=1,
        y=0,
        name='EFI Zero',
        legendgroup='EFI',
        showlegend=False,
        line_color='silver',
        line_dash='solid',
        line_width=1,
        secondary_y=True,
    )

    # 绘制 Volume 子图
    volume_direction_groups = weekly_df.groupby('volume_direction')
    for (volume_direction, group_df) in volume_direction_groups:
        weekly_analysis_figure.add_bar(
            row=4, col=1,
            x=group_df.index,
            y=group_df['volume'],
            name=volume_direction.capitalize(),
            marker_color=elder_paint_bar[volume_direction],
        )

    # 添加 Quarter Volume SMA 参考线
    weekly_analysis_figure.add_scatter(
        row=4, col=1,
        x=weekly_df.index,
        y=weekly_df['quarter_volume_sma'],
        name=f'Quarter Volume SMA ({lib_indicators.QUARTER_VOLUME_SMA_PERIODS_W})',
        mode='lines',
        line_color='orange',
        line_dash='solid',
        line_width=1,
    )

    # 配置 X 轴属性
    weekly_analysis_figure.update_xaxes(
        type='date',
        dtick='M3',
        hoverformat='%Y/%m/%d, %a',
        rangebreaks=[dict(dvalue=int(86400000 / 7), values=missing_dates)],
        rangeslider_visible=False,
        tickformat='%b %Y',
        showgrid=False,
        zeroline=False,
    )

    # 配置 Y 轴属性
    weekly_analysis_figure.update_yaxes(
        type='linear',
        hoverformat=f'.{precision}f',
        tickformat=f'.{precision}f',
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    weekly_analysis_figure.update_yaxes(
        row=4, col=1,
        hoverformat='d',
        tickformat='d',
    )

    # 配置图表 Annotations 属性
    weekly_analysis_figure.update_annotations(
        x=0,
        xanchor='left',
        xref='paper',
    )

    # 配置图表布局属性
    weekly_analysis_figure.update_layout(
        title_text=f'{market}    {symbol}    {name}  -  Weekly',

        title_x=0,
        title_xanchor='left',
        title_xref='paper',

        title_y=1,
        title_yanchor='top',
        title_yref='container',

        title_pad_t=15,
        margin_t=60,

        margin_b=45,
        margin_l=40,

        hovermode='x unified',
        hoverlabel_namelength=-1,
        template='plotly_dark',
    )

    return weekly_analysis_figure

# 绘制日频分析图表
def get_daily_analysis_figure(daily_df: pd.DataFrame, symbol: str, name: str, market: str) -> go.Figure | None:
    if not isinstance(daily_df, pd.DataFrame):
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The argument <daily_df> should be a {type(pd.DataFrame())} instead of a {type(daily_df)}!')
        return None

    if daily_df.empty:
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The value of argument <daily_df> cannot be an empty DataFrame!')
        return None

    if daily_df.index.name != 'date':
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The DataFrame <daily_df> is missing the <date> index!')
        return None

    if not isinstance(symbol, str):
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The argument <symbol> should be a {type(str())} instead of a {type(symbol)}!')
        return None
    symbol = symbol.strip().upper()
    if not symbol:
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The value of argument <symbol> cannot be an empty string!')
        return None

    if not isinstance(name, str):
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The argument <name> should be a {type(str())} instead of a {type(name)}!')
        return None
    name = name.strip().upper()
    if not name:
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The value of argument <name> cannot be an empty string!')
        return None

    if not isinstance(market, str):
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The argument <market> should be a {type(str())} instead of a {type(market)}!')
        return None
    market = market.strip().upper()
    if not market:
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The value of argument <market> cannot be an empty string!')
        return None
    if market not in ('A', 'AF', 'HK', 'US'):
        print(f'[-] [function:{get_daily_analysis_figure.__name__}] The value of argument <market> is incorrect!')
        return None

    precision = GLOBAL_PRECISION
    if (market == 'AF') and (precision < 3):
        precision = 3

    # 绘制最近八个月的日频数据
    daily_df = daily_df.dropna().tail(168)
    missing_dates = pd.date_range(start=daily_df.index.min(), end=daily_df.index.max(), freq='D', inclusive='both').difference(daily_df.index, sort=True)

    # 定义图表布局
    daily_analysis_figure = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.060,
        subplot_titles=(
            f"Open: {daily_df['open'].iloc[-1]:.{precision}f} | High: {daily_df['high'].iloc[-1]:.{precision}f} | Low: {daily_df['low'].iloc[-1]:.{precision}f} | Close: {daily_df['close'].iloc[-1]:.{precision}f} | Fast EMA ({lib_indicators.EMA_PARAMS_D['fast']}): {daily_df['fast_ema'].iloc[-1]:.{precision}f} | Slow EMA ({lib_indicators.EMA_PARAMS_D['slow']}): {daily_df['slow_ema'].iloc[-1]:.{precision}f} | Impulse: {daily_df['elder_impulse'].iloc[-1].capitalize()}",
            f"ImpulseRelease: {daily_df['elder_impulse_release'].iloc[-1].title().replace('_', ' ')}",
            f"MACD ({lib_indicators.MACD_PARAMS['fast']}, {lib_indicators.MACD_PARAMS['slow']}, {lib_indicators.MACD_PARAMS['signal']}) | Histogram: {daily_df['MACD_histogram'].iloc[-1]:.{precision}f} | MACD aka DIF: {daily_df['MACD_macd'].iloc[-1]:.{precision}f} | Signal aka DEA: {daily_df['MACD_signal'].iloc[-1]:.{precision}f}",
            f"RSI ({lib_indicators.RSI_PERIODS_D}): {daily_df['rsi'].iloc[-1]:.{precision}f} | EFI ({lib_indicators.EFI_PERIODS_D}): {daily_df['efi'].iloc[-1]:.{precision}f}",
            f"Vol: {daily_df['volume'].iloc[-1]} | Vol SMA ({lib_indicators.QUARTER_VOLUME_SMA_PERIODS_D}): {daily_df['quarter_volume_sma'].iloc[-1]} | Vol SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['slow']}): {daily_df['slow_volume_sma'].iloc[-1]} | Vol SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['fast']}): {daily_df['fast_volume_sma'].iloc[-1]} | Vol SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['week']}): {daily_df['week_volume_sma'].iloc[-1]}",
        ),
        specs=[[{'secondary_y': True}], [{}], [{}], [{'secondary_y': True}], [{}]],
        row_heights=(0.52, 0.01, 0.21, 0.10, 0.16),
    )

    # 绘制 Candlestick 子图
    elder_impulse_groups = daily_df.groupby('elder_impulse')
    for (elder_impulse, group_df) in elder_impulse_groups:
        daily_analysis_figure.add_candlestick(
            row=1, col=1,
            x=group_df.index,
            open=group_df['open'],
            high=group_df['high'],
            low=group_df['low'],
            close=group_df['close'],
            name=elder_impulse.capitalize(),
            hoverinfo='x+y+z',
            line_width=1,
            increasing_fillcolor='rgba(0, 0, 0, 0)',
            increasing_line_color=elder_paint_bar[elder_impulse],
            decreasing_fillcolor=elder_paint_bar[elder_impulse],
            decreasing_line_color=elder_paint_bar[elder_impulse],
            secondary_y=False,
        )

    # 添加 Fast EMA 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['fast_ema'],
        name=f"Fast EMA ({lib_indicators.EMA_PARAMS_D['fast']})",
        mode='lines',
        line_color='red',
        line_dash='solid',
        line_width=1,
        secondary_y=False,
    )

    # 添加 Slow EMA 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['slow_ema'],
        name=f"Slow EMA ({lib_indicators.EMA_PARAMS_D['slow']})",
        mode='lines',
        line_color='yellow',
        line_dash='solid',
        line_width=1,
        secondary_y=False,
    )

    # 添加 ATR 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['atr'],
        name=f'ATR ({lib_indicators.ATR_PERIODS})',
        mode='none',
        secondary_y=True,
    )

    # 添加 Keltner 通道线
    for (atr_multiplier, dash_style) in enumerate(('dot', 'dashdot', 'solid'), start=1):
        daily_analysis_figure.add_scatter(
            row=1, col=1,
            x=daily_df.index,
            y=daily_df[f'keltner_upper_band_p{atr_multiplier}_atr'],
            name=f'Keltner Upper Band P{atr_multiplier} ATR',
            legendgroup=f'keltner_band_{atr_multiplier}_atr',
            mode='lines',
            line_color='silver',
            line_dash=dash_style,
            line_width=1,
            secondary_y=False,
        )

        daily_analysis_figure.add_scatter(
            row=1, col=1,
            x=daily_df.index,
            y=daily_df[f'keltner_lower_band_n{atr_multiplier}_atr'],
            name=f'Keltner Lower Band N{atr_multiplier} ATR',
            legendgroup=f'keltner_band_{atr_multiplier}_atr',
            mode='lines',
            line_color='silver',
            line_dash=dash_style,
            line_width=1,
            secondary_y=False,
        )

    # 添加 Buyer 参考价位

    # 添加 Entry Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['pullback_entry_buyer'],
        name='Entry [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Initial Stop Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['atr_initial_stop_buyer'],
        name='Initial Stop [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Trailing Stop Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['atr_trailing_stop_buyer'],
        name='Trailing Stop [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Breakeven Price Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['breakeven_price_buyer'],
        name='Breakeven Price [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Breakeven Stop Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['breakeven_stop_buyer'],
        name='Breakeven Stop [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Protect Profit Price Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['protect_profit_price_buyer'],
        name='Protect Profit Price [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Protect Profit Stop Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['protect_profit_stop_buyer'],
        name='Protect Profit Stop [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Profit Target Buyer 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['keltner_target_buyer'],
        name='Profit Target [B]',
        legendgroup='Buyer Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Seller 参考价位

    # 添加 Entry Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['pullback_entry_seller'],
        name='Entry [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Initial Stop Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['atr_initial_stop_seller'],
        name='Initial Stop [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Trailing Stop Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['atr_trailing_stop_seller'],
        name='Trailing Stop [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Breakeven Price Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['breakeven_price_seller'],
        name='Breakeven Price [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Breakeven Stop Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['breakeven_stop_seller'],
        name='Breakeven Stop [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Protect Profit Price Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['protect_profit_price_seller'],
        name='Protect Profit Price [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Protect Profit Stop Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['protect_profit_stop_seller'],
        name='Protect Profit Stop [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 添加 Profit Target Seller 参考线
    daily_analysis_figure.add_scatter(
        row=1, col=1,
        x=daily_df.index,
        y=daily_df['keltner_target_seller'],
        name='Profit Target [S]',
        legendgroup='Seller Prices',
        mode='none',
        secondary_y=False,
    )

    # 绘制 Elder Impulse Release 子图
    elder_impulse_release_groups = daily_df.groupby('elder_impulse_release')
    for (elder_impulse_release, group_df) in elder_impulse_release_groups:
        daily_analysis_figure.add_bar(
            row=2, col=1,
            x=group_df.index,
            y=[1 for _ in range(len(group_df))],
            name=elder_impulse_release.title().replace('_', ' '),
            yhoverformat='d',
            marker_color=elder_paint_bar[elder_impulse_release],
        )

    # 绘制 MACD 子图
    macd_histogram_direction_groups = daily_df.groupby('MACD_histogram_direction')
    for (macd_histogram_direction, group_df) in macd_histogram_direction_groups:
        daily_analysis_figure.add_bar(
            row=3, col=1,
            x=group_df.index,
            y=group_df['MACD_histogram'],
            name=macd_histogram_direction.capitalize(),
            marker_color='rgba(0, 0, 0, 0)',
            marker_line_color=elder_paint_bar[macd_histogram_direction],
        )

    # 添加 MACD aka DIF 参考线
    daily_analysis_figure.add_scatter(
        row=3, col=1,
        x=daily_df.index,
        y=daily_df['MACD_macd'],
        name='MACD aka DIF',
        mode='lines',
        line_color='red',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Signal aka DEA 参考线
    daily_analysis_figure.add_scatter(
        row=3, col=1,
        x=daily_df.index,
        y=daily_df['MACD_signal'],
        name='Signal aka DEA',
        mode='lines',
        line_color='lime',
        line_dash='solid',
        line_width=1,
    )

    # 绘制 RSI 和 EFI 子图

    # 添加 RSI 参考线
    daily_analysis_figure.add_scatter(
        row=4, col=1,
        x=daily_df.index,
        y=daily_df['rsi'],
        name=f'RSI ({lib_indicators.RSI_PERIODS_D})',
        legendgroup='RSI',
        mode='lines',
        line_color='lime',
        line_dash='solid',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Oversold 参考线
    daily_analysis_figure.add_hline(
        row=4, col=1,
        y=lib_strategies.RSI_LEVEL['oversold'],
        name='RSI Oversold',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Median 参考线
    daily_analysis_figure.add_hline(
        row=4, col=1,
        y=50,
        name='RSI Median',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dashdot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 RSI Overbought 参考线
    daily_analysis_figure.add_hline(
        row=4, col=1,
        y=lib_strategies.RSI_LEVEL['overbought'],
        name='RSI Overbought',
        legendgroup='RSI',
        showlegend=False,
        line_color='silver',
        line_dash='dot',
        line_width=1,
        secondary_y=False,
    )

    # 添加 EFI 参考线
    daily_analysis_figure.add_scatter(
        row=4, col=1,
        x=daily_df.index,
        y=daily_df['efi'],
        name=f'EFI ({lib_indicators.EFI_PERIODS_D})',
        legendgroup='EFI',
        mode='lines',
        line_color='cyan',
        line_dash='solid',
        line_width=1,
        secondary_y=True,
    )

    # 添加 EFI Zero 参考线
    daily_analysis_figure.add_hline(
        row=4, col=1,
        y=0,
        name='EFI Zero',
        legendgroup='EFI',
        showlegend=False,
        line_color='silver',
        line_dash='solid',
        line_width=1,
        secondary_y=True,
    )

    # 绘制 Volume 子图
    volume_direction_groups = daily_df.groupby('volume_direction')
    for (volume_direction, group_df) in volume_direction_groups:
        daily_analysis_figure.add_bar(
            row=5, col=1,
            x=group_df.index,
            y=group_df['volume'],
            name=volume_direction.capitalize(),
            marker_color='rgba(0, 0, 0, 0)',
            marker_line_color=elder_paint_bar[volume_direction],
        )

    # 添加 Quarter Volume SMA 参考线
    daily_analysis_figure.add_scatter(
        row=5, col=1,
        x=daily_df.index,
        y=daily_df['quarter_volume_sma'],
        name=f'Quarter Volume SMA ({lib_indicators.QUARTER_VOLUME_SMA_PERIODS_D})',
        mode='lines',
        line_color='orange',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Slow Volume SMA 参考线
    daily_analysis_figure.add_scatter(
        row=5, col=1,
        x=daily_df.index,
        y=daily_df['slow_volume_sma'],
        name=f"Slow Volume SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['slow']})",
        mode='lines',
        line_color='yellow',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Fast Volume SMA 参考线
    daily_analysis_figure.add_scatter(
        row=5, col=1,
        x=daily_df.index,
        y=daily_df['fast_volume_sma'],
        name=f"Fast Volume SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['fast']})",
        mode='lines',
        line_color='red',
        line_dash='solid',
        line_width=1,
    )

    # 添加 Week Volume SMA 参考线
    daily_analysis_figure.add_scatter(
        row=5, col=1,
        x=daily_df.index,
        y=daily_df['week_volume_sma'],
        name=f"Week Volume SMA ({lib_indicators.VOLUME_SMA_PERIODS_DAILY['week']})",
        mode='lines',
        line_color='lime',
        line_dash='solid',
        line_width=1,
    )

    # 配置 X 轴属性
    daily_analysis_figure.update_xaxes(
        type='date',
        dtick='M1',
        hoverformat='%Y/%m/%d, %a',
        rangebreaks=[dict(dvalue=int(86400000 / 1), values=missing_dates)],
        rangeslider_visible=False,
        tickformat='%b %Y',
        showgrid=False,
        zeroline=False,
    )

    # 配置 Y 轴属性
    daily_analysis_figure.update_yaxes(
        type='linear',
        hoverformat=f'.{precision}f',
        tickformat=f'.{precision}f',
        showticklabels=False,
        showgrid=False,
        zeroline=False,
    )

    daily_analysis_figure.update_yaxes(
        row=5, col=1,
        hoverformat='d',
        tickformat='d',
    )

    # 配置图表 Annotations 属性
    daily_analysis_figure.update_annotations(
        x=0,
        xanchor='left',
        xref='paper',
    )

    # 配置图表布局属性
    buyer_prices = f"Entry [B]: {daily_df['pullback_entry_buyer'].iloc[-1]:.{precision}f} | Initial Stop [B]: {daily_df['atr_initial_stop_buyer'].iloc[-1]:.{precision}f} | Trailing Stop [B]: {daily_df['atr_trailing_stop_buyer'].iloc[-1]:.{precision}f} | Breakeven [B]: ({daily_df['breakeven_price_buyer'].iloc[-1]:.{precision}f} | {daily_df['breakeven_stop_buyer'].iloc[-1]:.{precision}f}) | Protect Profit [B]: ({daily_df['protect_profit_price_buyer'].iloc[-1]:.{precision}f} | {daily_df['protect_profit_stop_buyer'].iloc[-1]:.{precision}f}) | Profit Target [B]: {daily_df['keltner_target_buyer'].iloc[-1]:.{precision}f} ({daily_df['reward_risk_ratio_buyer'].iloc[-1]:.2f})"
    seller_prices = f"Entry [S]: {daily_df['pullback_entry_seller'].iloc[-1]:.{precision}f} | Initial Stop [S]: {daily_df['atr_initial_stop_seller'].iloc[-1]:.{precision}f} | Trailing Stop [S]: {daily_df['atr_trailing_stop_seller'].iloc[-1]:.{precision}f} | Breakeven [S]: ({daily_df['breakeven_price_seller'].iloc[-1]:.{precision}f} | {daily_df['breakeven_stop_seller'].iloc[-1]:.{precision}f}) | Protect Profit [S]: ({daily_df['protect_profit_price_seller'].iloc[-1]:.{precision}f} | {daily_df['protect_profit_stop_seller'].iloc[-1]:.{precision}f}) | Profit Target [S]: {daily_df['keltner_target_seller'].iloc[-1]:.{precision}f} ({daily_df['reward_risk_ratio_seller'].iloc[-1]:.2f})"

    daily_analysis_figure.update_layout(
        title_text=f'{market}    {symbol}    {name}  -  Daily',
        title_subtitle_text=f'{buyer_prices}<br /><br />{seller_prices}',

        title_x=0,
        title_xanchor='left',
        title_xref='paper',

        title_y=1,
        title_yanchor='top',
        title_yref='container',

        title_pad_t=15,
        margin_t=115,

        margin_b=45,
        margin_l=40,

        hovermode='x unified',
        hoverlabel_namelength=-1,
        template='plotly_dark',
    )

    return daily_analysis_figure

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
