# M10 candidate preparation

M10 candidate packaging, native OS installation checks and corresponding-source/license audit are complete. Public release has not been performed. Physical user-device lecture timings remain unmeasured.

- Approved bundles now require the native helper and complete pinned-source/relink evidence; helper hash alone is rejected. Personal source kits preserve optional CPU fallback and include all required packaging inputs.
- Helper links exact static SDK archives with inherited pkg-config overrides removed. FFmpeg 8.1.2 archive SHA256 verified, Linux ARM64 source build succeeded. Relink kit includes helper object/source, exact archives and command (70MiB). Linux helper has only OS/runtime shared dependencies; no shared libav*.
- Native build manifest, final inventory and SBOM include helper evidence. Candidate review automatically requires native evidence for builds recording the helper, with an explicit --require-native option. Unsigned input hash and macOS-signed installed hash are checked in their own scopes.
- Installed smoke adds copyright-free H.264 synthetic fixture: six full-index keys, three half observations/JPEGs, native backend required, skipped-key lazy recovery, manual add and paired v7 PDF export. Existing MPEG4 CPU fallback smoke retained.
- Source smoke using pinned media tools and helper passed. This is **not** frozen/installed native OS evidence. Raw reports: Keyframe-M10-source-smoke.json and Keyframe-M10-native-helper-build.json.
- Final complete suite: **1009 passed, 122.81s**, /tmp/m10-release-suite.log. Focused review regressions: 8 passed. Shell syntax and git diff whitespace checks passed.
- Fresh review: no Critical; three Important findings (link isolation, incomplete evidence, missing native review enforcement) reproduced RED and fixed in one pass; no deferred Minor.

Rulings: native installation evidence must come from actual OS CI, so release/device signoff remains open. M10 requires an isolated remote candidate branch and CI usage, which is reversible; main/merge/public release are excluded.

Both native installer jobs ran successfully on release/keyframe-m10-candidate. Historical review/approval documents continue to identify their old public candidates; the separate M10 review record does not authorize replacing them.


## Final native and audit evidence

- Candidate commit `a7c11ee2381e6cae41fc24f9d4f373eb1cdeeb71` (same tree as local `1ffc979`): [native installer run38451133692](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38451133692), both OS success; [candidate source run38451133836](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38451133836), success.
- Downloaded candidate ZIPs were checked against GitHub artifact SHA256. All six frozen reports (bundled, installed, Qt replacement × two OS) independently passed the native half/lazy/v7 gate. Raw record: `Keyframe-M10-installed-validation.json`.
- Mac system Bash3.2 empty-array build failure was reproduced and fixed. Windows narrow CRT arguments lost Korean paths; UTF16 command-line parsing and UTF8 conversion, with Shell32 linkage, fixed the actual native OS failure. The half smoke now uses a Korean filename on both native platforms.
- M10 separate installed/source audit: [run38457216611](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38457216611), both OS passed at audit commit `e5791656781329af8a94cfade268b07e3b679aee`. Audit ZIPs, reviewed manifests and the installer bytes inside the candidate ZIPs were independently SHA256-bound. Raw record: `Keyframe-M10-audit-validation.json`.
- Mac PyInstaller aliases originally produced two matches for one metadata file. The reviewer now resolves aliases inside the installed root and deduplicates the same target, while rejecting external targets and distinct ambiguous materials. Regression RED→GREEN; focused 11 passed; final local suite **1012 passed, 123.70s** (`/tmp/m10-audit-fixed-suite.log`). [Latest source CI38457216627](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38457216627) also passed all jobs.
- Native-library inventories contain 143 Mac and 137 Windows entries, exactly the previously reviewed inventory document hashes. No extra FFmpeg/GPL shared codecs were added. The new static helper is separately inventoried and tied to the source/object/relink archives.

## FFmpeg version qualification

Six original/heldout clips reproduce the frozen FFmpeg6 half observation PTS and all 24 chronological group intervals on FFmpeg8. Eight representative timestamps differ (some by tens of seconds within the same group). Pair changes remain below the structural grouping thresholds, and every new selection has at least the old representative's supported-mark score when both are evaluated on FFmpeg8. All eight pairs and a detailed multicore pair were visually inspected; no obvious slide or meaningful annotation loss was observed. This is bounded QA, not a general ground-truth recall claim. Report: `Keyframe-M10-version-quality.json`; reproducible private-clip harness: `scripts/verify_keyframe_m10_versions.py`. Lecture images stay local. Historical M8 frozen reports remain unchanged.

The known validation2 SP Notes omission from odd keyframes remains; it was not automatically recovered and half has not been forced to all. Revisit identification remains deferred. M9 timings were measured on the server's FFmpeg6 baseline; they do not establish FFmpeg8 or physical Mac/Windows performance.

## Remaining delivery scope

Current CI installers retain version 0.5.0b1 as isolated candidates. A new public beta requires its own version/tag and final publication steps; the existing release is not replaced. User-device full-lecture timing is also pending. No user inspection was requested to complete these automated candidate checks.

Execution rulings, with costs: actual native OS CI supplies installation evidence (physical user-device performance remains outside that evidence); the isolated candidate branch was used for required CI (remote branch and Actions usage); core half policy, detector thresholds and revisit scope remain unchanged. No deferred Minor findings.

<details>
<summary>Execution ledger</summary>

# SDD ledger — plan: docs/milestones/Keyframe-M10-plan.md
BASE 3eb4653; isolated feature/keyframe-0.5 clean.
Pre-flight: static FFmpeg build produces libraries consumed by helper build; helper/evidence consumed by spec and manifest; installed half smoke consumes bundled helper. Existing historical CPU smoke remains independently valid.
Task 1: complete — missing module/package RED→GREEN; exact SHA256-pinned FFmpeg 8.1.2 static source build succeeded; helper only OS shared dependencies (ldd), no shared libav*; relink kit 70MiB. Remote lacks bare python; reran helper script with validation venv PATH. CI setup-python provides python.
Task 2: complete — native release gate missing require_native RED→GREEN; source smoke using pinned media tools+helper passed, six keys/three JPEGs, lazy add and v7 export; existing MPEG4 CPU smoke passed independently. Not a frozen installer run.
Final review: three Important findings; all accepted. Native linkage ambiguous flags, incomplete hash-only evidence, and missing native review gate each reproduced RED then fixed in one ongoing pass; focused tests 8 passed. Final suite pending.
Ruling: native installers require GitHub native runner execution; local source tests and Linux linked-helper smoke are not installation evidence — cost: M10 release/device signoff remains open until actual CI and installed validation.
Ruling: M10 authorization includes a new isolated candidate branch solely for native CI — native OS execution is necessary to make packaging concrete, and this is reversible; main/merge/public release remain excluded — cost: remote candidate branch and GitHub Actions build usage.
Final: fixed all three Important findings — explicit archive linkage, complete evidence/file hashes, native review enforcement — regression RED→GREEN; final suite 1009/1009 (122.81s).
Local verification complete; native CI outstanding. No deferred minor.
Remote candidate: release/keyframe-m10-candidate. Initial snapshot ba3a1adfbe73b8316ac4dd4c326fa9a2b0369553 matched local a38cec9 tree aa39d92b2003d6b724489f4577d7b1c6dce118f8 exactly. CI label update f0afa8c606794a5c0038743bca810fb021c0cbc2 matched local 5405e7b tree 859203364f64dd149588ec86fa2f532e02434217 exactly. Original local feature history preserved; GitHub snapshot created through connector because host has no gh/authenticated push.
CI current source run38445294973; native run38445294984, jobs115461964102 (Mac),115461964551 (Windows). Initial branch creation delayed push runs38445144850 source and38445144882 native also exist; no cancel capability available, same source except CI name. Public release untouched.
Native Mac CI run38445294984 failed on Bash3.2 empty LINK_EXTRA array under nounset after FFmpeg built successfully. Reproduced with GNU Bash3.2 built in /tmp (test_helper_recipe_accepts_empty_platform_link_flags RED), fixed guarded expansion, GREEN. Added real Unicode-input fixture smoke (RED Latin filename → GREEN Unicode filename); native OS CI must prove this too.
Bash+Unicode fixture fix localcedbd14 / remote317ce060688edce01038790f86fa841dc08eeb27 trees962e83597e989eaffdfd65a693cf7110351782d8 identical. New native run38446908348 jobs115467567103Mac success,115467567693Windows active; source38446908599 all jobs success. Mac candidate artifact11838578536 ZIPSHAff6a754a755bd770a3704a296c6d84670fcf7fad71d4890c0d7bc6013446ab97 downloaded/verified; all 3 frozen installed smokes native-half/v7/lazy passed. Candidate public-release gate remains not-approved pending corresponding source/license review. Mac inputs artifact11839376732, installer11838713276. Local full suite1011passed124.42s.
Windows actual Unicode fixture RED: run38446908348 job115467567693 1failed218passed4skipped, Native decoder failed open source. Root cause narrow CRT argv loses Unicode; parse GetCommandLineW/CommandLineToArgvW and UTF-8-convert all args, add Shell32 linkage. Linux focused25passed7.11s and full1011passed123.46s; Windows GREEN still pending new CI.
Pinned FFmpeg8 quality exact-timestamp check RED: original SP pages remain3 but representatives90/286/298 versus frozen FFmpeg6 92/284/296. This is not proof of missing content; investigate before quality parity claim. Historical M8 JSON restored unchanged.
Native CI final run38451133692 and source38451133836 succeeded at remotea7c11ee2381e6cae41fc24f9d4f373eb1cdeeb71, same tree as local1ffc979. Both candidate ZIP digests verified; bundled/installer/Qt-replacement frozen smokes independently validated for native half/lazy/v7. Source regression suite1011passed123.46s after Bash3/UTF16 fixes; ledger's earlier pending CI entries superseded.
FFmpeg6/8 qualification: 6 cases, identical observation PTS and all24 group intervals; 8 selected timestamps differ. Spatial pair tests below structural thresholds, v8 selected supported-mark scores >= old candidate on v8. All8 pairs visually inspected, including detailed validation2 MC; no obvious lost slide/annotation content. This is bounded QA, not universal accuracy proof. Historical M8 frozen references untouched.
Final native-library inventories143Mac/137Win have exact previously reviewed inventory document hashes, no extra FFmpeg/GPL libraries; native helper bytes are independently recorded. M10 companion audit now explicitly uses M10 candidate identity and --require-native, preserving historical approval/config records.
M10 companion audit run38456338914: Windows passed, Mac failed solely because PyInstaller data aliases counted as two native-helper-build.json files. Installed original bytes were untouched. Reproduced internal-file-alias RED; canonicalize only paths resolving inside installed root, deduplicate same target and retain ambiguity/external-target rejection. Focused11passed0.98s; whole suite1012passed123.70s.
M10 companion audit final38457216611: both OS PASSED at e579165. Downloaded audit artifacts11842907528Mac/11842352696Win, verified archive/manifest/actual-installer SHA256 and native helper/source/relink bindings. Latest source38457216627 all jobs success. Independent raw records retained in Keyframe-M10-audit-validation.json.
M10 candidate packaging+installation+source audit complete; public release/version/tag and physical user-device timing remain separate. Final report includes all rulings and no deferred minor. Plan-owned ledger archived below before cleanup.

</details>
