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
def initialize() -> dict:
    """
    기어 설계를 위한 도구 및 데이터를 초기화합니다.
    
    이 함수는 기어 설계 시스템을 사용하기 위한 필수 초기화 작업을 수행합니다.
    초기화가 완료되면 다른 기어 관련 함수들을 사용할 수 있습니다.
    
    Returns:
        dict: 초기화 결과
            - 성공 시: {"success": True, "message": "초기화 완료"}
            - 실패 시: {"success": False, "error": "오류 메시지"}
            - 이미 초기화된 경우: {"success": True, "message": "이미 초기화됨"}
    
    Note:
        - 초기화 시 다음 전역 변수들이 설정됩니다:
          * isInitialized: 초기화 상태 플래그
          * default_data: 기본 기어 설계 데이터
          * changed_data: 사용자 변경사항이 적용될 데이터 (default_data의 복사본)
        - 이 함수는 다른 기어 관련 함수들을 사용하기 전에 반드시 호출되어야 합니다
        - 여러 번 호출해도 안전합니다 (중복 초기화 방지)
    
    Examples:
        >>> initialize()
        {"success": True, "message": "초기화 완료"}
        
        >>> initialize()  # 이미 초기화된 상태에서 재호출
        {"success": True, "message": "이미 초기화됨"}
    """
    global isInitialized, default_data, changed_data
    
    # 이미 초기화된 경우
    if isInitialized:
        return {
            "success": True, 
            "message": "이미 초기화됨",
            "status": "already_initialized"
        }
    
    try:
        # 기어 설계 폼 초기화
        if not GD.initialize_form():
            return {
                "success": False, 
                "error": "기어 설계 폼 초기화 실패"
            }
        
        # 기본 설정 데이터 로드
        default_data = GD.save_default_config()
        changed_data = default_data.copy()
        isInitialized = True
        
        return {
            "success": True, 
            "message": "초기화 완료",
            "status": "initialized"
        }
        
    except Exception as e:
        return {
            "success": False, 
            "error": f"초기화 중 오류 발생: {str(e)}"
        }
    
@mcp.tool()
def modify_gear_data(user_message: str) -> dict:
    """
    사용자 메시지를 기반으로 기어 데이터를 수정합니다.
    
    이 함수는 LLM을 사용하여 자연어 요청을 JSON 데이터 변경사항으로 변환하고,
    기존 기어 데이터에 적용한 후 검증합니다.
    
    Args:
        user_message (str): 기어 데이터 변경을 요청하는 자연어 메시지
        
    Returns:
        dict: 처리 결과
            - 성공 시: 변경된 데이터의 JSON 구조
            - 실패 시: {"error": "오류 메시지"}
    
    Note:
        - 사전에 초기화가 완료되어야 합니다 (isInitialized = True)
        - 매크로 기어 제원 변경 시 CDMethod가 자동으로 1로 설정됩니다
        - 변경사항은 전역 변수 changed_data에 적용됩니다
        - LLM 호출을 통해 자연어를 JSON 변경사항으로 변환합니다    
    """
    global isInitialized, default_data, changed_data
    
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
    # LLM 프롬프트 구성
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

    try:
        # LLM 호출하여 변경데이터 추출
        response = llm_call(prompt=prompt, model="gpt-5-mini")
        modified_data = remove_code_block_llm(response)
        modified_data = json.loads(modified_data)
        
        # 기존 데이터에 변경사항 적용
        recursive_update(changed_data, modified_data)
        
        # 데이터 검증 및 로드
        valid = GD.load_and_validate_config(changed_data)
        
        if valid:
            return {
                "success": True, 
                "message": "데이터 수정 및 검증 완료",
                "modified_data": modified_data
            }
        else:
            return {
                "success": False, 
                "message": "데이터 수정 및 검증 실패",
                "modified_data": modified_data
            }
        
    except json.JSONDecodeError as e:
        return {"error": f"JSON 파싱 오류: {str(e)}"}
    except Exception as e:
        return {"error": f"처리 중 오류 발생: {str(e)}"}

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
    """
    기어 치형의 기하학적 계산을 수행합니다.
    
    Returns:
        dict: 치형 계산 결과를 포함하는 딕셔너리
            - "Geometry": 치형 계산 결과 데이터
            - "$*": 메타데이터 (키 이름이 $로 시작)
            - "error": 초기화되지 않은 경우 오류 메시지
    
    Note:
        - 사전에 초기화가 완료되어야 합니다 (isInitialized = True)
        - 계산 결과는 전역 변수 GD_Results에도 저장됩니다
    """
    global isInitialized, GD_Results
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
    results = GD.calculate_geometry()
    GD_Results = results

    return results

@mcp.tool()
def get_geometry_results() -> dict:
    """
    기어 치형의 기하학적 계산 결과를 전달합니다.
    """
    global isInitialized, GD_Results

    # 초기화 상태 확인
    if not isInitialized:
        return {"error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요."}
    
    # 기하학적 계산 결과 확인
    if GD_Results is None:
        return {"error": "기하학적 계산이 먼저 수행되어야 합니다. calc_geometry() 함수를 먼저 호출하세요."}
    
    # GD_Results의 유효성 검증
    if not isinstance(GD_Results, dict) or "Geometry" not in GD_Results:
        return {"error": "유효하지 않은 기하학적 계산 결과입니다. calc_geometry()를 다시 실행하세요."}
    
    return GD_Results["Geometry"]


@mcp.tool()
def calc_load_case() -> dict:
    """
    기어 치형의 하중 계산을 수행합니다.
    
    기하학적 계산 결과를 바탕으로 기어의 하중 분석을 수행하고
    안전률, 응력 등의 하중 관련 데이터를 계산합니다.
    
    Returns:
        dict: 하중 계산 결과를 포함하는 딕셔너리
            - "Rating": 하중 계산 결과 데이터
            - "$*": 메타데이터 (키 이름이 $로 시작)
            - "error": 오류 발생 시 오류 메시지
    
    Note:
        - 사전에 초기화가 완료되어야 합니다 (initialize() 호출 필요)
        - 기하학적 계산이 먼저 수행되어야 합니다 (calc_geometry() 호출 필요)
        - GD_Results에 유효한 기하학적 계산 결과가 저장되어 있어야 합니다
    
    Raises:
        - 초기화되지 않은 경우
        - 기하학적 계산이 수행되지 않은 경우
        - 계산 중 오류 발생 시
    
    Examples:
        >>> # 정상적인 호출 순서
        >>> initialize()
        >>> calc_geometry()
        >>> calc_load_case()
    """
    global isInitialized, GD_Results
    
    # 초기화 상태 확인
    if not isInitialized:
        return {"error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요."}
    
    # 기하학적 계산 결과 확인
    if GD_Results is None:
        return {"error": "기하학적 계산이 먼저 수행되어야 합니다. calc_geometry() 함수를 먼저 호출하세요."}
    
    # GD_Results의 유효성 검증
    if not isinstance(GD_Results, dict) or "Geometry" not in GD_Results:
        return {"error": "유효하지 않은 기하학적 계산 결과입니다. calc_geometry()를 다시 실행하세요."}
    
    try:
        # 하중 계산 수행
        results = GD.calculate_load_case(GD_Results)
        
        # 결과 유효성 검증
        if not isinstance(results, dict):
            return {"error": "하중 계산 결과가 올바르지 않습니다."}
        
        return results
        
    except Exception as e:
        return {"error": f"하중 계산 중 오류 발생: {str(e)}"}

@mcp.tool()
def get_messages() -> dict:
    """
    계산 결과에 대한 실행 메시지를 반환합니다.
    
    기어 계산 과정에서 발생한 경고, 오류, 정보 메시지들을 가져옵니다.
    메시지를 반환한 후에는 내부 메시지 버퍼가 초기화됩니다.
    
    Returns:
        dict: 실행 메시지 정보
            - 성공 시: 메시지 데이터를 포함하는 딕셔너리
            - 실패 시: {"error": "오류 메시지"}
    
    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 이 함수 호출 후 메시지 버퍼는 자동으로 초기화됩니다
        - 계산 함수들(calc_geometry, calc_load_case) 실행 후 호출하는 것을 권장합니다
    """
    global isInitialized
    if not isInitialized:
        return {"error": "초기화되지 않음"}
    
    try:
        result_message = GD.get_messages()
        
        # None 체크
        if result_message is None:
            return {"messages": [], "info": "메시지가 없습니다"}
        
        # ToString() 메서드 존재 여부 확인
        if not hasattr(result_message, 'ToString'):
            return {"error": "메시지 객체가 올바르지 않습니다"}
        
        message_string = result_message.ToString()
        
        # 빈 문자열 체크
        if not message_string or message_string.strip() == "":
            return {"messages": [], "info": "메시지가 없습니다"}
        
        # JSON 파싱
        results = json.loads(message_string)
        return results
        
    except json.JSONDecodeError as e:
        return {"error": f"메시지 파싱 오류: {str(e)}"}
    except AttributeError as e:
        return {"error": f"메시지 객체 오류: {str(e)}"}
    except Exception as e:
        return {"error": f"메시지 조회 중 오류 발생: {str(e)}"}

@mcp.tool()
def get_gearimage() -> dict:
    """
    기어 이미지를 생성하고 파일로 저장합니다.
    
    현재 설계된 기어의 2D 이미지를 PNG 형식으로 생성하여 저장합니다.
    파일명은 타임스탬프를 포함하여 자동으로 생성됩니다.
    
    Returns:
        dict: 이미지 생성 결과
            - 성공 시: {"success": True, "path": "파일경로", "filename": "파일명"}
            - 실패 시: {"success": False, "error": "오류 메시지"}
    
    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 기하학적 계산이 먼저 수행되어야 합니다 (calc_geometry() 호출 필요)
        - 이미지는 스크립트와 같은 디렉토리에 저장됩니다
    """
    global isInitialized, GD_Results
    
    if not isInitialized:
        return {"success": False, "error": "초기화되지 않음"}
    
    if GD_Results is None:
        return {"success": False, "error": "기하학적 계산이 먼저 수행되어야 합니다"}
    
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_image_{timestamp}.png"
        output_file = os.path.join(os.path.dirname(__file__), filename)
        
        # 디렉토리 존재 확인 및 생성
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        getimage = GD.get_gearimage(output_file)
        
        if getimage:
            # 파일이 실제로 생성되었는지 확인
            if os.path.exists(output_file):
                return {
                    "success": True, 
                    "path": output_file,
                    "filename": filename,
                    "size": os.path.getsize(output_file)
                }
            else:
                return {"success": False, "error": "이미지 파일이 생성되지 않았습니다"}
        else:
            return {"success": False, "error": "이미지 추출 실패"}
            
    except Exception as e:
        return {"success": False, "error": f"이미지 생성 중 오류 발생: {str(e)}"}

@mcp.tool()
def get_gear_report() -> dict:  # 함수명 스네이크 케이스로 통일
    """
    기어 설계 보고서를 PDF 형식으로 생성합니다.
    
    기하학적 계산 및 하중 계산 결과를 바탕으로 상세한 기어 설계 보고서를
    PDF 형식으로 생성하여 저장합니다.
    
    Returns:
        dict: 보고서 생성 결과
            - 성공 시: {"success": True, "path": "파일경로", "filename": "파일명"}
            - 실패 시: {"success": False, "error": "오류 메시지"}
    
    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 기하학적 계산과 하중 계산이 모두 완료되어야 합니다
        - 보고서는 스크립트와 같은 디렉토리에 저장됩니다
    """
    global isInitialized, GD_Results
    
    if not isInitialized:
        return {"success": False, "error": "초기화되지 않음"}
    
    if GD_Results is None:
        return {"success": False, "error": "기하학적 계산이 먼저 수행되어야 합니다"}
    
    if "Rating" not in GD_Results:
        return {"success": False, "error": "하중 계산이 먼저 수행되어야 합니다. calc_load_case()를 호출하세요"}
    
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_report_{timestamp}.pdf"
        output_file = os.path.join(os.path.dirname(__file__), filename)
        
        # 디렉토리 존재 확인 및 생성
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        getreport = GD.get_gearReport(output_file, GD_Results["Rating"])
        
        if getreport:
            # 파일이 실제로 생성되었는지 확인
            if os.path.exists(output_file):
                return {
                    "success": True, 
                    "path": output_file,
                    "filename": filename,
                    "size": os.path.getsize(output_file)
                }
            else:
                return {"success": False, "error": "보고서 파일이 생성되지 않았습니다"}
        else:
            return {"success": False, "error": "기어 보고서 추출 실패"}
            
    except KeyError as e:
        return {"success": False, "error": f"필수 데이터 누락: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"보고서 생성 중 오류 발생: {str(e)}"}
    
if __name__ == "__main__":
    print("Starting MCP server...")
    asyncio.run(mcp.run())