@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0rename_vids\scripts\rename-videos.ps1"
set "MEDIA_RENAMER_EXIT=%ERRORLEVEL%"
exit /b %MEDIA_RENAMER_EXIT%
