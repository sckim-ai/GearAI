# .NET IPC에 추가 필요한 Actions

mcp_server_gd_ipc.py가 완전히 동작하려면 다음 action들을 .NET의 ProcessCommand 메서드에 추가해야 합니다.

## 1. get_default_config

**목적**: 초기 기본 설정 데이터를 JSON 형식으로 반환

**구현 예시**:
```csharp
case "get_default_config":
    var defaultConfig = form.SaveDataInput_Json(true);
    return new {
        success = true,
        config = defaultConfig
    };
```

**Python에서 호출**:
```python
response = session.ipc_client.get_default_config()
# response = {"success": true, "config": {...}}
```

**현재 상태**: ❌ 미구현 (Python에서 fallback 처리됨)

---

## 2. get_all_results_summary

**목적**: 모든 계산 결과의 요약 정보를 반환 (markdown 형식)

**구현 예시**:
```csharp
case "get_all_results_summary":
    // gd_results_obj가 필요한데, 세션별로 관리 필요
    // 현재 .NET 코드가 stateless라면 구현 어려움

    // Option 1: 클라이언트에서 results를 보내는 방식
    var resultsObj = (JObject)command?["results"];
    if (resultsObj == null)
        return new { success = false, error = "results 데이터가 필요합니다" };

    var summary = form.GetAllResultSummary(resultsObj);
    return new {
        success = true,
        summary = summary
    };

    // Option 2: .NET에서 세션 관리
    // 세션 ID 기반으로 계산 결과 저장 후 조회
```

**Python에서 호출**:
```python
response = session.ipc_client.get_all_results_summary()
# response = {"success": true, "summary": {...}}
```

**현재 상태**: ❌ 미구현 (Python에서 fallback 처리됨)

---

## 3. get_geometry_results

**목적**: 기하학적 계산 결과만 조회 (세션 관리 필요)

**구현 예시**:
```csharp
case "get_geometry_results":
    // 세션별로 마지막 기하학적 계산 결과를 저장해야 함
    // stateless 구조에서는 구현 어려움

    // Option: calc_geometry 결과를 클라이언트가 저장하고 필요시 전달
    return new {
        success = false,
        error = "세션 관리가 필요한 action입니다. Python 세션에서 관리됩니다."
    };
```

**Python에서 호출**:
```python
response = session.ipc_client.get_geometry_results()
```

**현재 상태**: ❌ 미구현 (Python 세션에서 관리됨)

---

## 4. simple_sizing (미완성)

**목적**: SimpleSizing 계산 수행

**구현 예시**:
```csharp
case "simple_sizing":
    var sizingInput = command["input"]; // SimpleSizingInput 데이터
    bool withRating = command["with_rating"]?.ToObject<bool>() ?? true;
    bool useParallel = command["use_parallel"]?.ToObject<bool>() ?? false;
    int timeoutSeconds = command["timeout"]?.ToObject<int>() ?? 300;

    // SimpleSizing.Calculate 호출
    // progress callback 처리 필요 (IPC에서는 어려움)

    var sizingOutput = SimpleSizing.Calculate(
        sizingInput,
        withRating,
        useParallel,
        null, // progress callback
        cancellationToken
    );

    return new {
        success = true,
        output = sizingOutput
    };
```

**현재 상태**: ❌ 미구현

---

## 구현 우선순위

1. **get_default_config** (높음) - 초기화 시 필요
2. **get_all_results_summary** (중간) - 현재 Python fallback으로 동작
3. **get_geometry_results** (낮음) - Python 세션에서 이미 관리
4. **simple_sizing** (낮음) - 고급 기능

---

## .NET 세션 관리 고려사항

현재 .NET IPC 코드는 stateless입니다. 각 command마다 독립적으로 처리됩니다.

**문제점**:
- `calc_geometry` 결과를 저장하지 않아 `calc_loadcase`에서 재사용 불가
- `get_geometry_results`같은 조회 기능 구현 어려움

**해결 방안**:
1. Python에서 세션 관리 (현재 방식) ✅
2. .NET에서도 간단한 세션 관리 추가
   - Dictionary<string, object> sessions
   - session_id를 command에 포함

**권장**: 현재 Python에서 세션 관리하는 방식 유지
