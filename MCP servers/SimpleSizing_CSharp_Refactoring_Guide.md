# SimpleSizing C# 리팩토링 가이드

## 목표
SimpleSizingForm.cs의 `DgvResults_RowHeaderMouseDoubleClick`와 Program.cs의 IPC handler가 **동일한 로직**을 사용하도록 리팩토링

---

## 1단계: 공통 데이터 클래스 생성 (SimpleSizingCase.cs)

새 파일 생성: `GearDesign/Utility/SimpleSizingCase.cs`

```csharp
namespace GearDesign.Utility
{
    /// <summary>
    /// SimpleSizing 결과 케이스 데이터
    /// </summary>
    public class SimpleSizingCase
    {
        public string Z1 { get; set; }
        public string Z2 { get; set; }
        public string Module { get; set; }  // m_n [mm]
        public string CenterDistance { get; set; }  // a [mm]
        public string HelixAngle { get; set; }  // β [deg]
        public string PressureAngle { get; set; }  // α_n [deg]
        public string FaceWidth { get; set; }  // Facewidth [mm]

        /// <summary>
        /// DataGridViewRow에서 SimpleSizingCase 생성
        /// </summary>
        public static SimpleSizingCase FromDataGridViewRow(DataGridViewRow row)
        {
            return new SimpleSizingCase
            {
                Z1 = GetCellValueSafely(row, "z1"),
                Z2 = GetCellValueSafely(row, "z2"),
                Module = GetCellValueSafely(row, "m_n [mm]"),
                CenterDistance = GetCellValueSafely(row, "a [mm]"),
                HelixAngle = GetCellValueSafely(row, "β [deg]"),
                PressureAngle = GetCellValueSafely(row, "α_n [deg]"),
                FaceWidth = GetCellValueSafely(row, "Facewidth [mm]")
            };
        }

        /// <summary>
        /// Dictionary (IPC)에서 SimpleSizingCase 생성
        /// </summary>
        public static SimpleSizingCase FromDictionary(Dictionary<string, object> data)
        {
            return new SimpleSizingCase
            {
                Z1 = GetValueSafely(data, "z1"),
                Z2 = GetValueSafely(data, "z2"),
                Module = GetValueSafely(data, "module"),
                CenterDistance = GetValueSafely(data, "center_distance") ?? GetValueSafely(data, "a"),
                HelixAngle = GetValueSafely(data, "helix_angle"),
                PressureAngle = GetValueSafely(data, "pressure_angle"),
                FaceWidth = GetValueSafely(data, "face_width")
            };
        }

        private static string GetCellValueSafely(DataGridViewRow row, string columnName)
        {
            try
            {
                if (row.DataGridView.Columns.Contains(columnName) && row.Cells[columnName].Value != null)
                {
                    return row.Cells[columnName].Value.ToString();
                }
            }
            catch
            {
                // Ignore
            }
            return string.Empty;
        }

        private static string GetValueSafely(Dictionary<string, object> data, string key)
        {
            if (data.TryGetValue(key, out var value) && value != null)
            {
                return value.ToString();
            }
            return null;
        }

        /// <summary>
        /// 필수 값들이 모두 존재하는지 확인
        /// </summary>
        public bool IsValid()
        {
            return !string.IsNullOrEmpty(Z1) &&
                   !string.IsNullOrEmpty(Z2) &&
                   !string.IsNullOrEmpty(Module);
        }
    }
}
```

---

## 2단계: SimpleSizingForm.cs에 공통 함수 추가

```csharp
/// <summary>
/// SimpleSizing 케이스를 Main Form에 적용 (공통 로직)
/// </summary>
public static bool ApplySizingCaseToMainForm(Form1 mainForm, SimpleSizingCase sizingCase)
{
    if (mainForm == null)
    {
        throw new ArgumentNullException(nameof(mainForm), "Main form reference is null");
    }

    if (!sizingCase.IsValid())
    {
        throw new ArgumentException("SimpleSizingCase is not valid (missing required fields: z1, z2, module)");
    }

    try
    {
        // Apply values to main form
        mainForm.TB_m_n.Text = sizingCase.Module;
        mainForm.TB_z1.Text = sizingCase.Z1;
        mainForm.TB_z2.Text = sizingCase.Z2;
        mainForm.TB_x1.Text = "0.0000";  // 전위계수 초기화
        mainForm.TB_x2.Text = "0.0000";
        mainForm.TB_a1.Text = sizingCase.CenterDistance ?? string.Empty;
        mainForm.TB_j_bn1.Text = "0.0000";
        mainForm.TB_alpha_n.Text = sizingCase.PressureAngle ?? string.Empty;
        mainForm.TB_beta.Text = sizingCase.HelixAngle ?? string.Empty;
        mainForm.TB_b1.Text = sizingCase.FaceWidth ?? string.Empty;
        mainForm.TB_b2.Text = sizingCase.FaceWidth ?? string.Empty;
        mainForm.Drop_CDMethod.SelectedIndex = 0; // Center Distance Method: Auto

        return true;
    }
    catch (Exception ex)
    {
        throw new Exception($"Failed to apply sizing case to main form: {ex.Message}", ex);
    }
}
```

---

## 3단계: SimpleSizingForm.cs의 DgvResults_RowHeaderMouseDoubleClick 리팩토링

**기존 코드 (491-545줄)를 다음과 같이 변경**:

```csharp
private void DgvResults_RowHeaderMouseDoubleClick(object sender, DataGridViewCellMouseEventArgs e)
{
    try
    {
        DataGridView dgv = sender as DataGridView;
        int rowIndex = e.RowIndex;

        if (rowIndex < 0 || dgv.Rows.Count <= rowIndex)
            return;

        if (_input.mainForm == null)
        {
            MessageBox.Show("Main form reference not found. Cannot apply values.",
                "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        DataGridViewRow selectedRow = dgv.Rows[rowIndex];

        // 공통 데이터 클래스로 변환
        var sizingCase = SimpleSizingCase.FromDataGridViewRow(selectedRow);

        if (!sizingCase.IsValid())
        {
            MessageBox.Show("Unable to extract required values (z1, z2, module) from the selected row.",
                "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        // 공통 함수 호출
        ApplySizingCaseToMainForm(_input.mainForm, sizingCase);

        MessageBox.Show($"Values applied to main form:\nZ1: {sizingCase.Z1}\nZ2: {sizingCase.Z2}\nModule: {sizingCase.Module} mm",
            "Values Applied", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error applying values: {ex.Message}",
            "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
    }
}
```

---

## 4단계: Program.cs의 IPC handler 구현

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
        // Dictionary → SimpleSizingCase 변환
        var sizingCase = SimpleSizingCase.FromDictionary(caseData);

        if (!sizingCase.IsValid())
        {
            result = new { success = false, error = "필수 필드 누락 (z1, z2, module)" };
            break;
        }

        // 공통 함수 호출 (SimpleSizingForm과 동일한 로직)
        SimpleSizingForm.ApplySizingCaseToMainForm(mainForm, sizingCase);

        // 변경된 config 직렬화 (Python으로 반환)
        var updatedConfig = SerializeCurrentConfig();

        result = new {
            success = true,
            message = "SimpleSizing 케이스가 적용되었습니다",
            updated_config = updatedConfig
        };
    }
    catch (Exception ex)
    {
        result = new { success = false, error = ex.Message };
    }
    break;
}
```

---

## 5단계: SerializeCurrentConfig() 구현 (Program.cs)

```csharp
/// <summary>
/// 현재 mainForm의 config를 Dictionary로 직렬화
/// </summary>
private Dictionary<string, object> SerializeCurrentConfig()
{
    var config = new Dictionary<string, object>();

    // Basic Data 섹션
    var basicData = new Dictionary<string, object>
    {
        { "Normal Module", ParseDouble(mainForm.TB_m_n.Text) },
        { "z1", ParseInt(mainForm.TB_z1.Text) },
        { "z2", ParseInt(mainForm.TB_z2.Text) },
        { "Helix Angle", ParseDouble(mainForm.TB_beta.Text) },
        { "Pressure Angle", ParseDouble(mainForm.TB_alpha_n.Text) },
        { "x1", ParseDouble(mainForm.TB_x1.Text) },
        { "x2", ParseDouble(mainForm.TB_x2.Text) },
        { "Center Distance", ParseDouble(mainForm.TB_a1.Text) },
        { "CDMethod", mainForm.Drop_CDMethod.SelectedIndex },
        { "Face Width 1", ParseDouble(mainForm.TB_b1.Text) },
        { "Face Width 2", ParseDouble(mainForm.TB_b2.Text) }
        // 필요한 다른 필드들...
    };

    config["Basic Data"] = basicData;

    // Load Case, Material 등 다른 섹션도 필요에 따라 추가
    // config["Load Case"] = ...;
    // config["Material"] = ...;

    return config;
}

private double ParseDouble(string text)
{
    if (double.TryParse(text, out var value))
        return value;
    return 0.0;
}

private int ParseInt(string text)
{
    if (int.TryParse(text, out var value))
        return value;
    return 0;
}
```

---

## 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│ SimpleSizingForm (DataGridView 더블클릭)                     │
│                                                               │
│ DataGridViewRow                                               │
│       ↓                                                       │
│ SimpleSizingCase.FromDataGridViewRow()                       │
│       ↓                                                       │
│ SimpleSizingForm.ApplySizingCaseToMainForm()  ← 공통 함수    │
│       ↓                                                       │
│ mainForm.TB_* 업데이트                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Program.cs (IPC handler)                                     │
│                                                               │
│ Dictionary<string, object> (from Python)                     │
│       ↓                                                       │
│ SimpleSizingCase.FromDictionary()                            │
│       ↓                                                       │
│ SimpleSizingForm.ApplySizingCaseToMainForm()  ← 공통 함수    │
│       ↓                                                       │
│ mainForm.TB_* 업데이트                                        │
│       ↓                                                       │
│ SerializeCurrentConfig()                                     │
│       ↓                                                       │
│ updated_config → Python                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Python 측 컬럼명 매핑

Python SimpleSizing 결과에서 C#으로 전달되는 키:

| Python DataFrame 컬럼 | C# SimpleSizingCase 프로퍼티 | C# DataGridView 컬럼 |
|----------------------|------------------------------|---------------------|
| `z1` | `Z1` | `"z1"` |
| `z2` | `Z2` | `"z2"` |
| `module` | `Module` | `"m_n [mm]"` |
| `helix_angle` | `HelixAngle` | `"β [deg]"` |
| `pressure_angle` | `PressureAngle` | `"α_n [deg]"` |
| `face_width` | `FaceWidth` | `"Facewidth [mm]"` |
| `center_distance` 또는 `a` | `CenterDistance` | `"a [mm]"` |

---

## 장점

1. **단일 책임 원칙**: SimpleSizingCase가 데이터 변환 책임
2. **코드 중복 제거**: DgvResults_RowHeaderMouseDoubleClick와 IPC handler가 동일한 로직 사용
3. **유지보수 용이**: 비즈니스 로직 변경 시 한 곳만 수정
4. **테스트 가능**: ApplySizingCaseToMainForm()을 독립적으로 테스트 가능
5. **확장성**: 새로운 필드 추가 시 SimpleSizingCase만 수정

---

## 구현 체크리스트

- [ ] SimpleSizingCase.cs 파일 생성
- [ ] SimpleSizingForm.cs에 ApplySizingCaseToMainForm() 추가
- [ ] SimpleSizingForm.cs의 DgvResults_RowHeaderMouseDoubleClick 리팩토링
- [ ] Program.cs에 apply_simplesizing_case handler 추가
- [ ] Program.cs에 SerializeCurrentConfig() 추가
- [ ] 테스트:
  - [ ] SimpleSizingForm에서 더블클릭 테스트
  - [ ] Python IPC를 통한 적용 테스트
  - [ ] updated_config가 정확히 반환되는지 확인
