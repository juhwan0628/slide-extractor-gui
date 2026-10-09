@echo off
setlocal
cd /d "%~dp0\.."
where py >nul 2>nul
if errorlevel 1 (echo Install Python 3.11+ from python.org first. & exit /b 1)
where ffmpeg >nul 2>nul
if errorlevel 1 (echo Install FFmpeg and add it to PATH first. & exit /b 1)
where ffprobe >nul 2>nul
if errorlevel 1 (echo Install FFprobe and add it to PATH first. & exit /b 1)
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
.venv\Scripts\python.exe app.py
