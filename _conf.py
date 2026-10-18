#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import sys

BETWEEN_STOCKS_DELAY = 1.0    # 批量获取多只股票行情数据时，每只股票网络请求之间延迟秒数，必须是大于或等于零的整数或浮点数。
MAX_RETRIES = 5    # 最大重试次数，必须是大于或等于零的整数。
RETRY_DELAY = 1.0    # 重试延迟秒数，必须是大于或等于零的整数或浮点数。
TIMEOUT = 180.0    # 超时等待秒数，必须是大于零的整数或浮点数。

LOOKBACK_YEARS = 6    # 历史数据回溯年数，必须是大于零的整数。

STOCK_MIN_DAILY_KLINE_NUM = 252    # 最小上市交易日数，必须是大于或等于二百五十二的整数。
EXCLUDE_NEWLY_LISTED_STOCKS = True    # 排除新股。

FIGURE_LAYOUT_PERCENTAGE = 100    # 行情分析图表 HTML 布局百分比，必须是大于或等于一百的整数。

PRECISION = 2    # 对于以浮点数显示类型格式化的数值应当在小数点后显示多少个数位，必须是大于一的整数。

# 企业微信群组机器人
wechat_webhook_url = ''

def main() -> None:
    print('[!] This is a configuration.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
