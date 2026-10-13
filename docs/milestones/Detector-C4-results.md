# C4 representative selection experiment — 2026-10-13

User constraint: minimize owner review work. Assistant inspects and selects representatives; do not request repeated review of accepted cases. No product detector change.

## Ranking hypothesis
Use full observation series in C3 accepted bundles with6%/40% supplemental boundaries. Per-pixel brightest observed reference exposes added dark marks (>20 gray levels). Marks observed at least twice receive support; single-observation groups remain valid. Rank retained supported marks minus0.25 times unsupported marks; prefer later time on equal scores. These are appearance heuristics, not semantic handwriting/pointer labels.

A visual inspection caught a real failure: SP70s menu popup received high dark-mark score. Global static-edge penalties also selected incomplete early multicore annotations. Investigated spatial loss: SP menu erases printed edges in adjacent filled20px cells; multicore annotations affect separate cells. Final overlay hypothesis counts adjacent cells with≥25% new darkness and≥8 missing recurrent core edges. Recurrent edges (>25 gradient) appear in≥60% observations. Prefer minimum overlay-cell count, then retained marks. Thresholds are exploratory and must be validated beyond these3clips. This local occlusion rule can misclassify dense annotation/other overlays.

## Results and assistant inspection
SP all91/281/299s; half92/284/296s.
Multicore all79/176.9333/207.7333/289.4667s; half78/177.9333/207.7333/289.4667s.
Ethics all40/79.4/82/97.6667/230/300.0667s; half40/79.4/81/96.6667/230/299.0667s.

Assistant inspected initial baseline contact sheets and final selected all/half detector-resolution contact sheets. Final sheets show the3SP slide identities,4multicore slide identities,6ethics identities, accumulated visible annotations and no SP menu popup. The previously reviewed multicore219s content belongs to the fourth slide; ethics brief chapter slide remains. This is visual evidence for supplied clips, not exhaustive annotation-content recall or guaranteed pointer removal. Full color source JPEGs published as optional final results, without asking owner to label all alternatives.

The numeric missing-supported fraction is NOT semantic content loss: it includes erased annotation states, popup pixels, image changes and video regions. It cannot automatically become a human-review request. Displayed selected frames are comparable all/half by content, not equal timestamps.

## Verification
Synthetic checks: late completed notes beat long early states; last transient pointer loses; one observation remains; erased supported mark states expose incomplete coverage; static text covered by a rectangular overlay loses. Missing module RED, then4passed; overlay RED (wrong index5), then5passed. Real grouping/brief-slide regressions retained. Full suite output recorded below after final implementation verification.

## Remaining work
Do not claim general semantic detection solved. Need held-out lecture checks, recurring slide identity separated from occurrences, and conservative production integration. No routine owner review requested for these selected images. Automated diagnostics and assistant visual inspection should resolve ordinary examples; only concrete unresolved semantic cases go to owner with a recommendation.

Final implementation full suite:903 passed in111.60s, exit0. Five representative tests pass. Assistant additionally inspected full-color SPall91s and multicoreall176.9333s JPEGs: accumulated colored annotations visible, no covering menu. External page/image HTTP200 verified. No push, merge or product/release modification.
