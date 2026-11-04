"""以普通可见 Chrome 的持久会话执行所有 fc2cmadb 页面导航。"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.selenium_manager import SeleniumManager
from selenium.webdriver.support.ui import WebDriverWait

from .config import (
    CHROME_PROFILE_DIR,
    CHROME_STARTUP_WAIT_SECONDS,
    MANUAL_CHALLENGE_WAIT_SECONDS,
    MIN_NAVIGATION_INTERVAL_SECONDS,
    NAVIGATION_TIMEOUT_SECONDS,
    PAGE_WAIT_SECONDS,
)
from .site_state import is_counted_visit, record_site_visit


CHALLENGE_TITLES = ("just a moment", "请稍候", "attention required")
CHALLENGE_CONTENT_MARKERS = (
    "正在验证您是否是真人",
    "验证您不是自动程序",
    "performing security verification",
    "verify you are human",
)
DEBUG_PORT_FILE_NAME = "Fc2CmadbCrawlerDebugPort"
DRIVER_RESOLUTION_TIMEOUT_SECONDS = 30
WEBDRIVER_ATTACH_TIMEOUT_SECONDS = 30


def is_challenge_page(driver) -> bool:
    """检查标题与可见正文，不把普通页面的嵌入式 Turnstile 当成整页挑战。"""
    title = (driver.title or "").casefold()
    if any(marker in title for marker in CHALLENGE_TITLES):
        return True
    try:
        content = driver.execute_script(
            "return document.body ? document.body.innerText : '';"
        )
    except Exception:
        content = driver.page_source or ""
    visible_text = str(content or "").casefold()
    return any(marker.casefold() in visible_text for marker in CHALLENGE_CONTENT_MARKERS)


def find_chrome_executable() -> Path:
    """查找 Windows Chrome，不依赖 WebDriver 下载或创建浏览器。"""
    candidates: list[Path] = []
    discovered = shutil.which("chrome") or shutil.which("chrome.exe")
    if discovered:
        candidates.append(Path(discovered))
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("未找到 Chrome，请先安装 Google Chrome")


def reserve_debug_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def find_existing_debug_port(profile_dir: Path) -> int | None:
    """发现仍在运行的项目 Chrome，避免 CLI 重启后重新验证或登录。"""
    for port_file in (
        profile_dir / DEBUG_PORT_FILE_NAME,
        profile_dir / "DevToolsActivePort",
    ):
        try:
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1):
                return port
        except (OSError, URLError, ValueError, IndexError):
            continue
    return None


def wait_for_debugger(port: int, process: subprocess.Popen | None) -> None:
    endpoint = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + CHROME_STARTUP_WAIT_SECONDS
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError("Chrome 启动后立即退出；请先关闭本工具此前打开的 Chrome 窗口")
        try:
            with urlopen(endpoint, timeout=1):
                return
        except (OSError, URLError):
            time.sleep(0.1)
    raise RuntimeError("等待 Chrome 调试端口超时；请关闭占用该专用 Profile 的 Chrome 后重试")


def resolve_chromedriver(chrome: Path) -> Path:
    """限时查找或下载匹配的 ChromeDriver，避免附加阶段无限等待。"""
    command = [
        str(SeleniumManager._get_binary()),
        "--browser", "chrome",
        "--browser-path", str(chrome),
        "--timeout", "10",
        "--language-binding", "python",
        "--output", "json",
    ]
    kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=DRIVER_RESOLUTION_TIMEOUT_SECONDS,
            **kwargs,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("查找或下载 ChromeDriver 超过 30 秒；请检查网络后重试") from exc
    if completed.returncode:
        raise RuntimeError("无法取得匹配的 ChromeDriver；请检查网络及 Chrome 安装")
    try:
        driver = Path(json.loads(completed.stdout)["result"]["driver_path"])
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise RuntimeError("Selenium Manager 未返回有效的 ChromeDriver 路径") from exc
    if not driver.is_file():
        raise RuntimeError("Selenium Manager 返回的 ChromeDriver 文件不存在")
    return driver


class PersistentBrowser:
    """复用普通 Chrome；所有业务页面都通过 navigate 进入。"""

    def __init__(self, profile_dir: Path = CHROME_PROFILE_DIR):
        profile_dir = profile_dir.resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        port = find_existing_debug_port(profile_dir)
        self.chrome_process: subprocess.Popen | None = None
        if port is None:
            print("未发现可复用的项目 Chrome，正在启动浏览器...", flush=True)
            chrome = find_chrome_executable()
            port = reserve_debug_port()
            self.chrome_process = subprocess.Popen(
                [
                    str(chrome),
                    f"--remote-debugging-port={port}",
                    "--remote-debugging-address=127.0.0.1",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--start-maximized",
                    "about:blank",
                ]
            )
        else:
            print(f"正在复用项目 Chrome（调试端口 {port}）...", flush=True)
        print("正在等待 Chrome 调试端口...", flush=True)
        wait_for_debugger(port, self.chrome_process)
        if self.chrome_process is not None:
            (profile_dir / DEBUG_PORT_FILE_NAME).write_text(str(port), encoding="ascii")

        options = webdriver.ChromeOptions()
        options.debugger_address = f"127.0.0.1:{port}"
        options.page_load_strategy = "eager"
        try:
            print("Chrome 已就绪，正在查找 ChromeDriver...", flush=True)
            driver_path = resolve_chromedriver(find_chrome_executable())
            print("ChromeDriver 已就绪，正在附加 WebDriver...", flush=True)
            previous_socket_timeout = socket.getdefaulttimeout()
            try:
                # Selenium 4.36 在创建本地连接时读取默认 socket 超时。
                socket.setdefaulttimeout(WEBDRIVER_ATTACH_TIMEOUT_SECONDS)
                self.driver = webdriver.Chrome(options=options, service=Service(str(driver_path)))
            finally:
                socket.setdefaulttimeout(previous_socket_timeout)
            self.driver.set_page_load_timeout(NAVIGATION_TIMEOUT_SECONDS)
            self._last_navigation_at = 0.0
            self._last_timed_navigation_at = 0.0
            print("WebDriver 附加完成。", flush=True)
        except Exception:
            if self.chrome_process is not None:
                self.chrome_process.terminate()
            raise

    def _pace_navigation(self, min_interval_seconds: float = 0.0) -> None:
        now = time.monotonic()
        remaining = max(
            MIN_NAVIGATION_INTERVAL_SECONDS - (now - self._last_navigation_at)
            if self._last_navigation_at else 0.0,
            min_interval_seconds - (now - self._last_timed_navigation_at)
            if min_interval_seconds and self._last_timed_navigation_at else 0.0,
        )
        if remaining > 0:
            time.sleep(remaining)
        visited_at = time.monotonic()
        self._last_navigation_at = visited_at
        if min_interval_seconds:
            self._last_timed_navigation_at = visited_at

    def navigate(self, url: str, *, min_interval_seconds: float = 0.0) -> str:
        """导航、节流并处理挑战；人工完成后不刷新页面。"""
        previous_url = self.driver.current_url
        if previous_url != url:
            self._pace_navigation(min_interval_seconds)
            if is_counted_visit(url):
                record_site_visit(url)
            navigation = self.driver.execute_cdp_cmd("Page.navigate", {"url": url})
            if navigation.get("errorText"):
                raise RuntimeError(f"浏览器导航失败：{navigation['errorText']}")
        try:
            WebDriverWait(self.driver, PAGE_WAIT_SECONDS).until(
                lambda driver: (
                    (previous_url == url or driver.current_url != previous_url)
                    and driver.execute_script("return document.readyState")
                    in {"interactive", "complete"}
                )
            )
        except TimeoutException:
            self.driver.execute_cdp_cmd("Page.stopLoading", {})

        if is_challenge_page(self.driver):
            print("站点正在自动验证是否为真人，请稍候...")
            try:
                WebDriverWait(self.driver, PAGE_WAIT_SECONDS).until(
                    lambda driver: not is_challenge_page(driver)
                )
            except TimeoutException:
                try:
                    input("请在项目 Chrome 中完成验证；页面自动进入目标站点后按 Enter 继续...")
                except EOFError as exc:
                    raise RuntimeError("当前环境无法等待手动完成浏览器验证") from exc
                try:
                    WebDriverWait(self.driver, MANUAL_CHALLENGE_WAIT_SECONDS).until(
                        lambda driver: not is_challenge_page(driver)
                    )
                except TimeoutException as exc:
                    raise RuntimeError("浏览器仍停留在安全验证页；未进入目标站点") from exc
        return self.driver.page_source

    def close(self) -> None:
        """只断开 ChromeDriver，保留 Chrome 进程和登录状态。"""
        try:
            self.driver.service.stop()
        except Exception:
            pass

    def __enter__(self) -> "PersistentBrowser":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
