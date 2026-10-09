#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ "$(uname -s)" = Darwin ] && [ "$(uname -m)" = arm64 ] || { echo 'Requires Apple Silicon macOS'; exit 1; }
[ -d dist/SlideExtractor.app ] || { echo 'Missing PyInstaller .app'; exit 1; }
SLIDE_PYTHON="${SLIDE_PYTHON:-python3}"
APP_VERSION=$("$SLIDE_PYTHON" slide_core/version.py)
BUILD_MODE="${SLIDE_BUILD_MODE:-approved}"
case "$BUILD_MODE" in personal|approved) ;; *) echo 'Invalid build mode'; exit 1 ;; esac
mkdir -p build dist
DMG_STAGE=$(mktemp -d "$PWD/build/dmg.XXXXXX")
trap 'rm -rf "$DMG_STAGE"' EXIT
cp -R dist/SlideExtractor.app "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"
DMG="$PWD/dist/SlideExtractor-v$APP_VERSION-macOS-arm64-$BUILD_MODE.dmg"
hdiutil create -volname "Slide Extractor $APP_VERSION" -srcfolder "$DMG_STAGE" -format UDZO -ov "$DMG"
shasum -a 256 "$DMG" > "$DMG.sha256"
