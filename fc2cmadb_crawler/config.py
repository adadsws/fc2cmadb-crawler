from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Main crawler settings
DEFAULT_ACTRESS_ID = 10436
SITE_BASE_URL = "https://fc2cmadb.com"
OUTPUT_DIR = str(PROJECT_ROOT / "~outputs")
# 独立于项目的持久浏览器状态，保存用户手动登录后的 Chrome profile。
CHROME_PROFILE_DIR = Path(
    os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
) / "fc2cmadb-crawler" / "chrome-profile"
MAX_FILM_FOLDER_NAME_LENGTH = 80
FOLDER_TRUNCATION_SUFFIX = "+++"
