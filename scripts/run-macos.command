#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN=python3.12
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
else
  echo 'Python 3.12 recommended (brew install python@3.12)'; exit 1
fi
if ! "$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo 'Python 3.11+ required; try brew install python@3.12'; exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo 'Install FFmpeg: brew install ffmpeg'; exit 1
fi
if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python app.py
