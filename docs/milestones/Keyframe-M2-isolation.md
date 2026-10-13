# M2 보완 — 키프레임 전용 런타임
제품의 AnalysisSettings/PreparedSamples/BackgroundSamples/analyze_project/Window에서 fps와 sampling_mode를 제거했습니다. 임의 sampler/decoder override, FPS compact, GPU/FPS 분기 및 v3 JSON 런타임을 제거했습니다. JSON 기능은 M3에서 새 계약으로 복구하며 이번 개발 단계에서는 PDF만 제공합니다.

프리뷰와 PDF는 같은 감사된 nokey 디코더를 사용합니다. input seek의 정확 시간 절삭을 끄고 정수PTS 선택 필터로 실제 키프레임을 재검증합니다. 인접 비키프레임이나 원점 재시도 경로는 없습니다. frame_limit이 있을 때 trim을 sample showinfo 앞에 두어 메타데이터·RGB 개수를 일치시킵니다. 지원되지 않는 디코더가 비키프레임을 출력하면 실패합니다.

고정 FPS 기준선은 공개 커밋4a8d486db124e31b130d37055985fa1e631ae300을 git archive로 임시 폴더에 펼친 뒤 별도 인터프리터에서 실행합니다. reference 텍스트는 당시 구현 기록이며 앱 의존성이 아닙니다. 제품 source ZIP/PyInstaller에는 legacy_fps를 포함하지 않습니다. CI도 제품과 기준선을 별도 작업으로 검증합니다.

공통 캐시·소유권·취소·프로세스 회수·편집·PDF 공개 안전성·설정/UI 회귀는 현재 제품에 유지했습니다. obsolete FPS/GPU-grid/v3 전용 케이스는 test-migration.json에 명시했습니다. v3 짝 저장의 새 스키마 포팅은 M3에서 해야 하며 기존 기준선 통과로 대체하지 않습니다.

아직 0.5.0 배포 단계가 아닙니다. M3 모델/JSON, M4 실제 강의 성능·정확성, M5 Mac/Windows 설치 검증을 이어갑니다.

## 독립 리뷰 반영
리뷰의 Important(불규칙 관측 VFR 변화 탐지 및 close-during-probe/cancel-worker 공통 회귀 복원)과 Minor(벤치마크 구 API 의존) 모두 반영했습니다. 테스트는 현재 키프레임 제품에 실행되며 이전 FPS 기준선으로 대체하지 않습니다. benchmark-analysis/core는 키프레임/PDF API를 사용하고 기존 FPS 비교 코드는 reference 텍스트에 격리했습니다. benchmark-analysis는 실행 실패가 있으면 실패 종료코드를 반환합니다.

## 최종 검증 · 2026-10-12
- 제품 전체 `QT_QPA_PLATFORM=offscreen PYTHONPATH=. python -m pytest -vv -o faulthandler_timeout=40`: 614 passed, 146.06s.
- 격리된 기준선 `python legacy_fps/run_tests.py -q`: 707 passed, 171.23s.
- 리뷰 보완 집중 회귀(제품 계약/불규칙 시각/GUI 취소·닫기/벤치마크): 27 passed.
- `git diff --check`와 제품/벤치마크 compileall 통과.
- source/developer ZIP에서 레거시 미동봉·구 API 호출 제거를 실제 ZIP 생성과 벤치마크 실행으로 확인.
- 서버에서 다른 CPU 작업이 실행 중이므로 위 전체 소요 시간은 성능 비교 수치로 사용하지 않습니다.
- offscreen 소스 검증이며 새 Mac/Windows 설치본 실행·서명·배포는 아직 하지 않았습니다.
