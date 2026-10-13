# M9 — repeated performance validation

Authority: corrected M8 half default. Auto packet policy uses half strictly below 2-second GOP; all is a comparison only. No detector threshold, revisit identification, or release changes.

1. Add a reproducible serial benchmark: fresh Python process and empty application cache per run; CPU/all, native/all, auto in rotated order, three repetitions on three full lectures. Same full ROI spatial detector. Record preparation, cached analysis, total wall, self/child CPU, separately labeled RSS maxima, JPEG bytes/count, full index, policy/backend and representative timestamps. Retain every raw run and aggregate median/min/max; assert deterministic output within each input/mode.
2. Execute on available Oracle ARM64 host. OS filesystem cache is uncontrolled/warm; no claim of cold device startup. Capture environment and source hashes. Mac/Windows installed application timings require M10 artifacts; remote numbers do not substitute for them.
3. Review benchmark and interpretation; persist results and commit without merging/pushing. Record known half observation omissions separately from performance.

Review focus: fresh-process isolation, measurement scope, fallback detection, median arithmetic, no page-count-as-recall inference, no hidden all policy or historical report overwrite.
