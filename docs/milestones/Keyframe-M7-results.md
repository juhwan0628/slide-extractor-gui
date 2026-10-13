# M7 — Decode-before-selection implementation (2026-10-13)

Status: implementation ready; multicore reviewed; ethics has two required-content omissions awaiting page identification and diagnosis.
Native development backend only. Shipped GUI default remains all keyframes.

## Policy
all: every key packet; half: keyframe source ordinals 0,2,4,...
Selection occurs before avcodec_send_packet, RGB conversion and JPEG creation.
Every key packet is checked for IDR even when skipped.
Source ordinals are checked in the worker protocol; Sample.ordinal remains dense
observation order. Original PTS/time_base remains authoritative.

Python keyframe_stream and prepare_samples accept explicit selection_policy.
Half requires the native backend; unsupported input discards partial cache then
restarts the complete existing all-keyframe path. Profiles retain requested and
effective policy; immutable PreparedSamples records effective policy/backend.
No DetectorConfig sensitivity or debounce setting was changed.

## Safety boundary
Half conservatively falls back when subsequent video packets contain in-band
SPS/PPS or SEI. This prevents changes only on skipped keys from evading validation.
It also sends benign repeated parameter sets/SEI to full decoding; optimizing
that support requires inspecting the metadata, not silently ignoring it.
Native all retains the existing support boundary and decoded metadata checks.
Cancellation, source changes, timing failures and cache errors are not fallback reasons.

## 300-second clip measurements
Oracle ARM64; one native-all run followed by one native-half run per clip;
other server jobs/testing ran concurrently. Provisional, not installed-app claims.

| Clip | Frames all/half | Pages all/half | Prepare + detect all/half | Reduction vs native all |
|---|---:|---:|---:|---:|
| SP | 301 / 151 | 30 / 24 | 9.16 / 5.17 s | 43.6% |
| Multicore | 301 / 151 | 28 / 21 | 10.02 / 4.64 s | 53.7% |
| Ethics | 304 / 152 | 9 / 4 | 10.68 / 5.16 s | 51.7% |

Selected PTS and JPEG bytes are exact all-path [::2] subsets for all three clips.
Generated fixture tests also compare raw RGB and odd/even keyframe counts.
The earlier SP human review found six candidates duplicate; page agreement is
not ground-truth recall. Multicore and ethics page reductions are unclassified.

## Review evidence
Local lecture images are research-only and were not added to git or published.
Under experiments/selective-keyframe/results/m7-review:
- multicore-all.jpg, multicore-half.jpg, multicore-full-only.jpg, multicore-review.json
- ethics-all.jpg, ethics-half.jpg, ethics-full-only.jpg, ethics-review.json
Full-only candidates use greedy one-to-one transition agreement within two seconds.
These are candidates for owner review, not proven missing slides.
Multicore full-only pages: 6,7,13,17,23,25,28.
Ethics full-only pages: 2,3,4,5,6.

## Review and validation
Fresh-context review identified metadata changes on skipped keys; a repeated-SPS
regression reproduced acceptance before the guard and rejection afterward.
A real 800x450 -> 640x360 -> 800x450 stream verifies skipped-key dimension changes
are not silently accepted. Odd-count fixture was corrected to use 1.25 seconds.
The fixture's duration spelling was corrected from .5 to 0.5 after FFmpeg rejected it.

Final whole suite: **890 passed, 0 failed**, 193.04 seconds.
CMake Release build and git diff --check succeeded.

## M8 handoff
PreparedSamples has policy provenance. Project/JSON policy serialization,
policy-aware project/cache reuse, complete keyframe index and on-demand images
for skipped-frame editing remain M8. Do not activate half as GUI/default policy
before that integration and human content review.
Mac/Windows installed-app timings and pinned release builds remain M9/M10.

## Owner review update (2026-10-13 17:42 KST)
The owner reports all seven multicore full-only candidates are duplicates.
The ethics half result removes two nonduplicate required pages among the five candidates. Exact page numbers have not yet been supplied. Do not declare half selection content-equivalent or make it the default. Distinguish unavailable sampled content from detector rejection or representative selection. The remaining ethics candidate classifications have not been explicitly supplied.

## Clarification and detector trace (17:48 KST)
Owner identifies pages 2/3/4/5 as one slide with changing states and page 6 as a
second distinct slide: two distinct required slide contents are omitted.
Half still observes 51.4s and 79.4s from the first slide and the 81.0s observation
at the second slide's full-path detected onset.
Tracing the unmodified production detector reproduces all=9 / half=4 pages.
From 45.4 through 81.0 seconds half repeatedly has anchor_change=true and
future_change=true, but pair_stable=false; transitions are not committed.
All-path confirmation succeeds at 50.4,55.4,73.4,78.4 and81.0 seconds.
Half finally confirms82.6667 seconds; its prior segment retains representative40s.
This is detector confirmation/segmentation suppression with observed content,
not zero sampled frames of these contents. Sparse selection exposes the
current/future similarity requirement. It does not prove half is universally safe.
Evidence: Keyframe-M7-ethics-trace.json; scripts/trace_ethics_selection.py.
No production detector change has been made.
