# 0.4.9rc1 빌드

## 개인용 macOS arm64

`bash scripts/build-macos-personal.command`를 실행합니다. Python 3.12, 로컬 FFmpeg/FFprobe, 네트워크가 필요합니다.
`requirements-macos-arm64.lock`은 이전 Mac 빌드에서 확인한 버전에 기반하며, 이번 변경의 Mac 네이티브 검증은 아직 필요합니다.
필요한 QtCore/Gui/Widgets/Test만 포함하는 PySide6-Essentials를 사용합니다.

개인용 spec은 공통 spec을 선택합니다. 빌드는 입력 바이너리를 복사하고 SHA-256, -version 출력, Python/플랫폼/전체 패키지 목록을 manifest로 기록합니다. 번들 smoke와 codesign 검증이 성공한 뒤 새 임시 staging에서 버전이 붙은 DMG를 생성합니다. 개인용 manifest는 공개 배포 승인으로 표시되지 않습니다.

## 공용 후보 CI

`.github/workflows/native-build-template.yml`은 수동 실행 전용입니다. 같은 저장소의 실행 ID에서 플랫폼별 `approved-native-inputs-macOS-ARM64` / `approved-native-inputs-Windows-X64` artifact를 공급해야 합니다. 각 artifact는 ffmpeg/ffprobe, binary-manifest.json, 실제 라이선스 사본, SBOM, 정확한 소스 아카이브와 교체 안내를 포함해야 합니다.

소스 아카이브 경로는 CI 작업 디렉터리에서 접근 가능하게 manifest에 적습니다. macOS는 arm64, Windows는 x64 빌드 입력이 필요합니다. Windows lock과 설치 스크립트는 실기기 검증 전 상태입니다.

CI는 고정 lock을 설치하고 공통 진입점을 빌드해 번들 smoke, 설치 후보 생성, 실제 audit_release를 수행합니다. 실패해도 사설 artifact에 후보와 진단 자료를 보존합니다. audit 통과는 예비 검증이며 공개 업로드나 라이선스 검토 완료를 뜻하지 않습니다.

공개 Mac 배포에는 Developer ID 서명, notarization/stapling 및 깨끗한 Mac 설치 검증이 필요합니다. 현재 자격 증명·승인된 공급 바이너리가 없어 적용하지 않았습니다. 개인용 ad hoc 검증과 구분합니다.

## 검증

Linux 검증용 lock은 macOS 빌드 lock과 구분합니다. 개발용 ZIP에서 `requirements-dev.txt`를 설치해 전체 테스트를 실행합니다. 사용자용 ZIP은 테스트를 넣지 않습니다. ZIP은 `python packaging/build_source_zip.py OUTPUT.zip`, 개발용은 `--include-tests`로 생성합니다.

## 공급 입력과 완성 후보의 해시

Artifact 전송이 실행 권한을 보존하지 않으므로 CI는 FFmpeg/FFprobe의 공급 SHA-256을 먼저 검증한 뒤 실행 권한을 복원합니다. manifest의 각 도구 `sha256`은 공급 파일의 값이고 `bundle_sha256`은 검토한 **완성 후보 파일**의 값입니다. Mach-O 경로 수정/서명으로 두 값은 달라질 수 있습니다.

첫 빌드의 `candidate-inventory.json`과 번들에 포함된 `build-manifest.json`은 관측값이며 승인이 아닙니다. 검토자는 실제 자료·설치·서명 상태와 동일 후보를 확인한 뒤 후보 버전, build_manifest_sha256, 두 도구의 bundle_sha256을 검토 manifest에 기록합니다. 공급 입력 해시는 build manifest에 연결되어 있습니다.

승인한 해시는 **보존한 동일 후보**를 대상으로 audit_release에 적용해야 합니다. 새 빌드/새 서명으로 바이트가 달라지면 새 검토가 필요합니다. CI 재빌드가 이전 승인의 해시와 다르면 gate가 실패하는 것이 정상입니다. 첫 빌드도 사설 후보와 실제 해시를 보존하되 공개 승인으로 만들지 않습니다.

공용 모드는 실제 licenses, SBOM.json, SOURCE_AND_REPLACEMENT.md, build-manifest.json을 요구합니다. gate는 자료의 존재·내용·예상 구성 요소와 해시/후보 연결을 확인하지만, 내용의 법적 충분성은 검토자가 확인해야 합니다.

Mac 사설 후보 검토는 보존된 DMG를 마운트해서 그 안의 앱을 대상으로 수행하세요. DMG는 앱의 실행 권한·심볼릭 링크를 보존합니다. GitHub artifact에 따로 올라간 원시 .app 디렉터리를 설치본으로 취급하지 않습니다.
