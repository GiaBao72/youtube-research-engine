@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python khong tim thay trong PATH.
  echo Hay cai Python 3.10+ va tick "Add Python to PATH".
  pause
  exit /b 1
)

echo [2/4] Creating .venv if needed...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo Tao virtual environment that bai.
    pause
    exit /b 1
  )
)

echo [3/4] Installing requirements...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Cai dependencies that bai.
  pause
  exit /b 1
)

echo [4/4] Starting local CLI helper...
echo.
echo Repo san sang.
echo Dung lenh sau de analyze 1 video:
echo   .venv\Scripts\python -m youtube_research.cli analyze "https://www.youtube.com/watch?v=VIDEO_ID"
echo.
echo Hoac chay web UI bang file start_web.bat
echo.
pause
