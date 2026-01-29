from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re
import os
import requests
import winshell  # 用于创建快捷方式
from selenium.webdriver.firefox.options import Options

def click_enter_button(driver, timeout=10):
    """等待并点击 ENTER 按钮"""
    try:
        enter_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "text-white"))
        )
        enter_button.click()
    except Exception as e:
        print(f"Error clicking the button: {e}")

def wait_for_element(driver, class_name, timeout=10):
    """等待指定元素加载完成"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name))
        )
        return element
    except Exception as e:
        print(f"Error: {e}")
        return None

def parse_html(driver):
    """获取并解析网页 HTML"""
    html_content = driver.page_source
    return BeautifulSoup(html_content, "html.parser")

def extract_film_count(soup):
    """提取影片数量信息"""
    film_count_element_ = soup.find("div", class_="py-4")
    if not film_count_element_:
        print("未找到影片数量容器 / Video count container not found")
        return
    film_count_element = film_count_element_.find("p", class_="text-sm leading-5")
    if film_count_element:
        film_count_text = film_count_element.get_text(strip=True)
        # print(f"影片数量信息: {film_count_text}")
        match = re.search(r"全：\s*(\d+)", film_count_text)
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


def extract_film_data(soup):
    """提取影片信息"""
    global film_data_list
    containers = soup.find_all("div", class_="2xl:w-1/6 xl:w-1/5 lg:w-1/4 md:w-1/2 w-full p-4")
    for i, container in enumerate(containers):
        # try:
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
            global count_film
            count_film += 1
            print(f"第{count_film}个影片 / Video #{count_film}")
            print(f"影片编号 / Video ID: {film_number}")
            print(f"影片名称 / Video Title: {film_title}")
            print(f"制作人 / Producer: {producer}")
            
        # except Exception as e:
        #     print(f"Error extracting data: {e}")

def extract_actress_info(soup):
    """提取演员名称和头像信息"""
    try:
        # # 提取头像 URL
        # avatar_element = soup.find("div", class_="h-24 w-24 overflow-hidden rounded-full bg-gray-100 shadow-lg")
        # avatar_url = avatar_element.find("img", class_="lazyload")["src"].strip()
        # if avatar_url.startswith("/"):
        #     avatar_url = "https://fc2ppvdb.com" + avatar_url
        
        # 提取演员名称
        name_element = soup.find("div", class_="sm:w-11/12 px-2 text-white title-font text-lg font-medium")
        actress_name = name_element.next.strip()
        # .replace("\n", "").replace(" ", "")
        
        print(f"演员名称 / Actress Name: {actress_name}")
        # print(f"头像 URL: {avatar_url}")
        
        return actress_name#, avatar_url
    except Exception as e:
        print(f"Error extracting actress info: {e}")
        return None#, None

def safe_filename(filename,replace_char=" "):
    illegal_english_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

    for char in illegal_english_chars:
        filename = filename.replace(char, replace_char)

    return filename.strip()

def create_film_folders(actress_name, film_data):
    """
    创建文件夹结构
    :param actress_name: 演员名称
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
        folder_path = os.path.join(actress_folder, folder_name)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"创建影片文件夹 / Creating video folder: {folder_path}")

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
        print(f"下载头像时出错: {e}")

def load_cookies_from_netscape_file(file_path):
    cookies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 6:
                    cookie = {
                        'domain': parts[0],
                        'path': parts[2],
                        'name': parts[5],
                        'value': parts[6] if len(parts) > 6 else ""
                    }
                    cookies.append(cookie)
    except Exception as e:
        print(f"Error loading cookies from {file_path}: {e}")
    return cookies

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

'''
设置演员ID
'''
actresses_id = 11126  # 替换为你想抓取的演员ID  

# 在 extract_film_data 函数中收集影片数据
film_data_list = []

# 初始化webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


# 设置 User-Agent
options = Options()
options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")

driver = webdriver.Firefox(options=options)
driver.get("https://fc2ppvdb.com")  # 打开一个初始页面以设置 Cookie 和 User-Agent

# 加载并设置 Cookie
cookie_file = "fc2ppvdb.com_cookies.txt"
if os.path.exists(cookie_file):
    print(f"Loading cookies from {cookie_file}")
    cookies = load_cookies_from_netscape_file(cookie_file)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error adding cookie {cookie['name']}: {e}")
else:
    print(f"Cookie file not found: {cookie_file}")

# 打开我们要抓取的网页
url = "https://fc2ppvdb.com/cookie/setage"
driver.get(url)

click_enter_button(driver)

count_film = 0
page=1

# 打开目标网页
url = f"https://fc2ppvdb.com/actresses/{actresses_id}"
driver.get(url)
wait_for_element(driver, "lazyload-wrapper")
soup = parse_html(driver)

# 提取演员信息
actress_name = extract_actress_info(soup)
# actress_name, avatar_url = extract_actress_info(soup)

# 创建演员文件夹
actress_folder = os.path.join(os.getcwd(), actress_name)

if not os.path.exists(actress_folder):
    os.makedirs(actress_folder)
    print(f"创建演员文件夹 / Creating actress folder: {actress_folder}")
else:
    print(f"演员文件夹已存在 / Actress folder exists: {actress_folder}")

    driver.quit()
    exit()

    # actress_folder += '_'
    # os.makedirs(actress_folder)
    # print(f"创建演员文件夹: {actress_folder}")

# 提取影片数量
if not soup:
    print("未能成功解析网页内容，程序终止。 / Failed to parse page content. Exiting.")
    driver.quit()
    exit()
num_films=int(extract_film_count(soup))

# 提取影片数据
extract_film_data(soup)

url_1 = f"https://fc2ppvdb.com/actresses/{actresses_id}"

while num_films//40>=page:
    page+=1
    url = f"https://fc2ppvdb.com/actresses/{actresses_id}?page={page}"
    print(f"正在打开 / Opening: {url}")
    driver.get(url)
    wait_for_element(driver, "lazyload-wrapper")
    soup = parse_html(driver)
    
    # 提取影片数据
    extract_film_data(soup)

print("-" * 50)
print(f"共提取到 {len(film_data_list)} 个影片数据 / Total videos extracted: {len(film_data_list)}")

# 在提取完所有影片数据后创建文件夹
create_film_folders(actress_name, film_data_list)

first_film_id = film_data_list[0]["film_number"] if film_data_list else "未知ID"

# 创建快捷方式
actress_folder = os.path.join(os.getcwd(), actress_name)
shortcut_name = f"id_{actresses_id} - latest_{first_film_id}"
create_shortcut(actress_folder, url_1, shortcut_name)

# # 下载头像
# download_avatar(actress_folder, avatar_url, avatar_name=f'id_{actresses_id}'+'.png')

# 关闭webdriver
driver.quit()

print("所有操作完成！ / All operations completed!")