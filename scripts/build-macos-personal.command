#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo 'Requires Apple Silicon macOS'; exit 1; }
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
mkdir -p build/personal dist
exec > >(tee build/personal/build.log) 2>&1
trap 'echo "Build failed. See build/personal/build.log"' ERR
if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN=python3.12
else
  PYTHON_BIN=python3
fi
"$PYTHON_BIN" -c 'import platform,sys; assert sys.version_info[:2] == (3,12) and platform.machine()=="arm64", "Native arm64 Python 3.12 required"'
command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1 || { echo 'Install FFmpeg first: brew install ffmpeg'; exit 1; }
LOCAL_FFMPEG=$(command -v ffmpeg)
LOCAL_FFPROBE=$(command -v ffprobe)
"$PYTHON_BIN" - "$LOCAL_FFMPEG" "$LOCAL_FFPROBE" <<'PY'
import json,hashlib,shutil,sys
from pathlib import Path
stage=Path('build/personal/tools');stage.mkdir(parents=True,exist_ok=True)
manifest={}
for name,source in zip(('ffmpeg','ffprobe'),sys.argv[1:]):
    source=Path(source).resolve();target=stage/name
    shutil.copy2(source,target)
    manifest[name]={'source':str(source),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
Path('build/personal/tools.json').write_text(json.dumps(manifest,indent=2)+'\n')
PY
export PERSONAL_FFMPEG_DIR="$PWD/build/personal/tools"
if [ ! -x .venv-native-049rc1/bin/python ]; then "$PYTHON_BIN" -m venv .venv-native-049rc1; fi
.venv-native-049rc1/bin/python -m pip install -r packaging/requirements-macos-arm64.lock
.venv-native-049rc1/bin/python -m pip check
.venv-native-049rc1/bin/python packaging/build_manifest.py --tools "$PERSONAL_FFMPEG_DIR" --mode personal --output build/personal/build-manifest.json
.venv-native-049rc1/bin/python -m pip freeze > build/personal/python-packages.txt
.venv-native-049rc1/bin/python -m PyInstaller --clean --noconfirm --distpath dist --workpath build/pyinstaller-personal packaging/SlideExtractor-personal.spec
QT_QPA_PLATFORM=offscreen dist/SlideExtractor.app/Contents/MacOS/SlideExtractor --smoke-report "$PWD/build/personal/installed-smoke.json"
.venv-native-049rc1/bin/python - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('build/personal/installed-smoke.json').read_text())
assert r['status']=='success' and r['frozen'] and r['bundled_tools_checked'], r
print('Bundled Qt, FFmpeg, analysis and PDF export checks passed.')
PY
codesign --verify --deep --strict dist/SlideExtractor.app
export SLIDE_BUILD_MODE=personal
export SLIDE_PYTHON="$PWD/.venv-native-049rc1/bin/python"
bash packaging/build-macos-dmg.sh
APP_VERSION=$("$SLIDE_PYTHON" slide_core/version.py)
printf '\nCreated: dist/SlideExtractor-v%s-macOS-arm64-personal.dmg\nDrag SlideExtractor into Applications, then launch it there.\n' "$APP_VERSION"
open "dist/SlideExtractor-v$APP_VERSION-macOS-arm64-personal.dmg"
