#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Author: Jimmy ZHAO
With thanks to: Dr. Alexander Elder and Kerry Lovvorn
"""

import sys

def main() -> None:
    while get_reward_to_risk_ratio():
        continue

def get_reward_to_risk_ratio() -> bool:
    while True:
        action = input("[?] Long or Short ('L' [Default] or 'S') (Type 'q' to quit): ").strip().upper()

        if action == 'Q':
            return False

        if not action:
            action = 'L'

        if action not in ('L', 'S'):
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

                if action == 'L':
                    if your_stop_for_this_trade > your_entry_for_this_trade:
                        print("[-] The 'Stop Price' cannot be higher than the 'Entry Price'!")
                        continue

                    if your_entry_for_this_trade - your_stop_for_this_trade <= 0.01:
                        print("[-] The difference between the 'Stop Price' and the 'Entry Price' is too small!")
                        continue

                elif action == 'S':
                    if your_stop_for_this_trade < your_entry_for_this_trade:
                        print("[-] The 'Stop Price' cannot be lower than the 'Entry Price'!")
                        continue

                    if your_stop_for_this_trade - your_entry_for_this_trade <= 0.01:
                        print("[-] The difference between the 'Stop Price' and the 'Entry Price' is too small!")
                        continue

                else:
                    pass

                while True:
                    argument = input("[?] Your Target for This Trade (Type 'b' to back | 'q' to quit): ").strip().lower()

                    if not argument:
                        continue

                    if argument == 'b':
                        break

                    if argument == 'q':
                        return False

                    try:
                        your_target_for_this_trade = float(argument)
                    except ValueError as e:
                        print('[-] The value of argument <your_target_for_this_trade> is incorrect!')
                        continue

                    if your_target_for_this_trade <= 0.00:
                        print('[-] The value of argument <your_target_for_this_trade> is incorrect!')
                        continue

                    if action == 'L':
                        if your_target_for_this_trade < your_entry_for_this_trade:
                            print("[-] The 'Target Price' cannot be lower than the 'Entry Price'!")
                            continue

                        if your_target_for_this_trade - your_entry_for_this_trade <= 0.01:
                            print("[-] The difference between the 'Target Price' and the 'Entry Price' is too small!")
                            continue

                    elif action == 'S':
                        if your_target_for_this_trade > your_entry_for_this_trade:
                            print("[-] The 'Target Price' cannot be higher than the 'Entry Price'!")
                            continue

                        if your_entry_for_this_trade - your_target_for_this_trade <= 0.01:
                            print("[-] The difference between the 'Target Price' and the 'Entry Price' is too small!")
                            continue

                    else:
                        pass

                    if action == 'L':
                        your_risk_for_this_trade = your_entry_for_this_trade - your_stop_for_this_trade
                        your_reward_for_this_trade = your_target_for_this_trade - your_entry_for_this_trade
                        reward_to_risk_ratio = your_reward_for_this_trade / your_risk_for_this_trade

                    elif action == 'S':
                        your_risk_for_this_trade = your_stop_for_this_trade - your_entry_for_this_trade
                        your_reward_for_this_trade = your_entry_for_this_trade - your_target_for_this_trade
                        reward_to_risk_ratio = your_reward_for_this_trade / your_risk_for_this_trade

                    else:
                        pass

                    print(f'[!] Risk: {your_risk_for_this_trade:.3f} | Reward to Risk Ratio: {reward_to_risk_ratio:.2f}')
                    print()
                    return True

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        sys.exit(0)
