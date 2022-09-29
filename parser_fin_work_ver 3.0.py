from selenium import webdriver
import time
import base64, requests
from random import choice
from lxml import html, etree
import json
from threading import Thread
from pytrends.request import TrendReq
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from loguru import logger
from selenium.common.exceptions import NoSuchElementException
import pandas as pd

# Антикапча
class Anticaptcha:
    __results = {}
    
    def __init__(self, key):
        self.__api_key = key
        self.__url = "https://api.anti-captcha.com/"    # Адрес вызова методов API
        self.__ct = "createTask"                        # Метод создания задачи
        self.__gtr = "getTaskResult"                    # Метод получения результата выполнения задачи
        self.__taskID = 0                               # ID задачи
        self.__imageUrl = ""                            # URL изобржения с капчей

    def createtask(self, url):
        self.__imageUrl = url
        if url in Anticaptcha.__results:
            return
        Anticaptcha.__results[self.__imageUrl] = ""
        with requests.get(url, stream=True) as r:
            # Кодирование изображения в base64 для передачи в текстовом виде
            data = base64.b64encode(r.content).decode()
            # Форма создания задачи
            struct = {
                "clientKey" : self.__api_key,
                "task": {
                    "type": "ImageToTextTask",  # Тип задачи
                    "body": data,               # Изображение
                    "phrase": False,            # Фраза (ХЗ, что значит)
                    "case": True,               # Важен ли регистр
                    "numeric": False,           # Состоит ли капча только из цифр
                    "math": 0,                  # Предствляет ли капча математическую или арифметическую задачу.
                    "minLength": 0,             # Минимальная длина
                    "maxLength": 0              # Максимальная длина
                }
            }
            response = requests.post(self.__url + self.__ct, json=struct).json() # Отправка формы задачи
            if response['errorId']==0:
                self.__taskID = response['taskId']
            else:
                self.__taskID = -1
    '''
        Проверка выполнения задачи
    '''
    def gettaskresult(self):
        if self.__taskID == 0:
            return "not started"
        elif self.__taskID == -1:
            return "failed"
        elif Anticaptcha.__results[self.__imageUrl]:
            return "ready"
        else:
            struct = {
                "clientKey": self.__api_key,
                "taskId": self.__taskID
            }
            with requests.post(self.__url + self.__gtr, json=struct) as r:
                json = r.json()
                try:
                    Anticaptcha.__results[self.__imageUrl] = json["solution"]["text"]
                except:
                    Anticaptcha.__results[self.__imageUrl] = json['errorId']
                return json['status']
            return "connection failed"


    def getresult(self):
        return Anticaptcha.__results[self.__imageUrl]

    '''
        Ожидание получения ответа
        Метод возвращает результат, полученный с сервиса антикапчи
    '''
    def join(self):
        response = self.gettaskresult()
        while response=="processing":
            response = self.gettaskresult()
        return self.getresult()


def get_token(url):
    print("__get_token")
    ac = Anticaptcha("c0fa45e36d4f1825b71671334067ac33")
    ac.createtask(url)
    return ac.join()

'''
    Вводит текст в элемент, найденный по xpath
'''        
def entertextbyxpath(browser, path, text):
    el = browser.find_element(by=By.XPATH, value=path)
    el.clear()
    el.send_keys(text)

'''
        Кликает по элементу, найденному по xpath
'''
def clickelementbyxpath(browser, path):
    #t1 = time.time()
    #time.sleep(0.5)
    element = browser.find_element(by=By.XPATH, value=path)
    element.click()
    return


def getstathistory_test(browser, kwords):
    browser.get("https://wordstat.yandex.ru/#!/history?period=weekly&words="+kwords)
    time.sleep(2.0)
    capcha_checker(browser)
    
    result = {}
    attention_counter = 0

    while result == {}:
        tables = []
        query = []
        
        while query == []:
            browser.get("https://wordstat.yandex.ru/#!/history?period=weekly&words="+kwords)
            tree = html.fromstring(browser.page_source)
            query = tree.xpath('//div[@class = "b-history__query"]')

        my_query = query[0].text

        if my_query == f'История показов по фразе «{kwords}»':
            tables = tree.xpath('//table[@class = "b-history__table"]')

        else:
            print(f'ATTENTION! Вероятность проскальзывания! Требуется ручная проверка данных ключевого слова "{kwords}", предыдущего и следующего за ним!')
            attention_counter = attention_counter + 1
            capcha_checker(browser)
            browser.get("https://wordstat.yandex.ru/#!/history?period=weekly&words="+kwords)
            time.sleep(60.0)
            tree = html.fromstring(browser.page_source)
            tables = tree.xpath('//table[@class = "b-history__table"]')

        table1 = tables[0].xpath('//tr[@class = "odd" or @class = "even"]')
        table2 = tables[1].xpath('//tr[@class = "odd" or @class = "even"]')

        for row in table1 + table2:
            #line = {}
            #line['absolute'] = int(''.join([i.text for i in row[2]]))
            #line['absolute'] = int(''.join([i.text for i in row[2]]))
            #line['relative'] = float(''.join([i.text for i in row[3]]).replace(",", "."))
            result[row[0].text.replace("\xa0-\xa0", ' - ')] = int(''.join([i.text for i in row[2]]))

        return result


def clickcapcha(browser):
    element = browser.find_element(by=By.XPATH, value='//input[contains(@class, "CheckboxCaptcha-Button")]')
    element.click()
    time.sleep(2.0)

def mobilecapcha(browser):
    telephone = input('Введите номер телефона учетной записи в формате 71234567890: ')
    number = browser.find_element(by=By.XPATH, value='//*[@id="passp-field-login"]')
    number.click()
    number.send_keys(telephone)
    time.sleep(2.0)
    # Ищем по xpath кнопку ввода капчи и кликаем на неё
    button_number = browser.find_element(by=By.XPATH, value='/html/body/div/div/div[2]/div[2]/div/div/div[2]/div[3]/div/div/div/div[1]/form/div[4]/button')
    button_number.click()
    sms = input('Введите код из смс: ')
    phonecode = browser.find_element(by=By.XPATH, value='//*[@id="passp-field-phoneCode"]')
    phonecode.click()
    phonecode.send_keys(sms)
    time.sleep(2.0)
    button_phonecode = browser.find_element(by=By.XPATH, value='/html/body/div/div/div[2]/div[2]/div/div/div[2]/div[3]/div/div/form/div/div[3]/button[1]')
    button_phonecode.click()
    time.sleep(2.0)
    acc_cliker = browser.find_element(by=By.XPATH, value='//*[@id="accounts:item-1660493369"]')
    acc_cliker.click()
    time.sleep(2.0)



def capcha_check_raw(browser):
    try:
        checkсaptcha_test = browser.find_elements(by=By.XPATH, value='//div[contains(@class, "AdvancedCaptcha-View")]')
        img = checkсaptcha_test[0].find_element(by=By.XPATH, value='//img[@class = "AdvancedCaptcha-Image"]')
        url = img.get_property('src')
        print('Решаю капчу: ' + url)
        cappcha = get_token(url)
        print(cappcha)

        if type(cappcha)==int:
            repeat = browser.find_element(by=By.XPATH, value='//button[contains(@class, "Button2 Button2_size_l Button2_view_clear")]') 
            repeat.click()
            time.sleep(2.0)
            checkсaptcha_test = browser.find_elements(by=By.XPATH, value='//div[contains(@class, "AdvancedCaptcha-View")]')
            img = checkсaptcha_test[0].find_element(by=By.XPATH, value='//img[@class = "AdvancedCaptcha-Image"]')
            url = img.get_property('src')
            print('Решаю капчу: ' + url)
            cappcha = get_token(url)
            return cappcha
            
        else:
            checkсaptcha_test = browser.find_elements(by=By.XPATH, value='//div[contains(@class, "AdvancedCaptcha-View")]')
            img = checkсaptcha_test[0].find_element(by=By.XPATH, value='//img[@class = "AdvancedCaptcha-Image"]')
            url = img.get_property('src')
            cappcha = get_token(url)
            return cappcha

    except KeyError:
        print('Исключение:')
        return capcha_check_raw(browser)

'''
Функция проверки капчи с ожиданием, вводом и повторными попытками в случае неудачи
'''
def capcha_checker(browser):
    time.sleep(2.0)
    numbercheck = browser.find_elements(by=By.XPATH, value='//*[@id="passp-field-login"]')
    сheckсaptcha = browser.find_elements(by=By.XPATH, value='//input[contains(@class, "CheckboxCaptcha-Button")]')
    if numbercheck:
        mobilecapcha(browser)
        if сheckсaptcha:
            clickcapcha(browser)

            while browser.find_elements(by=By.XPATH, value='//button[contains(@class, "Button2 Button2_size_l Button2_view_action")]') != []:
                    capcap = capcha_check_raw(browser)

                    entry = "/html/body/div[1]/div/div/form/div/div[2]/span/input" 
                    entry = browser.find_element(by=By.XPATH, value=entry)
                    # На некоторые текстовые поля нудно кликнуть перед вводом.
                    # Это как раз тот самый случай
                    entry.click()
                    time.sleep(5.0)

                    entry.send_keys(capcap)
                    # Ищем по xpath кнопку ввода капчи и кликаем на неё
                    button = browser.find_element(by=By.XPATH, value='/html/body/div[1]/div/div/form/div/div[3]/button[3]')
                    button.click()
                    time.sleep(5.0)

            return True

        else: 
            return False

    elif сheckсaptcha:

        clickcapcha(browser)

        while browser.find_elements(by=By.XPATH, value='//button[contains(@class, "Button2 Button2_size_l Button2_view_action")]') != []:
                capcap = capcha_check_raw(browser)

                entry = "/html/body/div[1]/div/div/form/div/div[2]/span/input" 
                entry = browser.find_element(by=By.XPATH, value=entry)
                # На некоторые текстовые поля нудно кликнуть перед вводом.
                # Это как раз тот самый случай
                entry.click()
                time.sleep(5.0)

                entry.send_keys(capcap)
                # Ищем по xpath кнопку ввода капчи и кликаем на неё
                button = browser.find_element(by=By.XPATH, value='/html/body/div[1]/div/div/form/div/div[3]/button[3]')
                button.click()
                time.sleep(5.0)

        return True

    else: 
        return False


'''
Логинимся в яндекс wordstsat
'''
def yandexlogin(browser, user, pswd):
        browser.get("http://wordstat.yandex.ru")
        clickelementbyxpath(browser, '//td[contains(@class, "b-head-userinfo__entry")]')
        entertextbyxpath(browser, '//*[@id="b-domik_popup-username"]', user)
        entertextbyxpath(browser, '//*[@id="b-domik_popup-password"]', pswd)
        clickelementbyxpath(browser, "/html/body/form/table/tbody/tr[2]/td[2]/div/div[5]/span[1]")
        time.sleep(2.0)
        capcha_checker(browser)


'''
Создаем сессию
'''
browser = webdriver.Firefox(executable_path=r'C://geckodriver.exe', firefox_binary=r'C:\Users\a.seredkin\AppData\Local\Mozilla Firefox\firefox.exe')
yandexlogin(browser, 'Bistrobistrobistro', 'BegyBistro@123')




counter = 0
# Загружаем spreadsheet в объект pandas
xl = pd.read_excel(r"C:\Users\a.seredkin\Documents\python\Parser\final\keys.xlsx")
# Загрузить лист в DataFrame по его имени: df1
list = xl['Ключи'].tolist() 
result_dict = {}

t=time.time()
for i in list:
    counter = counter+1
    print(f'Парсинг ключа под номером {counter} из {len(list)}:', i)
    result_dict[i]=getstathistory_test(browser, i)
    if counter % 50 == 0:
        print('Перезапуск бразуера')
        browser.quit()
        time.sleep(5.0)
        browser = webdriver.Firefox(executable_path=r'C://geckodriver.exe', firefox_binary=r'C:\Users\a.seredkin\AppData\Local\Mozilla Firefox\firefox.exe')
        yandexlogin(browser, '****', '****')

result_time = time.time()-t

print(f'на парсинг {len(result_dict.keys())} ключей потребовалось {result_time} секунд')


df = pd.DataFrame(result_dict)
df.to_excel('data.xlsx')

