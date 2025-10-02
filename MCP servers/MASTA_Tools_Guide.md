# MASTA Tools MCP 서버 사용 가이드

## 개요

MASTA Tools는 기존 LangGraph 통합 워크플로우를 개별 MCP 툴들로 분리한 새로운 구조입니다. 각 툴은 독립적으로 사용할 수 있으며, 사용자가 원하는 MASTA 컴포넌트만 선택적으로 생성할 수 있습니다.

## 핵심 MCP 툴 목록

### 1. `masta_initialize()` - MASTA 환경 초기화
```python
masta_initialize(masta_path: str = r"C:\Program Files\SMT\MASTA 13.0.3")
```

**기능**: MASTA Python API를 초기화하고 새로운 세션을 생성합니다.

**매개변수**:
- `masta_path` (str): MASTA 설치 경로 (기본값: 표준 설치 경로)

**반환값**:
- `success` (bool): 성공 여부
- `session_id` (str): 생성된 세션 ID (다른 모든 툴에서 사용)
- `design_name` (str): Design 객체 이름
- `assembly_name` (str): Assembly 객체 이름
- `execution_result` (str): Python 코드 실행 결과

### 2. `create_shaft()` - 축 생성 및 배치
```python
create_shaft(
    session_id: str,
    shaft_name: str,
    length: float,
    outer_diameter: float,
    bore_diameter: float = 0.0,
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0
)
```

**기능**: 축을 생성하고 3D 공간에 배치합니다.

**매개변수**:
- `session_id` (str): 초기화된 세션 ID
- `shaft_name` (str): 축의 고유 이름
- `length` (float): 축 길이 (mm)
- `outer_diameter` (float): 축 외경 (mm)
- `bore_diameter` (float): 축 내경 (mm, 기본값: 0.0)
- `position_x`, `position_y`, `position_z` (float): 축 위치 (mm)

### 3. `create_gear_pair()` - 기어 쌍 생성
```python
create_gear_pair(
    session_id: str,
    gear_pair_name: str,
    center_distance: float,
    pinion_teeth: int,
    wheel_teeth: int,
    normal_module: float,
    helix_angle: float = 0.0,
    pressure_angle: float = 20.0,
    pinion_face_width: float = 20.0,
    wheel_face_width: float = 20.0,
    addendum_factor: float = 1.0,
    dedendum_factor: float = 1.25,
    root_radius_factor: float = 0.3
)
```

**기능**: 평기어 쌍을 생성하고 기본 제원을 설정합니다.

**주요 매개변수**:
- `center_distance` (float): 기어 중심거리 (mm)
- `pinion_teeth` (int): 피니언 잇수
- `wheel_teeth` (int): 휠 잇수
- `normal_module` (float): 모듈 (mm)
- `helix_angle` (float): 헬리컬 각도 (도)
- `pressure_angle` (float): 압력각 (도)

### 4. `mount_gear_on_shaft()` - 기어 축 장착
```python
mount_gear_on_shaft(
    session_id: str,
    gear_pair_name: str,
    pinion_shaft_name: str,
    wheel_shaft_name: str,
    pinion_position: float,
    wheel_position: float
)
```

**기능**: 생성된 기어 쌍을 지정된 축에 장착합니다.

### 5. `create_bearing()` - 베어링 생성 및 장착
```python
create_bearing(
    session_id: str,
    bearing_name: str,
    shaft_name: str,
    position: float,
    bearing_designation: str = "6206"
)
```

**기능**: 베어링을 생성하고 축에 장착합니다.

**매개변수**:
- `bearing_designation` (str): SKF 베어링 designation

### 6. `show_model()` - 모델 시각화
```python
show_model(session_id: str)
```

**기능**: 생성된 MASTA 모델을 3D로 시각화합니다.

### 7. `get_session_status()` - 세션 상태 조회
```python
get_session_status(session_id: str)
```

**기능**: 현재 세션의 상태와 생성된 컴포넌트 정보를 조회합니다.

### 8. `execute_custom_code()` - 사용자 정의 코드 실행
```python
execute_custom_code(session_id: str, code: str)
```

**기능**: 사용자가 작성한 MASTA Python 코드를 실행합니다.

## 사용 예제

### 기본 기어박스 생성 예제

```python
# 1. MASTA 초기화
init_result = masta_initialize()
session_id = init_result["session_id"]

# 2. 축 3개 생성
create_shaft(session_id, "input_shaft", 120, 25, 0, 0, 0, 0)
create_shaft(session_id, "intermediate_shaft", 120, 30, 0, 60, 0, 0)
create_shaft(session_id, "output_shaft", 120, 35, 0, 120, 0, 0)

# 3. 기어 쌍 생성
create_gear_pair(
    session_id, "gear_pair_1", 60, 20, 40, 2.5,
    helix_angle=15, pinion_face_width=25, wheel_face_width=25
)

# 4. 기어를 축에 장착
mount_gear_on_shaft(
    session_id, "gear_pair_1",
    "input_shaft", "intermediate_shaft",
    60, 60
)

# 5. 베어링 장착
create_bearing(session_id, "bearing_1", "input_shaft", 15, "6205")
create_bearing(session_id, "bearing_2", "input_shaft", 105, "6205")
create_bearing(session_id, "bearing_3", "intermediate_shaft", 15, "6206")
create_bearing(session_id, "bearing_4", "intermediate_shaft", 105, "6206")

# 6. 모델 시각화
show_model(session_id)

# 7. 상태 확인
status = get_session_status(session_id)
print(f"생성된 컴포넌트: 축 {status['component_count']['shafts']}개, 기어 {status['component_count']['gears']}개, 베어링 {status['component_count']['bearings']}개")
```

### 단계별 사용법

#### 1단계: 초기화
```python
result = masta_initialize()
session_id = result["session_id"]  # 모든 후속 작업에 필요
```

#### 2단계: 축 생성
```python
# 입력축 (길이: 100mm, 외경: 20mm, 원점에 위치)
create_shaft(session_id, "input_shaft", 100, 20)

# 출력축 (길이: 100mm, 외경: 25mm, X방향으로 80mm 이동)
create_shaft(session_id, "output_shaft", 100, 25, 0, 80, 0, 0)
```

#### 3단계: 기어 생성 및 장착
```python
# 기어 쌍 생성 (중심거리: 40mm, 기어비: 3:1)
create_gear_pair(
    session_id, "main_gears", 40,
    pinion_teeth=20, wheel_teeth=60, normal_module=2.0
)

# 기어를 축에 장착
mount_gear_on_shaft(
    session_id, "main_gears",
    "input_shaft", "output_shaft",
    50, 50  # 양쪽 축의 중앙에 장착
)
```

#### 4단계: 베어링 장착
```python
# 각 축 양 끝에 베어링 장착
create_bearing(session_id, "bearing_in_1", "input_shaft", 10, "6204")
create_bearing(session_id, "bearing_in_2", "input_shaft", 90, "6204")
create_bearing(session_id, "bearing_out_1", "output_shaft", 10, "6205")
create_bearing(session_id, "bearing_out_2", "output_shaft", 90, "6205")
```

#### 5단계: 시각화
```python
show_model(session_id)
```

## 고급 사용법

### 사용자 정의 코드 실행
복잡한 작업이나 특수한 설정이 필요한 경우:

```python
custom_code = '''
# 특수한 기어 재료 설정
my_material = assembly.add_material("Custom_Steel")
my_material.youngs_modulus = 2.1e11
my_material.poisson_ratio = 0.3
my_material.density = 7850

# 기어에 재료 적용
gear_pair_1.active_gear_set_design.cylindrical_gears[0].material = my_material

print("사용자 정의 재료 적용 완료")
'''

execute_custom_code(session_id, custom_code)
```

### 세션 상태 모니터링
```python
# 현재 세션 상태 확인
status = get_session_status(session_id)

print(f"세션 ID: {status['session_id']}")
print(f"초기화 상태: {status['is_initialized']}")
print(f"생성된 축: {len(status['components']['shafts'])}개")
print(f"생성된 기어: {len(status['components']['gears'])}개")
print(f"생성된 베어링: {len(status['components']['bearings'])}개")

# 각 컴포넌트 세부 정보 확인
for shaft in status['components']['shafts']:
    print(f"축 '{shaft['name']}': 길이 {shaft['length']}mm, 외경 {shaft['outer_diameter']}mm")
```

## 장점

### 1. 유연성
- 필요한 컴포넌트만 선택적으로 생성
- 각 단계를 개별적으로 제어 가능
- 사용자 정의 코드로 특수 기능 구현

### 2. 단순성
- 복잡한 LangGraph 워크플로우 제거
- 명확한 함수 인터페이스
- 각 툴의 독립적 사용 가능

### 3. 디버깅 용이성
- 각 단계별로 결과 확인 가능
- 문제 발생 지점 쉽게 파악
- 개별 컴포넌트 수정 가능

## 기존 통합 버전과의 비교

| 구분 | 통합 버전 (LangGraph) | 개별 툴 버전 |
|------|---------------------|------------|
| 사용 방식 | 전체 워크플로우 자동 실행 | 단계별 수동 제어 |
| 유연성 | 제한적 | 높음 |
| 학습 곡선 | 낮음 | 중간 |
| 디버깅 | 어려움 | 쉬움 |
| 사용자 제어 | 제한적 | 완전 제어 |

## 문제 해결

### 일반적인 오류

1. **세션 없음 오류**
   ```
   "세션 'xxx'를 찾을 수 없습니다. masta_initialize()를 먼저 호출하세요."
   ```
   해결: `masta_initialize()` 먼저 실행

2. **MASTA 모듈 임포트 실패**
   ```
   "MASTA 모듈 임포트 실패"
   ```
   해결: MASTA 소프트웨어 설치 및 경로 확인

3. **베어링 designation 설정 실패**
   ```
   "베어링 designation 설정 실패"
   ```
   해결: 유효한 SKF 베어링 번호 사용 또는 기본 개념 베어링으로 사용

### 권장 작업 순서

1. `masta_initialize()` - 필수 첫 단계
2. `create_shaft()` - 필요한 모든 축 생성
3. `create_gear_pair()` - 기어 쌍 생성
4. `mount_gear_on_shaft()` - 기어를 축에 장착
5. `create_bearing()` - 베어링 생성 및 장착
6. `show_model()` - 최종 모델 확인

이 순서를 따르면 오류 없이 기어박스 모델을 생성할 수 있습니다.