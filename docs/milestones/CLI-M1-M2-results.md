# CLI M1·M2 results — 2026-11-09

## Scope and source
- Existing folder and feature/cli branch used; no new worktree.
- M1 implemented as required dependency of requested M2.
- M1 commit: 43dce97. M2 commit: c9bdaae.
- Planning/baseline documents committed as 7dd9923 after restoring the repository's existing Juhwan noreply Git identity in local config; global config unchanged.
- No push, main merge, public release, batch mode, or installation packaging performed.

## Delivered behavior
- Qt-free core first-frame helper shared by GUI compatibility import and pipeline.
- GUI parity includes first-frame warning behavior: black-intro warning retains auto ROI analysis.
- Automatic owned pipeline: preflight → probe/ROI → prepare_samples → analyze_project → existing PDF or PDF+JSON exporter → cleanup.
- Default output next to input: <stem>.slides.pdf. Explicit output requires lowercase .pdf.
- python -m slide_cli supports manual/full/auto ROI, one detection exclusion mask, simple/detailed sidecar, overwrite, quiet progress, structured run JSON and version.
- stdout is reserved for final output, stderr for progress/diagnostics.
- Exit 0 success, 1 processing failure, 2 usage/settings failure, 130 pre-publication cancellation.
- Existing outputs/source preserved; post-publication errors disclose saved paths instead of claiming nothing was saved.
- --quiet hides progress, not errors. PDF-only does not change an existing JSON sidecar.
- Native helper absent: existing CPU fallback used. No Qt imports required.

## Verification
- TDD: initial M1 11 failures for missing features → 11 passing; initial M2 13 feature failures → combined 25 passing.
- Four added boundary regressions reproduced warning-mode, published-output attribute, uppercase-extension and decoder cancellation defects; fixes brought combined count to 29.
- Independent review identified generic ValueError being classified as usage. Added test_processing_value_error_is_not_usage_error failed (2 instead of 1), then passed after explicit PipelineSettingsError classification.
- Final complete command: QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/python -m pytest -q
- Final result: 1042 passed in 148.26s; exit 0. This includes baseline 1012 plus 30 new cases.
- pip check: No broken requirements found. git diff --check clean.
- Real synthetic-video tests compare page counts, representative PTS and decoded PDF image bytes with GUI-used core, exercise PDF-only/simple/detailed output, output collisions, cache cleanup and POSIX SIGINT.
- A subprocess blocks PySide6/shiboken6/gui imports and successfully produces a PDF.
- Existing full-suite rotation/SAR/GUI/packaging regressions pass after moving preparation helper.
- Full logs: .superpowers/sdd/2026-11-09-shared-engine-cli/ (ignored local diagnostics).
- Verification environment: Linux aarch64 Python 3.12.3, FFmpeg 6.1.1; this does not qualify native macOS/Windows installer behavior.

## Remaining
M3: sequential batch. M4: pip installation/console entry point, GUI extra, packaging and CI distribution updates.
Use docs/cli.md for the current source-run command.
