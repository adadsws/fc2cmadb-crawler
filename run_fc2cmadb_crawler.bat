@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\Administrator\anaconda3\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo Running FC2CMADB crawler from:
echo %CD%
echo.

"%PYTHON_EXE%" "%~dp0main.py"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if not "%EXIT_CODE%"=="0" (
    echo Script exited with code %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
