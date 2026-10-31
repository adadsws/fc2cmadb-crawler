"""终端预览中标出源文本与目标文本的差异。"""

from __future__ import annotations

import os
import sys
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


def format_changed_pair(source: str, target: str, *, color: bool) -> tuple[str, str]:
    """共同前后缀保持原样，仅给两个字符串各自变化的部分着色。"""
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

    def render(value: str, background: str) -> str:
        end = len(value) - suffix if suffix else len(value)
        changed = value[prefix:end]
        if not color or not changed:
            return value
        return value[:prefix] + f"\x1b[97;{background}m{changed}\x1b[0m" + value[end:]

    return render(source, "41"), render(target, "42")
