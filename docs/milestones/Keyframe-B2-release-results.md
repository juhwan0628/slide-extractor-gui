# 0.5.0b2 public release results

Published 2026-10-14 KST as an official public beta (prerelease), following explicit user authorization and reported Mac verification.

- Public release: https://github.com/juhwan0628/slide-extractor-gui/releases/tag/v0.5.0b2
- Release ID: 412354938; tag commit: 81f3a836264052833dd9c5e11ec5696dce9f2792.
- Candidate commit: 2b803a2689d2c6e29a632551576a0fb20c76b450; native run38460514435 and source CI38460514398 successful.
- Separate installed/source/relink audit38514499414 at e3626aea027b40dafa81804cdedaeaf1511a8b19: both OS PASSED.
- Publication38514770597: successful. Four public assets downloaded again; actual bytes match GitHub digests and approved installer hashes. The support archive retains both OS helper object/static-library relink kits and final audit reports.
- Full b2 source suite: 1012 passed127.06s. Final metadata CI38514770564 successful.
- main advanced without force under lease to release source, followed by automatic download-badge update414eb818. Application/build tree verified identical. Old b1 approval history preserved; b2 has separate approval records.

Half policy and frozen detector behavior remain as qualified: native H264 packet inspection with GOP<2s uses half before RGB/JPEG; otherwise all. Full keyframe edit index and exact-PTS lazy restoration remain. No FPS fallback added. User Mac confirmation is not a physical-device timing benchmark; the 57–59% M9 speedup was measured on the FFmpeg6 Oracle server, not this FFmpeg8 package.

Fresh final release review: no Critical/Important findings. Deferred minor: SOURCE_AND_REPLACEMENT.md still calls the helper an M10 candidate/future companion artifact. Actual released materials are present: Sources-Licenses.zip → build-and-review-evidence.zip → {macOS-ARM64,Windows-X64}/inputs/helper-relink/. This wording does not remove the kit or affect application behavior.

## Execution record

# SDD ledger — plan: docs/milestones/Keyframe-B2-release-plan.md
Task 1: complete — version b2, full suite1012 passed127.06s; main history integrated preserving M10 application tree and latest stats.
Task 2: native builds/source CI complete — commit2b803a, run38460514435/38460514398; independent candidate zip digest/native smokes passed both OS. b2 audits38514499414 pending.
Authorization: user confirmed Mac and explicitly requested official publication 2026-10-14 KST; beta version retained.
Ruling: keep b1 approval history unchanged and create separate b2 records — binds new installers only — incorrect record isolation could confuse historical evidence.
Ruling: metadata-only publication edits use exact-source identity and live pipeline verification, no application reimplementation — code already qualified and unchanged — changed application input would require a new build.
Probe: validate_smoke raises ValueError on invalid reports, bare invocation enforces gate; no missing assertion bug.
Task 2: complete — both installed/source audits38514499414 PASSED; artifact zip digests, installer sha and reviewed-manifest sha verified independently.
Final review: fresh b2_publish_review no blocking findings so far; publication records ready.
Final: minor (deferred): SOURCE_AND_REPLACEMENT.md M10 candidate wording; nested relink kit is retained by release archive.
Task 3: source workflow Python blocks compile, six real native reports pass and corrupted native flag rejected; publication ready pending final reviewer.
Final review: b2_publish_review completed — no Critical/Important findings; one deferred documentation minor. Exact final approvals equal actual reports; native candidate/source/audit successful. Publication run38514770597 at81f3a836 in progress.
Task 3: complete — publish run38514770597 SUCCESS; public release412354938 draft=false/prerelease=true at81f3a836. All four public assets downloaded and byte SHA256 verified; helper object/static-library kits and final PASSED audits retained.
Task 4: complete — main fast-forwarded to81f3a836 under lease, then automatic badge update414eb818; application tree identical. Historical b1 approval records unchanged.
