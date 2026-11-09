# CLI M3 — sequential batch results (2026-11-09)

## Scope
Existing feature/cli branch and working folder retained. Multiple positional videos execute in order through the unchanged shared engine. --output-dir works for one or many inputs; -o remains single-input only and is mutually exclusive with --output-dir.

## Behavior
- All destinations planned before decoding. PDF and selected JSON sidecars are checked against other outputs and every batch input.
- Duplicate stems, case aliases, Unicode NFC/NFD aliases, resolved symlinks and existing hardlink aliases are rejected regardless of --overwrite.
- Case and Unicode alias rejection is conservative on Linux to protect portable output folders.
- One processing failure does not stop later files. Each result records input/output/status/published and error information when present.
- Cancelled run stops subsequent inputs, marks them skipped, and preserves earlier published output.
- Whole-run JSON contains status/succeeded/failed/skipped/results. Single-file JSON remains compatible with M2.
- Exit 0 all success; 1 partial processing failure; 2 invalid batch options or conflicting output plan; 130 cancellation.
- Core diagnostics stay on stderr; stdout contains one JSON document with --result-json.
- Source options including ROI, mask and JSON format apply uniformly to all files.
- Glob expansion remains the shell's responsibility; no recursive scanning or parallel execution added.

## Implementation decisions
- plan_outputs adds optional json_format so only requested sidecar destinations participate in collision checks.
- Shared outcome serialization moved from cli.py to outcomes.py, preventing circular imports with batch.py.
- One former usage-error test for two positional inputs was changed to two inputs plus -o, because multiple inputs are now valid.
- Existing CancelToken is shared for cooperative batch cancellation; previous committed results remain identified by individual result/publication exception, not token state.

## Evidence
- New batch cases: initial 12 feature failures / 1 passing existing rejection case.
- Batch plus existing CLI targeted tests: 31 passed in 11.82s.
- Fresh review found missing Unicode normalization. Regraded as Important (possible overwritten prior output on normalization-insensitive filesystems). Added test_unicode_normalization_aliases_rejected: RED then GREEN with NFC normalization matching exporter.
- Final full suite: QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/python -m pytest -q
- Result: 1056 passed in 150.92s, exit 0 (1042 previous + 14 new batch cases).
- Real synthetic videos exercised detailed PDF+JSON batch processing with an intervening missing input; later files succeeded and per-file caches were removed.
- Cancellation tests cover no subsequent execution and preservation of already completed publication.
- git diff --check clean; pip check reports no broken requirements.
- Source verification on Linux aarch64, not an installed macOS/Windows distribution qualification.
- Final logs: .superpowers/sdd/2026-11-09-shared-engine-cli/m3-final.log (ignored local diagnostics).

M4 installation/packaging remains pending. No push, main merge or public release performed.
