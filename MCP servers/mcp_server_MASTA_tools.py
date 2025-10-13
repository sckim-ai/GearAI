# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import datetime
import json
import asyncio
import uuid
import threading
import time
import subprocess
from typing import Dict, Optional, Union, List
import math

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from langchain_experimental.utilities import PythonREPL
from mcp.server.fastmcp import FastMCP

# API Key 정보 로드
load_dotenv()

mcp = FastMCP("MASTA_Tools")

# MASTA 설정
masta_path: str = r"C:\Program Files\SMT\MASTA 14.1.1"
# MASTA Python API를 사용하는 경우 프로세스 경로 (선택사항)
masta_exe_path: Optional[str] = None  # MASTA가 별도 실행 파일을 제공하는 경우 설정


class MASTAIPC:
    """MASTA와 프로세스 간 통신(IPC)을 담당하는 클래스

    Note: MASTA는 Python API를 직접 제공하므로 subprocess 대신
    PythonREPL을 사용하여 Python 코드를 직접 실행합니다.
    향후 MASTA가 별도 IPC 프로세스를 지원하는 경우 이 클래스를 확장할 수 있습니다.
    """

    def __init__(self, masta_path: str, progress_callback=None):
        """
        Args:
            masta_path: MASTA 설치 경로
            progress_callback: 진행 상황 콜백 함수 (선택)
                               함수 시그니처: callback(message: str, percentage: int)
        """
        self.masta_path = Path(masta_path)
        self.python_repl = PythonREPL()
        self.progress_callback = progress_callback
        self.is_initialized = False

    def start(self) -> bool:
        """MASTA 환경 초기화"""
        if not self.masta_path.exists():
            print(f"오류: MASTA 설치 경로를 찾을 수 없습니다: {self.masta_path}")
            return False

        try:
            # MASTA 경로를 안전하게 처리
            safe_path = str(self.masta_path).replace('\\', '\\\\')

            # MASTA 초기화 코드 생성
            init_code = f"""
import math
import sys

# MASTA 모듈 임포트 시도
try:
    import Utility
    import mastapy
    from mastapy import init
    from mastapy.system_model import Design
    print("MASTA 모듈 임포트 성공")
except ImportError as e:
    print(f"MASTA 모듈 임포트 실패: {{e}}")
    print("MASTA가 설치되어 있는지 확인하세요.")
    raise

# MASTA 초기화
try:
    init(r"{safe_path}")
    print(f"MASTA 초기화 성공: {safe_path}")
except Exception as e:
    print(f"MASTA 초기화 실패: {{e}}")
    raise

# 단위 환산 상수 정의
MM = 1e-3
RAD = math.pi/180
RPM = 2*math.pi/60

print("단위 환산 상수 정의 완료 (MM, RAD, RPM)")
"""

            # 코드 실행
            result = self.python_repl.run(init_code)
            self.is_initialized = True
            print(f"MASTA IPC 초기화 완료\n{result}")
            return True

        except Exception as e:
            print(f"MASTA 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def execute_code(self, code: str) -> str:
        """Python 코드 실행"""
        if not self.is_initialized:
            raise RuntimeError("MASTA IPC가 초기화되지 않았습니다")

        try:
            result = self.python_repl.run(code)
            return f"Successfully executed!\n\nStdout: {result}"
        except Exception as e:
            return f"Failed to execute. Error: {repr(e)}"

    def stop(self):
        """리소스 정리 (필요시)"""
        if self.is_initialized:
            print("MASTA IPC 세션 종료")
            # 필요한 정리 작업 수행
            self.is_initialized = False

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.stop()

# 세션 데이터 클래스
class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_initialized = False
        self.design_name = "my_design"
        self.assembly_name = "assembly"
        self.ipc_client: Optional[MASTAIPC] = None  # IPC 클라이언트 통합
        self.created_at = datetime.datetime.now()
        self.last_accessed = datetime.datetime.now()

        # 생성된 객체 추적
        self.shafts = []
        self.gears = []
        self.bearings = []

        # 세션별 출력 폴더 경로
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs", session_id)
        self.images_dir = os.path.join(self.output_dir, "images")
        self.reports_dir = os.path.join(self.output_dir, "reports")
        self.modelings_dir = os.path.join(self.output_dir, "modelings")
        self.files = []

    def update_access_time(self):
        self.last_accessed = datetime.datetime.now()

    def create_output_directories(self):
        """세션별 출력 디렉토리 생성"""
        try:
            os.makedirs(self.images_dir, exist_ok=True)
            os.makedirs(self.reports_dir, exist_ok=True)
            os.makedirs(self.modelings_dir, exist_ok=True)
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

    def cleanup_ipc(self):
        """IPC 클라이언트 정리"""
        if self.ipc_client:
            try:
                self.ipc_client.stop()
                print(f"세션 {self.session_id} IPC 클라이언트 종료됨")
            except Exception as e:
                print(f"IPC 클라이언트 종료 중 오류: {str(e)}")

    def execute_python_code(self, code: str) -> str:
        """Python 코드 실행 (IPC 클라이언트를 통해)"""
        if not self.ipc_client:
            return "Failed to execute. Error: IPC client not initialized"

        try:
            return self.ipc_client.execute_code(code)
        except Exception as e:
            return f"Failed to execute. Error: {repr(e)}"

# 전역 세션 관리자
session_manager: Dict[str, SessionData] = {}
SESSION_TIMEOUT = 3600  # 1시간

def get_session(session_id: str) -> SessionData:
    """기존 세션 데이터를 가져옴"""
    if session_id not in session_manager:
        raise ValueError(f"세션 '{session_id}'를 찾을 수 없습니다. masta_initialize()를 먼저 호출하세요.")

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
        # IPC 클라이언트 정리
        session.cleanup_ipc()

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

# MCP 툴 함수들
@mcp.tool()
def masta_initialize() -> dict:
    """
    MASTA 환경을 초기화합니다.

    이 함수는 새로운 세션을 생성하고 MASTA Python API를 초기화합니다.
    초기화가 완료되면 반환된 session_id를 사용하여 다른 MASTA 관련 함수들을 호출할 수 있습니다.

    Returns:
        dict: 초기화 결과
            - success: 성공 여부 (bool)
            - session_id: 생성된 세션 ID (str)
            - message: 결과 메시지 (str)
            - design_name: Design 객체 이름 (str)
            - assembly_name: Assembly 객체 이름 (str)
            - output_directory: 출력 디렉토리 경로 (str)

    Note:
        - 매번 새로운 세션을 생성하므로 독립적인 작업 공간을 제공합니다
        - 반환된 session_id를 다른 모든 함수 호출에 사용해야 합니다
        - 이 함수는 MASTA 작업을 시작하는 첫 번째 함수입니다
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
        # 세션별 IPC 클라이언트 생성 및 시작
        session.ipc_client = MASTAIPC(masta_path)

        if not session.ipc_client.start():
            return {
                "success": False,
                "error": "MASTA IPC 클라이언트 시작 실패",
                "session_id": new_session_id
            }

        # 세션별 출력 디렉토리 생성
        if not session.create_output_directories():
            return {
                "success": False,
                "error": "출력 디렉토리 생성 실패",
                "session_id": new_session_id
            }

        # Design 및 Assembly 객체 생성 코드
        design_code = f"""
# 새로운 Design 작성
{session.design_name} = Design()
{session.assembly_name} = {session.design_name}.root_assembly

print(f"Design 객체 생성 완료: {session.design_name}")
print(f"Assembly 객체 생성 완료: {session.assembly_name}")
"""

        # 코드 실행
        execution_result = session.execute_python_code(design_code)
        session.is_initialized = True

        return {
            "success": True,
            "session_id": new_session_id,
            "message": f"새 세션({new_session_id[:8]})이 생성되고 초기화되었습니다",
            "execution_result": execution_result,
            "design_name": session.design_name,
            "assembly_name": session.assembly_name,
            "output_directory": session.output_dir,
            "status": "initialized"
        }

    except Exception as e:
        # 오류 발생 시 IPC 클라이언트 정리
        if session.ipc_client:
            session.ipc_client.stop()

        return {
            "success": False,
            "error": f"초기화 중 오류 발생: {str(e)}",
            "session_id": new_session_id
        }

@mcp.tool()
def create_shaft(
    session_id: str,
    shaft_name: str,
    length: float,
    outer_diameter: float,
    bore_diameter: float = 0.0,
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0
) -> dict:
    """
    축을 생성하고 배치합니다.

    Args:
        session_id (str): 세션 ID (masta_initialize()로 생성된 ID 필수)
        shaft_name (str): 축 이름 (Python 변수명 규칙 준수)
        length (float): 축 길이 (mm)
        outer_diameter (float): 축 외경 (mm)
        bore_diameter (float): 축 내경 (mm, 기본값: 0.0)
        position_x (float): X축 위치 (mm, 기본값: 0.0)
        position_y (float): Y축 위치 (mm, 기본값: 0.0)
        position_z (float): Z축 위치 (mm, 기본값: 0.0)

    Returns:
        dict: 축 생성 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - shaft_name: 생성된 축 이름 (str)
            - shaft_info: 축 정보 (dict)
            - execution_result: 실행 결과 (str)
            - total_shafts: 세션 내 전체 축 개수 (int)

    Note:
        - 사전에 masta_initialize()가 완료되어야 합니다
        - shaft_name은 유효한 Python 변수명이어야 합니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "success": False,
            "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
            "session_id": session_id
        }

    try:
        # 축 생성 코드
        shaft_code = f"""
# 축 생성: {shaft_name}
{shaft_name} = {session.assembly_name}.add_shaft(
    length={length}*MM,
    outer_diameter={outer_diameter}*MM,
    bore={bore_diameter}*MM
)

# 축 위치 설정
import mastapy._math.vector_3d as vector_3d
position = vector_3d.Vector3D({position_x}, {position_y}, {position_z}) * MM
{shaft_name}.set_position_of_component_and_connected_components(position)

print(f"축 '{shaft_name}' 생성 완료")
print(f"  - 길이: {length} mm")
print(f"  - 외경: {outer_diameter} mm")
print(f"  - 내경: {bore_diameter} mm")
print(f"  - 위치: ({position_x}, {position_y}, {position_z}) mm")
"""

        # 코드 실행
        execution_result = session.execute_python_code(shaft_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result:
            return {
                "success": False,
                "error": f"축 생성 실패: {execution_result}",
                "session_id": session_id
            }

        # 세션에 축 정보 저장
        shaft_info = {
            "name": shaft_name,
            "length": length,
            "outer_diameter": outer_diameter,
            "bore_diameter": bore_diameter,
            "position": [position_x, position_y, position_z]
        }
        session.shafts.append(shaft_info)

        return {
            "success": True,
            "session_id": session_id,
            "shaft_name": shaft_name,
            "shaft_info": shaft_info,
            "execution_result": execution_result,
            "total_shafts": len(session.shafts)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"축 생성 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def create_gear_pair(
    session_id: str,
    gear_pair_name: str,
    center_distance: float,
    pinion_teeth: int,
    wheel_teeth: int,
    normal_module: float,
    helix_angle: float = 0.0,
    pressure_angle: float = 20.0,
    pinion_face_width: float = 20.0,
    wheel_face_width: float = 20.0,
    addendum_factor: float = 1.0,
    dedendum_factor: float = 1.25,
    root_radius_factor: float = 0.3
) -> dict:
    """
    기어 쌍을 생성하고 설정합니다.

    Args:
        session_id (str): 세션 ID
        gear_pair_name (str): 기어 쌍 이름
        center_distance (float): 중심거리 (mm)
        pinion_teeth (int): 피니언 잇수
        wheel_teeth (int): 휠 잇수
        normal_module (float): 모듈 (mm)
        helix_angle (float): 헬리컬 각도 (도, 기본값: 0.0)
        pressure_angle (float): 압력각 (도, 기본값: 20.0)
        pinion_face_width (float): 피니언 치폭 (mm, 기본값: 20.0)
        wheel_face_width (float): 휠 치폭 (mm, 기본값: 20.0)
        addendum_factor (float): 치끝 계수 (기본값: 1.0)
        dedendum_factor (float): 치뿌리 계수 (기본값: 1.25)
        root_radius_factor (float): 치뿌리 반지름 계수 (기본값: 0.3)

    Returns:
        dict: 기어 쌍 생성 결과
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "success": False,
            "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
            "session_id": session_id
        }

    try:
        # 기어 쌍 생성 코드
        gear_code = f"""
# 기어 쌍 생성: {gear_pair_name}
{gear_pair_name} = {session.assembly_name}.add_cylindrical_gear_pair({center_distance}*MM)

# 기어 쌍 기본 제원 설정
{gear_pair_name}.active_gear_set_design.normal_module = {normal_module} * MM
{gear_pair_name}.active_gear_set_design.helix_angle = {helix_angle} * RAD
{gear_pair_name}.active_gear_set_design.normal_pressure_angle_maintain_transverse_profile = {pressure_angle} * RAD

# 피니언과 휠 기어 정의
pinion_{gear_pair_name} = {gear_pair_name}.active_gear_set_design.cylindrical_gears[0]
wheel_{gear_pair_name} = {gear_pair_name}.active_gear_set_design.cylindrical_gears[1]

# 잇수 설정
pinion_{gear_pair_name}.number_of_teeth = {pinion_teeth}
wheel_{gear_pair_name}.number_of_teeth = {wheel_teeth}

# 치폭 설정
pinion_{gear_pair_name}.face_width = {pinion_face_width} * MM
wheel_{gear_pair_name}.face_width = {wheel_face_width} * MM

# 피니언 기본 랙 프로파일 설정
pinion_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.basic_rack_addendum_factor = {addendum_factor}
pinion_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.basic_rack_dedendum_factor = {dedendum_factor}
pinion_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.both_flanks.edge_radius_factor = {root_radius_factor}

# 휠 기본 랙 프로파일 설정
wheel_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.basic_rack_addendum_factor = {addendum_factor}
wheel_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.basic_rack_dedendum_factor = {dedendum_factor}
wheel_{gear_pair_name}.cylindrical_gear_cutting_options.cylindrical_gear_cutter.both_flanks.edge_radius_factor = {root_radius_factor}

print(f"기어 쌍 '{gear_pair_name}' 생성 완료")
print(f"  - 중심거리: {center_distance} mm")
print(f"  - 피니언 잇수: {pinion_teeth}")
print(f"  - 휠 잇수: {wheel_teeth}")
print(f"  - 모듈: {normal_module} mm")
print(f"  - 헬리컬각: {helix_angle}°")
print(f"  - 압력각: {pressure_angle}°")
print(f"  - 기어비: {wheel_teeth/pinion_teeth:.2f}")
"""

        # 코드 실행
        execution_result = session.execute_python_code(gear_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result:
            return {
                "success": False,
                "error": f"기어 쌍 생성 실패: {execution_result}",
                "session_id": session_id
            }

        # 세션에 기어 정보 저장
        gear_info = {
            "name": gear_pair_name,
            "center_distance": center_distance,
            "pinion_teeth": pinion_teeth,
            "wheel_teeth": wheel_teeth,
            "normal_module": normal_module,
            "helix_angle": helix_angle,
            "pressure_angle": pressure_angle,
            "gear_ratio": wheel_teeth / pinion_teeth,
            "pinion_face_width": pinion_face_width,
            "wheel_face_width": wheel_face_width
        }
        session.gears.append(gear_info)

        return {
            "success": True,
            "session_id": session_id,
            "gear_pair_name": gear_pair_name,
            "gear_info": gear_info,
            "execution_result": execution_result,
            "total_gears": len(session.gears)
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
            "error": f"기어 쌍 생성 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def mount_gear_on_shaft(
    session_id: str,
    gear_pair_name: str,
    pinion_shaft_name: str,
    wheel_shaft_name: str,
    pinion_position: float,
    wheel_position: float
) -> dict:
    """
    기어를 축에 장착합니다.

    Args:
        session_id (str): 세션 ID
        gear_pair_name (str): 기어 쌍 이름
        pinion_shaft_name (str): 피니언이 장착될 축 이름
        wheel_shaft_name (str): 휠이 장착될 축 이름
        pinion_position (float): 피니언 장착 위치 (축 길이 방향, mm)
        wheel_position (float): 휠 장착 위치 (축 길이 방향, mm)

    Returns:
        dict: 기어 장착 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        # 기어 장착 코드
        mount_code = f"""
# 기어 장착: {gear_pair_name}
# 기어 쌍에서 피니언과 휠 참조
pinion_mount = {gear_pair_name}.cylindrical_gears[0]
wheel_mount = {gear_pair_name}.cylindrical_gears[1]

# 축에 기어 장착
{pinion_shaft_name}.mount_component(pinion_mount, {pinion_position}*MM)
{wheel_shaft_name}.mount_component(wheel_mount, {wheel_position}*MM)

print(f"기어 장착 완료:")
print(f"  - 피니언: {pinion_shaft_name}에 {pinion_position}mm 위치에 장착")
print(f"  - 휠: {wheel_shaft_name}에 {wheel_position}mm 위치에 장착")
"""

        # 코드 실행
        execution_result = session.execute_python_code(mount_code)

        return {
            "success": True,
            "session_id": session_id,
            "gear_pair_name": gear_pair_name,
            "mounting_info": {
                "pinion_shaft": pinion_shaft_name,
                "wheel_shaft": wheel_shaft_name,
                "pinion_position": pinion_position,
                "wheel_position": wheel_position
            },
            "execution_result": execution_result
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
            "error": f"기어 장착 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def create_bearing(
    session_id: str,
    bearing_name: str,
    shaft_name: str,
    position: float,
    bearing_designation: str = "6206"
) -> dict:
    """
    베어링을 생성하고 축에 장착합니다.

    Args:
        session_id (str): 세션 ID
        bearing_name (str): 베어링 이름
        shaft_name (str): 베어링이 장착될 축 이름
        position (float): 베어링 장착 위치 (축 길이 방향, mm)
        bearing_designation (str): 베어링 designation (기본값: "6206")

    Returns:
        dict: 베어링 생성 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        # 베어링 생성 코드
        bearing_code = f"""
# 베어링 생성: {bearing_name}
{bearing_name} = {session.assembly_name}.add_bearing("{bearing_name}")

# 베어링을 축에 장착
{shaft_name}.mount_component({bearing_name}, {position}*MM)

# 베어링 designation 설정
try:
    from mastapy.bearings import BearingCatalog
    {bearing_name}.set_detail_from_catalogue(BearingCatalog.SKF, "{bearing_designation}")
    print(f"베어링 designation '{bearing_designation}' 설정 완료")
except Exception as e:
    print(f"베어링 designation 설정 실패: {{e}}")
    print("기본 개념 베어링으로 설정됨")

print(f"베어링 '{bearing_name}' 생성 및 장착 완료")
print(f"  - 축: {shaft_name}")
print(f"  - 위치: {position} mm")
print(f"  - Designation: {bearing_designation}")
"""

        # 코드 실행
        execution_result = session.execute_python_code(bearing_code)

        # 세션에 베어링 정보 저장
        bearing_info = {
            "name": bearing_name,
            "shaft_name": shaft_name,
            "position": position,
            "designation": bearing_designation
        }
        session.bearings.append(bearing_info)

        return {
            "success": True,
            "session_id": session_id,
            "bearing_name": bearing_name,
            "bearing_info": bearing_info,
            "execution_result": execution_result,
            "total_bearings": len(session.bearings)
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
            "error": f"베어링 생성 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def show_model(session_id: str) -> dict:
    """
    생성된 MASTA 모델을 시각화합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 시각화 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        # 모델 시각화 코드
        show_code = f"""
# MASTA 모델 시각화
try:
    Utility.plot_images(assembly={session.assembly_name})
    print("모델 시각화 완료")
except Exception as e:
    print(f"시각화 중 오류: {{e}}")
"""

        # 코드 실행
        execution_result = session.execute_python_code(show_code)

        return {
            "success": True,
            "session_id": session_id,
            "message": "모델 시각화 완료",
            "execution_result": execution_result,
            "model_summary": {
                "shafts": len(session.shafts),
                "gears": len(session.gears),
                "bearings": len(session.bearings)
            }
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
            "error": f"모델 시각화 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def get_session_status(session_id: str) -> dict:
    """
    세션 상태 및 생성된 컴포넌트 정보를 조회합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 세션 상태 정보
    """
    try:
        session = get_session(session_id)

        return {
            "success": True,
            "session_id": session_id,
            "is_initialized": session.is_initialized,
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat(),
            "components": {
                "shafts": session.shafts,
                "gears": session.gears,
                "bearings": session.bearings
            },
            "component_count": {
                "shafts": len(session.shafts),
                "gears": len(session.gears),
                "bearings": len(session.bearings)
            },
            "design_name": session.design_name,
            "assembly_name": session.assembly_name
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

@mcp.tool()
def execute_custom_code(session_id: str, code: str) -> dict:
    """
    사용자 정의 MASTA Python 코드를 실행합니다.

    Args:
        session_id (str): 세션 ID
        code (str): 실행할 Python 코드

    Returns:
        dict: 코드 실행 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        # 코드 실행
        execution_result = session.execute_python_code(code)

        return {
            "success": True,
            "session_id": session_id,
            "execution_result": execution_result
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
            "error": f"코드 실행 중 오류: {str(e)}",
            "session_id": session_id
        }

# 세션 관리 툴들
@mcp.tool()
def get_active_sessions() -> dict:
    """
    현재 활성 세션들의 정보를 반환합니다.

    Returns:
        dict: 세션 정보
            - active_sessions: 활성 세션 수 (int)
            - sessions: 각 세션의 상세 정보 리스트 (list)
    """
    return get_session_info()

@mcp.tool()
def get_session_files(session_id: str) -> dict:
    """
    세션에서 생성된 파일 목록을 반환합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 파일 목록 정보
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - files: 파일 정보 리스트 (list)
            - file_count: 파일 개수 (int)
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
def cleanup_session(session_id: str) -> dict:
    """
    특정 세션을 정리합니다.

    세션과 함께 생성된 모든 파일들과 IPC 클라이언트도 정리됩니다.

    Args:
        session_id (str): 정리할 세션 ID

    Returns:
        dict: 정리 결과
            - success: 성공 여부 (bool)
            - message: 결과 메시지 (str)
    """
    if session_id in session_manager:
        session = session_manager[session_id]

        # IPC 클라이언트 정리
        session.cleanup_ipc()

        # 파일들 정리
        session.cleanup_files()

        # 세션 삭제
        del session_manager[session_id]

        return {
            "success": True,
            "message": f"세션 {session_id}와 관련 파일들이 정리되었습니다"
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
    print("Starting MASTA Tools MCP server...")
    print(f"세션 타임아웃: {SESSION_TIMEOUT}초")
    print("백그라운드 세션 정리 스레드 시작됨")

    print(masta_initialize())
    # mcp.run()