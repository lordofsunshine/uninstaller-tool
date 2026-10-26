@echo off
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py
    goto finished
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    goto finished
)

echo [!] The virtual environment was not found.
echo [!] Run setup.bat first.
pause
exit /b 1

:finished
if errorlevel 1 (
    echo.
    echo [!] The program exited with an error.
    pause
)
