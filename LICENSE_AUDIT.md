# Slide Extractor GUI — 배포 라이선스 사전 감사
검토일: 2026-10-08. 목적: 비상업적 GitHub Releases (Windows x64 onedir+Inno Setup; macOS arm64 .app/.dmg). 범위는 현재 소스·requirements 및 Oracle 개발환경에 설치된 바이너리. **아직 Windows/macOS 실제 릴리스 아티팩트가 없으므로 최종 바이너리 구성품 감사는 미완료. 이 문서는 법률 자문이 아니다.**

## 결론 및 출고 게이트
**조건부 배포 가능 / 현 단계 RELEASE HOLD**. 전체 기술 스택을 교체할 이유는 없다. 다만 FFmpeg 빌드 선정, Qt LGPL 의무 이행, 플랫폼별 전이 의존성·라이선스 파일 고정, 릴리스 패키지 검사 없이는 규정 준수를 확정할 수 없다.

## 서버 측 실물 확인
- FFmpeg / ffprobe: Ubuntu 6.1.1-3ubuntu5, '--enable-gpl', '--enable-libx264', '--enable-libx265', '--enable-libsvtav1', '--enable-libdav1d', '--enable-shared'. 이는 GPL 기능을 포함한 **개발 서버 실행 바이너리**이며 목표 Windows/macOS 배포 바이너리와 다르다. 서버 바이너리를 그대로 배포용으로 사용하지 말 것.
- qpdf 11.9.0; 해당 프로그램은 Apache-2.0. qpdf 바이너리에 링크되는 제3자 라이브러리는 선택한 릴리스 파일을 기준으로 별도 검사.
- 분석 소스에 직접 PyMuPDF import 없음; 현재 GUI PDF 생성은 ReportLab. 개발 테스트 가상환경에 pymupdf 1.28.2가 **남아 있지만** requirements.txt 및 GUI import 의존성에는 없음. PyInstaller 빌드에서는 불필요한 개발 가상환경을 쓰지 말고 깨끗한 release venv를 사용해 의도치 않은 동봉을 방지.
- `opencv-python-headless` wheel에는 LGPL v2.1 FFmpeg 포함(공식 PyPI 설명). wheel 내부 `LICENSE-3RD-PARTY.txt` 및 플랫폼별 FFmpeg 통합을 검증할 것.
- 현 requirements는 범위 지정('>=')으로 고정되지 않음. 릴리스용 플랫폼별 lock/SBOM 생성 필수.

## 직접 의존성과 전이 의존성
| 구성 | 현재 시험 환경 버전 | 확인된 주요 라이선스·고지 | 출고 판단 |
|---|---|---|---|
| Python 인터프리터 | 3.12.3 | PSF/관련 저작권 notice | 가능; 동봉된 표준 라이브러리 라이선스 포함 |
| numpy | 2.5.3 | BSD-3-Clause 및 vendored notices | 가능, wheel의 LICENSE 확인 |
| opencv-python-headless / OpenCV | 5.0.0.93 | Python packaging MIT, OpenCV Apache-2.0, bundled FFmpeg LGPL2.1 + third-party | 가능; 플랫폼 wheel의 LICENSE-3RD-PARTY 필수 |
| Pillow | 12.3.0 | HPND/MIT-CMU 및 bundled library notices | 가능; wheel 포함 이미지 코덱 라이선스 확인 |
| reportlab | 5.0.1 | BSD style | 가능; LICENSE notice 포함 |
| scikit-image | 0.26.0 | BSD-3-Clause/하위 파일별 notice | 가능; 다만 현재 호출은 사용되지 않는 SSIM 함수만이므로 제거 추천 |
| scipy | 1.18.1 | BSD-3-Clause 및 일부 전이 라이선스 | 가능; scikit-image 제거 시 제거 가능한지 확인 |
| PySide6/Qt, PySide6_Essentials/Addons, shiboken6 | 6.11.2 | LGPL-3.0-only 또는 GPL 등, 모듈마다 확인 | **조건부**: LGPL 재링크/교체, license notice, 대응 소스 획득 수단, 동적 라이브러리·플러그인 교체 가능성 |
| charset-normalizer | 3.5.2 | MIT | 가능; 실제 release dependency 여부 재확인 |
| imageio | 2.38.0 | BSD-2-Clause | 가능; scikit-image 제거 시 제외 가능 |
| lazy-loader | 0.6 | BSD-3-Clause | 가능; scikit-image 제거 시 제외 가능 |
| networkx | 3.7 | BSD-3-Clause | 가능; scikit-image 제거 시 제외 가능 |
| tifffile | 2026.9.20 | BSD-3-Clause | 가능; scikit-image 제거 시 제외 가능 |
| qpdf | 11.9.0 | Apache-2.0 | 가능; bundled lib notices 필요 |
| FFmpeg / ffprobe | 6.1.1 server | LGPL2.1+ 기본, GPL2+ if --enable-gpl | **배포용 별도 선택**: LGPL build 선호; --enable-nonfree 사용 금지; 정확한 바이너리 configure/NOTICE/source offer 확보 |
| PyInstaller | 빌드 도구 | GPL-with-bootloader-exception | 가능; bundle 라이선스는 다른 의존성 규정 준수에 종속 |
| Inno Setup | 빌드 도구 | Inno Setup license | 무료/비상업적 사용 가능; 저작권/배포 조항 준수. 공식 상업 라이선스는 상업 사용자에 구매 요청(법적 필수라고는 안내하지 않음). |
| pytest, pypdf | 개발 도구 | runtime에 미포함 | 개발 테스트에서만 사용; release artifact 제외 |
| PyMuPDF | dev venv에는 설치 | AGPL/상업 | **release에 포함 금지**. 소스 직접 의존성 제거 확인됨. |

## 최종 배포 전에 실제 수행해야 할 작업
1. **FFmpeg**: 플랫폼별 실제 배포용 FFmpeg/ffprobe 바이너리/동적 라이브러리 원천과 버전 고정. `ffmpeg -version`의 `configuration`을 릴리스 빌드에서 수집해 GPL/nonfree/기타 구성 확인. LGPL 빌드라 해도 재배포 라이선스, 저작권, 소스 획득 가능 안내를 배포 패키지에 포함. 코덱 특허 등 저작권 라이선스 외 쟁점은 지역별 별도 검토.
2. **Qt/PySide6**: 실제 사용하는 Qt modules가 LGPL 대상인지 확인하고 GPL-only 모듈 미포함을 검증. Qt LGPLv3 전문, third-party notices, 대응 소스(정확한 버전과 수정분)/서면 offer 중 해당 요건을 충족하는 방식 제공. DLL/dylib 교체·수정본 실행이 가능한지 패키지에서 테스트. 서명/보안 정책이 이 권리를 실질적으로 제한하지 않도록 확인.
3. **OpenCV wheel**: FFmpeg 내장 구성뿐 아니라 번들 바이너리별 저작권·라이선스 `LICENSE-3RD-PARTY.txt`를 정확한 빌드에서 복사. macOS/Windows 각각 플랫폼별 휠 변경 시 재검토.
4. **필요 없는 과잉 전이 라이브러리**: `slide_core/compare.py`의 `ssim_score` 미사용 여부 테스트 후 scikit-image/scipy 제거를 별도 코드 작업으로 검토. 불필요한 LGPL/GPL 구성과 공격면/설치 크기를 줄인다.
5. **PDF backend**: ReportLab 라이선스 파일을 정확한 wheel에서 동봉. qpdf 바이너리의 의존성 및 LICENSE/NOTICE 검사. qpdf는 제품의 필수 기능이 아닌 선택 최적화.
6. **Python runtime/기타**: platform별 SBOM과 실제 bundle manifest 생성. 직접·간접 패키지 버전, wheel의 라이선스 파일, 컴파일/링크된 하위 라이브러리 및 PyInstaller 포함 파일을 매칭. PyMuPDF/dev-only package 미포함 증명.
7. **사용자 앱 소스 라이선스**: 개발자 본인이 앱 코드 라이선스 결정(MIT/Apache-2.0 등 검토 가능). 해당 선택이 제3자 LGPL 의무를 축소하는 것은 아님. 사용자 라이선스·프로젝트 소스의 LICENSE와 제3자 THIRD_PARTY_NOTICES 분리.
8. **릴리스 QA**: Windows Setup/Portable, macOS DMG의 깨끗한 설치 후 PDF+JSON 출력, 저작권 및 라이선스 페이지 접근, Qt 동적 라이브러리 교체 가능, bundled binary provenance, 소스/notice URL 유효 여부 확인. 통과 전 GitHub Releases 자동 게시 보류.

## 추적 자료 (공식)
- FFmpeg https://ffmpeg.org/legal.html
- Qt LGPL https://www.qt.io/development/open-source-lgpl-obligations
- PySide6 https://doc.qt.io/qtforpython-6/
- OpenCV wheel licensing https://pypi.org/project/opencv-python-headless/
- OpenCV license https://opencv.org/license/
- qpdf https://github.com/qpdf/qpdf
- ReportLab https://docs.reportlab.com/developerfaqs/
- scikit-image https://scikit-image.org/docs/stable/license.html
- PyInstaller https://pyinstaller.org/en/stable/license.html
- Inno Setup https://jrsoftware.org/isorder.php and https://github.com/jrsoftware/issrc/blob/main/license.txt

## 판정 표기
이 감사는 **설계 단계의 구성 검토**이다. 실물 Windows/macOS 설치 파일이 아직 없어 바이너리별 라이선스·SBOM/Notice 완전성 및 모든 LGPL 의무 이행을 확정하지 않는다. 라이선스 적용 범위에 법적 판단이 필요한 사안은 배포 직전 전문가 검토를 권한다.

## 2026-10-08 실행 현황 (실제 수행)
- **완료:** GUI core에서 사용되지 않는 `ssim_score`와 `skimage.metrics.structural_similarity`를 삭제하고 `requirements.txt`에서 scikit-image를 제거했다. 따라서 새 클린 환경에서는 이로 인한 SciPy/ImageIO/Tifffile/NetworkX 의존성을 설치할 이유가 없다. 시험 환경의 이전 패키지 존재 여부는 릴리스 구성과 무관하다.
- **완료:** Ubuntu 서버 FFmpeg/ffprobe 구성에 `--enable-gpl`, `--enable-libx264` 등이 있음을 확인했다. 이 빌드는 LGPL 배포용으로 채택하지 않는다. FFmpeg 공식 법적 체크리스트는 GPL/nonfree 제외, 대응 소스 제공, 빌드 설정 공개 등을 요구한다.
- **방침 확정:** 동적 LGPL Qt/PySide6와 교체 가능 패키지, 정확한 대응 Qt 소스의 자체 제공 또는 적법한 서면 제공 약정이 필요하다. upstream URL만 넣는 것으로 끝내지 않는다.
- **준비:** `packaging/README.md`, `packaging/binary-manifest.example.json`, `packaging/audit_release.py`, `THIRD_PARTY_NOTICES.md` (초안)를 추가했다. 배포 승인되지 않은 manifest 또는 GPL/nonfree FFmpeg 입력 시 검사기는 실패하도록 한다.
- **미완료 (RELEASE HOLD):** Windows x64, macOS arm64 실제 배포용 LGPL FFmpeg 바이너리 및 정확한 소스와 라이선스 확보; 각 OS Qt DLL/dylib 교체 가능성 검증; wheel 원산지/해시/SBOM 고정; 완전한 저작권 고지 및 license copies; 설치 파일 빌드·감사. 이 단계가 끝나야 최종 재배포 적합 판정을 낼 수 있다.
- **중요:** 최초 감사 기록에 남아 있는 scikit-image/SciPy 및 PyMuPDF 개발 시험 가상환경은 현재 `requirements.txt`의 직접 요구사항이 아니다. 최종 산출물에 우연히 포함되지 않도록 별도 클린 build venv에서 패키징한다.

출처: https://ffmpeg.org/legal.html ; https://www.qt.io/development/open-source-lgpl-obligations ; https://pypi.org/project/opencv-python-headless/

### 추가 검증 (2026-10-08)
새 /tmp 가상환경을 만들고 `requirements-dev.txt`를 처음부터 설치한 뒤 `pytest -q tests` 실행 결과 **6 passed**. 해당 환경에서 `scikit-image`, `SciPy`, `PyMuPDF`의 import spec은 모두 **False**, 즉 설치되지 않았다. P0/P1 GUI 정확성 문제가 해결됐다는 의미는 아니며, 개발 서버와 별개로 Windows/macOS 릴리스 바이너리 승인 절차는 계속 보류한다.
초기 `packaging/audit_release.py`에 미승인 예제 manifest 및 서버 GPL FFmpeg를 넣어 실행한 결과 예상대로 **RELEASE BLOCKED (exit 1)**. 이는 게이트의 거부 동작만 검증하며 실제 규정 준수 승인을 뜻하지 않는다.

## Dependency inventory change (2026-10-09)
M1 made `pypdf>=5` a production dependency (formerly dev-only) for runtime PDF validation. Review exact pypdf/third-party license metadata when platform-specific artifacts are built. This update is informational only; the user deferred final binary licensing review until after development. **RELEASE HOLD remains.**

## M5/M6 evaluation-only package checkpoint (2026-10-09)

The M5 PTS-based PDF+JSON v3 exporter is implemented and synthetic source tests were run. `pypdf` is a runtime dependency (see requirements). The evaluation source ZIP includes no FFmpeg/Qt binaries and is **not** a signed or audited redistributable native installer. FFmpeg must be installed by the end user, and PySide6 wheels come from their own pip installation. No native Windows/macOS bundle was produced, so LGPL Qt replacement, exact corresponding sources, SBOM, and signed installer gates are still **BLOCKED**. The Ubuntu FFmpeg enabled GPL features and was excluded from the package. This is a personal test candidate only, not a published binary release.
