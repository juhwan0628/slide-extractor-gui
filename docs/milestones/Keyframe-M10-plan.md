# M10 — native half distribution

Authority: corrected M8/M9. Native H.264 half for packet GOP <2 seconds, otherwise all; full edit index/lazy recovery retained. No revisit research or detector retuning.

1. Build helper against exact source-built static LGPL FFmpeg 8.1.2, retain link/source evidence and helper hash. Approved packaging must fail if helper/evidence absent. Personal packaging retains optional CPU fallback.
2. Add independent installed bundled-helper smoke with copyright-free synthetic H.264 fixture; auto half must use bundled helper, full index, skipped-key lazy materialization, JSON v7 and export. Preserve existing MPEG4 CPU fallback smoke.
3. Wire native OS build/evidence collection. Verify source tests and Linux reference helper. Native OS installer runs and public release remain unverified until actual CI artifacts are available; never relabel source tests as installed validation.
4. Fresh review, report exact remaining gates and commit locally. Use an isolated candidate branch to run the native CI required by M10. No merge, main branch push, or public release in this step.

Review focus: missing helper must fail approved build; exact static library provenance and LGPL relink material; no system helper masking bundled path; native smoke cannot silently pass CPU fallback; no claims of native installer execution without evidence.
