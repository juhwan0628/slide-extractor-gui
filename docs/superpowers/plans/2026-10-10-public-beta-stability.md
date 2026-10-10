# 공개 전 안정성 수정 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** 반복 분석 캐시 한도, 영상 열기 실패의 Undo 이력 손실, 복구 오류 안내 누락을 해결한다.
**Architecture:** 캐시 작성 잠금을 Project 수명 보호 객체로 인계하고 재분석 프로젝트는 같은 보호 객체를 공유한다. 만료 정리와 용량 부족시 미사용 세션 정리는 OS 잠금과 루트 예약 잠금 아래 수행한다. GUI는 새 영상 채택 성공 시에만 편집 이력을 비우고 복구 오류를 공통 안내 경로에서 처리한다.
**Tech Stack:** Python 3.12, Qt/PySide6, pytest, fcntl/msvcrt.
**Spec:** 사용자가 승인한 감사의 P1 캐시 수명/P2 Undo 이력/P2 복구 예외 세 항목.

## Global Constraints
- 출력 PDF/원본 파일, 활성/다른 프로세스 캐시는 삭제하지 않는다.
- 자동 ROI/변화 감지/병합 알고리즘과 서명 정책은 변경하지 않는다.
- 캐시 세션4GiB/루트8GiB/여유1GiB 한도를 유지한다.
- 기존 캐시 재사용과 취소시 이전 프로젝트 보존 계약을 유지한다.

## Review Focus
- 24시간 이상 열린 Project와 동일 캐시를 공유한 재분석 보호.
- 다른 프로세스의 작성/읽기 보호, Windows 삭제와 예약 상호잠금.
- 샘플링 중 취소/오류의 부분 캐시 즉시정리, 오류가 원인예외를 덮지 않음.
- 새 영상 실패/취소시 이력 유지, 성공시 초기화.
- 복구 LeaseBusy/OSError 안내와 출력파일/저널 보존.

### Task 1: Cache lifecycle
Files: slide_core/cache.py, slide_core/pts.py, slide_core/analysis.py, tests/test_cache_lifecycle.py.
Interfaces: CacheSession.retain() creates shared cache pin with close(); sample_stream accepts cache_owner callback; Project runtime _cache_pin shares across cached reanalysis. CacheSession(auto_prune=True, discard_on_error=True) handles inactive sessions under budget lock.
- [x] Write failing expired/pressure/partial-error/project-sharing/process-lock tests; run RED.
- [x] Implement shared pin, Windows-safe verified deletion, prune + pressure reservation retry, sampling/error ownership.
- [x] Run cache/analysis/sampling suite; full suite; commit.

### Task 2: GUI failure handling
Files: gui/window.py, tests/test_pre_public_failures.py.
Interfaces: unchanged public GUI methods; reset at successful probe adoption. Shared recovery helper catches RecoveryRequired/LeaseBusy/OSError and returns failure without publishing.
- [x] Write failing failed/cancelled probe history and recovery exception tests; run RED.
- [x] Preserve current preparation state on failed probe and history until adoption; handle recover errors.
- [x] Run GUI/export regressions, whole suite; commit.

### Task 3: Verification and delivery
Files: .github/workflows/ci.yml, packaging/QA_STATUS.md.
- [x] Add cache lifecycle tests to real Windows CI; verify actionlint and latest full suite.
- [x] Independent whole-branch review; fix important findings with RED→GREEN.
- [ ] Publish reviewed source changes to GitHub; preserve screenshot and current release metadata; report installed beta availability accurately.
