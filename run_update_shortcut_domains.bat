@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Please install Python or run: python -m fc2cmadb_crawler.update_shortcut_domains
    pause
    exit /b 1
)

python -m fc2cmadb_crawler.update_shortcut_domains
echo.
pause
