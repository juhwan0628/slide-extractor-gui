# Slide Extractor GUI

로컬 강의 영상의 슬라이드 전환을 분석하고, 타임라인에서 페이지를 편집한 뒤 PDF로 저장하는 데스크톱 앱입니다.

기존 CLI [slide-extractor](https://github.com/juhwan0628/slide-extractor)와 별도 프로젝트입니다.
맥과 Windows는 **같은 소스·같은 버전**을 사용합니다.

## 설치와 배포 상태

목표 배포 파일은 Apple Silicon Mac용 `.dmg`, Windows x64용 설치 `.exe`입니다. 필요한 Python·Qt·FFmpeg·FFprobe를 포함합니다.
현재 `0.4.9rc1`은 베타 후보이며 **이 저장소용 공개 설치 파일은 아직 생성·검증되지 않았습니다.**
GitHub Actions와 동시 릴리스 준비 절차는 [RELEASING.md](RELEASING.md)를 참고하세요.
베타는 유료 서명·공증 없이 준비하므로 OS에 따라 경고나 실행 차단이 발생할 수 있습니다.

## 사용 흐름

1. 영상을 불러와 분석합니다. CPU 멀티스레드·프레임 메타데이터를 기본으로 사용합니다.
2. 타임라인에서 페이지 추가·제거·복원·분할·병합과 대표 프레임 변경을 수행합니다.
3. PDF 또는 PDF와 프로젝트 JSON을 저장합니다. 기존 파일 덮어쓰기는 승인 후 수행합니다.

## 개발 실행

Python 3.12와 FFmpeg/FFprobe가 필요합니다. 최종 설치본 사용자는 이 절차를 수행하지 않습니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

Windows 개발 환경에서는 `.venv\Scripts\python.exe`를 사용합니다.

## 테스트

```bash
python -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen PYTHONPATH=. python -m pytest -q
```

테스트 영상은 합성 데이터로 생성합니다. 강의 원본이나 추출된 교안은 저장소에 포함하지 않습니다.
성능 개선의 상세 기록과 실제 플랫폼별 검증 상태는 [packaging/QA_STATUS.md](packaging/QA_STATUS.md)를 참고하세요.

## 구조

- `gui/`: 공통 Qt GUI.
- `slide_core/`: 분석·편집·캐시·PDF 저장.
- `packaging/`: 고정 빌드 입력, DMG/EXE, 라이선스 자료 및 릴리스 검사.
- `.github/workflows/`: 공통 테스트, 네이티브 후보 빌드, 검토된 동시 draft 릴리스.
- `tests/`: 회귀·통합·동시성 검증.

## 이용과 라이선스

사용자가 처리 권한을 가진 로컬 영상을 입력해 사용합니다. 강의 영상·교안 또는 LMS 접근 제어 우회 기능을 배포하지 않습니다.
앱 자체의 오픈소스 라이선스는 아직 선택되지 않았습니다. 공개 시 별도 `LICENSE`를 확정해야 합니다.
제3자 의존성 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), 배포 입력 검토는 [LICENSE_AUDIT.md](LICENSE_AUDIT.md)를 참고하세요.
