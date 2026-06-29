@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Please install Python or run: python copy_non_media_files.py
    pause
    exit /b 1
)

python copy_non_media_files.py
echo.
pause
