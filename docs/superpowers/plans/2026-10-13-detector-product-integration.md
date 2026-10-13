# Detector Product Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make validated slide grouping and annotation-aware representative selection available in the GUI, with all keyframes and accurate v5 persistence.

**Architecture:** Adjacent-boundary detection stages uint8 gray images on disk; representative selection scans that store with fixed per-pixel working memory. Dispatch and algorithm-specific JSON validation keep legacy projects available. Enable new-analysis defaults only after quality, compatibility and full-lecture checks.

**Tech Stack:** Existing Python/NumPy/Qt/FFmpeg stack, tempfile/raw seekable disk staging; no new dependencies.

**Spec:** docs/superpowers/specs/2026-10-13-detector-product-integration.md (approved2026-10-13 20:59KST).

## Global Constraints
- Every decoder keyframe; native-half remains experimental and rejected by spatial product analysis.
- No FPS sampling, revisit identity or unique-page consolidation.
- Pixel delta20; changed-pixel fraction.06; nonoverlapping20px cells, cell changed fraction.02 and coverage.30.
- Representative settings exactly match approved spec; do not import scripts into slide_core.
- Sample IDs/sourcePTS/cache images/editing topology remain authoritative.
- Preserve strict legacy v4 reading/re-export; new algorithm writes v5 with honest spatial_change/persistence1.
- Every image pass checks cancellation; stage-file/mmap cleanup on success/error/cancel, including Windows.
- Preserve previous project and CachePin ownership on failure.
- No release, push or merge in this implementation plan.

## Review Focus
- Long uninterrupted annotation slide: image RAM stays independent of observation count, and disk errors fail cleanly.
- Brief true slide at EOF: retained without future observation, serialized with valid adjacentPTS references.
- Tiny/all-invalid ROI masks: no divide-by-zero or silently fabricated output.
- Existing v4 project reanalysis: no silent algorithm switch or misleading v4 output after v5 detection.
- Cancel during representative pass: previous project/cache survives; temporary data closes/deletes on Windows.

---

### Task1: Product spatial groups and disk-backed representative selection
**Files:** Create slide_core/spatial_groups.py, slide_core/representatives.py; test tests/test_spatial_groups.py, tests/test_representatives.py.
**Interfaces:** spatial_detect(samples,gray_frames,*,duration,valid_mask,config,cancel_token=None,progress=None)->(tuple[Transition],tuple[DetectedSegment]); select_representative(read_frame,start,end,valid_mask,config,check_cancel)->int original sample index. read_frame(index)->uint8 2D ndarray; internal disk writer validates shape/type/cardinality.

- [ ] Write tests before modules: `test_brief_slide_and_return` expects3segments fromA,B,A; `test_local_writing_one_group` expects1segment; `test_sparse_distributed_boundary` expects boundary for6.25%pixels across>30%cells but none for local6.25%; `test_eof_slide` retains last singleton; `test_mask_excludes_changes` excludes ignored region.
- [ ] Add representative tests using100x100 white images: completed marks in last2frames win over early long state; last5x5 transient pointer loses; one observation index0; erased persistent notes expose coverage diagnostic; gray120 overlay covering static lines loses. Assert exact accepted research parity.
- [ ] Add nonmonotonic/cardinality/type/all-invalid-mask tests raisingValueError. Add injected stage write failure and cancellation tests in each scan; assert temporary directory empty and file handles closed after failure. A frame supplier reuses its buffer; staging/selection must still preserve frames correctly.
- [ ] Run `/tmp/slide-gui-review-venv/bin/python -m pytest -q tests/test_spatial_groups.py tests/test_representatives.py`; expected RED due missing APIs.
- [ ] Implement adjacent fraction/cell evidence and chronological segment records. Write frames sequentially to managed raw temporary file; seek/read one frame per scan. Avoid whole-group np.stack or N-sized image masks. Build brightest-reference, support/core-edge accumulators, then candidates. Use sufficiently wide counters. Rank minimum adjacent occlusion-cell count then supported-.25unsupported marks, latest tie.
- [ ] Run focused tests; expected PASS. Compare research vs product on synthetic cases and build/detector-core caches; require exact group boundaries and representative indices. Run full suite; expected no regression in existing legacy path.
- [ ] Commit product primitives and tests; ledger task completion with test command/result.

### Task2: Declared detector settings and analysis dispatch
**Files:** Modify slide_core/config.py, slide_core/analysis.py, slide_core/transitions.py; test tests/test_spatial_analysis.py and existing analysis/cancellation tests.
**Interfaces:** DetectorConfig exposes declared algorithm plus immutable spatial/representative settings; existing fields retain old meanings. Analysis dispatch invokes spatial_detect fromTask1 or old streaming_detect according to effective config. _settings_key includes full effective detector config.

- [ ] Write `test_explicit_spatial_analysis_preserves_brief_page`, `test_detector_change_invalidates_detection`, `test_spatial_rejects_half_prepared`, `test_cancel_preserves_previous_project`. Existing sample cache reuse remains legal under detector/ROI changes; detection result reuse requires matching config.
- [ ] Run focused analysis tests; expected RED because new algorithm settings/dispatch absent.
- [ ] Implement validated config and centralized effective-config resolution. Initially leave new default activation toTask4. Explicit halfPreparedSamples fail with typed policy error before analysis, without deleting its cache. Preserve legacy explicit config and importedv4 settings.
- [ ] Pass cancellation/progress into staging/selection. Progress starts at0, is monotonic across subpasses and finishes before assembly; verify progress events and cancellation in pass2/pass3.
- [ ] Run focused and full suite; expected PASS. Commit with ledger.

### Task3: Strict v5 JSON and legacy v4 compatibility
**Files:** Modify slide_core/keyframe_json.py and actual version gates identified in gui/export/load code; create tests/test_keyframe_json_v5.py; preserve tests/test_keyframe_json*.py.
**Interfaces:** Existing encode/validate entrypoints retain signatures, dispatch schema4/5. New algorithm settings serialize explicitly, spatial_change uses persistence1; legacy v4 retains original algorithm/settings/status contract.

- [ ] Find every schema/version and detector field gate using grep before edits; list consumers in ledger.
- [ ] Write `test_spatial_v5_roundtrip`, `test_brief_boundary_v5_interval`, `test_v4_legacy_roundtrip_unchanged`, `test_reject_mixed_algorithm_status`, `test_reject_missing_spatial_parameters`, `test_reject_invalid_metric_or_reference`. Assert v5 algorithm name, thresholds.06/.30 and exact sample references; v4 remains supported.
- [ ] Run new and legacy JSON tests; expected new tests RED.
- [ ] Implement separate algorithm/version-specific field validation with shared structural cross-reference checks. Do not silently migrate existing v4 files or export spatial data as old confirmed2/eof-only evidence. Ensure model config is reconstructed and preserved by the actual load/reanalysis path. Invalid numeric values (NaN/inf/bool), statuses, half-policy provenance and boundary ordinals fail closed where represented.
- [ ] Run JSON tests and GUI/export tests; expected PASS, PDF/image output unaffected. Commit with ledger.

### Task4: Real-product parity, full-lecture checks and default activation
**Files:** Create scripts/verify_spatial_product.py, docs/milestones/Detector-Integration-results.md; modify new-analysis effective default/GUI reset only after gates; test tests/test_spatial_defaults.py and gui tests affected by intentional new behavior.
**Interfaces:** Task2 analysis API andTask3 v5 persistence; verify script compares samples, boundaryPTS, representative indices, saved JSON and exported page count.

- [ ] Verify all-only accepted original clips: SP3/MC4/ethics6, and owner-accepted representative content. Assert fixed30% coverage preserves original C4 representatives (identical boundaries imply identical rank); first-SP validation recovery5chronological groups; validation2 all11SP/1MC/3ethics, including all3briefNotes occurrences. Assistant inspects any mismatch before changing acceptance expectations.
- [ ] Run real existing analysis API, export/save/load/reanalyze/edit flows with explicit spatial config; expected parity with research and valid v5. Add full-lecture benchmark using an available source, measure sampling/detection/representative/assembly wall times, peakRSS, temporary bytes and cleanup. Record hardware/load and distinguish one-run measurements from speed claims.
- [ ] Stress ranking using repeat input2000/20000frames; measure processRSS and show image working memory independent ofN, disk bytes linearN. Check cancellation during a long group and injected disk failure preserve previous project. Required checks must finish or exact blocking condition is recorded; do not activate default with unmet gates.
- [ ] Write `test_new_analysis_default_is_spatial`, `test_v4_reanalysis_stays_legacy`, `test_default_input_remains_all`. Run tests; expected RED before activation.
- [ ] Activate new-analysis default after gates; retain declared legacy config for loaded v4. Update tests only for intentionally changed default behavior, preserving legacy algorithms' own tests with explicit legacy selection rather than deleting coverage.
- [ ] Run final full suite plus representative real outputs; expected PASS and unchanged accepted content. Commit with ledger.
- [ ] Request one fresh whole-branch code review using requesting-code-review skill. Address important findings with RED→GREEN and full suite. Record remaining issues; no push/merge/release. Finish with implementation results, evidence and exact remaining device/release work.

## Self-review
Spec memory, cleanup, truthful status, v4/v5 compatibility, all-keyframe policy, cancellation, masks, accepted content and scope boundaries mapped toTasks1–4. Shared interfaces are spatial_detect/config inTasks1–2 and effective-config/schema persistence inTasks2–3–4. Execution recommended: native/inline, because tasks depend on shared interfaces and owner wants minimal handoffs; one fresh review at end.
