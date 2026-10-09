# 개인용 빌드 도구

완성된 DMG/EXE를 설치하려면 루트의 INSTALL-MAC.md 또는 INSTALL-WINDOWS.md를 참고하세요. 아래 도구는 개발·개인 검증용입니다.

## Mac

네이티브 arm64 Python 3.12와 로컬 FFmpeg를 준비하고 저장소 루트에서 `bash scripts/build-macos-personal.command`를 실행합니다. 결과와 검사 기록은 `dist/`, `build/personal/`에 생성됩니다.

## Windows

Python 3.12 64비트와 Python launcher를 준비한 뒤 저장소 루트의 `BUILD-WINDOWS.bat`를 실행합니다. 개인용 FFmpeg 입력을 자동으로 준비하고 빌드합니다. 이는 GitHub Actions의 소스 컴파일 배포 입력과 다릅니다.

완성 앱은 실행할 때 Python이나 FFmpeg를 별도 설치하지 않습니다. 개인용 빌드 도구는 호환성을 위해 유지하며, GitHub 설치 파일에는 포함하지 않습니다.
