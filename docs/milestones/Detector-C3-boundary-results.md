# C3 supplemental boundary experiment — 2026-10-13

## Owner correction and trace
Owner: multicore all/half bundle3 must split from displayed219s candidate; other displayed groupings accepted.219.4667s is a representative, not the observed onset. Adjacent observations show onset208.4667s(all),209.4667s(half),10.88%/10.87% changed pixels and52.08% changed20px cells. The original12% pixel rule misses it. No time-based exception is implemented.

## Experiment
Keep C2 broad candidates and optionally add distributed lower-magnitude candidates. Same>20 gray delta and40% tile coverage; compare pixel fractions3%,6%,9%,12%. Threshold values are sensitivity probes, not globally calibrated policy.

All3%/6%/9% variants add exactly the required multicore boundary in both policies;12% does not. SP remains3bundles; ethics remains6bundles, including the brief slide. Multicore changes3→4bundles. Baseline alternatives remain accessible, with an additional onset observation in the split group. Group starts are observation PTS, not exact source slide-transition times.

This is stronger than fitting one threshold immediately below10.9%, since a range yields the same result on these clips. It remains a training-set result: no held-out generalization or semantic tiny-content classification is proven. Local cumulative writing might eventually cover many cells and produce false boundaries; retained alternatives and larger labeled coverage are still necessary.

## Verification and review
Synthetic test: equal6.25% changed area distributed across cells splits, while localized6.25% writing stays grouped. Failed with missing parameter before implementation;5 focused tests then passed. Temporary review#c3b shows all/half multicore bundles using detector grayscale resolution. Earlier review sections remain intact; expiry23:46KST unchanged. Product detector defaults remain unchanged.

Full suite:898 passed in121.41s, exit0. Six clip/policy comparisons verified threshold-range consistency;219.4667s candidate belongs to the new fourth multicore bundle. External review HTTP200. No release or production change.
