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
PAGE_WAIT_SECONDS = 20
NAVIGATION_TIMEOUT_SECONDS = 30
MANUAL_CHALLENGE_WAIT_SECONDS = 120
CHROME_STARTUP_WAIT_SECONDS = 20
MIN_NAVIGATION_INTERVAL_SECONDS = 0.8
MAX_FILM_FOLDER_NAME_LENGTH = 80
FOLDER_TRUNCATION_SUFFIX = "+++"
