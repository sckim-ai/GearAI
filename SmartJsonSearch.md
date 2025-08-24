# JSONPathSearcher 사용 가이드

## 개요
JSONPathSearcher는 JSON 데이터에서 키와 값을 효율적으로 검색하고, 해당 경로와 설명을 반환하는 Python 클래스입니다.

## 주요 특징
- 🔍 **다양한 검색 방식**: 정확한 매칭, 부분 매칭, 퍼지 매칭 지원
- 📝 **설명 키 자동 감지**: `$키이름` 형식의 설명을 자동으로 포함
- 🛤️ **경로 추적**: 중첩된 JSON 구조에서 정확한 경로 제공
- 🎯 **유사도 점수**: 검색 결과를 관련성 순으로 정렬

## 설치

### 필수 패키지 설치
```bash
pip install fuzzywuzzy python-Levenshtein
```

## 기본 사용법

### 1. 초기화

#### JSON 파일에서 로드
```python
from JSONPathSearcher import JSONPathSearcher

# JSON 파일 경로를 지정하여 초기화
searcher = JSONPathSearcher(json_file="data.json")

# Windows 경로 예시
searcher = JSONPathSearcher(json_file=r"C:\SW\GearAI\Default.GD1")
```

#### Python 딕셔너리에서 로드
```python
data = {
    "user": {
        "name": "홍길동",
        "$name": "사용자 이름",
        "email": "hong@example.com",
        "$email": "이메일 주소"
    }
}

searcher = JSONPathSearcher(json_data=data)
```

### 2. 키(Key) 검색

```python
# 'module'이 포함된 모든 키 검색
results = searcher.search("module")

# 유사도 임계값 조정 (기본값: 70)
results = searcher.search("modul", threshold=60)  # 오타 허용

# 결과 처리
for result in results:
    print(f"경로: {result['path']}")
    print(f"값: {result['value']}")
    if 'description' in result:
        print(f"설명: {result['description']}")
    print(f"점수: {result['score']:.1f}")
    print(f"매칭 타입: {result['match_type']}")
```

### 3. 값(Value) 검색

```python
# 값에서 'active' 검색
results = searcher.search_value("active")

for result in results:
    print(f"경로: {result['path']}")
    print(f"값: {result['value']}")
    if 'description' in result:
        print(f"설명: {result['description']}")
```

### 4. 통합 검색 (키와 값 모두)

```python
# 키와 값 모두에서 검색
all_results = searcher.search_all("module")

print(f"키에서 발견: {len(all_results['keys'])}개")
print(f"값에서 발견: {len(all_results['values'])}개")

# 키 검색 결과
for r in all_results['keys']:
    print(f"키 경로: {r['path']}")

# 값 검색 결과
for r in all_results['values']:
    print(f"값 경로: {r['path']}")
```

### 5. 경로로 값 가져오기

```python
# 특정 경로의 값 직접 가져오기
value = searcher.get_value_by_path("user.profile.name")
print(f"값: {value}")

# 배열 인덱스 포함 경로
value = searcher.get_value_by_path("system.modules[0].name")
print(f"값: {value}")

# 중첩된 경로
value = searcher.get_value_by_path("config.database.connections[2].host")
print(f"값: {value}")
```

## JSON 구조 예시

### 설명 키를 포함한 JSON 구조
```json
{
    "module_config": {
        "$module_config": "모듈 설정 정보",
        "name": "auth_module",
        "$name": "모듈 이름",
        "version": "1.0.0",
        "$version": "모듈 버전",
        "settings": {
            "$settings": "세부 설정",
            "enabled": true,
            "$enabled": "활성화 여부",
            "timeout": 3000,
            "$timeout": "타임아웃 (밀리초)"
        }
    }
}
```

## 반환 데이터 형식

### 검색 결과 구조
```python
{
    'path': 'system.modules[0].name',   # JSON 경로
    'value': 'auth_module',              # 해당 키의 값
    'description': '인증 모듈',          # 설명 (있는 경우)
    'score': 100.0,                      # 유사도 점수 (0-100)
    'match_type': 'exact'                # 매칭 타입
}
```

### 매칭 타입
- `exact`: 정확히 일치
- `partial`: 부분 문자열 일치
- `fuzzy`: 유사도 기반 매칭
- `exact_value`: 값이 정확히 일치
- `partial_value`: 값이 부분적으로 일치
- `fuzzy_value`: 값이 유사도 기반 매칭

## 고급 사용법

### 1. 유사도 임계값 조정
```python
# 낮은 임계값 = 더 많은 결과 (오타 허용)
results = searcher.search("modl", threshold=50)

# 높은 임계값 = 더 정확한 결과만
results = searcher.search("module", threshold=90)
```

### 2. 검색 결과 필터링
```python
# 특정 점수 이상만 필터링
results = searcher.search("module")
high_score_results = [r for r in results if r['score'] >= 80]

# 특정 매칭 타입만 필터링
exact_matches = [r for r in results if r['match_type'] == 'exact']

# 설명이 있는 결과만 필터링
with_description = [r for r in results if 'description' in r]
```

### 3. 경로 패턴 분석
```python
results = searcher.search("config")

# 최상위 레벨 키만 필터링
top_level = [r for r in results if '.' not in r['path']]

# 배열 내부 항목만 필터링
array_items = [r for r in results if '[' in r['path']]

# 특정 깊이의 항목만 필터링
depth_2 = [r for r in results if r['path'].count('.') == 1]
```

## 실전 예제

### 예제 1: 설정 파일에서 모든 모듈 찾기
```python
# 모든 module 관련 설정 찾기
module_results = searcher.search("module")

# 활성화된 모듈만 찾기
active_modules = []
for result in module_results:
    if isinstance(result['value'], dict):
        # 해당 경로에서 status 확인
        status_path = f"{result['path']}.status"
        status = searcher.get_value_by_path(status_path)
        if status == "active":
            active_modules.append(result)

print(f"활성 모듈 수: {len(active_modules)}")
```

### 예제 2: 설명 기반 검색
```python
# 모든 키와 설명 매핑 생성
def get_all_descriptions(searcher, keyword):
    results = searcher.search(keyword)
    descriptions_map = {}
    
    for result in results:
        if 'description' in result:
            descriptions_map[result['path']] = {
                'value': result['value'],
                'description': result['description']
            }
    
    return descriptions_map

# 사용
desc_map = get_all_descriptions(searcher, "config")
for path, info in desc_map.items():
    print(f"{path}: {info['description']}")
```

### 예제 3: 값 업데이트 위치 찾기
```python
# 특정 값을 가진 모든 위치 찾기
def find_update_targets(searcher, old_value):
    results = searcher.search_value(str(old_value))
    
    update_paths = []
    for result in results:
        if result['value'] == old_value:
            update_paths.append({
                'path': result['path'],
                'current_value': result['value'],
                'description': result.get('description', 'No description')
            })
    
    return update_paths

# 사용
targets = find_update_targets(searcher, "localhost")
print(f"'localhost'를 업데이트해야 할 위치: {len(targets)}개")
```

## 주의사항

1. **대소문자 구분**: 검색은 대소문자를 구분하지 않지만, 경로와 값은 원본 그대로 반환됩니다.

2. **설명 키 규칙**: 
   - 설명 키는 `$`로 시작해야 합니다
   - 설명 키는 해당 키와 같은 레벨에 있어야 합니다
   - 설명 키 자체는 검색 대상에서 제외됩니다

3. **성능 고려사항**:
   - 큰 JSON 파일의 경우 첫 검색이 느릴 수 있습니다
   - threshold를 낮추면 더 많은 비교 연산이 필요합니다
   - 자주 사용하는 검색 결과는 캐싱을 고려하세요

4. **경로 표현**:
   - 딕셔너리 키: 점(`.`)으로 구분
   - 배열 인덱스: 대괄호(`[]`) 사용
   - 예: `users[0].profile.settings.theme`

## 문제 해결

### 인코딩 문제
```python
# UTF-8이 아닌 경우
with open('data.json', 'r', encoding='cp949') as f:
    data = json.load(f)
searcher = JSONPathSearcher(json_data=data)
```

### 특수 문자가 포함된 키
```python
# 점(.)이 포함된 키는 경로 파싱에 주의
# 예: {"user.name": "value"} 
# 이런 경우 get_value_by_path가 제대로 동작하지 않을 수 있음
```

### 메모리 효율
```python
# 큰 파일의 경우 필요한 부분만 로드
import ijson

# 스트리밍 방식으로 처리 (별도 구현 필요)
```

## 라이선스 및 기여
이 코드는 자유롭게 사용 가능합니다. 개선 사항이나 버그 리포트는 환영합니다.