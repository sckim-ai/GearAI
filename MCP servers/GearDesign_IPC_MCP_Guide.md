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
  - 목표 겹침비율(εβ)을 달성하기 위한 치폭(b) 계산. 헬리컬각이 0인 경우 사용 불가!
  - 계산식: b = (εβ × π × mn) / sin(β)
  - 예시: εβ=1.3, β=25°, mn=2.5 → b ≈ 24.2mm
- **`calculate_helixangle_for_ep_beta(target_overlap_ratio, face_width, normal_module, session_id)`**:
  - 목표 겹침비율(εβ)을 달성하기 위한 헬릭스각(β) 계산. 헬리컬각이 25도 이상인 경우 치폭 증가 필요.
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

### 최적 기어 설계 가이드 ⭐

**핵심 개념**:
- **최적 기어**: 경량(Lightweight) + 고효율(High Efficiency) + 저소음(Low Noise) 동시 달성
- **3단계 프로세스**: 1) 경량 설계 우선 → 2) 저소음 설계 수행 → 3) 고효율 검증
- **⚠️ Trade-off 관리**: 각 단계에서 다른 성능 지표 영향 최소화

**전체 프로세스 플로우**:
```
[1단계] 경량 설계 (안전율 최적화)
  → Contact/Bending 안전율을 요구값의 1.0~1.3배로 조정
  → Micropitting은 참고만 (미달 허용)

[2단계] 저소음 설계 (Overlap Ratio 최적화)
  → 목표 overlap ratio (1.0 또는 2.0) 달성
  → 헬릭스각/치폭 조정 (효율 영향 최소화)

[3단계] 고효율 검증
  → 효율 확인 및 trade-off 판단
  → 효율 저하 > 5%이면 재조정 고려
```

---

#### 1단계: 경량 설계 (안전율 최적화)

**목표**: Contact(S_H), Bending(S_F) 안전율을 요구값의 **1.0~1.3배** 범위로 최적화

**핵심 원칙**:
- **⚠️ 중요**: **Contact(S_H)와 Bending(S_F)에만 집중**, Micropitting(S_MP)은 참고만
- Micropitting은 요구 안전율 미달해도 허용 (개선 불가능한 경우 많음)
- 안전율이 요구값의 **1.2배 이상**이면 과도 (개선 필요)

**SimpleSizing 기반 프로세스**:
```
1. SimpleSizing 실행 (Rank 1 중 PPTE 최소 또는 중량 최소 케이스 선택)
2. apply_simplesizing_case() → calc_geometry → calc_load_case
3. get_allresults_summary()에서 S_H(Contact), S_F(Bending) 확인 (S_MP는 참고만)
4. 안전율 평가 및 조정 (최대 5회 반복):
   - S_H, S_F가 요구값의 1.2배 이상 → 모듈/치폭 감소
   - S_H, S_F가 요구값 미만 → 모듈/치폭 증가
   - 불균형 시 → 모듈 조정 + 잇수 조정 (기어비/중심거리 유지)
```

**안전률 평가 기준** (요구 안전율 S_H=1.2, S_F=1.5 예시):

| 실제 안전률 | 평가 | 조치 |
|-----------|------|------|
| S_H=1.1, S_F=1.1 | 미달 | 모듈 증가 또는 치폭 증가 |
| S_H=1.25, S_F=1.60 | 적정 ✅ | 1단계 완료 → 2단계 진행 |
| S_H=2.0, S_F=5.0 | 과도 (개선 필요) | 모듈/치폭 감소 (과중량) |
| S_H=1.2, S_F=3.5 | 불균형 (개선 필요) | Bending 과도 → 모듈 감소 |
| S_H=2.5, S_F=1.6 | 불균형 (개선 필요) | Contact 과도 → 모듈 증가 |
| S_H=1.25, S_F=1.60, S_MP=0.8 | 적정 ✅ | Micropitting 미달이지만 OK |

**안전률 균형 조정**:
1. **Contact 적정, Bending 과도** → 모듈 감소
2. **Bending 적정, Contact 과도** → 모듈 증가
3. **둘 다 과도** → 잇수 조정을 통한 중심거리 감소, 치폭 감소
4. **Micropitting 미달** → 무시 (Contact/Bending에만 집중)

---

#### 2단계: 저소음 설계 (Overlap Ratio 최적화)

**목표**: Overlap ratio를 **1.0** 또는 **2.0**에 가깝게 조정하여 전달오차(PPTE) 최소화 (경량/효율 유지)

**핵심 원칙**:
- **경량+저소음**: Overlap ratio 1.0 우선 목표
- **초저소음**: Overlap ratio 2.0 목표 (경량/효율 일부 희생)
- **⚠️ 제약**: 헬릭스각 25° 미만 권장 (효율 및 축하중 고려)

**Overlap ratio 평가 기준**:

| Overlap ratio | 목표 1.0 평가 | 목표 2.0 평가 | 조치 |
|--------------|-------------|-------------|------|
| 0.95~1.05 | 적정 ✅ | 부적정 | 목표 1.0: 2단계 완료 → 3단계 진행 |
| 1.95~2.05 | 부적정 | 적정 ✅ | 목표 2.0: 2단계 완료 → 3단계 진행 |
| 1.20~1.80 | 부적정 (개선 필요) | 부적정 (개선 필요) | 1.0 또는 2.0 중 선택 후 조정 |

**계산 기반 조정 방법** (정확, 권장 ⭐):
```
1. get_allresults_summary()에서 현재 overlap ratio, 최소치폭, 모듈 확인
2. calculate_helixangle_for_ep_beta(목표_overlap, 치폭, 모듈, session_id) 호출
3-1. 반환된 헬릭스각 < 25° → modify_gear_data()로 헬릭스각만 조정
3-2. 반환된 헬릭스각 ≥ 25° → calculate_facewidth_for_ep_beta(목표_overlap, 25, 모듈)
     → 헬릭스각 25° + 계산된 치폭으로 modify_gear_data() 조정
4. calc_geometry() → calc_load_case() → get_allresults_summary() 재확인
5. 안전율 재검증: S_H, S_F가 여전히 적정 범위 내인지 확인
   - 안전율 미달 발생 시 → 1단계로 복귀 (모듈 재조정)
```

**⚠️ 주의**:
- 헬릭스각 증가 시 효율 감소 (일반적으로 1~3%)
- 치폭 증가 시 질량 증가 및 비용 증가
- **안전율 재검증 필수**: 치폭/헬릭스각 변경 시 안전율 변동 가능

---

#### 3단계: 고효율 검증 및 Trade-off 판단

**목표**: 효율 확인 및 경량/저소음과의 균형 평가

**효율 평가 기준**:
```
1. get_allresults_summary()에서 효율(Efficiency) 확인
2. 기준 효율 대비 변화율 계산:
   - 효율 저하 < 2%: 허용 가능 ✅ (최적 기어 달성)
   - 효율 저하 2~5%: 주의 (사용자에게 trade-off 설명)
   - 효율 저하 > 5%: 재조정 권장 (헬릭스각/치폭 재검토)
```

**Trade-off 판단 기준**:

| 효율 저하 | 경량 달성 | 저소음 달성 | 권장 조치 |
|---------|---------|-----------|---------|
| < 2% | ✅ | ✅ | 최적 기어 달성 ✅ (설계 완료) |
| 2~5% | ✅ | ✅ | 사용자 확인 필요 (trade-off 설명) |
| > 5% | ✅ | ✅ | 재조정 권장 (overlap ratio 1.0으로 변경 고려) |
| > 5% | ✅ | ❌ | 저소음 목표 완화 고려 |

**LLM 응답 예시 (효율 저하 > 5% 시)**:
```
효율 평가:
- 1단계 후 효율: 99.2%
- 2단계 후 효율: 93.5% (5.7% 저하 ⚠️)
- 원인: Overlap ratio 2.0 달성 위해 헬릭스각 25° + 치폭 50mm 적용

Trade-off 분석:
- 경량: S_H=1.25, S_F=1.60 (적정 ✅)
- 저소음: Overlap ratio = 2.02 (적정 ✅)
- 효율: 93.5% (5.7% 저하 ⚠️, 재조정 권장)

재조정 제안:
1. Overlap ratio 목표를 2.0 → 1.0으로 변경
2. 헬릭스각/치폭 재계산 → 효율 개선 예상
3. 사용자 확인: 초저소음(overlap 2.0) vs 고효율(overlap 1.0) 중 선택
```

---

#### 최적 기어 설계 전체 LLM 응답 예시

```
요청: "경량+저소음 기어, 기어비 3, overlap ratio 1.0으로 설계"

=== 1단계: 경량 설계 (안전율 최적화) ===

SimpleSizing 결과 (Rank 1, PPTE 최소):
- 모듈 3.75, z1=23, z2=94 적용

안전률 평가 (요구: S_H=1.2, S_F=1.2):
- 실제: S_H=2.1, S_F=5.3, S_MP=0.85
- 평가: Contact/Bending 과도 (개선 필요), Micropitting 미달이지만 무시

조정 1회: 모듈 감소 (3.75 → 2.5mm)
→ 결과: S_H=0.9, S_F=3.0 (S_H 부족)

조정 2회: 모듈 2.0mm + 잇수 증가 (z1=29, z2=117)
→ 결과: S_H=1.2, S_F=1.7 (적정 ✅)
→ 효율: 99.2%, 질량: 1.2kg

1단계 완료 ✅ → 2단계 진행

=== 2단계: 저소음 설계 (Overlap Ratio 최적화) ===

Overlap ratio 평가 (목표: 1.0):
- 실제: 0.75 (부적정)
- 현재: 최소치폭 30mm, 헬릭스각 15°, 법선모듈 2.0mm

계산 기반 조정:
→ calculate_helixangle_for_ep_beta(1.0, 30.0, 2.0, session_id)
→ 필요 헬릭스각 = 19.5° (25도 미만 ✅)
→ modify_gear_data("헬릭스각 19.5도로 변경")
→ 재계산 결과: Overlap ratio = 1.00 ✅

안전율 재검증:
- S_H=1.18, S_F=1.65 (여전히 적정 ✅)
- 효율: 98.9% (0.3% 감소)

2단계 완료 ✅ → 3단계 진행

=== 3단계: 고효율 검증 및 Trade-off 판단 ===

효율 평가:
- 1단계 후 효율: 99.2%
- 2단계 후 효율: 98.9%
- 효율 저하: 0.3% (< 2%, 허용 가능 ✅)

최종 결과:
┌─────────────────────────────────────────┐
│ 최적 기어 설계 완료 ✅                     │
├─────────────────────────────────────────┤
│ 경량: S_H=1.18, S_F=1.65 (적정)          │
│ 저소음: Overlap ratio = 1.00 (달성)       │
│ 고효율: 98.9% (0.3% 감소, 허용)           │
│ 질량: 1.2kg                              │
│ 모듈: 2.0mm, z1=29, z2=117               │
│ 치폭: 30mm, 헬릭스각: 19.5°               │
└─────────────────────────────────────────┘

→ 출력물 생성: get_2D_image, get_gear_report 실행 가능
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

## 기어설계 주요 시나리오

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
  → 최적 기어 설계 가이드 적용 (3단계: 경량→저소음→효율)
  → calc_geometry → calc_load_case → get_allresults_summary
```

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
5. **최적 기어 설계 3단계 프로세스**:
   - **1단계 (경량)**: 안전률을 요구값의 1.0~1.3배로 최적화 (Contact/Bending만, Micropitting 무시)
   - **2단계 (저소음)**: Overlap ratio를 1.0 또는 2.0으로 조정 (계산 기반 방법 권장 ⭐)
   - **3단계 (효율)**: 효율 감소 확인 및 trade-off 판단 (< 2%: 무시, 2~5%: 조정 고려, > 5%: 재설계)
6. **안전률 평가**:
   - Contact(S_H), Bending(S_F)만 최적화 대상
   - **Micropitting(S_MP)은 참고만** (미달해도 허용)
   - 결과 평가 3단계: 미달(NG) / 적정(OK, 1.0~1.3×) / 과도(개선 필요, > 1.3×)
7. **저소음 설계 도구**:
   - **계산 기반 조정 권장**: calculate_helixangle_for_ep_beta() → 25° 기준 분기 → calculate_facewidth_for_ep_beta()
   - Overlap ratio는 get_allresults_summary()에서만 확인
8. **결과 표시 및 반복**: get_allresults_summary()와 get_simplesizing_results()는 항상 표로 표시, 미달/과도 시 최대 5회 반복
