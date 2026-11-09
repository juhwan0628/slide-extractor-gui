# D2 CLI-only distribution verification — 2026-11-09

## Delivered
- Shared synthetic video helper extracted to tests/cli_fixtures.py; old keyframe-test callers retain a re-export.
- GUI first-frame compatibility check moved to tests/test_gui_source_preparation.py, retained in original full suite only.
- CLI source/pipeline/batch tests exported independently of GUI tests and original packaging layout.
- CLI-only wheel installation tests maintained as a committed release template, not copied from the GUI-oriented wheel tests.
- Exporter v2 emits independent tests, pinned test constraints, CLI-only usage documentation, three-OS CI and an integrity verifier.
- verify_snapshot.py checks every declared file hash, rejects missing/tampered/unexpected files and symlinks; known generated build/test directories and .git metadata are excluded from inventory comparison.
- Existing core and CLI runtime unchanged (git diff 2e51f63..HEAD -- slide_core slide_cli is empty).

## Verified snapshot
- Source commit: 873f2faddb95cac5ef2fd3ac6bb5ee4c14ab743f.
- Snapshot: dist/cli-d2-873f2fad (50 files).
- No GUI/app source, Qt dependency, original repository path dependency or native helper required.
- Real snapshot installed into a dedicated venv; PYTHONPATH and SLIDE_NATIVE_KEYFRAME_HELPER removed.
- Confirmed gui/app/PySide6/shiboken6 absent.
- Final snapshot test suite: 46 passed in 35.92s; exit 0.
- Includes single/batch processing, advanced JSON/PDF validation, failure continuation, cancellation, output collision protection and fresh wheel installation outside snapshot source.
- Standalone verifier passes before installation and after tests. Installed wheel excludes gui/app/tests/legacy packages.
- pip check clean in the initial isolated run (same pinned dependencies reused for final snapshot reinstall).

## Original repository verification
- Related source tests: 48 passed in 23.68s.
- Export verifier tests: 7 passed; includes missing/extra/symlink damage rejection.
- Full original suite after fixture/GUI split: 1068 passed in 169.55s; exit 0.
- Subsequent CI UTF-8/docs/whitespace/version-assertion changes did not change runtime code; targeted version/export tests passed (8), and final exported suite reran (46).
- git diff --check clean after removing extra trailing blank lines.

## Review and scope
- Independent review flagged missing Windows UTF-8 mode for Korean filenames; release CI job now sets PYTHONUTF8=1, inherited by pytest and subprocesses. CLI-only docs specify the same mode for Windows redirected JSON.
- Removed a hardcoded version assertion in exported tests; expected version now comes from shared VERSION.
- Release CI YAML parsed locally: Linux/macOS/Windows matrix present, UTF-8 enabled.
- Only Linux aarch64 actually executed here. Remote OS CI awaits D3; no claim that macOS/Windows are already green.
- D1 partial export limitation is mitigated by mandatory verifier checks before install/build/CI: incomplete output is rejected.
- No remote changes, main integration, tag or release creation performed.
- Next: D3 source integration, legacy preservation tag and history-preserving CLI transition PR.
