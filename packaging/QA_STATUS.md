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
