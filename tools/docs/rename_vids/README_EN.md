# Rename videos

[Chinese](README.md) | [English](README_EN.md)

Rename videos and their folders using total bitrate and frame height.

## Features

- The default video name format is `movie [023Mbps_2048p].mp4`; containing folders receive a tag in the same format.
- Review a preview before confirming any rename.
- Undo multiple recent batches. When a target name already exists, that target is archived so it can be restored.

## 1. Prepare the environment

You need Windows PowerShell and `ffprobe.exe`. Follow the [FFprobe setup guide](../../rename_vids/reference/tools/ffmpeg.md) to place `ffprobe.exe` in `tools/rename_vids/`, or add it to your system `PATH`.

## 2. Install the tool

This tool is included with the [main project](../../../README_EN.md). Download or clone the project and complete the FFprobe setup above. No Python packages are needed.

## 3. Use the tool

Double-click `tools/rename_videos_by_media_info.bat`, choose `1`, and enter a video folder. The preview groups changes by folder, showing each folder rename before all file renames within it. Confirm to apply them. Rename mode stays active so you can enter another folder.

Choose `2` from the main menu to list folders with undoable changes, newest first. Select a batch by number, review its before and after names grouped by folder and files, and confirm. You can then select another batch. Enter selects `1` in numeric menus. Use `b` for the main menu and `q` to exit.
