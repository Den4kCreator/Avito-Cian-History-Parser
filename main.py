import logging
import re
import os
from datetime import datetime, timedelta, time
from itertools import groupby
from time import sleep
import csv
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request


from hcaptcha_solver import hcaptcha_solver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (NoSuchElementException, TimeoutException)
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup as BS
import pytesseract
from PIL import Image

from root_chromedriver import RootChromeDriver, ChromeDriver
from cfg import * 


# SETUP
# create logger
logging.basicConfig(
    filename='execution.log', level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8')


def send_email_msg(body_msg, subject_msg, send_from, password, send_to):
    # Create a secure SSL/TLS context
    context = ssl.create_default_context()
    with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        
        # Login with the provided credentials
        smtp.login(send_from, password)
        
        # Compose the message
        msg = MIMEMultipart()
        msg["From"] = send_from
        msg["To"] = send_to
        msg["Subject"] = subject_msg
        msg.attach(MIMEText(body_msg, "plain"))
        
        # Send the message
        send_errors = smtp.sendmail(from_addr=send_from, to_addrs=send_to, msg=msg.as_string())
        return send_errors


def cian_parse_cards(driver, collected_cards):
    # LOGGING INFO
    logging.info(f'start cian parse cards function')

    # wait cards loading
    WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, '//div[@data-testid="offer-card"]'))
    )
    cards_count_elem = driver.find_element(By.XPATH, '//div[@class="_93444fe79c--wrapper--W0WqH"]')
    cards_count = int(cards_count_elem.get_property('childElementCount')) if cards_count_elem else 0

    # LOGGING INFO
    logging.info(f'find ads (cards) - {cards_count}')
    
    for card_n in range(1, cards_count+3):
        try:
            btn = driver.find_element(By.XPATH, f'//div[@class="_93444fe79c--wrapper--W0WqH"]/div[{card_n}]//button[@data-mark="PhoneButton"]')
        except NoSuchElementException:
            continue
        # scroll to btn
        ActionChains(driver)\
            .scroll_to_element(btn)\
            .move_to_element(btn)\
            .perform()
        btn.click()

        # LOGGING INFO
        logging.info(f'find and click phone button')

        # accept number
        try:
            WebDriverWait(driver, 2, poll_frequency=1).until(
                EC.presence_of_element_located((By.XPATH, '//button//span[text()="Всё равно позвонить"]'))
            ).click()

            # LOGGING INFO
            logging.info(f'click on accept number button')
        except TimeoutException:
            pass
    html = driver.page_source
    soup = BS(html, 'html.parser')
    cards = soup.find_all('div', {'data-testid': 'offer-card'})
    for card in cards:
        link = card.find('a', class_='_93444fe79c--link--VtWj6').get('href')
        title = card.find('span', attrs={'data-mark': 'OfferTitle'}).text
        # right side
        right_elem = card.find('div', attrs={'data-name': 'BrandingLevelWrapper'})
        id_ = link.split('suburban/')[1].replace('/', '')
        type_company = right_elem.find('div', class_='_93444fe79c--container--GyJAp').find('span').text.strip()
        phone = right_elem.find('span', attrs={'data-mark': 'PhoneValue'}).text.strip()
        price = card.find('span', {'data-mark': 'MainPrice'}).text.strip().replace('\xa0', ' ')
        additional_address = ' | '.join(
            [e.find('a').text.strip() + ' ' + e.find('div').text.strip() for e in card.find_all('div', class_='_93444fe79c--container--w7txv')]).replace('\n', '|')
        address = additional_address + ' | ' + card.find('div', {'class': '_93444fe79c--labels--L8WyJ'}).text.strip().replace('\n', '|')

        electric = 'Не указано'
        gaz = 'Не указано'
        sewarage = 'Не указано'
        water = 'Не указано'
        area = 'Не указано'
        # request and collect this data
        driver.get(link)
        sleep(3)
        date_created_text = driver.find_element(By.XPATH, '//div[@data-testid="metadata-added-date"]').text
        date_created = date_created_text.split('Обновлено:')
        if len(date_created) > 1:
            date_created = date_created[1].strip()
            date_created = cian_convert_date(date_created)
        else:
            date_created = date_created[0].strip()
        try:
            views_data = driver.find_element(By.XPATH, '//button[@data-name="OfferStats"]').text
        except NoSuchElementException:
            continue
        else:
            total_views, today_views = views_data.split(', ')
            total_views, today_views = int(''.join(re.findall(r'\d+', total_views))), int(''.join(re.findall(r'\d+', today_views)))
            
        card_html = driver.page_source
        soup = BS(card_html, 'html.parser')
        params_elems = soup.find_all('div', attrs={'data-name': 'OfferSummaryInfoItem'})
        params_elems = [] if params_elems is None else params_elems
        # format_params_elems = [ for p in params_elems]
        for p in params_elems:
            if not p:
                continue
            p = p.text
            if 'Электричество' in p:
                electric = p.replace('Электричество', '').replace('\xa0', ' ')
            elif 'Газ' in p:
                gaz = p.replace('Газ', '').replace('\xa0', ' ')
            elif 'Канализация' in p:
                sewarage = p.replace('Канализация', '').replace('\xa0', ' ')
            elif 'Водоснабжение' in p:
                water = p.replace('Водоснабжение', '').replace('\xa0', ' ')
            elif 'Площадь' in p:
                area = p.replace('Площадь', '').replace('\xa0', '')
        
        dict_card = {
            'ad_name': title,
            'ad_total_views': total_views,
            'ad_id': id_,
            'ad_area': area,
            'ad_total_price': price,
            'ad_address': address,
            'ad_type_company': type_company,
            'ad_phone': phone,
            'ad_link': link,
            'ad_date_created': date_created,
            'electric': electric,
            'gaz': gaz,
            'water': water,
            'sewarage': sewarage,
            'parse_timestamp': str(datetime.now().strftime(TIMESTAMP_DT_FORMAT)),
        }
        if not any([dict_card['ad_id'] == dict_2_card['ad_id'] for dict_2_card in collected_cards]):
            print(dict_card)
            collected_cards.append(dict_card)       



def cian_parse(driver: ChromeDriver, region_id: str):
    # LOGGING INFO
    logging.info(f'cian parse start function, region_id - {region_id}')

    region_id = str(region_id)
    collected_cards = []    # container ads
    ex = ''   # Doesnt have any exceptions on start function

    # we have a first page => &p=1
    page_url = f'https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&object_type%5B0%5D=3&offer_type=suburban&p=1&region={region_id}'
    for page_n in range(1, 5_000):
        if page_n > 1:
            page_url = page_url.replace(f'&p={page_n-1}', f'&p={page_n}')
        # collect current (first) page and replace to 2 3 4 5...
        print(f'[*]Get - {page_url}')
        driver.get(page_url)

        # scroll down
        body = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')))
        body.send_keys(Keys.END)
        body.send_keys(Keys.END)

        # LOGGING INFO
        logging.info('Scroll page to down')

        # check that page is exists
        try:
            if page_n > 1:
                WebDriverWait(driver, 3, poll_frequency=1).until(
                    EC.url_contains(f'&p={page_n}')
                )
        except TimeoutException:
            return [collected_cards, ex]
        else:
            try:
                cian_parse_cards(driver, collected_cards)
            except Exception as ex:
                # LOGGING INFO
                logging.error(f'get error for cian parse func - {ex}')
                return [collected_cards, ex]
    
    # LOGGING INFO
    logging.info(f'success end parsing for cian')

    return [collected_cards, ex]


def avito_driver_get_handler(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, timeout=6, poll_frequency=2).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='h-captcha']/iframe"))
        )
    except TimeoutException:
        return
    else:
        # LOGGING INFO
        logging.info(f'find captcha on avito, solving')

        print('[!]hCaptcha detected!, solving...')
        solver = hcaptcha_solver.Captcha_Solver(verbose=True)
        captcha_is_present = solver.is_captcha_present()
        print(f'Captcha is present flag - {captcha_is_present}\nSolving...')
        solver.solve_captcha(driver)
        driver.find_element(By.XPATH, '//div[@class="h-captcha"]//button[@type="submit"]').click()
        sleep(6)
        return


def avito_ads_parse(driver, collected_ads):
    # LOGGING INFO
    logging.info(f'start avito_ads_parse')

    ads_count = driver.find_elements(By.CSS_SELECTOR, 'div[data-marker="item"]')
    ads_count = 0 if ads_count is None else len(ads_count)

    # LOGGING INFO
    logging.info(f'collect ads_count - {ads_count}')

    for ad_num in range(1, ads_count):

        ad_xpath = f'//div[@data-marker="item"][{ad_num}]'
        # Собираем цены в объявлениях потом метод get("content")
        ad_price = driver.find_element(By.XPATH, ad_xpath + '//p[@data-marker="item-price"]').text.replace('\xa0', '').replace(r'\xa0', '')

        # Собираем url объявлений
        ad_url = driver.find_element(By.XPATH, ad_xpath + '//a[@data-marker="item-title"]').get_attribute("href")

        # Собираем названия объявлений
        ad_name = driver.find_element(By.XPATH, ad_xpath + '//h3[@itemprop="name"]').text

        # Собираем удельные цены (за сотку и т.д.)  
        try:
            ad_unit_price = driver.find_element(By.XPATH, ad_xpath + '//div[@class="iva-item-priceStep-uq2CQ"]//span/p').text
        except NoSuchElementException:
            ad_unit_price = 'Нет удельной цены'

        # Переходим на страницу объявляние для сбора доп инфы
        if len(driver.window_handles) == 1: 
            driver.execute_script("window.open('', '_blank');")
        # Переключаемся на новое вкладка
        driver.switch_to.window(driver.window_handles[-1])
        # начинаем сбор до инфы
        avito_driver_get_handler(driver, ad_url)
        sleep(4)

        # собираем доп инфу
        ad_address = driver.find_element(By.XPATH, '//div[@itemprop="address"]').text.strip().replace('\n', '|')
        ad_id = driver.find_element(By.XPATH, '//span[@data-marker="item-view/item-id"]').text
        ad_id = re.search('\d+', ad_id)[0]
        ad_company_type = driver.find_element(By.XPATH, '//div[@data-marker="seller-info/label"]').text
        ad_publ_time = driver.find_element(By.XPATH, '//span[@data-marker="item-view/item-date"]').text
        ad_publ_time = avito_convert_date(ad_publ_time)
        ad_total_views = driver.find_element(By.XPATH, '//span[@data-marker="item-view/total-views"]').text
        ad_total_views = int(re.search('\d+', ad_total_views)[0])
        ad_today_views = driver.find_element(By.XPATH, '//span[@data-marker="item-view/today-views"]').text
        ad_today_views = int(re.search('\d+', ad_today_views)[0])

        # собираем инфу с категорий снизу
        ad_area_found_list = [e.text.replace('Площадь:', '').strip() for e in driver.find_elements(By.XPATH, '//li[@class="params-paramsList__item-appQw"]') if 'Площадь:' in e.text]
        ad_area = ad_area_found_list[0] if ad_area_found_list else ad_name
        
        # коммуникации
        ad_descr = driver.find_element(By.XPATH, '//div[@data-marker="item-view/item-description"]').text.lower()
        electric = 'Упоминаеться' if re.search('электр', ad_descr) else 'Не указано'
        gaz = 'Упоминаеться' if re.search('газ', ad_descr) else 'Не указано'
        sewarage = 'Упоминаеться' if re.search('канализа', ad_descr) else 'Не указано'
        water = 'Упоминаеться' if re.search('вод[ао]', ad_descr) else 'Не указано'

        # собираем номер телефона (после открытия телефооного банера, элементы ктегорий не видимы становяться)
        # поэтом парсинг телефона после категорий (в поледнюю очередь!!!)
        try:
            # Наводим курсор на кнопку телефона и нажимаем на нее для отображения картинки с номером телефона
            button_phone = driver.find_element(By.XPATH, '//button[@data-marker="item-phone-button/card"]')
            sleep(2)
            ActionChains(driver).move_to_element(button_phone).click(button_phone).perform()

            # Скачиваем img с номерами телефонов и кладем в папку "phone_num_imgs", проверив, есть ли она
            num_img_url = driver.find_element(By.XPATH, '//img[@data-marker="phone-popup/phone-image"]').get_attribute("src")
            if not os.path.exists("phone_num_imgs"):
                os.mkdir("phone_num_imgs")
            urllib.request.urlretrieve(num_img_url, f"phone_num_imgs/phone_img.png")

            # Открываем картинку с помощью PIL
            img = Image.open(f"phone_num_imgs/phone_img.png")

            # Распознаем текст телефона с картинки с помощью tesseract
            # custom_config = r"--oem3 --psm13"  # Настройки для tesseract, эти по сути автоматические https://help.ubuntu.ru/wiki/tesseractб, oem3 это это режим работы движка, он и так по умолчанию 3, но вот остальные режимы: 0 = Original Tesseract only. 1 = Neural nets LSTM only. 2 = Tesseract + LSTM. 3 = Default, based on what is available.
            phone_num = pytesseract.image_to_string(img).replace("\n", "")
            os.remove(f"phone_num_imgs/phone_img.png")
        except Exception as ex:
            print(ex)
            phone_num = "Не получилось выгрузить номер телефона"

        # Добавляем все сведения из объявления  в словарь
        ad_dict_new = {
            "ad_name": ad_name,
            'ad_area': ad_area,
            'ad_id': ad_id,
            "ad_link": ad_url,
            "ad_total_price": ad_price,
            'ad_type_company': ad_company_type,
            'gaz': gaz,
            'water': water,
            'sewarage': sewarage,
            'electric': electric,
            "ad_unit_price": ad_unit_price,
            "ad_address": ad_address,
            "ad_date_created": ad_publ_time,
            'ad_total_views': ad_total_views,
            "ad_phone": phone_num,
            'parse_timestamp': str(datetime.now().strftime(TIMESTAMP_DT_FORMAT)),
        }
        if not any([ad_dict_new['ad_id'] == ad_d['ad_id'] for ad_d in collected_ads]):
            print(ad_dict_new)
            collected_ads.append(ad_dict_new)
        # Переключаемся обратно на основное вкладка
        driver.switch_to.window(driver.window_handles[0])


def avito_parse(driver: ChromeDriver, region_id):
    # LOGGING INFO
    logging.info(f'start avito parsing, region_id: {region_id}')

    # start function
    collected_ads = []    # container ads
    ex = ''   # Doesnt have any exceptions on start function

    page_url = f'https://www.avito.ru/{region_id}/zemelnye_uchastki?cd=1&p=1'
    for page_n in range(1, 5_000):   
        if page_n > 1:
            page_url = page_url.replace(f'&p={page_n-1}', f'&p={page_n}')
        
        # collect current (first) page and replace to 2 3 4 5...
        print(f'[*]Get - {page_url}')
        avito_driver_get_handler(driver, page_url)

        # LOGGING INFO
        logging.info(f'success get and handling page on captcha - {page_url}')

        # scroll down
        body = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body')))
        body.send_keys(Keys.END)
        body.send_keys(Keys.END)

        # LOGGING INFO
        logging.info('Scroll page to down')
        
        # check that page is exists
        try:
            if page_n > 1:
                WebDriverWait(driver, 3, poll_frequency=1).until(
                    EC.url_contains(f'&p={page_n}')
                )
        except TimeoutException:
            # LOGGING INFO
            logging.info('get timeout exception for wait page')
            return [collected_ads, ex]
        # Все объявления на странице
        # Счетчик для нумерации файлов с номером телефона
        try:
            avito_ads_parse(driver, collected_ads)
        except Exception as ex:
            # LOGGING INFO
            logging.error(f'get error for avito_ads_parse function - {ex}')
            return [collected_ads, ex]
    
    # LOGGING INFO
    logging.info('success end parsing for avito')
    return [collected_ads, ex]

def cian_convert_date(date_string):
    # Словарь для перевода названий месяцев
    months = {
        'янв': 1,
        'фев': 2,
        'мар': 3,
        'апр': 4,
        'май': 5,
        'июн': 6,
        'июл': 7,
        'авг': 8,
        'сен': 9,
        'окт': 10,
        'ноя': 11,
        'дек': 12
    }

    # Разбиваем строку на дату и время
    date, time = date_string.split(', ')
    hours, mins = [int(n) for n in time.split(':')]

    # Если в строке указано "сегодня" или "сегодня", то возвращаем текущую дату или вчерашнюю
    # время оставляем из строки
    if 'сегодня' in date:
        now = datetime.now()
        target_date = datetime(now.year, now.month, now.day, hours, mins)
    elif 'вчера' in date:
        now = datetime.now() - timedelta(days=1)
        target_date = datetime(now.year, now.month, now.day, hours, mins)
    else:
        # Разбиваем дату на день и месяц
        day, month = date.split(' ')
        # Получаем номер месяца из словаря
        month_number = months[month]
        # Возвращаем дату и время в формате YYYY-MM-DD HH:MM
        target_date = datetime(datetime.now().year, month_number, int(day), hours, mins)
    return target_date.strftime('%Y-%m-%d %H:%M')



def avito_convert_date(date_string):
    # Словарь для перевода названий месяцев
    months = {
        'января': 1,
        'февраля': 2,
        'марта': 3,
        'апреля': 4,
        'мая': 5,
        'июня': 6,
        'июля': 7,
        'августа': 8,
        'сентября': 9,
        'октября': 10,
        'ноября': 11,
        'декабря': 12
    }

    date_string = date_string.replace('· ', '')

    # Разбиваем строку на дату и время
    date, time = date_string.split(' в ')
    hours, mins = [int(re.search('\d+', n)[0]) for n in time.split(':')]

    # Если в строке указано "сегодня" или "сегодня", то возвращаем текущую дату или вчерашнюю
    # время оставляем из строки
    if 'сегодня' in date:
        now = datetime.now()
        target_date = datetime(now.year, now.month, now.day, hours, mins)
    elif 'вчера' in date:
        now = datetime.now() - timedelta(days=1)
        target_date = datetime(now.year, now.month, now.day, hours, mins)
    else:
        # Разбиваем дату на день и месяц
        day, month = date.split(' ')
        # Получаем номер месяца из словаря
        month_number = months[month]
        # Возвращаем дату и время в формате YYYY-MM-DD HH:MM
        target_date = datetime(datetime.now().year, month_number, int(day), hours, mins)
    return target_date.strftime('%Y-%m-%d %H:%M')



def update_total_csv(ads_data: list, fn):
    csv_ads_id = []
    if os.path.exists(fn):
        with open(fn, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            csv_ads_id = [str(row['ad_id']) for row in reader]
    
    # LOGGING INFO
    logging.info(f'Finish read total csv (ads id) - {csv_ads_id}')

    # process ads_data
    process_ads_data = ads_data.copy()
    for ad in process_ads_data:
        del ad['parse_timestamp']

    # LOGGING INFO
    logging.info(f'finish process ads_data - {[process_ads_data]}')
    
    # Сохранение данных в CSV файл
    with open(fn, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=process_ads_data[0].keys())
        
        # записать заголовки если файл новый
        if not csv_ads_id:
            writer.writeheader()

        # Write new data only if 'ad_id' not in csv_ads_id
        for ad in process_ads_data:
            if str(ad['ad_id']) not in csv_ads_id:
                writer.writerow(ad)
    
    # LOGGING INFO
    logging.info(f'finish saved total csv')


def read_history_csv(fn):
    data = []
    if os.path.exists(fn):
        with open(fn, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            try:
                header = next(reader)  # Skip the header row
            except StopIteration:
                return data
    
            for key, group in groupby(reader, key=lambda row: row[0]):
                ad_data = {'ad_id': key, 'prices': [], 'views': []}
                for row in group:
                    parse_timestamp, ad_total_price, ad_total_views = row[1:]
                    if ad_total_price:
                        ad_data['prices'].append({'timestamp': parse_timestamp, 'ad_total_price': ad_total_price})
                    if ad_total_views:
                        ad_data['views'].append({'timestamp': parse_timestamp, 'ad_total_views': int(ad_total_views)})
                data.append(ad_data)
    return data


def update_history_csv(ads_data, fn):
    existing_ads = read_history_csv(fn)

    # LOGGING INFO
    logging.info(f'read existings_ads - {existing_ads}')
    logging.info(f'start update history csv')

    # update existing ads
    for ad in ads_data:
        # LOGGING INFO
        logging.info(f'get ad - {ad}')


        ad_id = ad['ad_id']
        
        existing_ad = next((existing_ad for existing_ad in existing_ads if str(existing_ad['ad_id']) == str(ad_id)), None)

        if existing_ad:
            # Update existing ad with new prices and views
            existing_ad['prices'].insert(0, {'ad_total_price': ad['ad_total_price'], 'timestamp': ad['parse_timestamp']})
            existing_ad['views'].insert(0, {'ad_total_views': ad['ad_total_views'], 'timestamp': ad['parse_timestamp']})
        else:
            # Add new ad
            ad_dict = {
                'ad_id': ad_id, 
                'prices': [{'ad_total_price': ad['ad_total_price'], 'timestamp': ad['parse_timestamp']}], 
                'views': [{'ad_total_views': ad['ad_total_views'], 'timestamp': ad['parse_timestamp']}]
            }
            existing_ads.append(ad_dict)
    
    # LOGGING INFO
    logging.info(f'Finish building existing ads - {existing_ads}')
        
    
    # Write the existing ads rows
    with open(fn, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)

        # write headers because we rewrite ads
        writer.writerow(['ad_id', 'timestamp', 'ad_total_price', 'ad_total_views'])

        # Write the updated data to the file
        for ad in existing_ads:
            ad_id = ad['ad_id']
            
            # Extract and write price history
            for price, view in zip(ad.get('prices'), ad.get('views', [])):
                timestamp = price['timestamp']
                assert price['timestamp'] == view['timestamp'], f'View timestamp and price timestamp is not equal (ad_id - {ad_id})'
                ad_total_views = view['ad_total_views']
                ad_total_price = price['ad_total_price']
                ad_data = [ad_id, timestamp, ad_total_price, ad_total_views]
                writer.writerow(ad_data)
    
    # LOGGING INFO
    logging.info(f'Finish writing existings ads')



def sleep_to_point(point: datetime):
    ''' sleep program until not target time (point) '''
    
    get_remaining_secs = lambda: (
        point - datetime.now()).total_seconds()
    
    units = [(3600, 'hours'), (60, 'minutes'), (1, 'seconds')]
    for unit, name in units:
        units_count = 1
        while units_count > 0:
            remaining_sec = get_remaining_secs()
            units_count = (remaining_sec // unit)
            if units_count > 0:
                # print('*sleep*')
                sleep(unit if name != 'seconds' else units_count)


def main():
    while True:
        # (next program run in the 22:00)
        msg = f'Начало работы парсера'
        logging.info(msg)

        # check exceptions and send emails about it
        exceptions_msg = ''
    
        # set ocr tesseract path
        if not os.path.exists(TESSERACT_OCR_PATH):
            msg = f'EXCEPTION WITH FIND OCR_TESSERACT:\nProgramm was not found tesseract ocr .exe file ;(\n'
            print(msg)
            exceptions_msg += msg
            logging.error(msg)
        else:
            # save ocr path and start parsing
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_OCR_PATH
            
            with RootChromeDriver()._init_local_driver() as driver:
                # parsing moskow and MO
                
                # avito
                avito_parsed = []
        
                try:
                    parsed_result = avito_parse(driver, AVITO_REGIONS['Москва и МО'])   
                except Exception as ex:
                    parsed_result = [[], f'AVITO REGION - [Москва и МО] GET EXCEPTION\n{ex}\n']
                else:
                    ex = parsed_result[1]
                    if ex:
                        parsed_result[1] = f'AVITO REGION - [Москва и МО] GET EXCEPTION\n{ex}\n'
                finally:
                    avito_parsed.append(parsed_result)
                
                # unpack avito_parsed
                try:
                    avito_ads = []
                    for ads, ex_str in avito_parsed:
                        avito_ads += ads
                        if ex_str:
                            exceptions_msg += ex_str
                except Exception as ex:
                    msg = f'\nEXCEPTION WITH UNPACK AVITO PARSED DATA\n{ex}\n'
                    exceptions_msg += msg
                    logging.error(msg)
                
                # cian

                # create cian parsed for moskow and MO
                cian_parsed = []
                
                # extend cian parsed for Москва
                try:
                    parsed_result = cian_parse(driver, CIAN_REGIONS['Москва'])
                except Exception as ex:
                    parsed_result = [[], f'CIAN REGION - [Москва] GET EXCEPTION\n{ex}\n']
                else:
                    ex = parsed_result[1]
                    if ex:
                        parsed_result[1] = f'CIAN REGION - [Москва] GET EXCEPTION\n{ex}\n'
                finally:    
                    cian_parsed.append(parsed_result)
                
                # extend cian parsed for MO
                try:
                    parsed_result = cian_parse(driver, CIAN_REGIONS['Московская область'])
                except Exception as ex:
                    parsed_result = [[], f'CIAN REGION - [Московская область] GET EXCEPTION\n{ex}\n']
                else:
                    ex = parsed_result[1]
                    if ex:
                        parsed_result[1] = f'CIAN REGION - [Московская область] GET EXCEPTION\n{ex}\n'
                finally:
                    cian_parsed.append(parsed_result)
        
                # unpack cian_parsed
                try:
                    cian_ads = []
                    for ads, ex_str in cian_parsed:
                        cian_ads += ads
                        if ex_str:
                            exceptions_msg += ex_str
                except Exception as ex:
                    msg += f'\nEXCEPTION WITH UNPACK CIAN PARSED DATA\n{ex}\n'
                    exceptions_msg += msg
                    logging.error(msg)

            # write msg about found ads
            logging.info(f'Found avito - {len(avito_ads)}')
            logging.info(f'Found cian - {len(cian_ads)}')
            if exceptions_msg:
                logging.error(f'Exceptions after parsing and unpacking - {exceptions_msg}')
            
            # update prices and views history     
            try:
                update_history_csv(cian_ads, CIAN_HISTORY_CSV_FN)
                update_history_csv(avito_ads, AVITO_HISTORY_CSV_FN)
            except Exception as ex:
                ex_msg = f'\nEXCEPTION WITH UPDATE HISTORY CSV FILES - {ex}\n'
                exceptions_msg += ex_msg
                logging.error(ex_msg)
            else:
                msg = 'History csv for cian and avito was updated!'
                logging.info(msg)
           
            # update total ads
            try:
                update_total_csv(cian_ads, CIAN_TOTAL_CSV_FN)
                update_total_csv(avito_ads, AVITO_TOTAL_CSV_FN)
            except Exception as ex:
                ex_msg = f'\nEXCEPTION WITH UPDATE TOTAL CSV FILES - {ex}\n'
                exceptions_msg += ex_msg
                logging.error(ex_msg)
            else:
                msg = 'Total csv for cian and avito was updated!'
                logging.info(msg)
     
        # send msg about errors
        if exceptions_msg:
            try:
                send_email_errors = send_email_msg(
                    subject_msg=ERROR_NOTIFICATION_SUBJECT, 
                    send_from=MAIL_LOGIN, password=MAIL_PASSWORD,
                    send_to=MAIL_SEND_TO, body_msg=exceptions_msg
                )
            except Exception as ex:
                msg = '\nEXCEPTION WITH SENDING EMAIL MESSAGE!\n'
                logging.info(msg)
            else:
                logging.info('Sending email was completed')
                if send_email_errors:
                    logging.error(str(send_email_errors))
        
        # next program run in the 22:00
        next_time_point = datetime.combine(datetime.now().date(), time(22, 0, 0))
        if next_time_point < datetime.now():
            next_time_point += timedelta(days=1)

        msg = f'Завершение работы парсера, следующий запуск в [{str(next_time_point)}]'
        print(msg)
        logging.info(msg)

        # sleep to point 22:00 today or tommorow 
        sleep_to_point(next_time_point)

if __name__ == '__main__':
    main()
