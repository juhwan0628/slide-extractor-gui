# Detector C1/C2 initial research — 2026-10-13

## Scope and status
M8-M10 paused. No slide_core detector change and no default/release change.
Existing owner-reviewed cases are recorded in Detector-C1-labels.json.
Caches are reproducibly built from three300-second clips with source SHA256 and
original PTS; build/detector-core NPZ files are local research data, not public assets.
Real pointer-only labels, small meaningful revisions and held-out videos are still missing.

## C1 baseline reproduction
SP all30 / half24; multicore all28 / half21; ethics all9 / half4.
Owner labels: SP6 and multicore7 unmatched candidates duplicate.
Ethics full2/3/4/5 one required slide, full6 a brief second required slide.

At the320x180 detector resolution, ethics representative51.4 vs56.4/79.4
has ~1.1% changed pixels;51.4 vs74.4 has no pixels beyond20 gray levels.
40 vs51.4 differs across41.6% of pixels and66.0% of20px cells.
79.4 vs81.0 differs across34.1% of pixels and61.8% of cells.
81 vs82 differs across0% of pixels beyond20;82 vs82.6667 differs across57.4%.
These are example measurements, not general calibrated thresholds.

## C2 hypothesis probe
A research-only detector collects broad spatial changes without requiring a future
similar frame.16 pixel/cell threshold combinations per input policy were checked.
Compare existing baseline, baseline plus broad candidates and broad-only group
hypothesis separately; candidate counts are not final-page quality.

The example setting pixel_fraction=.12 / tile_fraction=.4 produces6 ethics
candidate groups with all and half inputs:
all representatives40,79.4,82,97.6667,230,300.0667 seconds;
half representatives40,79.4,81,96.6667,230,299.0667 seconds.
79.4 corresponds to the owner's same-slide group2/3/4/5;82/81 retain the brief slide.
Reference comparisons support these matches, but owner review of the resulting
images remains necessary. The current representative rule is last observation only,
a deliberate temporary probe; C4 must replace it.

An onset-only test near50.4 initially appeared to fail first-slide recovery.
This evaluation was invalid: the broad candidate starts41.4 and its representative
79.4 contains the required slide. Exact reference event timing is not content recall.
A future evaluation must compare content/representatives and chronological occurrences.

## What this does not prove
Broad-only grouping yields just3 candidate groups each on SP/multicore at this
setting. That is not evidence of successful duplicate removal; small genuine slide
changes may be lost. Broad candidates should supplement other evidence until
content grouping and uncertainty handling are validated.
No global threshold or broad-only detector is approved for production.

## Verification
Synthetic regression tests: a one-observation distinct slide plus return produces
both boundaries; small transient pointer and local accumulating writing do not
produce broad candidates.3 tests passed after missing-module failures.
Full existing suite plus research tests:893 passed, zero failures,108.41 seconds.
The probe's explanatory output was subsequently corrected; its candidate function
was unchanged. No performance claim about the production pipeline is made.

## Next
C3: preserve baseline small-change evidence while grouping confirmed same-slide
states; inspect ambiguous candidates instead of deleting them to meet a page cap.
Expand real labels, test persistent localized content replacements, and compare
content recall/duplicate output/representative loss/manual review together.
Temporary review page includes C2 ethics images; original expiry unchanged.
