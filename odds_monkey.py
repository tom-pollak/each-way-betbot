import sys
from time import sleep, time
from datetime import datetime

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

from sporting_index import setup_sporting_index, sporting_index_bet, refresh_sporting_index, get_balance_sporting_index
from betfair_api import lay_ew, get_betfair_balance, login_betfair, get_race
from calculate import calculate_stakes, calculate_profit, kelly_criterion, check_repeat_bets
from output import update_csv_sporting_index, update_csv_betfair, show_info, output_lay_ew, output_race

REFRESH_TIME = 60


def find_races(driver, row=0, window=0):
    driver.switch_to.window(driver.window_handles[window])
    driver.switch_to.default_content()
    horse_name = driver.find_element_by_xpath(
        f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[9]'
    ).text.title()

    date_of_race = driver.find_element_by_xpath(
        f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[1]'
    ).text
    race_time = date_of_race[-5:].lower()
    date_of_race += ' %s' % datetime.today().year
    venue = driver.find_element_by_xpath(
        f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[8]'
    ).text.lower().strip()
    venue = venue[:len(venue) - 5].strip().title()

    bookie_odds = driver.find_element_by_xpath(
        f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[13]'
    ).text

    bookie_exchange = driver.find_element_by_xpath(
        f'//*[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]/td[10]/a'
    ).get_attribute('href')
    if 'sportingindex' not in bookie_exchange:
        print('Sportingindex not in bookie_exchange, have you adjusted the filters?')
        print(bookie_exchange)
        sys.exit()

    rating = driver.find_element_by_xpath(
        f'//*[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]/td[17]').text

    max_profit = driver.find_element_by_xpath(
        f'//*[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]/td[20]'
    ).text.split('£')[1]

    driver.find_element_by_xpath(
        f'//*[@id="dnn_ctr1157_View_RadGrid1_ctl00_ctl{"{:02d}".format(2 * row + 4)}_calcButton"]'
    ).click()
    sleep(2)

    driver.switch_to.frame('RadWindow2')
    horse_name_window = WebDriverWait(driver, 60).until(
        EC.visibility_of_element_located(
            (By.XPATH, '//*[@id="lblOutcomeName"]'))).text.title()

    if horse_name != horse_name_window:
        print('ERROR horse_name not same: %s, %s' %
              (horse_name, horse_name_window))
        driver.switch_to.default_content()
        driver.find_element_by_class_name('rwCloseButton').click()
        return {}

    win_odds = WebDriverWait(driver, 600).until(
        EC.visibility_of_element_located(
            (By.XPATH, '//*[@id="txtLayOdds_win"]'))).get_attribute('value')

    place_odds = driver.find_element_by_xpath(
        '//*[@id="txtLayOdds_place"]').get_attribute('value')
    places_paid = driver.find_element_by_xpath(
        '//*[@id="lblPlacesPaid_lay"]').get_attribute('value')
    place_payout = driver.find_element_by_xpath(
        '//*[@id="txtPlacePayout"]').get_attribute('value')

    bookie_stake = WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located(
            (By.XPATH,
             '//*[@id="lblStep1"]/strong[1]'))).text.replace('£', '')

    win_stake = driver.find_element_by_xpath(
        '//*[@id="lblStep2"]/strong[1]').text.replace('£', '')
    place_stake = driver.find_element_by_xpath(
        '//*[@id="lblStep3"]/b').text.replace('£', '')

    driver.switch_to.default_content()
    driver.find_element_by_class_name('rwCloseButton').click()

    return {
        'date_of_race': date_of_race,
        'race_time': race_time,
        'horse_name': horse_name,
        'bookie_odds': float(bookie_odds),
        'venue': venue,
        'bookie_exchange': bookie_exchange,
        'rating': float(rating),
        'current_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'win_odds': float(win_odds),
        'place_odds': float(place_odds),
        'places_paid': float(places_paid),
        'place_payout': float(place_payout),
        'bookie_stake': float(bookie_stake),
        'win_stake': float(win_stake),
        'place_stake': float(place_stake),
        'max_profit': float(max_profit),
    }


def hide_race(driver, row=0, window=0):
    # print('Hiding bet')
    driver.switch_to.window(driver.window_handles[window])
    driver.find_element_by_xpath(
        f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[55]//div//a'
    ).click()
    WebDriverWait(driver, 60).until(
        EC.invisibility_of_element_located((
            By.ID,
            'dnn_ctr1157_View_RadAjaxLoadingPanel1dnn_ctr1157_View_RadGrid1')))


def trigger_betfair_options(driver):
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable(
            (By.XPATH,
             '//*[@id="dnn_ctr1157_View_RadGrid1_ctl00"]/thead/tr/th[17]/a'
             ))).click()

    WebDriverWait(driver, 60).until(
        EC.visibility_of_element_located((
            By.XPATH,
            '//*[@id="dnn_ctr1157_View_RadToolBar1"]/div/div/div/ul/li[6]/a/span/span/span/span'
        ))).click()
    WebDriverWait(driver, 60).until(
        EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="headingFour"]/h4/a'))).click()
    sleep(0.5)
    driver.find_element_by_xpath(
        '//*[@id="dnn_ctr1157_View_rlbExchanges"]/div/div/label/input').click(
        )
    driver.find_element_by_xpath(
        '//*[@id="dnn_ctr1157_View_rlbExchanges_i0"]/label/input').click()
    driver.find_element_by_xpath(
        '//*[@id="dnn_ctr1157_View_btnApplyFilter"]').click()
    driver.find_element_by_xpath(
        '//*[@id="dnn_ctr1157_ModuleContent"]/div[10]/div[1]/a').click()
    sleep(0.5)


def refresh_odds_monkey(driver, betfair=False):
    for i in range(5):
        driver.switch_to.default_content()
        try:
            action = ActionChains(driver)
            element = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    '//*[@id="dnn_ctr1157_View_RadGrid1_ctl00"]/thead/tr/th[2]'
                )))
            action.move_to_element(element)
            action.perform()

            WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//*[@id="dnn_ctr1157_View_RadToolBar1_i11_lblRefreshText"]'
                ))).click()
            # driver.execute_script("InitiateAjaxRequest('refresh');")
            # wait until spinner disappeared
            WebDriverWait(driver, 60).until(
                EC.invisibility_of_element_located((
                    By.ID,
                    'dnn_ctr1157_View_RadAjaxLoadingPanel1dnn_ctr1157_View_RadGrid1'
                )))
            return

        except (TimeoutException, ElementClickInterceptedException) as e:
            if i == 4:
                print(e)
            driver.refresh()
            WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//*[@id="dnn_LOGO1_imgLogo"]')))
            if betfair:
                trigger_betfair_options(driver)
                driver.switch_to.default_content()
    raise ValueError("Couldn't refresh Oddsmonkey")


def open_betfair_oddsmonkey(driver):
    driver.execute_script(
        '''window.open("https://www.oddsmonkey.com/Tools/Matchers/EachwayMatcher.aspx","_blank");'''
    )
    driver.switch_to.window(driver.window_handles[2])
    trigger_betfair_options(driver)


def get_no_rows(driver):
    count = 0
    while True:
        try:
            driver.find_element_by_xpath(
                f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{count}"]//td[1]'
            )
            count += 1
        except NoSuchElementException:
            return count


def betfair_bet(driver, race):
    # print('Found arbitrage bet: %s' % race['horse_name'])
    if race['max_profit'] <= 0:
        # print('\tMax profit < 0')
        return

    headers = login_betfair()
    betfair_balance = get_betfair_balance(headers)
    stakes_ok, bookie_stake, win_stake, place_stake = calculate_stakes(
        race['balance'], betfair_balance, race['bookie_stake'],
        race['win_stake'], race['win_odds'], race['place_stake'],
        race['place_odds'])

    if not stakes_ok:
        return

    profits = calculate_profit(race['bookie_odds'], bookie_stake,
                               race['win_odds'], win_stake, race['place_odds'],
                               place_stake, race['place_payout'])
    if min(*profits) <= 0:
        # print('\tProfits < £0')
        return

    minutes_until_race = (
        datetime.strptime(race['date_of_race'], '%d %b %H:%M %Y') -
        datetime.now()).total_seconds() / 60
    if minutes_until_race <= 2:
        print('\tRace too close to start time: %s' % minutes_until_race)
        return

    market_ids, selection_id, got_race, race['horse_name'] = get_race(
        race['date_of_race'], race['venue'], race['horse_name'])
    if not got_race:
        return

    race['bookie_stake'] = bookie_stake
    race, bet_made = sporting_index_bet(driver, race, make_betfair_ew=True)
    if bet_made is None:
        print(
            f"Horse not found: {race['horse_name']}  venue: {race['venue']}  race time: {race['date_of_race']}"
        )
        return
    if bet_made:
        lay_win, lay_place = lay_ew(market_ids, selection_id, win_stake,
                                    race['win_odds'], place_stake,
                                    race['place_odds'])
        betfair_balance = get_betfair_balance(headers)
        sporting_index_balance = get_balance_sporting_index(driver)
        race['balance'] = sporting_index_balance
        if lay_win[4] and lay_place[4]:
            win_profit, place_profit, lose_profit = calculate_profit(
                race['bookie_odds'], bookie_stake, lay_win[4], lay_win[3],
                lay_place[4], lay_place[3], race['place_payout'])
            min_profit = min(win_profit, place_profit, lose_profit)
        else:
            win_profit = place_profit = lose_profit = min_profit = 0

        output_lay_ew(race, betfair_balance, sporting_index_balance,
                      min_profit, *lay_win, *lay_place, win_profit,
                      place_profit, lose_profit)
        update_csv_betfair(race, sporting_index_balance, bookie_stake,
                           win_stake, place_stake, betfair_balance, lay_win[3],
                           lay_place[3], min_profit, lay_win[4], lay_place[4])


def evaluate_bet(driver, race):
    # print('Found bet no lay: %s' % race['horse_name'])
    race['ew_stake'], race['expected_return'], race[
        'expected_value'] = kelly_criterion(race['bookie_odds'],
                                            race['win_odds'],
                                            race['place_odds'],
                                            race['place_payout'],
                                            race['balance'])

    if race['ew_stake'] < 0.1:
        # print(f"\tStake is too small: £{race['ew_stake']}")
        return False

    bet_made = False
    race, bet_made = sporting_index_bet(driver, race)
    if bet_made is None:  # horse not found
        print(
            f"Horse not found: {race['horse_name']}  venue: {race['venue']}  race time: {race['date_of_race']}"
        )
        return False
    if bet_made:  # bet made
        output_race(driver, race)
        update_csv_sporting_index(driver, race)
        return True
    return False


def start_sporting_index(driver):
    race = {'balance': get_balance_sporting_index(driver)}
    processed_horses = []
    driver.switch_to.window(driver.window_handles[0])
    refresh_odds_monkey(driver)
    if not driver.find_elements_by_class_name('rgNoRecords'):
        for row in range(get_no_rows(driver)):
            horse_name = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[9]'
                ))).text.title()
            if horse_name not in processed_horses:
                race.update(find_races(driver, row, 0))
                processed_horses.append(
                    race['horse_name']
                )  # has to be before get race because of if condition above

                _, _, _, race['horse_name'] = get_race(race['date_of_race'],
                                                       race['venue'],
                                                       race['horse_name'])

                if check_repeat_bets(race['horse_name'], race['date_of_race'],
                                     race['venue']):
                    evaluate_bet(driver, race)
            driver.switch_to.window(driver.window_handles[0])
            driver.switch_to.default_content()
            sys.stdout.flush()


def start_betfair(driver):
    race = {'balance': get_balance_sporting_index(driver)}
    processed_horses = []
    driver.switch_to.window(driver.window_handles[2])
    refresh_odds_monkey(driver, betfair=True)
    if not driver.find_elements_by_class_name('rgNoRecords'):
        for row in range(get_no_rows(driver)):
            horse_name = WebDriverWait(driver, 60).until(
                EC.visibility_of_element_located((
                    By.XPATH,
                    f'//table//tr[@id="dnn_ctr1157_View_RadGrid1_ctl00__{row}"]//td[9]'
                ))).text.title()
            if horse_name not in processed_horses:
                race.update(find_races(driver, row, 2))
                processed_horses.append(race['horse_name'])
                betfair_bet(driver, race)
            driver.switch_to.window(driver.window_handles[2])
            driver.switch_to.default_content()
            sys.stdout.flush()


def scrape(driver):
    START_TIME = time()
    setup_sporting_index(driver)
    open_betfair_oddsmonkey(driver)
    count = 0
    driver.switch_to.window(driver.window_handles[0])
    while True:
        # So sporting index dosent logout
        if count % 2 == 0:
            refresh_sporting_index(driver)
            if count % 10 == 0:
                show_info(count, START_TIME)

        start_betfair(driver)
        start_sporting_index(driver)
        sys.stdout.flush()
        sleep(REFRESH_TIME)
        count += 1
