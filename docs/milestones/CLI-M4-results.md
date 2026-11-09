# CLI M4 — installation and packaging verification (2026-11-09)

## Delivered
- pyproject.toml defines slide-extractor 0.5.0b2 from the shared runtime version, Python >=3.12, core dependencies and the optional gui extra.
- Console command slide-extractor = slide_cli.cli:main; python -m slide_cli remains supported.
- Wheel explicitly includes slide_core, slide_cli, gui and app.py. No runtime tests, legacy_fps or packaging package is included.
- Qt/shiboken are absent from a fresh default CLI installation. GUI source is available when the optional Qt dependency is installed.
- Existing GUI requirements and platform locks unchanged.
- Source ZIP now contains pyproject.toml, CLI modules and CLI documentation.
- README/docs/cli.md cover local-source/wheel installation, batch commands, GUI extra and external media-tool requirements.
- CLI wheel CI matrix configured for ubuntu-24.04, macos-latest and windows-latest. YAML parsed successfully; remote jobs were not dispatched and are not claimed green.
- Packaging artifacts ignored via *.egg-info/; existing build/dist ignores retained.

## Verification
- Initial missing-package/source-ZIP tests failed before packaging implementation.
- Isolated installer fixture initially inherited PYTHONPATH=. while running pip inside the source tree: source egg-info made pip consider the package already present, so no console script was installed. Verified wheel entry_points.txt was correct, then moved pip's working directory outside the source tree. This fixes the test isolation rather than hiding a missing entry point.
- Targeted installation tests: 5 passed in 13.71s.
- Final complete command: QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/python -m pytest -q
- Result: 1061 passed in 167.74s; exit 0 (1056 prior + 5 installation tests).
- Built wheel: dist/slide_extractor-0.5.0b2-py3-none-any.whl; 113562 bytes; SHA256 1e4fb919c16ca92bc9b93440c9cebfc5b8b78af96c4cd6ce28c4559223476e5c.
- Real isolated wheel installation runs --help/--version and module entry outside the repository; pip check succeeds and PySide6/shiboken6 are absent.
- H264 synthetic video with no native helper uses cpu-keyframes/all. On Linux/POSIX the test exposes only ffmpeg/ffprobe in PATH, proving qpdf is optional; detailed JSON/PDF validates. Missing all media tools reports a processing error instead of publishing output.
- Current developer venv also has the built wheel installed. From /tmp, .venv/bin/slide-extractor --version returns 0.5.0b2.
- Installed GUI app was imported from site-packages and its actual event loop/window opened and closed under offscreen Qt, exit 0.
- Independent M4 review found no important issues. Reviewer documentation minor was addressed in README/docs/cli.md.
- git diff --check and pip check clean.

## Long real-video installed-wheel check
- Same Chapter 9 video previously tested; duration 1543.2s, H264 1280x720.
- Invoked the Qt-free installed wheel command from outside the source folder with PYTHONPATH and SLIDE_NATIVE_KEYFRAME_HELPER removed.
- Fresh application sample cache, no reused analysis/preparation; OS file cache was not flushed.
- cpu-keyframes/all: 20 pages, PDF plus detailed JSON, wall 38.50s (pipeline 38.11s), exit 0.
- GNU time maximum RSS: 95580 KiB (not a combined simultaneous process-tree memory total).
- PDF/JSON pair independently revalidated; sample cache absent after completion.
- Prior native-idr/half single run: 20 pages, wall 22.38s. Different effective sampling/backend means representative PTS differ; this is not an exact image parity or statistically repeated benchmark.
- Outputs/logs remain under ignored profiles/chapter9-installed-cpu-20261109. The existing Drive deliverables were not replaced by this packaging check.

## Scope and next step
Linux aarch64 was directly verified. macOS/Windows CI is configured but remains unrun; native signed installer qualification and native-helper wheel bundling are not implied. The pure Python wheel does not bundle FFmpeg/FFprobe, qpdf or the native helper; it uses the established CPU fallback when the helper is absent.
M0–M4 implementation is complete on feature/cli. Main integration, GitHub push/release and PyPI publication are separate steps.
