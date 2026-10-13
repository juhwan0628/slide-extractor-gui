# M6 — Native all-IDR integration validation (2026-10-13)

## Implementation
Added a managed C++ all-IDR helper, canonical libavfilter display transformation,
versioned PTS/RGB protocol, bounded Python worker transport and explicit native-idr
keyframe preparation backend. Existing CacheSession owns JPEG publishing, quota,
pinning and cleanup. Shipped GUI/default backend remains cpu-keyframes.

Unsupported native input discards its complete partial generation before restarting
the existing full-keyframe backend. Cancellation, invalid timing, source mutation
and cache errors propagate. Preparation has no total 120-second deadline; inactivity
is tracked separately from consumer/cache time. Demux counters expose real packet
progress across sparse keyframes.

## Real 300-second clip comparison
Oracle Linux ARM64, installed FFmpeg libraries/CLI 6.1.1, one run per backend,
fixed order FFmpeg then native. Other server work, including tests, was running.
These values are provisional; not Mac/Windows or installed-release claims.
All frames retained; alternate-IDR selection is not included.

| Clip | Frames | Pages FFmpeg/native | Prepare FFmpeg/native | Prepare + detect FFmpeg/native |
|---|---:|---:|---:|---:|
| SP | 301 | 30 / 30 | 8.92 / 7.39 s | 11.42 / 10.15 s |
| Multicore | 301 | 28 / 28 | 10.72 / 7.83 s | 11.67 / 9.31 s |
| Ethics | 304 | 9 / 9 | 10.88 / 8.28 s | 12.36 / 9.94 s |

All three clips matched exact decoded PTS/RGB SHA256, JPEG bytes and detector
transition times. Multicore's former experimental 27-page output is corrected to
the current application's 28 pages by using the canonical display transformation.
Detailed single-run records: Keyframe-M6-comparison.json.
The comparison was run before lifecycle progress-record refinements; those changes
do not alter frame decode/filter policy and are separately covered by regression tests.

## Verification
Native build: CMake Release, GCC 13.3, FFmpeg development libraries.
Generated fixtures verify exact RGB/PTS for rotation, non-square SAR, nonzero origin,
B-frames, SDR matrix/range variants and selected video stream.
Non-IDR key packets are rejected as native-unsupported; MPEG4 uses full fallback.
Protocol/lifecycle/cache tests cover incomplete output, count/geometry/PTS failures,
worker failure, partial cleanup, cancellation, inactivity, slow cache consumer and
monotonic demux progress.
Fresh-context read-only review identified false consumer-time inactivity and absent
demux progress; both were reproduced and fixed, and the reviewer verified the fixes.

Final whole suite: **880 passed, 0 failed**, 187.42 seconds.
Targeted native/protocol/cache suite: **33 passed**.

## Remaining work
M7 selection policy and human content review; M8 skipped-frame editing/index and
policy-aware reuse; M9 repeated full-lecture/real-device timings; M10 pinned FFmpeg
8.1.2 linkage, platform artifacts, license/SBOM audits and installed-app release checks.
Dynamic dimensions/color/SAR are rejected by the native worker; exhaustive malformed
AVCC/configuration and dynamic-input fixture coverage remains to expand.
No native binary was shipped, no release changed and no FPS path was reintroduced.
