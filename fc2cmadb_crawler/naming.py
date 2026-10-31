"""主爬虫与独立工具共用的 FC2 作品目录命名规则。"""

from __future__ import annotations

from .config import FOLDER_TRUNCATION_SUFFIX, MAX_FILM_FOLDER_NAME_LENGTH


def safe_filename(filename: str, replace_char: str = " ") -> str:
    for char in '<>:"/\\|?*':
        filename = filename.replace(char, replace_char)
    return filename.strip()


def truncate_folder_name(folder_name: str) -> str:
    if len(folder_name) < MAX_FILM_FOLDER_NAME_LENGTH:
        return folder_name
    keep_length = MAX_FILM_FOLDER_NAME_LENGTH - len(FOLDER_TRUNCATION_SUFFIX)
    return folder_name[:keep_length].rstrip() + FOLDER_TRUNCATION_SUFFIX


def format_film_folder_name(film_number: str, producer: str, film_title: str) -> str:
    name = f"fc2-ppv-{film_number} {safe_filename(producer)}-{safe_filename(film_title)}"
    return truncate_folder_name(name)
