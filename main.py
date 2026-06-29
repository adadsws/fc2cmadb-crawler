import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from bs4 import NavigableString
import html
import json
import re
import os
import sys
import time
import subprocess
import requests
import winshell  # 用于创建快捷方式
from urllib.parse import urlparse

try:
    import winreg
except ImportError:
    winreg = None

for output_stream in (sys.stdout, sys.stderr):
    if hasattr(output_stream, "reconfigure"):
        output_stream.reconfigure(errors="replace")

'''
设置演员ID
'''
actresses_id = 4199   # 替换为你想抓取的演员ID  
SITE_BASE_URL = "https://fc2cmadb.com"
SITE_HOST = urlparse(SITE_BASE_URL).netloc
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
COOKIE_FILENAME = f"{SITE_HOST}_cookies.txt"
OLD_COOKIE_FILENAME = "fc2ppvdb.com_cookies.txt"
MAX_FILM_FOLDER_NAME_LENGTH = 80
FOLDER_TRUNCATION_SUFFIX = "+++"


def choose_actress_id(default_actress_id):
    """启动时选择使用默认演员 ID，或手动输入新的演员 ID。"""
    default_actress_id = str(default_actress_id).strip()
    print("#" * 60)
    print("请选择演员 ID 来源 / Select actress ID source")
    print(f"1. 使用 main.py 默认 ID / Use default ID: {default_actress_id}")
    print("2. 手动输入演员 ID / Enter ID manually")
    print("#" * 60)

    while True:
        try:
            choice = input("请输入数字 1 或 2（直接回车默认 1）: ").strip()
        except EOFError:
            print(f"无法读取输入，使用默认 ID / Cannot read input, using default ID: {default_actress_id}")
            return default_actress_id

        if choice in ("", "1"):
            print(f"使用默认演员 ID / Using default actress ID: {default_actress_id}")
            return default_actress_id

        if choice == "2":
            try:
                manual_id = input("请输入 actresses_id: ").strip()
            except EOFError:
                print(f"无法读取输入，使用默认 ID / Cannot read input, using default ID: {default_actress_id}")
                return default_actress_id

            if manual_id.isdigit():
                print(f"使用手动输入演员 ID / Using manually entered actress ID: {manual_id}")
                return manual_id

            print("输入无效，请输入纯数字 ID / Invalid input, please enter digits only")
            continue

        print("选择无效，请输入 1 或 2 / Invalid choice, please enter 1 or 2")


def click_enter_button(driver, timeout=10):
    """等待并点击 ENTER 按钮"""
    try:
        enter_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "text-white"))
        )
        enter_button.click()
    except Exception as e:
        error_type = type(e).__name__
        print(f"点击按钮失败 / Failed to click button ({error_type})")

def wait_for_element(driver, class_name, timeout=20):
    """等待指定元素加载完成"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name))
        )
        return element
    except Exception as e:
        # 只打印简洁的错误信息，不显示堆栈跟踪
        error_type = type(e).__name__
        print(f"等待元素超时 / Element wait timeout: {class_name} ({error_type})")
        return None

def wait_for_page_load(driver, timeout=40):
    """等待 Inertia 数据或影片卡片加载完成"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda current_driver: current_driver.execute_script(
                """
                const pageEl = document.querySelector('script[data-page="app"]');
                if (pageEl && pageEl.textContent) {
                    try {
                        const page = JSON.parse(pageEl.textContent);
                        if (page.component === 'Error' || page.props?.status) return true;
                        if (Array.isArray(page.props?.articles?.data)) return true;
                    } catch (error) {}
                }
                return Array.from(document.querySelectorAll('.card a[href]'))
                    .some((link) => /\\/articles\\/\\d+(?:[/?#]|$)/.test(link.getAttribute('href') || '')
                        && ((link.getAttribute('title') || '').trim() || (link.textContent || '').trim()));
                """
            )
        )
        soup = parse_html(driver)
        page_data = extract_inertia_page_data(soup)
        if describe_inertia_error(page_data):
            return False
        return True
    except Exception as e:
        error_type = type(e).__name__
        print(f"等待页面加载超时 / Page load timeout ({error_type})")
        return False

def fetch_actress_articles(driver, actress_id, page):
    """导航到指定页并等待影片卡片加载完成，返回解析后的 soup"""
    url = f"{SITE_BASE_URL}/actresses/{actress_id}?page={page}"
    driver.get(url)
    if not wait_for_page_load(driver):
        return None
    return BeautifulSoup(driver.page_source, 'html.parser')

def disable_js(driver):
    driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled", {"value": True})

def enable_js(driver):
    driver.execute_cdp_cmd("Emulation.setScriptExecutionDisabled", {"value": False})

def parse_html(driver):
    """获取并解析网页 HTML"""
    html_content = driver.page_source
    return BeautifulSoup(html_content, "html.parser")

def extract_inertia_page_data(soup):
    """提取新站 Inertia JSON 数据；兼容旧版 data-page 属性。"""
    script_element = soup.select_one('script[data-page="app"]')
    if script_element:
        payload = script_element.string or script_element.get_text()
        if payload and payload.strip():
            try:
                return json.loads(payload)
            except json.JSONDecodeError as e:
                print(f"Inertia JSON 解析失败 / Failed to parse Inertia JSON ({e})")

    for element in soup.select("[data-page]"):
        payload = element.get("data-page")
        if not payload or payload == "app":
            continue
        try:
            return json.loads(html.unescape(payload))
        except json.JSONDecodeError:
            continue

    return None

def get_inertia_props(soup):
    page_data = extract_inertia_page_data(soup)
    if not isinstance(page_data, dict):
        return {}
    return page_data.get("props") or {}

def get_articles_paginator(soup):
    props = get_inertia_props(soup)
    articles = props.get("articles")
    if isinstance(articles, dict) and isinstance(articles.get("data"), list):
        return articles
    return None

def describe_inertia_error(page_data):
    if not isinstance(page_data, dict):
        return False
    props = page_data.get("props") or {}
    component = page_data.get("component")
    status = props.get("status")
    if component != "Error" and not status:
        return False

    print(f"页面返回错误 / Page returned error: {status or component}")
    auth = props.get("auth") or {}
    if status == 403 and not auth.get("user"):
        print(
            "当前会话未登录或没有访问权限。请在浏览器登录 fc2cmadb.com，"
            f"导出 Cookies 为 {COOKIE_FILENAME} 后再运行脚本。"
        )
    return True

def extract_film_count(soup):
    """提取影片数量信息"""
    articles = get_articles_paginator(soup)
    if articles:
        total_films = articles.get("total")
        if total_films is not None:
            print(f"影片总数 / Total videos: {total_films}")
            return total_films

    page_text = soup.get_text(" ", strip=True)
    match = re.search(r"全\s*[:：]\s*(\d+)\s*件?", page_text)
    if match:
        total_films = match.group(1)
        print(f"影片总数 / Total videos: {total_films}")
        return total_films

    film_count_element_ = soup.find("div", class_="py-4")
    if not film_count_element_:
        print("未找到影片数量容器 / Video count container not found")
        return
    film_count_element = film_count_element_.find("p", class_="text-sm leading-5")
    if film_count_element:
        film_count_text = film_count_element.get_text(strip=True)
        # print(f"影片数量信息: {film_count_text}")
        match = re.search(r"全\s*[:：]\s*(\d+)", film_count_text)
        if match:
            total_films = match.group(1)
            print(f"影片总数 / Total videos: {total_films}")
            return total_films
        else:
            print("未找到影片总数 / Total video count not found")
            return
    else:
        print("未找到影片数量信息 / Video count info not found")
        return

def extract_total_pages(soup):
    articles = get_articles_paginator(soup)
    if articles:
        try:
            return int(articles.get("last_page") or 1)
        except (TypeError, ValueError):
            return None

    page_numbers = []
    for link in soup.select('a[href*="page="]'):
        href = link.get("href") or ""
        match = re.search(r"[?&]page=(\d+)", href)
        if match:
            page_numbers.append(int(match.group(1)))
    if page_numbers:
        return max(page_numbers)

    if extract_article_items_from_dom(soup):
        return 1
    return None

def extract_article_items(soup):
    articles = get_articles_paginator(soup)
    if articles:
        return articles.get("data") or []
    dom_items = extract_article_items_from_dom(soup)
    if dom_items:
        return dom_items
    return None

def find_article_card(element):
    current = element
    for _ in range(8):
        if not current:
            break
        classes = current.get("class") or []
        if "card" in classes:
            return current
        current = current.parent
    return element.parent

def extract_title_from_article_link(link):
    title = (link.get("title") or "").strip()
    if title:
        return title
    text = link.get_text(strip=True)
    if text:
        return text
    image = link.find("img")
    if image:
        return (image.get("alt") or "").strip()
    return ""

def extract_article_items_from_dom(soup):
    """解析新 UI 已渲染出来的作品卡片，用于 Inertia deferred 数据回退。"""
    items = []
    seen_video_ids = set()

    for card in soup.select(".card"):
        article_links = []
        for link in card.select('a[href]'):
            href = link.get("href") or ""
            match = re.search(r"/articles/(\d+)(?:[/?#]|$)", href)
            if match:
                article_links.append((link, match.group(1)))
        if not article_links:
            continue

        video_id = article_links[0][1]
        if video_id in seen_video_ids:
            continue

        title = ""
        for candidate, candidate_video_id in article_links:
            if candidate_video_id != video_id:
                continue
            title = extract_title_from_article_link(candidate)
            if title and title != video_id:
                break
        if not title or title == video_id:
            title = video_id

        writer_name = "UNKNOWN"
        writer_link = card.select_one('a[href*="/writers/"]')
        if writer_link:
            writer_name = (writer_link.get("title") or writer_link.get_text(strip=True) or "UNKNOWN").strip()

        items.append({
            "video_id": video_id,
            "title": title,
            "writer": {"name": writer_name or "UNKNOWN"},
        })
        seen_video_ids.add(video_id)

    return items

def extract_film_data(soup):
    """提取影片信息"""
    global count_film, film_data_list
    article_items = extract_article_items(soup)
    if article_items is not None:
        for i, article in enumerate(article_items):
            try:
                film_number = article.get("video_id") or article.get("id")
                if not film_number:
                    raise ValueError("影片编号元素未找到，可能未正确提取")
                film_number = str(film_number).strip()

                film_title = (article.get("title") or "").strip()
                if not film_title:
                    raise ValueError("影片标题元素未找到，可能未正确提取")

                writer = article.get("writer") or {}
                producer = (writer.get("name") if isinstance(writer, dict) else None) or "UNKNOWN"
                producer = str(producer).strip() or "UNKNOWN"

                film_data_list.append({
                    "film_number": film_number,
                    "film_title": film_title,
                    "producer": producer
                })

                print("-" * 50)
                count_film += 1
                print(f"第{count_film}个影片 / Video #{count_film}")
                print(f"影片编号 / Video ID: {film_number}")
                print(f"影片名称 / Video Title: {film_title}")
                print(f"制作人 / Producer: {producer}")
            except Exception as e:
                error_type = type(e).__name__
                print(f"跳过第 {i + 1} 个影片 / Skipping video #{i + 1} ({error_type}: {e})")
        return

    containers = soup.find_all("div", class_="2xl:w-1/6 xl:w-1/5 lg:w-1/4 md:w-1/2 w-full p-4")
    for i, container in enumerate(containers):
        try:
            number_element = container.find("span", class_="absolute top-0 left-0 text-white bg-gray-800 bg-opacity-90 px-1")
            if not number_element:
                number_element = container.find("span", class_="absolute top-0 left-0 text-white bg-gray-800 px-1")
            if not number_element:
                raise ValueError("影片编号元素未找到，可能未正确提取")  
            else:
                film_number = number_element.get_text(strip=True)

            film_title_element = container.find("a", class_="text-white title-font text-base font-medium line-clamp-2")
            if not film_title_element:
                raise ValueError("影片标题元素未找到，可能未正确提取")
            else:
                film_title = film_title_element.get("title", "").strip()

            producer_element = container.find("a", class_="text-blue-600 dark:text-blue-700 line-clamp-1")
            if not producer_element:
                # raise ValueError("制作人元素未找到，可能未正确提取")
                producer = "UNKNOWN"
            else:
                producer = producer_element.get("title", "").strip()

            # 保存影片数据到列表
            film_data_list.append({
                "film_number": film_number,
                "film_title": film_title,
                "producer": producer
            })
            
            print("-" * 50)
            count_film += 1
            print(f"第{count_film}个影片 / Video #{count_film}")
            print(f"影片编号 / Video ID: {film_number}")
            print(f"影片名称 / Video Title: {film_title}")
            print(f"制作人 / Producer: {producer}")
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"跳过第 {i + 1} 个影片卡片 / Skipping video card #{i + 1} ({error_type}: {e})")

def extract_actress_info(soup):
    """提取演员名称和头像信息"""
    try:
        props = get_inertia_props(soup)
        actress = props.get("actress")
        if isinstance(actress, dict):
            actress_name = (actress.get("name") or "").strip()
            if actress_name:
                print(f"演员名称 / Actress Name: {actress_name}")
                return actress_name

        # # 提取头像 URL
        # avatar_element = soup.find("div", class_="h-24 w-24 overflow-hidden rounded-full bg-gray-100 shadow-lg")
        # avatar_url = avatar_element.find("img", class_="lazyload")["src"].strip()
        # if avatar_url.startswith("/"):
        #     avatar_url = SITE_BASE_URL + avatar_url
        
        # 提取演员名称
        name_element = soup.find("div", class_="sm:w-11/12 px-2 text-white title-font text-lg font-medium")
        if not name_element:
            raise ValueError("演员名称元素未找到")
        actress_name = next(
            (
                text.strip()
                for text in name_element.contents
                if isinstance(text, NavigableString) and text.strip()
            ),
            "",
        )
        if not actress_name:
            raise ValueError("演员名称为空")
        # .replace("\n", "").replace(" ", "")
        
        print(f"演员名称 / Actress Name: {actress_name}")
        # print(f"头像 URL: {avatar_url}")
        
        return actress_name#, avatar_url
    except Exception as e:
        error_type = type(e).__name__
        print(f"提取演员信息失败 / Failed to extract actress info ({error_type})")
        return None#, None

def safe_filename(filename,replace_char=" "):
    illegal_english_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

    for char in illegal_english_chars:
        filename = filename.replace(char, replace_char)

    return filename.strip()

def truncate_folder_name(folder_name):
    if len(folder_name) < MAX_FILM_FOLDER_NAME_LENGTH:
        return folder_name
    keep_length = MAX_FILM_FOLDER_NAME_LENGTH - len(FOLDER_TRUNCATION_SUFFIX)
    return folder_name[:keep_length].rstrip() + FOLDER_TRUNCATION_SUFFIX

def create_film_folders(actress_folder, film_data):
    """
    创建文件夹结构
    :param actress_folder: 演员文件夹路径
    :param film_data: 包含影片编号、制作人和影片名称的列表
    """
    
        
    # 创建影片子文件夹
    for film in film_data:
        film_number = film.get("film_number", "未知编号")
        producer = film.get("producer", "未知制作人")
        film_title = film.get("film_title", "未知影片名称")
        
        producer = safe_filename(producer)
        film_title = safe_filename(film_title)
        
        # 格式化子文件夹名称
        folder_name = f"fc2-ppv-{film_number} {producer}-{film_title}"
        folder_name = truncate_folder_name(folder_name)
        folder_path = os.path.join(actress_folder, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            # print(f"创建影片文件夹 / Creating video folder: {folder_path}")
            # # 创建 nothing.txt
            # with open(os.path.join(folder_path, "nothing.txt"), "w") as f:
            #     pass

def create_shortcut(folder_path, url, shortcut_name):
    """
    创建快捷方式
    :param folder_path: 快捷方式保存的文件夹路径
    :param url: 快捷方式指向的 URL
    :param shortcut_name: 快捷方式的名称
    """
    shortcut_path = os.path.join(folder_path, f"{shortcut_name}.url")
    with open(shortcut_path, "w") as shortcut_file:
        shortcut_file.write(f"[InternetShortcut]\nURL={url}\n")
    print(f"创建快捷方式 / Creating shortcut: {shortcut_path}")
    
def download_avatar(folder_path, avatar_url, avatar_name="avatar.jpg"):
    """
    下载头像并保存到指定文件夹
    :param folder_path: 保存头像的文件夹路径
    :param avatar_url: 头像的 URL
    """
    try:
        response = requests.get(avatar_url, stream=True)
        if response.status_code == 200:
            avatar_path = os.path.join(folder_path, avatar_name)
            with open(avatar_path, "wb") as avatar_file:
                for chunk in response.iter_content(1024):
                    avatar_file.write(chunk)
            print(f"头像已下载: {avatar_path}")
        else:
            print(f"下载头像失败，状态码: {response.status_code}")
    except Exception as e:
        error_type = type(e).__name__
        print(f"下载头像时出错 / Failed to download avatar ({error_type})")

def parse_chrome_major_version(version_text):
    match = re.search(r"(\d+)\.", version_text)
    if match:
        return int(match.group(1))
    return None

def detect_chrome_major_version():
    """检测本机 Chrome 主版本，避免 ChromeDriver 与浏览器版本不匹配。"""
    chrome_paths = [
        os.getenv("CHROME_BINARY"),
        os.path.join(os.getenv("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.getenv("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]

    for chrome_path in chrome_paths:
        if not chrome_path or not os.path.exists(chrome_path):
            continue
        try:
            result = subprocess.run(
                [chrome_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            major_version = parse_chrome_major_version(result.stdout or result.stderr)
            if major_version:
                print(f"Detected Chrome major version: {major_version}")
                return major_version
        except Exception:
            pass

    if winreg:
        registry_paths = [
            r"SOFTWARE\Google\Chrome\BLBeacon",
            r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon",
        ]
        for registry_path in registry_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                major_version = parse_chrome_major_version(version)
                if major_version:
                    print(f"Detected Chrome major version: {major_version}")
                    return major_version
            except OSError:
                pass

            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                    version, _ = winreg.QueryValueEx(key, "version")
                major_version = parse_chrome_major_version(version)
                if major_version:
                    print(f"Detected Chrome major version: {major_version}")
                    return major_version
            except OSError:
                pass

    return None

def create_driver():
    """初始化 undetected-chromedriver（绕过 Cloudflare 反爬检测）"""
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument('--headless')  # 如需无头模式，取消此注释

    chrome_version = os.getenv("CHROME_VERSION_MAIN")
    kwargs = {"options": options, "use_subprocess": True}
    if chrome_version:
        kwargs["version_main"] = int(chrome_version)
    else:
        detected_version = detect_chrome_major_version()
        if detected_version:
            kwargs["version_main"] = detected_version

    driver = uc.Chrome(**kwargs)
    driver.maximize_window()
    return driver

def load_cookies_from_netscape_file(file_path):
    # cf_clearance 由浏览器自行获取，不从文件加载（不同会话的 cf_clearance 不通用）
    SKIP_NAMES = {"cf_clearance"}
    cookies = []
    now = time.time()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#HttpOnly_"):
                    line = line[len("#HttpOnly_"):]
                elif line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 6:
                    domain = parts[0]
                    name = parts[5]
                    if name in SKIP_NAMES:
                        continue
                    if not cookie_domain_matches(domain, SITE_HOST):
                        print(f"跳过非本站 Cookie / Skipping cookie for another domain: {domain} ({name})")
                        continue
                    expiry = int(parts[4]) if parts[4].isdigit() else 0
                    if expiry > 0 and expiry < now:
                        continue  # skip expired cookies
                    cookie = {
                        'domain': domain,
                        'path': parts[2],
                        'name': name,
                        'value': parts[6] if len(parts) > 6 else ""
                    }
                    if expiry > 0:
                        cookie["expiry"] = expiry
                    if len(parts) > 3:
                        cookie["secure"] = parts[3].upper() == "TRUE"
                    cookies.append(cookie)
    except Exception as e:
        error_type = type(e).__name__
        print(f"加载 Cookies 失败 / Failed to load cookies from {file_path} ({error_type})")
    return cookies

def cookie_domain_matches(cookie_domain, site_host):
    cookie_domain = cookie_domain.lstrip(".").lower()
    site_host = site_host.lower()
    return site_host == cookie_domain or site_host.endswith("." + cookie_domain)

def unique_existing_paths(paths):
    seen = set()
    existing_paths = []
    for path in paths:
        absolute_path = os.path.abspath(path)
        normalized_path = os.path.normcase(absolute_path)
        if normalized_path in seen:
            continue
        seen.add(normalized_path)
        if os.path.exists(absolute_path):
            existing_paths.append(absolute_path)
    return existing_paths

def find_cookie_file(filename=COOKIE_FILENAME):
    """优先读取当前启动目录，其次读取脚本所在目录。"""
    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(SCRIPT_DIR, filename),
    ]
    existing_paths = unique_existing_paths(candidates)
    return existing_paths[0] if existing_paths else None

def wait_for_manual_browser_session(driver):
    print(
        "未找到新站 Cookie 文件。浏览器已打开 fc2cmadb.com；"
        "请在浏览器中登录并完成站点确认，然后回到此窗口按 Enter 继续。"
    )
    print("如果你已经不需要登录，也可以直接按 Enter。")
    try:
        input("登录/确认完成后按 Enter 继续...")
    except EOFError:
        print("当前环境无法等待输入，将继续尝试使用现有浏览器会话。")

# 模拟设置 Cookie 的函数
def simulate_cookies():
    session = requests.Session()

    # 设置 Cookie
    cookies = {
        'example_cookie': 'example_value',
        'another_cookie': 'another_value'
    }
    session.cookies.update(cookies)

    # 示例请求
    url = 'https://example.com'
    try:
        response = session.get(url)
        print("Response status code:", response.status_code)
        print("Response content:", response.text[:200])  # 打印部分内容
    except requests.RequestException as e:
        print(f"Error during request: {e}")


# 在 extract_film_data 函数中收集影片数据
film_data_list = []
count_film = 0

def validate_film_count(extracted_count, expected_count):
    if expected_count is None:
        print("未获取网页显示总数，跳过严格数量校验 / Expected total not found, skipping strict count validation")
        return True

    print(
        f"数量校验 / Count validation: 提取数量={extracted_count}，"
        f"网页显示数量={expected_count}"
    )
    if extracted_count == expected_count:
        print("数量校验通过 / Count validation passed")
        return True

    print("数量校验失败 / Count validation failed")
    print(f"差异 / Difference: {abs(extracted_count - expected_count)} 个影片")
    return False

def main():
    global count_film, film_data_list

    driver = None
    film_data_list = []
    count_film = 0
    page = 1
    target_actress_id = choose_actress_id(actresses_id)

    try:
        driver = create_driver()

        # 先访问主页（uc.Chrome 会自动通过 Cloudflare 并获取新的 cf_clearance）
        driver.get(SITE_BASE_URL)
        time.sleep(3)

        print("#" * 60)

        # 加载 Cookie（登录态等）——不加载 cf_clearance，保留浏览器自己的新会话
        cookie_file = find_cookie_file()
        if cookie_file:
            print(f"Loading cookies from {cookie_file}")
            cookies = load_cookies_from_netscape_file(cookie_file)
            loaded = 0
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                    loaded += 1
                except Exception:
                    pass
            print(f"Loaded {loaded}/{len(cookies)} cookies")
        else:
            print(f"Cookie file not found: {COOKIE_FILENAME}")
            old_cookie_file = find_cookie_file(OLD_COOKIE_FILENAME)
            if old_cookie_file:
                print(
                    f"检测到旧域名 Cookie 文件 {old_cookie_file}；"
                    f"新站需要导出 {COOKIE_FILENAME}。"
                )
            wait_for_manual_browser_session(driver)

        driver.get(SITE_BASE_URL)
        time.sleep(2)

        print("#" * 60)

        # 打开目标网页（第一页，同时用于提取演员信息）
        url = f"{SITE_BASE_URL}/actresses/{target_actress_id}?page=1"
        driver.get(url)
        if not wait_for_page_load(driver):
            print("目标页面未加载影片卡片，程序终止。 / Target page did not load video cards. Exiting.")
            return 1

        soup = parse_html(driver)
        if not soup:
            print("未能成功解析网页内容，程序终止。 / Failed to parse page content. Exiting.")
            return 1

        # 提取演员信息
        actress_name = extract_actress_info(soup)
        # actress_name, avatar_url = extract_actress_info(soup)
        if not actress_name:
            print("无法获取演员名称，程序终止。 / Cannot get actress name. Exiting.")
            return 1

        print("#" * 60)

        # 创建演员文件夹
        actress_folder = os.path.join(OUTPUT_DIR, safe_filename(actress_name))

        if os.path.exists(actress_folder):
            suffix = 1
            while os.path.exists(f"{actress_folder}_{suffix}"):
                suffix += 1
            actress_folder = f"{actress_folder}_{suffix}"
            print(f"演员文件夹已存在，改用 / Actress folder exists, using: {actress_folder}")

        # 提取影片数量，计算总页数
        film_count = extract_film_count(soup)
        if film_count is not None:
            num_films = int(film_count)
            total_pages = max(extract_total_pages(soup) or 1, max(1, (num_films + 29) // 30))
            print(f"总影片数 / Total films: {num_films}，总页数 / Total pages: {total_pages}")
        else:
            num_films = None
            total_pages = extract_total_pages(soup)
            if total_pages:
                print(f"无法获取影片数量，检测到总页数 / Cannot get film count, detected total pages: {total_pages}")
            else:
                print("无法获取影片数量，将逐页抓取直到空页 / Cannot get film count, will fetch until empty")

        print("#" * 60)
        print("开始提取影片数据 / Starting to extract video data...")
        print("#" * 60)

        url_1 = f"{SITE_BASE_URL}/actresses/{target_actress_id}"

        # 逐页加载影片数据（直接读取 Inertia JSON，保留旧 DOM 解析作为回退）
        while True:
            if total_pages is not None and page > total_pages:
                break
            print("#" * 60)
            print(f"正在获取第 {page} 页 / Fetching page {page}")
            if page == 1:
                # 第一页已加载，直接使用当前 soup
                page_soup = soup
            else:
                page_soup = fetch_actress_articles(driver, target_actress_id, page)
            if page_soup is None:
                break
            article_items = extract_article_items(page_soup)
            containers = page_soup.find_all("div", class_="2xl:w-1/6 xl:w-1/5 lg:w-1/4 md:w-1/2 w-full p-4")
            if article_items is not None and not article_items:
                print(f"第 {page} 页无影片数据，停止翻页 / No film data on page {page}, stopping")
                break
            if article_items is None and not containers:
                print(f"第 {page} 页无影片数据，停止翻页 / No film data on page {page}, stopping")
                break
            extract_film_data(page_soup)
            page += 1

        print("#" * 60)
        extracted_count = len(film_data_list)
        print(f"共提取到 {extracted_count} 个影片数据 / Total videos extracted: {extracted_count}")
        if not validate_film_count(extracted_count, num_films):
            print("提取数量与网页显示总数不一致，停止创建文件夹。 / Count mismatch, stop before creating folders.")
            print("#" * 60)
            return 1

        print("#" * 60)
        print("创建文件夹 / Starting to create folders...")

        os.makedirs(actress_folder)
        print(f"创建演员文件夹 / Creating actress folder: {actress_folder}")

        # 在提取完所有影片数据后创建文件夹
        create_film_folders(actress_folder, film_data_list)

        first_film_id = film_data_list[0]["film_number"] if film_data_list else "未知ID"

        print("#" * 60)

        # 创建快捷方式
        shortcut_name = f"id_{target_actress_id} - latest_{first_film_id}"
        create_shortcut(actress_folder, url_1, shortcut_name)

        # # 下载头像
        # download_avatar(actress_folder, avatar_url, avatar_name=f'id_{target_actress_id}'+'.png')

        print("#" * 60)
        if num_films is not None:
            print("所有操作完成，数量校验成功！ / All operations completed, count validation passed!")
        else:
            print("所有操作完成（未获取网页显示总数，未进行严格数量校验）。 / All operations completed without strict count validation.")
        print("#" * 60)
        return 0
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    raise SystemExit(main())
