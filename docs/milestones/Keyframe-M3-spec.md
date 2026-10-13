# M3 — 키프레임 모델과 JSON v4
기준: Keyframe-0.5-design.md, 사용자의 M3 시작 지시. M2 3a1ee59 위에서 같은 feature/keyframe-0.5 worktree에 구현하며 main/공개0.4.12 릴리즈는 변경하지 않습니다.

샘플은 sample_id, ordinal, source_pts, time_base, pts_origin, cache_path, width, height만 가집니다. ordinal은 관측 순서0..N-1이며 고정 시간 격자/명목 시간은 제거합니다. Project/Request/Result/Snapshot은 순번·엄격한 PTS 증가·일관된 timebase/origin을 검증합니다. Project와 Snapshot은 decoder-keyframes-v1 provenance를 유지합니다.

상세 JSON은 schema_version=4, sampling.algorithm=decoder-keyframes-v1로 제한합니다. source timebase/origin과 각 sample의 정수source_pts/ordinal을 원본 시간의 권위 데이터로 저장합니다. timestamp_s는 파생된 편의값입니다. 디코더 keyframe flag로 확인한 샘플만 들어가며 실제 슬라이드 경계라는 뜻은 아닙니다. 변화 탐지 bounds=(left_sample,right_sample)와 observed_at_s를 저장하고 true_boundary_s=null, uncertainty_kind=keyframe_and_detector로 유지합니다. 원본 소스/캐시의 전체 경로는 저장하지 않습니다. 실제 사용한 DetectorConfig를 기록하며 페이지/세그먼트 참조, PDF UUID/count/hash를 교차검증합니다. FPS/v3 parser/fallback은 제품에 추가하지 않습니다.

간단 JSON은 {"slides":[{"page":1,"start":0,"end":...}]} 호환 형태를 유지합니다. 범위는 현재 PDF 대표 페이지 순서를 기준으로 첫페이지0, 이후대표시각부터 다음대표시각/영상끝까지이며 실제 슬라이드 전환이라고 주장하지 않습니다. Merge/Delete/Replace/Add는 기존 키프레임만 선택합니다. 상세 JSON은 별도로 탐지 경계를 보존합니다.

PDF+JSON은 기존 안전한 ExportTransaction/출력자원 lock/검증/rollback/recovery를 재사용합니다. immutable snapshot만으로 PDF/sidecar를 구성하고 원본 변경/프로젝트 변경/승인 후 출력 교체/취소는 기존 파일을 보존하며 실패합니다. publish 이후 취소는 저장 완료로 처리합니다. PDF-only 기본값은 유지하고 Save options에서 Simple/Detailed v4를 복구합니다. GUI 설정 변화가 편집된 결과나 준비 캐시를 바꾸지 않습니다.

검증은 합성 VFR/비영점PTS/GOP/편집, 모델·스키마 malformed/primitives/참조/출력hash, 실패 주입 트랜잭션, GUI 저장 옵션과 설치 entry의 offscreen smoke입니다. 실제강의 성능은 M4, Mac/Windows 설치본은 M5입니다.
