# Keyframe M4 Validation Plan
> **For agentic workers:** Use superpowers:executing-plans. This is validation tooling, not a product sampling change.
**Goal:** Validate real SP, multicore, AI ethics lectures with external FPS baselines and exact-keyframe exports.
**Architecture:** Frozen FPS commit 4a8d486 runs in an archived tree and separate subprocess; current app never imports it. Same source/settings, sequential balanced rounds, fresh application caches (OS file cache not dropped).
**Spec:** docs/milestones/Keyframe-0.5-design.md
**Tech Stack:** Python, FFmpeg, current profiling, PDF/JSON validators.
## Global constraints
Keyframes only in product; no new FPS fallback. Private lectures/images excluded from git. No release/version bump/native claims.
## Tasks
- [x] 1: External benchmark harness. Tests: actual tiny-video worker produces phase timings, PTS, pages and validated paired outputs; real background early/ready click paths. Run tests RED then implement and GREEN. Harness files in legacy_fps excluded from product. Commit.
- [x] 2: Three complete lectures (SP02-2-S01-12 34.9min, multicore Execution/Commit 117.3min, AI ethics chapter1 49.9min), modes keyframes/0.5/1 FPS once on each complete input; same remuxed middle300-second excerpt per source, three sequential balanced rounds. Full keyframe input also exercises real early/ready background Analyze paths. Capture wall/parent+child CPU, preparation profile, reused-cache analysis, cache bytes, gap distributions, current-product full PDF+JSON publication (once per source); FPS exports are not equal-work comparisons. Fixed20-page product PDF repeatability checked separately. Publish summary medians/ranges, explicit overlapping phase warning and host load. Keep raw outputs private.
- [x] 3: Accuracy: compare actual representative/transition tracks and inspect private contact sheets at disagreements, distinguish slide identity vs handwriting state. No unsupported all-lecture recall claim without ground truth. Synthetic long-GOP transient slide demonstrates limitation without fallback. Verify early Analyze continues same background producer and ready Analyze reuses it on real input. Decode-only/null and RGB pipe controls separate cost scopes, never subtract overlapping timings as additive CPU costs.
- [x] 4: Full regression, whole-milestone independent review, important fixes RED/GREEN if found; commit measured results and update milestone status. Retain feature branch.
## Review focus
Failure hiding; baseline interpreter contamination; unfair fresh/reuse caches; overlapping costs mislabeled; accuracy claims without annotation. Harness tests pin output success/error status; subprocess PYTHONPATH scoped separately; fresh roots per round; timing scope text; report explicitly labels human-audited subset.
## Interfaces / preflight
1 -> 2/3: worker JSON report fields; runs use same source fingerprints/settings and deterministic sample/representative PTS arrays.
2/3 -> 4: numeric raw reports and inspection notes feed versioned results; private asset paths not published.

Closure: independent review found no Critical/Important issues. Two Minor documentation items are deferred and explicitly scoped in Keyframe-M4-results.md. Isolated RGB-pipe attribution remains unestablished; native qualification belongs to M5.
