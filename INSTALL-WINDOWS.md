# Windows 개인용 자동 빌드 — 0.4.9rc1

Python 3.12 64비트와 Python launcher를 준비한 뒤 BUILD-WINDOWS.bat를 더블클릭합니다.
FFmpeg/FFprobe 다운로드, 해시 확인, 폴더 생성, 패키지 설치, exe 생성, 번들 검증을 자동 처리합니다. 수동 파일 복사나 vendor 폴더 생성은 필요하지 않습니다.
첫 실행에는 인터넷이 필요합니다. 다운로드를 마친 도구는 다음 빌드에서 해시 확인 후 재사용합니다.

간편 키트에서는 결과가 바깥 output 폴더에 생성됩니다.
그 안의 SlideExtractor-v0.4.9rc1-Windows-x64-personal.zip을 새 폴더에 풀고 VALIDATE-WINDOWS.bat를 실행한 뒤 SlideExtractor.exe를 실행하세요.
exe 옆 _internal 폴더도 함께 유지합니다. 완성 앱 실행에는 별도 Python/FFmpeg가 필요하지 않습니다.

대표·긴 강의로 분석→편집→PDF 단독/JSON 동시 저장, 취소, 재실행·캐시 재사용을 확인하세요.
문제가 생기면 _app/build/personal-windows/build.log와 installed-smoke.json, 또는 완성 앱 폴더의 validation-smoke.json을 보내주세요.

이 키트는 개인 검증용이며 실제 Windows 네이티브 빌드 성공은 사용자 기기에서 확인해야 합니다.
