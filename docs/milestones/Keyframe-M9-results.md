# M9 repeated performance results

Server benchmark complete: 3 full lectures × 3 modes × 3 repetitions, 27 successful serial fresh-worker runs. Product code and default policy unchanged. Installed Mac/Windows performance signoff remains pending M10.

Oracle Linux ARM64; new application cache per run, uncontrolled OS page cache. Median wall seconds include probe, preparation and cached analysis; exclude interpreter/import, cleanup and GUI/export. Native all is an experimental comparison only. RSS values are separate lifetime process maxima, not a combined concurrent peak.

| Lecture | CPU/all total | Native/all total | Default half total | CPU/all time reduction | Half prepare | Half analysis | JPEGs all → half | JPEG MiB all → half |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SP01-S01-15 | 37.87 | 30.17 | 15.75 | 58.4% | 10.85 | 4.88 | 2020 → 1010 | 83.6 → 41.7 |
| Issue (Memory) | 98.04 | 78.07 | 40.57 | 58.6% | 29.77 | 10.80 | 4121 → 2061 | 237.6 → 118.8 |
| 제1장 | 65.98 | 54.20 | 28.50 | 56.8% | 20.51 | 7.73 | 3021 → 1511 | 150.4 → 75.2 |

## Variation and memory

| Lecture/mode | Total min–max seconds | Python RSS MiB median | Child RSS MiB median |
|---|---:|---:|---:|
| Issue (Memory)/auto | 39.95–44.38 | 68.5 | 58.4 |
| Issue (Memory)/cpu-all | 94.07–102.93 | 68.2 | 87.2 |
| Issue (Memory)/native-all | 77.64–90.13 | 70.9 | 58.4 |
| SP01-S01-15/auto | 15.61–15.77 | 64.3 | 57.7 |
| SP01-S01-15/cpu-all | 37.03–37.93 | 62.5 | 86.8 |
| SP01-S01-15/native-all | 30.12–30.37 | 63.3 | 57.8 |
| 제1장/auto | 28.19–34.41 | 66.0 | 58.3 |
| 제1장/cpu-all | 65.20–66.56 | 64.0 | 89.4 |
| 제1장/native-all | 53.96–54.37 | 65.5 | 58.4 |

## Interpretation and quality limits

Packet inspection median overhead was 0.371s (SP), 0.615s (multicore), and 0.508s (ethics). This is included in the preparation totals.

Half reduces both preparation and analysis work; packet preflight is included in preparation, so improvement does not hide its overhead. Full keyframe edit indexes retain 2020/4121/3021 keys respectively, despite initial JPEG counts being halved. Within each lecture/mode all three runs produced identical representative timestamps, backend, policy and page counts. CPU/all and native/all representative timestamps must be compared separately from half.

SP full lecture gives 44 chronological page occurrences with all and 39 with half; multicore 11/11 and ethics 59/59. Counts are not ground-truth recall or proof of equal content quality. Historical SP validation2 Notes-only odd keyframes at 152.4667/210.4/297.0s remain a known half input omission; full editing index permits manual recovery but automatic recovery is not implemented. Do not force all as a remedy without user agreement. Revisit identification remains deferred.

Three repetitions on one host establish reproducibility, not a broad hardware confidence interval. No physical Mac/Windows installed measurements, GUI click latency, cold filesystem cache, lazy-edit latency, PDF/export, or aggregate child+parent concurrent memory claims are made.

## Verification and execution record

Aggregation test: 1 passed; initial missing-module RED observed, implementation GREEN. Benchmark raw records and per-phase profiles: Keyframe-M9-performance.json. Product core unchanged; prior M8 suite is historical evidence, not rerun for this benchmark-only change.

Fresh independent review found no Critical/Important issues and independently recalculated all aggregates. Four deferred harness improvements: persist failed-determinism raw rows, explicit overwrite guard, raw harness/native dependency identity, and full-index PTS signature (currently count and selected representative timestamps only). These do not invalidate the successful server measurements. The commit containing this report and script identifies the executed harness; raw git_head identifies the unchanged product base 01e77b6.

Execution ruling: installed Mac/Windows measurements await M10 artifacts because those builds/devices are unavailable in this session; this means M9 server validation is complete, while device release performance signoff is pending.
