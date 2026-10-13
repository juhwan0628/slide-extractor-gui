# Detector core priority — 2026-10-13
User decision: pause M8/M9/M10 and resolve detector omissions/duplicates first.
M6/M7 implementation is preserved; half selection remains a development path.

## Goal
Reduce distinct-slide omissions and duplicate output simultaneously, while keeping
manual review work manageable. Internal observations/candidates are not output pages.

## Ground truth already supplied
SP six full-only candidates: duplicates.
Multicore seven full-only candidates: duplicates.
Ethics full pages2/3/4/5: one slide with changing states.
Ethics full page6: a second distinct required slide.
Both ethics slide contents are omitted by the half detector.
Trace shows current/future similarity blocks confirmation despite observed change.

## Design hypotheses, not implemented rules
Maintain an active slide group with an initial structural reference and a recent
representative candidate. Do not let repeated local changes move the only reference.
Evaluate spatial change, persistence/reversion and accumulated change together.
Pointer-like changes require evidence of small localized transient/reverting behavior;
small area alone is insufficient, and a brief distinct slide is not automatically noise.
Writing-like persistent local changes can update one group's representative rather
than emit another output page. Content additions/deletions remain possible transitions.
Representatives should favor readable, sufficiently complete content without treating
latest time as automatically best. Occlusion and return-to-earlier-slide behavior need tests.
Uncertain content is represented by grouped review candidates, not every changed frame.
Do not silently discard uncertainty to satisfy a numeric page cap.

## C1: Evidence and labels
Build labeled intervals from supplied ethics/SP/multicore clips:
distinct slides, annotation states, transient pointer/cursor, brief genuine slides.
Use original PTS. Inspect exact missed intervals rather than optimizing total page count.
Define slide recall, duplicate pages, representative-content loss and manual review work.

## C2: Offline grouping experiments
Reuse the same caches for every detector variant. Compare all and half input policies.
Separate change evidence, group boundaries and representative selection.
Test contributions individually before combining; thresholds are calibrated on labeled
examples and checked on held-out intervals/videos rather than chosen for this one clip.

## C3: Owner review of paired results
Require both ethics slide contents, group2/3/4/5, and retain SP/multicore content.
Inspect uncertain groups and review burden. Higher output count is not itself a fix.
New small content changes and brief true slides must not become pointer/annotation noise.

## C4: Production integration
After experimental evidence and owner design/result review, add regression tests,
integrate the selected grouping policy, verify full suite and real lecture outputs.
Then resume remaining decoder/cache/editing/device/release milestones.
No product detector code has been changed by this priority decision.

## Owner correction — 19:06 KST
Ethics page6 is a brief genuine slide, not a continuously present slide.
Duration/persistence and content-change magnitude must be independent evidence.
A dramatic content transition can justify retaining a single observed frame; lack
of persistence must not automatically suppress it. Add explicit brief-slide recall
coverage at both all and half input policies.
Pointer suppression requires localized small/transient evidence; brief appearance
or return to the former slide alone does not distinguish a pointer from a real slide.
Slide revisits require separating chronological occurrence from content identity.
Hash-based identity is an experimental hypothesis, not an established competitor
fact. Evaluate exact/perceptual identity under annotations, pointers and small but
meaningful slide revisions; similarity alone must not silently merge content.
Keep revisit events even if the export may eventually group identical content.
