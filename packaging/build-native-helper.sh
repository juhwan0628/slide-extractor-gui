#!/usr/bin/env bash
# Run after build-ffmpeg.sh: no system libav* linkage accepted.
set -euo pipefail
cd "$(dirname "$0")/.."
SDK="$PWD/build/ffmpeg-sdk"
OUTPUT="$PWD/vendor/approved"
RELINK="$OUTPUT/helper-relink"
mkdir -p "$RELINK"
case "$(uname -s)" in
 MINGW*|MSYS*) CXX=g++; EXT=.exe; LINK_EXTRA=(-static -lshell32) ;;
 Darwin) CXX=clang++; EXT=; LINK_EXTRA=() ;;
 Linux) CXX=c++; EXT=; LINK_EXTRA=() ;;
 *) echo 'Unsupported helper host'; exit 1 ;;
esac
unset PKG_CONFIG_PATH PKG_CONFIG_SYSROOT_DIR
export PKG_CONFIG_LIBDIR="$SDK/lib/pkgconfig"
FLAGS=$(pkg-config --static --cflags libavformat libavcodec libavfilter libavutil)
LIBS=$(pkg-config --static --libs libavformat libavcodec libavfilter libavutil)
# FFmpeg supplies trusted pkg-config flags; deliberate shell word splitting.
$CXX -std=c++17 -O2 $FLAGS -c native/keyframe_decode.cpp -o "$RELINK/keyframe_decode.o"
read -r -a LINK_ARGS <<< "$LIBS"
for i in "${!LINK_ARGS[@]}"; do
 case "${LINK_ARGS[$i]}" in
  -lavformat|-lavcodec|-lavfilter|-lavutil|-lavdevice|-lswscale|-lswresample|-lpostproc)
   library="${LINK_ARGS[$i]#-l}"
   [ -f "$SDK/lib/lib$library.a" ] || { echo "Missing exact static archive: $library"; exit 1; }
   LINK_ARGS[$i]="$SDK/lib/lib$library.a" ;;
 esac
done
$CXX "$RELINK/keyframe_decode.o" "${LINK_ARGS[@]}" ${LINK_EXTRA[@]+"${LINK_EXTRA[@]}"} -o "$OUTPUT/slide-keyframe-decode$EXT"
printf '%q ' "$CXX" keyframe_decode.o "${LINK_ARGS[@]}" ${LINK_EXTRA[@]+"${LINK_EXTRA[@]}"} -o "slide-keyframe-decode$EXT" > "$RELINK/link-command.txt"
printf '\n' >> "$RELINK/link-command.txt"
cp native/keyframe_decode.cpp "$RELINK/"
cp -R "$SDK/lib" "$RELINK/ffmpeg-libraries"
python packaging/record_native_helper.py "$OUTPUT" "$SDK"
