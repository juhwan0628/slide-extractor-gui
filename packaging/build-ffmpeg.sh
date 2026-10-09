#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# The archive must already have passed native_inputs.py's pinned SHA256 check.
SOURCE_ARCHIVE="$PWD/build/native-sources/ffmpeg-8.1.2.tar.xz"
[ -f "$SOURCE_ARCHIVE" ] || { echo 'Missing verified source archive'; exit 1; }
BUILD_DIR="$PWD/build/ffmpeg-source"
OUTPUT_DIR="$PWD/vendor/approved"
mkdir -p "$BUILD_DIR" "$OUTPUT_DIR"
tar -xf "$SOURCE_ARCHIVE" -C "$BUILD_DIR" --strip-components=1
cd "$BUILD_DIR"
FLAGS=(--disable-autodetect --disable-gpl --disable-nonfree --disable-version3 --disable-shared --enable-static --disable-doc --disable-debug --disable-ffplay)
case "$(uname -s)" in
  MINGW*|MSYS*) FLAGS+=(--target-os=mingw32 --arch=x86_64 --cc=gcc --extra-ldflags=-static); EXT=.exe ;;
  Darwin) FLAGS+=(--arch=arm64 --cc=clang); EXT= ;;
  Linux) EXT= ;; # Source-build validation only; no Linux desktop release.
  *) echo 'Unsupported build host'; exit 1 ;;
esac
./configure "${FLAGS[@]}"
make -j "${SLIDE_BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN)}" ffmpeg$EXT ffprobe$EXT
cp "ffmpeg$EXT" "ffprobe$EXT" "$OUTPUT_DIR/"
cp config.h config.log ffbuild/config.mak "$OUTPUT_DIR/"
