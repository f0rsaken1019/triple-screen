#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import sys

MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO = 0.02

def main() -> None:
    if not isinstance(MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO, float):
        print(f'[-] The configuration <MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO> should be a {type(float())} instead of a {type(MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO)}!')
        sys.exit(1)

    if (MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO <= 0.00) or (MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO >= 1.00):
        print('[-] The value of configuration <MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO> is incorrect!')
        sys.exit(1)

    while get_maximum_number_of_shares_for_this_trade():
        continue

def get_maximum_number_of_shares_for_this_trade() -> bool:
    while True:
        argument = input("[?] Your Account Equity (Type 'q' to quit): ").strip().lower()

        if not argument:
            continue

        if argument == 'q':
            return False

        try:
            your_account_equity = float(argument)
        except ValueError as e:
            print('[-] The value of argument <your_account_equity> is incorrect!')
            continue

        if your_account_equity <= 0.00:
            print('[-] The value of argument <your_account_equity> is incorrect!')
            continue

        while True:
            argument = input("[?] Your Entry for This Trade (Type 'b' to back | 'q' to quit): ").strip().lower()

            if not argument:
                continue

            if argument == 'b':
                break

            if argument == 'q':
                return False

            try:
                your_entry_for_this_trade = float(argument)
            except ValueError as e:
                print('[-] The value of argument <your_entry_for_this_trade> is incorrect!')
                continue

            if your_entry_for_this_trade <= 0.00:
                print('[-] The value of argument <your_entry_for_this_trade> is incorrect!')
                continue

            while True:
                argument = input("[?] Your Stop for This Trade (Type 'b' to back | 'q' to quit): ").strip().lower()

                if not argument:
                    continue

                if argument == 'b':
                    break

                if argument == 'q':
                    return False

                try:
                    your_stop_for_this_trade = float(argument)
                except ValueError as e:
                    print('[-] The value of argument <your_stop_for_this_trade> is incorrect!')
                    continue

                if your_stop_for_this_trade <= 0.00:
                    print('[-] The value of argument <your_stop_for_this_trade> is incorrect!')
                    continue

                if abs(your_entry_for_this_trade - your_stop_for_this_trade) <= 0.01:
                    print("[-] The difference between the 'Stop Price' and the 'Entry Price' is too small!")
                    continue

                while True:
                    argument = input("[?] Minimum Number of Shares (Default: 1) (Type 'b' to back | 'q' to quit): ").strip().lower()

                    if not argument:
                        argument = 1
                    else:
                        if argument == 'b':
                            break

                        if argument == 'q':
                            return False

                    try:
                        minimum_number_of_shares = int(argument)
                    except ValueError as e:
                        print('[-] The value of argument <minimum_number_of_shares> is incorrect!')
                        continue

                    if minimum_number_of_shares <= 0:
                        print('[-] The value of argument <minimum_number_of_shares> is incorrect!')
                        continue

                    if (minimum_number_of_shares != 1) and (minimum_number_of_shares % 10 != 0):
                        print('[-] The value of argument <minimum_number_of_shares> is incorrect!')
                        continue

                    your_maximum_risk_for_this_trade = your_account_equity * MAXIMUM_RISK_FOR_SINGLE_TRADE_AS_ACCOUNT_EQUITY_RATIO
                    your_maximum_risk_per_share = abs(your_entry_for_this_trade - your_stop_for_this_trade)
                    maximum_number_of_shares_you_may_trade = int(your_maximum_risk_for_this_trade / your_maximum_risk_per_share)
                    maximum_number_of_shares_you_may_trade = maximum_number_of_shares_you_may_trade // minimum_number_of_shares * minimum_number_of_shares

                    print(f'[!] Maximum Number of Shares You May Trade: {maximum_number_of_shares_you_may_trade}')
                    print()
                    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
