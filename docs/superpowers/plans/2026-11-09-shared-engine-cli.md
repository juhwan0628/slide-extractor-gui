# Shared-engine CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Use the existing folder and feature/cli branch; do not create additional worktrees.

**Goal:** 현재 GUI 엔진으로 영상→PDF를 무인 실행하는 CLI를 제공한다.
**Architecture:** slide_cli가 옵션을 공통 AnalysisSettings로 변환하고 slide_core.pipeline을 호출한다. 검출기·디코딩·PDF/JSON 저장은 기존 엔진을 공유한다.
**Tech Stack:** Python 3.12+, argparse, 기존 NumPy/OpenCV/Pillow/reportlab/pypdf, FFmpeg/FFprobe.
**Spec:** docs/superpowers/specs/2026-11-09-shared-engine-cli-design.md

## Global Constraints
- 한 저장소·한 기본 작업 폴더, feature/cli 브랜치 사용.
- Python 3.12 이상. 기본 CLI 설치에는 Qt를 요구하지 않는다.
- 키프레임 정책과 검출기 기본값 유지. FPS 경로 재도입 금지.
- 원본·기존 결과 보호, stdout/stderr 및 종료 코드 계약은 설계 문서 준수.
- GUI 설치본 배포·PyPI 게시·GitHub push는 이 계획 작성 단계에 포함하지 않는다.

## Review Focus
- 한글·공백 경로와 대소문자/심볼릭 링크로 겹치는 출력: M2 사전 충돌 검사.
- 회전·SAR 보정과 초반 검은 프레임: M1 ROI·표시 좌표 검증.
- Ctrl+C와 출력 게시 직후 취소: M2 취소 및 게시 완료 상태 검증.
- JSON 동반 저장 중 실패와 기존 출력: M1 기존 트랜잭션·복구 상태 유지 검증.
- 네이티브 도우미 없는 설치와 패키지 소스 누락: M4 Qt 없는 CPU 설치 검증.

## 파일 구성
- 새 파일: slide_core/source_preparation.py, slide_core/pipeline.py.
- 새 패키지: slide_cli/__init__.py, slide_cli/__main__.py, slide_cli/cli.py, slide_cli/batch.py.
- 수정: gui/preparation.py, pyproject.toml(신규), .github/workflows/ci.yml, packaging/build_source_zip.py, README.md, docs/cli.md(신규).
- 테스트: tests/test_cli_pipeline.py, tests/test_cli.py, tests/test_cli_batch.py, tests/test_cli_install.py.
- GUI용 requirements 및 플랫폼 잠금 파일은 기존 빌드와 호환을 유지하고 필요 변경만 검토한다.

## M0 — 개발 기준 확인
- [x] 현재 main 기준과 작업 트리 상태를 기록하고 기존 고정 의존성으로 개발 환경을 구성한다.
- [x] QT_QPA_PLATFORM=offscreen PYTHONPATH=. python -m pytest -q 실행 결과를 기준으로 기록한다. 현재 기록만으로 통과를 주장하지 않는다.
- [x] 기존 GUI·코어·패키징 테스트의 기준 실패가 있으면 CLI 변경과 구분한다.

## M1 — 공통 자동 실행 파이프라인
**Files:** slide_core/source_preparation.py, slide_core/pipeline.py, gui/preparation.py, tests/test_cli_pipeline.py.
**Interfaces:**
- prepare_first_frame(source, *, cancel_token=None): 기존 GUI 함수와 같은 반환 계약을 유지한다.
- PipelineResult: pdf_path: Path, json_path: Path|None, page_count: int, representative_pts: tuple[int,...], selection_policy: str, decoder_backend: str, elapsed_s: float.
- run_pipeline(input_path: Path, output_path: Path, *, settings: AnalysisSettings|None=None, json_format: str|None=None, overwrite: bool=False, cancel_token: CancelToken|None=None, progress: Callable|None=None) -> PipelineResult.
- PipelineCleanupError(RuntimeError): result: PipelineResult를 보유해 게시 후 캐시 정리 실패를 전달한다.
- [x] 같은 자동 ROI, 대표 PTS·페이지 수·렌더 이미지 일치, 성공/실패/취소 캐시 정리, 게시 후 정리 실패 테스트를 작성한다. 회전/SAR/검은 인트로 fixture도 포함한다.
- [x] 신규 테스트가 새 모듈 부재로 실패하는지 확인한다.
- [x] 첫 프레임 준비 함수를 Qt 없는 코어로 옮기고 GUI에서 호환 재노출한다. 기존 GUI 호출 계약을 보존한다.
- [x] 기존 prepare_samples/analyze_project/export_pdf_only/export_project를 연결하고 finally에서 준비 객체를 discard한다. 결과와 기존 예외를 사용해 게시 여부를 유지한다.
- [x] python -m pytest -q tests/test_cli_pipeline.py 및 영향을 받는 기존 ROI·preparation·export 테스트 실행. PDF+JSON 실패 시 이전 출력과 저널 보호를 확인한다.
- [x] 기능 단위 커밋.

## M2 — 단일 영상 CLI
**Files:** slide_cli/__init__.py, slide_cli/__main__.py, slide_cli/cli.py, tests/test_cli.py.
**Interfaces:** build_parser() -> argparse.ArgumentParser; main(argv: list[str]|None=None) -> int.
- [x] 설계의 옵션, 기본 출력 경로, stderr 진행/stdout 결과, 결과 JSON, 0/1/2/130 종료 코드 테스트를 작성하고 실패를 확인한다.
- [x] argparse로 입력·ROI·마스크·출력 경로를 검증한다. display 좌표·직사각형 범위·파일 동일성·기존 출력 충돌을 분석 전에 검사하며 저장 시 재검사를 생략하지 않는다.
- [x] SIGINT에서 CancelToken을 취소한다. 게시 전에는 130, 이미 게시된 출력은 경로/게시 상태와 후속 오류를 명확히 보고한다. 이전 signal handler를 복원한다.
- [x] 일반 로그를 stderr에 두고 코어의 출력이 결과 JSON을 오염하지 않도록 경로를 검증한다. --quiet에서도 오류는 유지한다.
- [x] python -m pytest -q tests/test_cli.py tests/test_cli_pipeline.py 실행. 한글/공백 경로, 중첩 마스크, 기존 파일, 원본과 출력 동일 경로, 취소 후 자식 프로세스 종료를 확인한다.
- [x] 기능 단위 커밋.

## M3 — 순차 배치
**Files:** slide_cli/batch.py, slide_cli/cli.py, tests/test_cli_batch.py.
**Interfaces:** plan_outputs(inputs: list[Path], output_dir: Path|None) -> list[tuple[Path,Path]]; run_batch(jobs: list[tuple[Path,Path]], *, run_one: Callable, cancel_token: CancelToken) -> list[dict].
- [x] 여러 파일·한 파일 실패 후 계속 처리·출력 충돌·다중 입력 -o 거부·배치 취소·JSON 요약 테스트를 작성하고 실패를 확인한다.
- [x] 전체 출력 경로를 먼저 확정하고 같은 배치에서 겹치는 출력은 --overwrite 여부와 무관하게 분석 전에 거부한다.
- [x] 순차 실행하고 파일별 input/output/status/error_code/published를 모은다. 전체 성공 0, 일부 실패 1, 취소 130을 반환한다. 취소하면 이후 입력은 시작하지 않는다.
- [x] python -m pytest -q tests/test_cli_batch.py tests/test_cli.py 실행. 한 파일 처리 종료 후 캐시가 정리되는지 확인한다.
- [x] 기능 단위 커밋.

## M4 — 설치·문서·배포 경로 검증
**Files:** pyproject.toml, packaging/build_source_zip.py, .github/workflows/ci.yml, README.md, docs/cli.md, tests/test_cli_install.py.
**Interfaces:** console script slide-extractor = slide_cli.cli:main; python -m slide_cli; GUI 의존성 extra gui.
- [x] Qt 없는 설치, wheel의 slide_core/slide_cli 포함, --help/--version, FFmpeg 누락 오류, CPU fallback E2E, 소스 ZIP 포함 범위 테스트를 작성한다.
- [x] setuptools 패키지를 slide_core/gui/slide_cli로 명시하고 legacy_fps/tests를 런타임 패키지에서 제외한다. CLI 기본 의존성과 GUI extra를 정의한다.
- [x] 소스 ZIP 목록과 CI를 갱신한다. FFmpeg/FFprobe 외에 qpdf가 CLI 런타임에 실제 필요한지 코드·설치 E2E로 확인하고 문서에 검증된 요구 사항만 기록한다.
- [x] python -m pytest -q tests/test_cli_install.py 실행 후 Qt 없는 새 venv에 wheel을 설치해 실제 합성 영상→PDF/JSON을 실행한다.
- [x] 전체 GUI·코어 회귀 테스트와 기존 소스 패키지 검사 실행. macOS/Windows 경로·취소·잠금은 해당 OS에서 확인된 범위만 보고한다.
- [x] 긴 실영상 한 개로 cold start 총시간·페이지 수·대표 PTS·메모리·잔여 캐시를 확인한다. GUI 백그라운드 준비로 숨겨진 시간과 CLI 전체 실행시간을 혼동하지 않는다.
- [x] 기능 단위 커밋. 검토 가능한 diff·테스트 결과·설치 명령을 정리한다. main 통합 및 공개 배포는 별도 단계로 다룬다.

## 후속 범위
플랫폼별 네이티브 wheel/단일 실행 파일 배포, 디렉터리 감시, 내부 glob/재귀 탐색, 병렬 처리, 다운로드·전사 연결, 새로운 검출 알고리즘은 첫 버전 검증 이후에 검토한다.
