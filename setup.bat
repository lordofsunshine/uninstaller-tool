@echo off
color 0B
cls
echo.
echo   ================================
echo    Program Installation Setup
echo   ================================
echo.

echo [*] Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo [!] Python is not installed!
    echo [!] Please install Python 3.x first.
    echo [!] Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo [+] Python is installed successfully
echo.

echo [*] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo [+] Virtual environment created
echo.

echo [*] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo [+] Pip upgraded successfully
echo.

echo [*] Installing required packages...
echo    This may take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    color 0C
    echo.
    echo [!] Error installing packages!
    echo [!] Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo [+] Packages installed successfully
echo.

color 0A
echo   ================================
echo    Setup completed successfully!
echo   ================================
echo.
echo [*] Starting the program...
timeout /t 2 >nul
echo.

python main.py

if errorlevel 1 (
    color 0C
    echo.
    echo [!] Program exited with an error!
    echo.
    pause
)

call venv\Scripts\deactivate.bat 