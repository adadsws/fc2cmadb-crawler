#!/usr/bin/env python3
"""扫描源目录并复制非视频文件；默认结果写入项目输出目录。"""
from __future__ import annotations

import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import COPY_BUFFER_SIZE, VIDEO_EXTENSIONS, PROGRESS_BAR_WIDTH
from .preview_colors import format_changed_pair, supports_color


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BackToMainMenu(Exception):
    """结束当前目标选择，回到源路径入口。"""


class QuitTool(Exception):
    """从任意输入层级退出。"""


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


def default_copy_destination(source: Path) -> Path:
    return PROJECT_ROOT / "~outputs" / f"{source.name}_nonvids"


def sibling_copy_destination(source: Path) -> Path:
    """在源目录旁生成非视频副本目录，根目录没有可用的相邻目录。"""
    if source.parent == source:
        raise ValueError("磁盘根目录没有相邻目标目录，请选择其他目标路径")
    return source.with_name(f"{source.name}_nonvids")


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


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


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


def prompt_source_path() -> Path | str | None:
    while True:
        try:
            raw_source = input("请输入源路径（b 返回主菜单，q 退出） / Source path: ").strip()
        except EOFError:
            return None
        if raw_source.lower() in {"b", "q"}:
            return raw_source.lower()
        if not raw_source:
            print("源路径不能为空。")
            continue

        source = resolve_path(raw_source)
        if not source.exists() or not source.is_dir():
            print(f"源路径不是有效文件夹: {source}")
            continue
        return source


def prompt_destination_path(default_destination: Path) -> Path | None:
    while True:
        try:
            raw_destination = input("请输入目标路径（b 返回主菜单，q 退出） / Destination path: ").strip()
        except EOFError:
            raise QuitTool from None
        if raw_destination.lower() == "b":
            raise BackToMainMenu
        if raw_destination.lower() == "q":
            raise QuitTool
        if raw_destination:
            return resolve_path(raw_destination)
        print("目标路径不能为空；默认路径请在数字菜单选择 2。")


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

            if is_video_file(file_path):
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
    print(f"已排除视频文件数: {result.excluded_files}")
    print(f"已排除视频总大小: {format_size(result.excluded_bytes)}")
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
    current_mode: str | None = None,
) -> tuple[Path, str]:
    specified_destination = resolve_path(destination_arg) if destination_arg else None

    while True:
        try:
            sibling_destination = sibling_copy_destination(source)
        except ValueError:
            sibling_destination = None
        if current_mode is None:
            print()
            print("请选择操作 / Choose action:")
            if sibling_destination is not None:
                print(f"1. 复制到源目录旁: {sibling_destination}")
            if specified_destination is not None:
                print(f"2. 复制到指定目标路径: {specified_destination}")
            else:
                print(f"2. 复制到默认目标路径: {default_destination.resolve()}")
        if current_mode is None:
            print("3. 手动输入目标路径后复制")
            print("b. 返回主菜单    q. 退出")
            default_choice = "1" if sibling_destination is not None else "2"
            try:
                choice = input(f"请输入数字（回车默认 {default_choice}） / Enter number: ").strip() or default_choice
            except EOFError:
                raise QuitTool from None
        else:
            choice = current_mode
        if choice.lower() == "b":
            raise BackToMainMenu
        if choice.lower() == "q":
            raise QuitTool
        if choice == "1":
            if sibling_destination is None:
                print("磁盘根目录没有相邻目标目录，请选择其他目标路径。")
                current_mode = None
                continue
            destination = sibling_destination
        elif choice == "2":
            destination = specified_destination or default_destination.resolve()
        elif choice == "3":
            destination = prompt_destination_path(default_destination)
        else:
            print("请输入 1、2、3，或输入 b 返回、q 退出。")
            current_mode = None
            continue

        destination = destination.resolve()
        if destination == source or is_relative_to(destination, source):
            print("目标路径不能等于源路径，也不能放在源路径内部。")
            current_mode = None
            continue

        return destination, choice


def confirm_existing_destination(destination: Path) -> bool:
    if not destination.exists():
        return True

    print("注意: 目标路径已存在，同名文件会被覆盖。")
    while True:
        print()
        print("请选择操作 / Choose action:")
        print("1. 继续复制并覆盖同名文件")
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
            if is_relative_to(target_path.resolve(), source):
                errors.append(f"目标路径指向源目录，已跳过: {target_path}")
                continue
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
        print("用法: python -m tools.copy_nonvids [源路径] [目标路径]")
        return 2

    current_mode = None
    last_exit_code = 0
    while True:
        if args:
            source = resolve_path(args[0])
            if not source.exists() or not source.is_dir():
                print(f"源路径不是有效文件夹: {source}")
                return 1
        else:
            source = prompt_source_path()
            if source is None or source == "q":
                return last_exit_code
            if source == "b":
                current_mode = None
                continue

        result = scan_source(source)
        print_scan_summary(source, result)
        if not result.files_to_copy:
            print("没有需要复制的非视频文件。")
            if args:
                return 0
            continue

        try:
            destination, current_mode = prompt_copy_destination(
                source, default_copy_destination(source),
                args[1] if len(args) == 2 else None, current_mode,
            )
        except BackToMainMenu:
            current_mode = None
            continue
        except QuitTool:
            return last_exit_code
        source_preview, destination_preview = format_changed_pair(
            str(source), str(destination), color=supports_color()
        )
        print("复制预览 / Copy preview:")
        print(f"  源目录: {source_preview}")
        print(f"  目标目录: {destination_preview}")
        try:
            confirm_existing_destination(destination)
        except BackToMainMenu:
            current_mode = None
            continue
        except QuitTool:
            return last_exit_code
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
            last_exit_code = 1
        else:
            last_exit_code = 0
        if args:
            return last_exit_code
        print("当前复制方式保持不变；输入下一源目录，b 返回主菜单，q 退出。")


if __name__ == "__main__":
    raise SystemExit(main())
