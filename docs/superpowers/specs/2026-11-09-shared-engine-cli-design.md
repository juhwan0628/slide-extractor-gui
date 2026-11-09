# GUI·CLI 공통 엔진 설계 — 2026-11-09

## 합의한 목표
로컬 영상 경로 하나를 받아 사람 개입 없이 자동 ROI → 현재 키프레임 엔진 분석 → PDF 저장 → 캐시 정리를 완료한다. GUI와 CLI는 같은 저장소와 slide_core를 사용한다. 개발 폴더를 늘리지 않고 기본 작업 폴더에서 브랜치로 개발한다.

## 기준과 작업 방식
- 기본 폴더: /home/ubuntu/workspace/02_slide-extractor/slide-extractor-gui
- 기준 커밋: a1fdf2d131921aef183629b713cc26654ec2098c (main / origin/main)
- 작업 브랜치: feature/cli. 기본 구현은 현재 세션에서 직접 수행한다.
- 과거 GUI·worktree·검증 자료는 99_archive/slide-extractor-history에 보존했다. 과거 CLI는 99_archive/slide-extractor-legacy-cli에 있다.
- 새 작업 디렉터리나 worktree는 명시적인 필요가 생긴 경우에만 만든다.

## 접근 선택
사용자가 GUI 저장소에 CLI를 추가하고 엔진을 공유하는 방식을 선택했다. 과거 FPS CLI 재사용은 현재 엔진과 결과가 달라지고, 엔진 복사 방식은 유지보수가 이중화된다.

## 제품 계약
- Python 3.12 이상. 기본 CLI 설치에는 Qt를 요구하지 않는다.
- 기본 명령: slide-extractor lecture.mp4
- 기본 출력: 입력 영상과 같은 폴더의 lecture.slides.pdf. 쓰기 불가 시 오류를 반환하고 다른 위치로 임의 이동하지 않는다.
- -o/--output: 단일 영상의 PDF 경로. .pdf 확장자만 허용한다.
- --json {simple,detailed}: 선택적 JSON 동반 저장. 기본값은 JSON 없음. JSON 스키마는 기존 엔진을 따른다.
- --roi auto|full|x,y,w,h: 기본 auto. --ignore-mask x,y,w,h: 최대 한 개. 좌표는 회전·SAR 보정 후 표시 영상의 픽셀 기준이다. 마스크는 검출에만 적용한다.
- --overwrite: 명시적 덮어쓰기. 기본은 기존 출력 충돌 시 실패.
- --quiet: 진행 출력을 숨긴다. 오류는 stderr에 유지한다.
- --result-json: 성공·실패 결과 요약을 stdout에 JSON 한 개로 출력한다. 타임라인 JSON 옵션과 구분한다.
- 여러 입력은 순차 처리한다. --output-dir을 지원하며 한 파일 실패 후 다음 파일을 처리한다. 한 배치 내부에서 동일 출력으로 매핑되는 입력은 디코딩 전에 전체 거부한다. -o는 여러 입력과 함께 사용할 수 없다.
- 셸에서 확장된 파일 목록을 지원한다. 프로그램 내부 glob 확장·폴더 재귀 탐색은 첫 버전에 넣지 않는다.
- 일반 진행·진단은 stderr, 최종 요약은 stdout.
- 종료 코드: 0 전체 성공, 1 처리 실패 또는 배치 일부 실패, 2 명령행·설정 오류, 130 사용자 취소.
- 기본 키프레임 auto/all/half 정책과 spatial 검출기는 유지한다. FPS 혼합, 임계값 조정, 자동 전역 중복 제거는 추가하지 않는다.

## 공통 구조와 자원 수명
slide_core는 추출·저장 엔진, gui는 화면·편집, slide_cli는 명령 해석·진행·결과 표현을 담당한다.
GUI에서 Qt 없이 동작하는 첫 프레임 ROI 제안 코드를 slide_core/source_preparation.py로 이동하고 gui/preparation.py에서 호환 재노출한다. CLI 자동 ROI는 GUI의 최초 제안과 같은 경로를 사용한다.
slide_core/pipeline.py의 run_pipeline은 준비·분석·저장 함수를 호출한다. GUI 전체 작업 흐름은 첫 버전에 이 함수로 교체하지 않는다. GUI는 중간 결과 검토·편집이 필요하기 때문이다.
샘플 준비 객체의 소유권을 명확히 하고 성공·실패·취소에서 pin을 닫고 자기 캐시만 정리한다. CancelToken을 공유하며 Ctrl+C는 협력적 취소로 전달한다.
기존 저장 트랜잭션·잠금·원본 변경 검사를 재사용한다. 게시 완료 후 정리 실패는 출력이 존재함을 결과에 명시하며 단순 미생성 실패로 보고하지 않는다. 출력 보호 사전 검사를 수행하더라도 실제 게시 시점의 검사는 유지한다.
기본 설치에서는 FFmpeg/FFprobe가 외부 도구로 필요하다. 기존 CPU 대체 경로를 지원하고, 네이티브 도우미 부재 시 속도가 달라질 수 있음을 명시한다. 플랫폼별 네이티브 wheel 배포는 후속 작업이다.

## 성공 기준
같은 입력·ROI·검출 설정·실효 디코더/선택 정책에서 GUI 엔진과 CLI의 페이지 수·대표 PTS·PDF 렌더 이미지가 같다. PDF 파일 바이트는 export ID 등 때문에 비교하지 않는다.
Qt 미설치 환경에서 설치된 명령과 python -m slide_cli가 작동한다. 합성 영상 E2E와 긴 실영상 제한 검증을 구분해 보고한다.
