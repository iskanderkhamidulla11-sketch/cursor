@echo off
setlocal
cd /d "%~dp0"

set "BOT_TOKEN=8744061218:AAEqVgx_kCCfminLJuHy2tQ0vTJ-Prs2Gm8"
set "WEBAPP_URL=https://iskanderkhamidulla11-sketch.github.io/cursor/frontend/"

if not exist "backend\venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -m venv "backend\venv"
)

echo Installing dependencies...
call "backend\venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"

echo Starting Telegram bot...
call "backend\venv\Scripts\python.exe" "backend\main.py"

endlocal
