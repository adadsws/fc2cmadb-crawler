# Fix shortcut domains

[Chinese](README.md) | [English](README_EN.md)

Update FC2 domains in `.url` web shortcuts within a folder.

## Features

- Recursively find `.url` files and change only links whose domains contain `fc2`.
- Use `fc2cmadb.com` by default or enter another domain; URL paths and parameters are preserved.
- Review changes before confirming, and undo multiple recent batches.

## 1. Prepare the environment

Install Python 3 and run `python --version` to check that it works. Crawler dependencies are not needed.

## 2. Install the tool

This tool is included with the [main project](../../../README_EN.md). Download or clone the project and open a terminal in its root folder. No extra Python packages are required.

## 3. Use the tool

Run `python -m tools.update_shortcut_domains` or double-click `tools/run_update_shortcut_domains.bat`. Choose a target domain, enter the folder containing shortcuts, and confirm the preview. You can also run:

```powershell
python -m tools.update_shortcut_domains "folder" "target domain"
```

Choose `3` from the main menu to list folders with undoable changes, newest first. Select a batch by number, preview all its files, and confirm; you can then choose another batch. After one folder, enter another to continue. Enter selects `1` in numeric menus; use `b` for the main menu and `q` to exit.
