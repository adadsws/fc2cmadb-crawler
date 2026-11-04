"""终端预览中标出源文本与目标文本的差异。"""

from __future__ import annotations

import os
import sys
from difflib import SequenceMatcher
from typing import TextIO


def supports_color(stream: TextIO | None = None) -> bool:
    """只在交互终端中着色；Windows CMD 需要启用 VT 序列。"""
    stream = sys.stdout if stream is None else stream
    if not stream.isatty():
        return False
    if os.name != "nt":
        return True

    import ctypes
    import msvcrt

    try:
        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint()
        kernel32 = ctypes.windll.kernel32
        kernel32.GetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint))
        kernel32.SetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError, ValueError):
        return False


def _changed_masks(source: str, target: str) -> tuple[list[bool], list[bool]]:
    """用最长共同子序列保留尽量多的相同字符。"""
    prefix = 0
    limit = min(len(source), len(target))
    while prefix < limit and source[prefix] == target[prefix]:
        prefix += 1

    suffix = 0
    while (
        suffix < len(source) - prefix
        and suffix < len(target) - prefix
        and source[-1 - suffix] == target[-1 - suffix]
    ):
        suffix += 1

    source_mask = [True] * len(source)
    target_mask = [True] * len(target)
    for index in range(prefix):
        source_mask[index] = target_mask[index] = False
    for index in range(1, suffix + 1):
        source_mask[-index] = target_mask[-index] = False

    source_end = len(source) - suffix
    target_end = len(target) - suffix
    old = source[prefix:source_end]
    new = target[prefix:target_end]
    if not old or not new:
        return source_mask, target_mask

    if len(old) * len(new) > 250_000:
        matches = ((block.a, block.b, block.size) for block in SequenceMatcher(
            None, old, new, autojunk=False
        ).get_matching_blocks())
    else:
        # 名称通常较短；动态规划得到总标色字符数最少的对齐。
        rows = [[0] * (len(new) + 1) for _ in range(len(old) + 1)]
        for old_index in range(len(old) - 1, -1, -1):
            for new_index in range(len(new) - 1, -1, -1):
                if old[old_index] == new[new_index]:
                    rows[old_index][new_index] = rows[old_index + 1][new_index + 1] + 1
                else:
                    rows[old_index][new_index] = max(
                        rows[old_index + 1][new_index], rows[old_index][new_index + 1]
                    )
        aligned: list[tuple[int, int, int]] = []
        old_index = new_index = 0
        while old_index < len(old) and new_index < len(new):
            if old[old_index] == new[new_index]:
                aligned.append((old_index, new_index, 1))
                old_index += 1
                new_index += 1
            elif rows[old_index + 1][new_index] >= rows[old_index][new_index + 1]:
                old_index += 1
            else:
                new_index += 1
        matches = aligned

    for old_start, new_start, size in matches:
        for offset in range(size):
            source_mask[prefix + old_start + offset] = False
            target_mask[prefix + new_start + offset] = False
    return source_mask, target_mask


def format_changed_pair(source: str, target: str, *, color: bool) -> tuple[str, str]:
    """多处变化分别标色，尽量缩短两侧标色文字的总长度。"""
    if not color:
        return source, target
    source_mask, target_mask = _changed_masks(source, target)

    def render(value: str, mask: list[bool], background: str) -> str:
        pieces: list[str] = []
        start = 0
        while start < len(value):
            end = start + 1
            while end < len(value) and mask[end] == mask[start]:
                end += 1
            part = value[start:end]
            pieces.append(f"\x1b[97;{background}m{part}\x1b[0m" if mask[start] else part)
            start = end
        return "".join(pieces)

    return render(source, source_mask, "41"), render(target, target_mask, "42")
