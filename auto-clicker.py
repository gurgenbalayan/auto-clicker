import sqlite3
import re
import string
import subprocess
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
import xml.etree.ElementTree as ET
from pathlib import Path
nltk.download('words')



paths_to_check = [
    os.environ.get("PROGRAMFILES", r"C:\Program Files"),
    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    os.environ.get("LOCALAPPDATA", r"C:\Users\%USERNAME%\AppData\Local"),
    os.environ.get("APPDATA", r"C:\Users\%USERNAME%\AppData\Roaming"),
]

executables = ["GoogleUpdate.exe", "GoogleUpdateSetup.exe", "GoogleCrashHandler.exe", "GoogleCrashHandler64.exe", "GoogleUpdateBroker.exe", "GoogleUpdateComRegisterShell64.exe", "GoogleUpdateCore.exe", "GoogleUpdateOnDemand.exe", "GoogleUpdateSetup.exe", "updater.exe", "update.exe"]

def rename_if_exists(path: Path):
    if path.exists():
        new_path = path.with_name(path.name + ".bak")
        try:
            if path.is_dir():
                path.rename(new_path)
                print(f"[DIR] Переименовано: {path} -> {new_path}")
            else:
                path.rename(new_path)
                print(f"[FILE] Переименовано: {path} -> {new_path}")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось переименовать {path}: {e}")

def find_and_rename_google_update():
    for base in paths_to_check:
        base_path = Path(base)
        if not base_path.exists():
            continue

        for root, dirs, files in os.walk(base_path):
            path_obj = Path(root)

            # Проверка папки на "Google/Update"
            if "google" in path_obj.parts and "update" in path_obj.parts:
                rename_if_exists(path_obj)

            # Переименование исполняемых файлов
            for exe in executables:
                exe_path = path_obj / exe
                if exe_path.exists():
                    rename_if_exists(exe_path)
def clean_domain(url):
    return re.sub(r'^(https?:\/\/)?(www\.)?', '', url).split('/')[0].lower()
def parse_proxy(proxy_str):
    """
    Разбирает прокси строку формата:
    - IP:PORT
    - USER:PASS@IP:PORT

    Возвращает словарь с ключами:
    user, password, ip, port (если нет — значения будут None)
    """
    pattern_with_auth = re.compile(r'(?:(?P<user>[^:@]+):(?P<password>[^@]+)@)?(?P<ip>[\d.]+):(?P<port>\d+)')
    match = pattern_with_auth.match(proxy_str.strip())

    if not match:
        raise ValueError(f"Невалидный формат прокси: {proxy_str}")

    return {
        'user': match.group('user'),
        'password': match.group('password'),
        'ip': match.group('ip'),
        'port': match.group('port')
    }


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
            raise FileNotFoundError("❌ Proxifier.exe found. Make sure the path is correct.")
        if not os.path.exists(ppx_path):
            raise FileNotFoundError("❌ The specified .ppx file does not exist.")

        print("[✔] I launch Proxifier with the profile...")
        subprocess.Popen([proxifier_exe])
        time.sleep(3)  # Дать немного времени на запуск
        return True
    except Exception as e:
        print(e)
        return False

def update_proxy(ppx_path, new_ip, new_port, user, pswd):
    try:
        script_dir = os.path.dirname(os.path.realpath(__file__))
        ppx_path = os.path.join(script_dir, ppx_path)
        print(f"ppx_path: {ppx_path}")
        if not os.path.exists(ppx_path):
            raise FileNotFoundError(f"File not found: {ppx_path}")

        # Парсим XML-файл
        tree = ET.parse(ppx_path)
        root = tree.getroot()

        # Ищем <Proxy> внутри <ProxyList>
        proxy = root.find(".//ProxyList/Proxy")
        if proxy is None:
            raise ValueError("⚠️ Proxy not found in file!")

        # Меняем IP и порт
        address = proxy.find("Address")
        port = proxy.find("Port")

        if address is not None:
            print(f"[i] Proxy found in file! {address.text}")
            address.text = new_ip

        if port is not None:
            print(f"[i] Old port: {port.text}")
            port.text = str(new_port)

        for proxy in root.findall(".//ProxyList/Proxy[@id='100'][@type='SOCKS5']"):
            # Удаляем старый <Authentication>
            auth = proxy.find("Authentication")
            if auth is not None:
                proxy.remove(auth)
            if user is not None and pswd is not None:
                # Добавляем новый <Authentication>
                new_auth = ET.Element("Authentication", enabled="true")
                username = ET.SubElement(new_auth, "Username")
                username.text = user
                password = ET.SubElement(new_auth, "Password")
                password.text = pswd
                proxy.append(new_auth)

        # Сохраняем обратно
        tree.write(ppx_path, encoding="utf-8", xml_declaration=True)
        print(f"[✔] File updated: {ppx_path} → {new_ip}:{new_port}")
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
    languages = ['en-US']
    return random.choice(languages)

def generate_random_timezone():
    timezones = ['America/New_York']
    return random.choice(timezones)

def generate_random_screen_resolution():
    resolutions = ['1920x1080', '1366x768', '1280x800', '1440x900', '1600x900']
    return random.choice(resolutions)

def get_next_from_file(file_name):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    file_path = os.path.join(script_dir, file_name)
    with open(file_path, "r", encoding='utf-8-sig') as f:
        lines = f.readlines()
    if not lines:
        return None
    first_line = lines[0].strip()
    with open(file_path, "w", encoding='utf-8-sig') as f:
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
    return src_path, dest_path

def load_cookies(db_path, cookies_file2, cookie_file):
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
            try:
                proc.terminate()
                proc.wait(timeout=3) # Принудительно завершить процесс
                print(f"Process completed: {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    try:
        with open(cookie_file, "r") as f:
            cookies = json.load(f)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        db_path = os.path.join(script_dir, db_path)
        db_path2 = os.path.join(script_dir, cookies_file2)
        # try:
        #     # Пытаемся открыть файл на чтение и сразу закрыть
        #     with open(db_path, 'a'):
        #         pass
        #     with open(db_path2, 'a'):
        #         pass
        #     return True
        # except IOError:
        #     return False

        subprocess.run(['attrib', db_path], shell=True)
        subprocess.run(['attrib', db_path2], shell=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        conn2 = sqlite3.connect(db_path2)
        cursor2 = conn2.cursor()
        values_list = []
        # grouped_cookies = {}
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
        print("✅ Cookie inserted.")
        return True
    except Exception as e:
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                try:
                    proc.terminate()
                    proc.wait(timeout=3)  # Принудительно завершить процесс
                    print(f"Process completed: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        print("! Cookies not inserted")
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
    chrome_dir = "chromedriver/chromedriver.exe"
    chrome_path = os.path.join(script_dir, chrome_dir)
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
                    if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)  # Принудительно завершить процесс
                            print(f"Process completed: {proc.info['pid']}")
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                            try:
                                proc.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                print(e)
    try:
        word_list = words.words()
    except Exception as e:
        word_list = [''.join(random.choices(string.ascii_letters, k=10))]
    if len(word_list) > 0:
        word = random.choice(word_list)
    else:
        word = ''.join(random.choices(string.ascii_letters, k=10))
    profile_path = os.path.join(profile, word)
    options = webdriver.ChromeOptions()
    options2 = webdriver.ChromeOptions()
    # options.add_argument("--incognito")
    # options.add_argument("--disable-blink-features=AutomationControlled")
    # options.add_argument("--disable-infobars")
    options.add_argument(f'--user-agent={generate_random_user_agent()}')
    options.add_argument("--no-sandbox")
    options.add_argument(f'--lang={generate_random_language()}')
    options.add_argument(f'--timezone={generate_random_timezone()}')
    options.add_argument(f'--window-size={generate_random_screen_resolution()}')
    options.add_argument("--start-maximized")
    # options.add_argument('--disable-extensions')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--allow-profiles-outside-user-dir')
    # options.add_argument('--enable-profile-shortcut-manager')
    # options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=DnsOverHttps")
    # options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    # local_state = {
    #     "dns_over_https.mode": "off",
    #     "dns_over_https.templates": "",
    # }
    #
    # options.add_experimental_option("localState", local_state)
    options.add_argument("--disable-webrtc")
    options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
    options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
    options2.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.page_load_strategy = 'eager'
    try:
        driver_before = uc.Chrome(driver_executable_path=chrome_path, options=options2)
    except Exception as e:
        print(f"! Chrome not installed1 {str(e)}")
        return None, "", ""
    driver_before.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    driver_before.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attrs) {
            const ctx = getContext.apply(this, arguments);
            if (type === '2d') {
                const originalToDataURL = this.toDataURL;
                this.toDataURL = function() {
                    return "data:image/png;base64,fake_canvas_fingerprint";
                };
            }
            return ctx;
        };
        """
    })

    driver_before.quit()
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
            try:
                proc.terminate()
                proc.wait(timeout=3)  # Принудительно завершить процесс
                print(f"Process completed: {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                try:
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    time.sleep(5)


    cookies_file2 = os.path.join(profile_path, "Default", "Safe Browsing Network", "Safe Browsing Cookies")
    cookies_file = os.path.join(profile_path, "Default", "Network", "Cookies")
    cookie_file, deleted_cookie_file = get_cookie_file()
    if not cookie_file:
        print("Cookies are out!")
        return None, "", ""
    res_load = load_cookies(cookies_file, cookies_file2, cookie_file)
    if not res_load:
        print("Cookies failed to load!")
        return None, "", ""
    proxy_data = parse_proxy(proxy)
    ip = proxy_data["ip"]
    port = proxy_data["port"]
    user = proxy_data["user"]
    password = proxy_data["password"]
    ppx_file = os.path.join("Proxifier PE", "Profiles", "proxy.ppx")
    result_rewrite = update_proxy(ppx_file, ip, port, user, password)
    if result_rewrite:
        result_start = start_proxifier_with_profile(ppx_file)
        if not result_start:
            print("Failed to start Proxifier")
            return None, "", ""
    else:
        print("Failed to install proxy")
        return None, "", ""
    try:
        driver = uc.Chrome(driver_executable_path=chrome_path, options=options)
    except Exception as e:
        print(f"! Chrome not installed2 {str(e)}")
        return None, "", ""
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            const getContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, attrs) {
                const ctx = getContext.apply(this, arguments);
                if (type === '2d') {
                    const originalToDataURL = this.toDataURL;
                    this.toDataURL = function() {
                        return "data:image/png;base64,fake_canvas_fingerprint";
                    };
                }
                return ctx;
            };
            """
    })
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    # time.sleep(33333)
    return driver, cookie_file, deleted_cookie_file

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

    print(f"Scrolling Completed: Direction — {direction}")

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
                print(f"Error when clicking on the link {e}")
                continue
    return False

def main(delay):
    services = ['gupdate', 'gupdatem']
    for service in services:
        try:
            print(f"Отключаем службу: {service}")
            subprocess.run(['sc', 'config', service, 'start=', 'disabled'], check=True)
            subprocess.run(['sc', 'stop', service], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при работе со службой {service}: {e}")
    while True:
        find_and_rename_google_update()
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                try:
                    proc.terminate()
                    proc.wait(timeout=3)  # Принудительно завершить процесс
                    print(f"Process completed: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
        site = get_next_from_file("sites.txt")
        proxy = get_next_from_file("proxy.txt")
        if not site or not proxy:
            print("sites.txt or proxy.txt files are not available")
            break
        driver, cookie_file, deleted_cookie_file = setup_driver(proxy)
        if driver is None:
            print("driver not installed")
            continue
        try:
            driver.get('https://www.google.com')
        except Exception as e:
            print(f"The site does not open. Proxy {proxy} is not working")
            print(e)
            continue
        # load_cookies(driver, cookie_file)
        # time.sleep(3333)
        try:
            driver.get(f'https://www.google.com/url?sa=i&url=http%3A%2F%2F{site}&source=images&cd=vfe')
            res = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            old_url = clean_domain(site)
            print(f"site: {old_url}")
            print(f"res: {res}")
        except Exception as e:
            print(f"The site does not open. The site does not work.")
            print(e)
            continue
        links = driver.find_elements(By.TAG_NAME, "a")
        time.sleep(2)
        try:
            links[0].click()
            time.sleep(2)
            new_url = clean_domain(driver.current_url)
            print(f"New url: {new_url}")
            if new_url == old_url:
                print("Redirecting succesed")
            else:
                continue
                print("Redirecting failed")
            time.sleep(delay)
            if "ERR_" in driver.page_source or "This site can’t be reached" in driver.page_source:
                print("[-] Error loading page (possibly DNS or proxy)")
                continue
            else:
                print("[+] The page seemed to load normally.")
            clicked_links = []
            clicked_links.append(f"https://{site}")
            clicked_links.append(f"http://{site}")
            clicked_links.append(f"http://{site}/")
            clicked_links.append(f"https://{site}/")
            clicked_links.append(f"https://www.{site}/")
            clicked_links.append(f"https://www.{site}")
            clicked_links.append(f"http://www.{site}/")
            clicked_links.append(f"http://www.{site}")
            human_like_scroll(driver, direction="down")
            human_like_scroll(driver, direction="up")
            print(f"[+] Deleted cookies file {deleted_cookie_file}")
            shutil.move(cookie_file, deleted_cookie_file)
            # for i in range(3):
            #     human_like_scroll(driver, direction="down")
            #     human_like_scroll(driver, direction="up")
            #     result = click_internal_links(driver, clicked_links, site, delay)
            #     if result:
            #         i += 1
            #         clicked_links.append(result)
            #     else:
            #         break
            #     time.sleep(delay)
        except Exception as e:
            print(e)
        driver.quit()
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'] == 'chrome.exe' or proc.info['name'] == 'Proxifier.exe':
                try:
                    proc.terminate()
                    proc.wait(timeout=3)  # Принудительно завершить процесс
                    print(f"Process completed: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, default=1, help="Delay between actions in seconds")
    args = parser.parse_args()
    main(args.delay)
