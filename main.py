import logging
import re
import os
from random import randrange
from datetime import datetime, timedelta, time
from itertools import groupby
from time import sleep
import csv
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.request
# import threading
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
# from concurrent.futures import as_completed

# from hcaptcha_solver import hcaptcha_solver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (NoSuchElementException, TimeoutException)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup as BS
import pytesseract
from PIL import Image

from root_chromedriver import RootChromeDriver
from cfg import * 


# SETUP
# create logger
logging.basicConfig(
    filename='execution.log', level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8')


# parsed links
AVITO_PARSED_URLS = []
CIAN_PARSED_URLS = []

# create errors container
ERRORS_CONTAINER = []

# correct count parallel browsers
NUM_PARALLEL_BROWSERS = NUM_PARALLEL_BROWSERS if NUM_PARALLEL_BROWSERS <= MAX_PAGES_COUNT else MAX_PAGES_COUNT

# cerate executor for async parsing
# THREADING_LOCK = threading.Lock()
THREAD_POOL_EXECUTOR = ThreadPoolExecutor(max_workers=NUM_PARALLEL_BROWSERS) 
ASYNCIO_EVENT_LOOP = asyncio.get_event_loop()


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


def cian_ad_parse(ad_url, rootdriver, collected_ads):
    global CIAN_PARSED_URLS
    
    if ad_url in CIAN_PARSED_URLS:
        return
    sleep(randrange(1, 6))

    # open ad page
    rootdriver.get(ad_url)

    # LOGGER INFO
    logging.info(f'loaded cian ad - {ad_url}')

    # get phones
    phones = ''
    
    try:
        # accept cookis for click button phone
        # try:
        #     WebDriverWait(rootdriver, timeout=5).until(
        #         EC.presence_of_element_located((By.CLASS_NAME, "_25d45facb5--container--zRDqi"))
        #     ).click()
        # except Exception as ex:
        #     pass
        # else:
        #     logging.info('accept cookies')
        
        # # close div which blocked phone button
        # try:
        #     WebDriverWait(rootdriver, timeout=3).until(
        #         EC.presence_of_element_located((By.XPATH, "//div[@class='_25d45facb5--content--UaWj0']"))
        #     ).click()
        # except Exception as ex:
        #     pass
        # else:
        #     logging.info('close div which blocked phone button')
        
        # close dialog
        try:
            WebDriverWait(rootdriver, timeout=3).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="dialog"]//span[text()="Принять"]'))
            ).click()
        except Exception as ex:
            pass
        else:
            logging.info('close dialog')

        WebDriverWait(rootdriver, timeout=10, poll_frequency=1).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="contacts-button"]'))
        ).click()
        phones_elems = WebDriverWait(rootdriver, timeout=4, poll_frequency=1).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[@data-name="Phones"]//div'))
        )
        phones_text = (e.text for e in phones_elems)
        phones = ' | '.join(phones_text)
    except Exception as ex:
        logging.error(f'error get phone: {ex}')

    
    html = rootdriver.page_source
    soup = BS(html, 'html.parser')

    title = soup.find('div', attrs={'data-name': 'OfferTitleNew'}).text
    id_ = ad_url.split('suburban/')[1].replace('/', '')
    type_company = soup.find('div', attrs={'data-name': 'AuthorAside'}).text.strip()
    price = soup.find('div', attrs={'data-testid': 'price-amount'}).text.strip().replace('\xa0', ' ')
    additional_address = soup.find('div', attrs={'data-id': 'content'}).text.replace('\n', ' | ')
    main_address = soup.find('div', attrs={'data-name': 'AddressContainer'}).text.replace('\n', ' | ')
    address = 'DESCRIPTION ADDRESS --> | ' + additional_address + ' | MAIN ADDRESS --> | ' + main_address

    # коммуникации
    electric = 'Не указано'
    gaz = 'Не указано'
    sewarage = 'Не указано'
    water = 'Не указано'
    area = 'Не указано'


    date_created_text = rootdriver.find_element(By.XPATH, '//div[@data-testid="metadata-added-date"]').text
    date_created = date_created_text.split('Обновлено:')
    if len(date_created) > 1:
        date_created = date_created[1].strip()
        date_created = cian_convert_date(date_created)
    else:
        date_created = date_created[0].strip()
    try:
        views_data = rootdriver.find_element(By.XPATH, '//button[@data-name="OfferStats"]').text
    except NoSuchElementException:
        return collected_ads
    else:
        total_views, today_views = views_data.split(', ')
        total_views, today_views = int(''.join(re.findall(r'\d+', total_views))), int(''.join(re.findall(r'\d+', today_views)))
        
    card_html = rootdriver.page_source
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
        'ad_phone': phones,
        'ad_link': ad_url,
        'ad_date_created': date_created,
        'electric': electric,
        'gaz': gaz,
        'water': water,
        'sewarage': sewarage,
        'parse_timestamp': str(datetime.now().strftime(TIMESTAMP_DT_FORMAT)),
    }
    if not any([dict_card['ad_id'] == dict_2_card['ad_id'] for dict_2_card in collected_ads]):
        print(dict_card)
        CIAN_PARSED_URLS.append(ad_url)
        collected_ads.append(dict_card)
        logging.info(str(dict_card))


def cian_parse_ads(page_n, page_url, collected_ads):
    try:
        with RootChromeDriver().get_rootdriver() as rootdriver:
            # logging.info('start rootdriver')

            # collect current (first) page and replace to 2 3 4 5...
            msg = f'[*]Get - {page_url}'
            print(msg)
            logging.info(msg)
    
            rootdriver.get(page_url)
        
            # scroll down
            body = WebDriverWait(rootdriver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body')))
            body.send_keys(Keys.END)
            body.send_keys(Keys.END)
        
            logging.info(f'Scroll page to down - {page_url}')
        
            # check that page is exists
            # check that page is not 1 if we have => page_n > 1 
            if page_n > 1:
                try:
                    WebDriverWait(rootdriver, 3, poll_frequency=1).until(
                       lambda d: int(re.findall(r'&p=(\d+)', d.current_url)[0]) == 1 if re.findall(r'&p=(\d+)', d.current_url) else False  
                    )
                except TimeoutException:
                    pass
                else:
                    logging.info(f'get timeout exception for wait page (in the end) - {page_url}')
                    return False
            
            # start page parse 
            logging.info(f'start cian parse ads on page - {page_url}')
            
            # wait ads loading
            WebDriverWait(rootdriver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//div[@data-testid="offer-card"]'))
            )
            
            # get ad urls
            ads_urls = []
            ads_urls_elems = WebDriverWait(rootdriver, timeout=15).until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, '//div[@class="_93444fe79c--wrapper--W0WqH"]//article[@data-name="CardComponent"]//a[@class="_93444fe79c--link--VtWj6"]'))
            )
            for e in ads_urls_elems:
                ads_urls.append(
                    e.get_attribute('href')
                )
            # convert to list
            # ads_urls = list(ads_urls)
            logging.info(f'collect ads urls - {len(ads_urls)} - ({page_url})')
    
            # parse ads urls
            
            
            try:
                for ad_url in ads_urls:
                    cian_ad_parse(ad_url, rootdriver, collected_ads)
            except Exception as ex:
                ex_msg = f'ERROR cian_ad_parse FUNCTION - {ex} ({page_url})'
                handle_global_error(ex_msg)
                ads_parse_result = True   # error point
            else:
                ads_parse_result = True
            finally:
                logging.warning('close rootdriver')
                return ads_parse_result
    except Exception as ex:
        # handle error
        ex_msg = f'ERROR PARSE CIAN ADS FUNCTION (FOR EVERY PAGE), page_url - [{page_url}], exception - [{ex}]'
        handle_global_error(ex_msg)
        return True   # error point


def cian_parse(region_id: str, executor=None, loop=None):
    logging.info(f'cian parse start function, region_id - {region_id}')

    region_id = str(region_id)
    collected_ads = []    # container ads

    # we have a first page => &p=1
    # init page urls with page_nums
    page_urls = []

    async def scrape(page_n_list, page_url_list, collected_ads, executor, loop):
        tasks = []
        for page_n, page_url in zip(page_n_list, page_url_list):
            tasks.append(
                loop.run_in_executor(executor, cian_parse_ads, page_n, page_url, collected_ads)
            )
        results = await asyncio.gather(*tasks)
        last_page_flag = not all(results)
        return last_page_flag


    # generate urls
    page_url = f'https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&object_type%5B0%5D=3&offer_type=suburban&p=1&region={region_id}'
    for page_n in range(1, MAX_PAGES_COUNT):
        if page_n > 1:
            page_url = page_url.replace(f'&p={page_n-1}', f'&p={page_n}')
        page_urls.append(
            [page_url, page_n])
    
    # for page_urls_group in split_list(page_urls, NUM_PARALLEL_BROWSERS):
    #     for page_url, page_n in page_urls_group:
    #         threads = []
    #         # for url in urls:
    #         thread = threading.Thread(target=cian_parse_ads, args=(page_n, page_url, collected_ads))
    #         threads.append(thread)
    #         thread.start()
        
    #     for thread in threads:
    #         thread.join()
            
            # collect ads for every page
            # cian_parse_ads(page_n, page_url, collected_ads)
    
    # process_pages(page_urls, collected_ads)
            
    for page_urls_group in split_list(page_urls, NUM_PARALLEL_BROWSERS):
        # unpack group and send to loop
        page_n_list = [group[1] for group in page_urls_group]
        page_url_list = [group[0] for group in page_urls_group]
        
        last_page_flag = loop.run_until_complete(
            scrape(page_n_list, page_url_list, collected_ads, executor, loop))
        if last_page_flag:
            break

    logging.info(f'success end parsing for cian, region - {region_id}')
    return collected_ads


def avito_driver_get_handler(rootdriver, url, target_elems_xpath):
    # captcha_flag = True
    # while captcha_flag:
    for _ in range(10):
        try:
            rootdriver.get(url)
        except Exception as ex:
            ex_msg = f'exception with get page in the avito_driver_get_handler - {ex}'
            print(ex_msg)
            logging.error(ex_msg)
            # and continue next code block (change ip) ...
        else:
            try:
                WebDriverWait(rootdriver, timeout=15).until(EC.presence_of_all_elements_located((By.XPATH, target_elems_xpath)))
            except TimeoutException:
                # try to find catpcha
                try:
                    WebDriverWait(rootdriver, timeout=7, poll_frequency=2).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@class='h-captcha']/iframe"))
                    )
                except TimeoutException:
                    pass
            else:
                return
        # change ip, we have problems
        try:
            rootdriver._urban_get_ip()
        except Exception as ex:
            ex_msg = f'ERROR URBAN GET IP - {ex}'
            logging.error(ex_msg)
            # sleep(randrange(5, 10))
            # handle_global_error(ex_msg)
    raise ValueError('target elems was not found')


# def solving_avito_captcha(rootdriver):
#     print('[!]hCaptcha detected!, solving...')
#     submit_btn = WebDriverWait(rootdriver, timeout=3).until(
#         EC.presence_of_element_located((By.XPATH, '//button[@type="submit"]'))
#     )
#     x, y = submit_btn.location['x'], submit_btn.location['y']
#     action_chains = ActionChains(rootdriver)
#     action_chains.move_to_element_with_offset(submit_btn, x, y)

#     solver = hcaptcha_solver.Captcha_Solver(verbose=True)
#     # captcha_is_present = solver.is_captcha_present()
#     # print(f'Captcha is present flag - {captcha_is_present}\nSolving...')
#     try:
#         solver.solve_captcha(rootdriver)
#     except (ElementClickInterceptedException, TimeoutException):
#         pass
#     # except Exception as ex:
#     #     print(f'ERROR SOLVE CAPTCHA FUNC - {ex}')
#     #     logging.error(f'ERROR SOLVER.SOLVE_CAPTCHA FUNC - {ex}')
#     #     return
#     action_chains.click().perform()



def avito_ad_parse(rootdriver, ad_url, collected_ads):
    global AVITO_PARSED_URLS

    if ad_url in AVITO_PARSED_URLS:
        return False
    # process captcha and wait next elem of target url
    avito_driver_get_handler(rootdriver, ad_url, "//span[@class='style-price-value-string-rWMtx']")
    # rootdriver.get(ad_url)

    # wait load ad elem
    # wait load price elem of ad
    
    # render html, get soup
    html = rootdriver.page_source
    soup = BS(html, 'html.parser')
    
    ad_price = soup.find('span', class_='style-price-value-string-rWMtx').text.strip().replace('\xa0', ' ')
    # ad_name = soup.find('div', class_='style-titleWrapper-Hmr_5').find('h1').text.strip().replace('\xa0', ' ')
    ad_name = soup.find('h1', attrs={'data-marker': 'item-view/title-info'}).text.strip().replace('\xa0', ' ')
    ad_unit_price_elem = soup.find('div', class_='style-item-price-sub-price-_5RUD')

    if ad_unit_price_elem:
        ad_unit_price = ad_unit_price_elem.text.strip().replace('\xa0', ' ')
        if 'залог' in ad_unit_price:
            ad_unit_price = 'Нет удельной цены'
    else:
        ad_unit_price = 'Нет удельной цены'

    # собираем доп инфу
    ad_address = soup.find('div', attrs={'itemprop': 'address'}).text.strip().replace('\n', '|')
    ad_id = soup.find('span', attrs={'data-marker': 'item-view/item-id'}).text
    ad_id = re.search('\d+', ad_id)[0]
    ad_company_type = soup.find('div', attrs={'data-marker': 'seller-info/label'}).text
    ad_publ_time = soup.find('span', attrs={'data-marker': 'item-view/item-date'}).text
    ad_publ_time = avito_convert_date(ad_publ_time)
    ad_total_views = soup.find('span', attrs={'data-marker': 'item-view/total-views'}).text
    ad_total_views = int(re.search('\d+', ad_total_views)[0])
    ad_today_views = soup.find('span', attrs={'data-marker': 'item-view/today-views'}).text
    ad_today_views = int(re.search('\d+', ad_today_views)[0])
    
    # собираем инфу с категорий снизу
    ad_area_found_list = [e.text.replace('Площадь:', '').strip().replace('\xa0', '') for e in 
                          soup.find_all('li', class_='params-paramsList__item-appQw') if 'Площадь:' in e.text]
    # ad_area_found_list = [e.text.replace('Площадь:', '').strip() for e in 
    #                       rootdriver.find_elements(By.XPATH, '//li[@class="params-paramsList__item-appQw"]') if 'Площадь:' in e.text]
    ad_area = ad_area_found_list[0] if ad_area_found_list else ad_name
    
    # коммуникации
    ad_descr = soup.find('div', attrs={'data-marker': 'item-view/item-description'}).text.lower()
    # ad_descr = rootdriver.find_element(By.XPATH, '//div[@data-marker="item-view/item-description"]').text.lower()
    
    electric = 'Упоминаеться' if re.search('электр', ad_descr) else 'Не указано'
    gaz = 'Упоминаеться' if re.search('газ', ad_descr) else 'Не указано'
    sewarage = 'Упоминаеться' if re.search('канализа', ad_descr) else 'Не указано'
    water = 'Упоминаеться' if re.search('вод[ао]', ad_descr) else 'Не указано'

    # собираем номер телефона (после открытия телефооного банера, элементы ктегорий не видимы становяться)
    # поэтом парсинг телефона после категорий (в поледнюю очередь!!!)
    try:
        # Наводим курсор на кнопку телефона и нажимаем на нее для отображения картинки с номером телефона
        button_phone = WebDriverWait(rootdriver, timeout=5, poll_frequency=1).until(
            EC.presence_of_element_located((By.XPATH, '//button[@data-marker="item-phone-button/card"]'))
        )
        # sleep(2)
        ActionChains(rootdriver).move_to_element(button_phone).click(button_phone).perform()

        # Скачиваем img с номерами телефонов и кладем в папку "phone_num_imgs", проверив, есть ли она
        num_img_url = WebDriverWait(driver=rootdriver, timeout=4).until(EC.presence_of_element_located((By.XPATH, '//img[@data-marker="phone-popup/phone-image"]'))).get_attribute("src")
        # num_img_url = soup.find('img', attrs={'data-marker': 'phone-popup/phone-image'}).get("src")
        if not os.path.exists("phone_num_imgs"):
            os.mkdir("phone_num_imgs")
        
        img_path = f"phone_num_imgs/phone_img_{ad_id}.png"
        urllib.request.urlretrieve(num_img_url, img_path)

        # Открываем картинку с помощью PIL
        with Image.open(img_path) as img:
            # Распознаем текст телефона с картинки с помощью tesseract
            # custom_config = r"--oem3 --psm13"  # Настройки для tesseract, эти по сути автоматические https://help.ubuntu.ru/wiki/tesseractб, oem3 это это режим работы движка, он и так по умолчанию 3, но вот остальные режимы: 0 = Original Tesseract only. 1 = Neural nets LSTM only. 2 = Tesseract + LSTM. 3 = Default, based on what is available.
            phone_num = pytesseract.image_to_string(img).replace("\n", "")
        
        # удаляем картинку
        if os.path.exists(img_path):
            os.remove(img_path)
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
        AVITO_PARSED_URLS.append(ad_url)
        logging.info(str(ad_dict_new))
    return True


def avito_ads_parse(ads_urls, rootdriver, collected_ads):
    for ad_url in ads_urls:
        try:
            # if ad parse success we get True
            if not avito_ad_parse(rootdriver, ad_url, collected_ads):
                return False
            # ads_parse_results += 
            sleep(randrange(1, 6))
        except Exception as ex:
            ex_msg = f'ERROR avito_ads_parse FUNCTION - {ex} ({ad_url})'
            handle_global_error(ex_msg)
            return True   # error point
    return True


def avito_parse(region_id, loop=None, executor=None):
    logging.info(f'start avito parsing, region_id: {region_id}')

    # start function
    collected_ads = []    # container ads

    async def scrape(page_n_list, page_url_list, collected_ads, executor, loop):
        tasks = []
        for page_n, page_url in zip(page_n_list, page_url_list):
            tasks.append(
                loop.run_in_executor(executor, process_page, page_n, page_url, collected_ads)
            )
    
    #     # for future in as_completed(tasks):
    #     #     try:
    #     #         future.result()
    #     #     except Exception as ex:
    #     #         print(f'future exception - {ex}')
    #     #         continue
        results = await asyncio.gather(*tasks)
        last_page_flag = not all(results)
        return last_page_flag
        

    def process_page(page_n, page_url, collected_ads):
        try:
            with RootChromeDriver().get_rootdriver() as rootdriver:
                # logging.info('start root driver')
                
                msg = f'[*]Get - {page_url}'
                print(msg)
                logging.info(msg)
    
                # process captcha and wait next elem of target url
                avito_driver_get_handler(rootdriver, page_url, '//div[@data-marker="item"]')
                    
                # logging.info(f'success get and handling page on captcha - {page_url}')
                
                # scroll down
                body = WebDriverWait(rootdriver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body')))
                body.send_keys(Keys.END)
                body.send_keys(Keys.END)
                
                # logging.info(f'Scroll page to down - [{page_url}]')
                
                # check that page is exists
                on_next_page_flag = True
                if page_n > 1:
                    # try:
                    if rootdriver.current_url.find('&p=') == -1:
                        on_next_page_flag = False
                    
                    else:
                        current_page_num = int(re.findall(r'&p=(\d+)', rootdriver.current_url)[0])
                        if current_page_num == 1:
                            on_next_page_flag = False

                        # WebDriverWait(rootdriver, 3, poll_frequency=1).until(
                        #    lambda d: int(re.findall(r'&p=(\d+)', d.current_url)[0]) == 1 if re.findall(r'&p=(\d+)', d.current_url) else False
                        # )
                    # except TimeoutException:
                    #     pass
                    # else:
                if not on_next_page_flag:
                    logging.info(f'get timeout exception for wait page (in the end) - {page_url}')
                    return False
        
                # collect and wait ads for load ads elems
                WebDriverWait(rootdriver, timeout=20).until(
                    EC.presence_of_all_elements_located((By.XPATH, '//div[@data-marker="item"]'))
                )
                
                # collect ad urls
                ads_urls = []
                try:
                    for ad_num in range(1, AVITO_ADS_ON_ONE_PAGE):
                        ad_url = WebDriverWait(driver=rootdriver, timeout=3).until(
                            EC.presence_of_element_located(
                                (By.XPATH, f'//div[@data-marker="item"][{ad_num}]//a[@data-marker="item-title"]'))).get_attribute("href")
                        ads_urls.append(ad_url)
                except TimeoutException:
                    if ads_urls == 0:
                        return False
                
                # logging.info(f'collect ads_count - {ads_count}')
                logging.info(f'collected urls count - {len(ads_urls)} - ({page_url})')
            
                # true or false
                result_ads_parse = avito_ads_parse(ads_urls, rootdriver, collected_ads)
        except Exception as ex:
            # handle error
            ex_msg = f'ERROR PARSE AVITO ADS FUNCTION (FOR EVERY PAGE), page_url - [{page_url}], exception - [{ex}]'
            handle_global_error(ex_msg)
            result_ads_parse = True   # error point
        finally:
            logging.warning('close rootdriver')
            return result_ads_parse
        
    # create page urls 
    page_urls = []

    page_url = f'https://www.avito.ru/{region_id}/zemelnye_uchastki?cd=1&p=1'
    for page_n in range(1, MAX_PAGES_COUNT):
        if page_n > 1:
            page_url = page_url.replace(f'&p={page_n-1}', f'&p={page_n}')
        page_urls.append(
            [page_url, page_n])
    
    # start process urls (pages)
    # process pages
    # for page_urls_group in split_list(page_urls, NUM_PARALLEL_BROWSERS):
    #     for page_url, page_n in page_urls_group:
    #         threads = []
    #         # for url in urls:
    #         thread = threading.Thread(target=process_page, args=(page_n, page_url, collected_ads))
    #         threads.append(thread)
    #         thread.start()
        
    #     for thread in threads:
    #         thread.join()

    
    # logging.info(f'success end parsing for avito, region {region_id}')
    # return collected_ads
        
    # process_pages(page_urls, collected_ads)

    for page_urls_group in split_list(page_urls, NUM_PARALLEL_BROWSERS):
        # unpack group and send to loop
        page_n_list = [group[1] for group in page_urls_group]
        page_url_list = [group[0] for group in page_urls_group]
        
        last_page_flag = loop.run_until_complete(
            scrape(page_n_list, page_url_list, collected_ads, executor, loop))
        if last_page_flag:
            break
    logging.info(f'success end parsing for avito, region {region_id}')
    return collected_ads


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

    date_string = date_string.replace('· ', '').strip()

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
    if not ads_data:
        return

    csv_ads_id = []
    if os.path.exists(fn):
        with open(fn, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            csv_ads_id = [str(row['ad_id']) for row in reader]
    
    logging.info(f'read total csv - {fn}, ads id count - {len(csv_ads_id)}')
    
    # Сохранение данных в CSV файл
    with open(fn, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=ads_data[0].keys())
        
        # записать заголовки если файл новый
        if not csv_ads_id:
            writer.writeheader()

        # Write new data only if 'ad_id' not in csv_ads_id
        for ad in ads_data:
            if str(ad['ad_id']) not in csv_ads_id:
                writer.writerow(ad)
    
    logging.info(f'saved new data to total csv')


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

    logging.info(f'start update history csv for [{fn}]')

    # update existing ads
    for ad in ads_data:
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
    
    logging.info(f'Created existing ads')
        
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
    
    logging.info(f'Finished writing existings ads')



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

def history_csv_updater(ads, fn):
    # ex_msg = ''
    # update total ads for avito
    try:
        update_history_csv(ads, fn)
    except Exception as ex:
        ex_msg = f'ERROR UPDATE HISTORY CSV FILE - [{fn}], ERROR MESSAGE - [{ex}]'
        handle_global_error(ex_msg)
    else:
        msg = f'HISTORY csv for [{fn}] was updated!'
        logging.info(msg)
    # return ex_msg


def total_csv_updater(ads, fn):
    # ex_msg = ''
    # update total ads for avito
    try:
        update_total_csv(ads, fn)
    except Exception as ex:
        ex_msg = f'ERROR UPDATE TOTAL CSV FILE - [{fn}], ERROR MESSAGE - [{ex}]'
        handle_global_error(ex_msg)
    else:
        msg = f'Total csv for [{fn}] was updated!'
        logging.info(msg)
    # return ex_msg


def add_global_error_to_container(error: str):
    global ERRORS_CONTAINER
    ERRORS_CONTAINER.append(error)


def handle_global_error(error_msg):
    logging.error(error_msg)
    add_global_error_to_container(error_msg)



def split_list(input_list, chunk_size):
    """
    Разбивает список на подсписки заданного размера.

    Parameters:
    input_list (list): Исходный список.
    chunk_size (int): Размер подсписка.

    Returns:
    list: Список подсписков.
    """
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]


def main():
    # set ocr tesseract path
    if not os.path.exists(TESSERACT_OCR_PATH):
        ex_msg = f'ERROR FIND OCR_TESSERACT:\nProgramm was not found tesseract ocr .exe file ;('
        print(ex_msg)
        handle_global_error(ex_msg)
    else:
        # save ocr path and start parsing
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_OCR_PATH


    # Создаем цикл событий asyncio
    # loop = asyncio.get_event_loop()

    # Создаем пул потоков для параллельного выполнения асинхронных задач
    # executor = ThreadPoolExecutor(max_workers=5)
    

    while True:
        msg = 'Start Parsing Program'
        logging.info(msg)
            
        # with RootChromeDriver().get_rootdriver() as rootdriver:

        # -- AVITO --
        avito_ads = []

        avito_ads.extend(
            avito_parse(AVITO_REGIONS['Москва и МО'], executor=THREAD_POOL_EXECUTOR, loop=ASYNCIO_EVENT_LOOP)
        )
        logging.info(f'Found avito ads count - {len(avito_ads)}')

        # update prices and views history  - avito
        history_csv_updater(avito_ads, AVITO_HISTORY_CSV_FN)
        total_csv_updater(avito_ads, AVITO_TOTAL_CSV_FN)

        # -- CIAN --
        # create cian parsed for moskow and MO
        cian_ads = []
        
        # extend cian parsed for Москва
        cian_ads.extend(cian_parse(CIAN_REGIONS['Москва'], executor=THREAD_POOL_EXECUTOR, loop=ASYNCIO_EVENT_LOOP))
        # extend cian parsed for MO
        cian_ads.extend(cian_parse(CIAN_REGIONS['Московская область'], executor=THREAD_POOL_EXECUTOR, loop=ASYNCIO_EVENT_LOOP))
        logging.info(f'Found cian ads count - {len(cian_ads)}')

        # update prices and views history - cian
        total_csv_updater(cian_ads, CIAN_TOTAL_CSV_FN)
        history_csv_updater(cian_ads, CIAN_HISTORY_CSV_FN)
        

        # send msg about errors
        if ERRORS_CONTAINER:
            errors_container_str = '\n'.join(ERRORS_CONTAINER)
            try:
                send_email_errors = send_email_msg(
                    subject_msg=ERROR_NOTIFICATION_SUBJECT, 
                    send_from=MAIL_LOGIN, password=MAIL_PASSWORD,
                    send_to=MAIL_SEND_TO, body_msg=errors_container_str
                )
            except Exception as ex:
                msg = f'ERROR SENDING EMAIL MESSAGE! - {ex}'
                logging.error(msg)
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
