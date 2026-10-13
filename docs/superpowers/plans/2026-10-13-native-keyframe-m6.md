# M6 Native All-IDR Implementation Plan
> For agentic workers: use superpowers:executing-plans task-by-task.
Goal: validated native all-IDR preparation behind an explicit development backend.
Architecture: managed C++ helper with canonical libavfilter graph, Python protocol/lifecycle adapter, existing CacheSession.
Tech Stack: C++17, FFmpeg libraries, Python, pytest.
Spec: ../specs/2026-10-13-native-keyframe-m6-design.md
## Global Constraints
Keep shipped FFmpeg default; no FPS path; no total preparation timeout; 120-second inactivity; canonical display cache_filter.
## Review Focus
Non-IDR key packets restart completely; decoded PTS is authoritative; truncated output never commits cache; cancel never falls back; actual output geometry/color metadata validated.
## Task 1: Protocol and lifecycle
Files: slide_core/native_keyframes.py, tests/test_native_keyframes.py.
Interface: parse_frames(read_exact, width, height, time_base) yields (pts, rgb); decode_native(source, pipe, cancelled, stall_timeout) yields same.
- [x] Test valid records, invalid headers/lengths/timing, truncation, absent completion, worker exit, cancel and inactivity; observe missing implementation failures.
- [x] Implement bounded queue transport, concurrent stderr drain and always-reaped child.
- [x] Run protocol/lifecycle tests.
## Task 2: Native helper
Files: native/keyframe_decode.cpp, native/CMakeLists.txt, tests/test_native_keyframes_integration.py.
Interface: helper source stream_index cache_filter width height; little-endian versioned records, terminal record, unsupported exit 20.
- [x] Write real media fixture comparison tests, observe helper missing.
- [x] Implement robust AVCC IDR classification and decoded-frame validation; canonical libavfilter transform.
- [x] Build helper and compare exact PTS/RGB with FFmpeg on fixtures.
## Task 3: Preparation integration
Files: slide_core/pts.py, tests/test_native_keyframes.py.
Interface: keyframe_stream(..., backend='cpu-keyframes'); optional native-idr validation backend.
- [x] Test same cache contract and complete fallback after unsupported native generation; cancellation/invalid timing propagate.
- [x] Integrate decoder at existing cache boundary; preserve shipped default.
- [x] Run complete suite and compare three real clips; document remaining acceptance gaps.
- [x] Commit tested changes.
