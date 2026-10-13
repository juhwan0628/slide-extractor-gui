# M3 완료 — 관측 순번·원본 PTS 모델과 JSON v4
개발 기준: 3a1ee59. 계획/설계: Keyframe-M3-plan.md, Keyframe-M3-spec.md.

## 구현
- Sample grid_index/nominal_time 제거, ordinal+source_pts/time_base/pts_origin으로 통일.
- 모델/요청/결과/스냅샷의 순번·시간 순서·공통 시계·원본 시계 및 Project/Snapshot 알고리즘 provenance 검증.
- 상세 keyframe JSON v4: 원본 정수PTS, 실제 설정, 불확실한 탐지 구간, 편집된 PDF 페이지, 탐색 범위, PDF UUID/count/hash 교차검증. v3/FPS runtime은 복귀하지 않음.
- 간단 page/start/end JSON: 현재 PDF의 대표 페이지 탐색 범위.
- immutable snapshot의 PDF+JSON 동시 저장과 기존 승인지점·출력잠금·rollback/recovery·저장완료/취소 상태 보존.
- Save options의 Simple/Detailed v4 복구, PDF-only 기본값 유지. 편집/캐시/분석을 변경하지 않음.
- source 설치 entry offscreen smoke에서 합친 페이지의 detailed/simple/PDF-only 실제 저장 검증, native 테스트 recipe에 새 계약 추가. source evaluation ZIP에 계약 문서 포함, legacy는 미동봉.

## 검증
- 모델19 RED→203 focused GREEN; 전체636 passed(139.88s).
- JSON28 RED→28 GREEN; 새 paired export12 RED→40 focused GREEN.
- 기존 schema/paired transaction/real media/path 승인/출력 cleanup 포팅94 passed16.34s; pre-GUI 전체764 passed163.05s.
- GUI4 RED→4 GREEN; 실제 합친 PDF/JSON과 선택/취소/승인 동작 포함. source 설치 entry도 paired/simple/PDF-only 실제 실행.
- 독립 전체-M3 리뷰: Critical 없음, Important2, Minor 없음.
- 리뷰 수정: 잠금 취득/원본 및 출력 확인 이후 publication guard 추가. guard 통과 전 취소·프로젝트 변경은 기존 파일 보존; 이후 원자적 commit/rollback은 완료.
- 리뷰 수정: ROI/마스크 투영 및 유효 픽셀 임계값을 detection_geometry로 공유. 분석에서 허용되는 1920×1080 / ROI1920×1070 / mask1920×1009 사례도 상세 JSON 허용(2880 valid pixels,178×320).
- 두 리뷰 이슈9 재현 RED→GREEN, 관련154 회귀 통과.
- 최종 무제외 전체783 passed170.69s, git diff --check / compileall 통과.
- 서버의 동시 CPU 작업이 있었으므로 전체 테스트 소요시간은 성능 비교값으로 사용하지 않음.

## 실행 중 설계 결정
1. 상세 schema v4로 분리 — 불규칙 키프레임 계약을 v3 FPS 격자로 가장하지 않기 위함. 기존 v3 소비자는 새 상세 형식으로 마이그레이션 필요.
2. 간단 필드는 유지하되 대표 PDF 페이지 탐색 범위로 구성 — 합치기/삭제 결과와 정렬을 맞추기 위함. 실제 탐지 구간이 필요한 소비자는 상세 detected_segments/boundaries 사용.
3. 원본 정수PTS가 시간의 권위 데이터, 파생 실수초는 편의값 — 고정 명목시간 및 가짜 정확한 경계를 만들지 않기 위함. 정밀 시각 소비자는 PTS/time_base를 기준으로 처리해야 함.

Deferred minor 없음. 재리뷰 없이9 RED→GREEN 및 전체783 GREEN으로 수정 검증.

## 남은 단계
M4 실제 SP/멀티코어/AI윤리 강의 정확성·최종필기 상태·준비/분석/JPEG/PDF 비용 비교. FPS는 외부 고정 기준선만 사용.
M5 같은 소스의0.5.0베타 Mac/Windows 실제 설치·실행·저장·라이선스 출고 검증 및 버전/문서/릴리즈 정리.
이번 단계에서 새 DMG/EXE 설치 검증·GitHub push·공개 릴리즈는 수행하지 않음.
