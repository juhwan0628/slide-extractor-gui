# Slide Extractor 0.4.11rc1 베타

강의 영상에서 슬라이드 전환을 분석하고, 타임라인에서 페이지를 편집해 PDF로 저장합니다.

## 다운로드

| 기기 | 다운로드 |
|---|---|
| Apple Silicon Mac | **[Mac DMG 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.11rc1/SlideExtractor-v0.4.11rc1-macOS-arm64.dmg)** |
| Windows x64 | **[Windows 설치 EXE 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.11rc1/SlideExtractor-v0.4.11rc1-Setup-Windows-x64.exe)** |

**자기 기기에 맞는 설치 파일 하나만 받으면 됩니다.**

- Apple Silicon Mac: `.dmg`를 열고 앱을 Applications로 복사합니다.
- Windows x64: `Setup-Windows-x64.exe`를 실행합니다. 사용자 계정 폴더에 설치하며 관리자 권한을 요구하지 않습니다.
- Python과 FFmpeg는 포함되어 있습니다. 직접 설치하거나 빌드할 필요가 없습니다.

## 이번 버전의 수정

- 영상 선택 시 샘플 프레임을 백그라운드에서 준비합니다. Analyze를 누르면 진행 중인 준비를 이어받거나 완료된 프레임을 재사용합니다.
- 긴 영상의 정상 디코딩을 총 실행 시간으로 중단하지 않고, 진행이 멈춘 시간을 기준으로 타임아웃을 판단합니다.
- 기본 분석 간격을 0.5 FPS로 설정합니다. 1 FPS로 올릴 때는 기존 준비를 취소·정리하고 다시 준비하며, 완료된 1 FPS 캐시를 0.5 FPS로 낮출 때는 재디코딩 없이 불필요한 프레임을 정리합니다.
- 분석 설정과 저장 옵션을 분리합니다. 결과 화면의 Save options…에서 JSON 설정을 바꿔도 편집 내용은 유지됩니다.
- Start over로 현재 작업과 임시 캐시를 정리하고 영상 선택 화면으로 돌아갑니다. 이미 저장한 출력 파일은 유지합니다.

## 기존 주요 기능

- Shift 범위 선택, Ctrl/Cmd 개별 선택, 전체 선택과 선택 개수 표시.
- 우클릭 Merge는 선택 중 마지막 시점의 원본 페이지를 남기며 나머지 선택 페이지를 제거합니다. 선택하지 않은 페이지는 유지합니다.
- 선택 페이지 일괄 삭제와 최대 100회 Undo/Redo. 페이지·선택·포커스·프리뷰 위치를 복원합니다.
- 페이지 목록에서 Ctrl/Cmd+M, Delete/Backspace, Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z 지원. Windows는 Ctrl+Y도 지원합니다.
- 자동 분석은 유지하며 필기·페이지 재방문의 자동 처리 개선은 향후 연구 과제로 남겨둡니다.

- CPU 멀티스레드·프레임 메타데이터를 활용한 분석 및 PDF 추출 개선.
- Windows 외부 도구 콘솔 깜빡임과 PDF 저장 오류 수정.
- PDF 단독 저장 후 남던 `.lock` 수정. 정상 저장·반복 덮어쓰기·게시 실패·취소 시 출력 잠금을 정리합니다.
- PDF+JSON 저장과 같은 안전한 잠금 정리 및 동시 저장 보호를 사용합니다.

- 앱 소스에 MIT 라이선스 적용, 앱 내 About / Licenses 안내 추가.
- macOS OpenCV wheel의 불필요한 GPL 코덱을 제거하고 두 OS 모두 이미지 전용 OpenCV 소스 빌드 사용.
- 원본 라이선스, 대응 소스, 빌드 설정·패치·해시 및 Qt 라이브러리 교체 검사 기록 제공.

## 베타 제한

유료 코드 서명·macOS 공증을 적용하지 않은 후보입니다. OS 보안 설정에 따라 경고 또는 실행 차단이 발생할 수 있으며 관리자 실행으로 해결된다고 보장하지 않습니다.
분석은 기본 0.5 FPS이므로 짧은 전환이나 특이한 화면 구성은 직접 검토가 필요합니다.
지원 대상은 macOS arm64와 Windows x64이며 Intel Mac과 Windows ARM은 이번 후보 대상이 아닙니다.


## 개발·라이선스 자료

[대응 소스·라이선스·검증 자료 ZIP](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.11rc1/SlideExtractor-v0.4.11rc1-Sources-Licenses.zip) · [SHA-256 해시](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.11rc1/SHA256SUMS.txt)

자료 ZIP은 일반 설치에 필요하지 않습니다. Qt·FFmpeg 등 정확한 원본 소스, OpenCV 수정 패치, 두 OS의 라이선스·빌드·출고 검사 기록과 FFmpeg 빌드 입력을 모았습니다. 내부 README와 docs/SOURCE_AND_REPLACEMENT.md에서 구성과 라이브러리 교체 방법을 확인할 수 있습니다. 원래 자료의 바이트와 해시는 보존됩니다.

GitHub가 자동으로 제공하는 **Source code ZIP / tar.gz**는 앱 저장소 소스입니다. 외부 라이브러리의 대응 소스는 위 자료 ZIP에 있습니다.


## 검증 기록

서버 소스 검사 655개 통과. 동일 소스 GitHub Linux 검사 649개 통과·6개 플랫폼 전용 제외, Windows 캐시 21개와 출력 잠금 7개 통과. Mac·Windows 새 디코딩/캐시/설정 검사 각 35개 통과. 두 OS의 번들·DMG/EXE 설치본·QtCore 교체 설치본에서 백그라운드 준비, 저장 옵션 변경, 캐시 정리, 수동 편집과 PDF/JSON 저장을 검증했습니다. 별도 원본 설치본 출고 감사도 두 OS 모두 통과했습니다. [검증 상세](https://github.com/juhwan0628/slide-extractor-gui/blob/main/packaging/QA_STATUS.md).
