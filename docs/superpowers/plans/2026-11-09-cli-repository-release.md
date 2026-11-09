# CLI Repository Release Plan — 2026-11-09

**Goal:** 기존 juhwan0628/slide-extractor 이력을 보존하면서 새 공유 엔진 CLI 배포 저장소로 전환한다.
**Architecture:** 개발 원본은 slide-extractor-gui 하나로 유지한다. 검증된 원본 커밋에서 allowlist로 CLI 배포 스냅샷을 생성하고, CLI 저장소의 기존 main을 부모로 하는 일반 커밋/PR로 반영한다.
**Scope:** 현재는 계획 작성만. 원격 브랜치·태그 생성, push, merge, release publication은 아직 수행하지 않는다.

## 확인한 기준
- 원본 개발 저장소: juhwan0628/slide-extractor-gui, feature/cli, ccbff5b.
- 현재 원본 개발 검증: Linux에서 1061 tests passed.
- 배포 대상: juhwan0628/slide-extractor, main = 66709913a8c67a703c2e453b747d2c93368d9779 (2026-10-05).
- 대상 pyproject: 0.1.0, FPS 기반 slide_extractor 패키지.
- 조회 시 대상 공개 Releases는 없음. 실행 시 태그/브랜치 충돌과 원격 HEAD를 다시 확인한다.
- 새 장기 작업 폴더는 만들지 않는다. 원본 폴더에서 브랜치로 개발하고, export 산출물은 ignored dist에 둔다.
- CLI 저장소에는 장기 개발용 독립 체크아웃을 유지하지 않는다. 대상 Git 이력은 원본 저장소의 별도 remote/ref 및 임시 index로 처리할 수 있다. 실제 방법은 구현 시 검증한다.

## 결정과 제안
- force push 및 orphan 이력 교체를 사용하지 않는다.
- 구버전 main을 legacy-cli-v0.1.0-20261109 태그로 보존한다(이름 충돌 시 덮어쓰지 않는다).
- 신규 CLI 버전 제안: v0.5.0b2 prerelease. GUI의 기존 동명 태그를 수정하지 않으며, 서로 다른 저장소 태그는 provenance로 구분한다.
- 원본 GUI 저장소 main에도 CLI 구현을 통합한 뒤 그 원격에서 접근 가능한 확정 커밋을 배포 기준으로 고정한다. 기존 GUI installer tag/assets는 변경하지 않는다.
- CLI 저장소 내용 교체 커밋은 기존 대상 main의 후손이어야 한다. 다른 Git 이력을 강제로 결합하거나 원본 GUI 이력을 통째로 push하지 않는다.
- 공통 코어는 원본에서만 수정한다. CLI 저장소의 긴급 수정도 원본에 반영한 뒤 다시 export한다.

## 배포 스냅샷 범위
포함: slide_core/*.py, slide_cli/*.py, CLI 전용 pyproject.toml/README.md/CHANGELOG.md/docs/cli.md, LICENSE/THIRD_PARTY_NOTICES.md, CLI 테스트·합성 fixture, CLI CI, source-manifest.json.
제외: gui/, app.py, GUI screenshot/native installer workflow/download badges, legacy_fps/, 이전 slide_extractor/, output/, 강의 원본·추출 결과·벤치마크 개인 경로·secret·build cache.
공통 .py는 원본 blob 그대로 내보내고 파일별 SHA256을 manifest로 검증한다. 파일을 지우거나 압축하는 export 단계에서 코어를 재작성하지 않는다.

source-manifest.json: schema_version, source_repository, source_commit, package_version, tracked_file_sha256, export_tool_version.
대상 커밋 SHA는 자기 파일에 넣으면 순환하므로 manifest에 넣지 않는다. 배포 기록에서 대상 커밋과 wheel SHA256을 연결한다.

배포용 pyproject는 packages=["slide_core","slide_cli"]로 제한한다. gui extra/app.py를 제거하고 core dependency/console entry/version은 원본과 일치시킨다. 원본 GUI 저장소의 GUI 선택 설치 기능은 유지한다.

## D1 — 원본에 재현 가능한 export 기능 준비
- [x] scripts/export_cli_release.py 및 packaging/cli_release/ 아래 CLI README·metadata 템플릿을 원본에서 관리한다.
- [x] export는 깨끗하고 확정된 commit SHA만 받는다. 작업 트리의 미커밋 파일을 암묵적으로 섞지 않는다.
- [x] export 출력을 allowlist로 생성하고 제외 파일·누락·symlink·manifest hash·동일 입력 재생성 일치 테스트를 작성한다.
- [x] 버전은 공유 VERSION에서 읽고 템플릿에 중복 상수로 방치하지 않는다.
- [x] 원본의 기존 전체 테스트를 통과시킨다.

## D2 — CLI-only 테스트와 설치 검증 분리
현재 테스트는 그대로 복사할 수 없다:
- test_cli_pipeline.py에 gui.preparation 호환성 검증이 있다. GUI 전용 테스트는 원본에 남기고 공유 파이프라인 검증은 CLI-only에서도 실행되게 분리한다.
- test_cli_install.py는 gui/app.py/gui extra 포함과 GUI source ZIP을 검사한다. 대상 저장소에는 CLI 배포물의 실제 계약을 검증하는 별도 설치 테스트를 생성/유지한다.
- test_cli.py/test_cli_batch.py는 tests.test_keyframe_sampling.video에 의존한다. 합성 영상 helper를 독립 fixture로 분리하거나, 필요한 의존 fixture를 명시적으로 함께 export한다.
- [x] export된 저장소에 GUI 없이 pytest와 wheel build/install이 성공하는지 검증한다.
- [x] 새 venv에서 명령/모듈 실행, 단일·배치·고급JSON, 실패·취소·출력충돌을 검증한다.
- [x] wheel에 GUI/legacy/private data가 없는지 검사한다.
- [x] Python 3.12 Linux/macOS/Windows matrix CI를 대상 snapshot에 포함한다. 실제 green을 확인한 플랫폼만 검증 완료로 보고한다.

## D3 — 원본 기준 확정 및 대상 PR 준비
- [ ] 원본 feature/cli와 export 변경을 GUI 저장소의 검토 가능한 PR로 정리한다.
- [ ] 원본 CI 성공 후 main에 통합하고 배포 source_commit을 고정한다. 고정된 커밋에서 export를 재생성한다.
- [ ] 대상 main과 태그를 다시 조회하고 구버전 태그를 생성한다.
- [ ] 대상 기존 main을 부모로 하는 release/shared-engine-cli 브랜치 커밋을 생성한다. 변경 목록과 삭제 목록을 함께 검토한다.
- [ ] 대상 README는 CLI를 첫 화면으로 설명하고 개발 원본 링크·기여 경로·manifest 정보를 제공한다.
- [ ] 전환 안내: python -m slide_extractor → slide-extractor / python -m slide_cli, 기본 output 폴더→입력 옆, JSON 기본→명시 옵션, sample-fps 등 구옵션 제거, 신규 ROI/JSON 정책을 표로 적는다.
- [ ] 대상 PR CI가 3 OS에서 성공하고 설치 artifact가 PR commit에 연결되는지 확인한다.

## D4 — 일반 merge와 첫 CLI 릴리스
- [ ] 검토한 PR을 대상 main에 일반 merge한다. 다른 기여가 들어오면 새 main 기준으로 다시 검증하고 덮어쓰지 않는다.
- [ ] 검증된 대상 commit에 v0.5.0b2 prerelease를 만든다. 예상 태그가 이미 있으면 수정하지 않고 버전을 다시 정한다.
- [ ] 대상 저장소에서 생성한 wheel 및 해당 sdist를 포함한다. source manifest·원본 commit·artifact hashes·설치 명령·migration notes를 제공한다.
- [ ] 일반 wheel은 외부 FFmpeg/FFprobe가 필요하고 native helper는 포함하지 않는다고 명시한다. qpdf는 선택적이다.
- [ ] 재다운로드한 artifact hash, 새 venv 설치, source manifest hash를 확인한 뒤 배포 완료를 보고한다.
- [ ] PyPI 업로드는 별도 요청이 있을 때 진행한다.

## D5 — 이후 업데이트와 복구
- [ ] 이후 버전도 원본 수정→테스트→확정 커밋→동일 export→대상 PR/CI→release 순서로 운영한다.
- [ ] exporter가 생성하는 영역을 README/AGENTS에 명시하고 CLI 저장소 수동 코어 수정은 허용하지 않는 운영 규칙을 기록한다.
- [ ] 문제가 있으면 일반 revert commit 및 수정 릴리스로 복구한다. 기존 tag/assets를 다른 bytes로 교체하지 않는다.
- [ ] 원본·대상 두 repository의 commit/version/artifact 연결을 매 릴리스 기록한다.

## 완료 조건
기존 0.1.0 이력에 접근 가능, 대상 main은 기존 main의 후손, CLI-only 설치와 3 OS CI green, 공통 소스 hashes 일치, 설치 artifact 재다운로드 검증 완료.
이 계획 자체는 원격 변경·배포 실행을 수행하지 않는다.
