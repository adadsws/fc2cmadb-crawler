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
import shutil
import unicodedata
import requests
from dataclasses import dataclass
from urllib.parse import urlparse

from .browser import PersistentBrowser
from .naming import format_film_folder_name, safe_filename

from .config import (
    DEFAULT_ACTRESS_ID,
    OUTPUT_DIR,
    SITE_BASE_URL,
)

for output_stream in (sys.stdout, sys.stderr):
    if hasattr(output_stream, "reconfigure"):
        output_stream.reconfigure(errors="replace")


MIN_WRAP_TEXT_WIDTH = 24
FALLBACK_CONSOLE_WIDTH = 100


@dataclass(frozen=True)
class CrawlerTarget:
    """一次输入任务；kind 为 actress_id 或 fc2_number。"""

    kind: str
    value: str


def get_text_width(text):
    width = 0
    for char in str(text):
        if char == "\t":
            width += 4
        elif unicodedata.combining(char):
            continue
        elif unicodedata.east_asian_width(char) in {"F", "W"}:
            width += 2
        else:
            width += 1
    return width


def split_text_by_width(text, max_width):
    parts = []
    current = []
    current_width = 0

    for char in str(text):
        char_width = get_text_width(char)
        if current and current_width + char_width > max_width:
            parts.append("".join(current))
            current = []
            current_width = 0
        current.append(char)
        current_width += char_width

    if current:
        parts.append("".join(current))
    return parts or [""]


def wrap_text_by_width(text, max_width):
    tokens = re.findall(r"\s+|\S+", str(text))
    if not tokens:
        return [""]

    lines = []
    current = ""
    current_width = 0

    for token in tokens:
        if token.isspace():
            if current and current_width + 1 <= max_width:
                current += " "
                current_width += 1
            continue

        token_width = get_text_width(token)
        if current_width + token_width <= max_width:
            current += token
            current_width += token_width
            continue

        if current:
            lines.append(current.rstrip())
            current = ""
            current_width = 0

        if token_width <= max_width:
            current = token
            current_width = token_width
            continue

        split_parts = split_text_by_width(token, max_width)
        lines.extend(split_parts[:-1])
        current = split_parts[-1]
        current_width = get_text_width(current)

    if current or not lines:
        lines.append(current.rstrip())
    return lines


def print_wrapped(prefix, message, continuation_prefix=None):
    if continuation_prefix is None:
        continuation_prefix = " " * len(prefix)

    console_width = shutil.get_terminal_size(
        fallback=(FALLBACK_CONSOLE_WIDTH, 20)
    ).columns
    console_width = max(console_width, MIN_WRAP_TEXT_WIDTH + get_text_width(prefix))
    first_width = max(MIN_WRAP_TEXT_WIDTH, console_width - get_text_width(prefix))
    next_width = max(
        MIN_WRAP_TEXT_WIDTH,
        console_width - get_text_width(continuation_prefix),
    )

    is_first_line = True
    for paragraph in str(message).splitlines() or [""]:
        line_width = first_width if is_first_line else next_width
        wrapped_lines = wrap_text_by_width(paragraph, line_width)
        for wrapped_index, wrapped_line in enumerate(wrapped_lines):
            if is_first_line and wrapped_index == 0:
                print(f"{prefix}{wrapped_line}")
            else:
                print(f"{continuation_prefix}{wrapped_line}")
        is_first_line = False


def print_section(title, level=0):
    indent = "  " * level
    print()
    print_wrapped(f"{indent}== ", title)


def print_step(message, level=1, marker=">"):
    print_wrapped(f"{'  ' * level}{marker} ", message)


def print_detail(message, level=2, marker="-"):
    print_step(message, level=level, marker=marker)


def _prompt_digits(prompt):
    """读取纯数字输入；b 返回主菜单，q 或 EOF 退出。"""
    while True:
        try:
            value = input(prompt).strip()
        except EOFError:
            return "q"
        if value.lower() == "b":
            return "b"
        if value.lower() == "q":
            return "q"
        if value.isdigit():
            return value
        print_step("输入无效，请只输入数字 / Invalid input, please enter digits only")


def choose_crawler_target(default_actress_id, current_mode=None):
    """在选定模式中连续读取目标；b 返回模式菜单，q 退出。"""
    default_actress_id = str(default_actress_id).strip()
    while True:
        if current_mode is None:
            print_section("输入模式 / Input mode")
            print_step("输入 1：演员 ID 模式 / Enter 1: actress ID mode")
            print_step("输入 2：FC2 番号模式 / Enter 2: FC2 number mode")
            print_step("输入 q 退出 / Enter q to quit")
            try:
                value = input("请选择模式（1、2 或 q）: ").strip()
            except EOFError:
                print_step("输入流已关闭，退出任务菜单 / Input stream closed; exiting task menu")
                return None
            if value.lower() == "q":
                return None
            if value not in {"1", "2"}:
                print_step("请输入 1 或 2 选择模式；输入 q 退出")
                continue
            current_mode = "actress_id" if value == "1" else "fc2_number"

        if current_mode == "actress_id":
            actress_id = _prompt_digits(
                f"请输入演员 ID（如：{default_actress_id}；b 返回，q 退出）: ",
            )
            if actress_id == "q":
                return None
            if actress_id != "b":
                print_step(f"使用演员 ID / Using actress ID: {actress_id}")
                return CrawlerTarget("actress_id", actress_id)
        else:
            fc2_number = _prompt_digits("请输入纯数字 FC2 番号（如：1035965；b 返回，q 退出）: ")
            if fc2_number == "q":
                return None
            if fc2_number != "b":
                print_step(f"使用 FC2 番号 / Using FC2 number: {fc2_number}")
                return CrawlerTarget("fc2_number", fc2_number)
        current_mode = None


def choose_actress_id(default_actress_id):
    """兼容旧调用方：只返回演员 ID；FC2 模式返回 None。"""
    target = choose_crawler_target(default_actress_id)
    if target is None or target.kind != "actress_id":
        return None
    return target.value


def click_enter_button(driver, timeout=10):
    """等待并点击 ENTER 按钮"""
    try:
        enter_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "text-white"))
        )
        enter_button.click()
    except Exception as e:
        error_type = type(e).__name__
        print_detail(f"点击按钮失败 / Failed to click button ({error_type})", marker="!")

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
        print_detail(f"等待元素超时 / Element wait timeout: {class_name} ({error_type})", marker="!")
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
        if describe_inertia_error(page_data, current_url=driver.current_url, page_title=driver.title):
            return False
        return True
    except Exception as e:
        error_type = type(e).__name__
        print_detail(f"等待页面加载超时 / Page load timeout ({error_type})", marker="!")
        return False

def build_actress_page_url(actress_id, page=1):
    """构造演员分页 URL，始终显式指定页码。"""
    return f"{SITE_BASE_URL}/actresses/{actress_id}?page={page}"


def build_article_page_url(fc2_number):
    """构造纯数字 FC2 番号对应的作品详情页 URL。"""
    value = str(fc2_number).strip()
    if not value.isdigit():
        raise ValueError("FC2 番号必须为纯数字")
    return f"{SITE_BASE_URL}/articles/{value}"


def fetch_actress_articles(browser, actress_id, page):
    """导航到指定页并等待影片卡片加载完成，返回解析后的 soup"""
    url = build_actress_page_url(actress_id, page)
    browser.navigate(url)
    driver = browser.driver
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
                print_detail(f"Inertia JSON 解析失败 / Failed to parse Inertia JSON ({e})", marker="!")

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


def _collect_actress_ids(value, result):
    """只在演员语义节点内递归收集数字 ID，避免误取用户或制作商 ID。"""
    if isinstance(value, dict):
        direct_id = value.get("id") or value.get("actress_id") or value.get("actressId")
        if direct_id is not None and str(direct_id).isdigit():
            result.add(str(direct_id))
            return
        for child in value.values():
            if isinstance(child, (dict, list)):
                _collect_actress_ids(child, result)
    elif isinstance(value, list):
        for child in value:
            _collect_actress_ids(child, result)


def extract_actress_ids_from_article(soup):
    """从作品详情页 Inertia 主体或主内容演员链接提取演员 ID。"""
    result = set()
    props = get_inertia_props(soup)
    article = props.get("article") or props.get("video") or props.get("post")
    if isinstance(article, dict):
        for key in ("actress", "actresses", "cast", "casts", "performer", "performers"):
            if key in article:
                _collect_actress_ids(article[key], result)
        for key in ("actress_id", "actressId"):
            value = article.get(key)
            if value is not None and str(value).isdigit():
                result.add(str(value))

    if not result:
        for key in ("actress", "actresses", "cast", "casts", "performer", "performers"):
            if key in props:
                _collect_actress_ids(props[key], result)

    if result:
        return sorted(result, key=int)

    main = soup.select_one("main article, article, main") or soup
    for link in main.select('a[href*="/actresses/"]'):
        match = re.search(r"/actresses/(\d+)(?:[/?#]|$)", link.get("href") or "")
        if match:
            result.add(match.group(1))
    return sorted(result, key=int)


def article_resolution_is_ready(driver):
    """等待详情页出现错误状态或可解析演员，避免早于前端 hydration 读取 DOM。"""
    soup = parse_html(driver)
    page_data = extract_inertia_page_data(soup)
    if isinstance(page_data, dict):
        props = page_data.get("props") or {}
        if page_data.get("component") == "Error" or props.get("status"):
            return True
    return bool(extract_actress_ids_from_article(soup))


def resolve_actress_id_from_fc2_number(browser, fc2_number):
    """访问 FC2 作品详情并要求唯一演员 ID。"""
    url = build_article_page_url(fc2_number)
    print_step(f"打开 FC2 作品详情 / Opening FC2 article: {url}")
    browser.navigate(url)
    driver = browser.driver
    try:
        WebDriverWait(driver, 40).until(
            article_resolution_is_ready
        )
    except Exception as e:
        print_detail(f"等待 FC2 作品详情超时 / Article load timeout ({type(e).__name__})", marker="!")
        return None

    soup = parse_html(driver)
    page_data = extract_inertia_page_data(soup)
    if describe_inertia_error(page_data, current_url=driver.current_url, page_title=driver.title):
        return None
    actress_ids = extract_actress_ids_from_article(soup)
    if not actress_ids:
        print_detail(f"FC2 番号 {fc2_number} 未找到演员 ID。", marker="!")
        return None
    if len(actress_ids) != 1:
        print_detail(
            f"FC2 番号 {fc2_number} 对应多个演员 ID：{', '.join(actress_ids)}；已拒绝自动选择。",
            marker="!",
        )
        return None
    actress_id = actress_ids[0]
    print_step(f"FC2 番号 {fc2_number} 对应演员 ID：{actress_id}")
    return actress_id

def get_articles_paginator(soup):
    props = get_inertia_props(soup)
    articles = props.get("articles")
    if isinstance(articles, dict) and isinstance(articles.get("data"), list):
        return articles
    return None

def describe_inertia_error(page_data, current_url=None, page_title=None):
    if not isinstance(page_data, dict):
        return False
    props = page_data.get("props") or {}
    component = page_data.get("component")
    status = props.get("status")
    if component != "Error" and not status:
        return False

    print_section("页面错误 / Page error", level=1)
    print_step(f"页面返回错误 / Page returned error: {status or component}", level=2, marker="!")
    if current_url:
        print_detail(f"错误页面 URL / Error URL: {current_url}", level=3)
    if page_title:
        print_detail(f"页面标题 / Page title: {page_title}", level=3)

    status_text = str(status or "")
    if status_text == "404":
        print_detail(
            "目标页面不存在或已被删除。请检查演员 ID 是否仍然有效，"
            "或是否需要使用新站更新后的 ID。",
            level=3,
            marker="!",
        )
        print_detail(
            "Target page was not found or has been deleted. "
            "Please check whether the actress ID is still valid or has changed on the new site.",
            level=3,
            marker="!",
        )

    auth = props.get("auth") or {}
    if status == 403 and not auth.get("user"):
        print_detail(
            "当前持久浏览器 profile 未登录或没有访问权限。请在已打开的浏览器中登录 "
            "fc2cmadb.com，然后返回终端继续。",
            level=3,
            marker="!",
        )
    return True

def extract_film_count(soup):
    """提取影片数量信息"""
    articles = get_articles_paginator(soup)
    if articles:
        total_films = articles.get("total")
        if total_films is not None:
            print_step(f"影片总数 / Total videos: {total_films}")
            return total_films

    page_text = soup.get_text(" ", strip=True)
    match = re.search(r"全\s*[:：]\s*(\d+)\s*件?", page_text)
    if match:
        total_films = match.group(1)
        print_step(f"影片总数 / Total videos: {total_films}")
        return total_films

    film_count_element_ = soup.find("div", class_="py-4")
    if not film_count_element_:
        print_detail("未找到影片数量容器 / Video count container not found", marker="!")
        return
    film_count_element = film_count_element_.find("p", class_="text-sm leading-5")
    if film_count_element:
        film_count_text = film_count_element.get_text(strip=True)
        # print(f"影片数量信息: {film_count_text}")
        match = re.search(r"全\s*[:：]\s*(\d+)", film_count_text)
        if match:
            total_films = match.group(1)
            print_step(f"影片总数 / Total videos: {total_films}")
            return total_films
        else:
            print_detail("未找到影片总数 / Total video count not found", marker="!")
            return
    else:
        print_detail("未找到影片数量信息 / Video count info not found", marker="!")
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

                count_film += 1
                print_detail(f"第 {count_film} 个影片 / Video #{count_film}")
                print_detail(f"影片编号 / Video ID: {film_number}", level=3, marker="*")
                print_detail(f"影片名称 / Video Title: {film_title}", level=3, marker="*")
                print_detail(f"制作人 / Producer: {producer}", level=3, marker="*")
            except Exception as e:
                error_type = type(e).__name__
                print_detail(f"跳过第 {i + 1} 个影片 / Skipping video #{i + 1} ({error_type}: {e})")
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
            
            count_film += 1
            print_detail(f"第 {count_film} 个影片 / Video #{count_film}")
            print_detail(f"影片编号 / Video ID: {film_number}", level=3, marker="*")
            print_detail(f"影片名称 / Video Title: {film_title}", level=3, marker="*")
            print_detail(f"制作人 / Producer: {producer}", level=3, marker="*")
            
        except Exception as e:
            error_type = type(e).__name__
            print_detail(f"跳过第 {i + 1} 个影片卡片 / Skipping video card #{i + 1} ({error_type}: {e})")

def extract_actress_info(soup):
    """提取演员名称和头像信息"""
    try:
        props = get_inertia_props(soup)
        actress = props.get("actress")
        if isinstance(actress, dict):
            actress_name = (actress.get("name") or "").strip()
            if actress_name:
                print_step(f"演员名称 / Actress Name: {actress_name}")
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
        
        print_step(f"演员名称 / Actress Name: {actress_name}")
        # print(f"头像 URL: {avatar_url}")
        
        return actress_name#, avatar_url
    except Exception as e:
        error_type = type(e).__name__
        print_detail(f"提取演员信息失败 / Failed to extract actress info ({error_type})", marker="!")
        return None#, None

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
        
        # 与独立目录更新工具使用同一命名规则。
        folder_name = format_film_folder_name(film_number, producer, film_title)
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
    print_step(f"创建快捷方式 / Creating shortcut: {shortcut_path}")


def build_actress_shortcut_name(actress_id, first_film_id):
    """保持原项目的演员页快捷方式命名格式。"""
    return f"id_{actress_id} - latest_{first_film_id}"
    
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
            print_step(f"头像已下载 / Avatar downloaded: {avatar_path}")
        else:
            print_detail(f"下载头像失败，状态码 / Avatar download failed, status: {response.status_code}", marker="!")
    except Exception as e:
        error_type = type(e).__name__
        print_detail(f"下载头像时出错 / Failed to download avatar ({error_type})", marker="!")

def is_logged_in(driver):
    """根据任意站内页的 Inertia 数据判断持久浏览器 profile 登录态。"""
    props = get_inertia_props(parse_html(driver))
    return bool((props.get("auth") or {}).get("user"))


def wait_for_manual_login(browser):
    driver = browser.driver
    print_step(
        "当前持久浏览器 profile 未登录。请在已打开的浏览器中登录并完成站点确认，"
        "然后回到此窗口按 Enter 继续。"
    )
    try:
        input("登录/确认完成后按 Enter 继续...")
    except EOFError:
        print_detail("当前环境无法等待手动登录。", marker="!")
        return False
    try:
        WebDriverWait(driver, 120).until(is_logged_in)
        return True
    except Exception:
        return False


def prepare_authenticated_session(browser):
    """优先复用当前已登录站内页，必要时只访问一次首页。"""
    driver = browser.driver
    current_host = (urlparse(driver.current_url).hostname or "").casefold()
    expected_host = (urlparse(SITE_BASE_URL).hostname or "").casefold()
    if current_host == expected_host and is_logged_in(driver):
        print_step("已复用当前页面和持久浏览器 profile 中的登录状态。")
        return True

    print_step(f"打开新站准备页 / Opening site preparation page: {SITE_BASE_URL}")
    browser.navigate(SITE_BASE_URL)
    if is_logged_in(driver):
        print_step("已复用持久浏览器 profile 中的登录状态。")
        return True
    if wait_for_manual_login(browser):
        print_step("已确认登录，后续启动会尝试复用此浏览器 profile。")
        return True
    return False


# 在 extract_film_data 函数中收集影片数据
film_data_list = []
count_film = 0

def validate_film_count(extracted_count, expected_count):
    if expected_count is None:
        print_step("未获取网页显示总数，跳过严格数量校验 / Expected total not found, skipping strict count validation")
        return True

    print_step(
        f"数量校验 / Count validation: 提取数量={extracted_count}，"
        f"网页显示数量={expected_count}"
    )
    if extracted_count == expected_count:
        print_step("数量校验通过 / Count validation passed")
        return True

    print_step("数量校验失败 / Count validation failed")
    print_detail(f"差异 / Difference: {abs(extracted_count - expected_count)} 个影片")
    return False

def crawl_actress(browser, target_actress_id):
    global count_film, film_data_list

    driver = browser.driver

    film_data_list = []
    count_film = 0
    page = 1

    print_section(f"演员 {target_actress_id} / Actress {target_actress_id}")

    # 打开目标网页（第一页，同时用于提取演员信息）
    url = build_actress_page_url(target_actress_id)
    browser.navigate(url)
    if not wait_for_page_load(driver):
        print_step("目标页面未加载影片卡片，跳过当前演员。 / Target page did not load video cards. Skipping current actress.")
        return 1

    soup = parse_html(driver)
    if not soup:
        print_step("未能成功解析网页内容，跳过当前演员。 / Failed to parse page content. Skipping current actress.")
        return 1

    # 提取演员信息
    actress_name = extract_actress_info(soup)
    # actress_name, avatar_url = extract_actress_info(soup)
    if not actress_name:
        print_step("无法获取演员名称，跳过当前演员。 / Cannot get actress name. Skipping current actress.")
        return 1

    # 创建演员文件夹
    actress_folder = os.path.join(OUTPUT_DIR, safe_filename(actress_name))

    if os.path.exists(actress_folder):
        suffix = 1
        while os.path.exists(f"{actress_folder}_{suffix}"):
            suffix += 1
        actress_folder = f"{actress_folder}_{suffix}"
        print_step(f"演员文件夹已存在，改用 / Actress folder exists, using: {actress_folder}")

    # 提取影片数量，计算总页数
    film_count = extract_film_count(soup)
    if film_count is not None:
        num_films = int(film_count)
        total_pages = max(extract_total_pages(soup) or 1, max(1, (num_films + 29) // 30))
        print_step(f"总影片数 / Total films: {num_films}")
        print_step(f"总页数 / Total pages: {total_pages}")
    else:
        num_films = None
        total_pages = extract_total_pages(soup)
        if total_pages:
            print_step(f"无法获取影片数量，检测到总页数 / Cannot get film count, detected total pages: {total_pages}")
        else:
            print_step("无法获取影片数量，将逐页抓取直到空页 / Cannot get film count, will fetch until empty")

    print_section("提取影片数据 / Extracting video data")

    url_1 = build_actress_page_url(target_actress_id)

    # 逐页加载影片数据（直接读取 Inertia JSON，保留旧 DOM 解析作为回退）
    while True:
        if total_pages is not None and page > total_pages:
            break
        print_step(f"第 {page} 页 / Page {page}")
        if page == 1:
            # 第一页已加载，直接使用当前 soup
            page_soup = soup
        else:
            page_soup = fetch_actress_articles(browser, target_actress_id, page)
        if page_soup is None:
            break
        article_items = extract_article_items(page_soup)
        containers = page_soup.find_all("div", class_="2xl:w-1/6 xl:w-1/5 lg:w-1/4 md:w-1/2 w-full p-4")
        if article_items is not None and not article_items:
            print_detail(f"第 {page} 页无影片数据，停止翻页 / No film data on page {page}, stopping")
            break
        if article_items is None and not containers:
            print_detail(f"第 {page} 页无影片数据，停止翻页 / No film data on page {page}, stopping")
            break
        extract_film_data(page_soup)
        page += 1

    print_section("数量校验 / Count validation")
    extracted_count = len(film_data_list)
    print_step(f"共提取到 {extracted_count} 个影片数据 / Total videos extracted: {extracted_count}")
    if not validate_film_count(extracted_count, num_films):
        print_step("提取数量与网页显示总数不一致，停止创建文件夹并跳过当前演员。 / Count mismatch, skipping current actress before creating folders.")
        return 1

    print_section("创建文件夹 / Creating folders")

    os.makedirs(actress_folder)
    print_step(f"创建演员文件夹 / Creating actress folder: {actress_folder}")

    # 在提取完所有影片数据后创建文件夹
    create_film_folders(actress_folder, film_data_list)

    first_film_id = film_data_list[0]["film_number"] if film_data_list else "未知ID"

    print_section("创建快捷方式 / Creating shortcut")

    # 创建快捷方式
    shortcut_name = build_actress_shortcut_name(target_actress_id, first_film_id)
    create_shortcut(actress_folder, url_1, shortcut_name)

    # # 下载头像
    # download_avatar(actress_folder, avatar_url, avatar_name=f'id_{target_actress_id}'+'.png')

    print_section("完成 / Finished")
    if num_films is not None:
        print_step("所有操作完成，数量校验成功！ / All operations completed, count validation passed!")
    else:
        print_step("所有操作完成（未获取网页显示总数，未进行严格数量校验）。 / All operations completed without strict count validation.")
    return 0


def main():
    browser = None
    last_exit_code = 0

    try:
        print_section("浏览器 / Browser")
        browser = PersistentBrowser()

        print_section("登录状态 / Authentication")
        if not prepare_authenticated_session(browser):
            print_detail("未确认登录成功，程序已退出。", marker="!")
            return 1

        print_step("登录准备完成，可以开始输入任务。 / Authentication is ready; input is now available.")

        current_mode = None
        while True:
            target = choose_crawler_target(DEFAULT_ACTRESS_ID, current_mode)
            if target is None:
                print_step("已退出 / Exiting.")
                return last_exit_code
            current_mode = target.kind

            if target.kind == "fc2_number":
                target_actress_id = resolve_actress_id_from_fc2_number(browser, target.value)
                if target_actress_id is None:
                    last_exit_code = 1
                    print_section("继续 / Continue")
                    print_step("当前 FC2 番号未能定位唯一演员，可重新输入。")
                    continue
            else:
                target_actress_id = target.value

            last_exit_code = crawl_actress(browser, target_actress_id)
            print_section("继续 / Continue")
        print_step("当前任务处理结束，请在当前模式继续输入；b 返回模式菜单，q 退出。")
        print_step("Task finished. Enter another number in this mode; b returns to the mode menu, q exits.")
    finally:
        if browser:
            browser.close()
