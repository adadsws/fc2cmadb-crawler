# Update FC2 folder names

[Chinese](README.md) | [English](README_EN.md)

Update existing FC2 video folder names using current data from `fc2cmadb.com`.

## Features

- Recursively find folders containing `fc2-ppv-<number>` in their names and retrieve current producer and title data.
- Keep all text before the producer, follow the crawler's naming rules for the rest, and leave files inside the folders unchanged.
- Preview changes, skip name conflicts or ambiguous boundaries, and undo multiple recent batches.

## 1. Prepare the environment

Install Python 3 and make sure `fc2cmadb.com` is reachable. Run `python --version` to check your environment.

## 2. Install the tool

This tool is included with the [main project](../../../README_EN.md). Download or clone the project, then install this tool's packages from the project root:

```powershell
python -m pip install requests beautifulsoup4
```

## 3. Use the tool

Run `python -m tools.update_fc2_folder_names` or double-click `tools/run_update_fc2_folder_names.bat`. Enter the root folder to scan and confirm the preview. To preview without renaming:

```powershell
python -m tools.update_fc2_folder_names "root folder" --dry-run
```

The preview lists the before and after names of every folder to be renamed. Choose `2` from the main menu to list folders with undoable changes, newest first. Select a batch by number and confirm its undo preview; you can then choose another batch. After one root folder, enter another to continue. Enter selects `1` in numeric menus; use `b` for the main menu and `q` to exit.
