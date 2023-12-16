# import re
# from os import getenv
# from os import listdir
# from os.path import exists as path_exists
# import subprocess
# from time import sleep

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import Chrome as ChromeDriver
from selenium.webdriver import Remote as RemoteDriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions

# from fake_useragent import UserAgent as UA


class RootChromeDriver:
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
        
    def _set_my_config(self) -> None:
        ''' adding the params to self.opts object '''
        # initialize
        # self.opts.add_argument("--headless")
        self.opts.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        self.opts.add_argument("--disable-notifications")
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument('--ignore-certificate-errors')
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--disable-blink-features=AutomationControlled")
        self.opts.add_argument("--disable-extensions")
        self.opts.add_argument('--headless')
        self.opts.add_argument("--disable-popup-blocking")
        self.opts.add_argument("--disable-plugins-discovery")
        self.opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.opts.add_experimental_option('useAutomationExtension', False)
    
    def _init_remote_driver(self, remote_url):
        # find jar file
        # servers_jar = list(filter(lambda s: s.endswith('.jar'), listdir('.'))) 
        # if not servers_jar:
        #     raise FileNotFoundError ('Selenium Jar server is not found')
        # jar_path = servers_jar[0]
        
        # # start jar for windows
        # cmd = f'java -jar {jar_path} standalone'
        # process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.DETACHED_PROCESS, text=True)
        # # Wait for the desired information in the output
        # attempt = 0
        # max_attempts = 10
        # delay = 10
        # while attempt < max_attempts:
        #     output = process.stdout
        #     # if output == '':
        #     #     break
        #     print(output)
        #     if output:
        #         # Check for the presence of the IP address in the output
        #         match = re.search(r'http://\d+\.\d+\.\d+\.\d+:\d+', output)
        #         if match:
        #             remote_url = match[0]
        #             print(f'[+] Found IP address: {remote_url}')
        #             break
        #     sleep(delay)
        # else:
        #     raise ValueError (f'Not found open ip address and port after {max_attempts} attempts')
        
        # Wait for the process to finish
        # process.wait()
        
        # if process.returncode != 0:
        #     raise ValueError(f'Run jar for windows was finished with error - {process.returncode}')
        
        # output, error = process.communicate()
        # output, error = output.decode('utf-8'), error.decode('utf-8')
        # print(output)
        # remote_url = re.search(r'http://\d+\.\d+\.\d+\.\d+:\d+', output)[0]
        # if error:
        #     
        # print('[+]Successful jar runned')

        # create remote driver
        driver = RemoteDriver(command_executor=remote_url, options=self.opts)
        return driver


    def _init_local_driver(self):
        # self.opts.experimental_options('prefs', {'intl.accept_languages': 'en,en_US'})

        # if self.profile_path:
        #     self.opts.add_argument(f"--user-data-dir={self.profile_path}")

        driver_path = ChromeDriverManager().install()
        service = ChromeService(driver_path)

        driver = ChromeDriver(options=self.opts, service=service)
        # setting driver
        driver.implicitly_wait(5)
        driver.maximize_window()
        return driver
    
if __name__ == '__main__':
    root_driver = RootChromeDriver()
    driver = root_driver._init_local_driver()
    input('wait..')
    driver.close()
    driver.quit()