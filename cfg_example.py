# path to Tesseract-OCR on PC
TESSERACT_OCR_PATH = r""   # install tesseract ocr, macos - "https://stackoverflow.com/questions/17140753/tesseract-install-mac-os"  (i dont know about installing on mac os)
                                                         # install teserract ocr, windows - "https://github.com/UB-Mannheim/tesseract/wiki" (exe file - tesseract-ocr-w64-setup-5.3.3.20231005.exe (64 bit) (or > last version))

# EMAIL SETTINGS
MAIL_HOST = "smtp-mail.outlook.com"
MAIL_PORT = 587
MAIL_LOGIN = ''
MAIL_PASSWORD = ''        
MAIL_SEND_TO = ''  # any user
ERROR_NOTIFICATION_SUBJECT = 'PARSING ERROR! (ОШИБКА ПАРСЕРА!): Ошибка в работе приложения по поиску земельных участков на Avito и CIAN!'


# PARSING PROCESS
MAX_PAGES_COUNT = 5_000  # parsing pages from 1 to N
NUM_PARALLEL_BROWSERS = 12   # parsing async N pages 


# PARSE TIMESTAMP FORMAT
TIMESTAMP_DT_FORMAT = '%Y-%m-%d %H:%M'

# OUTPUT FILES PATH
AVITO_TOTAL_CSV_FN = 'avito_total.csv'
CIAN_TOTAL_CSV_FN = 'cian_total.csv'
AVITO_HISTORY_CSV_FN = 'avito_history.csv'
CIAN_HISTORY_CSV_FN = 'cian_history.csv'

# locations which will seen (for parsing) (select this keys in the main file)
CIAN_REGIONS = {'Москва': 1, 'Московская область': 4593}
AVITO_REGIONS = {'Москва и МО': 'moskva_i_mo'}