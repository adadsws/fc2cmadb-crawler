# FC2 PPV Data Crawler

[Chinese](README.md) | [English](README_EN.md)

This project collects actress and video information from `fc2cmadb.com` and creates folders for each video. It also includes three standalone tools: copy non-video files, fix shortcut domains, and rename videos using media information.

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
- `q`: Exit from the mode menu.

After each task, the selected mode stays active. Enter another number directly, or enter `b` to return to the mode menu. Numbers shown in prompts are examples; pressing Enter does not start a crawl.

Generated folders are written to `~outputs/`. If an FC2 page does not identify one actress, enter another number. Complete any security challenge in the open Chrome window.

## Standalone tools

These tools are unrelated to the crawler's data collection, sign-in, and folder creation. Each runs independently.

| No. | Tool | Purpose | Entry point | Environment setup |
|---|---|---|---|---|
| 1 | Copy files | Copy everything except videos, including images, while keeping the directory structure. | `python -m tools.copy_non_media_files` or double-click `tools/run_copy_non_media_files.bat`. | Python 3; crawler dependencies are not needed. |
| 2 | Fix shortcut domains | Change `.url` domains containing `fc2` to `fc2cmadb.com`. | `python -m tools.update_shortcut_domains` or double-click `tools/run_update_shortcut_domains.bat`. | Python 3; crawler dependencies are not needed. |
| 3 | Rename videos | Add total bitrate and frame height to video and containing directory names. The default format is `name [bitrateMbps_heightp].extension`, for example `movie [023Mbps_2048p].mp4`; directory names get a tag in the same format. Preview and undo are available. | Double-click `tools/rename_vids/rename_videos_by_media_info.bat`. | Windows PowerShell; place `ffprobe.exe` beside the BAT file or on PATH. See [FFprobe setup](tools/rename_vids/reference/tools/ffmpeg.md). |

See [AGENT_CONTEXT.md](AGENT_CONTEXT.md) for the project structure and tests.
