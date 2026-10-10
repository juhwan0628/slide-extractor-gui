# 배포 검증 기록

## 2026-10-10 — 0.4.10rc2 공개 전 안정성 수정

- 반복 분석 캐시: 새 샘플링 시작 시 만료 세션을 정리하고, 용량 부족 시 사용하지 않는 완료 캐시를 회수합니다. 현재 프로젝트, 재분석으로 공유하는 캐시, 다른 프로세스의 사용 중인 캐시는 OS 잠금으로 보호합니다. 분석 실패·취소의 부분 캐시는 즉시 정리합니다.
- 영상 열기 실패·취소: 이전 프로젝트의 편집 이력과 ROI 준비 상태를 보존합니다. 새 영상을 성공적으로 채택한 뒤에만 Undo/Redo를 초기화합니다.
- 중단된 출력 복구: 잠금 충돌과 파일 접근 오류를 사용자 경고로 처리하고 복구 저널·백업을 보존합니다.
- 회귀 검사 17개를 추가했습니다. 오래 열린 캐시·재분석 공유·별도 프로세스·용량 압박·취소·정리 실패와 실제 Qt 실패 경로를 검사했습니다.
- 서버 전체 검사: **617 passed in 48.00s**, 종료 코드 0. GitHub workflow 문법 검사(actionlint)와 diff 공백 검사 통과.
- 독립 최종 리뷰의 디스크 여유 공간 검사·manifest 저장 실패 두 추가 발견도 실패→통과로 수정했습니다. 독립 집중 검사 30개 통과, 남은 중요 발견 없음.
- 실제 Windows CI에 캐시 삭제·활성 잠금·별도 프로세스 보호 검사를 추가합니다.
- 이 기록 시점의 rc2 네이티브 설치본은 아직 빌드·출고 감사 전입니다. 아래 rc1 설치본 검증은 rc2 검증을 대신하지 않습니다.

## 2026-10-10 학교 커뮤니티 공개 전 점검

점검 대상은 공개 베타 **0.4.10rc1** 설치 파일과 README/사용법 문서입니다. 유료 코드 서명·공증, ROI 재설계, 필기·재방문 자동 처리 개선은 이번 점검에서 변경하지 않습니다.

### 확인 결과

- 서버의 전체 앱 회귀 테스트: **597 passed in 41.47s**, 종료 코드 0. 최신 다운로드 집계 테스트 3개도 별도로 통과했습니다.
- 공개 문서 커밋 `60ebe92f37094545ab5a2c2d6cfeef67d8ca3dc5`의 GitHub CI `38047964150`: Linux **594 passed, 6 skipped**; 실제 Windows 출력 잠금 검사 **7 passed, 1 skipped**. 플랫폼 전용 skip을 전체 OS 검증으로 표현하지 않습니다.
- 공개 DMG/EXE의 GitHub asset SHA-256은 기존 두 OS 설치본 출고 감사 `38015955293` 및 승인 자료의 해시와 일치합니다. 이번 점검에서는 새 네이티브 빌드·사용자 기기 재설치를 수행하지 않았습니다.
- 네이티브 실행 코드와 빌드 입력은 출고 소스 `36365be00f0ff5991231d5f4d74b28e12f962e4f` 이후 변경되지 않았습니다. 추가된 코드는 다운로드 집계용 스크립트·테스트이며 앱 실행 경로와 분리돼 있습니다.
- 공개 트리에 원본 영상·추출 PDF·환경변수 파일·설치 파일·vendor 폴더가 없습니다. 로컬 추적 파일/이력의 주요 키 패턴 검사에서 검출 없음. 이는 보안 감사를 대체하는 보증은 아닙니다.
- 앱의 분석·출력 경로에서 서버 업로드/텔레메트리 호출을 찾지 못했습니다. GitHub 다운로드 링크는 사용자가 열 수 있는 안내 링크입니다.
- 설치 안내에 남은 0.4.9rc3 링크를 **0.4.10rc1**로 정정하고, 화면 관리 안내를 실제 Mac 발표 영상 캡처로 갱신합니다.

### 공개 홍보 전 해결 권장: 반복 분석 캐시 누적

`gui/window.py`는 임시 폴더의 `slide-gui-cache`를 공유합니다. `CacheSession.close()`는 예약·잠금만 해제하고 JPEG를 남깁니다. `prune_cache()`에는 완료 24시간/미완료 1시간 만료 정리가 구현돼 있으나 실제 분석 경로에서 호출하지 않습니다.

기본 전체 캐시 한도는 8 GiB입니다. 반복 분석으로 한도에 도달하면 새 분석이 `CacheBudgetExceeded`로 실패할 수 있으며 앱 재시작만으로 정리되지 않습니다. 기존 PDF나 원본 영상을 손상시키는 재현은 아닙니다.

격리된 임시 폴더에서 전체 한도를 4096바이트로 줄인 재현: 완료·종료·24시간 이상 만료 처리한 JPEG 세션 5개가 남고 6번째 세션에서 예약 실패. 명시적으로 만료 정리를 실행하면 5개를 제거하고 새 쓰기가 성공합니다. 이 횟수는 축소 한도의 테스트 값이며 실제 사용자 실패 횟수 추정치가 아닙니다.

단순 정리 함수 호출만 추가하면 오래 열린 현재 프로젝트의 캐시를 삭제할 수 있습니다. 수정 시 현재/재사용 프로젝트의 캐시를 보호하고 다른 앱 인스턴스·취소·오류·Windows 잠금까지 회귀 검증해야 합니다. **학내 반복 사용을 권하기 전에 이 항목을 수정한 설치본을 만드는 것을 권장합니다.** 이 점검에서 실행 코드를 수정하거나 새 버전을 배포하지 않았습니다.

### 추가 발견: 실패 경로의 GUI 처리

- **P2 영상 열기 실패 후 Undo/Redo 소실:** 실제 offscreen Qt에서 분석→페이지 삭제로 Undo 이력 1개를 만든 뒤 존재하지 않는 영상을 열었습니다. 기존 프로젝트·페이지는 유지되지만 Undo 이력은 0개로 초기화됐습니다. 새 영상 채택 성공 전에 `open_source()`가 이력을 초기화하는 것이 원인입니다. 파일 선택 창에서 선택하지 않고 취소하는 경우와는 구분합니다.
- **P2 중단된 출력 복구의 예외 안내:** offscreen Qt의 실제 `export_pending()`에서 복구 함수가 `LeaseBusy`를 반환하도록 주입하자 예외가 메서드 밖으로 전달됐습니다. 실제 두 인스턴스의 복구 충돌 전체 재현은 하지 않았습니다. 출력 잠금 보호가 풀리는 문제는 아니며, 복구 실패를 잡아 사용자에게 안내할 필요가 있습니다.
- 위 두 항목은 이번 감사에서 확인만 했고 실행 코드는 변경하지 않았습니다. 캐시 수정과 함께 회귀 테스트를 추가하는 것을 권장합니다.

### 알려진 베타 제한

- Mac은 Apple Silicon, Windows는 x64 설치본을 제공합니다. Intel Mac/Windows ARM은 검증 대상이 아닙니다.
- 유료 서명·공증 미적용으로 OS 정책에 따른 경고·실행 차단이 가능합니다. 관리자 실행으로 해결된다고 보장하지 않습니다.
- 짧은 전환은 누락되고 필기·재방문은 중복될 수 있으므로 결과를 검토하고 수동 편집합니다.
- ROI는 첫 프레임 기반 고정 사각형이며 Ignore mask는 변화 감지에만 적용됩니다.

<details>
<summary>이전 개발·후보·출고 검증 기록 — 당시 상태이며 현재 상태는 위 점검을 기준으로 확인</summary>

# 0.4.9rc2 검증 상태

## 서버에서 확인

- M0–M3: 기준 실패 재현, 정확성/취소/게시 경계 수정, 성능 측정, 레거시 정리.
- 최종 새 Essentials-only 환경: 520개 테스트 통과(38.70초), 경고 없음. 독립 리뷰의 3개 중요 문제를 실패→통과 재현으로 수정.
- 최종 Linux PyInstaller 실행 파일은 외부 PATH 없이 번들 Qt/FFmpeg로 분석·PDF 저장 smoke 성공. Mac 검증과 구분합니다.
- 1080p PDF 10.573→7.879초, 같은 출력 계약 유지. 큰 타임라인 모델 검색 비용 감소.
- 서버는 Linux aarch64이며 이 결과를 Mac 네이티브 설치 검증으로 간주하지 않습니다.

## Mac 설치 후 기록할 항목

| 항목 | 상태 |
|---|---|
| 새 폴더에서 고정 입력 빌드·번들 smoke | 대기 |
| Applications에 설치 후 개발 환경 없이 실행 | 대기 |
| 대표/긴 강의 열기·분석·편집 | 대기 |
| PDF 단독과 JSON 동시 저장, 내용·페이지 확인 | 대기 |
| 재실행·캐시 재사용·손상 캐시 복구 | 대기 |
| 분석/추출 취소, 저장 완료 직후 취소 | 대기 |
| 기존 파일 승인, 승인 뒤 파일 변경 거부 | 대기 |
| GUI 응답·소요 시간·부모/FFmpeg 메모리 | 대기 |
| 반복 실행 후 남은 프로세스·임시 파일 | 대기 |
| VFR·색상 태그 입력 | 대기 |

## 공개 배포

승인 FFmpeg/Qt 입력, 정확한 소스/라이선스 사본/SBOM/교체 절차, 공개 서명/notarization, 깨끗한 Mac 설치가 아직 대기입니다. Windows 설치·실영상 검증도 별도로 대기입니다. 자료를 채웠다는 선언만으로 audit_release를 우회하지 않습니다.

최종 독립 리뷰에서 발견된 CI 실행 권한, 공급/번들 해시 구분, 실제 배포 자료 검사 문제는 재현 테스트로 보강했습니다. 후보·공급 입력·빌드 기록의 연결을 유지하고, 검토자가 확인한 동일 후보만 승인 해시로 검증합니다.

## 2026-10-10 Windows/잠금 및 GitHub 준비

- 사용자의 Windows 빌드 로그에서 번들 smoke success(0.4.9rc1, frozen, bundled tools, 분석 2개·PDF 2페이지)를 확인했습니다. 사용자는 콘솔 깜빡임과 PDF 저장 해결을 확인했습니다.
- 공통 디렉터리 동기화와 Windows FFmpeg/프로세스 정리 옵션을 수정했습니다.
- 출력 잠금 파일 정리 변경은 서버에서 539개 테스트 및 4프로세스 반복 충돌 검증을 통과했습니다. 해당 변경의 실제 Mac/Windows 재검증은 별도입니다.
- GitHub Actions는 새 GUI 저장소용으로 준비 중이며 아직 실행하지 않았습니다. 서버 테스트 결과를 GitHub 러너 통과로 표현하지 않습니다.
- 유료 서명·공증은 베타 필수 조건에서 제외합니다. 배포 자료와 실제 구성품 검토는 유지합니다.


## 2026-10-10 GitHub native candidate checkpoint

- Source commit b04bfbffadb7c8de3b8e775626ac7c20596c4da9, version 0.4.9rc1. Native run 37972733321: both macOS arm64 and Windows x64 SUCCESS.
- macOS: source-built FFmpeg, frozen empty-PATH analysis/PDF smoke, strict ad-hoc codesign verification, DMG creation and mounted-DMG copied-app smoke passed.
- Windows: source-built static FFmpeg, frozen empty-PATH analysis/PDF smoke, Inno Setup installer and installed-app empty-PATH smoke passed. The hosted runner account is not a separate standard-user security-policy test; unsigned code bypassing Smart App Control is not claimed.
- Source CI 37972733336: 553 passed, 6 skipped. Remote Linux suite: 559 passed in 38.90s.
- Actual CI failures fixed: FFmpeg log is ffbuild/config.log; inventory selects tools files instead of licenses/ffmpeg directory. Deterministic directory-first reproduction failed with IsADirectoryError before the fix, then passed.
- Input artifacts retain pinned FFmpeg/Qt/Qt for Python sources, original licenses, wheel notices and observed inventories. Official FFmpeg 8.1.2 PGP signature independently verified.
- native-installer-* artifacts contain only the corresponding DMG/EXE; no manual build scripts or source folders.
- Unsigned/ad-hoc installation test candidates; not public release approval. Modified Qt-library execution, final native/wheel sources and notices review, app license choice and release approval remain pending. No GitHub Release published.


## 2026-10-10 PDF-only lock regression — verified native candidates

- Default PDF-only export used the persistent cache lease rather than the output lease cleanup wrapper. Previous paired PDF+JSON checks did not cover this path. The common exporter now uses `export_file_lease` on both platforms.
- RED: three regression tests reproduced leftover locks after save/overwrite, publication failure and cancellation. GREEN after the shared lease change: all three pass; output concurrency and replacement safety tests retained.
- Remote Linux full suite: 562 passed in 39.50s. Source CI run 37977571494: 556 passed, 6 skipped. Its actual Windows lock job: 7 passed, 1 skipped (POSIX-only rename test).
- Native candidate source: 53290faa60ea4091da9af4dccc4ae5aa9dfa39bb, version 0.4.9rc2, run 37977571499. Both macOS mounted-DMG installation and Windows installer installation passed; frozen/installed analysis/PDF smoke and both lock-cleanup assertions passed on both OSes.
- Frozen and installed smoke now exercise PDF+JSON and PDF-only save/overwrite, and assert `pdf_only_checked` and `output_lock_cleanup_checked`. Historical unrelated output locks are not deleted in bulk.

- Installer-only artifacts: macOS ARM64 11639648425; Windows X64 11640181724. Both native jobs and run 37977571499 concluded SUCCESS. No public GitHub Release was published.


## 2026-10-10 Repository presentation and release staging

- User-facing README includes a real GUI capture of self-authored synthetic slides, CI/status badges, platform downloads and collapsed developer/test instructions. OS installation pages now describe prebuilt DMG/EXE rather than personal build kits. Legacy developer entry points remain compatible.
- Release staging workflow run 37986792406 SUCCESS. Draft prerelease v0.4.9rc2 targets the exact tested native source commit and includes both unchanged installers, all three SHA256-verified corresponding source archives, hashes and observed build/review evidence. Public release approval remains false.
- Existing release assets/gate/packaging checks: 20 passed. actionlint, embedded Python parsing and rendered local Markdown link checks passed. Source CI run 37986792488 succeeded on both jobs. No production application behavior changed.

## 2026-10-09 — 0.4.9rc3 license and native release review

- MIT License applied to application source and included in installed apps; About / Licenses dialog added.
- Exact rc2 macOS OpenCV avcodec returned GPL version 3 or later with x264/x265. rc2 remains an unpublished superseded draft.
- rc3 uses pinned source-built image-only OpenCV with videoio/FFmpeg/x264/x265 absent. Exact source archive, packaging patch, build flags and SHA256 are retained.
- Native source commit a0c7043c26eca7cd75079ba39c4757134b1793c2; native run 37991615142: both OS SUCCESS. Source CI 37991615111: 563 passed, 6 skipped. Remote complete source suite: 569 passed.
- Both actual DMG/EXE installs, empty PATH, analysis, PDF-only/repeated PDF save, PDF+JSON and output-lock cleanup succeeded.
- Modified installed QtCore was loaded with qVersion 6.12.9; macOS local ad-hoc re-sign/strict verification and Windows unsigned execution succeeded. This is a compatible binary replacement smoke, not a rebuilt-Qt compatibility guarantee.
- Independent installed-byte/source/notice audit run 37992725057: both PASSED, errors empty. Exact installer/audit manifest hashes are in packaging/release-approval.json.
- Actual Qt modules: Mac Core/DBus/Gui/Network/Svg/Widgets; Windows Core/Gui/Network/Svg/Widgets. No GPL-only Qt module or OpenCV video codec helper was found. Mac NumPy has no GCC/libquadmath dylibs; Windows OpenBLAS/GCC exception notices are preserved.
- Source archives, platform-specific OpenCV patches, original notices, runtime addendum and bound audit reports accompany the release. No paid signing or notarization is added.
- A release metadata tag may differ from the immutable native build commit only in the workflow's explicit review/documentation allowlist. Any application/build input change fails staging. Candidate commit and actual installer SHA256 remain bound to native and source CI records.


## 2026-10-10 — 0.4.10rc1 manual page editing

- Shift range / Ctrl-Cmd individual selection and selection count; selected right-click preserves the set. Merge retains the chronologically last exact Page identity/frame/metadata and preserves unselected pages. Bulk deletion is atomic.
- Undo/Redo restores pages, selection, current focus, preview sample and native Shift anchor/base selection; 100-edit history. Edit shortcuts are restricted to the page list; text inputs and busy states are tested.
- Fresh whole-branch review reproduced stale Qt model-row callbacks and lost Shift anchors after Undo. Both received failing regressions then fixes; reverse/disjoint ranges and subsequent plain navigation also pass.
- Real synthetic exports verify edited PDF/JSON counts, stable page IDs and timestamps, PDF-only export, no leftover output locks and unchanged source bytes. Automatic analysis remains unchanged.
- Remote full suite: 597 passed in 44.80s, exit0. Same source CI 38015387742: 591 passed, 6 skipped; Windows locks 7 passed, 1 skipped. actionlint and diff checks passed.
- Immutable candidate commit 36365be00f0ff5991231d5f4d74b28e12f962e4f, native run 38015387743: both OS SUCCESS. Empty PATH bundled app, installed DMG/EXE app, manual editing/keyboard/edited export and modified QtCore smoke passed.
- Native inventory delta is only QtTest framework/binding on Mac and Qt6Test.dll/QtTest.pyd on Windows. Official Qt Test 6.12 licensing: https://doc.qt.io/qt-6.12/qttest-index.html#licenses-and-attributions. Full pinned source archives and original license copies include this module. No extra video codec was found.
- Independent fresh installed-byte/source/notice audit run 38015955293, review commit 4e656bf97adc8e3f9d3a7edbfd259bbc0bcb18d7: both PASSED, errors empty. Exact installer and audit-manifest SHA256 are bound in release-approval.json.

</details>
