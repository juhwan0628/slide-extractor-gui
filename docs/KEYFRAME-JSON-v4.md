# Keyframe JSON v4

상세 JSON은 schema_version:4, sampling.algorithm:decoder-keyframes-v1입니다. FPS/v3 파일과 호환되지 않습니다. 제품은 v3를 읽거나 FPS로 보충하지 않습니다.

source.time_base_num/time_base_den/origin_pts와 samples[].source_pts는 원본 정수 시간 데이터입니다. 관측 시간은 (source_pts-origin_pts)*time_base입니다. ordinal은 관측 순번0..N-1이고 일정한 시간 간격을 뜻하지 않습니다. timestamp_s는 편의용 파생 실수입니다. 매우 큰 정수PTS를 JavaScript에서 다룰 때는 정밀도를 보존하는 JSON 파서를 사용해야 합니다.

detected_boundaries의 lower_s/upper_s는 인접 키프레임에서 변화가 관측된 구간이고 observed_at_s는 오른쪽 관측 시각입니다. 실제 전환 순간은 확정할 수 없어 true_boundary_s:null, uncertainty_kind:keyframe_and_detector로 저장합니다. 키프레임 자체가 슬라이드 전환이라는 뜻은 아닙니다.

detected_segments는 편집 전 분석 결과입니다. pages는 현재 PDF의 실제 페이지 순서·UUID·대표 키프레임입니다. Merge/Delete/Add/Replace 후에도 탐지 경계는 유지하고 페이지 목록만 반영합니다. navigation_ranges는 대표 페이지 순서로 첫페이지0초, 이후 대표시각부터 다음 대표시각/영상끝까지 이어집니다. 실제 경계와 분리된 탐색 범위입니다.

간단 JSON은 기존 {slides:[{page,start,end}]} 형태를 유지하지만 현재 PDF의 대표 페이지 탐색 범위를 제공합니다. 모든 페이지를 마지막 페이지로 합치면 한 페이지의 범위는 0~영상끝입니다. 정확한 키프레임 PTS와 탐지 경계가 필요하면 상세 v4를 선택하세요.

artifact의 PDF basename/count/SHA256/export UUID는 PDF와 교차검증합니다. 원본은 basename·크기·수정시각·bounded fingerprint만 기록하고 원본/캐시 전체 경로는 내보내지 않습니다. PDF는 JPEG 미리보기가 아닌 원본의 선택한 키프레임을 정확한 PTS로 추출합니다. PDF-only가 기본이고 Save options에서 JSON을 켭니다.

검증 API: slide_core.keyframe_json.loads(raw, pdf_bytes=..., pdf_page_count=..., pdf_export_id=...). 구조·원시타입·순번·원본 시간·참조·ROI·페이지/세그먼트·아티팩트 일치를 검사합니다. 중복 JSON 키, NaN/Infinity, 알 수 없는 필드와 v3 payload는 거부합니다. PDF bytes는 hash 검증용이며 PDF 구조/이미지/UUID 검증은 출력 엔진이 별도로 수행합니다.

이 문서는 개발 브랜치의 M3 계약입니다. 설치본0.5.0 출고 검증은 M5에서 진행합니다.

출력 엔진은 출력 잠금을 획득하고 경로·원본 확인을 마친 뒤 publication guard로 취소·프로젝트 변경을 재확인합니다. guard를 통과하면 원자적 commit/rollback 구간을 끝까지 수행하고 그 이후 취소는 저장 완료로 처리합니다. ROI와 제외 영역의 detector 투영 및 유효 픽셀 임계값은 분석과 JSON이 같은 geometry 함수를 사용합니다.
