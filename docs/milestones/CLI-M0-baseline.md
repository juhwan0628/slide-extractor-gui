# M0 baseline — 2026-11-09

- Scope: M0 only; no CLI implementation or product source changes.
- Branch: feature/cli; baseline HEAD/main: a1fdf2d131921aef183629b713cc26654ec2098c.
- Initial changes: two staged design/plan documents from the previous turn.
- Environment: Linux aarch64, Python 3.12.3; local .venv installed from packaging/requirements-linux-aarch64-validation.lock plus pytest 9.2.0.
- Media tools: FFmpeg/FFprobe 6.1.1; qpdf 11.9.0.
- pip check: No broken requirements found.
- Command: QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/python -m pytest -q
- Result: 1012 passed in 134.73s; exit 0. No baseline failures or skips reported.
- Full log and exact pip freeze: .superpowers/sdd/2026-11-09-shared-engine-cli/{baseline-tests.log,environment.txt} (ignored local diagnostics).
- Product paths slide_core/gui/native/packaging have no diff against HEAD.
- This is a Linux source baseline, not verification of installed macOS/Windows packages or new CLI behavior.
- Existing Git author identity is unset; documents remain uncommitted. No identity was invented and no push was performed.
