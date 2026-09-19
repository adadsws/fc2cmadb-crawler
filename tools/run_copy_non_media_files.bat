@echo off
setlocal
cd /d "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Please install Python or run: python -m tools.copy_non_media_files
    pause
    exit /b 1
)

python -m tools.copy_non_media_files
echo.
pause
