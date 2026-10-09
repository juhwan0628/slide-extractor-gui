# Source and library replacement

The Slide Extractor code is MIT-licensed. Qt/PySide6/shiboken6 libraries use the LGPLv3 option; FFmpeg/FFprobe use LGPLv2.1 or later. Nothing in the app's terms prohibits reverse engineering needed to debug modifications to LGPL components.

## Exact sources and build information

Source archives, SHA256SUMS, wheel/build records and original license texts accompany the release at https://github.com/juhwan0628/slide-extractor-gui/releases. The full pinned Qt 6.12.0 and Qt for Python 6.12.0 source archives are unchanged upstream sources for the official PySide6 wheel libraries. Installed-wheel metadata and library hashes identify the binaries; no private Qt patches are introduced by this project. OpenCV comes from the SHA256-pinned 5.0.0.93 source distribution with the CMake settings in packaging/opencv-image-only.json. Its original OpenCV and packaging sources are preserved in that archive. FFmpeg comes from the upstream 8.1.2 archive with the exact configure/build script packaging/build-ffmpeg.sh. FFmpeg and Qt source modifications: none. OpenCV packaging/type-generation changes are supplied as the patch described below; build configuration differences are recorded separately.

The build-manifest, SBOM and supplied license copies describe the observed runtime packages. System libraries/frameworks remain OS-provided and are not claimed as our own software. Original copyright notices of vendored numerical/image libraries remain in the wheel/source license materials.

## Windows

1. Close Slide Extractor and back up its installed folder.
2. The installed folder contains `_internal/PySide6/Qt6Core.dll`, Qt6Gui.dll, Qt6Widgets.dll, plugins and binding DLLs. Replace a compatible library/plugin with your modified build. Keep the corresponding Qt/PySide6 ABI and architecture (x64).
3. Run SlideExtractor.exe from that installed folder. No application signature enforcement or application-level hash allowlist prevents replacement.
4. FFmpeg and FFprobe are separate executables under `_internal/tools/`; compatible modified tools can be replaced there.

## macOS Apple Silicon

1. Close the app, copy SlideExtractor.app to a writable location and keep a backup.
2. Qt frameworks and bindings are inside `Contents/Frameworks/PySide6/`. Replace compatible arm64 frameworks/libraries/plugins; the QtCore binary is in `Qt/lib/QtCore.framework/Versions/A/QtCore`.
3. Changes invalidate existing ad-hoc signatures. Locally re-sign your modified copy with `codesign --force --deep --sign - /path/to/SlideExtractor.app` and verify it with `codesign --verify --deep --strict /path/to/SlideExtractor.app`.
4. Run your modified app. macOS may require its normal per-app security confirmation. Do not disable system security globally.
5. FFmpeg/FFprobe are separate executables under `Contents/Frameworks/tools/`; replace compatible arm64 tools there and re-sign the modified app as above.

## Verification scope

Both platforms are tested using an installed copy with a byte-modified QtCore runtime version string. This changes the library hash and qVersion() result; it demonstrates that the app loads a modified compatible library and completes analysis/PDF export. The test is a limited replacement test, not a guarantee of compatibility with arbitrary Qt versions, ABI changes or rebuilt plugins. The modified test library is not distributed to users. macOS tests use local ad-hoc signing, not paid Developer ID signing or notarization; Windows is unsigned.

OpenCV image-only builds apply `opencv-image-only.patch` to skip typing refinements for excluded APIs and omit the unused Windows videoio helper from wheel packaging. The exact original source archive, patch and patch SHA-256 are supplied together. No image-processing C++ code is modified.
