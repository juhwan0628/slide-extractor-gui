# 네이티브 배포와 검사

공통 Python/Qt 소스에서 macOS arm64 DMG와 Windows x64 설치 EXE를 만듭니다.
현재 공개 승인 기록은 packaging/release-approval.json과 RELEASING.md에
버전·커밋·run·해시별로 보존합니다. 이전 승인으로 수정된 앱을 출고하지 않습니다.
M1–M4 안정화 변경의 새로운 네이티브 빌드·설치 검증은 M5에서 진행합니다.

## 현재 구성

- PyInstaller onedir/.app, Inno Setup EXE와 DMG. 플랫폼별 고정 lock과 native runner.
- PySide6-Essentials의 동적 Qt 라이브러리와 정확한 원본 소스·고지·교체 검사.
- 별도 FFmpeg/FFprobe 실행 파일. 공급 해시와 configure flags를 검사하며
  GPL/nonfree 설정의 개발 서버 바이너리는 배포에 복사하지 않습니다.
- OpenCV는 고정 소스의 이미지 전용 구성입니다. 배포 모듈에 videoio나 bundled
  FFmpeg·x264/x265가 다시 포함되면 검사에서 거부합니다.
- ReportLab·pypdf가 PDF 생성·검증을 담당합니다. PyMuPDF와 개발 전용 pytest는
  설치본에 포함하지 않습니다.
- OpenSSL 3.x 런타임이 발견되면 실제 버전·바이너리 해시와 전용
  licenses/OpenSSL-LICENSE.txt·RUNTIME-NOTICES.md의 경로·해시를 기록합니다.
  저장소의 검토 원문과 바이트가 다르거나 없으면 출고 검사를 실패시킵니다.
  NumPy/Python의 임의 Apache 문서는 대체 증거로 사용하지 않습니다.
- macOS ad-hoc·공증 없음, Windows unsigned가 합의한 베타 정책입니다.
  서명 상태 기록과 사용자 설치 안내는 유지합니다.

## 절차와 상태

[빌드와 테스트](BUILD_AND_TEST.md), [출고 절차](../RELEASING.md),
[검증 기록](QA_STATUS.md)을 확인하세요. 고정 소스·원문 라이선스·SBOM·설치본
해시·실행 검증은 유지하며 기술 출고 검사를 법적 인증서로 표현하지 않습니다.
초기의 RELEASE HOLD 문구와 검사 미완료 목록은 날짜가 붙은
[라이선스 감사 이력](../LICENSE_AUDIT.md)에서 당시 기록으로 구분합니다.
