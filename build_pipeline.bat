@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run start_local.bat or start_web.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m youtube_research.cli build-pipeline %*
