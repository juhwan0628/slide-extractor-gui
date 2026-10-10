# Slide Extractor 0.4.9rc3 베타

강의 영상에서 슬라이드 전환을 분석하고, 타임라인에서 페이지를 편집해 PDF로 저장합니다.

## 다운로드

| 기기 | 다운로드 |
|---|---|
| Apple Silicon Mac | **[Mac DMG 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.9rc3/SlideExtractor-v0.4.9rc3-macOS-arm64.dmg)** |
| Windows x64 | **[Windows 설치 EXE 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.9rc3/SlideExtractor-v0.4.9rc3-Setup-Windows-x64.exe)** |

**자기 기기에 맞는 설치 파일 하나만 받으면 됩니다.**

- Apple Silicon Mac: `.dmg`를 열고 앱을 Applications로 복사합니다.
- Windows x64: `Setup-Windows-x64.exe`를 실행합니다. 사용자 계정 폴더에 설치하며 관리자 권한을 요구하지 않습니다.
- Python과 FFmpeg는 포함되어 있습니다. 직접 설치하거나 빌드할 필요가 없습니다.

## 변경 사항

- CPU 멀티스레드·프레임 메타데이터를 활용한 분석 및 PDF 추출 개선.
- Windows 외부 도구 콘솔 깜빡임과 PDF 저장 오류 수정.
- PDF 단독 저장 후 남던 `.lock` 수정. 정상 저장·반복 덮어쓰기·게시 실패·취소 시 출력 잠금을 정리합니다.
- PDF+JSON 저장과 같은 안전한 잠금 정리 및 동시 저장 보호를 사용합니다.

- 앱 소스에 MIT 라이선스 적용, 앱 내 About / Licenses 안내 추가.
- macOS OpenCV wheel의 불필요한 GPL 코덱을 제거하고 두 OS 모두 이미지 전용 OpenCV 소스 빌드 사용.
- 원본 라이선스, 대응 소스, 빌드 설정·패치·해시 및 Qt 라이브러리 교체 검사 기록 제공.

## 베타 제한

유료 코드 서명·macOS 공증을 적용하지 않은 후보입니다. OS 보안 설정에 따라 경고 또는 실행 차단이 발생할 수 있으며 관리자 실행으로 해결된다고 보장하지 않습니다.
분석은 기본 1 FPS이므로 짧은 전환이나 특이한 화면 구성은 직접 검토가 필요합니다.
지원 대상은 macOS arm64와 Windows x64이며 Intel Mac과 Windows ARM은 이번 후보 대상이 아닙니다.


## 개발·라이선스 자료

[대응 소스·라이선스·검증 자료 ZIP](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.9rc3/SlideExtractor-v0.4.9rc3-Sources-Licenses.zip) · [SHA-256 해시](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.9rc3/SHA256SUMS.txt)

자료 ZIP은 일반 설치에 필요하지 않습니다. Qt·FFmpeg 등 정확한 원본 소스, OpenCV 수정 패치, 두 OS의 라이선스·빌드·출고 검사 기록과 FFmpeg 빌드 입력을 모았습니다. 내부 README와 docs/SOURCE_AND_REPLACEMENT.md에서 구성과 라이브러리 교체 방법을 확인할 수 있습니다. 원래 자료의 바이트와 해시는 보존됩니다.

GitHub가 자동으로 제공하는 **Source code ZIP / tar.gz**는 앱 저장소 소스입니다. 외부 라이브러리의 대응 소스는 위 자료 ZIP에 있습니다.
