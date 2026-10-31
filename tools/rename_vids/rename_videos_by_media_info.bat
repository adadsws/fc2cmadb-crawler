@echo off
setlocal
set "MEDIA_RENAMER_SELF=%~f0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\rename-videos.ps1"
set "MEDIA_RENAMER_EXIT=%ERRORLEVEL%"
set "MEDIA_RENAMER_SELF="
exit /b %MEDIA_RENAMER_EXIT%
