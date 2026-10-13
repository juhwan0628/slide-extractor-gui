# M1 — 키프레임 디코딩과 원본 PTS 연결

완료일:2026-10-12KST. 작업 브랜치 feature/keyframe-0.5, 기반4a8d486.

## 구현

slide_core.pts.keyframe_stream을 별도 저수준 API로 추가했습니다. cpu-keyframes는 FFmpeg 입력 앞에 -skip_frame nokey를 지정하고 -fps_mode passthrough를 유지합니다. 디코딩 뒤 FPS 필터로 프레임을 버리는 경로가 아닙니다. 실제 절감량은 코덱과 M4 실영상 프로파일로 확인합니다.

한 디코딩 스트림의 showinfo audit/sample 순번 및 원본 integer PTS를 raw RGB 순번과 연결합니다. 실제 iskey:1 여부, 단조 증가 PTS, 감사/선택 PTS 일치와 최종 이미지 개수를 검증합니다. 별도 ffprobe 배열과 출력 이미지를 추정 순번으로 합치지 않습니다. 원본 time_base·origin, 표시 변환, JPEG90 품질과 기존 소유 캐시 정책을 재사용합니다.

진행 정지 기반 타임아웃·취소·프로세스 종료·부분 캐시 제거를 적용합니다. EOF의 여분 픽셀 검사가 원래 감사 오류를 가리던 경합을 오류 주입으로 재현한 뒤 수정했습니다.

M1 내부 Sample의 grid_index는 관측 순번이며 nominal_time은 actual_time입니다. 불규칙 샘플을 고정격자 v3 JSON으로 내보내면 안 됩니다. GUI/PreparedSamples/설정은 기존 FPS 경로를 계속 사용하며 M2/M3에서 모드·JSON 구조를 통합합니다. 공개 버전은 변경하지 않았습니다.

## 검증

- 최초 RED:13failed1.96s (키프레임 API/디코더 백엔드 미구현).
- 새 키프레임 회귀19개:실제 MPEG4/H264/H265, B-frame·VFR·비영점 시작PTS; 전체 디코딩 ffprobe keyframe PTS와 추출PTS 정확 일치; 같은 PTS의 full-frame 픽셀 비교. 이 실행에서는 관련 인코더 skip 없음.
- 모든 프레임이 I-frame인 영상과 긴 GOP 영상은 실제 키프레임10개/1개로 관측하며 중복 생성하지 않습니다. 이 검사는 긴 GOP의 슬라이드 누락 방지를 증명하지 않습니다.
- 거짓 키프레임·잘못된 PTS·중복PTS·PTS누락·잘린 이미지·빈 결과·원본 변경·취소·정지 시 오류와 부분 캐시 제거 및 자식 회수를 검증했습니다.
- 새 경로 및 기존 샘플링/디코더 집중 검사:41passed15.45s.
- 전체 프로젝트:726passed81.95s, 종료코드0.
- 독립 읽기 전용 리뷰 keyframe_m1_review:남은 Critical/Important 없음. diff 공백 검사 통과.

## 후속

M2:백그라운드 준비·캐시 모드/모델·타임라인 연결. M3:불규칙 시점 JSON 및v3호환. M4:실영상 전체 흐름의 반복 성능 및 누락/필기 비교. 아직Mac/Windows설치본, GUI전체키프레임동작 또는 실영상 속도 향상을 검증했다고 주장하지 않습니다.

Deferred minor:키프레임 전용 회전/비정방SAR/동적색상 회귀 추가. 기존 표시 파이프라인은 재사용하고 있으나 새 실영상 fixture는 기본 변환만 검사했습니다.
