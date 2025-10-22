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
    ↓
워크플로우 실행 → 결과 평가
    ↓
[결과 만족?]
    ├─ YES → 종료 (출력물 생성)
    └─ NO (개선 필요)
        ↓
    [개선 방법 선택]
        ├─ 미세 조정 (치폭/헬리컬각 등) → 기본 워크플로우 재수행
        └─ 모듈/잇수 재탐색 필요 → SimpleSizing 워크플로우 재수행
    ↓
(최대 5회 반복 가능)
```

### 1️⃣ 기본 워크플로우 (구체적 제원 제공 시)

**조건**: 모듈, 잇수 등 **모두 구체적 수치**로 제공
**예시**: "모듈 3, 잇수 20-60, 헬리컬각 15도"

**실행 순서**:
```
initialize() → modify_gear_data() → calc_geometry() → calc_load_case()
→ get_allresults_summary() (표로 표시 필수)
→ [결과 평가]
   ├─ 만족 → get_2D_image/get_gear_report/get_3d_image/get_3d_modeling → 종료
   └─ 개선 필요 → modify_gear_data() → calc_geometry() → calc_load_case() (반복)
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
→ 사용자 선택 → apply_simplesizing_case(row_index)
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ [결과 평가]
   ├─ 만족 → get_2D_image/get_gear_report/get_3d_image/get_3d_modeling → 종료
   └─ 개선 필요
      ├─ 미세 조정 (치폭/헬리컬각 등) → modify_gear_data() → calc_geometry() → calc_load_case() (반복)
      └─ 모듈/잇수 재탐색 → simple_sizing_gearpair() → get_simplesizing_results() (반복)
```

### 3️⃣ 결과 평가 및 개선 가이드

**결과 평가 기준**:
- **안전률**: Contact/Bending 안전률이 요구 안전률 충족 여부
- **성능 지표**: PPTE, 질량, 효율, overlap ratio 등이 목표값 달성 여부
- **제약 조건**: 중심거리, 치폭, 헬리컬각 등이 허용 범위 내 여부

**개선 방법 선택**:

| 개선 필요 사항 | 권장 워크플로우 | 비고 |
|---------------|----------------|------|
| 치폭/헬리컬각/압력각 조정 | 기본 워크플로우 | modify_gear_data()로 미세 조정 |
| 안전률 균형 조정 (모듈 변경) | 기본 워크플로우 | 모듈만 변경하고 재계산 |
| 모듈/잇수 재탐색 필요 | SimpleSizing 워크플로우 | 탐색 범위 조정 후 재수행 |
| 성능 기준 미달 (PPTE, 질량 등) | SimpleSizing 워크플로우 | 치폭/헬리컬각 범위 변경 후 재수행 |

**반복 제한**: 최대 5회까지 반복 가능, 그 이상 필요 시 사용자에게 제약 조건 완화 제안

---

## 핵심 도구

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

### SimpleSizing
- **`simple_sizing_gearpair(user_message, session_id)`**: 다양한 조합 계산
- **`get_simplesizing_results(session_id, return_all=False, top_n=100)`**: 결과 조회
  - 반환 구조: 각 결과에 `index` (원본 row_index) 포함
- **`apply_simplesizing_case(row_index, session_id)`**: 선택한 케이스 적용
  - **row_index는 원본 DataFrame의 인덱스** (`index` 필드 값)
  - 적용 후 calc_geometry → calc_load_case 필수

---

## SimpleSizing 상세 가이드

### 파라미터 탐색 범위

**SimpleSizing이 탐색하는 파라미터** (최소/최대 범위 내 조합 생성):
- **모듈 (m_n)**: 최소값 ~ 최대값 범위
- **잇수 (z_pinion)**: 최소값 ~ 최대값 범위

**SimpleSizing에서 고정되는 파라미터** (입력값 그대로 사용):
- **치폭 (Facewidth)**: 단일 고정값
- **압력각 (α_n)**: 단일 고정값
- **헬리컬각 (β)**: 단일 고정값

**⚠️ 중요**: SimpleSizing은 치폭/압력각/헬리컬각을 변경하면서 탐색하지 않습니다!

**치폭/헬리컬각 Case Study가 필요한 경우**:
```
[Case 1: 치폭 30mm, 헬리컬각 15°]
→ modify_gear_data("치폭 30mm, 헬리컬각 15도")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ 최적 케이스 선택 및 성능 기록

[Case 2: 치폭 40mm, 헬리컬각 20°]
→ modify_gear_data("치폭 40mm, 헬리컬각 20도")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ 최적 케이스 선택 및 성능 기록

→ 모든 Case 비교 후 최종 선택
```

### 성능 기준 분석

**DataFrame 주요 컬럼**:
- **`rank`**: Pareto rank (낮을수록 우수, Rank 1 = Pareto front)
- **`PPTE`**: 전달오차 (낮을수록 좋음)
- **`total mass`**: 총 질량 (낮을수록 좋음)
- **`efficiency`**: 효율 (높을수록 좋음)
- 기타: `module`, `z1`, `z2`, `CenterDistance`, `SF_bending`, `SF_contact`

**분석 원칙 (절대 규칙!)**:
1. **모든 분석에서 `rank`를 1차 정렬 기준**으로 사용
2. **Rank 1 솔루션 중에서** 요청된 성능 지표 기준으로 2차 정렬
3. **Rank 2+ 추천 금지** (특별한 이유 없으면)

**성능 기준별 정렬 방법**:

| 성능 기준 | 1차 정렬 | 2차 정렬 | 추가 고려사항 |
|-----------|----------|----------|---------------|
| **저소음** | rank ↑ | PPTE ↑ | Overlap ratio ≈ 1 또는 2 |
| **경량** | rank ↑ | total mass ↑ | 안전률 확인 필수 |
| **고효율** | rank ↑ | efficiency ↓ | - |
| **컴팩트** | rank ↑ | CenterDistance ↑ | - |
| **고강도** | rank ↑ | min(SF_bending, SF_contact) ↓ | - |
| **복합 기준** | rank=1 필터링 | 트레이드오프 설명 | Rank 1 내에서 각 지표 비교 |

(↑: 오름차순, ↓: 내림차순)

### row_index vs display_order

**핵심**: SimpleSizing 결과를 rank/지표로 정렬하면 **표시 순서와 원본 인덱스가 달라집니다**!

**LLM 응답 템플릿**:
```
SimpleSizing 결과 (rank + PPTE 기준 정렬):

| Display | row_index | 모듈 | z1 | z2 | Rank | PPTE | S_H | S_F | 평가 |
|---------|-----------|------|----|----|------|------|-----|-----|------|
| 1 | 45 | 3.75 | 23 | 94 | 1 | 0.82 | 1.74 | 5.73 | ⭐ 추천 |
| 2 | 5 | 4.0 | 21 | 86 | 1 | 0.95 | 1.61 | 5.48 | - |
| 3 | 102 | 3.5 | 24 | 101 | 1 | 1.12 | 1.68 | 5.92 | - |

**추천**: Display 1번 케이스 (row_index=45)
  - 모듈 3.75mm, z1=23, z2=94
  - PPTE 최소 (0.82), 안전률 양호

→ apply_simplesizing_case(row_index=45, session_id) 실행 예정
```

**주의사항**:
- **Display**: 표 순서 (1, 2, 3, ...) → 사용자 소통용
- **row_index**: 원본 인덱스 (`index` 필드) → **apply_simplesizing_case()에 필수**
- **절대 Display 번호를 apply_simplesizing_case()에 전달하지 말 것!**

### 경량 설계 가이드 ⭐
- **경량의 핵심**: 요구 안전율을 만족하면서, 무게 최소화. 이를 위해서는 실제 안전율이 요구 안전율에 근접해야 함. 즉, 요구 안전율이 1.2라면 실제 안전율도 1.2에 just한 사양이여야 함.
- **안전율 balance 유지**: 확인해야할 주요 안전율인 Contact/Bending 안전율 모두 요구 안전율에 근접해야 함. 
   1) Contact은 만족하나, Bending이 과도한 경우 → 모듈이 크게 설정되어있음. 모듈 감소 필요
   2) Bending은 만족하나, Contact이 과도한 경우 → 모듈이 작게 설정되어있음. 모듈 증가 필요

### 저소음 설계 가이드 ⭐

**핵심 개념**:
- **저소음의 핵심**: PPTE(전달오차) 최소화 + Overlap ratio 최적화
- **Overlap ratio 목표**: **1.0 (권장 0.95-1.05)** 또는 **2.0 (권장 1.95-2.05)**
  - 초저소음: 1.0보다 2.0 우위 (경량/효율 희생)
  - 경량+저소음: 1.0 우선 목표
- **⚠️ 제약**: 헬리컬각 25° 미만 권장
- **⚠️ SimpleSizing 한계**: Overlap ratio는 SimpleSizing 결과에 없음 → `get_allresults_summary()`에서만 확인 가능

**[프로세스 A] SimpleSizing 1번 + 미세 조정** (일반적, 빠름):
```
1. SimpleSizing 실행 (Rank 1 중 PPTE 최소 케이스 선택)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. get_allresults_summary()에서 overlap ratio 확인
4. overlap ratio가 목표(1.0 or 2.0)와 차이 크면:
   → modify_gear_data()로 치폭/헬리컬각 조정 → 재계산 → 최대 5번 반복
```

**[프로세스 B] 치폭/헬리컬각 Case Study** (최적, 시간 소요):
```
1. 치폭/헬리컬각 조합별로 SimpleSizing 수행 (예: 30mm/15°, 40mm/20°, 50mm/25°)
2. 각 Case의 최적 솔루션 비교 (PPTE, overlap ratio, 질량, 효율)
3. 사용자 요구에 맞는 Case 선택 → apply_simplesizing_case()
```

**LLM 응답 예시 (프로세스 A)**:
```
SimpleSizing 결과 (Rank 1, PPTE 최소):
- 모듈 3.75, z1=23, z2=94 적용
- calc 후 overlap ratio = 1.35 확인

초저소음 목표 (overlap ratio → 2.0):
→ 치폭 30→50mm, 헬리컬각 15→22° 조정
→ 재계산: overlap ratio = 2.3
→ 치폭 50→40mm, 헬리컬각 22→20° 조정
→ 재계산: overlap ratio = 1.96 ✅
⚠️ 질량 1.2→1.5kg, 효율 99.1→98.8% 감소
```

**LLM 응답 예시 (프로세스 B)**:
```
치폭/헬리컬각 Case Study 결과:

| Case | 치폭 | 헬리컬각 | PPTE | Overlap | 질량 | 효율 | 평가 |
|------|------|----------|------|---------|------|------|------|
| 1 | 30mm | 15° | 0.95 | 1.15 | 1.2kg | 99.1% | 경량우수, 저소음보통 |
| 2 | 40mm | 20° | 0.82 | 1.85 | 1.45kg | 98.9% | ⭐균형 |
| 3 | 50mm | 25° | 0.78 | 2.02 | 1.68kg | 98.6% | 초저소음, 질량불리 |

추천: Case 2 (overlap≈2.0, PPTE우수, 질량/효율 타협 적절)
```

### SimpleSizing 결과 부족 시 대응

SimpleSizing 결과가 0개 또는 매우 적은 경우 조건 완화:

1. **모듈 범위 확대**: 최소값 감소 또는 최대값 증가 (예: 2~4 → 1.5~5)
2. **잇수 범위 확대**: 최소값 감소 또는 최대값 증가 (예: z_min=15 → 12)
3. **치폭 조정**: 치폭 증가 또는 범위로 변경 (예: 30mm → 30~50mm)
4. **최대 계산 횟수 증가**: 더 많은 조합 탐색
5. **안전률 기준 완화**: 최소 안전률 요구사항 낮추기

**LLM 응답 예시**:
```
SimpleSizing 결과가 0건입니다. 현재 조건(모듈 2~2.5, z_min=20)이 너무 엄격합니다.
다음 중 하나를 조정해주세요:
1. 모듈 범위 확대 (예: 1.5~3.0)
2. 최소 잇수 감소 (예: z_min=15)
3. 치폭 증가 또는 범위 지정 (예: 30~50mm)
```

---

## 주요 시나리오

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
  → 사용자에게 추천 (Display 1번, row_index=45)
  → apply_simplesizing_case(row_index=45)
  → calc_geometry → calc_load_case → get_allresults_summary
```

### 3. 저소음 설계 (SimpleSizing + Overlap Ratio 최적화)
```
요청: "저소음 기어, 기어비 3, 초저소음으로 설계해줘"

[1단계: SimpleSizing]
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (rank ↑ → PPTE ↑ 정렬)
  → Rank 1 중 PPTE 최소 선택 (Display 1번, row_index=45)
  → apply_simplesizing_case(row_index=45)
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.35 확인)

[2단계: Overlap Ratio 최적화] (최대 5회까지 반복 가능)
→ modify_gear_data("치폭 45mm, 헬리컬각 20도로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.7 확인)
  → modify_gear_data("치폭 55mm, 헬리컬각 20도로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.95 확인) ✅
```

### 4. 복합 성능 기준 (SimpleSizing 워크플로우)
```
요청: "경량+저소음, 기어비 4"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (Rank 1 필터링 → total mass + PPTE 비교)
  → 트레이드오프 설명 (Display 1번: 경량 우선, Display 2번: 저소음 우선, Display 3번: 균형)
  → apply_simplesizing_case(row_index=34) → calc_geometry → calc_load_case
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

## 요약: 가장 중요한 7가지

1. **워크플로우 선택**: 성능 기준/범위/추상적 표현 → SimpleSizing, 구체적 제원 → 기본
2. **SimpleSizing 파라미터**: 모듈/잇수만 탐색, 치폭/압력각/헬리컬각은 고정
3. **성능 분석**: 반드시 rank 1차 정렬 → Rank 1 중 요청 지표 기준 선택
4. **row_index**: Display 번호가 아닌 `index` 필드 값을 apply_simplesizing_case()에 전달
5. **저소음 설계**: 프로세스 A (빠름) vs B (최적), overlap ratio는 get_allresults_summary()에서만 확인
6. **결과 표시**: get_allresults_summary()와 get_simplesizing_results()는 항상 표로 표시 (row_index 포함)
7. **최종 결과 평가**: 6번 결과에서 미흡한 점 발생 시 개선을 위한 워크플로수 재수행. 결과 만족 시 종료 (최대 5회 반복 가능)
