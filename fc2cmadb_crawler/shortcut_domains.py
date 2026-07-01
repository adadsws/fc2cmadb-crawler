#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .config import (
    DEFAULT_SHORTCUT_DOMAIN,
    DOMAIN_COUNT_LIMIT,
    SHORTCUT_PREVIEW_LIMIT,
)


@dataclass
class ShortcutChange:
    path: Path
    encoding: str
    original_url: str
    new_url: str
    original_text: str
    new_text: str


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


def prompt_folder_path() -> Path:
    while True:
        raw_folder = input("请输入快捷方式所在文件夹 / Shortcut folder: ").strip()
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
        for change in changes[:SHORTCUT_PREVIEW_LIMIT]:
            print(f"- {change.path}")
            print(f"  {change.original_url}")
            print(f"  -> {change.new_url}")
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
        print("0. 取消")
        choice = input("请输入数字 / Enter number: ").strip()
        if choice == "1":
            return True
        if choice == "0":
            return False
        print("请输入 1 或 0。")


def apply_changes(changes: list[ShortcutChange]) -> tuple[int, list[str]]:
    changed_count = 0
    errors: list[str] = []

    for change in changes:
        try:
            with change.path.open("w", encoding=change.encoding, newline="") as shortcut_file:
                shortcut_file.write(change.new_text)
        except (OSError, UnicodeEncodeError) as exc:
            errors.append(f"{change.path}: {exc}")
            continue
        changed_count += 1

    return changed_count, errors


def main(argv: list[str] | None = None) -> int:
    configure_console()
    args = sys.argv[1:] if argv is None else argv

    if len(args) > 2:
        print("用法: python -m fc2cmadb_crawler.update_shortcut_domains [文件夹路径] [目标域名]")
        return 2

    try:
        target_domain = normalize_domain(
            args[1] if len(args) == 2 else DEFAULT_SHORTCUT_DOMAIN
        )
    except ValueError as exc:
        print(exc)
        return 1

    if args:
        folder = resolve_path(args[0])
        if not folder.exists() or not folder.is_dir():
            print(f"路径不是有效文件夹: {folder}")
            return 1
    else:
        folder = prompt_folder_path()

    changes, scan_errors, domain_counts = scan_shortcuts(folder, target_domain)
    print_scan_summary(folder, target_domain, changes, scan_errors, domain_counts)

    if not changes:
        print("没有需要修改的快捷方式。")
        return 0 if not scan_errors else 1

    if not confirm_update():
        print("已取消修改。")
        return 0

    changed_count, update_errors = apply_changes(changes)
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
