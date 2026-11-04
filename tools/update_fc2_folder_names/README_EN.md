# Update FC2 folder names

[Chinese](README.md) | [English](README_EN.md)

Update existing FC2 video folder names using current seller names from `fc2cmadb.com`.

## Features

- Recursively find folders containing `fc2-ppv-<number>` in their names. Count existing seller names first, process valid cache hits, then query the most frequent uncached names first. Query each name once per batch, and skip the site when a current or old name matches the project's 30-day cache. Accept only an exact seller-name match; the folder's old name must match that seller's current or recorded old name.
- Start or reuse the main crawler's visible Chrome session and confirm sign-in using the same check as the crawler before showing the menu or scanning folders.
- Keep all text before the producer and each folder's original video title. Truncate long names using the crawler's naming rules; leave files inside the folders unchanged.
- Preview changes, skip name conflicts or ambiguous boundaries, and undo multiple recent batches.
- Each run shows one notice when article and search visits reach 50 in total. The program continues, and the count resets on the next launch. Seller names are cached in the project's `~outputs/`. Search visits are at least 12 seconds apart by default; cache hits make no site visit. The first 429 stops further lookups. The prepared partial result is previewed and can be explicitly applied; unprepared folders are skipped.

## 1. Prepare the environment

Install Python 3 and Google Chrome, and make sure `fc2cmadb.com` is reachable. Run `python --version` to check your environment. On first use, you may need to complete site verification or sign in in Chrome.

## 2. Install the tool

This tool is included with the [main project](../../README_EN.md). Download or clone the project, then install this tool's packages from the project root:

```powershell
python -m pip install selenium==4.36.0 beautifulsoup4==4.11.1 requests
```

## 3. Use the tool

Run `python -m tools.update_fc2_folder_names` or double-click `tools/run_update_fc2_folder_names.bat`. The tool prepares Chrome and confirms sign-in first. If signed out, sign in in that Chrome window when prompted; the menu or root scan starts only after confirmation. Select update, enter the root folder to scan, and confirm the preview. To preview without renaming:

```powershell
python -m tools.update_fc2_folder_names "root folder" --dry-run
```

For larger batches, set a minimum interval between search visits (2–32 seconds; default: 12). The BAT entry also accepts these arguments:

```powershell
tools/run_update_fc2_folder_names.bat "root folder" --dry-run --interval 12
```

The preview first shows how many folders would be renamed or skipped; skipped folders are not listed individually. It counts length truncations and producer name updates, summarizes each old-to-new producer change, and lists before and after names only for other changes by default. A folder may count in both of the first two categories. Choose `2` in the confirmation menu to review every pending folder rename, then return to the menu; choose `1` to apply the changes. Choose `2` from the main menu to list folders with undoable changes, newest first. Select a batch by number and confirm its undo preview; you can then choose another batch. After one root folder, enter another to continue. Enter selects `1` in numeric menus; use `b` for the main menu and `q` to exit.

If typed straight double quotes differ from the curly quotes in a folder name, the tool suggests the actual path when there is exactly one match. Copy that path and enter it again.

For undo only, run `python -m tools.update_fc2_folder_names --undo` without starting Chrome.
