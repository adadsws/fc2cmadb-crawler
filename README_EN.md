# FC2 PPV Data Crawler

[Chinese](README.md) | [English](README_EN.md)

This project collects actress and video information from `fc2cmadb.com` and creates folders for each video. It also includes four tools that can be used separately.

[Introduction video (Bilibili)](https://www.bilibili.com/video/BV11zzfBMEWu)

Please do not misuse this script. If this project infringes your copyright, please contact the author to request its removal.

## Features

- Crawls all videos for a specified actress, with pagination support.
- Creates folders named `fc2-ppv-{ID} {maker}-{video title}`.
- Automatically truncates overly long folder names and marks them with `+++`.
- Verifies the number of extracted videos after crawling and reports success only when the counts match.
- Creates one actress-page `.url` shortcut in each actress folder; video folders contain no webpage shortcuts.

## 1. Prepare the environment

On Windows, install [Python 3](https://www.python.org/downloads/windows/) and [Google Chrome](https://www.google.com/chrome/). Open a new Command Prompt or PowerShell window and check that Python and pip work:

```powershell
python --version
python -m pip --version
```

If `python` is not recognized, see the [Python installation guide for Windows](https://docs.python.org/3/using/windows.html) for command setup.

## 2. Install the crawler

If Git is installed, run:

```bash
git clone https://github.com/adadsws/fc2cmadb-crawler.git
cd fc2cmadb-crawler
python -m pip install -r requirements.txt
```

Without Git, download and extract the ZIP from the [project page](https://github.com/adadsws/fc2cmadb-crawler), then run `python -m pip install -r requirements.txt` in the extracted project directory.

## 3. Run the crawler

Run `python -m fc2cmadb_crawler.main`, or double-click `run_fc2cmadb_crawler.bat`. On the first run, sign in to `fc2cmadb.com` in the dedicated Chrome window, then follow the terminal prompt. Later runs try to reuse the sign-in state.

The browser profile is stored at `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`. Exiting the CLI leaves the Chrome window open; close that window manually when you want to end the browser session.

After sign-in, choose an input mode:

- `1`: Enter a numeric actress ID.
- `2`: Enter the numeric FC2 number without the `FC2-PPV-` prefix.
- `q`: Exit from the mode menu or a number prompt.

After each task, the selected mode stays active. Enter another number directly, enter `b` to return to the mode menu, or enter `q` to exit. Numbers shown in prompts are examples; pressing Enter does not start a crawl.

Generated folders are written to `~outputs/`. If an FC2 page does not identify one actress, enter another number. Complete any security challenge in the open Chrome window.

## Tools

Each tool runs on its own. Tool 4 updates the video folders created by this project.

| No. | Tool | Purpose | Entry point | Environment setup |
|---|---|---|---|---|
| 1 | [Copy non-video files](tools/docs/copy_nonvids/README_EN.md) | Copy non-video files while preserving folders. | `python -m tools.copy_nonvids` or `tools/run_copy_nonvids.bat` | Python 3 |
| 2 | [Rename videos](tools/docs/rename_vids/README_EN.md) | Rename videos and folders using media information. | `tools/rename_videos_by_media_info.bat` | Windows PowerShell, FFprobe |
| 3 | [Fix shortcut domains](tools/docs/update_shortcut_domains/README_EN.md) | Update FC2 domains in `.url` shortcuts. | `python -m tools.update_shortcut_domains` or `tools/run_update_shortcut_domains.bat` | Python 3 |
| 4 | [Update FC2 folder names](tools/docs/update_fc2_folder_names/README_EN.md) | Update video folder names from site data. | `python -m tools.update_fc2_folder_names` or `tools/run_update_fc2_folder_names.bat` | Python 3, `requests`, `beautifulsoup4` |
