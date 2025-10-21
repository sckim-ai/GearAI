# GearDesign IPC MCP 서버 사용 가이드

## 개요
이 MCP 서버는 기어 설계 시스템과 IPC(Inter-Process Communication)를 통해 통신하여 기어 치형 계산, 하중 분석, 이미지 생성, 보고서 작성 등을 수행합니다.

**중요**: 모든 작업은 세션 기반으로 동작하며, 반드시 `initialize()`로 시작해야 합니다.

---

## 필수 워크플로우

### 기본 워크플로우 (Basic Design Flow)
```
1. initialize() → 세션 생성 및 초기화
2. modify_gear_data() 또는 load_GearDesign_data() → 기어 데이터 설정
3. calc_geometry() → 기하학적 계산 수행
4. get_geometry_results() → 기하학 결과 확인 (필요시)
5. calc_load_case() → 하중 계산 수행
6. get_allresults_summary() → 최종 결과 요약 (표 형식으로 사용자에게 표시)
7. get_2D_image() / get_3d_image() / get_gear_report() → 출력물 생성
```

### SimpleSizing 워크플로우 (Sizing Flow)
```
1. initialize() → 세션 생성 및 초기화
2. modify_gear_data() → 기본 기어 데이터 설정
3. simple_sizing_gearpair() → 사이징 수행
4. get_simplesizing_results() → 사이징 결과 조회 및 분석
5. (사용자가 선택한 케이스로) modify_gear_data() → 최종 제원 적용
6. calc_geometry() → calc_load_case() → 최종 검증
```

---

## 워크플로우 선택 가이드 (중요!)

### 사용자 요청 분석 및 워크플로우 결정

**LLM은 사용자 요청을 받으면 반드시 아래 기준에 따라 워크플로우를 선택해야 합니다.**

#### 1️⃣ 기본 워크플로우 선택 (Basic Design Flow)
다음 조건에 **모두** 해당하면 사이징 없이 바로 계산을 수행합니다:

**조건**:
- ✅ 모듈(Module)이 **구체적 수치**로 제공됨 (예: "모듈 3", "모듈 2.5")
- ✅ 잇수(z1, z2)가 **구체적 수치**로 제공됨 (예: "잇수 20-60", "피니언 25, 기어 75")
- ✅ 기타 주요 제원이 **구체적**으로 명시됨 (헬리컬각, 압력각, 전위계수 등)

**예시**:
```
✅ "모듈 3, 잇수 20-60인 헬리컬 기어를 설계해줘. 헬리컬각은 15도야."
   → 모듈(3), 잇수(20-60), 헬리컬각(15도) 모두 명확 → 기본 워크플로우

✅ "모듈 2.5, 피니언 25개, 기어 75개로 평기어를 계산해줘."
   → 모듈(2.5), 잇수(25-75) 명확 → 기본 워크플로우

✅ "이 파일의 모듈을 3.5로 바꾸고 재계산해줘."
   → 기존 파일 수정 요청 → 기본 워크플로우
```

**워크플로우**:
```
initialize → modify_gear_data → calc_geometry → calc_load_case → get_allresults_summary
```

---

#### 2️⃣ SimpleSizing 워크플로우 선택 (Sizing Flow)
다음 조건 중 **하나라도** 해당하면 사이징을 먼저 수행합니다:

**조건**:
- ❌ 모듈이 **범위로 제공**되거나 **미지정** (예: "모듈 2~4", "적절한 모듈")
- ❌ 잇수가 **미지정**이고 기어비만 제공 (예: "기어비 3", "감속비 5:1")
- ❌ 작동조건(토크, 속도, 동력)만 제공되고 구체적 제원 없음
- ❌ "적절한", "적당한", "좋은" 등의 **추상적 표현** 사용
- ❌ "찾아줘", "선정해줘", "설계해줘"와 같은 **탐색적 요청**

**예시**:
```
❌ "기어비 3 정도 되는 기어를 찾아줘. 모듈은 2~4 사이로."
   → 모듈이 범위(2~4), 잇수 미지정 → SimpleSizing 워크플로우

❌ "감속비 5:1로 토크 100Nm를 전달할 수 있는 기어를 설계해줘."
   → 작동조건만 제공, 구체적 제원 없음 → SimpleSizing 워크플로우

❌ "기어비 4에 적절한 헬리컬 기어를 선정해줘."
   → "적절한"이라는 추상적 표현, 잇수 미지정 → SimpleSizing 워크플로우

❌ "치폭 30, 헬리컬각 10도로 좋은 기어쌍을 찾아줘."
   → 모듈/잇수 미지정, "좋은"이라는 추상적 표현 → SimpleSizing 워크플로우
```

**워크플로우**:
```
initialize → modify_gear_data (기본설정) → simple_sizing_gearpair →
get_simplesizing_results (표로 표시) → 사용자 선택 → modify_gear_data (선택 케이스 적용) →
calc_geometry → calc_load_case → get_allresults_summary
```

---

#### 3️⃣ 판단이 애매한 경우

다음과 같이 **일부는 명확하고 일부는 불명확한 경우**:

**예시**:
```
"모듈 3으로 기어비 4가 되는 기어를 찾아줘."
→ 모듈은 명확(3)하지만 잇수는 미지정
→ 🔍 SimpleSizing 워크플로우 선택 (잇수 탐색 필요)
```

**기준**:
- 모듈 또는 잇수 중 **하나라도 미지정이면 SimpleSizing** 수행
- 사용자가 여러 대안을 비교하고 싶어하는 의도가 있으면 SimpleSizing

---

### 워크플로우 선택 의사결정 트리

```
사용자 요청 접수
    ↓
[모듈이 구체적 수치인가?]
    ├─ NO → SimpleSizing 워크플로우
    └─ YES
        ↓
    [잇수가 구체적 수치인가?]
        ├─ NO → SimpleSizing 워크플로우
        └─ YES
            ↓
        [추상적 표현("적절한", "좋은") 사용?]
            ├─ YES → SimpleSizing 워크플로우
            └─ NO → 기본 워크플로우
```

---

## 도구 사용 가이드

### 1. 세션 관리

#### `initialize()`
- **목적**: 새 세션 생성 및 IPC 프로세스 시작
- **반환**: `session_id` (이후 모든 함수 호출에 필수)
- **사용 시점**: 모든 작업의 첫 단계
- **주의**: 매번 새로운 세션을 생성하므로 session_id를 잘 보관해야 함

#### `delete_session(session_id)`
- **목적**: 세션 및 관련 파일 삭제
- **사용 시점**: 작업 완료 후 정리가 필요할 때

---

### 2. 데이터 입력/수정

#### `modify_gear_data(user_message, session_id)`
- **목적**: 자연어로 기어 데이터 수정
- **입력 예시**:
  - "모듈을 3으로, 기어1 잇수를 20으로 설정해줘"
  - "헬리컬각을 15도로 변경해줘"
  - "기어비를 3으로 설정해줘" (자동으로 잇수비 계산)
- **특징**:
  - LLM이 자연어를 JSON 데이터 변경으로 자동 변환
  - 매크로 기어 제원 변경 시 CDMethod=1 자동 설정
  - 기어비 변경 시 기어 타입에 따라 잇수비 자동 계산
- **주의**:
  - 경로 불일치 오류 발생 시 LLM의 JSON 키 이름 확인 필요
  - change_summary를 확인하여 실제 변경사항 검증

#### `load_GearDesign_data(file_path, session_id)`
- **목적**: 기존 JSON/GD1 파일에서 기어 데이터 로드
- **입력**: 파일 절대 경로
- **사용 시점**: 기존 설계 파일을 불러올 때

#### `save_GearDesignData(session_id)`
- **목적**: 현재 기어 데이터를 JSON 파일로 저장
- **사용 시점**: 설정한 데이터를 나중에 재사용하고 싶을 때

---

### 3. 계산 수행

#### `calc_geometry(session_id)`
- **목적**: 기어 치형 기하학적 계산 수행
- **특징**: 이전 메시지 삭제됨 (새로 시작)
- **주의**: calc_load_case() 전에 반드시 실행 필요

#### `calc_load_case(session_id)`
- **목적**: 기어 하중 계산 수행
- **전제조건**: calc_geometry() 완료
- **반환**: 계산 메시지 (경고, 정보 등)
- **주의**: 이 함수 실행 후 get_allresults_summary(), get_gear_report() 사용 가능

---

### 4. 결과 조회

#### `get_geometry_results(session_id)`
- **목적**: 기하학적 계산 결과 조회
- **사용 시점**: calc_geometry() 후, 기하학 데이터만 필요할 때

#### `get_allresults_summary(session_id)`
- **목적**: 모든 계산 결과를 표 형태로 요약
- **전제조건**: calc_geometry() + calc_load_case() 완료
- **반환 형식**:
  ```json
  {
    "summary": {
      "$테이블명": "테이블 설명",
      "테이블명": {
        "columns": ["컬럼1", "컬럼2", ...],
        "rowHeaders": ["행1", "행2", ...],
        "rows": [[값1, 값2, ...], ...]
      }
    }
  }
  ```
- **LLM의 의무**:
  - 반환된 표 데이터를 **반드시 마크다운 표 형식**으로 사용자에게 표시
  - $ 접두사 키는 메타데이터이므로 표 제목/설명으로 활용
  - rows 배열을 columns와 매칭하여 표로 변환

#### `get_messages(session_id)`
- **목적**: 계산 과정의 경고/오류 메시지 조회
- **사용 시점**: 계산 후 문제 발생 여부 확인

---

### 5. 출력물 생성

#### `get_2D_image(session_id)`
- **목적**: 기어 치물림 2D 이미지 PNG 생성
- **전제조건**: calc_geometry() 완료

#### `get_3d_image(session_id, width=800, height=600)`
- **목적**: 기어 3D 이미지 PNG 생성
- **전제조건**: calc_geometry() 완료

#### `get_3d_modeling(session_id)`
- **목적**: 기어 3D 모델링 STEP 파일 생성
- **전제조건**: calc_geometry() 완료

#### `get_gear_report(session_id)`
- **목적**: 기어 설계 보고서 PDF 생성
- **전제조건**: calc_geometry() + calc_load_case() 완료
- **주의**: 하중 계산 없이 호출 시 오류

---

### 6. SimpleSizing (기어쌍 사이징)

#### `simple_sizing_gearpair(user_message, session_id)`
- **목적**: 다양한 기어 제원 조합을 계산하여 적절한 설계안 도출
- **입력 예시**:
  - "기어비 3에 적절한 기어를 선정해줘. 모듈은 2~4 사이로"
  - "치폭 30, 헬리컬각 10도로 사이징해줘"
- **특징**:
  - 최적화는 아니지만 case study를 통해 다양한 조합 제시
  - 사용자 메시지는 이전 대화를 기반으로 주요 요구사항 요약
- **반환**: 계산된 케이스 수, 변경 내역

#### `get_simplesizing_results(session_id, return_all=False, top_n=100)`
- **목적**: SimpleSizing 계산 결과 조회
- **파라미터**:
  - `return_all=True`: 모든 결과 반환
  - `return_all=False, top_n=100`: 상위 100개만 반환 (기본값)
- **반환**: DataFrame 형태의 결과 (records 형식 dict)
- **LLM의 의무**:
  - 결과를 **표 형식**으로 사용자에게 표시
  - 사용자가 선택할 수 있도록 주요 컬럼 강조
  - 선택된 케이스를 modify_gear_data()로 적용하도록 안내

---

## 중요 주의사항

### 1. 필수 실행 순서
- ❌ **잘못된 예**: calc_load_case() 없이 get_gear_report() 호출
- ❌ **잘못된 예**: calc_geometry() 없이 calc_load_case() 호출
- ✅ **올바른 예**: initialize → modify_gear_data → calc_geometry → calc_load_case → get_allresults_summary

### 2. 기어비 설정 규칙
기어비는 기어 타입에 따라 다르게 계산됩니다:
- Gear pair: z2 / z1
- Three gear: z3 / z1
- Planetary: z3 / z1 (링기어 / 선기어)
- Double pinion planetary: z3 / z1

사용자가 "기어비 3"을 요청하면 modify_gear_data()가 자동으로 잇수비를 계산합니다.

### 3. 세션 관리
- 각 세션은 독립적인 작업 공간
- 세션 타임아웃: 1시간 (이후 자동 삭제)
- 세션별 출력 디렉토리: `outputs/{session_id}/`

### 4. 오류 처리
- 모든 함수는 `success` 필드로 성공/실패 표시
- `success=False`일 때 `error` 메시지 확인
- `change_summary`로 실제 변경사항 검증

### 5. LLM 표시 규칙
- **get_allresults_summary()**: 반드시 마크다운 표로 표시
- **get_simplesizing_results()**: 반드시 표로 표시하고 선택 가능하게 안내
- **calc_load_case()**: 반환된 메시지를 사용자에게 전달

---

## 사용 예시 시나리오

### 시나리오 1: 구체적 제원이 주어진 경우 (기본 워크플로우)
```
사용자: "모듈 3, 잇수 20-60인 헬리컬 기어를 설계해줘. 헬리컬각은 15도야."

LLM 판단:
- 모듈(3) ✅ 구체적
- 잇수(20-60) ✅ 구체적
- 헬리컬각(15도) ✅ 구체적
→ 기본 워크플로우 선택

LLM 실행:
1. initialize() → session_id 획득
2. modify_gear_data("모듈 3, 기어1 잇수 20, 기어2 잇수 60, 헬리컬각 15도", session_id)
3. calc_geometry(session_id)
4. calc_load_case(session_id)
5. get_allresults_summary(session_id) → 결과를 표로 표시
6. get_2D_image(session_id) → 이미지 경로 전달
7. get_gear_report(session_id) → 보고서 경로 전달
```

### 시나리오 2: 러프한 조건만 주어진 경우 (SimpleSizing 워크플로우)
```
사용자: "기어비 3 정도 되는 기어를 찾아줘. 모듈은 2~4 사이, 치폭은 30으로."

LLM 판단:
- 모듈(2~4) ❌ 범위 지정
- 잇수 ❌ 미지정 (기어비만 제공)
- "찾아줘" ❌ 탐색적 요청
→ SimpleSizing 워크플로우 선택

LLM 실행:
1. initialize() → session_id 획득
2. modify_gear_data("기본 설정: 치폭 30", session_id)
3. simple_sizing_gearpair("기어비 3, 모듈 2~4, 치폭 30", session_id)
4. get_simplesizing_results(session_id, False, 20) → 상위 20개 결과를 표로 표시
5. 사용자에게 선택 요청: "위 결과 중 적절한 케이스를 선택해주세요."
6. (사용자가 2번 케이스 선택)
7. modify_gear_data("2번 케이스: 모듈 2.5, 잇수 24-72 적용", session_id)
8. calc_geometry(session_id) → calc_load_case(session_id)
9. get_allresults_summary(session_id) → 최종 결과 표시
10. get_gear_report(session_id) → 보고서 생성
```

### 시나리오 3: 일부만 구체적인 경우 (SimpleSizing 워크플로우)
```
사용자: "모듈 3으로 감속비 4:1인 기어를 설계해줘."

LLM 판단:
- 모듈(3) ✅ 구체적
- 잇수 ❌ 미지정 (기어비만 제공)
→ SimpleSizing 워크플로우 선택 (잇수 탐색 필요)

LLM 실행:
1. initialize() → session_id 획득
2. modify_gear_data("모듈 3 설정", session_id)
3. simple_sizing_gearpair("기어비 4, 모듈 3 고정", session_id)
4. get_simplesizing_results(session_id, False, 10) → 상위 10개 결과 표시
5. 사용자 선택 → modify_gear_data 적용
6. calc_geometry → calc_load_case → 최종 검증
```

### 시나리오 4: 기존 파일 수정 (기본 워크플로우)
```
사용자: "이 파일(Ex3-Three gear.GD1)을 불러와서 기어1 잇수를 30으로 바꿔줘."

LLM 판단:
- 기존 파일 수정 요청
- 변경할 제원(잇수 30) ✅ 구체적
→ 기본 워크플로우 선택

LLM 실행:
1. initialize() → session_id 획득
2. load_GearDesign_data("D:\\path\\Ex3-Three gear.GD1", session_id)
3. modify_gear_data("기어1 잇수를 30으로 변경", session_id)
4. calc_geometry(session_id)
5. calc_load_case(session_id)
6. get_allresults_summary(session_id) → 표로 표시
7. save_GearDesignData(session_id) → 수정된 데이터 저장
```

---

## 디버깅 팁

1. **경로 불일치 오류**: LLM이 생성한 JSON 키가 기존 데이터 구조와 맞지 않음
   - change_summary의 "not_found" 항목 확인
   - 올바른 키 이름으로 재시도

2. **계산 실패**: get_messages()로 상세 오류 확인

3. **세션 오류**: get_active_sessions()로 세션 상태 확인

4. **파일 생성 확인**: get_session_files()로 생성된 파일 목록 조회

---

## 요약 체크리스트

### 워크플로우 선택
- [ ] 사용자 요청 분석: 모듈/잇수가 구체적 수치인가?
- [ ] 추상적 표현("적절한", "좋은") 또는 범위 지정 시 SimpleSizing 선택
- [ ] 구체적 제원이 모두 주어진 경우 기본 워크플로우 선택

### 실행 순서
- [ ] initialize()로 세션 생성 확인
- [ ] session_id를 모든 함수에 전달
- [ ] calc_geometry → calc_load_case 순서 준수
- [ ] SimpleSizing 사용 시: simple_sizing_gearpair → get_simplesizing_results → 사용자 선택 → modify_gear_data

### 결과 표시
- [ ] get_allresults_summary() 결과를 **반드시 마크다운 표로 표시**
- [ ] get_simplesizing_results() 결과를 **반드시 표로 표시**하고 선택 가능하게 안내
- [ ] calc_load_case() 메시지를 사용자에게 전달

### 오류 처리
- [ ] 오류 발생 시 success 필드와 error 메시지 확인
- [ ] change_summary로 실제 변경사항 검증
- [ ] 기어비 설정 시 기어 타입 고려
