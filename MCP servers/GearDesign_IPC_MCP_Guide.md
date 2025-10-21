# GearDesign IPC MCP 서버 사용 가이드

## 개요
기어 설계 시스템과 IPC 통신하여 치형 계산, 하중 분석, 사이징, 보고서 생성 등을 수행합니다.
**중요**: 모든 작업은 세션 기반이며, `initialize()`로 시작 필수.

---

## 워크플로우 선택 (의사결정 트리)

```
사용자 요청 분석
    ↓
[성능 기준 요청?] ("저소음", "경량", "고효율" 등)
    ├─ YES → SimpleSizing 워크플로우
    └─ NO
        ↓
    [모듈/잇수 구체적 수치?]
        ├─ NO → SimpleSizing 워크플로우
        └─ YES
            ↓
        [추상적 표현?] ("적절한", "좋은" 등)
            ├─ YES → SimpleSizing 워크플로우
            └─ NO → 기본 워크플로우
```

### 1️⃣ 기본 워크플로우 (구체적 제원 제공 시)

**조건**: 모듈, 잇수 등 **모두 구체적 수치**로 제공
**예시**: "모듈 3, 잇수 20-60, 헬리컬각 15도"

**실행 순서**:
```
initialize() → modify_gear_data() → calc_geometry() → calc_load_case()
→ get_allresults_summary() (표로 표시 필수) → get_2D_image/get_gear_report/get_3d_image/get_3d_modeling
```

### 2️⃣ SimpleSizing 워크플로우 (러프한 조건/성능 기준)

**조건**: 다음 중 **하나라도** 해당
- 모듈/잇수가 범위 또는 미지정 (예: "모듈 2~4", "기어비만 제공")
- 성능 기준 요청 (예: "저소음", "경량", "고효율")
- 추상적 표현 (예: "적절한", "찾아줘")

**실행 순서**:
```
initialize() → modify_gear_data(기본설정) → simple_sizing_gearpair()
→ get_simplesizing_results() (rank 기반 분석 + 표 표시 필수)
→ 사용자 선택 → modify_gear_data(선택 케이스)
→ calc_geometry() → calc_load_case() → get_allresults_summary()
```

---

## 핵심 도구 (필수 정보만)

### 세션 관리
- **`initialize()`**: 세션 생성 및 IPC 시작 → `session_id` 반환 (모든 함수에 필수)
- **`delete_session(session_id)`**: 세션 및 파일 삭제

### 데이터 입력/수정
- **`modify_gear_data(user_message, session_id)`**: 자연어로 기어 데이터 수정
  - 기어비 요청 시 자동으로 잇수비 계산
  - 매크로 제원 변경 시 CDMethod=1 자동 설정
- **`load_GearDesign_data(file_path, session_id)`**: JSON/GD1 파일 로드
- **`save_GearDesignData(session_id)`**: 현재 데이터 JSON 저장

### 계산 수행
- **`calc_geometry(session_id)`**: 기하학적 계산 (calc_load_case 전 필수)
- **`calc_load_case(session_id)`**: 하중 계산 (메시지 반환)

### 결과 조회
- **`get_allresults_summary(session_id)`**: 모든 계산 결과 요약 → **표로 표시 필수**
  - 전제조건: calc_geometry + calc_load_case 완료
- **`get_messages(session_id)`**: 계산 경고/오류 메시지 조회

### 출력물 생성
- **`get_2D_image(session_id)`**: 2D 치물림 이미지 (PNG)
- **`get_3d_image(session_id, width, height)`**: 3D 이미지 (PNG)
- **`get_3d_modeling(session_id)`**: 3D 모델 (STEP)
- **`get_gear_report(session_id)`**: 설계 보고서 (PDF)

### SimpleSizing (기어쌍 사이징)
- **`simple_sizing_gearpair(user_message, session_id)`**: 다양한 조합 계산
  - 이전 대화 기반 요구사항 요약하여 입력
- **`get_simplesizing_results(session_id, return_all=False, top_n=100)`**: 결과 조회
  - **반드시 rank 기반 분석 후 표로 표시**

---

## SimpleSizing 성능 기준 분석 (중요!)

### DataFrame 주요 컬럼
- **`rank`**: Pareto rank (**낮을수록 우수**, Rank 1 = Pareto front)
- **`PPTE`**: 전달오차 (낮을수록 좋음)
- **`total mass`**: 총 질량 (낮을수록 좋음)
- **`efficiency`**: 효율 (높을수록 좋음)
- 기타: `module`, `z1`, `z2`, `CenterDistance`, `SF_bending`, `SF_contact`

### 분석 원칙 (절대 규칙!)
1. **모든 분석에서 `rank`를 1차 정렬 기준**으로 사용
2. **Rank 1 솔루션 중에서** 요청된 성능 지표 기준으로 2차 정렬
3. **Rank 2 이상은 특별한 이유 없으면 추천하지 않음** (일부 지표만 좋고 전체적으로 열등)

### 성능 기준별 정렬 방법

| 성능 기준 | 1차 정렬 | 2차 정렬 | 추가 고려사항 |
|-----------|----------|----------|---------------|
| **저소음** | rank ↑ | PPTE ↑ | - |
| **경량** | rank ↑ | total mass ↑ | 안전률 확인 필수 |
| **고효율** | rank ↑ | efficiency ↓ | - |
| **컴팩트** | rank ↑ | CenterDistance ↑ | - |
| **고강도** | rank ↑ | min(SF_bending, SF_contact) ↓ | - |
| **복합 기준** | rank=1 필터링 | 트레이드오프 설명 | Rank 1 내에서 각 지표 비교 |

(↑: 오름차순, ↓: 내림차순)

### LLM 응답 템플릿

**단일 성능 기준**:
```
[성능 기준]을 위해 Pareto rank와 [지표]를 기준으로 정렬했습니다:

| Rank | 모듈 | z1 | z2 | [주요 지표] | [보조 지표1] | [보조 지표2] |
|------|------|----|----|-------------|--------------|--------------|
| 1    | ...  | .. | .. | ...         | ...          | ...          |

**분석**: Rank 1 중 [N]번 케이스가 [성능 기준]에 가장 적합
**추천**: [모듈 X, z1=Y, z2=Z]
```

**복합 성능 기준**:
```
[성능1] + [성능2]를 고려하여 Pareto front(Rank 1) 솔루션 제시:

| Rank | 모듈 | z1 | z2 | [지표1] | [지표2] | [지표3] | 종합평가 |
|------|------|----|----|---------|---------|---------|----------|
| 1    | ...  | .. | .. | ...     | ...     | ...     | 균형     |
| 1    | ...  | .. | .. | ...     | ...     | ...     | [성능1]우선 |
| 1    | ...  | .. | .. | ...     | ...     | ...     | [성능2]우선 |

**트레이드오프**:
- 1번: [지표1]과 [지표2]의 균형 우수 ✨ 추천
- 2번: [지표1]은 우수하나 [지표2]는 다소 열등
- 3번: [지표2]는 우수하나 [지표1]은 다소 열등
```

---

## 주요 시나리오 (간략)

### 1. 구체적 제원 제공 (기본 워크플로우)
```
요청: "모듈 3, 잇수 20-60, 헬리컬각 15도 설계"
→ initialize → modify_gear_data → calc_geometry → calc_load_case
  → get_allresults_summary (표 표시) → get_gear_report 
```

### 2. 러프한 조건 (SimpleSizing 워크플로우)
```
요청: "기어비 3, 모듈 2~4 사이로 찾아줘"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (rank+지표 기준 표 표시)
  → 사용자 선택 → modify_gear_data → calc_geometry → calc_load_case
```

### 3. 성능 기준 요청 (SimpleSizing 워크플로우)
```
요청: "저소음 기어, 기어비 3"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (rank ↑ → PPTE ↑ 정렬, 표 표시)
  → Rank 1 중 PPTE 최소 케이스 추천 → 사용자 선택 → 최종 검증
```

### 4. 복합 성능 기준 (SimpleSizing 워크플로우)
```
요청: "경량+저소음, 기어비 4"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (Rank 1 필터링 → total mass + PPTE 비교)
  → 트레이드오프 설명 → 사용자 선택 → 최종 검증
```

---

## 주의사항

### 필수 실행 순서
- calc_geometry() 전: modify_gear_data() 또는 load_GearDesign_data()
- calc_load_case() 전: calc_geometry() 필수
- get_gear_report() 전: calc_load_case() 필수

### 기어비 설정
- Gear pair: z2/z1
- Three gear: z3/z1
- Planetary: z3/z1 (링기어/선기어)
- Double pinion planetary: z3/z1

### 세션 관리
- 세션 타임아웃: 1시간 자동 삭제
- 출력 디렉토리: `outputs/{session_id}/`

### 오류 처리
- 모든 함수는 `success` 필드로 성공/실패 표시
- `change_summary`로 변경사항 검증
- 경로 불일치 시 LLM의 JSON 키 확인

---

## 체크리스트

### 워크플로우 선택
- [ ] 성능 기준("저소음", "경량", "고효율") → SimpleSizing
- [ ] 모듈/잇수 구체적 수치 → 기본 워크플로우
- [ ] 범위/미지정/추상적 표현 → SimpleSizing

### 실행
- [ ] initialize() 세션 생성
- [ ] session_id 모든 함수에 전달
- [ ] calc_geometry → calc_load_case 순서
- [ ] SimpleSizing: simple_sizing_gearpair → get_simplesizing_results → 선택 → modify_gear_data

### 결과 표시 (필수!)
- [ ] get_allresults_summary() → **마크다운 표**
- [ ] get_simplesizing_results() → **rank 기반 분석 + 표**
- [ ] calc_load_case() 메시지 전달

### SimpleSizing 성능 분석 (핵심!)
- [ ] **모든 분석 1차 정렬: rank ↑**
- [ ] 저소음: 2차 PPTE ↑
- [ ] 경량: 2차 total mass ↑ (안전률 확인)
- [ ] 고효율: 2차 efficiency ↓
- [ ] 복합: Rank 1 필터링 → 트레이드오프 설명
- [ ] **Rank 2+ 추천 금지** (특별한 이유 없으면)

### 오류 처리
- [ ] success 필드 확인
- [ ] change_summary 검증
- [ ] 기어비 요청 시 기어 타입 고려

---

## 요약: 가장 중요한 3가지

1. **워크플로우 선택**: 성능 기준/범위/추상적 표현 → SimpleSizing, 구체적 제원 → 기본
2. **SimpleSizing 분석**: 반드시 rank 1차 정렬 → Rank 1 중에서 요청 지표 기준 선택
3. **결과 표시**: get_allresults_summary()와 get_simplesizing_results()는 **항상 표로 표시**
