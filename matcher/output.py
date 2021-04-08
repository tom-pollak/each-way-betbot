import os
import shutil
from time import time
from datetime import datetime
from dotenv import load_dotenv
from csv import DictWriter

from matcher.sites.betfair_api import (
    get_betfair_balance,
    login_betfair,
    get_betfair_balance_in_bets,
)
from matcher.sites.sporting_index import get_balance_sporting_index

BASEDIR = os.path.abspath(os.path.dirname(__file__) + "/../")
load_dotenv(os.path.join(BASEDIR, ".env"))
RETURNS_CSV = os.environ.get("RETURNS_CSV")


def show_info(count, START_TIME):
    def convert_time(time_secs):
        hours = int(time_secs // 60 ** 2)
        mins = int(time_secs // 60 - hours * 60)
        secs = round(time_secs - (hours * 60 * 60) - (mins * 60))
        return f"{hours:02}:{mins:02}:{secs:02}"

    diff = time() - START_TIME
    time_alive = convert_time(diff)

    print(f"Time is: {datetime.now().strftime('%H:%M:%S')}\tTime alive: {time_alive}")
    print(f"Refreshes: {count}")
    if datetime.now().hour < 7:
        print("\nMatcher started to early (before 7am)")
        raise KeyboardInterrupt
    if datetime.now().hour >= 18:
        print("\nFinished matching today")
        print("---------------------------------------------")
        raise KeyboardInterrupt


def output_race(driver, race):
    balance = get_balance_sporting_index(driver)
    print(
        f"\nNo Lay bet made ({datetime.now().strftime('%H:%M:%S')}): {race['horse_name']} - {race['bookie_odds']}"
    )
    print(f"\t{race['date_of_race']} - {race['venue']}")
    print(f"\tLay win: {race['win_odds']} Lay place: {race['place_odds']}")
    try:
        print(
            f"\tExpected value: {race['expected_value']}, Expected return: £{format(race['expected_return'], '.2f')}"
        )
    except KeyError:
        print("Key Error in output_race")
    print(
        f"\tCurrent balance: £{format(balance, '.2f')}, stake: £{format(race['ew_stake'], '.2f')}\n"
    )


def output_lay_ew(
    race,
    betfair_balance,
    sporting_index_balance,
    profit,
    win_bet_made,
    win_is_matched,
    win_stake,
    win_matched,
    win_odds,
    place_bet_made,
    place_is_matched,
    place_stake,
    place_matched,
    place_odds,
    win_profit,
    place_profit,
    lose_profit,
):
    print(
        f"\nArb bet made ({datetime.now().strftime('%H:%M:%S')}): {race['horse_name']} - profit: £{format(profit, '.2f')}"
    )
    print(f"\t{race['date_of_race']} - {race['venue']}")
    print(
        f"\tBack bookie: {race['bookie_odds']} - £{format(race['ew_stake'], '.2f')} Lay win: {win_odds} - £{format(win_stake, '.2f')} Lay place: {place_odds} - £{format(place_stake, '.2f')}"
    )

    print(
        f"\tLay win: {win_bet_made} - is matched: {win_is_matched} Lay place: {place_bet_made} is matched: {place_is_matched}"
    )

    if not win_is_matched:
        print(f"\tLay win matched size: £{format(win_matched, '.2f')} ", end="")
    if not place_is_matched:
        print(f"\tLay place matched size: £{format(place_matched, '.2f')}")
    if not win_matched and place_matched:
        print()

    print(
        f"\tWin profit: £{format(win_profit, '.2f')} Place profit: £{format(place_profit, '.2f')} Lose profit: £{format(lose_profit, '.2f')}"
    )
    print(
        f"Current balance: £{format(sporting_index_balance, '.2f')}, betfair balance: £{format(betfair_balance, '.2f')}\n"
    )


def update_csv_sporting_index(driver, race):
    headers = login_betfair()
    race["is_lay"] = False
    race["win_matched"] = 0
    race["lay_matched"] = 0
    race["arbritrage_profit"] = 0
    race["balance"] = get_balance_sporting_index(driver)
    race["betfair_balance"] = get_betfair_balance(headers)
    race["balance_in_betfair"] = get_betfair_balance_in_bets()
    csv_columns = [
        "date_of_race",
        "horse_name",
        "bookie_odds",
        "venue",
        "ew_stake",
        "balance",
        "rating",
        "expected_value",
        "expected_return",
        "win_stake",
        "place_stake",
        "win_odds",
        "place_odds",
        "betfair_balance",
        "max_profit",
        "is_lay",
        "win_matched",
        "lay_matched",
        "arbritrage_profit",
        "place_payout",
        "balance_in_betfair",
        "current_time",
    ]
    with open(RETURNS_CSV, "a+", newline="") as returns_csv:
        csv_writer = DictWriter(
            returns_csv, fieldnames=csv_columns, extrasaction="ignore"
        )
        csv_writer.writerow(race)


def update_csv_betfair(
    race,
    sporting_index_balance,
    bookie_stake,
    win_stake,
    place_stake,
    betfair_balance,
    win_matched,
    lay_matched,
    arbritrage_profit,
    win_odds,
    place_odds,
):
    race["is_lay"] = True
    race["ew_stake"] = bookie_stake
    race["win_stake"] = win_stake
    race["place_stake"] = place_stake
    race["betfair_balance"] = betfair_balance
    race["balance"] = sporting_index_balance
    race["win_matched"] = win_matched
    race["lay_matched"] = lay_matched
    race["arbritrage_profit"] = arbritrage_profit
    race["expected_value"] = race["expected_return"] = 0
    race["win_odds"] = win_odds
    race["place_odds"] = place_odds
    race["balance_in_betfair"] = get_betfair_balance_in_bets()
    csv_columns = [
        "date_of_race",
        "horse_name",
        "bookie_odds",
        "venue",
        "ew_stake",
        "balance",
        "rating",
        "expected_value",
        "expected_return",
        "win_stake",
        "place_stake",
        "win_odds",
        "place_odds",
        "betfair_balance",
        "max_profit",
        "is_lay",
        "win_matched",
        "lay_matched",
        "arbritrage_profit",
        "place_payout",
        "balance_in_betfair",
        "current_time",
    ]
    with open(RETURNS_CSV, "a+", newline="") as returns_csv:
        csv_writer = DictWriter(
            returns_csv, fieldnames=csv_columns, extrasaction="ignore"
        )
        csv_writer.writerow(race)


def reset_csv():
    if not os.path.isdir("stats"):
        os.mkdir("stats")
    if not os.path.isfile(".env"):
        shutil.copyfile(".env.template", ".env")
    now = datetime.now().strftime("%d-%m-%Y")
    RETURNS_HEADER = "date_of_race,horse_name,bookie_odds,venue,ew_stake,balance,rating,expected_value,expected_return,win_stake,place_stake,win_odds,place_odds,betfair_balance,max_profit,is_lay,win_matched,lay_matched,arbritrage_profit,place_payout,balance_in_betfair,current_time"
    RETURNS_BAK = os.path.join(BASEDIR, "stats/returns-%s.csv" % now)
    create_new_returns = "y"

    if os.path.isfile(RETURNS_CSV):
        create_new_returns = input(
            "Create new return.csv? (Recommended for new user) Y/[n] "
        ).lower()

    if create_new_returns == "y":
        if os.path.isfile(RETURNS_CSV):
            count = 2
            while os.path.isfile(RETURNS_BAK):
                RETURNS_BAK = f"{RETURNS_BAK}({str(count)})"
                count += 1
            os.rename(RETURNS_CSV, RETURNS_BAK)
        with open(RETURNS_CSV, "w", newline="") as returns_csv:
            returns_csv.write(RETURNS_HEADER)
            print("Created new returns.csv")
