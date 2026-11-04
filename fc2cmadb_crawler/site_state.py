"""当前程序会话的站点访问提示，以及保存在 ~outputs 的販売者名称缓存。"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .config import PROJECT_ROOT


STATE_PATH = PROJECT_ROOT / "~outputs" / "fc2cmadb-site-state.sqlite3"
VISIT_NOTICE_THRESHOLD = 50
SELLER_CACHE_DAYS = 30


@dataclass
class VisitCounter:
    """每次程序启动时重新创建；提醒不阻止导航。"""

    count: int = 0

    def record(self, url: str) -> int | None:
        if not is_counted_visit(url):
            return None
        self.count += 1
        if self.count == VISIT_NOTICE_THRESHOLD:
            print(f"[提示] 本次会话影片详情与搜索访问已达 {VISIT_NOTICE_THRESHOLD} 次；程序继续运行。", flush=True)
        return self.count


_visit_counter = VisitCounter()


@dataclass(frozen=True)
class CachedSeller:
    current_name: str
    old_names: tuple[str, ...]
    slug: str


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.execute("PRAGMA busy_timeout=30000")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS seller_names ("
        "alias_key TEXT PRIMARY KEY, current_name TEXT NOT NULL, old_names_json TEXT NOT NULL, "
        "slug TEXT NOT NULL, fetched_at REAL NOT NULL)"
    )
    connection.commit()
    return connection


def is_counted_visit(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").casefold() != "fc2cmadb.com":
        return False
    return parsed.path == "/search" or parsed.path.startswith("/articles/")


def record_site_visit(url: str) -> int | None:
    """统计当前程序进程的实际导航；达到阈值只提示。"""
    return _visit_counter.record(url)


def load_cached_seller(
    name: str, *, path: Path = STATE_PATH, now: float | None = None
) -> CachedSeller | None:
    key = name.strip().casefold()
    if not key or not path.is_file():
        return None
    with closing(_connect(path)) as connection, connection:
        row = connection.execute(
            "SELECT current_name, old_names_json, slug, fetched_at FROM seller_names WHERE alias_key=?",
            (key,),
        ).fetchone()
    if row is None or (now if now is not None else time.time()) - row[3] >= SELLER_CACHE_DAYS * 86400:
        return None
    old_names = json.loads(row[1])
    if not isinstance(old_names, list) or not all(isinstance(value, str) for value in old_names):
        return None
    return CachedSeller(row[0], tuple(old_names), row[2])


def save_cached_seller(
    seller: CachedSeller, *, path: Path = STATE_PATH, now: float | None = None
) -> None:
    """同一次验证得到的当前名与旧名共用取得时间。"""
    fetched_at = now if now is not None else time.time()
    names = {name.strip().casefold() for name in (seller.current_name, *seller.old_names) if name.strip()}
    if not names:
        return
    with closing(_connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany(
            "INSERT INTO seller_names(alias_key, current_name, old_names_json, slug, fetched_at) "
            "VALUES(?, ?, ?, ?, ?) ON CONFLICT(alias_key) DO UPDATE SET "
            "current_name=excluded.current_name, old_names_json=excluded.old_names_json, "
            "slug=excluded.slug, fetched_at=excluded.fetched_at",
            [
                (name, seller.current_name, json.dumps(seller.old_names, ensure_ascii=False), seller.slug, fetched_at)
                for name in names
            ],
        )
