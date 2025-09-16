import os
import sys
from pathlib import Path
import datetime
import json
import asyncio
import uuid
import threading
import time
from typing import Dict, Optional

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from gear_design_manager import GearDesignManager
from utils import llm_call, remove_code_block_llm  # LLM 호출 함수 임포트

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("GearDesign_agent")

gear_design_path = r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"

# 세션 데이터 클래스
class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_initialized = False
        self.default_data = None
        self.changed_data = None
        self.gd_results = None  # Python dict (parsed JSON)
        self.gd_results_obj = None  # .NET 객체 (원본)
        self.gd_manager = None
        self.created_at = datetime.datetime.now()
        self.last_accessed = datetime.datetime.now()

        # 세션별 출력 폴더 경로
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs", session_id)
        self.images_dir = os.path.join(self.output_dir, "images")
        self.reports_dir = os.path.join(self.output_dir, "reports")
        self.files = []  # 생성된 파일 목록 추적

    def update_access_time(self):
        self.last_accessed = datetime.datetime.now()

    def create_output_directories(self):
        """세션별 출력 디렉토리 생성"""
        try:
            os.makedirs(self.images_dir, exist_ok=True)
            os.makedirs(self.reports_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"출력 디렉토리 생성 실패: {str(e)}")
            return False

    def add_file(self, file_path: str, file_type: str):
        """생성된 파일을 추적 목록에 추가"""
        self.files.append({
            "path": file_path,
            "type": file_type,
            "created_at": datetime.datetime.now().isoformat()
        })

    def cleanup_files(self):
        """세션 종료 시 생성된 파일들 정리"""
        import shutil
        try:
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)
                print(f"세션 {self.session_id} 파일들이 정리되었습니다")
        except Exception as e:
            print(f"파일 정리 중 오류: {str(e)}")

# 전역 세션 관리자
session_manager: Dict[str, SessionData] = {}
SESSION_TIMEOUT = 3600  # 1시간


# 세션 관리 함수들
def get_session(session_id: str) -> SessionData:
    """기존 세션 데이터를 가져옴 (존재하지 않으면 오류)"""
    if session_id not in session_manager:
        raise ValueError(f"세션 '{session_id}'를 찾을 수 없습니다. initialize()을 먼저 호출하세요.")

    session = session_manager[session_id]
    session.update_access_time()
    return session

def create_new_session(session_id: str) -> SessionData:
    """새로운 세션을 생성"""
    if session_id in session_manager:
        raise ValueError(f"세션 '{session_id}'가 이미 존재합니다.")

    session = SessionData(session_id)
    session_manager[session_id] = session
    return session

def cleanup_expired_sessions():
    """만료된 세션 정리"""
    current_time = datetime.datetime.now()
    expired_sessions = []

    for session_id, session in session_manager.items():
        if (current_time - session.last_accessed).seconds > SESSION_TIMEOUT:
            expired_sessions.append((session_id, session))

    for session_id, session in expired_sessions:
        # 파일들 정리
        session.cleanup_files()

        # 세션 삭제
        del session_manager[session_id]
        print(f"세션 만료로 정리됨: {session_id}")

def get_session_info() -> dict:
    """현재 활성 세션 정보 반환"""
    return {
        "active_sessions": len(session_manager),
        "sessions": [
            {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "is_initialized": session.is_initialized
            }
            for session in session_manager.values()
        ]
    }


@mcp.tool()
def initialize() -> dict:
    """
    기어 설계를 위한 도구 및 데이터를 초기화합니다.

    이 함수는 새로운 세션을 자동으로 생성하고 기어 설계 시스템을 초기화합니다.
    초기화가 완료되면 반환된 session_id를 사용하여 다른 기어 관련 함수들을 호출할 수 있습니다.

    Returns:
        dict: 초기화 결과
            - 성공 시: {"success": True, "message": "초기화 완료", "session_id": "새로생성된세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지"}

    Note:
        - 매번 새로운 세션을 생성하므로 독립적인 작업 공간을 제공합니다
        - 반환된 session_id를 다른 모든 함수 호출에 사용해야 합니다
        - 이 함수는 기어 설계 작업을 시작하는 첫 번째 함수입니다

    Examples:
        >>> # 초기화하면 자동으로 새 세션 생성
        >>> result = initialize()
        >>> session_id = result["session_id"]
        >>>
        >>> # 반환된 session_id로 다른 함수들 호출
        >>> modify_gear_data("모듈을 2로 변경", session_id)
        >>> calc_geometry(session_id)
    """
    # 새로운 세션 자동 생성
    new_session_id = str(uuid.uuid4())

    try:
        session = create_new_session(new_session_id)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": new_session_id
        }

    try:
        # 세션별 GearDesignManager 인스턴스 생성
        session.gd_manager = GearDesignManager(gear_design_path)

        # 기어 설계 폼 초기화
        if not session.gd_manager.initialize_form():
            return {
                "success": False,
                "error": "기어 설계 폼 초기화 실패",
                "session_id": new_session_id
            }

        # 기본 설정 데이터 로드
        session.default_data = session.gd_manager.save_default_config()
        session.changed_data = session.default_data.copy()

        # 세션별 출력 디렉토리 생성
        if not session.create_output_directories():
            return {
                "success": False,
                "error": "출력 디렉토리 생성 실패",
                "session_id": new_session_id
            }

        session.is_initialized = True

        return {
            "success": True,
            "message": f"새 세션({new_session_id[:8]})이 생성되고 초기화되었습니다",
            "session_id": new_session_id,
            "output_directory": session.output_dir,
            "status": "initialized"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"초기화 중 오류 발생: {str(e)}",
            "session_id": new_session_id
        }


@mcp.tool()
def modify_gear_data(user_message: str, session_id: str) -> dict:
    """
    사용자 메시지를 기반으로 기어 데이터를 수정합니다.

    이 함수는 LLM을 사용하여 자연어 요청을 JSON 데이터 변경사항으로 변환하고,
    기존 기어 데이터에 적용한 후 검증합니다.

    Args:
        user_message (str): 기어 데이터 변경을 요청하는 자연어 메시지
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 처리 결과
            - 성공 시: 변경된 데이터의 JSON 구조와 세션 정보
            - 실패 시: {"error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 매크로 기어 제원 변경 시 CDMethod가 자동으로 1로 설정됩니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

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
        {"role": "user", "content": f"사용자 요청: {user_message}\n현재 데이터: {json.dumps(session.default_data, ensure_ascii=False)}"}
    ]

    try:
        # LLM 호출하여 변경데이터 추출
        response = llm_call(prompt=prompt, model="gpt-5-mini")
        modified_data = remove_code_block_llm(response)
        modified_data = json.loads(modified_data)

        # 기존 데이터에 변경사항 적용
        recursive_update(session.changed_data, modified_data)

        # 데이터 검증 및 로드
        valid = session.gd_manager.load_and_validate_config(session.changed_data)

        if valid:
            return {
                "success": True,
                "message": "데이터 수정 및 검증 완료",
                "modified_data": modified_data,
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "message": "데이터 수정 및 검증 실패",
                "modified_data": modified_data,
                "session_id": session.session_id
            }

    except json.JSONDecodeError as e:
        return {
            "error": f"JSON 파싱 오류: {str(e)}",
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "error": f"처리 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

# 재귀적으로 dict를 업데이트하는 함수
def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            recursive_update(d[k], v)
        else:
            d[k] = v
    return

@mcp.tool()
def calc_geometry(session_id: str) -> dict:
    """
    기어 치형의 기하학적 계산을 수행합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 치형 계산 결과를 포함하는 딕셔너리
            - "Geometry": 치형 계산 결과 데이터
            - "$*": 메타데이터 (키 이름이 $로 시작)
            - "session_id": 세션 ID
            - "error": 초기화되지 않은 경우 오류 메시지

    Note:
        - 사전에 초기화가 완료되어야 합니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    try:
        results_obj = session.gd_manager.calculate_geometry()

        # .NET 객체를 JSON 문자열로 변환 후 Python dict로 파싱
        results_json = results_obj.ToString()
        results = json.loads(results_json)

        # 원본 객체와 파싱된 dict 둘 다 저장
        session.gd_results_obj = results_obj  # .NET 객체 (calculate_load_case용)
        session.gd_results = results  # Python dict (일반 사용)

        # 결과에 세션 ID 추가
        if isinstance(results, dict):
            results["session_id"] = session.session_id

        return results

    except Exception as e:
        return {
            "error": f"기하학적 계산 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_geometry_results(session_id: str) -> dict:
    """
    기어 치형의 기하학적 계산 결과를 전달합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    # 초기화 상태 확인
    if not session.is_initialized:
        return {
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    # 기하학적 계산 결과 확인
    if session.gd_results is None:
        return {
            "error": "기하학적 계산이 먼저 수행되어야 합니다. calc_geometry() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    # gd_results의 유효성 검증
    if not isinstance(session.gd_results, dict) or "Geometry" not in session.gd_results:
        return {
            "error": "유효하지 않은 기하학적 계산 결과입니다. calc_geometry()를 다시 실행하세요.",
            "session_id": session.session_id
        }

    result = session.gd_results["Geometry"].copy()
    result["session_id"] = session.session_id
    return result


@mcp.tool()
def calc_load_case(session_id: str) -> dict:
    """
    기어 치형의 하중 계산을 수행하고 계산 메시지를 반환합니다.

    기하학적 계산 결과를 바탕으로 기어의 하중 분석을 수행하고
    안전률, 응력 등을 계산한 후 계산 과정에서 발생한 메시지를 반환합니다.
    계산 결과 데이터는 세션에 저장됩니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 하중 계산 메시지
            - "success": True (성공 시)
            - "message": "하중 계산이 완료되었습니다"
            - 계산 과정에서 발생한 메시지들 (경고, 정보 등)
            - "session_id": 세션 ID
            - "error": 오류 발생 시 오류 메시지

    Note:
        - 사전에 초기화와 기하학적 계산이 완료되어야 합니다
        - 계산 결과 데이터는 세션에 저장되어 get_gear_report() 등에서 사용됩니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    # 초기화 상태 확인
    if not session.is_initialized:
        return {
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    # 기하학적 계산 결과 확인
    if session.gd_results_obj is None:
        return {
            "error": "기하학적 계산이 먼저 수행되어야 합니다. calc_geometry() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    # gd_results의 유효성 검증 (Python dict 사용)
    if not isinstance(session.gd_results, dict) or "Geometry" not in session.gd_results:
        return {
            "error": "유효하지 않은 기하학적 계산 결과입니다. calc_geometry()를 다시 실행하세요.",
            "session_id": session.session_id
        }

    try:
        # 하중 계산 수행 (.NET 객체 사용)
        results_obj = session.gd_manager.calculate_load_case(session.gd_results_obj)

        # .NET 객체를 Python dict로 변환하여 세션에 저장
        results_json = results_obj.ToString()
        results = json.loads(results_json)

        # 결과 유효성 검증
        if not isinstance(results, dict):
            return {
                "error": "하중 계산 결과가 올바르지 않습니다.",
                "session_id": session.session_id
            }

        # 세션의 gd_results에 Rating 정보 추가 (전체 결과로 업데이트)
        session.gd_results = results

        messages = {}
        messages["success"] = True
        messages["message"] = "하중 계산이 완료되었습니다."
        messages["session_id"] = session.session_id

        return messages

    except Exception as e:
        return {
            "error": f"하중 계산 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_messages(session_id: str) -> dict:
    """
    계산 결과에 대한 실행 메시지를 반환합니다.

    기어 계산 과정에서 발생한 경고, 오류, 정보 메시지들을 가져옵니다.
    메시지를 반환한 후에는 내부 메시지 버퍼가 초기화됩니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 실행 메시지 정보
            - 성공 시: 메시지 데이터를 포함하는 딕셔너리
            - 실패 시: {"error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 호출 후 메시지 버퍼는 자동으로 초기화됩니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    try:
        result_message = session.gd_manager.get_messages()

        # None 체크
        if result_message is None:
            return {
                "messages": [],
                "info": "메시지가 없습니다",
                "session_id": session.session_id
            }

        # ToString() 메서드 존재 여부 확인
        if not hasattr(result_message, 'ToString'):
            return {
                "error": "메시지 객체가 올바르지 않습니다",
                "session_id": session.session_id
            }

        message_string = result_message.ToString()

        # 빈 문자열 체크
        if not message_string or message_string.strip() == "":
            return {
                "messages": [],
                "info": "메시지가 없습니다",
                "session_id": session.session_id
            }

        # JSON 파싱
        results = json.loads(message_string)
        results["session_id"] = session.session_id
        return results

    except json.JSONDecodeError as e:
        return {
            "error": f"메시지 파싱 오류: {str(e)}",
            "session_id": session.session_id
        }
    except AttributeError as e:
        return {
            "error": f"메시지 객체 오류: {str(e)}",
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "error": f"메시지 조회 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_gearimage(session_id: str) -> dict:
    """
    기어 이미지를 생성하고 파일로 저장합니다.

    현재 설계된 기어의 2D 이미지를 PNG 형식으로 생성하여 저장합니다.
    파일명은 타임스탬프를 포함하여 자동으로 생성됩니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 이미지 생성 결과
            - 성공 시: {"success": True, "path": "파일경로", "filename": "파일명", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화와 기하학적 계산이 완료되어야 합니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "success": False,
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    if session.gd_results is None:
        return {
            "success": False,
            "error": "기하학적 계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_image_{timestamp}.png"
        output_file = os.path.join(session.images_dir, filename)

        getimage = session.gd_manager.get_gearimage(output_file)

        if getimage:
            # 파일이 실제로 생성되었는지 확인
            if os.path.exists(output_file):
                # 생성된 파일을 세션에 추가
                session.add_file(output_file, "image")

                return {
                    "success": True,
                    "path": output_file,
                    "filename": filename,
                    "size": os.path.getsize(output_file),
                    "session_id": session.session_id,
                    "relative_path": f"outputs/{session.session_id}/images/{filename}"
                }
            else:
                return {
                    "success": False,
                    "error": "이미지 파일이 생성되지 않았습니다",
                    "session_id": session.session_id
                }
        else:
            return {
                "success": False,
                "error": "이미지 추출 실패",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"이미지 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_allresults_summary(session_id: str) -> dict:
    """
    모든 계산 결과의 요약 정보를 반환합니다.

    현재 세션에 저장된 기하학적 계산 및 하중 계산 결과를 바탕으로
    요약된 결과 정보를 추출하여 반환합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 요약 정보
            - 성공 시: 요약된 결과 데이터와 세션 정보
            - 실패 시: {"error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화와 기하학적 계산이 완료되어야 합니다
        - 하중 계산이 수행되지 않은 경우에도 기하학적 계산 결과는 포함됩니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    if session.gd_results is None:
        return {
            "error": "기하학적 계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        summary = session.gd_manager.get_allresults_summary(session.gd_results_obj)
        summary["session_id"] = session.session_id
        return summary

    except KeyError as e:
        return {
            "error": f"필수 데이터 누락: {str(e)}",
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "error": f"요약 정보 추출 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_gear_report(session_id: str) -> dict:
    """
    기어 설계 보고서를 PDF 형식으로 생성합니다.

    기하학적 계산 및 하중 계산 결과를 바탕으로 상세한 기어 설계 보고서를
    PDF 형식으로 생성하여 저장합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 보고서 생성 결과
            - 성공 시: {"success": True, "path": "파일경로", "filename": "파일명", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화, 기하학적 계산, 하중 계산이 모두 완료되어야 합니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "success": False,
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    if session.gd_results is None:
        return {
            "success": False,
            "error": "기하학적 계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    if "LC" not in session.gd_results:
        return {
            "success": False,
            "error": "하중 계산이 먼저 수행되어야 합니다. calc_load_case()를 호출하세요",
            "session_id": session.session_id
        }

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_report_{timestamp}.pdf"
        output_file = os.path.join(session.reports_dir, filename)

        getreport = session.gd_manager.get_gearReport(output_file, session.gd_results_obj)

        if getreport:
            # 파일이 실제로 생성되었는지 확인
            if os.path.exists(output_file):
                # 생성된 파일을 세션에 추가
                session.add_file(output_file, "report")

                return {
                    "success": True,
                    "path": output_file,
                    "filename": filename,
                    "size": os.path.getsize(output_file),
                    "session_id": session.session_id,
                    "relative_path": f"outputs/{session.session_id}/reports/{filename}"
                }
            else:
                return {
                    "success": False,
                    "error": "보고서 파일이 생성되지 않았습니다",
                    "session_id": session.session_id
                }
        else:
            return {
                "success": False,
                "error": "기어 보고서 추출 실패",
                "session_id": session.session_id
            }

    except KeyError as e:
        return {
            "success": False,
            "error": f"필수 데이터 누락: {str(e)}",
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"보고서 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

# 세션 관리 관련 MCP 툴 추가
@mcp.tool()
def get_active_sessions() -> dict:
    """
    현재 활성 세션들의 정보를 반환합니다.

    Returns:
        dict: 세션 정보
            - active_sessions: 활성 세션 수
            - sessions: 각 세션의 상세 정보 리스트
    """
    return get_session_info()

@mcp.tool()
def cleanup_sessions() -> dict:
    """
    만료된 세션들을 정리합니다.

    Returns:
        dict: 정리 결과
            - cleaned_sessions: 정리된 세션 수
            - remaining_sessions: 남은 세션 수
    """
    before_count = len(session_manager)
    cleanup_expired_sessions()
    after_count = len(session_manager)
    cleaned_count = before_count - after_count

    return {
        "cleaned_sessions": cleaned_count,
        "remaining_sessions": after_count,
        "message": f"{cleaned_count}개의 만료된 세션이 정리되었습니다"
    }

@mcp.tool()
def get_session_files(session_id: str) -> dict:
    """
    세션에서 생성된 파일 목록을 반환합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 파일 목록 정보
    """
    try:
        session = get_session(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "files": session.files,
            "file_count": len(session.files)
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

@mcp.tool()
def get_file_content(session_id: str, filename: str) -> dict:
    """
    세션의 파일 내용을 base64로 인코딩하여 반환합니다.

    Args:
        session_id (str): 세션 ID
        filename (str): 파일명

    Returns:
        dict: 파일 내용 (base64 인코딩)
    """
    try:
        session = get_session(session_id)

        # 파일 찾기
        target_file = None
        for file_info in session.files:
            if os.path.basename(file_info["path"]) == filename:
                target_file = file_info["path"]
                break

        if target_file is None:
            return {
                "success": False,
                "error": f"파일 '{filename}'을 찾을 수 없습니다",
                "session_id": session_id
            }

        if not os.path.exists(target_file):
            return {
                "success": False,
                "error": f"파일 '{filename}'이 존재하지 않습니다",
                "session_id": session_id
            }

        # 파일을 base64로 인코딩
        import base64
        with open(target_file, "rb") as f:
            file_content = base64.b64encode(f.read()).decode('utf-8')

        return {
            "success": True,
            "filename": filename,
            "content": file_content,
            "size": os.path.getsize(target_file),
            "session_id": session_id
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"파일 읽기 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def delete_session(session_id: str) -> dict:
    """
    특정 세션을 강제로 삭제합니다.

    세션과 함께 생성된 모든 파일들도 삭제됩니다.

    Args:
        session_id (str): 삭제할 세션 ID

    Returns:
        dict: 삭제 결과
    """
    if session_id in session_manager:
        session = session_manager[session_id]

        # 파일들 정리
        session.cleanup_files()

        # 세션 삭제
        del session_manager[session_id]

        return {
            "success": True,
            "message": f"세션 {session_id}와 관련 파일들이 삭제되었습니다"
        }
    else:
        return {
            "success": False,
            "error": f"세션 {session_id}를 찾을 수 없습니다"
        }

# 주기적 세션 정리를 위한 백그라운드 스레드
def periodic_cleanup():
    """주기적으로 만료된 세션을 정리하는 함수"""
    while True:
        time.sleep(300)  # 5분마다 실행
        try:
            cleanup_expired_sessions()
        except Exception as e:
            print(f"세션 정리 중 오류 발생: {str(e)}")

# 백그라운드 정리 스레드 시작
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    print("Starting MCP server...")
    print(f"세션 타임아웃: {SESSION_TIMEOUT}초")
    print("백그라운드 세션 정리 스레드 시작됨")
    asyncio.run(mcp.run())