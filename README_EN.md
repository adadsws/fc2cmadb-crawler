# FC2 PPV Data Crawler

[Chinese](README.md) | [English](README_EN.md)

This tool crawls actress and video information from `fc2cmadb.com`, creates one folder per video, and creates only one actress-page `.url` shortcut in the actress folder.

[Introduction video (Bilibili)](https://www.bilibili.com/video/BV11zzfBMEWu)

Please do not misuse this script. If this project infringes your copyright, please contact the author to request its removal.

## Features

- Crawls all videos for a specified actress, with pagination support.
- Creates folders named `fc2-ppv-{ID} {maker}-{video title}`.
- Automatically truncates overly long folder names and marks them with `+++`.
- Verifies the number of extracted videos after crawling and reports success only when the counts match.
- Includes tools for copying non-media files and updating shortcut domains.

## Installation

Python 3.x and Chrome are required.

```bash
git clone https://github.com/adadsws/fc2cmadb-crawler.git
cd fc2cmadb-crawler
pip install -r requirements.txt
```

## Sign-in

On the first launch, the program starts a normal visible Chrome window and then attaches Selenium through a local debugging port. Sign in to `fc2cmadb.com` in that window, then return to the terminal and press Enter. The sign-in state is stored in a dedicated local Chrome profile and is reused on later launches. You only need to sign in again when the site reports that the session is no longer valid.

On Windows, the profile is stored at `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile` by default. It is outside the project directory and is never committed to Git. Do not delete it unless you want to clear the saved sign-in state.

## Running the crawler

The default actress ID is configured in `fc2cmadb_crawler/config.py`:

```python
DEFAULT_ACTRESS_ID = 10436
```

Start the crawler with:

```bash
python -m fc2cmadb_crawler.main
```

On Windows, you can also double-click:

```text
run_fc2cmadb_crawler.bat
```

The program first checks the currently open project-Chrome page. If it already proves that the profile is signed in, the home page is not revisited; otherwise the program performs at most one preparation navigation before showing the task menu:

- Press Enter to use the configured default actress ID.
- Enter a multi-digit number directly to keep the legacy actress-ID behavior.
- Enter `1` for explicit actress-ID mode. Use this route when the actress ID itself is `2`.
- Enter `2` for FC2-number mode, then enter the digits only, without the `FC2-PPV-` prefix. The program resolves the unique actress ID from the article page and reuses the existing actress crawl.
- Enter `q` to quit.

If an FC2 article has no actress or more than one distinct actress ID, the program refuses to guess and returns to the task menu.

All preparation pages, actress pages, pagination, and FC2 detail pages use one throttled navigation path. Repeated URLs are skipped, security challenges are allowed to finish automatically before manual action is requested, and the page is not refreshed after manual verification. Exiting the CLI detaches Selenium but leaves the project Chrome open so its cookies and sign-in state can be reused. The actress shortcut keeps the original `id_{actress ID} - latest_{latest number}.url` format; video folders contain no `.url` files.

## Utilities

Copy all files except videos and images while preserving the directory structure:

```bash
python -m tools.copy_non_media_files
python -m tools.copy_non_media_files "D:\source_folder" "D:\target_folder"
```

On Windows, you can double-click `tools/run_copy_non_media_files.bat`.
Without a destination argument, copied files go to `~outputs/<source folder name>_non_media_files/` in this project. An explicitly selected destination is used as provided.

Update `.url` shortcuts whose domains contain `fc2` so they use `fc2cmadb.com`:

```bash
python -m tools.update_shortcut_domains
python -m tools.update_shortcut_domains "D:\shortcut_folder"
```

On Windows, you can double-click `tools/run_update_shortcut_domains.bat`.

## Project structure

```text
fc2cmadb-crawler/
├── AGENTS.md
├── AGENT_CONTEXT.md
├── README.md
├── README_EN.md
├── fc2cmadb_crawler/
│   ├── config.py
│   ├── crawler.py
│   ├── main.py
│   └── __init__.py
├── run_fc2cmadb_crawler.bat
├── tools/
│   ├── copy_non_media_files.py
│   ├── update_shortcut_domains.py
│   ├── run_copy_non_media_files.bat
│   └── run_update_shortcut_domains.bat
├── requirements.txt
├── CHANGELOG.md
├── ~outputs/                  # Generated output; not committed
└── tests/                     # Offline automated tests
```

Generated actress folders are written to `~outputs/` by default. See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for the architecture, development workflow, and known issues.
