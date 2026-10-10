# Mac 설치

지원 대상: Apple Silicon Mac (arm64). Intel Mac은 현재 지원하지 않습니다.

1. [베타 설치 파일](https://github.com/juhwan0628/slide-extractor-gui/releases/download/v0.4.10rc1/SlideExtractor-v0.4.10rc1-macOS-arm64.dmg)을 다운로드합니다.
2. DMG를 엽니다.
3. `SlideExtractor.app`을 Applications 폴더로 복사합니다.
4. Applications에서 앱을 실행합니다. Python·Qt·FFmpeg는 앱에 포함돼 있습니다.

현재 베타는 ad-hoc 서명이며 Apple 공증을 받지 않았습니다. “Apple could not verify…” 경고가 표시될 수 있습니다. 출처를 확인한 앱에 한해 실행을 시도한 후 시스템 설정 → 개인정보 보호 및 보안 → 해당 앱의 ‘확인 없이 열기’를 이용할 수 있습니다. 조직이 관리하는 Mac은 별도 정책이 적용될 수 있습니다.

처음에는 짧은 영상으로 분석 → 페이지 확인 → Save PDF를 실행해 보세요. [직접 빌드하는 개발자용 안내](packaging/BUILD_PERSONAL.md)는 별도입니다.

[Apple 공식 앱 실행 안내](https://support.apple.com/102445)
