# Slide Extractor 0.5.0b1 베타

강의 영상의 디코더 키프레임에서 슬라이드 변화를 찾아 필요한 페이지를 PDF로 저장합니다.

## 다운로드

| 기기 | 설치 파일 |
|---|---|
| Apple Silicon Mac | [DMG 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b1/SlideExtractor-v0.5.0b1-macOS-arm64.dmg) |
| Windows x64 | [설치 EXE 다운로드](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b1/SlideExtractor-v0.5.0b1-Setup-Windows-x64.exe) |

자기 기기에 맞는 설치 파일 하나만 받으면 됩니다. Python·Qt·FFmpeg·FFprobe는 포함돼 있습니다. Mac은 앱을 Applications로 복사하고, Windows는 설치 EXE를 실행합니다.

동일 후보의 두 OS 설치 검증·별도 출고 감사·독립 리뷰를 통과했으며, 사용자가 두 운영체제 실기기 정상 동작을 확인했습니다. 검증된 동일 DMG·EXE를 공개합니다.

[대응 소스·라이선스·검증 자료 ZIP](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b1/SlideExtractor-v0.5.0b1-Sources-Licenses.zip) · [SHA-256](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.5.0b1/SHA256SUMS.txt)

## 변경 사항

- 시간 간격(FPS) 샘플링을 제품에서 제거하고 키프레임 전용으로 통일했습니다. FPS 기준선은 별도 개발 검증 도구에만 남습니다.
- 영상 선택 시 조용히 백그라운드에서 준비합니다. Analyze는 같은 준비 작업을 이어받거나 완료 캐시를 재사용합니다.
- 타임라인 추가·교체·Merge는 관측된 키프레임을 사용합니다. Merge는 선택한 페이지 중 마지막 시점의 대표 페이지를 유지합니다.
- 상세 JSON은 관측 순번·원본 정수 PTS·time_base와 전환 구간을 기록하는 v4 형식입니다. 기존 FPS/v3 형식과 호환되지 않습니다. 간단 JSON도 선택할 수 있습니다.
- PDF는 선택한 키프레임을 원본 해상도에서 정확한 PTS로 추출합니다.
- 기존 분석/저장 옵션 분리, Start over, Undo/Redo, 출력 잠금 정리와 Windows 콘솔 숨김을 유지합니다.
- 설치본 검사에서 키프레임 전용 경로·새 JSON·편집·캐시·출력 검증이 누락되면 후보를 거부합니다.

## 실영상 검증과 제한

서버 M4 검증은 실제 강의 비교36회와 792회 회귀 검사에 성공했습니다. 디코딩 null 대조에서 FFmpeg CPU 비용이 약64~79% 감소했지만 전체 준비·분석 시간 개선폭은 작고 환경에 따라 다릅니다. 프레임 수 증가로 캐시·변화 탐지 비용이 늘 수 있습니다. 이 값은 Mac/Windows 설치본 성능을 뜻하지 않습니다.

키프레임은 의미상 슬라이드 전환과 다릅니다. 키프레임 간격이 긴 영상의 짧은 장면이나 마지막 관측 이후 필기는 누락될 수 있습니다. 커서·애니메이션·누적 필기는 추가 페이지로 잡힐 수 있어 수동 Merge·삭제가 필요합니다. 페이지 수가 많은 원본 해상도 PDF는 저장 시간과 메모리를 많이 사용합니다.

Mac은 ad-hoc 서명만 하고 Apple 공증은 적용하지 않습니다. Windows는 unsigned입니다. 실제 기기의 보안 경고·실행 정책은 hosted runner 성공으로 보장하지 않습니다. 지원 대상은 macOS ARM64와 Windows x64이며 Linux/Intel Mac/Windows ARM 배포는 이번 범위가 아닙니다.

앱 코드는 MIT이며 제3자 라이선스는 별도로 적용됩니다. 정확한 대응 소스·라이선스·빌드·감사 자료는 설치본과 함께 제공합니다.


## 검증 기록

서버 전체 847개, Mac 198개, Windows 197개 검사 통과 기록과 설치본 감사에 연결했습니다. [전체 검증·후보 해시](https://github.com/juhwan0628/slide-extractor-gui/blob/main/docs/milestones/Keyframe-M5-results.md).
