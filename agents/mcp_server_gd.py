import os
import sys
from pathlib import Path
import datetime
import json
import asyncio

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from gear_design_manager import GearDesignManager
from utils import llm_call, remove_code_block_llm  # LLM 호출 함수 임포트

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("GearDesign_agent")

gear_design_path = r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"
GD = GearDesignManager(gear_design_path)

isInitialized = False
default_data = None
changed_data = None
GD_Results = None

@mcp.tool()
def initialize() -> bool:
    global isInitialized, default_data, changed_data
    if isInitialized:
        return True
    
    if not GD.initialize_form():
        return False    
    else:
        default_data = GD.save_default_config()
        isInitialized = True
        changed_data = default_data.copy()
        return True
    
@mcp.tool()
def modifiy_gear_data(user_message: str) -> dict:
    """사용자 메시지를 전달받아 기어 데이터로 전환하여 반환"""   
    global isInitialized, default_data, changed_data
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
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
        {"role": "user", "content": f"사용자 요청: {user_message}\n현재 데이터: {json.dumps(default_data, ensure_ascii=False)}"}
    ]

    # 3. LLM 호출 및 결과 검증 후 파싱
    try:
        # 변경데이터 추출
        response = llm_call(prompt=prompt, model="gpt-5-mini")
        modified_data = remove_code_block_llm(response)
        modified_data = json.loads(modified_data)
        # 데이터 변경
        recursive_update(changed_data, modified_data)
        # 데이터 검증 및 로드
        GD.load_and_validate_config(changed_data)

        return modified_data
    except Exception as e:
        return {"error": e}

# 재귀적으로 dict를 업데이트하는 함수
def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            recursive_update(d[k], v)
        else:
            d[k] = v
    return

@mcp.tool()
def calc_geometry():
    """기어 치형의 기하학적 계산, 치형 계산 결과 반환"""
    """반환결과의 ["Geometry"] 키 값에 치형 계산 결과가 저장되며, 메타데이터는 내부 key값 앞에 $로 시작하는 키 값으로 저장됨"""    
    global isInitialized, GD_Results
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
    results = GD.calculate_geometry()
    GD_Results = results.copy()

    return results

@mcp.tool()
def calc_load_case():
    """기어 치형의 하중 계산, 하중 계산 결과 반환"""
    """반환결과의 ["Rating"] 키 값에 하중 계산 결과가 저장되며, 메타데이터는 내부 key값 앞에 $로 시작하는 키 값으로 저장됨"""    

    global GD_Results
    if GD_Results is None:
        return {"error": "기하학적 계산이 먼저 수행되어야 합니다."}

    results = GD.calculate_load_case(GD_Results)
    
    return results

@mcp.tool()
def get_messages() -> dict:
    """계산결과에 대한 실행 메시지 (경고, 오류 포함), 실행 후 메시지는 초기화됨"""    
    global isInitialized
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
    Result_Message = GD.get_messages()
    results = json.loads(Result_Message.ToString())    # json -> dict

    return results

@mcp.tool()
def get_gearimage() -> dict:
    """기어 이미지 추출. 성공 시 true 반환"""
    global GD_Results
    if GD_Results is None:
        return {"error": "기하학적 계산이 먼저 수행되어야 합니다."}
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(os.path.dirname(__file__), f"gear_image_{timestamp}.png")
    getimage = GD.get_gearimage(output_file)
    if getimage:
        return {"success": True, "path": output_file}
    else:
        return {"success": False, "error": "이미지 추출 실패"}

@mcp.tool()
def get_gearReport() -> dict:
    """기어 보고서 추출. 성공 시 true 반환"""
    global GD_Results
    if GD_Results is None or "Rating" not in GD_Results:
        return {"error": "하중 계산이 먼저 수행되어야 합니다."}

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(os.path.dirname(__file__), f"gear_report_{timestamp}.pdf")
    getreport = GD.get_gearReport(output_file, GD_Results["Rating"])
    if getreport:
        return {"success": True, "path": output_file}
    else:
        return {"success": False, "error": "기어 보고서 추출 실패"}
    
if __name__ == "__main__":
    print("Starting MCP server...")
    asyncio.run(mcp.run())