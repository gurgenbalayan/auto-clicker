import sqlite3
import subprocess
import requests
import undetected_chromedriver as uc
import json
import os
import shutil
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
import argparse
from nltk.corpus import words
from selenium.webdriver.support.wait import WebDriverWait
import time
import random
import nltk
import psutil
nltk.download('words')
import xml.etree.ElementTree as ET

def get_chrome_timestamp():
    """
    Возвращает текущее время в формате WebKit timestamp (микросекунды с 1601 года).
    """
    CHROME_EPOCH_DIFF = 11644473600  # Секунд между 1601 и 1970
    now = time.time()  # Текущее время в секундах
    return int((now + CHROME_EPOCH_DIFF) * 1_000_000)


# def get_ip():
#     try:
#         response = requests.get("https://api.ipify.org?format=json", timeout=5)
#         ip = response.json()["ip"]
#         print(f"Текущий IP-адрес: {ip}")
#         return ip
#     except requests.RequestException as e:
#         print(f"Ошибка при получении IP: {e}")
#         return None
def start_proxifier_with_profile(ppx_path):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        proxifier_exe = os.path.join(script_dir, "Proxifier PE", "Proxifier.exe")
        ppx_path = os.path.join(script_dir, ppx_path)
        if not os.path.exists(proxifier_exe):
            raise FileNotFoundError("❌ Proxifier.exe не найден. Убедись, что путь указан правильно.")
        if not os.path.exists(ppx_path):
            raise FileNotFoundError("❌ Указанный .ppx файл не существует.")

        print("[✔] Запускаю Proxifier с профилем...")
        subprocess.Popen([proxifier_exe])
        time.sleep(3)  # Дать немного времени на запуск
        return True
    except Exception as e:
        print(e)
        return False

def update_proxy(ppx_path, new_ip, new_port):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        ppx_path = os.path.join(script_dir, ppx_path)
        print(f"ppx_path: {ppx_path}")
        if not os.path.exists(ppx_path):
            raise FileNotFoundError(f"Файл не найден: {ppx_path}")

        # Парсим XML-файл
        tree = ET.parse(ppx_path)
        root = tree.getroot()

        # Ищем <Proxy> внутри <ProxyList>
        proxy = root.find(".//ProxyList/Proxy")
        if proxy is None:
            raise ValueError("⚠️ Прокси не найден в файле!")

        # Меняем IP и порт
        address = proxy.find("Address")
        port = proxy.find("Port")

        if address is not None:
            print(f"[i] Старый IP: {address.text}")
            address.text = new_ip

        if port is not None:
            print(f"[i] Старый порт: {port.text}")
            port.text = str(new_port)

        # Сохраняем обратно
        tree.write(ppx_path, encoding="utf-8", xml_declaration=True)
        print(f"[✔] Обновлён файл: {ppx_path} → {new_ip}:{new_port}")
        return True
    except Exception as e:
        print(e)
        return False
def generate_random_user_agent():
    browsers = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.48',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
    ]
    return random.choice(browsers)

def generate_random_language():
    languages = ['en-US', 'en']
    return random.choice(languages)

def generate_random_timezone():
    timezones = ['America/New_York', 'Europe/London']
    return random.choice(timezones)

def generate_random_screen_resolution():
    resolutions = ['1920x1080', '1366x768', '1280x800', '1440x900', '1600x900']
    return random.choice(resolutions)

def get_next_from_file(file_name):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(script_dir, file_name)
    with open(file_path, "r") as f:
        lines = f.readlines()
    if not lines:
        return None
    first_line = lines[0].strip()
    with open(file_path, "w") as f:
        f.writelines(lines[1:] + [lines[0]])

    return first_line


def get_cookie_file():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    cookie_dir = os.path.join(script_dir, "cookies")
    deleted_dir = os.path.join(script_dir, "deleted")

    if not os.path.exists(deleted_dir):
        os.makedirs(deleted_dir)
    files = os.listdir(cookie_dir)
    if not files:
        return None
    file = files[0]
    src_path = os.path.join(cookie_dir, file)
    dest_path = os.path.join(deleted_dir, file)
    shutil.move(src_path, dest_path)
    return dest_path

def load_cookies(db_path, cookies_file2, cookie_file):
    with open(cookie_file, "r") as f:
        cookies = json.load(f)
    script_dir = os.path.dirname(os.path.realpath(__file__))
    db_path = os.path.join(script_dir, db_path)
    db_path2 = os.path.join(script_dir, cookies_file2)
    subprocess.run(['attrib', db_path], shell=True)
    subprocess.run(['attrib', db_path2], shell=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    conn2 = sqlite3.connect(db_path2)
    cursor2 = conn2.cursor()
    values_list = []
    # grouped_cookies = {}
    try:
        for cookie in cookies:
            now_chrome = get_chrome_timestamp()
            expires_chrome = now_chrome + (30 * 24 * 60 * 60 * 1_000_000)  # +30 дней
            # Значения для вставки
            values = (
                now_chrome,  # creation_utc
                cookie["domain"],  # host_key
                '',  # top_frame_site_key (можно оставить пустым)
                cookie["name"],  # name
                cookie["value"],  # value
                b'',  # encrypted_value
                cookie.get("path", "/"),  # path
                expires_chrome,  # expires_utc
                int(cookie.get("secure", False)),  # is_secure
                int(cookie.get("httpOnly", False)),  # is_httponly
                now_chrome,  # last_access_utc
                1,  # has_expires
                1,  # is_persistent
                1,  # priority (обычно 1)
                0,  # samesite (None = 0, Lax = 1, Strict = 2)
                2,  # source_scheme (Unset = 0, NonSecure = 1, Secure = 2)
                443,  # source_port (обычный HTTP порт)
                now_chrome,  # last_update_utc
                2,  # source_type
                1  # has_cross_site_ancestor
            )
            values_list.append(values)
            # SQL-запрос
        sql = """
                INSERT INTO cookies (
                    creation_utc,
                    host_key,
                    top_frame_site_key,
                    name,
                    value,
                    encrypted_value,
                    path,
                    expires_utc,
                    is_secure,
                    is_httponly,
                    last_access_utc,
                    has_expires,
                    is_persistent,
                    priority,
                    samesite,
                    source_scheme,
                    source_port,
                    last_update_utc,
                    source_type,
                    has_cross_site_ancestor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

        cursor.executemany(sql, values_list)
        conn.commit()
        cursor2.executemany(sql, values_list)
        conn2.commit()
        conn2.close()
        conn.close()
        print("✅ Cookie вставлен.")
        return True
    except Exception as e:
        print("! Cookie не вставлены")
        print(e)
        return False
    #     domain = cookie['domain']
    #     if domain not in grouped_cookies:
    #         grouped_cookies[domain] = []
    #     grouped_cookies[domain].append(cookie)
    # i = 0
    # while i < 5:
    #     try:
    #         max_domain = max(grouped_cookies, key=lambda domain: len(grouped_cookies[domain]))
    #         max_cookies = grouped_cookies[max_domain]
    #         if max_cookies[0]["domain"][0] == ".":
    #             url = "http://" + max_cookies[0]["domain"][1:]
    #         else:
    #             url = "http://" + max_cookies[0]["domain"]
    #         driver.get(url)
    #         for cookie in max_cookies:
    #             if "sameSite" in cookie:
    #                 cookie["sameSite"] = "None"
    #             driver.add_cookie(cookie)
    #         cookies_g = driver.get_cookies()
    #         print(f"Добавил {len(cookies_g)} cookies по домену {max_cookies[0]["domain"]}")
    #         grouped_cookies.pop(max_domain)
    #         i += 1
    #     except Exception as e:
    #         grouped_cookies.pop(max_domain)
    #         print(e)

def setup_driver(proxy):
    # ip_before = get_ip()
    # if ip_before is None:
    #     print("Не удалось узнать IP-адрес ip_before")
    #     return None
    script_dir = os.path.dirname(os.path.realpath(__file__))
    profile = os.path.join(script_dir, "profile")
    if not os.path.exists(profile):
        os.makedirs(profile)
    else:
        delete_flag = False
        while not delete_flag:
            time.sleep(1)
            try:
                shutil.rmtree(profile)
                delete_flag = True
            except Exception as e:
                for proc in psutil.process_iter(attrs=['pid', 'name']):
                    if proc.info['name'] == 'chrome.exe':
                        try:
                            proc.terminate()  # Принудительно завершить процесс
                            print(f"Завершен процесс: {proc.info['pid']}")
                        except psutil.NoSuchProcess:
                            pass
                print(e)
    word_list = words.words()
    while True:
        word = random.choice(word_list)
        if len(word) == 10:
            break
    profile_path = os.path.join(profile, word)
    options = webdriver.ChromeOptions()
    options2 = webdriver.ChromeOptions()
    # options.add_argument("--incognito")
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--disable-infobars")
    # options.add_argument(f'--user-agent={generate_random_user_agent()}')
    options.add_argument(f'--lang={generate_random_language()}')
    options.add_argument(f'--timezone={generate_random_timezone()}')
    # options.add_argument(f'--window-size={generate_random_screen_resolution()}')
    # options.add_argument("--start-maximized")
    # options.add_argument('--disable-extensions')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--allow-profiles-outside-user-dir')
    options.add_argument('--enable-profile-shortcut-manager')
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options2.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument(f"--user-data-dir={profile_path}")
    # options.page_load_strategy = 'eager'
    driver_before = uc.Chrome(options=options2)
    driver_before.quit()
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
            try:
                proc.terminate()  # Принудительно завершить процесс
                print(f"Завершен процесс: {proc.info['pid']}")
            except psutil.NoSuchProcess:
                pass
    time.sleep(3)
    cookies_file2 = os.path.join(profile_path, "Default", "Safe Browsing Network", "Safe Browsing Cookies")
    cookies_file = os.path.join(profile_path, "Default", "Network", "Cookies")
    cookie_file = get_cookie_file()
    if not cookie_file:
        print("Файлы куки закончились!")
        return None
    res_load = load_cookies(cookies_file, cookies_file2, cookie_file)
    if not res_load:
        print("Файлы куки не загрузились")
        return None
    ip, port = proxy.split(':')
    ppx_file = os.path.join("Proxifier PE", "Profiles", "proxy.ppx")
    result_rewrite = update_proxy(ppx_file, ip, port)
    if result_rewrite:
        result_start = start_proxifier_with_profile(ppx_file)
        if not result_start:
            print("Не удалось запустить Proxifier")
            return None
    else:
        print("Не удалось установить proxy")
        return None
    driver = uc.Chrome(options=options)
    # time.sleep(33333)
    return driver

def human_like_scroll(driver, direction="down", min_wait=1, max_wait=3, scroll_variation=0.3, max_attempts=10):
    """
    Параметры:
    driver         — объект Selenium WebDriver
    direction      — 'down' или 'up'
    min_wait       — минимальное время ожидания между скроллами
    max_wait       — максимальное время ожидания между скроллами
    scroll_variation — случайная вариация шага прокрутки (в долях от высоты окна)
    max_attempts   — попытки без изменений высоты (для выхода при конце страницы)
    """
    last_height = driver.execute_script("return document.body.scrollHeight")
    attempts = 0

    while attempts < max_attempts:
        # Генерация вариации и вычисление скролла
        variation = random.uniform(-scroll_variation, scroll_variation)
        scroll_step = driver.execute_script("return window.innerHeight * (0.9 + arguments[0]);", variation)

        if direction == "up":
            scroll_step = -abs(scroll_step)
        else:
            scroll_step = abs(scroll_step)

        driver.execute_script(f"window.scrollBy(0, {scroll_step});")

        time.sleep(random.uniform(min_wait, max_wait))

        # Только при движении вниз проверяем, изменился ли scrollHeight
        if direction == "down":
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                attempts += 1
            else:
                attempts = 0
                last_height = new_height
        else:
            # Если вверх — просто считаем шаги, чтобы не зациклиться
            attempts += 1

    print(f"Скроллинг завершён: направление — {direction}")

def click_internal_links(driver, clicked_links, site_domain, delay):
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        href = link.get_attribute("href")
        if href and site_domain in href and "#" not in href and href not in clicked_links:
            try:
                # time.sleep(delay)
                link.click()
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # time.sleep(delay)
                return href
            except Exception as e:
                print(f"Ошибка при клике по ссылке: {e}")
                continue
    return False

def main(delay):
    while True:
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                try:
                    proc.terminate()  # Принудительно завершить процесс
                    print(f"Завершен процесс: {proc.info['pid']}")
                except psutil.NoSuchProcess:
                    pass
        site = get_next_from_file("sites.txt")
        proxy = get_next_from_file("proxy.txt")
        if not site or not proxy:
            print("Файлы sites.txt или proxy.txt недоступны")
            break
        driver = setup_driver(proxy)
        if driver is None:
            print("driver не установился")
            continue
        try:
            driver.get('https://www.google.com')
        except Exception as e:
            print(f"Сайт не открывается. Proxy {proxy} не работает")
            print(e)
            continue
        # load_cookies(driver, cookie_file)
        driver.get(f'https://www.google.com/url?sa=i&url=http%3A%2F%2F{site}&source=images&cd=vfe')
        try:
            res = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print(f"res: {res}")
        except Exception as e:
            print(f"Сайт не открывается. Proxy {proxy} не работает")
            print(e)
        links = driver.find_elements(By.TAG_NAME, "a")
        time.sleep(33333)
        try:
            links[0].click()
            time.sleep(delay)
            clicked_links = []
            clicked_links.append(f"https://{site}")
            clicked_links.append(f"http://{site}")
            clicked_links.append(f"http://{site}/")
            clicked_links.append(f"https://{site}/")
            clicked_links.append(f"https://www.{site}/")
            clicked_links.append(f"https://www.{site}")
            clicked_links.append(f"http://www.{site}/")
            clicked_links.append(f"http://www.{site}")
            for i in range(3):
                human_like_scroll(driver, direction="down")
                human_like_scroll(driver, direction="up")
                result = click_internal_links(driver, clicked_links, site, delay)
                if result:
                    i += 1
                    clicked_links.append(result)
                else:
                    break
                time.sleep(delay)
        except Exception as e:
            print(e)
        driver.quit()
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                try:
                    proc.terminate()  # Принудительно завершить процесс
                    print(f"Завершен процесс: {proc.info['pid']}")
                except psutil.NoSuchProcess:
                    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, default=1, help="Задержка между действиями в секундах")
    args = parser.parse_args()
    main(args.delay)
