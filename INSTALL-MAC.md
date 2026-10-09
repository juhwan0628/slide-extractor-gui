# Apple Silicon 개인용 설치 후보 0.4.9rc1

1. ZIP을 새 폴더에 풀어 기존 프로젝트·가상환경과 분리합니다.
2. 네이티브 arm64 Python 3.12와 FFmpeg를 준비합니다. 기존 0.4.8 빌드에 사용한 환경을 그대로 사용할 수 있습니다.
3. Finder에서 `scripts/build-macos-personal.command`를 실행합니다. 실행 권한이 없으면 터미널에서 `bash scripts/build-macos-personal.command`를 실행하세요.
4. 번들 Qt·FFmpeg·분석·PDF smoke 검사가 통과하면 `dist/SlideExtractor-v0.4.9rc1-macOS-arm64-personal.dmg`가 만들어집니다.
5. 앱을 Applications로 옮기고 **Applications의 앱**을 실행합니다.

빌드 기록은 `build/personal/build.log`, `build-manifest.json`, `installed-smoke.json`에 남습니다. 해시는 DMG 옆 `.sha256` 파일에 기록됩니다. 빌더는 별도 `.venv-native-049rc1` 환경을 만듭니다.

설치 후 대표 강의로 분석→편집→PDF 단독/JSON 동시 저장을 확인하세요. 다시 열어 캐시 재사용, 분석·저장 중 취소, 기존 파일 덮어쓰기도 확인하세요. [설치 검증 체크리스트](packaging/QA_STATUS.md)에 기록할 항목이 있습니다.

이 개인용 앱은 로컬 FFmpeg를 사용하며 Apple Developer 서명/notarization 완료 제품이 아닙니다. 공개 배포는 별도의 승인된 입력과 검증이 필요합니다.
