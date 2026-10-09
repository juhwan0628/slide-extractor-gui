@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
py -3.12 -c "import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize('P')==8" >nul 2>nul
if errorlevel 1 (
  echo Install Windows x64 Python 3.12 with the Python launcher first.
  echo See INSTALL-WINDOWS.md in this folder.
  pause
  exit /b 1
)
py -3.12 packaging\build_windows_personal.py %*
set "BUILD_RESULT=%ERRORLEVEL%"
if not "%BUILD_RESULT%"=="0" (
  echo Build failed. Check build\personal-windows\build.log
) else (
  echo Build and bundled smoke succeeded. The portable ZIP is in dist.
)
pause
exit /b %BUILD_RESULT%
