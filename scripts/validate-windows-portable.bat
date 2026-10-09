@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0SlideExtractor.exe" (
  echo Run this validator inside the extracted portable app folder.
  pause
  exit /b 1
)
if exist "%~dp0validation-smoke.json" del "%~dp0validation-smoke.json"
if exist "%~dp0validation-smoke.json" (
  echo Cannot replace old validation report. Use a writable folder.
  pause
  exit /b 1
)
set "PATH="
set "QT_QPA_PLATFORM=offscreen"
start "" /wait "%~dp0SlideExtractor.exe" --smoke-report "%~dp0validation-smoke.json"
set "VALIDATION_RESULT=%ERRORLEVEL%"
if not exist "%~dp0validation-smoke.json" (
  echo Validation did not write a report.
  pause
  exit /b 1
)
type "%~dp0validation-smoke.json"
if not "%VALIDATION_RESULT%"=="0" echo Validation failed. Keep validation-smoke.json for diagnosis.
pause
exit /b %VALIDATION_RESULT%
