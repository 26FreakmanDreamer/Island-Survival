@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :run

echo [setup] Creating Python 3.14 virtual environment...
py -3.14 -m venv .venv 2>nul
if errorlevel 1 (
    echo [setup] py launcher unavailable, trying python...
    python -m venv .venv
)
if errorlevel 1 goto :error

echo [setup] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :error

:run
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo [error] Launch failed. See the message above.
pause
exit /b 1
