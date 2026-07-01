#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import COPY_BUFFER_SIZE, MEDIA_EXTENSIONS, PROGRESS_BAR_WIDTH


@dataclass
class ScanResult:
    files_to_copy: list[tuple[Path, int]] = field(default_factory=list)
    bytes_to_copy: int = 0
    excluded_files: int = 0
    excluded_bytes: int = 0
    errors: list[str] = field(default_factory=list)


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


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def format_size(size_in_bytes: int) -> str:
    size = float(size_in_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size_in_bytes} B"


def is_media_file(path: Path) -> bool:
    return path.suffix.lower() in MEDIA_EXTENSIONS


class ProgressBar:
    def __init__(self, total_files: int, total_bytes: int) -> None:
        self.total_files = max(total_files, 1)
        self.total_bytes = total_bytes
        self.copied_files = 0
        self.copied_bytes = 0
        self.last_render_at = 0.0
        self.last_line_length = 0

    def add_bytes(self, copied_bytes: int) -> None:
        self.copied_bytes += copied_bytes
        self.render()

    def finish_file(self) -> None:
        self.copied_files += 1
        self.render()

    def finish(self) -> None:
        self.render(force=True)
        print()

    def render(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_render_at < 0.1:
            return
        self.last_render_at = now

        if self.total_bytes > 0:
            progress = min(self.copied_bytes / self.total_bytes, 1.0)
        else:
            progress = min(self.copied_files / self.total_files, 1.0)

        filled = int(PROGRESS_BAR_WIDTH * progress)
        bar = "#" * filled + "-" * (PROGRESS_BAR_WIDTH - filled)
        line = (
            f"\r复制进度: [{bar}] {progress * 100:6.2f}% "
            f"{format_size(self.copied_bytes)}/{format_size(self.total_bytes)} "
            f"文件 {self.copied_files}/{self.total_files}"
        )
        padding = " " * max(self.last_line_length - len(line), 0)
        sys.stdout.write(line + padding)
        sys.stdout.flush()
        self.last_line_length = len(line)


def prompt_source_path() -> Path:
    while True:
        raw_source = input("请输入源路径 / Source path: ").strip()
        if not raw_source:
            print("源路径不能为空。")
            continue

        source = resolve_path(raw_source)
        if not source.exists() or not source.is_dir():
            print(f"源路径不是有效文件夹: {source}")
            continue
        return source


def prompt_destination_path(default_destination: Path) -> Path:
    raw_destination = input(
        f"请输入目标路径，直接回车使用默认路径 / Destination path [{default_destination}]: "
    ).strip()
    if not raw_destination:
        return default_destination.resolve()
    return resolve_path(raw_destination)


def scan_source(source: Path) -> ScanResult:
    result = ScanResult()

    def on_error(error: OSError) -> None:
        result.errors.append(str(error))

    for root, _dirnames, filenames in os.walk(source, onerror=on_error):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            try:
                file_size = file_path.stat().st_size
            except OSError as exc:
                result.errors.append(f"{file_path}: {exc}")
                continue

            if is_media_file(file_path):
                result.excluded_files += 1
                result.excluded_bytes += file_size
                continue

            result.files_to_copy.append((file_path, file_size))
            result.bytes_to_copy += file_size

    return result


def print_scan_summary(source: Path, result: ScanResult) -> None:
    print()
    print("扫描完成 / Scan complete")
    print(f"源路径: {source}")
    print(f"将复制文件数: {len(result.files_to_copy)}")
    print(f"将复制总大小: {format_size(result.bytes_to_copy)}")
    print(f"已排除视频/图片文件数: {result.excluded_files}")
    print(f"已排除视频/图片总大小: {format_size(result.excluded_bytes)}")
    if result.errors:
        print(f"扫描时跳过错误数: {len(result.errors)}")
        for error in result.errors[:10]:
            print(f"  - {error}")
        if len(result.errors) > 10:
            print(f"  ... 还有 {len(result.errors) - 10} 个错误未显示")


def prompt_copy_destination(
    source: Path,
    default_destination: Path,
    destination_arg: str | None = None,
) -> Path | None:
    specified_destination = resolve_path(destination_arg) if destination_arg else None

    while True:
        print()
        print("请选择操作 / Choose action:")
        if specified_destination is not None:
            print(f"1. 复制到指定目标路径: {specified_destination}")
        else:
            print(f"1. 复制到默认目标路径: {default_destination.resolve()}")
        print("2. 手动输入目标路径后复制")
        print("0. 取消")

        choice = input("请输入数字 / Enter number: ").strip()
        if choice == "0":
            return None
        if choice == "1":
            destination = specified_destination or default_destination.resolve()
        elif choice == "2":
            destination = prompt_destination_path(default_destination)
        else:
            print("请输入 1、2 或 0。")
            continue

        if destination == source or is_relative_to(destination, source):
            print("目标路径不能等于源路径，也不能放在源路径内部。")
            continue

        return destination


def confirm_existing_destination(destination: Path) -> bool:
    if not destination.exists():
        return True

    print("注意: 目标路径已存在，同名文件会被覆盖。")
    while True:
        print()
        print("请选择操作 / Choose action:")
        print("1. 继续复制并覆盖同名文件")
        print("0. 取消")
        choice = input("请输入数字 / Enter number: ").strip()
        if choice == "1":
            return True
        if choice == "0":
            return False
        print("请输入 1 或 0。")


def copy_file_with_progress(source: Path, target: Path, progress: ProgressBar) -> None:
    with source.open("rb") as source_file, target.open("wb") as target_file:
        while True:
            chunk = source_file.read(COPY_BUFFER_SIZE)
            if not chunk:
                break
            target_file.write(chunk)
            progress.add_bytes(len(chunk))

    shutil.copystat(source, target)
    progress.finish_file()


def copy_files(source: Path, destination: Path, result: ScanResult) -> tuple[int, int, list[str]]:
    copied_files = 0
    copied_bytes = 0
    errors: list[str] = []
    progress = ProgressBar(len(result.files_to_copy), result.bytes_to_copy)

    print("开始复制 / Copying...")
    progress.render(force=True)
    for file_path, file_size in result.files_to_copy:
        relative_path = file_path.relative_to(source)
        target_path = destination / relative_path
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            copy_file_with_progress(file_path, target_path, progress)
        except OSError as exc:
            errors.append(f"{file_path} -> {target_path}: {exc}")
            continue

        copied_files += 1
        copied_bytes += file_size

    progress.finish()
    return copied_files, copied_bytes, errors


def main(argv: list[str] | None = None) -> int:
    configure_console()
    args = sys.argv[1:] if argv is None else argv

    if len(args) > 2:
        print("用法: python -m fc2cmadb_crawler.copy_non_media_files [源路径] [目标路径]")
        return 2

    if args:
        source = resolve_path(args[0])
        if not source.exists() or not source.is_dir():
            print(f"源路径不是有效文件夹: {source}")
            return 1
    else:
        source = prompt_source_path()

    result = scan_source(source)
    print_scan_summary(source, result)

    if not result.files_to_copy:
        print("没有需要复制的非视频/非图片文件。")
        return 0

    default_destination = source.parent / f"{source.name}_non_media_files"
    destination_arg = args[1] if len(args) == 2 else None
    destination = prompt_copy_destination(source, default_destination, destination_arg)
    if destination is None:
        print("已取消复制。")
        return 0

    print(f"目标路径: {destination}")
    if not confirm_existing_destination(destination):
        print("已取消复制。")
        return 0

    copied_files, copied_bytes, copy_errors = copy_files(source, destination, result)
    print()
    print("复制完成 / Copy complete")
    print(f"成功复制文件数: {copied_files}")
    print(f"成功复制总大小: {format_size(copied_bytes)}")
    print(f"输出路径: {destination}")

    if copy_errors:
        print(f"复制失败数: {len(copy_errors)}")
        for error in copy_errors[:10]:
            print(f"  - {error}")
        if len(copy_errors) > 10:
            print(f"  ... 还有 {len(copy_errors) - 10} 个错误未显示")
        return 1

    return 0
