#!/usr/bin/env python3
"""按 FC2 作品详情更新目录名称；只替换制作人及其后的文字。"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from fc2cmadb_crawler.config import (
    FOLDER_TRUNCATION_SUFFIX,
    MAX_FILM_FOLDER_NAME_LENGTH,
    SITE_BASE_URL,
)
from fc2cmadb_crawler.naming import safe_filename, truncate_folder_name

from .preview_colors import format_changed_pair, supports_color
from .undo_history import batch_folder_paths, mark_undone, pending_batches, read_batch, write_batch


FC2_MARKER = "fc2-ppv-"
NUMBER_PATTERN = re.compile(r"fc2-ppv-(\d+)")
REQUEST_TIMEOUT = 15
UNDO_TOOL_NAME = "fc2-folder-names"


class BackToMainMenu(Exception):
    """放弃本批次并回到操作菜单。"""


class QuitTool(Exception):
    """放弃本批次并退出工具。"""


@dataclass(frozen=True)
class FilmMetadata:
    number: str
    producer: str
    title: str
    writer_slug: str = ""


@dataclass(frozen=True)
class RenamePlan:
    source: Path
    target: Path
    number: str


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
    return Path(value).expanduser().resolve()


def is_reparse_directory(path: Path) -> bool:
    """不进入目录联接或符号链接，避免扫描到用户未指定的目录树。"""
    try:
        info = path.lstat()
    except OSError:
        return True
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


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
    """优先借助站点制作人名称或 slug 找边界；含糊时跳过。"""
    match = NUMBER_PATTERN.search(name)
    if match is None or match.group(1) != metadata.number:
        raise ValueError("详情页番号与目录番号不一致")
    after_number = name[match.end():]
    old_producer_area, separator, old_title = after_number.partition("-")
    if not separator or not old_title.strip():
        raise ValueError("原名称缺少可识别的制作人-标题结构")

    matches = []
    for hint in (metadata.producer, metadata.writer_slug):
        if hint:
            index = old_producer_area.casefold().rfind(hint.casefold())
            if index >= 0 and old_producer_area[index:].strip().casefold() == hint.casefold():
                matches.append(index)
    if matches:
        return name[:match.end() + max(matches)]

    before_producer = re.match(r"\S*\s+", after_number)
    if before_producer is None:
        raise ValueError("无法定位制作人前的空格分界")
    old_producer = old_producer_area[before_producer.end():].strip()
    if not old_producer:
        raise ValueError("原名称缺少制作人")
    if " " in old_producer and old_producer.casefold() not in parent_name.casefold():
        raise ValueError("制作人前可能还有附加文字，无法确定保留边界")
    return name[:match.end() + before_producer.end()]


def fetch_metadata(session: requests.Session, number: str) -> FilmMetadata:
    url = f"{SITE_BASE_URL}/articles/{number}"
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
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
    if page.get("component") == "Error" or props.get("status"):
        raise ValueError(f"站点返回错误状态：{props.get('status') or page.get('component')}")
    article = props.get("article")
    if not isinstance(article, dict) or str(article.get("video_id")) != number:
        raise ValueError("详情页番号与目录番号不一致")
    writer = article.get("writer")
    producer = writer.get("name") if isinstance(writer, dict) else None
    slug = writer.get("slug") if isinstance(writer, dict) else None
    title = article.get("title")
    if not isinstance(producer, str) or not producer.strip():
        raise ValueError("详情页缺少制作人")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("详情页缺少影片标题")
    return FilmMetadata(number, producer.strip(), title.strip(), str(slug or "").strip())


def build_target_name(source_name: str, metadata: FilmMetadata, parent_name: str = "") -> str:
    prefix = preserved_prefix(source_name, metadata, parent_name)
    producer = safe_filename(metadata.producer)
    title = safe_filename(metadata.title)
    if not producer or not title:
        raise ValueError("站点制作人或标题清理后为空")
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


def make_plan(root: Path, session: requests.Session) -> tuple[list[RenamePlan], list[str], int, int]:
    folders, scan_issues = find_folders(root)
    plans: list[RenamePlan] = []
    skipped: list[str] = list(scan_issues)
    metadata_cache: dict[str, FilmMetadata | Exception] = {}
    planned_targets: set[str] = set()
    issue_count = len(scan_issues)

    for source in folders:
        try:
            number = extract_number(source.name)
            if number not in metadata_cache:
                try:
                    metadata_cache[number] = fetch_metadata(session, number)
                except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                    metadata_cache[number] = exc
            metadata = metadata_cache[number]
            if isinstance(metadata, Exception):
                raise ValueError(f"获取 {number} 资料失败：{metadata}")
            target_name = build_target_name(source.name, metadata, source.parent.name)
            if target_name == source.name:
                skipped.append(f"已符合新名称: {source}")
                continue
            target = source.with_name(target_name)
            key = str(target).casefold()
            if target.exists() or key in planned_targets:
                raise ValueError(f"目标目录已存在或重复：{target}")
            planned_targets.add(key)
            plans.append(RenamePlan(source, target, number))
        except ValueError as exc:
            skipped.append(f"{source}: {exc}")
            issue_count += 1

    return plans, skipped, len(folders), issue_count


def print_preview(plans: list[RenamePlan], skipped: list[str], total: int) -> None:
    print(f"发现匹配目录: {total}；待重命名: {len(plans)}；跳过: {len(skipped)}")
    if plans:
        print("预览 / Preview（红色为旧差异，绿色为新差异）:")
        color = supports_color()
        for plan in sorted(plans, key=lambda item: str(item.source).casefold()):
            old, new = format_changed_pair(plan.source.name, plan.target.name, color=color)
            print(f"- [目录] {plan.source.parent}")
            print(f"  {old}")
            print(f"  -> {new}")
    for reason in skipped:
        print(f"[跳过] {reason}")


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


def run_root(root: Path, session: requests.Session, *, dry_run: bool = False) -> int:
    if not root.is_dir() or is_reparse_directory(root):
        print(f"不是可扫描的普通目录: {root}")
        return 1
    plans, skipped, total, issue_count = make_plan(root, session)
    print_preview(plans, skipped, total)
    if not plans or dry_run:
        return 1 if issue_count else 0

    while True:
        try:
            choice = input("1. 确认重命名（回车默认 1）；b 返回主菜单；q 退出: ").strip().lower() or "1"
        except EOFError:
            raise QuitTool from None
        if choice == "b":
            raise BackToMainMenu
        if choice == "q":
            raise QuitTool
        if choice == "1":
            renamed, failed = apply_plan(plans, root)
            print(f"重命名完成: {renamed}；失败或状态变化: {failed}")
            return 1 if failed or issue_count else 0
        print("请输入 1，或输入 b 返回、q 退出。")


def main(argv: list[str] | None = None) -> int:
    configure_console()
    parser = argparse.ArgumentParser(description="按 fc2cmadb.com 最新资料更新 FC2 作品目录名")
    parser.add_argument("root", nargs="?", help="递归扫描的根目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不重命名")
    parser.add_argument("--undo", action="store_true", help="列出最近处理的文件夹并选择一批撤销")
    args = parser.parse_args(argv)
    if args.undo:
        if args.root or args.dry_run:
            parser.error("--undo 不能与根目录或 --dry-run 同用")
        try:
            return undo_menu()
        except (BackToMainMenu, QuitTool):
            return 0

    with requests.Session() as session:
        if args.root:
            try:
                return run_root(resolve_path(args.root), session, dry_run=args.dry_run)
            except (BackToMainMenu, QuitTool):
                return 0

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
                run_root(resolve_path(raw_root), session, dry_run=args.dry_run)
            except BackToMainMenu:
                current_mode = None
                continue
            except QuitTool:
                return 0
            print("保持当前模式；输入下一个根目录，b 返回主菜单，q 退出。")


if __name__ == "__main__":
    raise SystemExit(main())
