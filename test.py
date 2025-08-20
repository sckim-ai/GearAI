import time
import functools

def time_it(description):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"[Timer] {description}: {end - start:.4f}초")
            return result
        return wrapper
    return decorator


# ① pythonnet load
from pythonnet import load          # ① 먼저 load 함수만 가져옵니다

import os, sys, pathlib             # ② clr 는 아직 import 하지 않습니다

base = pathlib.Path(r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows")
dll  = base / "GearDesign.dll"
cfg  = base / "GearDesign.runtimeconfig.json"

# ③ .NET 8 CoreCLR + WindowsDesktop 런타임을 ‘가장 먼저’ 올립니다
load("coreclr", runtime_config=str(cfg))

# ④ 이제 의존 DLL 경로 추가
os.add_dll_directory(str(base))
sys.path.append(str(base))
os.chdir(str(base)) 

import clr                           # ⑤ 이 시점에야 clr 를 import!

# ⑥ 어셈블리 로드 & 타입 확인
asm = clr.AddReference(str(dll))    # 여기서 불러온 dll이 참고하고 있는 Nuget을 Pyhonnet을 통해 자동으로 참조가능

import System.Windows.Forms as WinForms
from GearDesign import GearDesignForm
import System.Threading as Th
import json
from Newtonsoft.Json.Linq import JObject
from GearDesign.Utility import SimpleSizing, SimpleSizingInput, SimpleSizingOutput

# WinForms는 STA(Single-Threaded Apartment) 모드여야 함
Th.Thread.CurrentThread.TrySetApartmentState(Th.ApartmentState.STA)

form = GearDesignForm(str(base))                 # ← 인스턴스 생성

# ⑪ 초기 로드
form.Initial_Load()

# ⑫ 현재 상태 저장
jGear = form.SaveDataInput_Json(True)       # 현 상태 저장

# ⑬ JSON → Python dict 변환
jGear_py = json.loads(jGear.ToString())    # json -> dict

# Default.json 파일 경로 지정
default_json_path = r"D:\SW\Streamlit\agents\data\schema\Default.json"

# 파일에 저장 (UTF-8 인코딩)
with open(default_json_path, "w", encoding="utf-8") as f:
    json.dump(jGear_py, f, ensure_ascii=False, indent=2)


# ⑭ 데이터 수정
jGear_py["Basic Data"]["GearTypeNum"] = "0"
jGear_py["Basic Data"]["Normal Module"] = "3"
jGear_py["Basic Data"]["CDMethod"] = 1

# ⑮ Python dict → JSON 변환
jGear = JObject.Parse(json.dumps(jGear_py))

# 데이터 검증
dataValid = form.LoadData_Validation(jGear)
if not dataValid.IsValid:
    errorMessage = "\nJSON 검증 실패:\n" + "\n".join(dataValid.Errors)
    raise ValueError(errorMessage)

# ⑯ 데이터 로드
form.LoadDataInput_Json(jGear)

# ⑰ 기하학적 계산
start = time.perf_counter()
Result_Geo = form.CalcGeometry()
end = time.perf_counter()
print(f"[Timer] CalcGeometry(): {end - start:.4f}초")

# ⑱ 하중 계산
start = time.perf_counter()
Result_Rating = form.CalcLoadCase(Result_Geo)
end = time.perf_counter()
print(f"[Timer] CalcLoadCase(): {end - start:.4f}초")

# 3. 메시지 관리

# Result_Message = form.GetMessages()

# print(jGear)

# form.ClearMessages() # 메시지 초기화
_input = SimpleSizingInput()
_input.target_GR = 3
_input.target_GR_dev = 5 / 100.0
_input.z_pinion_min = 15
_input.z_pinion_max = 35
_input.z_pinion_step = 1
_input.hunting = 0
_input.m_n_min = 2
_input.m_n_max = 5
_input.m_n_step = 0.5
_input.a_max = 500
_input.a_min = 100
_input.d_max = 500
_input.d_min = 10
_input.maxcases = 1000
_input.helix_angle = 0
_input.pressure_angle = 20
_input.min_contact_safety_factor = 1.2
_input.min_bending_safety_factor = 1.6

import asyncio
import System.Threading.Tasks as Tasks

# Define missing parameters for the C# method call
withRating = True  # Boolean parameter for including rating calculations
useParallel = False  # Boolean parameter for parallel processing (set to false as per C# code)

# Import necessary .NET types for delegates and cancellation
from System import Action
from System.Threading import CancellationTokenSource

# Create cancellation token source
_cancellationTokenSource = CancellationTokenSource()

# Define progress callback function with new signature
def progress_callback(current, total):
    """Progress update callback function"""
    percentage = (current / total * 100) if total > 0 else 0
    print(f"Progress: {current}/{total} ({percentage:.1f}%)")

# Convert Python function to .NET delegate
UpdateProgress = Action[int, int](progress_callback)  # Action<int, int> delegate

# Convert Python async call to work with .NET Task
async def calculate_simple_sizing():
    """Async wrapper for SimpleSizing.Calculate"""
    try:
        # Create the .NET Task
        task = SimpleSizing.Calculate(_input, withRating, useParallel, UpdateProgress, _cancellationTokenSource.Token)
        
        # Convert .NET Task to Python awaitable
        while not task.IsCompleted:
            await asyncio.sleep(3)  # Poll every 100ms
            
        if task.IsFaulted:
            raise Exception(f"Calculation failed: {task.Exception}")
            
        return task.Result
    except Exception as e:
        print(f"Error in SimpleSizing calculation: {e}")
        return None

# Simple synchronous approach
def calculate_simple_sizing_sync():
    """Synchronous wrapper for SimpleSizing.Calculate"""
    try:
        print("Starting SimpleSizing calculation (synchronous approach)...")
        
        # Create the .NET Task
        task = SimpleSizing.Calculate(_input, withRating, useParallel, UpdateProgress, _cancellationTokenSource.Token)
        print(f"Task created: {task}")
        print(f"Task type: {type(task)}")
        
        # Simple approach: try to wait for task completion
        try:
            print("Attempting to wait for task completion...")
            task_completed = task.Wait(300000)  # Wait up to 5 minutes
            
            if task_completed:
                print("Task completed!")
                if task.IsFaulted:
                    exception_msg = str(task.Exception) if task.Exception else "Unknown error"
                    print(f"Task faulted: {exception_msg}")
                    return None
                elif task.IsCanceled:
                    print("Task was canceled")
                    return None
                else:
                    print("Task succeeded!")
                    return task.Result
            else:
                print("Task did not complete within timeout")
                return None
                
        except Exception as wait_error:
            print(f"Error waiting for task: {wait_error}")
            print("Falling back to async approach...")
            return None
            
    except Exception as e:
        print(f"Error in synchronous SimpleSizing calculation: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None

# Execute the calculation
print("=== Starting SimpleSizing calculation ===")
_output = calculate_simple_sizing_sync()

# Print the calculation result
if _output is not None:
    print("\n✅ SimpleSizing calculation completed successfully!")
    print(f"Output type: {type(_output)}")
    
    # Convert .NET DataTable to pandas DataFrame
    try:
        import pandas as pd
        from System.Data import DataTable
        
        gear_list = _output.GearList
        print(f"GearList type: {type(gear_list)}")
        
        if gear_list is not None and isinstance(gear_list, DataTable):
            # Convert DataTable to list of dictionaries
            data = []
            for row in gear_list.Rows:
                row_dict = {}
                for col in gear_list.Columns:
                    col_name = str(col.ColumnName)
                    col_value = row[col_name]
                    row_dict[col_name] = col_value
                data.append(row_dict)
            
            # Create pandas DataFrame
            df = pd.DataFrame(data)
            print(f"\nDataFrame shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print("\nFirst few rows:")
            print(df.head())
            
            # Save to CSV for easy viewing
            df.to_csv("gear_results.csv", index=False, encoding='utf-8-sig')
            print("\n📊 Results saved to 'gear_results.csv'")
            
        else:
            print(f"GearList is not a DataTable: {gear_list}")
            
    except Exception as e:
        print(f"Error converting DataTable: {e}")
        print(f"Raw GearList: {_output.GearList}")
        
else:
    print("\n❌ SimpleSizing calculation failed!")



# ⑲ 결과 출력
# print(jGear)
# print(Result_Rating["Geometry"])
# print(Result_Rating["LC"])




