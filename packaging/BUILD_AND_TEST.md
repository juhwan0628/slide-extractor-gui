# 빌드와 검증

사용자는 GitHub Releases에서 macOS Apple Silicon DMG 또는 Windows x64 설치
EXE를 받습니다. 일반 사용자에게 Python 설치나 직접 빌드를 요구하지 않습니다.

## 공통 개발·테스트

저장소를 checkout하고 Python 3.12 가상환경에서 requirements-dev.txt를
설치한 뒤 QT_QPA_PLATFORM=offscreen python -m pytest -q를 실행합니다.
Linux 검증 lock과 macOS/Windows 빌드 lock은 구분합니다.

## 네이티브 후보와 출고

.github/workflows/native-build-template.yml은 main의 지정 빌드 입력 변경 또는
workflow_dispatch로 실행됩니다. 두 OS의 고정 runtime lock, 원본 소스와 패치,
이미지 전용 OpenCV, 공급 FFmpeg 해시·설정, 라이선스·SBOM을 검사합니다.
현재 FFmpeg 입력 복원은 workflow에 명시한 기존 run을 사용하므로, 보관 만료 시
검증된 공급 입력을 다시 준비해야 합니다.

번들·설치 DMG/EXE·빈 PATH·QtCore 교체 검사를 통과한 동일 후보를
candidate-license-audit.yml에서 다시 검사합니다. 승인 자료는 그 버전·커밋·run·
설치 파일 해시에만 적용합니다. 재빌드하면 다시 검사해야 합니다.
출고와 소스·라이선스 에셋 구성은 [RELEASING](../RELEASING.md)을 따릅니다.

합의한 베타 정책은 macOS ad-hoc 서명·공증 없음, Windows unsigned입니다.
Developer ID·유료 Windows 코드 서명은 이번 베타의 필수 조건이 아닙니다.
사용자 보안 경고와 우회 안내는 운영체제별 설치 문서를 확인하세요.
호스팅 runner의 성공은 모든 실기기의 보안 정책 통과를 보장하지 않습니다.

## 유지하는 개인 평가 경로

scripts/build-macos-personal.command와 BUILD-WINDOWS.bat는 개발자의 개인
검증용입니다. 검토된 공식 설치 파일을 대신하는 공개 출고 경로가 아닙니다.
python packaging/build_source_zip.py OUTPUT.zip으로 소스 평가 ZIP을 만들고,
--include-tests를 추가하면 개발 테스트도 포함합니다. Windows 전용 평가
빌드킷은 python packaging/build_windows_kit.py OUTPUT.zip입니다.
두 ZIP은 LICENSE와 공통 spec의 필수 소스 자료를 포함하며, 네이티브 FFmpeg·Qt
바이너리를 이미 승인한 완성 설치 파일로 표현하지 않습니다.
사용자에게 배포하는 기본 다운로드는 DMG/EXE입니다.

## 프로파일

영상 선택 후 준비 작업은 preparation-UUID.json, Analyze 작업은
analysis-UUID.json에 기록합니다. 준비 전체 시간은 이미 UI 설정 시간과
겹치므로 Analyze 대기와 합산하지 않습니다. seconds.total은 검출 파이프라인,
preparation_wait는 Analyze 후 남은 준비 대기, click_to_result_total은 버튼
클릭부터 결과 생성까지입니다. GUI 렌더링·보고서 디스크 기록은 결과 생성
이후이므로 후자의 범위에 포함하지 않습니다.
실패·취소는 상태와 예외 종류로 기록하며 영상 경로와 예외 전문은 넣지 않습니다.
프로파일은 로컬 진단 파일이며 업로드하지 않습니다.
