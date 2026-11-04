#!/usr/bin/env python3
"""按販売者名称更新 FC2 目录；只替换制作人及其后的文字。"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import stat
import sys
from collections import Counter
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException

from fc2cmadb_crawler.browser import PersistentBrowser
from fc2cmadb_crawler.crawler import prepare_authenticated_session
from fc2cmadb_crawler.config import (
    FOLDER_TRUNCATION_SUFFIX,
    MAX_FILM_FOLDER_NAME_LENGTH,
    SITE_BASE_URL,
)
from fc2cmadb_crawler.naming import safe_filename, truncate_folder_name
from fc2cmadb_crawler.site_state import (
    CachedSeller,
    load_cached_seller,
    save_cached_seller,
)

from .._shared.preview_colors import format_changed_pair, supports_color
from .._shared.undo_history import batch_folder_paths, mark_undone, pending_batches, read_batch, write_batch


FC2_MARKER = "fc2-ppv-"
NUMBER_PATTERN = re.compile(r"fc2-ppv-(\d+)")
UNDO_TOOL_NAME = "fc2-folder-names"
MIN_METADATA_INTERVAL_SECONDS = 12
MAX_METADATA_INTERVAL_SECONDS = 32


class BackToMainMenu(Exception):
    """放弃本批次并回到操作菜单。"""


class QuitTool(Exception):
    """放弃本批次并退出工具。"""


class SiteRateLimited(RuntimeError):
    """首次 429 即停止本批后续获取。"""


class ScanInterrupted(RuntimeError):
    """扫描中断时携带已经安全准备好的部分改名计划。"""

    def __init__(
        self, reason: str, plans: list[RenamePlan], skipped: list[str], total: int, issue_count: int
    ) -> None:
        super().__init__(reason)
        self.plans = plans
        self.skipped = skipped
        self.total = total
        self.issue_count = issue_count


@dataclass(frozen=True)
class FilmMetadata:
    number: str
    producer: str
    title: str
    writer_slug: str = ""
    old_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProducerLookup:
    """一批目录中同一原制作人字段共享的边界和最新名称。"""
    prefix_offset: int
    old_producer: str
    new_producer: str


@dataclass(frozen=True)
class RenamePlan:
    source: Path
    target: Path
    number: str
    reasons: frozenset[str]
    producer_change: tuple[str, str] | None


@dataclass
class MetadataPacing:
    """在同一次浏览器会话内保留页间节奏，跨根目录继续生效。"""
    interval_seconds: int = MIN_METADATA_INTERVAL_SECONDS


def configure_console() -> None:
    if os.name == "nt" and sys.stdout.isatty():
        import ctypes

        kernel32 = ctypes.windll.kernel32
        old_output = kernel32.GetConsoleOutputCP()
        old_input = kernel32.GetConsoleCP()
        if kernel32.SetConsoleOutputCP(65001) and kernel32.SetConsoleCP(65001):
            atexit.register(kernel32.SetConsoleOutputCP, old_output)
            atexit.register(kernel32.SetConsoleCP, old_input)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")


def resolve_path(raw_path: str) -> Path:
    value = raw_path.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    path = Path(value).expanduser()
    try:
        return path.resolve()
    except OSError:
        if '"' not in value:
            raise
        # Windows 不允许目录名包含英文双引号；保留原输入供错误提示匹配真实目录。
        return path.absolute()


def is_reparse_directory(path: Path) -> bool:
    """不进入目录联接或符号链接，避免扫描到用户未指定的目录树。"""
    try:
        info = path.lstat()
    except OSError:
        return True
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def suggest_quoted_directory(path: Path) -> Path | None:
    """英文引号不能用于 Windows 目录名；只提示唯一的弯引号同名目录。"""
    if '"' not in path.name or not path.parent.is_dir():
        return None
    wanted = path.name
    try:
        matches = [
            child for child in path.parent.iterdir()
            if child.is_dir()
            and not is_reparse_directory(child)
            and child.name.replace("“", '"').replace("”", '"') == wanted
        ]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None


def report_unscannable_root(path: Path) -> None:
    print(f"不是可扫描的普通目录: {path}")
    suggestion = suggest_quoted_directory(path)
    if suggestion is not None:
        print(f"目录名中的英文双引号可能写错；实际目录是: {suggestion}")


def find_folders(root: Path) -> tuple[list[Path], list[str]]:
    candidates: list[Path] = []
    scan_issues: list[str] = []

    def on_error(error: OSError) -> None:
        scan_issues.append(f"扫描失败: {error}")

    for current, dirnames, _files in os.walk(root, topdown=True, followlinks=False, onerror=on_error):
        current_path = Path(current)
        safe_names = []
        for name in dirnames:
            child = current_path / name
            if is_reparse_directory(child):
                scan_issues.append(f"跳过不可扫描目录或链接: {child}")
            else:
                safe_names.append(name)
        dirnames[:] = safe_names
        if FC2_MARKER in current_path.name:
            candidates.append(current_path)
    return sorted(candidates, key=lambda path: (-len(path.parts), str(path).casefold())), scan_issues


def extract_number(name: str) -> str:
    if name.count(FC2_MARKER) != 1:
        raise ValueError("名称中缺少唯一的 fc2-ppv- 标记")
    match = NUMBER_PATTERN.search(name)
    if match is None:
        raise ValueError("fc2-ppv- 后缺少纯数字番号")
    return match.group(1)


def preserved_prefix(name: str, metadata: FilmMetadata, parent_name: str) -> str:
    """用販売者当前名称及旧名精确定位原制作人，优先匹配完整旧名。"""
    match = NUMBER_PATTERN.search(name)
    if match is None or match.group(1) != metadata.number:
        raise ValueError("详情页番号与目录番号不一致")
    after_number = name[match.end():]
    old_producer_area, separator, old_title = after_number.partition("-")
    if not separator or not old_title.strip():
        raise ValueError("原名称缺少可识别的制作人-标题结构")

    matches = []
    for hint in (metadata.producer, *metadata.old_names, metadata.writer_slug):
        if hint:
            index = old_producer_area.casefold().rfind(hint.casefold())
            if index >= 0 and old_producer_area[index:].strip().casefold() == hint.casefold():
                matches.append(index)
    if matches:
        return name[:match.end() + min(matches)]
    raise ValueError("原制作人不在販売者当前名称或旧名中，无法确定保留边界")


def writer_search_keyword(producer_area: str) -> str:
    """移除番号后的第一段附注，得到用于販売者搜索的现有名称。"""
    match = re.match(r"[_=]\S*\s+", producer_area)
    query = producer_area[match.end():].strip() if match else producer_area.strip()
    if not query:
        raise ValueError("原名称缺少可搜索的制作人")
    return query


def writer_search_url(producer_area: str) -> str:
    return f"{SITE_BASE_URL}/search?{urlencode({'keyword': writer_search_keyword(producer_area), 'stype': 'writer'})}"


def writer_names(writer: dict) -> tuple[str, ...]:
    aliases = (
        item["old_name"].strip()
        for item in (writer.get("writer_old_names") or [])
        if isinstance(item, dict) and isinstance(item.get("old_name"), str) and item["old_name"].strip()
    )
    name = writer.get("name")
    return (name.strip(), *aliases) if isinstance(name, str) and name.strip() else tuple(aliases)


def unique_writer_result(page: dict, props: dict, query: str) -> dict:
    """详情页或完整搜索列表中只选一个与查询词精确相等的販売者。"""
    if page.get("component") == "Writers/Show" and isinstance(props.get("writer"), dict):
        writer = props["writer"]
        if any(name.casefold() == query.casefold() for name in writer_names(writer)):
            return writer
        raise ValueError("販売者详情页名称与查询词不一致")
    results = props.get("writers")
    if page.get("component") != "Search/Writer" or not isinstance(results, dict):
        raise ValueError("搜索未返回唯一的販売者详情页")
    candidates = results.get("data")
    if not isinstance(candidates, list) or results.get("total") != len(candidates):
        raise ValueError("販売者搜索结果未完整列出，无法确认唯一匹配")
    matches = [
        item for item in candidates
        if isinstance(item, dict) and any(name.casefold() == query.casefold() for name in writer_names(item))
    ]
    if len(matches) != 1:
        raise ValueError("販売者搜索未找到唯一的精确名称匹配")
    return matches[0]


def fetch_metadata(
    browser: PersistentBrowser, number: str, producer_area: str, *, interval_seconds: int = 0
) -> FilmMetadata:
    """按现有販売者名称搜索；只接受唯一的販売者详情页。"""
    url = writer_search_url(producer_area)
    soup = BeautifulSoup(browser.navigate(url, min_interval_seconds=interval_seconds), "html.parser")
    script = soup.select_one('script[data-page="app"]')
    if script is None:
        raise ValueError("详情页缺少作品数据；可能需要登录或完成站点验证")
    payload = script.string or script.get_text()
    if not payload or not payload.strip():
        raise ValueError("详情页作品数据为空")
    page = json.loads(payload)
    if not isinstance(page, dict):
        raise ValueError("详情页作品数据格式无效")
    props = page.get("props") or {}
    if not isinstance(props, dict):
        raise ValueError("详情页作品数据格式无效")
    if str(props.get("status")) == "429":
        raise SiteRateLimited("站点返回 429（请求过于频繁）")
    if page.get("component") == "Error" or props.get("status"):
        raise ValueError(f"站点返回错误状态：{props.get('status') or page.get('component')}")
    writer = unique_writer_result(page, props, writer_search_keyword(producer_area))
    producer = writer.get("name")
    slug = writer.get("slug")
    if not isinstance(producer, str) or not producer.strip():
        raise ValueError("販売者详情页缺少名称")
    old_names = writer_names(writer)[1:]
    return FilmMetadata(number, producer.strip(), "", str(slug or "").strip(), old_names)


def source_parts(name: str) -> tuple[re.Match[str], str, str]:
    match = NUMBER_PATTERN.search(name)
    if match is None:
        raise ValueError("fc2-ppv- 后缺少纯数字番号")
    producer_area, separator, title = name[match.end():].partition("-")
    if not separator or not title.strip():
        raise ValueError("原名称缺少可识别的制作人-标题结构")
    return match, producer_area, title


def format_target_name(prefix: str, producer_name: str, original_title: str) -> str:
    producer = safe_filename(producer_name)
    title = safe_filename(original_title)
    if not producer or not title:
        raise ValueError("制作人或原目录标题清理后为空")
    new_producer_prefix = f"{prefix}{producer}-"
    full_name = new_producer_prefix + title
    if (
        len(full_name) >= MAX_FILM_FOLDER_NAME_LENGTH
        and len(new_producer_prefix)
        >= MAX_FILM_FOLDER_NAME_LENGTH - len(FOLDER_TRUNCATION_SUFFIX)
    ):
        raise ValueError("保留的前置文字与制作人过长，标题无法放入主程序长度限制")
    target_name = truncate_folder_name(full_name)
    if not target_name.startswith(new_producer_prefix):
        raise ValueError("保留的前置文字与制作人过长，无法在主程序长度限制内命名")
    if len(target_name.encode("utf-16-le")) // 2 > 255:
        raise ValueError("目标目录名称超过 Windows 单段路径限制")
    return target_name


def rename_reasons(prefix: str, old_producer: str, new_producer: str, original_title: str) -> frozenset[str]:
    producer = safe_filename(new_producer)
    full_name = f"{prefix}{producer}-{safe_filename(original_title)}"
    reasons = set()
    if old_producer != producer:
        reasons.add("producer")
    if len(full_name) >= MAX_FILM_FOLDER_NAME_LENGTH:
        reasons.add("truncation")
    return frozenset(reasons or {"other"})


def build_target_name(source_name: str, metadata: FilmMetadata, parent_name: str = "") -> str:
    prefix = preserved_prefix(source_name, metadata, parent_name)
    _, _, title = source_parts(source_name)
    return format_target_name(prefix, metadata.producer, title)


def classify_rename_reasons(source_name: str, metadata: FilmMetadata, parent_name: str) -> frozenset[str]:
    """根据同一命名边界判定原因；制作人更新和长度截断可以并存。"""
    prefix = preserved_prefix(source_name, metadata, parent_name)
    old_producer = source_name[len(prefix):].partition("-")[0].strip()
    _, _, title = source_parts(source_name)
    return rename_reasons(prefix, old_producer, metadata.producer, title)


def fetch_metadata_with_pacing(
    browser: PersistentBrowser, number: str, producer_area: str, pacing: MetadataPacing
) -> FilmMetadata:
    """按配置间隔搜索一次；429 由扫描器立即停止后续获取。"""
    return fetch_metadata(browser, number, producer_area, interval_seconds=pacing.interval_seconds)


def cached_metadata(number: str, producer_area: str) -> FilmMetadata | None:
    seller = load_cached_seller(writer_search_keyword(producer_area))
    if seller is None:
        return None
    return FilmMetadata(number, seller.current_name, "", seller.slug, seller.old_names)


def producer_frequency_order(folders: list[Path]) -> list[Path]:
    """先处理有效缓存，再按当前販売者名称出现次数降序搜索。"""
    keywords: dict[Path, str] = {}
    counts: Counter[str] = Counter()
    for source in folders:
        try:
            _, area, _ = source_parts(source.name)
            keyword = writer_search_keyword(area).casefold()
        except ValueError:
            keyword = ""
        keywords[source] = keyword
        if keyword:
            counts[keyword] += 1
    cached = {keyword for keyword in counts if load_cached_seller(keyword) is not None}
    return sorted(
        folders,
        key=lambda source: (
            0 if keywords[source] in cached else 1,
            -counts[keywords[source]],
            -len(source.parts),
            str(source).casefold(),
        ),
    )


def rename_order(plans: list[RenamePlan]) -> list[RenamePlan]:
    return sorted(plans, key=lambda plan: (-len(plan.source.parts), str(plan.source).casefold()))


def reuse_producer_lookup(producer_area: str, cache: dict[str, ProducerLookup | Exception]) -> ProducerLookup | None:
    """已识别的制作人后缀可跨不同的番号附注复用；多种匹配时交给首次查询判定。"""
    matches = []
    for value in cache.values():
        if not isinstance(value, ProducerLookup):
            continue
        old_name = value.old_producer
        candidate = producer_area[-len(old_name):]
        prefix = producer_area[:-len(old_name)]
        if candidate.casefold() == old_name.casefold() and (not prefix or prefix[-1].isspace()):
            matches.append(ProducerLookup(len(prefix), candidate, value.new_producer))
    groups = {(item.old_producer.casefold(), item.new_producer.casefold()) for item in matches}
    return matches[0] if len(groups) == 1 else None


def make_plan(root: Path, browser: PersistentBrowser) -> tuple[list[RenamePlan], list[str], int, int]:
    folders, scan_issues = find_folders(root)
    folders = producer_frequency_order(folders)
    plans: list[RenamePlan] = []
    skipped: list[str] = list(scan_issues)
    producer_cache: dict[str, ProducerLookup | Exception] = {}
    lookup_count = 0
    planned_targets: set[str] = set()
    issue_count = len(scan_issues)
    pacing = getattr(browser, "_fc2_metadata_pacing", None)
    if not isinstance(pacing, MetadataPacing):
        pacing = MetadataPacing()
        browser._fc2_metadata_pacing = pacing

    for index, source in enumerate(folders, 1):
        if index == 1 or index % 10 == 0:
            print(f"正在检查目录: {index}/{len(folders)}；制作人查询: {lookup_count} 次", flush=True)
        try:
            number = extract_number(source.name)
            match, producer_area, original_title = source_parts(source.name)
            cache_key = producer_area.casefold()
            if cache_key not in producer_cache:
                reused = reuse_producer_lookup(producer_area, producer_cache)
                if reused is not None:
                    producer_cache[cache_key] = reused
                else:
                    try:
                        metadata = cached_metadata(number, producer_area)
                        if metadata is None:
                            lookup_count += 1
                            metadata = fetch_metadata_with_pacing(browser, number, producer_area, pacing)
                            save_cached_seller(CachedSeller(metadata.producer, metadata.old_names, metadata.writer_slug))
                        prefix = preserved_prefix(source.name, metadata, source.parent.name)
                        prefix_offset = len(prefix) - match.end()
                        old_producer = producer_area[prefix_offset:].strip()
                        producer_cache[cache_key] = ProducerLookup(
                            prefix_offset, old_producer, metadata.producer
                        )
                    except SiteRateLimited as exc:
                        remaining = folders[index - 1:]
                        skipped.extend(f"未处理（停止访问）: {path}" for path in remaining)
                        issue_count += len(remaining)
                        print(f"本批制作人查询: {lookup_count} 次", flush=True)
                        raise ScanInterrupted(
                            str(exc), rename_order(plans), skipped, len(folders), issue_count
                        ) from exc
                    except (WebDriverException, RuntimeError, OSError, ValueError) as exc:
                        producer_cache[cache_key] = exc
            lookup = producer_cache[cache_key]
            if isinstance(lookup, Exception):
                raise ValueError(f"获取制作人资料失败：{lookup}")
            old_producer = producer_area[lookup.prefix_offset:].strip()
            if old_producer.casefold() != lookup.old_producer.casefold():
                raise ValueError("同组制作人边界不一致")
            prefix = source.name[:match.end() + lookup.prefix_offset]
            target_name = format_target_name(prefix, lookup.new_producer, original_title)
            if target_name == source.name:
                skipped.append(f"已符合新名称: {source}")
                continue
            target = source.with_name(target_name)
            key = str(target).casefold()
            if target.exists() or key in planned_targets:
                raise ValueError(f"目标目录已存在或重复：{target}")
            planned_targets.add(key)
            reasons = rename_reasons(prefix, old_producer, lookup.new_producer, original_title)
            producer_change = None
            if "producer" in reasons:
                producer_change = (old_producer, safe_filename(lookup.new_producer))
            plans.append(RenamePlan(source, target, number, reasons, producer_change))
        except ValueError as exc:
            skipped.append(f"{source}: {exc}")
            issue_count += 1

    print(f"本批制作人查询: {lookup_count} 次", flush=True)
    return rename_order(plans), skipped, len(folders), issue_count


def print_preview(plans: list[RenamePlan], skipped: list[str], total: int) -> None:
    print("待重命名预览:")
    print(f"匹配目录: {total}；待重命名: {len(plans)}；跳过: {len(skipped)}")
    print("改名原因统计（待重命名目录；前两项可重叠）:")
    print(f"- 长度截断: {sum('truncation' in plan.reasons for plan in plans)}")
    print(f"- 制作人名称更新: {sum('producer' in plan.reasons for plan in plans)}")

    color = supports_color()
    producer_changes = Counter(plan.producer_change for plan in plans if plan.producer_change)
    print(f"制作人名称变动: {len(producer_changes)} 组")
    for (old_name, new_name), count in sorted(
        producer_changes.items(), key=lambda item: (item[0][0].casefold(), item[0][1].casefold())
    ):
        old, new = format_changed_pair(old_name, new_name, color=color)
        print(f"- {old} -> {new}: {count} 个目录")

    other_plans = [plan for plan in plans if "other" in plan.reasons]
    print(f"其他原因预览: {len(other_plans)} 个目录")
    if other_plans:
        for plan in sorted(other_plans, key=lambda item: str(item.source).casefold()):
            old, new = format_changed_pair(plan.source.name, plan.target.name, color=color)
            print(f"- [目录] {plan.source.parent}")
            print(f"  {old}")
            print(f"  -> {new}")


def print_all_rename_preview(plans: list[RenamePlan]) -> None:
    """按目录列出本批全部待改名称，供确认前按需展开。"""
    print(f"全部待重命名目录预览: {len(plans)} 个目录")
    color = supports_color()
    for plan in sorted(plans, key=lambda item: str(item.source).casefold()):
        old, new = format_changed_pair(plan.source.name, plan.target.name, color=color)
        print(f"- [目录] {plan.source.parent}")
        print(f"  {old}")
        print(f"  -> {new}")


def apply_plan(plans: list[RenamePlan], root: Path) -> tuple[int, int]:
    history_path = write_batch(
        UNDO_TOOL_NAME,
        [{"source": str(plan.source), "target": str(plan.target)} for plan in plans],
        root,
    )
    print(f"撤销记录: {history_path}")
    renamed = 0
    failed = 0
    for plan in plans:
        if not plan.source.is_dir() or plan.target.exists():
            print(f"[跳过] 源目录已变化或目标目录已存在: {plan.source}")
            failed += 1
            continue
        try:
            plan.source.rename(plan.target)
            print(f"[完成] {plan.source} -> {plan.target}")
            renamed += 1
        except OSError as exc:
            print(f"[失败] {plan.source}: {exc}")
            failed += 1
    return renamed, failed


def undo_batch(history_path: Path) -> bool:
    try:
        entries = list(reversed(read_batch(history_path)["entries"]))
    except (OSError, ValueError) as exc:
        print(f"[停止] 撤销记录无法读取: {exc}")
        return False
    print(f"所选批次撤销预览: {history_path.name}")
    color = supports_color()
    for entry in sorted(entries, key=lambda item: item["source"].casefold()):
        old, new = format_changed_pair(entry["target"], entry["source"], color=color)
        print(f"- [目录] {old}\n  -> {new}")

    while True:
        try:
            choice = input("1. 撤销此批（回车默认 1）；b 返回主菜单；q 退出: ").strip().lower() or "1"
        except EOFError:
            raise QuitTool from None
        if choice == "b":
            raise BackToMainMenu
        if choice == "q":
            raise QuitTool
        if choice == "1":
            break
        print("请输入 1，或输入 b 返回、q 退出。")

    restored = 0
    for entry in entries:
        source = Path(entry["source"])
        target = Path(entry["target"])
        if target.is_dir() and not source.exists() and not is_reparse_directory(target):
            try:
                target.rename(source)
                restored += 1
                print(f"[撤销] {target} -> {source}")
            except OSError as exc:
                print(f"[停止] 无法恢复 {target}: {exc}")
                return False
        elif source.is_dir() and not target.exists():
            print(f"[已恢复] {source}")
        else:
            print(f"[停止] 路径已变化或发生冲突: {target}")
            return False
    mark_undone(history_path)
    print(f"本批撤销完成：恢复 {restored} 个目录。")
    return True


def undo_menu() -> int:
    """列出未撤销批次的处理目录，选择一批预览并恢复。"""
    while True:
        choices = []
        for history_path in pending_batches(UNDO_TOOL_NAME):
            try:
                record = read_batch(history_path)
                folders = batch_folder_paths(record, "source")
            except (OSError, ValueError, KeyError) as exc:
                print(f"[跳过无效记录] {history_path.name}: {exc}")
                continue
            choices.append((history_path, folders, record))
        if not choices:
            print("没有可撤销的目录更新批次。")
            return 0
        print("最近处理的文件夹（选择要撤销的一批）:")
        for number, (_history_path, folders, record) in enumerate(choices, 1):
            when = str(record.get("created_at", "")).replace("T", " ")[:19]
            print(f"{number}. {', '.join(folders) or '[路径未知]'}{f' ({when})' if when else ''}")
        try:
            choice = input("选择编号（回车默认 1；b 返回，q 退出）: ").strip().lower() or "1"
        except EOFError:
            raise QuitTool from None
        if choice == "b":
            raise BackToMainMenu
        if choice == "q":
            raise QuitTool
        if choice.isdigit() and 1 <= int(choice) <= len(choices):
            undo_batch(choices[int(choice) - 1][0])
            continue
        print(f"请输入 1 到 {len(choices)} 的编号。")


def run_root(root: Path, browser: PersistentBrowser, *, dry_run: bool = False) -> int:
    if not root.is_dir() or is_reparse_directory(root):
        report_unscannable_root(root)
        return 1
    stop_reason = None
    try:
        plans, skipped, total, issue_count = make_plan(root, browser)
    except ScanInterrupted as exc:
        plans, skipped, total, issue_count = exc.plans, exc.skipped, exc.total, exc.issue_count
        stop_reason = str(exc)
        print(f"[停止获取] {stop_reason}；未处理: {sum(item.startswith('未处理（停止访问）:') for item in skipped)} 个目录。")
    print_preview(plans, skipped, total)
    if not plans or dry_run:
        return 1 if issue_count or stop_reason else 0

    while True:
        print(f"1. 确认重命名{'已准备的 ' + str(len(plans)) + ' 个目录' if stop_reason else ''}")
        print("2. 预览所有将重命名")
        try:
            choice = input("请输入数字（回车默认 1；b 返回主菜单；q 退出）: ").strip().lower() or "1"
        except EOFError:
            raise QuitTool from None
        if choice == "b":
            raise BackToMainMenu
        if choice == "q":
            raise QuitTool
        if choice == "2":
            print_all_rename_preview(plans)
            continue
        if choice == "1":
            renamed, failed = apply_plan(plans, root)
            print(f"重命名完成: {renamed}；失败或状态变化: {failed}")
            return 1 if failed or issue_count or stop_reason else 0
        print("请输入 1、2，或输入 b 返回、q 退出。")


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="按 fc2cmadb.com 最新资料更新 FC2 作品目录名")
    parser.add_argument("root", nargs="?", help="递归扫描的根目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不重命名")
    parser.add_argument("--undo", action="store_true", help="列出最近处理的文件夹并选择一批撤销")
    parser.add_argument("--interval", type=int, default=MIN_METADATA_INTERVAL_SECONDS, metavar="秒", help="販売者搜索最短访问间隔")
    args = parser.parse_args(argv)
    if not 2 <= args.interval <= MAX_METADATA_INTERVAL_SECONDS:
        parser.error(f"--interval 必须在 2 到 {MAX_METADATA_INTERVAL_SECONDS} 秒之间")
    if args.undo:
        if args.root or args.dry_run:
            parser.error("--undo 不能与根目录或 --dry-run 同用")
        try:
            return undo_menu()
        except (BackToMainMenu, QuitTool):
            return 0

    # 交互菜单出现前附加浏览器；模式内连续处理共用同一会话。
    with ExitStack() as stack:
        if args.root:
            try:
                root = resolve_path(args.root)
                if not root.is_dir() or is_reparse_directory(root):
                    report_unscannable_root(root)
                    return 1
                browser = stack.enter_context(PersistentBrowser())
                if not prepare_authenticated_session(browser):
                    print("[停止] 未确认站点登录状态，本批未扫描。")
                    return 1
                browser._fc2_metadata_pacing = MetadataPacing(interval_seconds=args.interval)
                return run_root(root, browser, dry_run=args.dry_run)
            except (BackToMainMenu, QuitTool):
                return 0

        try:
            browser = stack.enter_context(PersistentBrowser())
        except (OSError, RuntimeError) as exc:
            print(f"[停止] 浏览器准备失败：{exc}")
            return 1
        if not prepare_authenticated_session(browser):
            print("[停止] 未确认站点登录状态，未进入操作菜单。")
            return 1
        browser._fc2_metadata_pacing = MetadataPacing(interval_seconds=args.interval)
        current_mode = None
        while True:
            if current_mode is None:
                print("1. 更新 FC2 作品文件夹名称")
                print("2. 按文件夹选择并撤销目录更新")
                print("q. 退出")
                try:
                    choice = input("请输入数字（回车默认 1）: ").strip().lower() or "1"
                except EOFError:
                    return 0
                if choice == "q":
                    return 0
                if choice == "2":
                    try:
                        undo_menu()
                    except BackToMainMenu:
                        continue
                    except QuitTool:
                        return 0
                    continue
                if choice != "1":
                    print("请输入 1、2，或输入 q 退出。")
                    continue
                current_mode = "update"

            try:
                raw_root = input("请输入根目录（b 返回主菜单，q 退出）: ").strip()
            except EOFError:
                return 0
            if raw_root.lower() == "q":
                return 0
            if raw_root.lower() == "b":
                current_mode = None
                continue
            if not raw_root:
                print("根目录不能为空。")
                continue
            try:
                root = resolve_path(raw_root)
                if not root.is_dir() or is_reparse_directory(root):
                    report_unscannable_root(root)
                    continue
                run_root(root, browser, dry_run=args.dry_run)
            except BackToMainMenu:
                current_mode = None
                continue
            except QuitTool:
                return 0
            print("保持当前模式；输入下一个根目录，b 返回主菜单，q 退出。")


if __name__ == "__main__":
    raise SystemExit(main())
