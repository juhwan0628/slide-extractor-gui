# 맥·Windows 동시 베타 배포

저장소: `juhwan0628/slide-extractor-gui`. 공통 소스와 `slide_core/version.py` 한 곳에서 버전을 관리합니다.
사용자는 macOS Apple Silicon `.dmg` 또는 Windows x64 설치 `.exe`를 받습니다. Python·Qt·FFmpeg·FFprobe를 포함하며 개발 환경을 준비할 필요가 없습니다.

## 현재 준비

- 최신 소스 CI: 553 passed, 6 skipped (run 37972733336).
- 네이티브 후보 run 37972733321: 같은 커밋 b04bfbff에서 macOS arm64 DMG와 Windows x64 설치 EXE 생성 및 설치본 분석·PDF smoke 모두 성공. 설치 파일 전용 native-installer-* 아티팩트가 있습니다. 공개 릴리스 승인은 별도입니다.
- `Native installer candidates`가 두 OS에서 고정 FFmpeg 8.1.2 소스를 직접 컴파일합니다. 개인용 Gyan GPL 빌드를 복사하지 않습니다.
- GPL·nonfree·version3·외부 라이브러리 자동 탐지를 비활성화하고 실제 `-version`의 설정을 확인합니다.
- Qt 6.12.0, Qt for Python 6.12.0 및 FFmpeg 소스는 `packaging/native-sources.lock.json`의 SHA256으로 확인합니다. 라이선스 원문과 설치된 wheel의 고지 파일을 수집합니다.
- 최종 후보의 실제 해시, 빌드 provenance, 빈 PATH 분석·PDF smoke 및 설치 smoke를 기록합니다.
- 후보 빌드는 공개 배포 승인이 아닙니다. `VERIFIED_INPUTS`는 후보에만 허용하며 기존 공개 배포 감사는 계속 `APPROVED` 자료를 요구합니다.

## 실행 순서

1. `Native installer candidates`를 수동 실행하거나 해당 workflow/소스 빌드 설정을 main에 반영합니다. 두 네이티브 러너가 소스 다운로드·컴파일·라이선스 수집·PyInstaller·DMG/Inno Setup·설치 테스트를 자동 수행합니다.
2. 같은 run의 `native-inputs-macOS-ARM64`, `native-inputs-Windows-X64`는 정확한 소스 아카이브, 원본 라이선스, wheel 고지, 컴파일 설정, 입력 해시와 인벤토리를 담습니다. `native-candidate-*`는 설치 파일 및 실제 설치 테스트 결과를 담습니다. 사용자가 폴더를 만들거나 빌드할 단계가 아닙니다.
3. `release-gate.txt`에는 아직 미완료인 공개 배포 감사가 기록됩니다. 후보 실행 성공은 설치 빌드/테스트 성공을 의미하며 해당 감사의 성공을 의미하지 않습니다. 입력 단계에 최종 번들 해시를 미리 요구하지 않습니다.
4. 두 후보에서 실제 Qt 모듈 및 수정 DLL/dylib 실행, wheel의 대응 소스/빌드 수정분, OpenCV의 내장 FFmpeg, 전체 native 의존성과 고지를 검토합니다. 앱 자체 소스 라이선스도 선택해야 합니다. 정확한 소스 아카이브는 14일 CI 보관에서 끝내지 않고 최종 공개 릴리스에 함께 제공해야 합니다.
5. 관찰된 후보에 맞춰 감사 manifest를 작성하고 `packaging/audit_release.py`를 통과시킵니다. 자동 생성된 입력 자료를 무조건 `APPROVED`로 바꾸지 않습니다.
6. `audit_release.py --report`로 실제 감사 결과를 기록합니다. `--installer`, `--version`, `--commit`, `--run-id`, `--platform`을 함께 지정하며 실패한 감사는 BLOCKED로 남습니다. 승인 기록의 `audits`에는 각 플랫폼의 이 보고서 내용을 넣습니다. 감사 상태·오류·설치 파일 해시·버전·커밋·run ID가 맞지 않으면 draft 준비가 실패합니다. 검토한 동일 run의 두 설치 파일을 `packaging/release-approval.json`에 버전·커밋·run ID·SHA256으로 기록합니다. 예제는 `release-approval.example.json`입니다.
7. 후보 커밋에 버전 태그를 만들고 승인 기록이 있는 ref에서 `Prepare reviewed beta draft`를 실행합니다. 태그와 run 커밋, 두 설치 파일의 이름과 해시를 검증해 두 파일 및 SHA256SUMS를 draft prerelease로 모읍니다. 한 OS만 성공하면 동시 릴리스를 만들지 않습니다.
8. 소스 제공 및 두 설치 파일을 최종 확인한 다음 공개합니다.

## 베타 확인

- 일반 사용자 설치·실행, 시스템 Python/FFmpeg 없는 환경.
- 한국어·공백 경로, 분석·편집·PDF/JSON, 취소·재시도.
- 콘솔 깜빡임, 저장 완료 후 출력 폴더 `.lock`·임시 파일 정리.
- 강의 원본·사용자 출력·캐시·인증 정보가 패키지에 없음.
- 유료 서명·공증은 베타의 필수 조건이 아닙니다. 상태는 unsigned/ad-hoc, not notarized로 안내합니다. 관리자 실행은 Smart App Control의 차단을 해결하지 않습니다.
