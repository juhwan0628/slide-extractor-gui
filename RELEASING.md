# 맥·Windows 동시 베타 배포

대상 저장소: `juhwan0628/slide-extractor-gui` (CLI 저장소와 별도).
공통 소스와 `slide_core/version.py` 한 곳에서 버전을 관리합니다.
최종 사용자 파일은 macOS Apple Silicon `.dmg`, Windows x64 설치용 `.exe`입니다.
FFmpeg·FFprobe·Python·Qt를 포함하므로 최종 사용자는 개발 환경을 준비하지 않습니다.

## 현재 준비와 남은 조건

- 공통 소스 CI, 네이티브 후보 빌드, 두 설치 파일을 검증해 모으는 수동 draft 릴리스 워크플로를 준비했습니다.
- 현재 서버 테스트와 사용자가 수행한 Windows 개인용 빌드는 GitHub Actions 실행 결과가 아닙니다.
- 공개 배포용 media 입력·대응 소스·라이선스 자료와 GUI 자체 소스 라이선스 선택은 남아 있습니다.
- 개인용 Gyan GPL FFmpeg를 승인 LGPL 입력으로 바꾸어 부르거나 `NOT_APPROVED`를 무조건 승인으로 바꾸지 않습니다.
- 베타에서 유료 서명·공증을 필수로 요구하지 않습니다. 서명 상태는 `unsigned/ad-hoc, not notarized`로 명시합니다. 관리자 설치는 Smart App Control을 해결하지 않습니다.

## 순서

1. 새 저장소에 공통 소스를 올리고 `Common source tests`를 실행합니다.
2. 두 OS의 배포용 FFmpeg/FFprobe, 고정 해시, 정확한 대응 소스, 라이선스 사본, SBOM, Qt 교체·소스 안내를 준비합니다. 기존 `packaging/README.md`의 입력 조건을 따릅니다.
3. 같은 저장소의 workflow run에 `approved-native-inputs-macOS-ARM64`, `approved-native-inputs-Windows-X64` 아티팩트를 준비합니다. `binary-manifest.json`은 검토된 실제 입력만 기록합니다. 이는 개발·CI 단계이며 사용자에게 폴더 생성을 요구하지 않습니다.
4. `Native installer candidates`를 해당 run ID로 실행합니다. 두 러너에서 각각 빌드하고 빈 PATH로 분석·PDF smoke, 실제 설치·DMG 복사본 smoke를 수행합니다. 공개 게시하지 않습니다.
5. 실제 빌드 입력/번들 감사와 설치 테스트를 검토합니다. 공급 입력 manifest와 최종 후보의 관찰 해시는 다르므로 해당 감사 기록을 정확한 후보에 맞춰 준비해야 합니다. 이 워크플로는 검사 실패를 성공으로 간주하지 않습니다.
6. `packaging/release-approval.example.json`을 기반으로 검토한 **동일 run의 두 설치 파일** 해시·버전·커밋을 `packaging/release-approval.json`에 기록합니다. 자료·동작 확인을 끝낸 뒤에만 `APPROVED`로 표시합니다.
7. 검토한 빌드의 커밋에 `v0.4.9rc1` 태그를 생성합니다. 승인 기록은 별도 후속 커밋이어도 됩니다.
8. 승인 기록이 있는 ref에서 `Prepare reviewed beta draft`를 실행합니다. run ID·태그·버전·커밋·해시를 확인하고 두 설치 파일과 `SHA256SUMS.txt`를 포함하는 **draft prerelease**를 만듭니다.
9. 두 설치 파일과 안내를 최종 확인한 다음 draft를 공개합니다. 한 OS만 성공한 상태에서는 동시 릴리스를 생성하지 않습니다.

## 베타 확인 항목

- 일반 사용자 설치/실행, Python/시스템 FFmpeg 없는 환경.
- 한국어·공백 경로, 영상 분석·편집·PDF/JSON 저장, 취소·재시도.
- 콘솔 창 깜빡임, 저장 완료 후 출력 폴더 `.lock`·임시 파일 정리.
- 맥 Gatekeeper와 Windows Smart App Control의 실제 동작 기록.
- 강의 원본·PDF·JSON·캐시·환경·인증 정보가 소스/설치 패키지에 없음.
