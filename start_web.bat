@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python khong tim thay trong PATH.
  echo Hay cai Python 3.10+ va tick "Add Python to PATH".
  pause
  exit /b 1
)

echo [2/5] Creating .venv if needed...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo Tao virtual environment that bai.
    pause
    exit /b 1
  )
)

echo [3/5] Installing requirements...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Cai dependencies that bai.
  pause
  exit /b 1
)

echo [4/5] Checking .env...
if not exist ".env" (
  copy .env.example .env >nul
  echo Da tao .env tu .env.example. Hay mo file .env va them OPENAI_API_KEY neu can.
)

echo [5/5] Starting web UI...
set PYTHONPATH=src
start http://127.0.0.1:8787
python -m youtube_research.web
