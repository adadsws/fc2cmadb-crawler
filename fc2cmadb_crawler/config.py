from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Main crawler settings
DEFAULT_ACTRESS_ID = 10436
SITE_BASE_URL = "https://fc2cmadb.com"
SITE_HOST = urlparse(SITE_BASE_URL).netloc
SCRIPT_DIR = str(PROJECT_ROOT)
OUTPUT_DIR = str(PROJECT_ROOT / "output")
COOKIE_FILENAME = f"{SITE_HOST}_cookies.txt"
OLD_COOKIE_FILENAME = "fc2ppvdb.com_cookies.txt"
MAX_FILM_FOLDER_NAME_LENGTH = 80
FOLDER_TRUNCATION_SUFFIX = "+++"

# copy_non_media_files.py settings
COPY_BUFFER_SIZE = 1024 * 1024
PROGRESS_BAR_WIDTH = 30

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
    ".avif",
    ".svg",
    ".ico",
    ".psd",
    ".raw",
    ".cr2",
    ".nef",
    ".arw",
    ".dng",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".m2ts",
    ".mts",
    ".3gp",
    ".ogv",
    ".rm",
    ".rmvb",
    ".vob",
    ".asf",
    ".divx",
    ".f4v",
}

MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# update_shortcut_domains.py settings
DEFAULT_SHORTCUT_DOMAIN = "fc2cmadb.com"
SHORTCUT_PREVIEW_LIMIT = 10
DOMAIN_COUNT_LIMIT = 20

