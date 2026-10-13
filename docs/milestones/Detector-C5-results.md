# C5 revisit and held-out pilot — 2026-10-13

## Owner baseline
C4 all/half representatives for SP3, multicore4, ethics6 accepted by owner at20:26KST. Stored in Detector-C1-labels.json referencing immutable committed C4 result. User review effort must stay minimal: assistant performs image comparison, not owner candidate labeling.

## Conservative identity probe
link_occurrences stores every chronological occurrence. SHA256(shape,dtype,pixels), followed by array equality, assigns a shared identity only to exact repeats. Approximate mean absolute grayscale distance below.02 suggests a candidate but does not merge. Thus tiny content revisions remain distinct. Exact A→B→A synthetic sequence retains3occurrences and2identities. This is a conservative prototype, not annotation-invariant slide identity.

## First unseen lecture pilot, fixed settings
Three different lectures, requested600–900s windows: SP02-2-S01-12, multicoreIssue(Memory), ethics chapter4. First remux retained negative PTS/discard flags, so source probing failed; research clip creation corrected with avoid_negative_ts make_zero. Clipping is stream-copy and may include earlier keyframes;600s is requested origin, not exact source PTS mapping. Clip hashes stored. No product media workaround introduced.

| Clip | Baseline all/half pages | Fixed6% pixel/40%tile groups all/half |
|---|---:|---:|
| SP |27/24|3/3|
| Multicore |37/27|2/2|
| Ethics |5/5|5/5|

Assistant inspected10-second coverage contact sheets plus selected representatives. MC sampled material showed2slides, ethics5; sampling is not exhaustive recall ground truth. SP is a definite failure:5chronological occurrences A→B→A→C→D,4distinct slides. C(Unsigned addition in C) and D(Signed addition) were merged into the third group; representative selected D and omitted C.

SP observed C onset34.8667s:6.69% pixels/36.11%tiles; D onset200.8667s:8.27%pixels/38.89%tiles. Fixed40% coverage rule excludes both. Real A-return compression differences yield different hashes; sampled A1s vs returnedA19.8667s distance.00308 flags an approximate candidate, not proven exact identity. This directly demonstrates why exact hash alone does not solve real slide returns.

## Post-validation calibration, explicitly not held-out success
6%pixel with20% or30%tile coverage yields5SP occurrences in all/half. Original3clip all/half bundles unchanged at3/4/6; unseenMC2/ethics5 unchanged.30% example selected SP1/9/33.8667/192.8667/300.8667s. Assistant inspected the five selected images: A,B,A,C,D recovered, completed C writing visible and no final popup. Separate report Detector-C5-sp-recovery.json. This window becomes calibration evidence after parameter adjustment. Need a fresh unseen window before claiming generalization. No threshold/default/product integration changed.

## Verification
Revisit tests: missing-module RED then2passed. Final suite905passed in114.79s, exit0. Experiment reports stored and diff check run. Baseline accepted cases remain recorded; production remains unchanged.

## Next design constraint
Keep occurrence chronology independent of slide identity. Hash/perceptual similarity can shortlist matches, but annotations, small semantic replacements and compressed returns require verification before unique-page export merging. Test these and fresh held-out windows before production. A decline in total page count is not evidence of accuracy; the SP failure is reported even though tests pass.
