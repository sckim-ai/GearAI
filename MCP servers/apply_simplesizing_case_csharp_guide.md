# C# Program.cs 구현 가이드: apply_simplesizing_case

## 구현 위치
`Program.cs`의 IPC command handler 부분

## 구현 코드

```csharp
case "apply_simplesizing_case":
{
    var caseData = command["case_data"]?.ToObject<Dictionary<string, object>>();
    if (caseData == null)
    {
        result = new { success = false, error = "case_data가 제공되지 않았습니다" };
        break;
    }

    try
    {
        // SimpleSizing 케이스 데이터를 현재 config에 적용
        ApplySizingCaseToConfig(caseData);

        // 변경된 전체 config 데이터를 직렬화하여 반환
        var updatedConfig = SerializeCurrentConfig();

        result = new {
            success = true,
            message = "SimpleSizing 케이스가 적용되었습니다",
            updated_config = updatedConfig  // 중요: 변경된 config 반환
        };
    }
    catch (Exception ex)
    {
        result = new { success = false, error = ex.Message };
    }
    break;
}
```

## 헬퍼 메서드 1: ApplySizingCaseToConfig

```csharp
/// <summary>
/// SimpleSizing 케이스 데이터를 현재 기어 설계 config에 적용
/// (SimpleSizingForm의 DgvResults_RowHeaderMouseDoubleClick 로직과 유사)
/// </summary>
private void ApplySizingCaseToConfig(Dictionary<string, object> caseData)
{
    // basicData는 현재 로드된 GearDesign config의 BasicData 객체

    // 모듈
    if (caseData.TryGetValue("module", out var module))
        basicData.NormalModule = Convert.ToDouble(module);

    // 잇수
    if (caseData.TryGetValue("z1", out var z1))
        basicData.z1 = Convert.ToInt32(z1);

    if (caseData.TryGetValue("z2", out var z2))
        basicData.z2 = Convert.ToInt32(z2);

    // 헬리컬각
    if (caseData.TryGetValue("helix_angle", out var helixAngle))
        basicData.HelixAngle = Convert.ToDouble(helixAngle);

    // 전위계수
    if (caseData.TryGetValue("x1", out var x1))
        basicData.x1 = Convert.ToDouble(x1);

    if (caseData.TryGetValue("x2", out var x2))
        basicData.x2 = Convert.ToDouble(x2);

    // 치폭 (선택사항)
    if (caseData.TryGetValue("face_width", out var faceWidth))
        basicData.FaceWidth = Convert.ToDouble(faceWidth);

    // 중심거리 계산 방법을 자동으로 설정
    basicData.CDMethod = 1; // 1 = 자동 계산

    // Config 유효성 검증 및 업데이트
    ValidateAndApplyConfig();
}

/// <summary>
/// Config 유효성 검증 및 내부 데이터 구조 업데이트
/// </summary>
private void ValidateAndApplyConfig()
{
    // 기어 타입에 따른 유효성 검증
    // 예: 잇수가 최소값 이상인지, 모듈이 유효한지 등

    // 필요한 경우 중심거리 재계산
    if (basicData.CDMethod == 1)
    {
        // 자동 중심거리 계산 로직
        CalculateCenterDistance();
    }

    // 내부 config 객체 업데이트
    UpdateInternalConfig();
}
```

## 헬퍼 메서드 2: SerializeCurrentConfig

```csharp
/// <summary>
/// 현재 GearDesign config를 Python이 이해할 수 있는 Dictionary로 직렬화
/// (load_and_validate_config의 입력 형식과 동일)
/// </summary>
private Dictionary<string, object> SerializeCurrentConfig()
{
    var config = new Dictionary<string, object>();

    // Basic Data 섹션
    var basicDataDict = new Dictionary<string, object>
    {
        { "Normal Module", basicData.NormalModule },
        { "z1", basicData.z1 },
        { "z2", basicData.z2 },
        { "Helix Angle", basicData.HelixAngle },
        { "Pressure Angle", basicData.PressureAngle },
        { "x1", basicData.x1 },
        { "x2", basicData.x2 },
        { "CDMethod", basicData.CDMethod },
        { "Center Distance", basicData.CenterDistance },
        // 필요한 다른 필드들...
    };

    config["Basic Data"] = basicDataDict;

    // Load Case 섹션 (있는 경우)
    if (loadCaseData != null)
    {
        var loadCaseDict = new Dictionary<string, object>
        {
            { "Torque1", loadCaseData.Torque1 },
            { "Speed1", loadCaseData.Speed1 },
            // 필요한 다른 필드들...
        };
        config["Load Case"] = loadCaseDict;
    }

    // 다른 섹션들...
    // config["Material"] = ...;
    // config["Tolerance"] = ...;

    return config;
}
```

## 데이터 흐름

```
Python (apply_simplesizing_case)
    ↓ IPC command
    {
        "action": "apply_simplesizing_case",
        "case_data": {
            "module": 2.5,
            "z1": 25,
            "z2": 75,
            "helix_angle": 15.0,
            "x1": 0.2,
            "x2": 0.2,
            ...
        }
    }
    ↓
C# (Program.cs)
    ↓ ApplySizingCaseToConfig(caseData)
    - basicData.NormalModule = 2.5
    - basicData.z1 = 25
    - basicData.z2 = 75
    - basicData.CDMethod = 1
    - ValidateAndApplyConfig()
    ↓ SerializeCurrentConfig()
    {
        "Basic Data": {
            "Normal Module": 2.5,
            "z1": 25,
            "z2": 75,
            "CDMethod": 1,
            ...
        },
        "Load Case": {...},
        ...
    }
    ↓ IPC response
    {
        "success": true,
        "message": "SimpleSizing 케이스가 적용되었습니다",
        "updated_config": {...}  // 위의 직렬화된 config
    }
    ↓
Python (apply_simplesizing_case)
    session.changed_data = updated_config
```

## 중요 사항

1. **updated_config 반환 필수**: Python에서 session.changed_data와 C# 내부 상태를 동기화하려면 반드시 updated_config를 반환해야 합니다.

2. **전체 config 반환**: 변경된 부분만이 아니라 전체 config를 반환해야 다른 함수들과 일관성을 유지할 수 있습니다.

3. **SimpleSizingForm 로직 재사용**: 기존 SimpleSizingForm의 DgvResults_RowHeaderMouseDoubleClick에 있는 로직을 재사용하면 일관된 동작을 보장할 수 있습니다.

4. **하위 호환성**: updated_config가 없어도 Python 코드는 경고만 출력하고 계속 실행됩니다. 하지만 데이터 동기화를 위해 구현을 권장합니다.

5. **타입 변환**: caseData의 값들은 object 타입이므로 적절한 타입으로 변환해야 합니다 (Convert.ToDouble, Convert.ToInt32 등).
