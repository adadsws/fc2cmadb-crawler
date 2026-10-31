#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import base64
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .config import (
    DEFAULT_SHORTCUT_DOMAIN,
    DOMAIN_COUNT_LIMIT,
    SHORTCUT_PREVIEW_LIMIT,
)
from .preview_colors import format_changed_pair, supports_color
from .undo_history import batch_folder_paths, mark_undone, pending_batches, read_batch, write_batch


UNDO_TOOL_NAME = "shortcut-domains"
UNDO_MENU_CHOICE = "__undo__"


class BackToMainMenu(Exception):
    """退出当前确认，返回域名选择。"""


class QuitTool(Exception):
    """从任意输入层级退出。"""


@dataclass
class ShortcutChange:
    path: Path
    encoding: str
    original_url: str
    new_url: str
    original_text: str
    new_text: str
    original_bytes: bytes


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")


def strip_outer_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def resolve_path(raw_path: str) -> Path:
    return Path(strip_outer_quotes(raw_path)).expanduser().resolve()


def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if not domain:
        raise ValueError("目标域名不能为空")
    parsed = urlsplit(domain if "://" in domain else f"https://{domain}")
    if not parsed.hostname:
        raise ValueError(f"目标域名无效: {domain}")
    return parsed.hostname


def host_contains_fc2(hostname: str | None) -> bool:
    return bool(hostname and "fc2" in hostname.lower())


def extract_url_hostname(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None

    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return parsed.hostname.lower() if parsed.hostname else None

    if not parsed.scheme and not parsed.netloc:
        schemeless = urlsplit(f"//{url}")
        if schemeless.netloc and "." in schemeless.netloc and schemeless.hostname:
            return schemeless.hostname.lower()

    return None


def decode_shortcut(raw_bytes: bytes) -> tuple[str, str]:
    if raw_bytes.startswith(b"\xff\xfe") or raw_bytes.startswith(b"\xfe\xff"):
        return raw_bytes.decode("utf-16"), "utf-16"
    if raw_bytes.startswith(b"\xef\xbb\xbf"):
        return raw_bytes.decode("utf-8-sig"), "utf-8-sig"

    encodings = ["utf-8", "mbcs", "cp932", "gbk"]
    for encoding in encodings:
        try:
            return raw_bytes.decode(encoding), encoding
        except (LookupError, UnicodeDecodeError):
            continue

    return raw_bytes.decode("latin-1"), "latin-1"


def rewrite_url_domain(url: str, target_domain: str) -> str | None:
    url = url.strip()
    if not url:
        return None

    parsed = urlsplit(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        if not host_contains_fc2(parsed.hostname):
            return None
        return urlunsplit((parsed.scheme, target_domain, parsed.path, parsed.query, parsed.fragment))

    if not parsed.scheme and not parsed.netloc:
        schemeless = urlsplit(f"//{url}")
        if schemeless.netloc and "." in schemeless.netloc:
            if not host_contains_fc2(schemeless.hostname):
                return None
            return urlunsplit(("https", target_domain, schemeless.path, schemeless.query, schemeless.fragment))

    return None


def collect_domain_counts(text: str) -> Counter[str]:
    domain_counts: Counter[str] = Counter()

    for line in text.splitlines():
        match = re.match(r"^\s*URL\s*=\s*(.*)$", line, re.IGNORECASE)
        if not match:
            continue

        hostname = extract_url_hostname(match.group(1))
        if hostname:
            domain_counts[hostname] += 1

    return domain_counts


def rewrite_shortcut_text(text: str, target_domain: str) -> tuple[str, str | None, str | None]:
    changed = False
    first_original_url: str | None = None
    first_new_url: str | None = None
    output_lines: list[str] = []

    for line in text.splitlines(keepends=True):
        if line.endswith("\r\n"):
            body = line[:-2]
            ending = "\r\n"
        elif line.endswith("\n") or line.endswith("\r"):
            body = line[:-1]
            ending = line[-1]
        else:
            body = line
            ending = ""

        match = re.match(r"^(\s*URL\s*=\s*)(.*)$", body, re.IGNORECASE)
        if not match:
            output_lines.append(line)
            continue

        prefix, original_url = match.groups()
        new_url = rewrite_url_domain(original_url, target_domain)
        if not new_url or new_url == original_url.strip():
            output_lines.append(line)
            continue

        if first_original_url is None:
            first_original_url = original_url.strip()
            first_new_url = new_url
        output_lines.append(f"{prefix}{new_url}{ending}")
        changed = True

    if not changed:
        return text, None, None

    return "".join(output_lines), first_original_url, first_new_url


def prompt_folder_path() -> Path | str | None:
    while True:
        try:
            raw_folder = input("请输入快捷方式所在文件夹（b 返回主菜单，q 退出） / Shortcut folder: ").strip()
        except EOFError:
            return None
        if raw_folder.lower() in {"b", "q"}:
            return raw_folder.lower()
        if not raw_folder:
            print("文件夹路径不能为空。")
            continue

        folder = resolve_path(raw_folder)
        if not folder.exists() or not folder.is_dir():
            print(f"路径不是有效文件夹: {folder}")
            continue
        return folder


def find_shortcut_files(folder: Path) -> list[Path]:
    shortcut_files: list[Path] = []
    for root, _dirnames, filenames in os.walk(folder):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() == ".url":
                shortcut_files.append(file_path)
    return sorted(shortcut_files, key=lambda path: str(path).lower())


def scan_shortcuts(folder: Path, target_domain: str) -> tuple[list[ShortcutChange], list[str], Counter[str]]:
    changes: list[ShortcutChange] = []
    errors: list[str] = []
    domain_counts: Counter[str] = Counter()

    for shortcut_file in find_shortcut_files(folder):
        try:
            raw_bytes = shortcut_file.read_bytes()
            original_text, encoding = decode_shortcut(raw_bytes)
            domain_counts.update(collect_domain_counts(original_text))
            new_text, original_url, new_url = rewrite_shortcut_text(original_text, target_domain)
        except OSError as exc:
            errors.append(f"{shortcut_file}: {exc}")
            continue

        if original_url and new_url and new_text != original_text:
            changes.append(
                ShortcutChange(
                    path=shortcut_file,
                    encoding=encoding,
                    original_url=original_url,
                    new_url=new_url,
                    original_text=original_text,
                    new_text=new_text,
                    original_bytes=raw_bytes,
                )
            )

    return changes, errors, domain_counts


def print_domain_counts(domain_counts: Counter[str]) -> None:
    print()
    print("域名出现次数 / Domain counts:")

    if not domain_counts:
        print("- 未发现 URL= 链接域名")
        return

    for domain, count in domain_counts.most_common(DOMAIN_COUNT_LIMIT):
        marker = " (fc2)" if host_contains_fc2(domain) else ""
        print(f"- {domain}: {count}{marker}")

    if len(domain_counts) > DOMAIN_COUNT_LIMIT:
        print(f"... 还有 {len(domain_counts) - DOMAIN_COUNT_LIMIT} 个域名未显示")


def print_scan_summary(
    folder: Path,
    target_domain: str,
    changes: list[ShortcutChange],
    errors: list[str],
    domain_counts: Counter[str],
) -> None:
    print()
    print("扫描完成 / Scan complete")
    print(f"文件夹: {folder}")
    print(f"目标域名: {target_domain}")
    print(f"发现域名种类: {len(domain_counts)}")
    print_domain_counts(domain_counts)
    print()
    print(f"需要修改的快捷方式数: {len(changes)}")

    if changes:
        print()
        print("预览 / Preview:")
        color = supports_color()
        for change in changes[:SHORTCUT_PREVIEW_LIMIT]:
            original_url, new_url = format_changed_pair(
                change.original_url, change.new_url, color=color
            )
            print(f"- {change.path}")
            print(f"  {original_url}")
            print(f"  -> {new_url}")
        if len(changes) > SHORTCUT_PREVIEW_LIMIT:
            print(f"... 还有 {len(changes) - SHORTCUT_PREVIEW_LIMIT} 个未显示")

    if errors:
        print()
        print(f"扫描错误数: {len(errors)}")
        for error in errors[:SHORTCUT_PREVIEW_LIMIT]:
            print(f"- {error}")
        if len(errors) > SHORTCUT_PREVIEW_LIMIT:
            print(f"... 还有 {len(errors) - SHORTCUT_PREVIEW_LIMIT} 个错误未显示")


def confirm_update() -> bool:
    while True:
        print()
        print("请选择操作 / Choose action:")
        print("1. 修改以上快捷方式域名")
        print("b. 返回主菜单    q. 退出")
        try:
            choice = input("请输入数字（回车默认 1） / Enter number: ").strip() or "1"
        except EOFError:
            raise QuitTool from None
        if choice.lower() == "b":
            raise BackToMainMenu
        if choice.lower() == "q":
            raise QuitTool
        if choice == "1":
            return True
        print("请输入 1，或输入 b 返回、q 退出。")


def choose_target_domain() -> str | None:
    """选择域名模式；回车只用于选择数字菜单的首项。"""
    while True:
        print("1. 使用默认域名 fc2cmadb.com")
        print("2. 输入其他目标域名")
        print("3. 按文件夹选择并撤销域名修改")
        print("q. 退出")
        try:
            choice = input("请输入数字（回车默认 1） / Enter number: ").strip() or "1"
        except EOFError:
            return None
        if choice.lower() == "q":
            return None
        if choice == "1":
            return DEFAULT_SHORTCUT_DOMAIN
        if choice == "3":
            return UNDO_MENU_CHOICE
        if choice == "2":
            while True:
                try:
                    raw_domain = input("请输入目标域名（b 返回主菜单，q 退出） / Target domain: ").strip()
                except EOFError:
                    return None
                if raw_domain.lower() == "b":
                    break
                if raw_domain.lower() == "q":
                    return None
                if not raw_domain:
                    print("目标域名不能为空。")
                    continue
                try:
                    return normalize_domain(raw_domain)
                except ValueError as exc:
                    print(exc)
            continue
        print("请输入 1、2、3，或输入 q 退出。")


def apply_changes(changes: list[ShortcutChange], folder: Path) -> tuple[int, list[str]]:
    changed_count = 0
    errors: list[str] = []
    writable: list[tuple[ShortcutChange, bytes]] = []
    entries: list[dict] = []

    for change in changes:
        try:
            if change.path.read_bytes() != change.original_bytes:
                errors.append(f"{change.path}: 预览后文件已变化，已跳过")
                continue
            updated_bytes = change.new_text.encode(change.encoding)
        except (LookupError, OSError, UnicodeEncodeError) as exc:
            errors.append(f"{change.path}: {exc}")
            continue
        writable.append((change, updated_bytes))
        entries.append({
            "path": str(change.path),
            "original_b64": base64.b64encode(change.original_bytes).decode("ascii"),
            "updated_sha256": hashlib.sha256(updated_bytes).hexdigest(),
            "old_domain": extract_url_hostname(change.original_url),
            "new_domain": extract_url_hostname(change.new_url),
        })

    if writable:
        history_path = write_batch(UNDO_TOOL_NAME, entries, folder)
        print(f"撤销记录: {history_path}")

    for change, updated_bytes in writable:
        try:
            change.path.write_bytes(updated_bytes)
        except OSError as exc:
            errors.append(f"{change.path}: {exc}")
            continue
        changed_count += 1

    return changed_count, errors


def undo_menu() -> int:
    """列出未撤销批次的处理目录，选择一批预览并恢复。"""
    while True:
        choices = []
        for history_path in pending_batches(UNDO_TOOL_NAME):
            try:
                record = read_batch(history_path)
                folders = batch_folder_paths(record, "path")
            except (OSError, ValueError, KeyError) as exc:
                print(f"[跳过无效记录] {history_path.name}: {exc}")
                continue
            choices.append((history_path, folders, record))
        if not choices:
            print("没有可撤销的快捷方式修改批次。")
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


def undo_batch(history_path: Path) -> bool:
    try:
        entries = read_batch(history_path)["entries"]
    except (OSError, ValueError) as exc:
        print(f"[停止] 撤销记录无法读取: {exc}")
        return False
    print(f"所选批次撤销预览: {history_path.name}")
    color = supports_color()
    for entry in entries:
        new_domain, old_domain = format_changed_pair(
            entry.get("new_domain") or "?", entry.get("old_domain") or "?", color=color
        )
        print(f"- {entry['path']}: {new_domain} -> {old_domain}")

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

    restore: list[tuple[Path, bytes]] = []
    for entry in entries:
        path = Path(entry["path"])
        try:
            current = path.read_bytes()
            original = base64.b64decode(entry["original_b64"], validate=True)
        except (OSError, ValueError) as exc:
            print(f"[停止] 无法读取撤销目标 {path}: {exc}")
            return False
        if current == original:
            continue
        if hashlib.sha256(current).hexdigest() != entry["updated_sha256"]:
            print(f"[停止] 文件已被其他操作修改: {path}")
            return False
        restore.append((path, original))

    for path, original in restore:
        try:
            path.write_bytes(original)
        except OSError as exc:
            print(f"[停止] 恢复失败 {path}: {exc}")
            return False
    mark_undone(history_path)
    print(f"本批撤销完成：恢复 {len(restore)} 个快捷方式。")
    return True


def update_folder(folder: Path, target_domain: str) -> int:
    """单次扫描、确认和修改，供参数模式与连续交互共用。"""
    changes, scan_errors, domain_counts = scan_shortcuts(folder, target_domain)
    print_scan_summary(folder, target_domain, changes, scan_errors, domain_counts)

    if not changes:
        print("没有需要修改的快捷方式。")
        return 0 if not scan_errors else 1

    confirm_update()

    try:
        changed_count, update_errors = apply_changes(changes, folder)
    except OSError as exc:
        print(f"无法保存撤销记录，未修改快捷方式: {exc}")
        return 1
    print()
    print("修改完成 / Update complete")
    print(f"成功修改快捷方式数: {changed_count}")
    print(f"目标域名: {target_domain}")

    all_errors = scan_errors + update_errors
    if all_errors:
        print(f"错误数: {len(all_errors)}")
        for error in all_errors[:SHORTCUT_PREVIEW_LIMIT]:
            print(f"- {error}")
        if len(all_errors) > SHORTCUT_PREVIEW_LIMIT:
            print(f"... 还有 {len(all_errors) - SHORTCUT_PREVIEW_LIMIT} 个错误未显示")
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    configure_console()
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--undo":
        if len(args) != 1:
            print("用法: python -m tools.update_shortcut_domains --undo")
            return 2
        try:
            return undo_menu()
        except (BackToMainMenu, QuitTool):
            return 0
    if len(args) > 2:
        print("用法: python -m tools.update_shortcut_domains [文件夹路径] [目标域名]")
        return 2

    if args:
        try:
            target_domain = normalize_domain(args[1] if len(args) == 2 else DEFAULT_SHORTCUT_DOMAIN)
        except ValueError as exc:
            print(exc)
            return 1
        folder = resolve_path(args[0])
        if not folder.exists() or not folder.is_dir():
            print(f"路径不是有效文件夹: {folder}")
            return 1
        try:
            return update_folder(folder, target_domain)
        except (BackToMainMenu, QuitTool):
            return 0

    target_domain = None
    last_exit_code = 0
    while True:
        if target_domain is None:
            target_domain = choose_target_domain()
            if target_domain is None:
                return last_exit_code
            if target_domain == UNDO_MENU_CHOICE:
                target_domain = None
                try:
                    undo_menu()
                except BackToMainMenu:
                    continue
                except QuitTool:
                    return last_exit_code
                continue
        folder = prompt_folder_path()
        if folder is None or folder == "q":
            return last_exit_code
        if folder == "b":
            target_domain = None
            continue
        try:
            last_exit_code = update_folder(folder, target_domain)
        except BackToMainMenu:
            target_domain = None
            continue
        except QuitTool:
            return last_exit_code
        print("当前目标域名保持不变；输入下一个文件夹，b 返回主菜单，q 退出。")


if __name__ == "__main__":
    raise SystemExit(main())
