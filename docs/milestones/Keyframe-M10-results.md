# M10 candidate preparation

Local candidate implementation and validation complete; native macOS/Windows CI and installed-device validation pending. No public release signoff.

- Approved bundles now require the native helper and complete pinned-source/relink evidence; helper hash alone is rejected. Personal source kits preserve optional CPU fallback and include all required packaging inputs.
- Helper links exact static SDK archives with inherited pkg-config overrides removed. FFmpeg 8.1.2 archive SHA256 verified, Linux ARM64 source build succeeded. Relink kit includes helper object/source, exact archives and command (70MiB). Linux helper has only OS/runtime shared dependencies; no shared libav*.
- Native build manifest, final inventory and SBOM include helper evidence. Candidate review automatically requires native evidence for builds recording the helper, with an explicit --require-native option. Unsigned input hash and macOS-signed installed hash are checked in their own scopes.
- Installed smoke adds copyright-free H.264 synthetic fixture: six full-index keys, three half observations/JPEGs, native backend required, skipped-key lazy recovery, manual add and paired v7 PDF export. Existing MPEG4 CPU fallback smoke retained.
- Source smoke using pinned media tools and helper passed. This is **not** frozen/installed native OS evidence. Raw reports: Keyframe-M10-source-smoke.json and Keyframe-M10-native-helper-build.json.
- Final complete suite: **1009 passed, 122.81s**, /tmp/m10-release-suite.log. Focused review regressions: 8 passed. Shell syntax and git diff whitespace checks passed.
- Fresh review: no Critical; three Important findings (link isolation, incomplete evidence, missing native review enforcement) reproduced RED and fixed in one pass; no deferred Minor.

Rulings: native installation evidence must come from actual OS CI, so release/device signoff remains open. M10 requires an isolated remote candidate branch and CI usage, which is reversible; main/merge/public release are excluded.

Next: execute source and two native installer jobs on release/keyframe-m10-candidate. Native jobs rebuild pinned FFmpeg/helper, retain relink/source/license evidence and enforce half smoke on bundled, installed and Qt replacement copies. Existing historical review/approval documents continue to identify their old candidates; they do not approve M10.
