@echo off
setlocal
cd /d "%~dp0"

set "BOT_TOKEN=8744061218:AAEqVgx_kCCfminLJuHy2tQ0vTJ-Prs2Gm8"
set "WEBAPP_URL=https://iskanderkhamidulla11-sketch.github.io/cursor/frontend/"

if not exist "backend\venv\Scripts\python.exe" (
  echo Creating virtual environment...
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -m venv "backend\venv"
  ) else (
    python -m venv "backend\venv"
  )
  if errorlevel 1 (
    echo Failed to create virtual environment.
    echo Install Python 3 and try again.
    pause
    exit /b 1
  )
)

echo Installing dependencies...
call "backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

echo Starting Telegram bot...
call "backend\venv\Scripts\python.exe" "backend\main.py"
set "EXIT_CODE=%errorlevel%"
echo.
echo Bot stopped with exit code: %EXIT_CODE%
pause

endlocal
