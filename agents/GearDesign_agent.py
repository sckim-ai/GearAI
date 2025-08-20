import time
import functools

def time_it(description):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"⏱️ {description}: {end - start:.4f}초")
            return result
        return wrapper
    return decorator


# ① pythonnet load
from pythonnet import load          # ① 먼저 load 함수만 가져옵니다

import os, sys, pathlib             # ② clr 는 아직 import 하지 않습니다

base = pathlib.Path(r"D:\SW\GearDesign\GearDesign\bin\Release\net8.0-windows")
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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import System.Windows.Forms as WinForms
from GearDesign import GearDesignForm
import System.Threading as Th
import json
from Newtonsoft.Json.Linq import JObject
from utils import llm_call, remove_code_block_llm  # LLM 호출 함수 임포트

# WinForms는 STA(Single-Threaded Apartment) 모드여야 함
Th.Thread.CurrentThread.TrySetApartmentState(Th.ApartmentState.STA)

form = GearDesignForm(str(base))                 # ← 인스턴스 생성
form.Initial_Load() # 초기 로드

# 1. Default.json 로드 (항상 현재 파일 위치 기준)   
default_json_path = os.path.join(os.path.dirname(__file__), "data", "schema", "Default.json")

with open(default_json_path, "r", encoding="utf-8") as f:
    gear_data = json.load(f)

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("GearDesign_agent")

@mcp.tool()
def initial_load() -> dict:
    """초기 로드, 초기 데이터 반환"""
    form.Initial_Load()
    jGear = form.SaveDataInput_Json(True)       # 현 상태 저장
    jGear_py = json.loads(jGear.ToString())    # json -> dict
    return jGear_py

@mcp.tool()
def edit_gear_data(user_message: str) -> dict:
    """사용자 메시지를 전달받아 기어 데이터로 전환하여 반환"""   

    # 2. LLM 프롬프트 구성
    system_prompt = (
        "너는 기어 설계 데이터의 JSON을 수정하는 AI야.\n"
        "아래의 사용자 요청에 따라 현재 JSON 데이터의 값을 적절히 변경해야 해.\n"
        "현재 JSON 데이터의 메타데이터는 Key 값 앞에 $가 붙어있으니 반드시 참고해서 데이터를 올바르게 변경해.\n"
        "반환 시 변경해야할 정확한 JSON KEY 값과 Value만 반환해.\n"    
        "매크로 기어 제원 (잇수, 모듈, 헬리컬각, 압력각, 전위계수 등)이 바뀌어 기어 사이의 중심거리가 변경되어야 하는 경우는 CDMethod를 1로 변경하여 중심거리를 자동계산하도록 해야 함\n"
        "반환하는 데이터 형태는 반드시 JSON의 표준 중첩구조를 따라야 해."
    )
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"사용자 요청: {user_message}\n현재 데이터: {json.dumps(gear_data, ensure_ascii=False)}"}
    ]

    # 3. LLM 호출 및 결과 파싱
    try:
        response = llm_call(prompt=prompt, model="gpt-4o-mini")
        edited_gear_data = remove_code_block_llm(response)
        edited_gear_data = json.loads(edited_gear_data)
        return edited_gear_data
    except Exception as e:
        print("LLM 응답 파싱 오류:", e)
        return {}  # 실패 시 null 반환

# 재귀적으로 dict를 업데이트하는 함수
def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            recursive_update(d[k], v)
        else:
            d[k] = v
    return 

# MCP
@mcp.tool()
def calc_geometry(jGear_py: dict) -> dict:
    """기어 치형의 기하학적 계산, 치형 계산 결과 반환"""
    """반환결과의 ["Geometry"] 키 값에 치형 계산 결과가 저장되며, 메타데이터는 내부 key값 앞에 $로 시작하는 키 값으로 저장됨"""    
    new = gear_data.copy()
    recursive_update(new, jGear_py)    
    jGear = JObject.Parse(json.dumps(new))

    form.LoadDataInput_Json(jGear)
    Result_Geo = form.CalcGeometry()

    Result_Geo_py = json.loads(Result_Geo.ToString())    # json -> dict
    return Result_Geo_py

@mcp.tool()
def calc_load_case(Result_Geo_py: dict) -> dict:
    """기어 강도평가, 효율, LTCA(Loaded Tooth Contact Analysis) 계산"""
    Result_Geo = JObject.Parse(json.dumps(Result_Geo_py))
    Result_Rating = form.CalcLoadCase(Result_Geo)

    Result_Rating_py = json.loads(Result_Rating.ToString())    # json -> dict
    return Result_Rating_py

@mcp.tool()
def calc_all(jGear_py: dict) -> dict:
    """기어 치형의 기하학적 계산, 기어 강도평가, 효율, LTCA(Loaded Tooth Contact Analysis) 계산"""
    Result_Geo_py = calc_geometry(jGear_py)
    Result_Rating_py = calc_load_case(Result_Geo_py)
    return Result_Rating_py

@mcp.tool()
def get_messages() -> dict:
    """정보, 경고, 오류 메시지 출력"""
    Result_Message = form.GetMessages()

    results = json.loads(Result_Message.ToString())    # json -> dict
    return results

@mcp.tool()
def clear_messages() -> dict:
    """메시지 초기화"""
    form.ClearMessages()
    return {"message": "메시지가 초기화되었습니다."}

if __name__ == "__main__":
    print("---- 시작 ----")
    jgear = edit_gear_data("모듈 3으로 바꿔줘")
    jgeo = calc_geometry(jgear)
    print("---- 종료 ----")
    print(jgear)
    mcp.run()


