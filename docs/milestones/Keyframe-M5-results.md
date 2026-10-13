# M5 — 0.5.0b1 네이티브 후보 검증

상태: M5 후보 검증 완료. 동일 후보의 Mac·Windows 빌드·설치·별도 출고 감사·최종 독립 리뷰 성공. 공개 릴리스 아님.

## 후보 식별

| 항목 | 값 |
|---|---|
| 앱 버전 / 네이티브 숫자 버전 | 0.5.0b1 / 0.5.0 |
| GitHub 설치본 후보 커밋 | `04849e137c198f619f851606014a667a814d4d40` |
| 대응하는 로컬 커밋 | `856d013d8322ad2cc567cb34f17a2a57105a0c49` |
| 두 후보의 동일 Git 트리 | `b93d63df573b3bd3de39a9e390cacf1e413ff66a` |
| 후보 네이티브 빌드 | [38286090517](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38286090517) |
| 같은 후보의 공통 소스 CI | [38286090268](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38286090268) |
| 별도 감사 커밋 | `24941686671c1e76237ae634ac09997e5bc47d1e` |
| 감사 / 검토 자료 CI | [38313742170](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38313742170) / [38313742096](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38313742096) |
| 브랜치 | release/keyframe-0.5-m5 |

앱·빌드 입력은 후보 이후 변경하지 않았습니다. 이후 커밋은 정확한 후보/감사 연결, 문서 및 배포 자료 정책의 테스트입니다. main과 기존 공개 릴리스는 유지합니다.

## 소스 및 설치본 검증

- 수정 후보 서버 전체: 833 passed in179.30s. 후보 GitHub Linux: 832 passed,1 skipped in73.26s.
- 최종 검토/배포 자료 정책까지 포함한 서버 전체: 847 passed in179.41s. 감사 커밋 CI38313742096은 Linux846 passed,1 skipped in73.98s이며 같은 Windows 잠금·캐시 검사도 성공했습니다. 최신 집중 검사58 passed in5.12s, exit0.
- Windows 출력 잠금: 7 passed,1 skipped. 캐시: 21 passed,1 skipped,2 deselected.
- 격리 FPS 기준선: 701 passed,6 skipped. 제품 런타임의 FPS 경로를 뜻하지 않습니다.
- 네이티브 Mac: 198 passed,2 skipped in22.10s. Windows: 197 passed,3 skipped in62.32s. 플랫폼 제외 항목을 성공 검사 수에 더하지 않습니다.
- 두 OS의 원본 번들, DMG/EXE 설치 앱, QtCore 문자열 교체 테스트 사본에서 빈 PATH 분석·편집·PDF 단독·상세v4/간단JSON·백그라운드 준비/재사용·Start over 캐시 정리·출력 잠금 정리와 공유 출고 계약 검증 성공.
- 다운로드한 두 candidate ZIP은 GitHub artifact digest와 일치합니다. 실제 보고서6개는 다시 공유 계약으로 검증했습니다.
- 실제 네이티브 파일 경로: Mac143개 / Windows137개. 다운로드한 원문 인벤토리 SHA는 기존 승인 구성과 동일합니다. 이것은 모든 라이브러리 바이너리 바이트가 같다는 의미가 아닙니다.
- actionlint 및 diff 공백 검사 성공.

## 원본 설치본 출고 감사

별도 감사38313742170: 두 OS PASSED, errors 없음. 원본 DMG/EXE를 새로 설치하고 실제 native 파일·FFmpeg 구성·대응 소스/패치·원문 고지/OpenSSL·Qt 교체 증거·공유 키프레임 계약을 대조했습니다. 다운로드한 감사 ZIP digest와 manifest/installer SHA도 다시 대조했습니다.

- Mac 감사 manifest SHA: `badbac8a8ff0680522497216faed751525c7495b436f7993445ccbc59eba1ee9`
- Windows 감사 manifest SHA: `9487bcef49341537217f0f81ff0222e04474f2cebfd8e62422702cf3f0ab5b08`
- release-approval.json은 VALIDATED_CANDIDATE, public_release_approved=false입니다. 후보 검증과 공개 승인은 구분합니다.
- 대응 소스·빌드 입력·원문 라이선스는 같은 native run의 native-inputs-macOS-ARM64 / native-inputs-Windows-X64 artifacts에 있으며 공개 릴리스 준비 시 Sources-Licenses.zip에 보존합니다.

## 실제 후보 설치 파일

GitHub artifact ZIP을 풀면 해당 설치 파일 하나가 있습니다. GitHub 로그인 필요, 현재 artifact 보관 기한은 2026-10-26 UTC입니다.

| 기기 | 후보 다운로드 | 설치 파일 크기 |
|---|---|---|
| Mac Apple Silicon | [DMG가 든 ZIP](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38286090517/artifacts/11763099370) | 84,815,404 bytes |
| Windows x64 | [설치 EXE가 든 ZIP](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38286090517/artifacts/11763976703) | 69,415,169 bytes |

Mac 파일: `SlideExtractor-v0.5.0b1-macOS-arm64-approved.dmg`
SHA256: `dc93248fa7954a6123daaafce7a0c494770735a772ac651db3bf1498104c4498`

Windows 파일: `SlideExtractor-v0.5.0b1-Setup-Windows-x64.exe`
SHA256: `0e63e6864f3ba2ec63eea0fac31901fc5f6a67523609e7e1bfdde5721858aa63`

DMG 이름의 approved는 기존 빌드 입력 명칭이며 공개 릴리스 승인 상태를 뜻하지 않습니다. 두 파일은 Python/FFmpeg 준비나 사용자 빌드가 필요 없는 설치 후보입니다. Mac은 앱을 Applications로 복사하고 Windows는 사용자 계정에 설치합니다.

## 재현 실패와 수정

초기 후보 `e27854e` / native38284876402는 Mac2건·Windows3건 실패하여 설치 파일을 만들지 못했습니다. 이 후보는 출고에서 제외합니다.

1. 배포 FFmpeg에는 PNG 입력 디코더가 없었습니다. GOP 테스트 합성 영상을 동일 A5초/B2초/A8초/C7초,5fps,MPEG4,GOP5/50 조건의 lavfi 색상 소스로 바꿨습니다. 관측/누락 판정은 유지하며 native RED → 두 OS GREEN입니다.
2. Windows 개발 벤치마크의 POSIX resource 의존성을 재현했습니다. 실제 분석/PDF 작업을 실행하는 모듈 부재 회귀 RED → GREEN이며 미지원 RSS는 null, Mac은 bytes를 KiB로 정규화합니다. 앱 의존성은 추가하지 않습니다.
3. 새 검증 도구가 Windows 개발용 ZIP에서 빠진 것을 기존 전체 회귀로 재현하고 포함했습니다.
4. 기존 배포 자료 정책이 후보의 b1 버전과 후속 M5 문서를 거부했습니다. 정확한 bN/rcN 형식 및 명시적 문서만 허용하도록 수정했습니다. 임의 버전 문자열, 앱/빌드/의존성 변경은 계속 차단합니다. 공개 승인 플래그는 false입니다.

## 남은 실제 기기 확인과 범위

- 실제 Mac/Windows에서 설치 후 사용자 강의 열기, 분석/편집, PDF 단독/JSON 저장과 Start over 확인.
- Mac 보안 경고·Windows Smart App Control 등 각 기기의 실행 정책은 hosted runner 성공으로 보장하지 않습니다.
- M4의 긴 GOP 누락, 마지막 관측 이후 필기 누락, 고페이지 원본 PDF 저장 비용 제한을 유지합니다. 이 문서는 모든 영상의 정확도나 native 성능 보장이 아닙니다.
- Mac ad-hoc 서명, Apple 공증 없음 / Windows unsigned. 유료 서명·Linux 배포는 이번 범위에 없습니다.
- 정확한 대응 소스·라이선스·원본 고지는 별도 감사에 연결합니다. 기술 검사는 법적 인증서가 아닙니다.

## 실행 중 결정

후보 브랜치/CI만 사용하고 main 병합·공개 릴리스는 수행하지 않습니다. GitHub Git API의 커밋 메타데이터가 달라 로컬/원격 대응은 동일 소스 트리로 증명합니다. 원격 skill 보조 스크립트가 없어 동등한 ledger·커밋·테스트 기록을 사용했습니다. 한 최종 리뷰어가 빌드 중 코드 검토를 시작했고 최종 판정은 실제 설치본 감사와 문서까지 기다립니다. b1 형식 문제는 필수 Sources-Licenses 자료 생성도 막아 이 M5에서 수정했습니다.

## 최종 리뷰와 결정의 한계

독립 리뷰: 남은 Critical/Important 없음. 계약40개, ZIP/빌드킷7개, 배포 정책·아카이브18개를 리뷰어도 실행했습니다. 최종 상태 기록 항목은 이 마무리에서 갱신했으며 미해결 코드 Minor는 없습니다.

| 결정 | 잘못 판단했을 때의 비용/제한 |
|---|---|
| M5는 후보 브랜치·CI만 포함하고 main·공개 릴리스는 유지 | 공개 개발 브랜치가 먼저 생기며 사용자는 아직 기존 안정 후보를 다운로드할 수 있음 |
| 원격 보조 스크립트 대신 동등한 ledger·검증·커밋 기록 사용 | 스크립트가 자동 생성하는 기록은 없음 |
| Git API의 서로 다른 커밋 메타데이터는 동일 트리로 연결 | 로컬/원격 SHA를 혼동하지 않고 별도로 추적해야 함 |
| 한 최종 리뷰어가 빌드 중 코드 검토를 시작하고 감사까지 기다림 | 후속 문서·감사 증거를 같은 리뷰어에게 공급해야 함; 완료함 |
| b1 버전도 필수 배포 자료를 만들 수 있도록 엄격한 bN/rcN 형식을 허용 | 허용 이름 형식이 늘지만 임의 문자열·앱/빌드 입력 변경은 차단 |
| 실제 기기 설치·OS 보안 정책은 사용자가 확인 | hosted runner 결과가 실제 기기 실행 성공을 보장하지 않음 |
| 모든 강의 정확도는 보장하지 않음 | 긴 GOP 등에서 누락이 있을 수 있음 |
| 임의 입력의 native 성능은 별도 검증 | 기기/입력에 따라 저장 시간·메모리 비용이 달라짐 |
| 라이선스 자료·설치 바이트 기술 감사는 법적 인증이 아님 | 별도 법적 판단은 제공하지 않음 |

## 배포 자료 준비 — 2026-10-13

사용자 실기기 확인은 아직 전입니다. main 병합·태그·공개 릴리스를 수행하지 않았으며 공개 승인false를 유지합니다.

- [Draft PR #1](https://github.com/juhwan0628/slide-extractor-gui/pull/1): 키프레임 전용 변경과 검증된 두 OS 후보의 main 통합 검토. 현재 main을 포함하는 브랜치로 통합 충돌이 없습니다.
- [후보 자료 준비38326933040](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38326933040): 기존 후보/감사/대응 소스의 정확한 바이트를 검증하고 네 파일 생성 성공. 공개 권한이나 릴리스 변경 명령이 없습니다.
- [대응 소스·라이선스 포함 후보 자료 ZIP](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38326933040/artifacts/11780983990): DMG, EXE, Sources-Licenses.zip, SHA256SUMS.txt 네 파일. 일반 설치에는 앞의 OS별 설치 ZIP만 사용하세요. 자료 artifact 보관 기한은2026-11-12 UTC입니다.
- 준비 워크플로 변경 후 서버847 passed180.24s, exit0; sourceCI38326933049 전체 작업 성공. App 및 native 빌드 입력은 변경하지 않았습니다.
- 연결 도구512MiB 한도보다 원본 소스 artifact가 커서, Actions에서 직접 받아 검증·조합했습니다. 압축 후 모든 원본 지원 자료의 바이트를 재검증합니다.

| 후보 파일 | bytes | SHA256 |
|---|---:|---|
| `SHA256SUMS.txt` | 329 | `9931d1f35b0229c086f93edb42ce263e977b2dfa0c7ccb79ca9da1eaef4badc4` |
| `SlideExtractor-v0.5.0b1-Setup-Windows-x64.exe` | 69415169 | `0e63e6864f3ba2ec63eea0fac31901fc5f6a67523609e7e1bfdde5721858aa63` |
| `SlideExtractor-v0.5.0b1-Sources-Licenses.zip` | 686543701 | `38250ec5b8cebd4be82bbb29f2c9107485310e3f75eed8b0ce2865405597f8b7` |
| `SlideExtractor-v0.5.0b1-macOS-arm64.dmg` | 84815404 | `dc93248fa7954a6123daaafce7a0c494770735a772ac651db3bf1498104c4498` |

## 사용자 실기기 확인 및 공개 승인 — 2026-10-13

사용자가 0.5.0 베타를 두 운영체제에서 정상 동작 확인했다고 보고했고, 이어서 실제 공개 배포를 명시적으로 지시했습니다. 위의 "실기기 확인 전" 및 public_release_approved=false 기록은 당시 후보 준비 상태의 이력입니다. 현재 승인은 APPROVED/public_release_approved=true입니다. 기존 후보 DMG·EXE의 해시와 앱·빌드 입력은 유지하며 main 통합 후 공개 워크플로에서 다시 검증합니다. 특정 추가 기능별 실기기 검사를 별도로 수행했다는 주장은 하지 않습니다.
