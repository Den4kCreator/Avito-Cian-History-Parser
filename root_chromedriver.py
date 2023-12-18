from time import sleep
from random import randrange

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (NoSuchElementException, TimeoutException, StaleElementReferenceException)
from selenium.webdriver import Chrome as ChromeDriver
# from selenium.webdriver import Remote as RemoteDriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions



class RootChromeDriver(ChromeDriver):
    ''' object for settings a chrome driver '''
    def __init__(self):
        # appdata_path = getenv('LOCALAPPDATA')
        # if appdata_path:
        #     self.profile_path = appdata_path + r'\Google\Chrome\User Data\ProfileDevTools'
        #     if not path_exists(self.profile_path):
        #         print('[!] ProfileDevTools doesn\'t exists, will be create new')
        #     else:
        #         print('[*] ProfileDevTools path was found (save the data after driver exit (cookie, passwords, history, profile info...))')
        # else:
        #     print('[*] ProfileDevTools path was build in the temp folder')
        #     self.profile_path = ''
        self.opts = ChromeOptions()
        self._set_my_config()   # setting opts

    def _set_extensions(self):
        # INIT URBAN SHIELD VPN
        if '--disable-extensions' in self.opts.arguments:
            print('[!]Delete "disable extensions" argument from chrome options')
            self.opts.arguments.remove('--disable-extensions')
        self.opts.add_extension(r'urban_shield_vpn_6_0_6.crx')
        
    def _set_my_config(self) -> None:
        ''' adding the params to self.opts object '''
        self.opts.add_argument("--headless=new")
        self.opts.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        self.opts.add_argument("--disable-notifications")
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument('--ignore-certificate-errors')
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--disable-blink-features=AutomationControlled")
        self.opts.add_argument("--disable-extensions")
        self.opts.add_argument("--disable-popup-blocking")
        self.opts.add_argument("--disable-plugins-discovery")
        self.opts.add_argument('--disable-application-cache')
        # self.opts.add_argument('--enable-logging')
        self.opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.opts.add_experimental_option('useAutomationExtension', False)
    
    # def _init_remote_driver(self, remote_url):
    #     # create remote driver
    #     driver = RemoteDriver(command_executor=remote_url, options=self.opts)
    #     return driver
        
    def _get_urban_new_ip(self):
        for _ in range(5):
            try:
                # wait for loading elems
                sleep(5)

                # close loader elem (because we need to click on pause btn)
                try:
                    WebDriverWait(self, 5).until(
                        EC.element_to_be_clickable((By.XPATH, '//div[@class="loader__bg"]'))
                    ).click()
                except Exception as e:
                    pass
                # click stop btn (change ip)
                WebDriverWait(self, 6).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@class="play-button play-button--pause"]'))
                ).click()
                sleep(5)
            except TimeoutException:
                # click start btn (change ip)
                sleep(randrange(0, 7))
                WebDriverWait(self, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//div[@class="play-button play-button--play"]'))
                ).click()
        
            # print new ip address
            try:
                new_ip = WebDriverWait(self, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//span[@class="main-content__ip"]'))
                ).text
            except TimeoutException:
                pass
            else:
                print(f'[+]Get ip - {new_ip}')
                return
    
    def _load_urban_vpn(self):
        # load vpn
        self.get('chrome-extension://almalgbpmcfpdaopimbdchdliminoign/popup/index.html#/consent/main')
        
        accept_rules_func = lambda: WebDriverWait(self, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[text()=' Agree & Continue ']"))
            ).click()

        for _ in range(5):
            # accept first window
            try:
               accept_rules_func()
            except TimeoutException:
                break
            except StaleElementReferenceException:
                pass
            # wait open new tab
            for _ in range(3):
                if len(self.window_handles) == 1:
                    sleep(2)
                else:
                    break
            else:
                # switch on first tab and close second (additional)
                # self.switch_to.window(self.window_handles[1])
                # sleep(2)
                # self.close()
                # sleep(2)
                self.switch_to.window(self.window_handles[0])
            
            # accept two window and click ok thanks
            for _ in range(5):
                try:
                    # accept two window
                    accept_rules_func()
                    sleep(3)
                except TimeoutException:
                    break
            try:
                # ok thanks click
                WebDriverWait(self, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[text()=' Ok, thanks ']"))
                ).click()
            except TimeoutException:
                pass

        # clean additional windows
        while len(self.window_handles) > 1:
            self.switch_to.window(self.window_handles[1])
            sleep(2)
            self.close()
            sleep(2)
            self.switch_to.window(self.window_handles[0])
        


    
    def _urban_get_ip(self):
        # try:
        self._load_urban_vpn()
        # except Exception as ex:
        #     print(f'EXCPETION LOAD URBAN - {ex}')
        # try:
        self._get_urban_new_ip()
        # except Exception as ex:
        #     print(f'EXCPETION URBAN IP - {ex}')
        

    def get_rootdriver(self):
        # set extensions
        self._set_extensions()
        
        # en lang for hcaptcha_solver
        self.opts.add_experimental_option('prefs', {'intl.accept_languages': 'en,en_US'})
        # self.opts.add_experimental_option('prefs', {'intl.accept_languages': 'ru,ru_RU'})

        # if self.profile_path:
        #     self.opts.add_argument(f"--user-data-dir={self.profile_path}")
        
        super().__init__(options=self.opts, service=ChromeService(ChromeDriverManager().install()))
        # driver = ChromeDriver(options=self.opts, service=service)
        
        # driver settings
        self.implicitly_wait(5)
        self.maximize_window()

        # additional loads
        self._urban_get_ip()
        return self
    
if __name__ == '__main__':
    root_driver = RootChromeDriver().get_rootdriver()
    input('wait..')
    root_driver.close()
    root_driver.quit()