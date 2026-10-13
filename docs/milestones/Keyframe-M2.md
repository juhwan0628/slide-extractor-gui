# M2 — 키프레임 준비·분석·프리뷰 통합

완료일:2026-10-12KST. 브랜치feature/keyframe-0.5, 기반3b45631. M1 디코더를 공통 준비·분석·GUI 구성에 연결했습니다. 공개 설치본/기본 모드/버전은 변경하지 않았습니다.

## 동작

AnalysisSettings.sampling_mode는fps 또는keyframes입니다. sampling_identity는알고리즘버전과유효FPS를구분하며키프레임에서는FPS가식별에영향을주지않습니다. PreparedSamples와BackgroundSamples가같은모드를보관하고분석재사용전소스와방식을검사합니다. FPS캐시를키프레임캐시로오인하지않으며키프레임캐시에1→0.5축소를적용하지않습니다.

prepare_samples와직접analyze_project가감사된keyframe_stream으로분기합니다. 준비중/완료뒤Analyze는같은생산자를이어받습니다. ROI·마스크·민감도변경과무관한키프레임샘플은그대로재사용합니다. Window(settings=AnalysisSettings(sampling_mode='keyframes'))구성으로전체화면흐름을사용할수있고새영상/Startover에도모드가유지됩니다. PlaybackClock와타임라인은기존actual_time을사용하므로불규칙한PTS를표시합니다. 창의기존FPS기본값은유지합니다.

키프레임분석화면에는FPS조절을표시하지않고PDF단독저장·편집을지원합니다. 상세v3JSON은불규칙시점을지원하지않으므로저장옵션의JSON선택은이개발모드에서비활성화하고pairedexport/payload_v3도출력전명시적으로거부합니다. M3에서불규칙시점스키마와simpleexport를통합한뒤활성화합니다. 고정FPS모드의JSON은유지합니다.

프로파일은sampling_mode/algorithm,실제cpu-keyframes와자동스레드설정0을기록합니다. 키프레임모드에서FPS경로의decode_options값을실제스레드수로잘못표시하던부분을회귀테스트로수정했습니다.

## 검증

- 최초M2RED:8failed2.59s; 모드API미구현.
- 실제VFR영상의키프레임PTS,빠른/늦은Analyze와1회의백그라운드디코딩,ROI/민감도/FPS무관재사용,잘못된방식캐시및FPS축소거부,불규칙시점프리뷰·Delete/Undo·PDF저장·Startover정리검증.
- FPS→키프레임분석실패시이전FPS캐시보존. 회전90도/non-squareSAR실영상과동적색상변화거부도검증해M1의추가변환검사항목을해결했습니다.
- 회전fixture가rotate태그를보존하지않는환경임을실제ffprobe로확인했습니다. -display_rotation으로실제matrix를생성하고probe회전값도검사하며제품코드는우회하지않았습니다.
- 초기전체회귀741passed1failed87.46s:기존test_m8_workflow.test_stages_auto_review_first_selection이worker캐시등록만기다리고mainQt큐의실제이미지표시전None을읽었습니다. 표시완료도기다리도록predicate를수정했고기존ROI/크기검증은유지했습니다. 렌더링제품코드는변경하지않았습니다.
- 독립리뷰Important:직접sampler지정이방식표시와실제샘플을혼동할수있었습니다. 생성VFR영상3RED1PASS로재현한뒤키프레임모드는감사된builtin만허용하고상충하는builtin을거부합니다. 기존customFPS호출signature는유지하되원본PTS/timebase/origin/격자계약을검사합니다. 오류시새캐시만정리합니다.
- 리뷰수정후키프레임통합및기존M8GUI검사22passed8.10s. 최종전체프로젝트746passed89.11s,종료코드0. diff공백검사통과.

## 후속

M3:불규칙시점JSON·v3호환·simpleJSON활성화. M4:실강의반복성능·슬라이드/최종필기비교. M5:기본키프레임전환·불필요FPS경로정리·0.5베타네이티브배포검증.
Deferredminor:수동비키프레임추가/교체와정확한프레임추출fallback의키프레임프로젝트전용회귀는M3에서추가합니다. 기존extract_selected와고정FPS편집/저장검사는유지했습니다.
