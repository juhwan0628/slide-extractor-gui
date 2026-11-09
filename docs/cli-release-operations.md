# CLI 업데이트와 복구 운영

개발 원본은 `juhwan0628/slide-extractor-gui`, CLI 배포 대상은 `juhwan0628/slide-extractor`다. 서버의 기본 작업 폴더는 `/home/ubuntu/workspace/02_slide-extractor/slide-extractor-gui` 하나로 유지하고 작업별 브랜치를 사용한다. export와 설치 검증 산출물은 ignored `dist/` 아래에 둔다.

## 관리 범위

| 위치 | 수정 방식 |
|---|---|
| 원본 `slide_core/`, `slide_cli/` | 원본 작업 브랜치에서 수정·테스트·PR |
| 원본 `packaging/cli_release/` | CLI 배포 README·사용법·metadata·CI·빌드 템플릿 수정 |
| 원본 `scripts/export_cli_release.py` | 포함 목록·manifest 생성 정책 수정, exporter 테스트 필수 |
| CLI 저장소의 모든 tracked 파일 | 확정 원본 커밋에서 export해 PR로 반영 |
| 공개 tag와 release assets | 게시 후 유지, 수정은 새 버전 |

CLI 저장소에서 코어를 직접 고치지 않는다. 긴급 수정도 원본에서 먼저 반영한다. GUI 설치본과 CLI wheel은 배포 대상과 의존성이 다르다. wheel에는 Qt·FFmpeg·FFprobe·네이티브 도우미가 포함되지 않는다.

## 다음 버전

1. 원본의 깨끗한 main에서 작업 브랜치를 만든다. 공통 VERSION과 변경 기록을 갱신하고 구현·템플릿을 함께 검토한다. `docs/cli.md`와 배포 템플릿 `cli.md`의 공통 안내도 같이 갱신한다.
2. 원본 테스트와 CI가 통과한 PR을 main에 병합한다. 원격 main의 전체 40자리 SHA를 기록한다.
3. 원본 폴더에서 해당 확정 SHA를 export한다. 목적지는 기존에 없는 ignored 경로여야 한다.

```bash
git fetch origin main
SOURCE_SHA=$(git rev-parse origin/main)
# 기록한 원격 main의 40자리 SHA와 SOURCE_SHA가 같은지 확인한 뒤 진행한다.
python scripts/export_cli_release.py --commit "$SOURCE_SHA" --output "dist/cli-$SOURCE_SHA"
python "dist/cli-$SOURCE_SHA/scripts/verify_snapshot.py"
```

4. CLI 원격 main을 다시 조회한다. 그 커밋을 부모로 하는 일반 커밋으로 snapshot 전체를 반영하고 PR을 만든다. 이전 생성 파일의 삭제도 반영한다. force push·orphan 이력 교체를 사용하지 않는다. GitHub API를 쓸 때도 기대 HEAD를 지정해 다른 변경을 덮어쓰지 않는다.
5. manifest의 모든 파일 hash, 원본 runtime blob과의 일치, GUI·개인 자료 제외를 확인한다. CLI CI의 Linux/macOS/Windows 세 작업이 모두 성공한 후 일반 merge한다.
6. 새 CLI main SHA를 고정한다. 게시용 `publish/cli-<version>` 브랜치를 그 SHA로 전진시키거나 그 브랜치의 `Publish verified CLI prerelease`를 수동 실행한다. 자동 게시가 시작되려면 해당 브랜치로 push 이벤트가 발생해야 한다. 첫 브랜치는 기존 main의 조상에서 만든 뒤 고정 SHA로 fast-forward할 수 있다. 같은 ref에 같은 SHA를 다시 지정하는 것만으로 실행을 기대하지 않는다.
7. 워크플로는 세 OS 검증 후 Ubuntu에서 wheel·sdist를 빌드하고 새 환경에 설치해 PDF·고급 JSON을 검증한다. 게시 repo, 브랜치 이름, HEAD와 현재 main 일치, 미존재 tag를 검사한다. 현재 워크플로는 사전 릴리스 게시용이다. 정식 버전 전환은 별도 변경으로 검토한다.
8. 공개 assets를 다시 내려받아 SHA256SUMS와 release API digest, provenance, source-manifest를 비교한다. wheel·sdist를 각각 새 가상환경에 설치하고 `pip check`, 버전, Qt 부재, 영상→PDF·고급 JSON을 확인한다.
9. 릴리스마다 아래 연결표와 CI URL을 기록한다. 문서만 갱신한 main snapshot은 기존 릴리스 파일을 바꾸지 않는다. 기능·패키지 수정 게시에는 새 버전을 사용한다.

## 릴리스 연결 기록

| 항목 | 최초 CLI 사전 릴리스 |
|---|---|
| 버전 | 0.5.0b2 |
| 원본 커밋 | `fc5340c714217e95857026e6cc489b58f121b08d` |
| CLI 커밋 / tag 대상 | `1d443278481563612d58a874014f410e1492220a` |
| 공개 릴리스 | https://github.com/juhwan0628/slide-extractor/releases/tag/v0.5.0b2 |
| 게시 CI | https://github.com/juhwan0628/slide-extractor/actions/runs/42575650167 |
| 파일 연결 | `provenance.json`의 두 repo/commit/version/artifact hash, `source-manifest.json`의 파일 hash, `SHA256SUMS` |
| 재다운로드 검증 | wheel·sdist 각각 설치 성공, Qt 없음, 4페이지 PDF·고급 JSON 검증 성공 |
| 구 CLI 보존 | `legacy/cli-v0.1.0-20261109` → `66709913a8c67a703c2e453b747d2c93368d9779` |

## 실패와 복구

- 검증 실패: 게시를 진행하지 않고 실패 로그의 원인을 원본에서 수정한다. main이 바뀌었으면 새로운 확정 snapshot과 CI를 사용한다.
- 기존 tag 충돌: 기존 tag/assets를 삭제하거나 교체하지 않는다. 버전을 올려 다시 진행한다. 게시 중 일부 asset만 올라갔어도 같은 버전의 bytes를 바꿔 끼우지 않는다.
- 기능 회귀: 사용자는 이전에 검증된 wheel을 별도 새 가상환경에 설치한다. 개발자는 원본에 일반 revert 또는 수정 PR을 반영하고 새 버전을 export·검증·게시한다. CLI 생성 파일만 수동 revert하면 manifest와 불일치할 수 있으므로 원본에서 재생성한다.
- FFmpeg 오류: `ffmpeg -version`, `ffprobe -version`과 PATH를 확인한다. `slide-extractor`를 찾지 못하면 가상환경의 Python으로 `python -m slide_cli`를 실행한다.
- 출력 충돌: 기존 PDF/JSON을 확인하고 출력 경로를 바꾼다. 교체 의도가 있을 때만 `--overwrite`를 사용한다. `published=true`인 실패는 출력이 이미 게시되었을 수 있으므로 결과 경로를 확인한다.
- Windows 한글 경로/리다이렉션: PowerShell에서 `$env:PYTHONUTF8="1"`을 지정한다.
- 성능 차이: 일반 wheel은 도우미 없는 CPU 대체 경로를 사용한다. 네이티브 GUI와 동일 속도로 해석하지 않는다.

PyPI 게시와 GUI 설치본 갱신은 이 절차에 포함하지 않는다.
