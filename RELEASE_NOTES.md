# Slide Extractor 0.5.0b2 베타

강의 영상의 키프레임만 디코딩해 슬라이드를 추출하고, 필요한 페이지를 편집해 PDF로 저장합니다.

## 다운로드

| 기기 | 설치 파일 |
|---|---|
| Apple Silicon Mac | [DMG 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b2/SlideExtractor-v0.5.0b2-macOS-arm64.dmg) |
| Windows x64 | [설치 EXE 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b2/SlideExtractor-v0.5.0b2-Setup-Windows-x64.exe) |

기기에 맞는 설치 파일 하나만 받으면 됩니다. Python·Qt·FFmpeg·FFprobe·전용 키프레임 디코더를 포함합니다.

[대응 소스·라이선스·재링크·검증 자료](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b2/SlideExtractor-v0.5.0b2-Sources-Licenses.zip) · [SHA-256](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b2/SHA256SUMS.txt)

## 변경 사항

- H.264 전용 디코더를 동봉합니다. 패킷 검사에서 GOP가 2초 미만이면 키프레임을 절반만 디코딩하고, 2초 이상이면 전부 사용합니다. 지원하지 않는 입력은 CPU 키프레임 경로를 사용하며 FPS/P·B 프레임 샘플링을 사용하지 않습니다.
- 필기·포인터 등 국소 변화는 같은 페이지로 묶고, 잠깐 나타나는 큰 화면 변화도 보존하도록 검출을 개선했습니다.
- 분석에 사용하지 않은 키프레임도 전체 편집 목록에 남습니다. 미리보기·추가·교체 시 필요한 프레임을 정확한 PTS로 복원합니다.
- half의 전체 편집 인덱스와 분석 관측 구분은 상세 JSON v7로 기록합니다. 간단 JSON과 기존 상세 JSON 읽기도 유지합니다.
- Windows 한글 영상 경로와 Mac 기본 Bash 빌드 호환 문제를 수정했습니다.

## 검증 범위와 알려진 한계

두 OS 후보에서 설치 후 번들 도구만으로 half 분석·지연 복원·편집·내보내기·Qt 교체 실행을 검증합니다. 실제 사용자 기기의 긴 강의 처리 시간은 별도 측정 대상입니다. 서버 반복 측정에서 이전 CPU/all 대비 약57~59% 시간 감소를 관측했지만, 이는 이전 FFmpeg6 서버 조건이며 새 설치본의 성능 보장은 아닙니다.

half에서 건너뛴 키프레임에만 잠깐 나타난 슬라이드는 자동 검출에서 누락될 수 있습니다. 전체 키프레임 편집 목록에서 수동 추가할 수 있으며 자동 복구와 슬라이드 회귀 식별은 아직 구현하지 않았습니다. Mac은 ad-hoc 서명, Windows는 미서명 베타입니다.
