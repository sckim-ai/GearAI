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

**결과 평가 3단계 기준** (⚠️ 과도함도 개선 필요!):

| 항목 | 미달 (NG) | 적정 (OK) | 과도 (개선 필요) |
|------|-----------|-----------|-----------------|
| **안전률** | 요구값 미만 | 요구값의 1.0~1.3배 | 요구값의 1.5배 이상 |
| **Overlap ratio** | - | 목표값 ±0.15 이내 | 목표값에서 ±0.15 초과 |
| **제약 조건** | 범위 벗어남 | 범위 내 | - |

**안전률 평가 예시**:
- 요구 안전률 1.2인 경우:
  - 미달: 실제 1.1 (NG, 불안정)
  - 적정: 실제 1.25 (OK, 경량 최적)
  - 과도: 실제 2.0 (개선 필요, 과중량)

**Overlap ratio 평가 예시**:
- 목표 1.0인 경우:
  - 적정: 0.95~1.15 (OK)
  - 과도: 1.35 (개선 필요, 목표 1.0 또는 2.0에 맞춰야 함)
- 목표 2.0인 경우:
  - 적정: 1.85~2.15 (OK)
  - 과도: 1.35 (개선 필요, 목표값에서 너무 멂)

**개선 방법 선택**:

| 평가 결과 | 개선 필요 사항 | 권장 워크플로우 | 비고 |
|----------|---------------|----------------|------|
| 미달 | 안전률 부족 | 기본 | 모듈 증가 또는 치폭 증가 |
| 과도 | 안전률 과도 (경량 목표) | 기본 | 모듈 감소 또는 치폭 감소 |
| 과도 | Contact만 과도 | 기본 | 모듈 감소 |
| 과도 | Bending만 과도 | 기본 | 모듈 증가 |
| 과도 | Overlap ratio 부적정 | 기본 | 치폭/헬리컬각 조정 |
| 미달 | 모듈/잇수 재탐색 필요 | SimpleSizing | 탐색 범위 조정 후 재수행 |

**반복 제한**: 최대 5회까지 반복 가능, 그 이상 필요 시 사용자에게 제약 조건 완화 제안

---

## 핵심 도구

### 세션 관리
- **`initialize()`**: 세션 생성 및 IPC 시작 → `session_id` 반환 (모든 함수에 필수)
- **`delete_session(session_id)`**: 세션 및 파일 삭제

### 데이터 입력/수정
- **`modify_gear_data(user_message, session_id)`**: 자연어로 기어 데이터 수정
  - 기어비 요청 시 자동으로 잇수비 계산
  - 작동조건 변경 시 사용자 요구에 정확하게 부합하도록 user_message 도출
  - 기어타입에 따라 토크/속도 조건은 아래의 규칙을 준수하여 변경해야 함 
   1) CASE1: Gear Pair 인 경우 아래의 정보가 모두 포함되어야 함
    - Gear1/Gear2 속도 중 1개 (Gear1/Gear2 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2 파워 중 1개, 또는 Gear1/Gear2 토크 중 1개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2는 사용자의 어휘에 따라 입력/출력 기어 or Pinion/Wheel 기어 등으로 불릴 수 있음
    - 예시1: 입력속도 1000 rpm, 출력토크 50Nm -> OK
    - 예시2: 입력속도 1000 rpm, 출력속도 500 rpm, 출력토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: 입력속도 1000 rpm, 입력파워 100W, 출력토크 50Nm -> NG (입력 파워와 토크 모두 주어짐)

   2) CASE2: Three Gear 
    - Gear1/Gear2/Gear3 의 속도 중 1개 (입/출력 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3 의 파워 중 2개, 또는 토크 중 2개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3은 사용자의 어휘에 따라 입력/아이들러/출력 기어 or Pinion/Idler/Wheel 기어 등으로 불릴 수 있음
    - 예시1: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 토크 50Nm -> OK
    - 예시2: Gear1 속도 1000 rpm, Gear2 속도 500 rpm, Gear3 토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 파워 50W -> NG (입력 파워와 토크 모두 주어짐)

   3) CASE3: Simple Planetary, Double Pinion Planetary
    - Sun/Carrier/Ring 의 속도 중 2개 (유성기어의 속도는 3개의 입력 중 2개로 결정되기 때문에 반드시 2개 입력 필요)
    - Sun/Carrier/Ring 의 파워 중 1개, 또는 토크 중 1개 (유성기어의 파워 또는 토크는 1개의 입력과 입력된 속도로 나머지가 모두 계산됨)

    #### 입출력 작동조건 단위 (사용자가 단위계를 입력하지 않은 경우 아래 단위로 간주함)
    - 시간 단위: "hr" (예: "100 hr", "5000 시간" 등)
    - 속도 단위: "rpm" (예: "1000rpm", "3600rpm" 등)
    - 파워 단위: "kW" (예: "100 kW", "5kW" 등) 
    - 토크 단위: "Nm" (예: "50Nm", "200Nm" 등)
  - 매크로 제원 변경 시 CDMethod=1 자동 설정
- **`load_GearDesign_data(file_path, session_id)`**: JSON/GD1 파일 로드
- **`save_GearDesignData(session_id)`**: 현재 데이터 JSON 저장

### 계산 수행
- **`calc_geometry(session_id)`**: 기하학적 계산 (calc_load_case 전 필수)
- **`calc_load_case(session_id)`**: 하중 계산 (메시지 반환)

### 결과 조회
- **`get_allresults_summary(session_id)`**: 계산 결과 요약 → **summary에 포함된 모든 결과를 동일한 포멧의 표로 표시 필수**
  - 전제조건: calc_geometry + calc_load_case 완료
- **`get_messages(session_id)`**: 계산 경고/오류 메시지 조회

### 출력물 생성
- **`get_2D_image(session_id)`**: 2D 치물림 이미지 (PNG)
- **`get_3d_image(session_id, width, height)`**: 3D 이미지 (PNG)
- **`get_3d_modeling(session_id)`**: 3D 모델 (STEP)
- **`get_gear_report(session_id)`**: 설계 보고서 (PDF)

### 저소음 설계 최적화 도구
- **`calculate_facewidth_for_ep_beta(target_overlap_ratio, helix_angle_deg, normal_module, session_id)`**:
  - 목표 겹침비율(εβ)을 달성하기 위한 치폭(b) 계산
  - 계산식: b = (εβ × π × mn) / sin(β)
  - 예시: εβ=1.3, β=25°, mn=2.5 → b ≈ 24.2mm
- **`calculate_helixangle_for_ep_beta(target_overlap_ratio, face_width, normal_module, session_id)`**:
  - 목표 겹침비율(εβ)을 달성하기 위한 헬릭스각(β) 계산
  - 계산식: β = arcsin((εβ × π × mn) / b)
  - 예시: εβ=1.3, b=25mm, mn=2.5 → β ≈ 23.5°

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

**핵심 개념**:
- **경량의 핵심**: 요구 안전율을 만족하면서 무게 최소화 → 실제 안전율이 요구값의 **1.0~1.3배 이내**여야 함
- **⚠️ 과도 조건**: 안전율이 요구값의 **1.2배 이상**이면 개선 필요 (과중량)

**[프로세스 A] SimpleSizing 1번 + 미세 조정** (일반적, 빠름):
```
1. SimpleSizing 실행 (Rank 1 중 중량 최소 케이스 선택)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. get_allresults_summary()에서 S_H, S_F 모두 확인
4. S_H, S_F가 목표 안전율 대비 1.2배 이상 크면:
   → modify_gear_data()로 모듈/치폭/잇수(기어비 유지 한) 조정 → 재계산 → 최대 5번 반복
```

**안전률 평가 기준** (요구 안전율 S_H=1.2, S_F=1.5 예시):

| 실제 안전률 | 평가 | 조치 |
|-----------|------|------|
| S_H=1.1, S_F=1.1 | 미달 | 모듈 증가 또는 치폭 증가 필요 |
| S_H=1.25, S_F=1.60 | 적정 ✅ | 경량 최적화 달성 |
| S_H=2.0, S_F=5.0 | 과도 (개선 필요) | 모듈/치폭 감소 필요 (과중량) |
| S_H=1.2, S_F=3.5 | 불균형 (개선 필요) | Bending 과도 → 모듈 감소/잇수 증가 |
| S_H=2.5, S_F=1.6 | 불균형 (개선 필요) | Contact 과도 → 모듈 증가/잇수 감소 |

**안전률 균형 조정**:
1. **Contact은 적정, Bending만 과도** → 모듈 감소/잇수 증가(기어비는 유지)
2. **Bending은 적정, Contact만 과도** → 모듈 증가/잇수 감소(기어비는 유지)
3. **둘 다 과도** → 모듈과 치폭 모두 감소

**LLM 응답 예시**:
```
안전률 평가 (요구: S_H=1.2, S_F=1.2):
- 실제: S_H=2.1 (과도, 요구값의 1.75배), S_F=5.3 (과도, 요구값의 4.4배)
- 평가: 안전률 과도 → 과중량 설계 (개선 필요)
- 조치: Bending이 더 과도하므로 모듈 감소 우선 (4.0 → 3.5mm)

개선 후:
- 실제: S_H=1.7, S_F=3.8 (여전히 과도)
- 추가 조치: 모듈 추가 감소 (3.5 → 3.0mm)
```

### 저소음 설계 가이드 ⭐

**핵심 개념**:
- **저소음의 핵심**: PPTE(전달오차) 최소화 + Overlap ratio 최적화
- **Overlap ratio 목표**: **1.0** 또는 **2.0** (정수에 가까울수록 좋음)
  - 초저소음: 1.0보다 2.0 우위 (경량/효율 희생)
  - 경량+저소음: 1.0 우선 목표
- **⚠️ 제약**: 헬리컬각 25° 미만 권장
- **⚠️ SimpleSizing 한계**: Overlap ratio는 SimpleSizing 결과에 없음 → `get_allresults_summary()`에서만 확인 가능

**Overlap ratio 평가 기준**:

| Overlap ratio | 목표 1.0 평가 | 목표 2.0 평가 | 조치 |
|--------------|-------------|-------------|------|
| 0.95~1.05 | 적정 ✅ | 부적정 | 목표 1.0: 만족 |
| 1.95~2.05 | 부적정 | 적정 ✅ | 목표 2.0: 만족 |
| 1.20~1.80 | 부적정 (개선 필요) | 부적정 (개선 필요) | 1.0 또는 2.0에 가깝게 조정 필요 |
| 1.35 | 부적정 (개선 필요) | 부적정 (개선 필요) | 중간값: 1.0 또는 2.0 중 선택 후 조정 |

**조정 방법** (3가지):

**방법 1: 수동 조정** (시행착오)
- **Overlap ratio 증가**: 치폭 증가 또는 헬리컬각 증가
- **Overlap ratio 감소**: 치폭 감소 또는 헬리컬각 감소

**방법 2: 계산 기반 치폭 조정** (정확, 권장 ⭐)
```
1. get_allresults_summary()에서 현재 overlap ratio, 헬릭스각, 모듈 확인
2. calculate_facewidth_for_ep_beta(목표_overlap, 헬릭스각, 모듈, session_id) 호출
3. 반환된 치폭을 modify_gear_data()로 적용
4. calc_geometry() → calc_load_case() → get_allresults_summary() 재확인
```

**방법 3: 계산 기반 헬릭스각 조정** (치폭 고정 시)
```
1. get_allresults_summary()에서 현재 overlap ratio, 치폭, 모듈 확인
2. calculate_helixangle_for_ep_beta(목표_overlap, 치폭, 모듈, session_id) 호출
3. 반환된 헬릭스각을 modify_gear_data()로 적용
4. calc_geometry() → calc_load_case() → get_allresults_summary() 재확인
```

**⚠️ 주의**:
- 헬릭스각은 25° 미만 권장 (효율 및 축하중 고려)
- 치폭이 너무 크면 질량 및 비용 증가
- 계산된 값이 실제 적용 가능한지 제약조건 확인 필요

**LLM 응답 예시 (방법 1: 수동 조정)**:
```
Overlap ratio 평가 (목표: 2.0):
- 실제: 1.35 (부적정, 목표 2.0에서 0.65 차이)
- 평가: 개선 필요 (1.0도 2.0도 아닌 중간값)
- 조치: 목표 2.0 달성을 위해 치폭/헬리컬각 증가 (치폭 30→45mm)

개선 후:
- 실제: 1.75 (여전히 부적정)
- 추가 조치: 치폭 추가 증가 (45→55mm) 또는 헬리컬각 증가 (15→20°)

최종:
- 실제: 2.05 (적정 ✅, 목표값 ±0.05 이내)
```

**LLM 응답 예시 (방법 2: 계산 기반 치폭 조정, 권장 ⭐)**:
```
Overlap ratio 평가 (목표: 2.0):
- 실제: 1.35 (부적정, 목표 2.0에서 0.65 차이)
- 현재: 치폭 30mm, 헬릭스각 20°, 법선모듈 2.5mm

정확한 치폭 계산:
→ calculate_facewidth_for_ep_beta(2.0, 20.0, 2.5, session_id)
→ 결과: 필요 치폭 = 45.8mm

적용:
→ modify_gear_data("치폭 45.8mm로 변경")
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ 최종 overlap ratio = 2.00 ✅ (1회 조정으로 목표 달성)
```

**LLM 응답 예시 (방법 3: 계산 기반 헬릭스각 조정, 치폭 제약 시)**:
```
Overlap ratio 평가 (목표: 1.0, 치폭은 30mm 고정):
- 실제: 0.75 (부적정, 목표 1.0에서 0.25 부족)
- 현재: 치폭 30mm, 헬릭스각 15°, 법선모듈 2.5mm

정확한 헬릭스각 계산:
→ calculate_helixangle_for_ep_beta(1.0, 30.0, 2.5, session_id)
→ 결과: 필요 헬릭스각 = 19.8°

적용:
→ modify_gear_data("헬릭스각 19.8도로 변경")
→ calc_geometry() → calc_load_case() → get_allresults_summary()
→ 최종 overlap ratio = 1.00 ✅ (1회 조정으로 목표 달성)

⚠️ 헬릭스각이 19.8°로 증가하여 효율 약간 감소 예상 (99.2% → 98.9%)
```

**[프로세스 A] SimpleSizing 1번 + 수동 미세 조정** (빠름, 시행착오):
```
1. SimpleSizing 실행 (Rank 1 중 PPTE 최소 케이스 선택)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. get_allresults_summary()에서 overlap ratio 확인
4. overlap ratio가 목표(1.0 or 2.0)와 차이 크면:
   → modify_gear_data()로 치폭/헬리컬각 수동 조정 → 재계산 → 최대 5번 반복
   (예: 치폭 30→40→50mm로 점진적 증가)
```

**[프로세스 A2] SimpleSizing 1번 + 계산 기반 조정** (빠름, 정확, ⭐ 권장):
```
1. SimpleSizing 실행 (Rank 1 중 PPTE 최소 케이스 선택)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. get_allresults_summary()에서 overlap ratio, 헬릭스각, 모듈, 치폭 확인
4. overlap ratio가 목표(1.0 or 2.0)와 차이 크면:
   → calculate_facewidth_for_ep_beta() 또는 calculate_helixangle_for_ep_beta() 호출
   → 계산된 값을 modify_gear_data()로 적용
   → calc_geometry → calc_load_case → get_allresults_summary() 재확인
   (일반적으로 1~2회 반복으로 목표 달성)
```

**[프로세스 B] 치폭/헬리컬각 Case Study** (최적, 시간 소요):
```
1. 목표 overlap ratio에 맞는 치폭/헬리컬각 조합 계산:
   - Case 1: 헬릭스각 15° 고정 → calculate_facewidth_for_ep_beta(목표, 15°, 예상모듈)
   - Case 2: 헬릭스각 20° 고정 → calculate_facewidth_for_ep_beta(목표, 20°, 예상모듈)
   - Case 3: 치폭 30mm 고정 → calculate_helixangle_for_ep_beta(목표, 30mm, 예상모듈)
   (예상모듈: 탐색 범위의 중간값 또는 사용자 지정값)

2. 각 Case별로 SimpleSizing 수행:
   → modify_gear_data("치폭 X, 헬릭스각 Y")
   → simple_sizing_gearpair() → get_simplesizing_results()
   → Rank 1 중 PPTE 최소 케이스 선택 및 성능 기록

3. 모든 Case 비교 (PPTE, overlap ratio, 질량, 효율, 안전률)

4. 사용자 요구에 맞는 Case 선택:
   → apply_simplesizing_case() → calc_geometry → calc_load_case
   → get_allresults_summary()에서 최종 검증
```

**LLM 응답 예시 (프로세스 A: 수동 조정)**:
```
SimpleSizing 결과 (Rank 1, PPTE 최소):
- 모듈 3.75, z1=23, z2=94 적용
- calc 후 overlap ratio = 1.35 확인

초저소음 목표 (overlap ratio → 2.0):
→ 치폭 30→50mm 조정
→ 재계산: overlap ratio = 2.3
→ 치폭 50→45mm 조정
→ 재계산: overlap ratio = 1.96 ✅ (3회 시행착오)
⚠️ 질량 1.2→1.5kg, 효율 99.1→98.9% 감소
```

**LLM 응답 예시 (프로세스 A2: 계산 기반 조정, ⭐ 권장)**:
```
SimpleSizing 결과 (Rank 1, PPTE 최소):
- 모듈 3.75, z1=23, z2=94 적용
- calc 후: overlap ratio = 1.35, 헬릭스각 20°, 법선모듈 2.5mm, 치폭 30mm

초저소음 목표 (overlap ratio → 2.0):
→ calculate_facewidth_for_ep_beta(2.0, 20.0, 2.5, session_id)
→ 계산 결과: 필요 치폭 = 45.8mm

적용 및 재계산:
→ modify_gear_data("치폭 45.8mm로 변경")
→ calc_geometry → calc_load_case
→ 최종: overlap ratio = 2.00 ✅ (1회 조정으로 목표 달성!)
⚠️ 질량 1.2→1.5kg, 효율 99.1→98.9% 감소
```

**LLM 응답 예시 (프로세스 B: 치폭/헬리컬각 Case Study)**:
```
목표 overlap ratio = 2.0, 예상 모듈 = 3.0mm (탐색 범위 중간값)

치폭/헬리컬각 조합 계산:
→ Case 1 (β=15° 고정): calculate_facewidth_for_ep_beta(2.0, 15, 3.0) = 72.7mm
→ Case 2 (β=20° 고정): calculate_facewidth_for_ep_beta(2.0, 20, 3.0) = 55.2mm
→ Case 3 (b=40mm 고정): calculate_helixangle_for_ep_beta(2.0, 40, 3.0) = 28.1°

SimpleSizing 수행 결과:

| Case | 치폭 | 헬리컬각 | 모듈 | z1 | z2 | PPTE | Overlap | 질량 | 효율 | 평가 |
|------|------|----------|------|----|----|------|---------|------|------|------|
| 1 | 72.7mm | 15° | 3.25 | 22 | 90 | 0.89 | 2.01 | 1.85kg | 99.2% | 중량 불리 |
| 2 | 55.2mm | 20° | 3.50 | 23 | 94 | 0.82 | 1.98 | 1.52kg | 98.9% | ⭐균형 |
| 3 | 40.0mm | 28.1° | 3.75 | 21 | 86 | 0.78 | 2.05 | 1.38kg | 98.3% | 경량, 효율 불리 |

추천: Case 2 (overlap≈2.0 달성, PPTE 우수, 질량/효율 타협 적절)
→ apply_simplesizing_case(row_index=45) 실행
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

**방법 1: 수동 조정 (시행착오)**
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
→ modify_gear_data("치폭 45mm로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.7 확인)
  → modify_gear_data("치폭 50mm로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.95 확인) ✅
```

**방법 2: 계산 기반 조정 (정확, ⭐ 권장)**
```
요청: "저소음 기어, 기어비 3, overlap ratio 2.0으로 설계해줘"

[1단계: SimpleSizing]
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (rank ↑ → PPTE ↑ 정렬)
  → Rank 1 중 PPTE 최소 선택 (Display 1번, row_index=45)
  → apply_simplesizing_case(row_index=45)
  → calc_geometry → calc_load_case
  → get_allresults_summary
     (overlap ratio = 1.35, 헬릭스각 20°, 법선모듈 2.5mm, 치폭 30mm 확인)

[2단계: Overlap Ratio 정확 계산 및 적용]
→ calculate_facewidth_for_ep_beta(2.0, 20.0, 2.5, session_id)
  → 계산 결과: 필요 치폭 = 45.8mm
→ modify_gear_data("치폭 45.8mm로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 2.00 확인) ✅ (1회 조정으로 목표 달성!)
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

## 요약: 가장 중요한 8가지

1. **워크플로우 선택**: 성능 기준/범위/추상적 표현 → SimpleSizing, 구체적 제원 → 기본
2. **SimpleSizing 파라미터**: 모듈/잇수만 탐색, 치폭/압력각/헬리컬각은 고정
3. **성능 분석**: 반드시 rank 1차 정렬 → Rank 1 중 요청 지표 기준 선택
4. **row_index**: Display 번호가 아닌 `index` 필드 값을 apply_simplesizing_case()에 전달
5. **결과 평가 3단계**: 미달(NG) / 적정(OK) / **과도(개선 필요)**
   - **경량**: 안전률이 요구값의 1.2배 이상이면 과도 (과중량)
   - **저소음**: Overlap ratio가 목표값(1.0 또는 2.0) ±0.05 벗어나면 부적정
6. **저소음 설계**:
   - 프로세스 A (수동 조정, 시행착오) vs A2 (계산 기반, 정확 ⭐) vs B (Case Study, 최적)
   - Overlap ratio는 get_allresults_summary()에서만 확인
   - **계산 기반 조정 권장**: calculate_facewidth_for_ep_beta() 또는 calculate_helixangle_for_ep_beta() 사용
7. **결과 표시**: get_allresults_summary()와 get_simplesizing_results()는 항상 표로 표시 (row_index 포함)
8. **반복 개선**: 미달/과도 시 개선 워크플로우 재수행 (최대 5회 반복 가능)
