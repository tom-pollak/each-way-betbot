from random import uniform


def simulate_bet(stake, odds, rating, balance):
    original_bal = balance
    stake *= 2
    for i in range(1000):
        if uniform(0, round(odds / (rating / 100), 2)) <= 1:
            balance += odds * stake
        balance -= stake
        if balance <= 0:
            return False
    if balance > original_bal:
        # print(balance)
        return True
    else:
        # print(balance)
        return False


# import numpy as np

import time


def find_stake(odds, rating, balance):
    start = time.time()
    count = 0
    stake = 0.1 * balance
    iterations = 0
    while iterations <= 40 and count < 750:
        count = 0
        for j in range(1000):
            if simulate_bet(stake, odds, rating, balance):
                count += 1
        # percentage_list.append(count)
        stake -= (750 - count) / 1000 * stake
        iterations += 1
        if stake < 0.1:
            count = 0
            for j in range(1000):
                if simulate_bet(stake, odds, rating, balance):
                    count += 1
            # print(stake, count / 10)
            print(f'\nElapsed time: {round(time.time() - start, 2)}')
            if count > 500:
                return 0.1, (count / 10)
            return False, (count / 10)
    print(f'\nElapsed time: {round(time.time() - start, 2)}')
    if iterations == 40:
        return False, (count / 10)
    return round(stake, 2), (count / 10)
