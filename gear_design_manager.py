"""
GearDesign .NET 라이브러리와의 상호작용을 관리하는 최적화된 클래스
"""
import time
import functools
import os
import sys
import pathlib
import json
import threading
from typing import Optional, Dict, Any, Callable
import pandas as pd


class TimerDecorator:
    """성능 측정을 위한 데코레이터"""
    
    @staticmethod
    def time_it(description: str):
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


class DotNetInitializer:
    """Python.NET 초기화를 담당하는 클래스"""
    
    def __init__(self, gear_design_path: str):
        self.base_path = pathlib.Path(gear_design_path)
        self.dll_path = self.base_path / "GearDesign.dll"
        self.config_path = self.base_path / "GearDesign.runtimeconfig.json"
        
    def initialize(self):
        """Python.NET 및 .NET 런타임 초기화"""
        from pythonnet import load
        
        # .NET 8 CoreCLR + WindowsDesktop 런타임 로드
        load("coreclr", runtime_config=str(self.config_path))
        
        # DLL 경로 설정
        os.add_dll_directory(str(self.base_path))
        sys.path.append(str(self.base_path))
        os.chdir(str(self.base_path))
        
        # CLR 및 어셈블리 로드
        import clr
        clr.AddReference(str(self.dll_path))
        
        # 스레드 설정
        self._setup_threading()
        
        return True
        
    def _setup_threading(self):
        """스레딩 환경 설정"""
        import System.Threading as Th
        from System.Threading import SynchronizationContext
        
        # STA 모드 설정
        Th.Thread.CurrentThread.TrySetApartmentState(Th.ApartmentState.STA)
        
        # SynchronizationContext 제거 (async 데드락 방지)
        SynchronizationContext.SetSynchronizationContext(None)
        
        print(f"Thread apartment state: {Th.Thread.CurrentThread.ApartmentState}")
        print(f"Thread ID: {Th.Thread.CurrentThread.ManagedThreadId}")


class GearDesignManager:
    """GearDesign 작업을 관리하는 메인 클래스"""
    
    def __init__(self, gear_design_path: str, default_json_path: str):
        self.gear_design_path = gear_design_path
        self.default_json_path = default_json_path
        self.form = None
        self._dotnet_init = DotNetInitializer(gear_design_path)
        self._initialize_dotnet()
        
    def _initialize_dotnet(self):
        """Python.NET 초기화"""
        self._dotnet_init.initialize()
        
        # .NET 타입 import
        from GearDesign import GearDesignForm
        from GearDesign.Utility import SimpleSizing, SimpleSizingInput, SimpleSizingOutput
        from System import Action
        from System.Threading import CancellationTokenSource
        from System.Threading.Tasks import Task, TaskScheduler
        import System.Threading.Tasks as Tasks
        from System import Func
        from Newtonsoft.Json.Linq import JObject
        from System.Data import DataTable
        
        # 클래스 속성에 저장
        self.GearDesignForm = GearDesignForm
        self.SimpleSizing = SimpleSizing
        self.SimpleSizingInput = SimpleSizingInput
        self.SimpleSizingOutput = SimpleSizingOutput
        self.Action = Action
        self.CancellationTokenSource = CancellationTokenSource
        self.Task = Task
        self.Tasks = Tasks
        self.Func = Func
        self.JObject = JObject
        self.DataTable = DataTable
        
    def initialize_form(self) -> bool:
        """GearDesignForm 초기화"""
        try:
            self.form = self.GearDesignForm(self.gear_design_path)
            self.form.Initial_Load()
            return True
        except Exception as e:
            print(f"Form 초기화 실패: {e}")
            return False
            
    def save_default_config(self) -> Dict[str, Any]:
        """기본 설정을 JSON 파일로 저장"""
        if not self.form:
            raise ValueError("Form이 초기화되지 않았습니다")
            
        # 현재 상태 저장
        jGear = self.form.SaveDataInput_Json(True)
        jGear_py = json.loads(jGear.ToString())
        
        # 파일에 저장
        with open(self.default_json_path, "w", encoding="utf-8") as f:
            json.dump(jGear_py, f, ensure_ascii=False, indent=2)
            
        return jGear_py
        
    def load_and_validate_config(self, config_data: Dict[str, Any]) -> bool:
        """설정 데이터 로드 및 검증"""
        if not self.form:
            raise ValueError("Form이 초기화되지 않았습니다")
            
        # Python dict → JSON 변환
        jGear = self.JObject.Parse(json.dumps(config_data))
        
        # 데이터 검증
        dataValid = self.form.LoadData_Validation(jGear)
        if not dataValid.IsValid:
            errorMessage = "JSON 검증 실패:\n" + "\n".join(dataValid.Errors)
            raise ValueError(errorMessage)
            
        # 데이터 로드
        self.form.LoadDataInput_Json(jGear)
        return True
        
    @TimerDecorator.time_it("기하학적 계산")
    def calculate_geometry(self):
        """기하학적 계산 수행"""
        if not self.form:
            raise ValueError("Form이 초기화되지 않았습니다")
        return self.form.CalcGeometry()
        
    @TimerDecorator.time_it("하중 계산")
    def calculate_load_case(self, geometry_result):
        """하중 계산 수행"""
        if not self.form:
            raise ValueError("Form이 초기화되지 않았습니다")
        return self.form.CalcLoadCase(geometry_result)
        
    def get_messages(self):
        """계산결과에 대한 실행 메시지 (경고, 오류 포함), 실행 후 메시지는 초기화됨"""
        if not self.form:
            raise ValueError("Form이 초기화되지 않았습니다")
        Result_Message = self.form.GetMessages()
        self.form.ClearMessages()
        return Result_Message
    
    def get_gearimage(self, path: str) -> bool:
        """기어 물림 이미지 추출. 성공 시 true 반환"""
        issuccess = self.form.SaveGearImage(path)
        return issuccess
        
    def create_simple_sizing_input(self) -> Any:
        """빈 SimpleSizingInput 객체 생성 (설정은 외부에서 수행)"""
        _input = self.SimpleSizingInput()
        _input.mainForm = self.form
        return _input
        
    def simple_sizing_calculate(self, 
                              sizing_input: Any, 
                              with_rating: bool = True, 
                              use_parallel: bool = False,
                              progress_callback: Optional[Callable[[int, int], None]] = None,
                              timeout_seconds: int = 300) -> Optional[Any]:
        """SimpleSizing 계산 수행"""
        
        # 진행률 콜백 설정
        if progress_callback:
            update_progress = self.Action[int, int](progress_callback)
        else:
            update_progress = self.Action[int, int](lambda current, total: 
                print(f"Progress: {current}/{total} ({current/total*100:.1f}%)"))
        
        # 취소 토큰 설정
        cancellation_source = self.CancellationTokenSource()
        
        try:
            # Task.Run으로 감싸서 SynchronizationContext 문제 해결
            def create_calculation_task():
                return self.SimpleSizing.Calculate(
                    sizing_input, with_rating, use_parallel, 
                    update_progress, cancellation_source.Token
                )
            
            task_func = self.Func[self.Tasks.Task[self.SimpleSizingOutput]](create_calculation_task)
            task = self.Task.Run[self.SimpleSizingOutput](task_func)
            
            # 타임아웃 설정
            timeout_thread = threading.Thread(
                target=self._cancel_after_timeout, 
                args=(cancellation_source, timeout_seconds, task)
            )
            timeout_thread.daemon = True
            timeout_thread.start()
            
            # Task 완료 대기
            return self._wait_for_task_completion(task, timeout_seconds)
            
        except Exception as e:
            print(f"SimpleSizing 계산 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            cancellation_source.Dispose()
            
    def _cancel_after_timeout(self, cancellation_source, timeout_seconds: int, task):
        """타임아웃 후 작업 취소"""
        time.sleep(timeout_seconds)
        if not task.IsCompleted:
            print(f"{timeout_seconds}초 후 작업을 취소합니다...")
            cancellation_source.Cancel()
            
    def _wait_for_task_completion(self, task, timeout_seconds: int, check_interval: int = 2) -> Optional[Any]:
        """Task 완료 대기"""
        timeout_ms = timeout_seconds * 1000
        check_interval_ms = check_interval * 1000
        elapsed = 0
        
        print("Task 완료 대기 중...")
        
        while elapsed < timeout_ms:
            if task.Wait(check_interval_ms):
                # Task 완료
                if task.IsFaulted:
                    exception_msg = str(task.Exception) if task.Exception else "Unknown error"
                    print(f"Task 실패: {exception_msg}")
                    return None
                elif task.IsCanceled:
                    print("Task가 취소되었습니다")
                    return None
                else:
                    print("Task 성공!")
                    return task.Result
                    
            elapsed += check_interval_ms
            print(f"Sizing 수행 중... {elapsed/1000}초 경과, Status: {task.Status}")
            
        print("Task가 제한시간 내에 완료되지 않았습니다")
        return None
        
    @staticmethod
    def convert_datatable_to_dataframe(datatable) -> Optional[pd.DataFrame]:
        """DataTable을 pandas DataFrame으로 변환"""
        if datatable is None:
            return None
            
        try:
            data = []
            for row in datatable.Rows:
                row_dict = {}
                for col in datatable.Columns:
                    col_name = str(col.ColumnName)
                    col_value = row[col_name]
                    row_dict[col_name] = col_value
                data.append(row_dict)
                
            return pd.DataFrame(data)
        except Exception as e:
            print(f"DataTable 변환 오류: {e}")
            return None


