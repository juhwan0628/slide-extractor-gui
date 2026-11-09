# D1 CLI export results — 2026-11-09

- Implemented scripts/export_cli_release.py and committed CLI-only README/pyproject templates.
- Source: full immutable Git SHA, clean working tree required; contents read from Git blobs, never copied from working files.
- Export includes shared core and CLI Python modules, LICENSE, THIRD_PARTY_NOTICES and CLI usage docs.
- GUI/app/legacy/private data are outside the allowlist. Core/CLI source blobs are unchanged.
- VERSION is parsed from the committed source with AST, not imported/executed.
- source-manifest.json records source repository/commit, package version, exporter version and SHA256 for every output except the self-referential manifest; source code hashes also recorded separately.
- Existing output paths are refused; selected symlink/nonregular Git entries rejected.
- Unit tests: 3 passed. Final full source suite: 1064 passed in 163.97s, exit 0.
- Real source 961e767ebafcef96414a68b82fb90ca27478e4fe exported twice to dist/cli-snapshot-961e767e-{a,b}; 41 files each, all bytes identical and all manifest hashes verified.
- Independent review found no blocking issue. Minor deferred: forceful interruption during final per-file publication may leave an incomplete destination; existing-output refusal prevents reuse/overwrite. D2 snapshot validation must reject incomplete exports.
- D1 prepares reproducible source snapshots, not a published release.
- Ruling: CLI-only testing/CI templates and migration changelog remain D2/D3 work; current usage documentation will be tailored to the CLI-only repository during D2. No independent repository/worktree created.
- Remote repositories, branches, tags and releases unchanged.

Next: D2 separates GUI-dependent tests and proves installation and CI using only the exported CLI snapshot.
