#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 slide_core/version.py)
DMG="dist/SlideExtractor-v${VERSION}-macOS-arm64-approved.dmg"
MOUNT=$(mktemp -d "$RUNNER_TEMP/slide-dmg.XXXXXX")
INSTALLED="$RUNNER_TEMP/Slide Extractor installed.app"
cleanup() { hdiutil detach "$MOUNT" -quiet || true; rmdir "$MOUNT" || true; }
trap cleanup EXIT
hdiutil attach "$DMG" -nobrowse -readonly -mountpoint "$MOUNT" -quiet
cp -R "$MOUNT/SlideExtractor.app" "$INSTALLED"
PATH="" QT_QPA_PLATFORM=offscreen "$INSTALLED/Contents/MacOS/SlideExtractor" --smoke-report "$PWD/build/installer-smoke.json"
codesign --verify --deep --strict "$INSTALLED"
