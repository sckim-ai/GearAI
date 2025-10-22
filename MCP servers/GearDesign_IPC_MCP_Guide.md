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
→ 사용자 선택 → apply_simplesizing_case(row_index)
→ calc_geometry() → calc_load_case() → get_allresults_summary()
```

**⚠️ SimpleSizing 결과가 없는 경우 (제약조건 미충족)**

SimpleSizing 결과가 0개 또는 매우 적게 나오는 경우, 다음 방법으로 조건을 완화:

1. **모듈 범위 확대**: 최소값 감소 또는 최대값 증가 (예: 2~4 → 1.5~5)
2. **잇수 범위 확대**: 최소값 감소 또는 최대값 증가 (예: z_min=15 → 12)
3. **치폭 조정**: 치폭 증가 또는 범위로 변경 (예: 30mm → 30~50mm)
4. **최대 계산 횟수 증가**: 더 많은 조합 탐색 (예: max_iterations 증가)
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
  - 반환 구조: 각 결과에 `index` (원본 row_index) 포함
- **`apply_simplesizing_case(row_index, session_id)`**: 선택한 케이스 적용
  - **row_index는 원본 DataFrame의 인덱스** (get_simplesizing_results 결과의 `index` 필드 값)
  - **UI 더블클릭과 동일한 로직 사용** (SimpleSizingCase 클래스 공통화)
  - 자동으로 updated_config를 반환하여 session.changed_data 동기화
  - 적용 후 calc_geometry → calc_load_case 필수

#### apply_simplesizing_case 내부 동작

```
Python MCP Server
    ↓ (IPC 전송: case_data = DataFrame row → dict)
C# Program.cs apply_simplesizing_case handler
    ↓ SimpleSizingCase.FromDictionary(case_data)
    ↓ SimpleSizingForm.ApplySizingCaseToMainForm(mainForm, sizingCase) ← UI와 공통
GearDesignForm 컨트롤 업데이트 (TB_m_n, TB_z1, TB_z2, TB_a1, TB_beta, TB_alpha_n, TB_b1, TB_b2, Drop_CDMethod 등)
    ↓ form.SaveDataInput_Json(false)
    ↓ (IPC 반환: updated_config)
Python session.changed_data = updated_config (자동 동기화)
```

**적용되는 값**:
- 모듈 (m_n)
- 잇수 (z1, z2)
- 중심거리 (a)
- 헬릭스각 (β)
- 압력각 (α_n)
- 페이스폭 (Facewidth)
- 전위계수 초기화 (x1=0, x2=0)
- 중심거리 방법 자동 설정 (CDMethod=0)

#### SimpleSizing 파라미터 탐색 범위 ⚠️

**SimpleSizing이 탐색하는 파라미터** (최소/최대 범위 내 조합 생성):
- **모듈 (m_n)**: 최소값 ~ 최대값 범위
- **잇수 (z1, z2)**: 최소값 ~ 최대값 범위

**SimpleSizing에서 고정되는 파라미터** (입력값 그대로 사용):
- **치폭 (Facewidth)**: 단일 고정값
- **압력각 (α_n)**: 단일 고정값
- **헬리컬각 (β)**: 단일 고정값

**중요**: SimpleSizing은 치폭/압력각/헬리컬각을 변경하면서 탐색하지 않습니다!

#### 치폭/압력각/헬리컬각 Case Study 방법

다양한 치폭/압력각/헬리컬각 조합을 비교하려면 **SimpleSizing을 여러 번 수행**해야 합니다:

**프로세스**:
```
[Case 1: 치폭 30mm, 헬리컬각 15°]
→ modify_gear_data("치폭 30mm, 헬리컬각 15도")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ 최적 케이스 선택 및 성능 기록

[Case 2: 치폭 40mm, 헬리컬각 20°]
→ modify_gear_data("치폭 40mm, 헬리컬각 20도")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ 최적 케이스 선택 및 성능 기록

[Case 3: 치폭 50mm, 헬리컬각 25°]
→ modify_gear_data("치폭 50mm, 헬리컬각 25도")
→ simple_sizing_gearpair() → get_simplesizing_results()
→ 최적 케이스 선택 및 성능 기록

→ 모든 Case 비교 후 최종 선택
```

**LLM 응답 예시**:
```
치폭과 헬리컬각에 따른 영향을 비교하기 위해 3가지 케이스로 SimpleSizing을 수행하겠습니다:

[Case 1 결과 - 치폭 30mm, 헬리컬각 15°]
- 최적: 모듈 3.75, z1=23, z2=94
- PPTE: 0.95, total mass: 1.2kg, overlap ratio: 1.15

[Case 2 결과 - 치폭 40mm, 헬리컬각 20°]
- 최적: 모듈 3.5, z1=24, z2=101
- PPTE: 0.82, total mass: 1.45kg, overlap ratio: 1.82

[Case 3 결과 - 치폭 50mm, 헬리컬각 25°]
- 최적: 모듈 3.25, z1=26, z2=108
- PPTE: 0.78, total mass: 1.68kg, overlap ratio: 2.05

**분석**: Case 3이 저소음(PPTE 최소, overlap ratio ≈ 2.0)에 최적이나 질량이 가장 큽니다.
Case 2는 저소음과 경량의 균형점입니다. 어느 케이스를 적용할까요?
```

**저소음 설계 시 적용**:
- **1단계**: 기본 치폭/헬리컬각으로 SimpleSizing → 최적 모듈/잇수 조합 선택
- **2단계**: apply_simplesizing_case()로 적용 후 calc_geometry/calc_load_case 실행
- **3단계**: get_allresults_summary()에서 overlap ratio 확인
- **4단계**: **overlap ratio 조정이 필요하면** modify_gear_data()로 치폭/헬리컬각 수정 후 재계산
  - 이 과정은 SimpleSizing 재수행이 **아님**
  - 이미 선택된 모듈/잇수 조합에서 치폭/헬리컬각만 미세 조정

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
| **저소음** | rank ↑ | PPTE ↑ | **Overlap ratio ≈ 1 또는 2** (초저소음: 2 권장) |
| **경량** | rank ↑ | total mass ↑ | 안전률 확인 필수 |
| **고효율** | rank ↑ | efficiency ↓ | - |
| **컴팩트** | rank ↑ | CenterDistance ↑ | - |
| **고강도** | rank ↑ | min(SF_bending, SF_contact) ↓ | - |
| **복합 기준** | rank=1 필터링 | 트레이드오프 설명 | Rank 1 내에서 각 지표 비교 |

(↑: 오름차순, ↓: 내림차순)

#### 저소음 설계 상세 가이드 ⭐

**물림율(Overlap Ratio) 최적화**가 저소음 설계의 핵심:
- **목표**: Overlap ratio를 정수로, 즉 **1.0 또는 2.0에 가깝게** 설정
- **초저소음**: Overlap ratio = **2.0**이 1.0보다 유리 (더 부드러운 동력 전달)
- **⚠️ 중요**: Overlap ratio는 **SimpleSizing 결과에 포함되지 않음** → `get_allresults_summary()`에서만 확인 가능

**⚠️ SimpleSizing과 Overlap Ratio의 관계**:
- SimpleSizing은 치폭/헬리컬각을 **고정값**으로 사용
- Overlap ratio는 SimpleSizing 결과에 포함되지 않음 → `get_allresults_summary()`에서만 확인 가능
- **옵션 1**: SimpleSizing 후 치폭/헬리컬각 미세 조정 (모듈/잇수 고정)
- **옵션 2**: 다양한 치폭/헬리컬각으로 SimpleSizing 여러 번 수행 후 비교

**조정 방법** (apply_simplesizing_case 이후):
1. **치폭(Facewidth) 조정**: 증가/감소 → overlap ratio 변화
2. **헬리컬각(β) 조정**: 증가/감소 → overlap ratio 변화
3. modify_gear_data()로 수정 후 calc_geometry → calc_load_case → get_allresults_summary() 재확인

**⚠️ 설계 제약 및 트레이드오프**:
- **헬리컬각 제한**: 특별한 요청이 없으면 **25° 미만 권장** (과도한 축방향 하중 방지)
- **Overlap ratio = 2.0의 단점**:
  - 과도한 치폭이 적용될 수 있음 → **경량화에 불리** (질량 증가)
  - 과도한 헬리컬각이 적용될 수 있음 → **효율 저하** (축방향 하중 증가로 인한 마찰 증가)
- **권장 접근**:
  - **일반 저소음**: Overlap ratio = **1.0** 목표 (균형잡힌 설계)
  - **초저소음 우선**: Overlap ratio = **2.0** 목표 (경량/효율 희생 가능)
  - **경량+저소음**: Overlap ratio = **1.0** 목표 + PPTE 최소화
  - 헬리컬각 25° 초과 필요 시 → 사용자에게 확인 요청

**저소음 설계 프로세스** (두 가지 접근):

**프로세스 A: 기본 접근** (SimpleSizing 1번 + 이후 미세 조정):
```
[1단계: SimpleSizing으로 모듈/잇수 결정]
1. 기본 치폭/헬리컬각으로 SimpleSizing 실행
2. Rank 1 중 PPTE 최소 케이스 선택
3. apply_simplesizing_case(row_index)로 적용
4. calc_geometry() → calc_load_case() 실행
5. get_allresults_summary()에서 overlap ratio 확인 ⭐

[2단계: Overlap Ratio 미세 조정]
6. overlap ratio가 1.0 또는 2.0과 차이가 큰 경우:
   - modify_gear_data()로 치폭/헬리컬각 조정 (모듈/잇수 고정)
   - calc_geometry() → calc_load_case() 재실행
   - get_allresults_summary()로 overlap ratio 재확인
7. overlap ratio ≈ 1.0 or 2.0 달성까지 6번 반복
```

**프로세스 B: 치폭/헬리컬각 Case Study** (SimpleSizing 여러 번):
```
[1단계: 다양한 치폭/헬리컬각으로 SimpleSizing 수행]
→ 치폭 30mm, 헬리컬각 15° 설정 → SimpleSizing 실행 → 결과 기록 (Case 1)
→ 치폭 40mm, 헬리컬각 20° 설정 → SimpleSizing 실행 → 결과 기록 (Case 2)
→ 치폭 50mm, 헬리컬각 25° 설정 → SimpleSizing 실행 → 결과 기록 (Case 3)

[2단계: 모든 케이스 비교 및 최종 선택]
→ 각 Case의 최적 솔루션 비교 (PPTE, overlap ratio, 질량, 효율 등)
→ 사용자 요구사항에 가장 적합한 Case 선택
→ apply_simplesizing_case() 적용

**장점**: 다양한 조합을 체계적으로 비교 가능
**단점**: SimpleSizing을 여러 번 수행해야 하므로 시간 소요
```

**권장 사용**:
- **일반적인 경우**: 프로세스 A (빠르고 효율적)
- **최적 설계 필요**: 프로세스 B (체계적 비교 가능)

**LLM 응답 예시 (프로세스 A-1: 초저소음 우선)**:
```
SimpleSizing에서 Rank 1, PPTE 최소 케이스를 적용했습니다.
계산 결과 overlap ratio = 1.35입니다.

초저소음 설계를 위해 overlap ratio를 2.0에 가깝게 조정하겠습니다:
- 치폭 30mm → 50mm로 증가
- 헬리컬각 15° → 22°로 증가 (25° 미만 유지)

재계산 후 overlap ratio = 1.95로 최적화되었습니다! ✅
⚠️ 단, 치폭/헬리컬각 증가로 총 질량 1.2kg → 1.5kg, 효율 99.1% → 98.8%로 감소했습니다.
```

**LLM 응답 예시 (프로세스 A-2: 경량+저소음 균형)**:
```
SimpleSizing에서 Rank 1, PPTE 최소 케이스를 적용했습니다.
계산 결과 overlap ratio = 1.35입니다.

경량화도 고려하여 overlap ratio를 1.0에 가깝게 조정하겠습니다:
- 치폭 30mm → 25mm로 감소
- 헬리컬각 15° → 18°로 증가

재계산 후 overlap ratio = 1.02로 최적화되었습니다! ✅
총 질량 1.2kg → 1.05kg (경량화), 효율 99.1% 유지, PPTE도 우수합니다.
```

**LLM 응답 예시 (프로세스 A-3: 헬리컬각 제한 확인)**:
```
overlap ratio 2.0 달성을 위해 헬리컬각 28°가 필요합니다.
⚠️ 권장 한계(25°)를 초과하므로 다음 옵션을 제안합니다:
1. 헬리컬각 25°, 치폭 증가로 overlap ratio 1.8 달성 (권장)
2. 사용자 승인 시 헬리컬각 28° 적용
어느 방향으로 진행할까요?
```

**LLM 응답 예시 (프로세스 B: 치폭/헬리컬각 Case Study)**:
```
초저소음 설계를 위해 다양한 치폭/헬리컬각 조합으로 SimpleSizing을 수행하겠습니다.

[Case 1: 치폭 30mm, 헬리컬각 15°]
SimpleSizing 결과:
- 최적 케이스(Rank 1, PPTE 최소): 모듈 3.75, z1=23, z2=94
- PPTE: 0.95, overlap ratio: 1.15, total mass: 1.2kg, efficiency: 99.1%

[Case 2: 치폭 40mm, 헬리컬각 20°]
SimpleSizing 결과:
- 최적 케이스(Rank 1, PPTE 최소): 모듈 3.5, z1=24, z2=101
- PPTE: 0.82, overlap ratio: 1.85, total mass: 1.45kg, efficiency: 98.9%

[Case 3: 치폭 50mm, 헬리컬각 25°]
SimpleSizing 결과:
- 최적 케이스(Rank 1, PPTE 최소): 모듈 3.25, z1=26, z2=108
- PPTE: 0.78, overlap ratio: 2.02, total mass: 1.68kg, efficiency: 98.6%

**종합 분석**:
| Case | PPTE | Overlap Ratio | 질량 | 효율 | 평가 |
|------|------|---------------|------|------|------|
| 1 | 0.95 | 1.15 | 1.2kg | 99.1% | 경량/효율 우수, 저소음 보통 |
| 2 | 0.82 | 1.85 | 1.45kg | 98.9% | ⭐ 균형잡힌 설계 |
| 3 | 0.78 | 2.02 | 1.68kg | 98.6% | 초저소음, 질량/효율 불리 |

**추천**: Case 2 (치폭 40mm, 헬리컬각 20°)
- overlap ratio ≈ 2.0에 가까워 초저소음 설계
- 질량과 효율의 희생이 Case 3보다 적음
- PPTE도 충분히 낮음

적용하시겠습니까?
```

### SimpleSizing 결과 활용 시 주의사항 ⚠️

#### row_index vs display_order 명확화

**핵심**: SimpleSizing 결과를 rank/지표로 정렬하면 **표시 순서와 원본 인덱스가 달라집니다**!

**get_simplesizing_results() 반환 구조**:
```json
{
  "results": [
    {"index": 45, "module": 3.75, "z1": 23, "z2": 94, "rank": 1, "PPTE": 0.82, ...},
    {"index": 5, "module": 4.0, "z1": 21, "z2": 86, "rank": 1, "PPTE": 0.95, ...},
    {"index": 102, "module": 3.5, "z1": 24, "z2": 101, "rank": 1, "PPTE": 1.12, ...}
  ]
}
```

**LLM 추천 프로세스** (3단계):
1. **SimpleSizing 결과표 작성** (rank → 성능 지표 순 정렬, display_order는 1부터 시작)
2. **추천 케이스 지정** 시 **반드시 index 필드 값을 명시**:
```
추천: display_order 1번 케이스
  - **row_index: 45** ← apply_simplesizing_case()에 사용할 값
  - 모듈: 3.75mm, z1=23, z2=94
  - rank: 1, PPTE: 0.82 (최소), S_H=1.74, S_F=5.73
```
3. **apply_simplesizing_case(row_index=45, session_id)** 실행

#### LLM 응답 템플릿 (SimpleSizing)

**필수 형식**:
```
SimpleSizing 결과 (rank + [성능 지표] 기준 정렬):

| Display | row_index | 모듈 | z1 | z2 | Rank | [성능 지표] | [보조 지표1] | [보조 지표2] | 평가 |
|---------|-----------|------|----|----|------|-------------|--------------|--------------|------|
| 1 | 45 | 3.75 | 23 | 94 | 1 | 0.82 | 1.74 | 5.73 | ⭐ 추천 |
| 2 | 5 | 4.0 | 21 | 86 | 1 | 0.95 | 1.61 | 5.48 | - |
| 3 | 102 | 3.5 | 24 | 101 | 1 | 1.12 | 1.68 | 5.92 | - |

**분석**: Rank 1 중 display_order 1번(row_index 45)이 PPTE 최소로 저소음에 최적
**추천**: display_order 1번 케이스
  - row_index: 45
  - 모듈: 3.75mm, z1=23, z2=94
  - rank: 1, PPTE: 0.82, S_H=1.74, S_F=5.73

→ apply_simplesizing_case(row_index=45, session_id) 실행 예정
```

**주의사항**:
- **Display**: 표에서의 순서 (1, 2, 3, ...) → 사용자와 소통용
- **row_index**: 원본 DataFrame 인덱스 (`index` 필드) → **apply_simplesizing_case()에 필수**
- **절대 Display 번호를 apply_simplesizing_case()에 전달하지 말 것!**

### LLM 응답 템플릿 (일반)

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
  → 사용자에게 추천 (예: "display_order 1번 케이스(row_index=45) 추천")
  → 사용자 선택 확인
  → apply_simplesizing_case(row_index=45) ← results의 "index" 필드 값 사용
  → calc_geometry → calc_load_case → get_allresults_summary
```

**apply_simplesizing_case 예시**:
- SimpleSizing 결과 중 Display 1번(index=45) 선택 시: `apply_simplesizing_case(45, session_id)`
- 자동으로 UI와 동일한 로직으로 mainForm 업데이트 및 config 동기화
- **주의**: Display 번호가 아닌 `index` 필드 값(원본 row_index)을 사용!

### 3. 저소음 설계 (SimpleSizing + Overlap Ratio 최적화)
```
요청: "저소음 기어, 기어비 3, 초저소음으로 설계해줘"

[1단계: SimpleSizing]
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (rank ↑ → PPTE ↑ 정렬, 표 표시)
  → Rank 1 중 PPTE 최소 케이스 선택 (예: Display 1번, index=45)
  → apply_simplesizing_case(row_index=45)
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio 확인) ⭐

[2단계: Overlap Ratio 최적화]
→ overlap ratio = 1.35 확인 (목표: 2.0)
  → modify_gear_data("치폭 45mm, 헬리컬각 20도로 변경")
  → calc_geometry → calc_load_case
  → get_allresults_summary (overlap ratio = 1.98 확인) ✅
  → 최적화 완료
```

### 4. 복합 성능 기준 (SimpleSizing 워크플로우)
```
요청: "경량+저소음, 기어비 4"
→ initialize → modify_gear_data → simple_sizing_gearpair
  → get_simplesizing_results (Rank 1 필터링 → total mass + PPTE 비교)
  → 트레이드오프 설명 (예: "Display 1번(index=12)은 경량 우선, Display 2번(index=78)은 저소음 우선, Display 3번(index=34)은 균형")
  → 사용자 선택 확인
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

### SimpleSizing 결과 부족 시 대응
- 결과가 0개 또는 소수인 경우 → 제약조건이 너무 엄격함
- **조건 완화 우선순위**:
  1. 모듈 범위 확대 (가장 효과적)
  2. 최소 잇수 감소
  3. 치폭 증가 또는 범위 지정
  4. 최대 계산 횟수 증가
- 사용자에게 구체적인 조정 방법 제안 필요

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
- [ ] SimpleSizing: simple_sizing_gearpair → get_simplesizing_results → 추천 → 사용자 선택 확인 → apply_simplesizing_case(row_index)
- [ ] **apply_simplesizing_case()에는 results의 `index` 필드 값(row_index) 전달** (Display 번호 아님!)
- [ ] apply_simplesizing_case 후 반드시 calc_geometry → calc_load_case 실행

### 결과 표시 (필수!)
- [ ] get_allresults_summary() → **마크다운 표**
- [ ] get_simplesizing_results() → **rank 기반 분석 + 표 (Display 순서 + row_index 컬럼 포함)**
- [ ] SimpleSizing 표에 **Display**와 **row_index** 컬럼 반드시 포함
- [ ] calc_load_case() 메시지 전달

### SimpleSizing 파라미터 이해 (중요!)
- [ ] SimpleSizing은 **모듈/잇수만** 최소/최대 범위 내에서 탐색
- [ ] **치폭/압력각/헬리컬각은 고정값** 사용 (SimpleSizing에서 변경 안 됨)
- [ ] 치폭/헬리컬각 Case Study 필요 시 → SimpleSizing 여러 번 수행

### SimpleSizing 성능 분석 (핵심!)
- [ ] **모든 분석 1차 정렬: rank ↑**
- [ ] 저소음: 2차 PPTE ↑
- [ ] 경량: 2차 total mass ↑ (안전률 확인)
- [ ] 고효율: 2차 efficiency ↓
- [ ] 복합: Rank 1 필터링 → 트레이드오프 설명
- [ ] **Rank 2+ 추천 금지** (특별한 이유 없으면)

### 저소음 설계 Overlap Ratio 최적화 (필수!)
- [ ] **프로세스 선택**:
  - **프로세스 A**: SimpleSizing 1번 → 케이스 적용 → 치폭/헬리컬각 미세 조정 (일반적)
  - **프로세스 B**: 다양한 치폭/헬리컬각으로 SimpleSizing 여러 번 → 비교 후 선택 (최적 설계)
- [ ] SimpleSizing 케이스 적용 후 calc_geometry → calc_load_case 실행
- [ ] **get_allresults_summary()에서 overlap ratio 확인** (SimpleSizing에는 없음!)
- [ ] overlap ratio 목표값 결정:
  - **일반 저소음**: 1.0 목표 (균형)
  - **초저소음 우선**: 2.0 목표 (경량/효율 희생 가능)
  - **경량+저소음**: 1.0 목표 + PPTE 최소화
- [ ] **(프로세스 A)** 치폭/헬리컬각 조정 시 **헬리컬각 25° 미만 유지** (특별 요청 없으면)
- [ ] 헬리컬각 25° 초과 필요 시 사용자에게 확인 요청
- [ ] **(프로세스 A)** 조정 후 calc_geometry → calc_load_case → get_allresults_summary() 재확인
- [ ] **(프로세스 B)** 모든 Case의 overlap ratio, PPTE, 질량, 효율 비교 후 최적 선택
- [ ] 질량, 효율 변화 모니터링 (overlap ratio 2.0은 경량/효율 불리)
- [ ] **(프로세스 A)** overlap ratio ≈ 목표값 달성까지 반복

### SimpleSizing 결과 부족 시
- [ ] 결과 0개 또는 소수 → 사용자에게 조건 완화 제안
- [ ] 우선 순위: 모듈 범위 확대 > 잇수 감소 > 치폭 조정
- [ ] 구체적인 수치 예시 제공 (예: 2~4 → 1.5~5)

### 오류 처리
- [ ] success 필드 확인
- [ ] change_summary 검증
- [ ] 기어비 요청 시 기어 타입 고려

---

## 요약: 가장 중요한 6가지

1. **워크플로우 선택**: 성능 기준/범위/추상적 표현 → SimpleSizing, 구체적 제원 → 기본
2. **SimpleSizing 파라미터 이해 ⚠️**:
   - **탐색**: 모듈/잇수 (최소/최대 범위 내)
   - **고정**: 치폭/압력각/헬리컬각 (단일 고정값)
   - **치폭/헬리컬각 Case Study**: SimpleSizing 여러 번 수행 필요
3. **SimpleSizing 분석**: 반드시 rank 1차 정렬 → Rank 1 중에서 요청 지표 기준 선택
4. **저소음 설계 (두 가지 접근)**:
   - **프로세스 A**: SimpleSizing 1번 → 케이스 적용 → 치폭/헬리컬각 미세 조정 (일반적)
   - **프로세스 B**: 다양한 치폭/헬리컬각으로 SimpleSizing 여러 번 → 비교 후 선택 (최적)
   - **get_allresults_summary()에서 overlap ratio 확인** (SimpleSizing에 없음!)
   - 목표: 일반(1.0) vs 초저소음(2.0, 경량/효율 불리)
   - 제약: **헬리컬각 25° 미만** 유지 (특별 요청 없으면)
5. **SimpleSizing 결과 부족**: 모듈 범위 확대/잇수 감소/치폭 조정으로 조건 완화 제안
6. **결과 표시**: get_allresults_summary()와 get_simplesizing_results()는 **항상 표로 표시** (row_index 포함)
