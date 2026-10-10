# 맥·Windows 동시 베타 배포

공통 소스와 `slide_core/version.py`에서 버전을 관리합니다. 사용자는 Mac Apple Silicon DMG 또는 Windows x64 설치 EXE를 받습니다. Python·Qt·FFmpeg·FFprobe가 포함됩니다.

## 0.4.10rc2 안정성 검증 기록

- 공통 소스: `ddf7ba086a45dfe79fa0da61dfe48f97af5358c2`. 서버 전체 **619 passed in 50.75s**. [같은 소스 CI 38050474696](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38050474696): Linux **613 passed, 6 skipped**; Windows 캐시 **21 passed, 1 skipped, 2 deselected**, 출력 잠금 **7 passed, 1 skipped**.
- 만료·용량 압박 캐시 자동 정리, 현재/재사용/다른 프로세스 캐시 보호, 취소·실패 부분 캐시 정리; 영상 열기 실패·취소 시 Undo/Redo와 준비 상태 보존; 복구 잠금·접근 오류 안내. 기존 분석 알고리즘은 유지합니다.
- [네이티브 설치본 38050474664](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38050474664): 두 OS 성공. 실제 DMG/EXE 설치 후 분석·수동 편집·키보드·PDF 출력·잠금 정리·QtCore 교체 실행 검사를 통과했습니다.
- 설치 검사 소유 캐시 잠금을 임시 폴더 삭제 전에 해제하는 Windows 호환 수정을 포함합니다. 성공·실패 정리 회귀가 실패→통과하고 독립 리뷰를 통과했습니다. 첫 실행 38049486364의 후보는 출고 대상에서 제외합니다.
- [별도 원본 설치본 출고 감사 38051180933](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38051180933): 두 OS PASSED, errors 없음. 실제 native 파일 목록은 rc1 승인 구성과 동일합니다. 정확한 원본 설치본·출고 manifest 해시는 `packaging/release-approval.json`에 고정합니다.
- 유료 서명·공증 정책과 지원 아키텍처는 유지합니다.

## 0.4.10rc1 검증 기록

- 공통 소스: `36365be00f0ff5991231d5f4d74b28e12f962e4f`. 로컬 전체 597 passed; [같은 소스 CI 38015387742](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38015387742) 591 passed, 6 skipped. Windows 출력 잠금 검사 7 passed, 1 skipped.
- [네이티브 후보 38015387743](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38015387743): macOS arm64 / Windows x64 모두 성공. 실제 설치본에서 Shift 선택·Merge·삭제·Undo/Redo·Shift 기준점 복원, 편집 후 PDF/PDF+JSON 및 잠금 정리, QtCore 교체 실행 검사를 통과했습니다.
- [별도 설치본 출고 감사 38015955293](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/38015955293): 두 OS 모두 PASSED. 원본 설치 파일과 감사 manifest 해시는 `packaging/release-approval.json`에 고정합니다.
- 기존 승인 인벤토리에서 추가된 native 구성은 설치본 검사에 쓰이는 Qt Test 모듈과 바인딩입니다. LGPLv3 대상 Qt 모듈이며 고정된 전체 Qt / Qt for Python 소스와 원문 라이선스에 포함됩니다. 다른 native 라이브러리나 OpenCV 영상 코덱은 추가되지 않았습니다.
- 변화 감지·분석 알고리즘은 유지합니다. 필기 누적과 페이지 재방문의 자동 처리는 향후 연구 과제입니다.

## 0.4.9rc3 검증 기록

- 네이티브 빌드: [37991615142](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/37991615142), 두 OS 성공. 실제 빌드 소스는 `a0c7043c26eca7cd75079ba39c4757134b1793c2`입니다.
- 같은 소스 CI: [37991615111](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/37991615111), 563 passed, 6 skipped.
- 실제 설치본 출고 검사: [37992725057](https://github.com/juhwan0628/slide-extractor-gui/actions/runs/37992725057), 맥·Windows 모두 PASSED. 설치 파일과 감사 manifest 해시는 `packaging/release-approval.json`에 기록합니다.
- 실제 설치·분석·PDF/PDF+JSON·출력 잠금 정리와 수정 QtCore의 실행을 검사했습니다. Qt 교체 검사는 호환 바이너리의 버전 문자열 변경 시험이며 임의 Qt ABI 또는 재빌드 호환성을 보장하지 않습니다.
- 앱 소스는 MIT입니다. GPL 코덱이 확인된 rc2 macOS OpenCV wheel은 공개하지 않으며 rc3는 이미지 전용 OpenCV 소스 빌드를 사용합니다.
- Mac은 ad-hoc 서명·공증 없음, Windows는 unsigned입니다. 유료 서명·공증은 이번 베타 조건이 아닙니다.

## 출고 절차

1. `Native installer candidates`에서 두 OS 후보를 빌드합니다. FFmpeg 입력과 실제 실행 설정을 검증하고, OpenCV 이미지 구성, 고정 소스·라이선스 수집, PyInstaller 및 DMG/Inno Setup 설치·빈 PATH 검사를 수행합니다.
2. 실제 native 라이브러리 목록을 검토하고 그 목록의 해시와 소스 CI/후보 run을 `packaging/candidate-review.json`에 고정합니다. `Audit reviewed installed candidates`는 원본 설치 파일을 새로 설치해 파일·소스·고지·Qt 교체 증거를 대조하고 `audit_release.py`를 실행합니다.
3. 통과한 동일 두 설치 파일과 보고서를 `packaging/release-approval.json`에 연결합니다. 입력 manifest의 `VERIFIED_INPUTS`나 관찰된 빌드 성공만으로 출고 승인하지 않습니다. 버전·커밋·run ID·해시가 다른 자료는 거부합니다.
4. `packaging/beta-review.json`은 검증한 후보·소스 CI·별도 감사와 공개 승인 상태를 가리킵니다. `Publish reviewed beta (both OS)`는 실제 보고서·설치 파일·모든 소스 및 패치 해시를 확인하고 private draft에 업로드합니다. GitHub가 관찰한 모든 자산 digest를 로컬 승인 파일과 다시 비교한 뒤에만 공개합니다. 이미 공개된 같은 태그는 덮어쓰지 않습니다.

GitHub 기본 토큰의 과거 커밋 태그 권한 제한 때문에 릴리스 태그는 **검토 자료 정리 커밋**을 가리킬 수 있습니다. 후보 커밋 이후 달라진 파일이 명시적인 문서/검토 자료 허용 목록에만 속하는지 확인합니다. 앱 코드·requirements·빌드 스펙·네이티브 입력 설정이 바뀌면 릴리스 준비가 실패합니다. 실제 빌드 커밋은 BETA_REVIEW.json과 build-manifest.json에 별도로 보존됩니다.

## 릴리스 에셋 구성

직접 업로드하는 파일은 설치 DMG·설치 EXE·Sources-Licenses.zip·SHA256SUMS.txt 네 개입니다. GitHub 자동 Source code ZIP/tar.gz를 포함하면 사용자가 보는 에셋은 여섯 개입니다. 일반 사용자 다운로드는 릴리스 설명 맨 위에서 안내합니다.

Sources-Licenses.zip은 대응 소스, OS별 패치, 라이선스, 빌드 입력·감사 자료와 원래 파일별 해시를 보존합니다. packaging/compact_release.py는 원래 자료의 파일 목록과 SHA-256을 검증하고, 압축 후 다시 모든 자료 바이트를 검증합니다. 외부 SHA256SUMS.txt는 설치 파일 두 개와 자료 ZIP을 가리킵니다.

이미 공개된 릴리스의 자료 정리는 별도 Consolidate published release assets 워크플로로 수행합니다. 고정된 원래 릴리스 ID·파일 목록·해시와 대조하며, 새 자료 ZIP과 해시 파일의 GitHub digest를 확인한 후에만 기존 개별 자료를 삭제합니다. 설치 파일과 태그는 변경하지 않습니다. 중단 후 재실행할 때는 이미 업로드한 ZIP에서 원래 자료를 복구해 재검증합니다.

소스 제공은 14일 CI 보관으로 끝내지 않습니다. 릴리스에 정확한 FFmpeg·Qt·Qt for Python·OpenCV 등 원본 소스, 수정 패치, 고지·라이선스 원문, 빌드·감사 기록 및 SHA256SUMS를 함께 제공합니다. 다운로드 사용자에게 vendor 폴더 생성이나 Python 설치를 요구하지 않습니다.

기술 출고 검사는 법적 인증서가 아닙니다. 새로운 dependency나 native wheel/라이브러리를 도입하면 실제 배포 바이트를 기준으로 다시 검토합니다.
