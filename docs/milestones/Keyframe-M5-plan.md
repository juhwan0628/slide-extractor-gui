# Keyframe M5 Native Candidate Plan
> **For agentic workers:** Use superpowers:executing-plans inline; one fresh whole-milestone reviewer at the end.
**Goal:** Prepare 0.5.0b1 from the keyframe-only source and validate the Mac ARM64 / Windows x64 installer bytes.
**Architecture:** Reuse pinned native inputs and the existing installer/audit pipelines. Candidate builds run on a dedicated release branch; main and public releases remain unchanged. Shared gates reject absent keyframe/v4/simple JSON/editor/cache evidence and forbidden legacy modules.
**Tech Stack:** Python3.12, PySide6, FFmpeg, image-only OpenCV, PyInstaller, GitHub Actions, DMG/Inno Setup.
**Spec:** docs/milestones/Keyframe-0.5-design.md
## Global constraints
- No FPS fallback/control/legacy runtime; no new algorithm or PDF redesign.
- Mac ad-hoc, not notarized; Windows unsigned. Physical security policies remain manual verification.
- Existing 0.4 approvals are historical and cannot approve this candidate.
- No public release, tag or main merge during this milestone; candidate branch/build artifacts only.
- Private lecture files and expensive M4 outputs stay outside Git.
## Tasks
- [x] 1. Candidate contract: tests reject missing/false keyframe, v4/simple JSON, edit/background/cache, frozen/version evidence and forbidden Analysis modules; RED then minimal shared verifier and spec guard. Set VERSION=0.5.0b1/BUNDLE_VERSION=0.5.0; revoke candidate approval flags; retain old release history in Git. Focused packaging tests GREEN, commit.
- [x] 2. Native gates: smoke verifies current config/module/sample contract; workflow and installed-byte audit use shared verifier. Native tests include GOP limit and installed-smoke tests. Dedicated release/keyframe-0.5-m5 branch push triggers source/native CI without main/publication. RED/GREEN where behavior changes; complete local suite.
- [x] 3. Candidate build and audit: transfer exact tracked source via connector Git objects if remote git auth unavailable; tree equality check. Run native builds/source tests, diagnose failures with reproductions, inspect exact native inventories; bind candidate/source run hashes then run separate installed-byte audit. Never substitute old approvals.
- [x] 4. Document actual candidate evidence/downloads/limitations, final fresh review, important fixes RED/GREEN/full suite; retain feature branch. M5 can only be marked fully verified when both native installers and audits pass. Missing remote capabilities become explicit pending checks, not inferred successes.
## Interfaces
1 -> 2: packaging/keyframe_release_contract.py provides validate_smoke(report, version, require_frozen=True), verify_modules(module_names).
2 -> 3: same source commit identity, keyframe smoke flags, native inventory hashes.
3 -> 4: exact installer hashes and source/native/audit results determine documented status.
## Review focus
Missing smoke flag accepted; hidden legacy module in bundle; old approval reused; mismatched source/installer run; claimed physical native verification without evidence.

Closure: same-candidate native/source checks and exact installed-byte audit pass; final independent review found no remaining Critical/Important. Completed Task4 status housekeeping; public approval remains false. Physical-device checks and public publication are subsequent actions. See Keyframe-M5-results.md.
