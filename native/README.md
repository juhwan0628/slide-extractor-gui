# Native keyframe worker (M6 development backend)

The shipped GUI still uses the existing FFmpeg keyframe path.
This executable is for explicit all-IDR validation; alternate-IDR selection is M7.

## Build
Requires CMake, pkg-config, a C++17 compiler and matching FFmpeg development libraries:
libavformat, libavcodec, libavfilter, libavutil.

```sh
cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native -j2
```

Linux validation currently uses Ubuntu FFmpeg 6.1.1. This is not the pinned
8.1.2 native runtime supplied in release packages. Mac/Windows builds, the pinned
library configuration, licensing/SBOM and installed-app checks remain M9/M10 work.

## Explicit use
Set SLIDE_NATIVE_KEYFRAME_HELPER to the built executable's absolute path.
Call slide_core.pts.keyframe_stream(..., backend='native-idr').
Default callers remain backend='cpu-keyframes'. Missing helper or unsupported
input restarts the complete existing keyframe path after discarding partial cache.
Cancellation, source mutation, invalid timing and cache errors do not fall back.

## Protocol
All integers are little endian. Magic/version: SEKF0001.
Type 1: decoded PTS int64, source ordinal uint64, time base numerator/denominator
int32, output width/height/payload length uint32, packed RGB24 bytes.
Type 2: completed frame count uint64; must be nonzero and match received frames;
successful process exit and EOF are mandatory.
Type 3: strictly increasing demux packet count uint64, emitted only after genuine
packet progress. It provides liveness across sparse keyframes.
Unknown records, missing completion, dimension changes and incomplete payloads
cannot publish a completed generation.

## Validation
Run QT_QPA_PLATFORM=offscreen python -m pytest -q.
Real helper tests build automatically when native build dependencies exist;
they skip when those dependencies are absent. Run them in a native-equipped
environment for M6 acceptance.
scripts/compare_native_keyframes.py compares exact PTS/RGB, JPEG and detector
transitions against the existing FFmpeg path and records provisional single-run timings.
Use PYTHONPATH pointing at the repository when invoking the script directly.

## Resource ownership
The worker handles demux/decode/filter only. Python preserves CacheSession
quotas, pins, JPEG policy and generation completion. Samples stay original-PTS
keyframe observations. Each preparation uses a fresh UUID-owned cache; no
persistent cross-backend cache lookup has been introduced.

## M7 selection
The helper accepts an optional final stride argument (1 or 2).
Python uses selection_policy='all' or 'half'; half selects source keyframe ordinals
0,2,4,... before decoding. Protocol validation expects the same source ordinal stride.
prepare_samples records actual selection_policy and decoder_backend; unsupported
native half inputs restart complete all preparation and report the effective policy.
Later in-band SPS/PPS or SEI conservatively disables the half fast path. Skipped
packets cannot silently hide configuration changes. Half is not a GUI default;
project/JSON policy identity and skipped-frame editing remain M8.
