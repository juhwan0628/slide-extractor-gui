# Keyframe M3 Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Implement inline, one whole-branch fresh review at the end.
**Goal:** 키프레임 관측 모델과 PDF에 일치하는 JSON v4/simple 저장.
**Architecture:** 고정 격자 모델을 ordinal+PTS로 교체하고 keyframe_json 검증/payload와 keyframe_export 출력 엔진을 분리. 기존 ExportTransaction을 재사용.
**Tech Stack:** Python, PySide6, FFmpeg, PIL, pypdf.
**Spec:** docs/milestones/Keyframe-M3-spec.md

## Global Constraints
- decoder-keyframes-v1 only; no FPS/v3 runtime/fallback; no non-keyframe insertion.
- PDF-only default; version/release/native packaging not advanced yet.
- Source/cache paths excluded from JSON; original integer PTS authoritative.

## Review Focus
- Long gaps/first keyframe later than origin: no invented transition timestamps.
- Nonzero/negative PTS and rational timing: consistent references and no float grid.
- Edited/merged pages: simple navigation and detailed detected boundaries remain distinct.
- Cancellation/output/source change: no partial pair or overwrite without approval.
- Concurrent project mutation: immutable snapshot, reject changed project before publication.

### Task 1: Observation model
Files: models.py, pts.py, analysis.py, editing.py, model/decoder fixtures/tests.
Consumes audited keyframe decoder. Produces Sample(sample_id,ordinal,source_pts,time_base,cache_path,width,height,pts_origin=0), Project.sampling_algorithm and immutable snapshot provenance.
- [x] Write test_keyframe_model.py: no grid_index/nominal_time; sparse PTS ordinals contiguous; mixed clocks/repeated ordinals rejected at Project/Request/Result/Snapshot; legacy provenance rejected.
- [x] Run pytest test_keyframe_model.py; Expected FAIL for missing ordinal contract.
- [x] Implement model and migrate synthetic fixture constructors; preserve existing validation.
- [x] Run full suite; Expected all PASS.
- [x] Commit model + contract evidence.

### Task 2: JSON and paired export
Files: keyframe_json.py, keyframe_export.py, simple_json.py; port reference paired export tests to current engine.
Consumes observation snapshot. Produces payload_keyframes(snap,pdf_path,pdf_sha,export_id), dumps/loads/validate and export_project(...sidecar_format='detailed'|'simple').
- [x] Write test_keyframe_json.py/test_keyframe_export.py: actual VFR PTS, UUID/count/hash, source path absence, edited pages, invalid fields/types/bounds/ordinals, source/project mutation, rollback/cleanup/cancel.
- [x] Run tests; Expected FAIL for absent module/function (tests import inside functions so contract failures are localized).
- [x] Implement strict v4 validation and immutable paired export; simple timeline reflects representative navigation.
- [x] Port paired transaction/path/safety cases, preserving original assertions against current product.
- [x] Run full suite; Expected all PASS.
- [x] Commit JSON/export and evidence.

### Task 3: GUI and smoke
Files: window.py, desktop_entry.py, settings/native smoke/product package tests; JSON contract documentation.
Consumes export_project and keyframe_json. Restores Save options with Simple slide times / Detailed keyframe JSON v4, PDF+JSON approval snapshots and paired worker; PDF-only remains default.
- [x] Test settings Preserve/Cancel/Merge/Add/Replace/Delete and real GUI paired publication; smoke validates paired and PDF-only.
- [x] Run new tests; Expected FAIL while options unavailable.
- [x] Wire GUI and restore product tests previously scoped to temporary M2 PDF-only.
- [x] Run full suite + diff check; Expected all PASS. Independent whole-M3 review; important fixes RED→GREEN+full suite.
- [x] Commit final changes and report limits. No push/release.
