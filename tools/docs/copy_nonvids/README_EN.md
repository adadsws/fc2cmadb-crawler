# Copy non-video files

[Chinese](README.md) | [English](README_EN.md)

Copy non-video files to another location while preserving the folder structure. The source folder stays unchanged.

## Features

- Videos are skipped; images, documents, and other files are copied.
- Choose the project `~outputs/` folder, `<source folder name>_nonvids` beside the source, or a destination you enter.
- An existing destination requires confirmation; files with matching names may be overwritten.

## 1. Prepare the environment

Install Python 3 and run `python --version` to check that it works. Crawler dependencies are not needed.

## 2. Install the tool

This tool is included with the [main project](../../../README_EN.md). Download or clone the project and open a terminal in its root folder. No extra Python packages are required.

## 3. Use the tool

Run `python -m tools.copy_nonvids` or double-click `tools/run_copy_nonvids.bat`. Enter a source folder and choose a destination. You can also run:

```powershell
python -m tools.copy_nonvids "source folder" "destination folder"
```

In the destination menu, `1` copies beside the source as `<source folder name>_nonvids`, `2` uses the default project output path, and `3` asks for a destination. Enter selects `1`; folder paths must be entered explicitly. After one folder, enter another to continue. Use `b` for the main menu and `q` to exit. The default project destination is under `~outputs/`.
