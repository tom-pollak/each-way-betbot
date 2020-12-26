from urllib import request, error
from dotenv import load_dotenv
from csv import DictWriter
import requests
import json
import datetime
import sys
import os

url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
MIN_PERCENTAGE_BALANCE = 0

load_dotenv(dotenv_path='.env')
APP_KEY = os.environ.get('APP_KEY')
USERNAME = os.environ.get('BETFAIR_USR')
PASSWORD = os.environ.get('BETFAIR_PASS')
headers = {}
if None in (USERNAME, PASSWORD, APP_KEY):
    raise Exception('Need to set betfair env vars')


def update_csv_betfair(race,
                       bookie_stake,
                       win_stake,
                       lay_stake,
                       betfair_balance,
                       win_matched,
                       lay_matched,
                       arbritrage_profit,
                       RETURNS_CSV):
    race['is_lay'] = True
    race['ew_stake'] = bookie_stake
    race['win_stake'] = win_stake
    race['lay_stake'] = lay_stake
    race['betfair_balance'] = betfair_balance
    race['win_matched'] = win_matched
    race['lay_matched'] = lay_matched
    race['arbritrage_profit'] = arbritrage_profit
    csv_columns = [
        'date_of_race',
        'horse_name',
        'horse_odds',
        'race_venue',
        'ew_stake',
        'balance',
        'rating',
        'current_time',
        'expected_value',
        'expected_return',
        'win_stake',
        'lay_odds',
        'lay_odds_place',
        'place_stake',
        'betfair_balance',
        'max_profit',
        'is_lay',
        'win_matched',
        'lay_matched',
        'arbritrage_profit'
    ]
    with open(RETURNS_CSV, 'a+', newline='') as returns_csv:
        csv_writer = DictWriter(returns_csv,
                                fieldnames=csv_columns,
                                extrasaction='ignore')
        csv_writer.writerow(race)


def login_betfair():
    url = 'https://identitysso-cert.betfair.com/api/certlogin'
    payload = f'username={USERNAME}&password={PASSWORD}'
    login_headers = {
        'X-Application': APP_KEY,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(
        'https://identitysso-cert.betfair.com/api/certlogin',
        data=payload,
        cert=('client-2048.crt', 'client-2048.key'),
        headers=login_headers)
    if response.status_code == 200:
        SESS_TOK = response.json()['sessionToken']
        global headers
        headers = {
            'X-Application': APP_KEY,
            'X-Authentication': SESS_TOK,
            'content-type': 'application/json'
        }
    else:
        raise Exception("Can't login")


def output_lay_ew(race,
                  betfair_balance,
                  profit,
                  win_bet_made,
                  win_is_matched,
                  win_matched,
                  place_bet_made,
                  place_is_matched,
                  place_matched):
    print(f"{race['horse_name']} - profit: £{profit}")
    print(
        f"\tBack bookie: {race['bookie_odds']} - {race['bookie_stake']} Lay win: {race['lay_odds']} - {race['lay_stake']} Lay place: {race['lay_odds_place']} - {race['place_stake']}"
    )
    print(
        f"\t Lay win: {win_bet_made} - is matched: {win_is_matched} Lay place: {place_bet_made} is matched {place_is_matched}"
    )

    if not win_is_matched:
        print(f"\tLay win matched size: {win_matched}")
    if not place_is_matched:
        print(f"\tLay place matched size: {place_matched}")

    print(f"\t{race['date_of_race']} - {race['race_venue']}")
    print(
        f"\tCurrent balance: {race['balance']}, betfair balance: {race['betfair_balance']}"
    )
    print('Bet made\n')


def call_api(jsonrpc_req, url=url):
    try:
        req = request.Request(url, jsonrpc_req.encode('utf-8'), headers)
        response = request.urlopen(req)
        json_res = response.read()
        return json_res.decode('utf-8')
    except error.URLError as e:
        print(e.reason)
        print('No service available at ' + str(url))
        exit()
    except error.HTTPError:
        print('Not a valid operation' + str(url))
        exit()


def get_event(venue, race_time):
    race_time_after = race_time + datetime.timedelta(0, 60)
    race_time = race_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    race_time_after = race_time_after.strftime('%Y-%m-%dT%H:%M:%SZ')

    event_req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listEvents", \
        "params": {"filter": {"eventTypeIds": ["7"], "marketTypeCodes": ["EACH_WAY"], \
        "marketStartTime": {"from": "%s", "to": "%s"}, "venues":["%s"]}, \
        "sort":"FIRST_TO_START","maxResults":"1"}}' % (
        race_time, race_time_after, venue)
    event_response = json.loads(call_api(event_req))

    try:
        event_id = event_response['result'][0]['event']['id']
    except:
        print('Exception from API-NG' + str(event_response['result']['error']))
    return event_id


def get_horse_id(horses, target_horse):
    for horse in horses['runners']:
        if horse['runnerName'] == target_horse:
            return horse['selectionId']


def get_horses(target_horse, event_id, race_time):
    markets_ids = {}
    race_time_after = race_time + datetime.timedelta(0, 60)
    race_time = race_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    race_time_after = race_time_after.strftime('%Y-%m-%dT%H:%M:%SZ')

    markets_req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/listMarketCatalogue", \
        "params": {"filter":{"eventIds": ["%s"], "marketStartTime": {"from": "%s", "to": "%s"}}, \
        "maxResults": "10", "sort":"FIRST_TO_START", \
        "marketProjection": ["RUNNER_DESCRIPTION"]}}' % (
        event_id, race_time, race_time_after)
    markets_response = json.loads(call_api(markets_req))

    try:
        market_type = markets_response['result']
        if len(market_type) != 3:
            print(market_type)
            raise Exception('Only %s market types returned' % len(market_type))
    except IndexError:
        print('Exception from API-NG' +
              str(markets_response['result']['error']))

    for market in market_type:
        if market['marketName'] == 'Each Way':
            markets_ids['Each Way'] = market['marketId']
        elif market['marketName'] == 'To Be Placed':
            markets_ids['Place'] = market['marketId']
        else:
            markets_ids['Win'] = market['marketId']

    selection_id = get_horse_id(market_type[0], target_horse)
    return markets_ids, selection_id


def lay_bets(market_id, selection_id, price, stake):
    matched = False
    bet_made = False
    stake_matched = 0
    bet_req = '{"jsonrpc": "2.0", "method": "SportsAPING/v1.0/placeOrders", \
        "params": {"marketId": "%s", "instructions": [{"selectionId": "%s", \
        "side": "LAY", "orderType": "LIMIT", "limitOrder": {"size": "%s", \
        "price": "%s", "persistenceType": "LAPSE"}}]}}' % (
        market_id, selection_id, stake, price)
    bet_res = json.loads(call_api(bet_req))
    print(bet_res)
    try:
        if bet_res['result']['status'] == 'SUCCESS':
            print('Bet made')
            bet_made = True
            stake_matched = bet_res['result']['instructionReports'][0][
                'sizeMatched']
            if stake_matched == stake:
                matched = True

    except KeyError:
        print('Error:' + bet_res['error'])
    return bet_made, matched, stake_matched


def get_betfair_balance():
    url = 'https://api.betfair.com/exchange/account/json-rpc/v1'
    balance_req = '{"jsonrpc": "2.0", "method": "AccountAPING/v1.0/getAccountFunds"}'
    balance_res = json.loads(call_api(balance_req, url=url))
    balance = balance_res['result']['availableToBetBalance']
    return balance


def calculate_stakes(bookie_balance,
                     betfair_balance,
                     bookie_stake,
                     bookie_odds,
                     win_stake,
                     win_odds,
                     place_stake,
                     place_odds,
                     avaliable_profit):
    max_profit_ratio = avaliable_profit / win_stake
    max_win_liability = (win_odds - 1) * win_stake
    max_place_liability = (place_odds - 1) * place_stake
    total_liability = max_win_liability + max_place_liability

    bookie_ratio = 1
    win_ratio = win_stake / bookie_stake
    place_ratio = place_stake / bookie_stake

    if total_liability > betfair_balance or bookie_stake > bookie_balance:
        liabiltity_ratio = betfair_balance / total_liability
        balance_ratio = bookie_stake / bookie_balance
        if balance_ratio < liabiltity_ratio:
            liabiltity_ratio = balance_ratio
    else:
        liabiltity_ratio = 1

    # maximum possible stakes
    bookie_stake *= liabiltity_ratio
    win_stake *= liabiltity_ratio
    place_stake *= liabiltity_ratio

    if win_stake >= 2 and place_stake >= 2 and bookie_stake >= 0.1:
        min_stake_proportion = max(2 / min(win_stake, place_stake),
                                   0.1 / bookie_stake)
        min_stake = min_stake_proportion * (bookie_stake + win_stake +
                                            place_stake)
        min_balance_staked = MIN_PERCENTAGE_BALANCE * (betfair_balance +
                                                       bookie_balance)
        if min_stake < min_balance_staked:
            min_stake_proportion = MIN_PERCENTAGE_BALANCE

        bookie_stake *= min_stake_proportion
        win_stake *= min_stake_proportion
        place_stake *= min_stake_proportion
        profit = max_profit_ratio * win_stake
        return True, bookie_stake, win_stake, place_stake, profit

    else:
        print('Stakes are too small to bet')
        print(
            f'Bookie stake: {bookie_stake} Win stake: {win_stake} Place stake: {place_stake}\n'
        )
        return False, 0, 0, 0, 0


def lay_ew(race_time,
           venue,
           horse,
           win_odds,
           win_stake,
           place_odds,
           place_stake):
    race_time = datetime.strptime(race_time, '%d %b %H:%M %Y')
    # if not isinstance(race_time, type(datetime.datetime.now())):
    #     raise Exception('race_time is not a datetime instance')
    event_id = get_event(venue, race_time)
    markets_ids, selection_id = get_horses(horse, event_id, race_time)
    lay_win, win_matched, win_stake_matched = lay_bets(markets_ids['Win'], selection_id, win_odds, win_stake)
    lay_place, place_matched, place_stake_matched = lay_bets(markets_ids['Place'],
                         selection_id,
                         place_odds,
                         place_stake)
    # print('Lay win: %s\tLay place: %s' % (lay_win, lay_place))
    return ((lay_win, win_matched, win_stake_matched),
            (lay_place, place_matched, place_stake_matched))


# Testing variables
# race_time = datetime.datetime(2020, 12, 16, 16)
# venue = 'Kempton'
# horse = 'Touchwood'
#
# event_id = get_event(venue, race_time)
# markets_ids, selection_id = get_horses(horse, event_id, race_time)
# print(markets_ids, selection_id)
# balance = get_betfair_balance()
# print(balance)
# print(calculate_stakes(5, 5, 14.5, 6.5, 14.5, 6.5, 15.22, 2, 0.73))
