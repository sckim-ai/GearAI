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
import base64

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from langchain_experimental.utilities import PythonREPL
from mcp.server.fastmcp import FastMCP

# API Key 정보 로드
load_dotenv()

mcp = FastMCP("MASTA_Tools")

# ============================================================================
# Utility 함수들 (원래 Utility.py의 기능)
# ============================================================================

def calculate_normal_module(Centerdistance: float, z1: int, z2: int, beta: float) -> float:
    """
    중심거리, 잇수, 헬리컬 각도로부터 노멀 모듈을 계산합니다.

    Args:
        Centerdistance: 중심거리 (mm)
        z1: 피니언 잇수
        z2: 휠 잇수
        beta: 헬리컬 각도 (도)

    Returns:
        float: 노멀 모듈 (mm)
    """
    total_teeth = z1 + z2
    helix_angle_rad = math.radians(beta)  # 헬리컬 각도를 라디안으로 변환
    normal_module = (2 * Centerdistance * math.cos(helix_angle_rad)) / total_teeth
    return normal_module


def get_nearest_bearing_code(inner_diameter: float) -> str:
    """
    내경에 가장 가까운 62xx 시리즈 베어링 형번을 반환합니다.

    Args:
        inner_diameter: 베어링 내경 (mm)

    Returns:
        str: 베어링 형번 (예: "6206")
    """
    # 내경별 62xx 시리즈 형번 매핑 (최대 100mm까지)
    bearing_codes = {
        10: "6200", 12: "6201", 15: "6202", 17: "6203", 20: "6204",
        25: "6205", 30: "6206", 35: "6207", 40: "6208", 45: "6209",
        50: "6210", 55: "6211", 60: "6212", 65: "6213", 70: "6214",
        75: "6215", 80: "6216", 85: "6217", 90: "6218", 95: "6219",
        100: "6220"
    }

    # 정확히 매칭되는 형번이 있는지 확인
    if inner_diameter in bearing_codes:
        return bearing_codes[inner_diameter]

    # 매칭이 없는 경우 가장 가까운 내경을 찾아 형번 반환
    nearest_diameter = min(bearing_codes.keys(), key=lambda x: abs(x - inner_diameter))
    return bearing_codes[nearest_diameter]


def generate_plot_code(assembly_name: str, output_path: str) -> str:
    """
    MASTA 어셈블리의 3D 뷰를 matplotlib으로 플롯하는 Python 코드를 생성합니다.

    Args:
        assembly_name: 어셈블리 변수 이름
        output_path: 이미지 저장 경로

    Returns:
        str: 실행할 Python 코드
    """
    return f"""
import matplotlib.pyplot as plt

# MASTA 모델 3D 뷰 시각화
plt.figure(figsize=(12, 12))

# 3개의 서브플롯 생성
plt.subplot(1, 3, 1)
plt.imshow({assembly_name}.three_d_isometric_view)
plt.title('Isometric View')
plt.axis('off')

plt.subplot(1, 3, 2)
plt.imshow({assembly_name}.three_d_view_orientated_in_xz_plane_with_y_axis_pointing_into_the_screen)
plt.title('XZ Plane View')
plt.axis('off')

plt.subplot(1, 3, 3)
plt.imshow({assembly_name}.three_d_view_orientated_in_xy_plane_with_z_axis_pointing_into_the_screen)
plt.title('XY Plane View')
plt.axis('off')

plt.tight_layout()

# 이미지 저장
plt.savefig(r'{output_path}', dpi=150, bbox_inches='tight')
print(f"모델 시각화 이미지 저장 완료: {output_path}")
plt.close()
"""

# ============================================================================

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

    def start(self) -> tuple[bool, str]:
        """MASTA 환경 초기화

        Returns:
            tuple[bool, str]: (성공 여부, 실행 결과 메시지)
        """
        if not self.masta_path.exists():
            error_msg = f"오류: MASTA 설치 경로를 찾을 수 없습니다: {self.masta_path}"
            print(error_msg)
            return False, error_msg

        try:
            # MASTA 경로를 안전하게 처리
            safe_path = str(self.masta_path).replace('\\', '\\\\')

            # MASTA 초기화 코드 생성
            init_code = f"""
# MASTA 모듈 임포트 시도
import mastapy as mp
import math

mp.init(r'C:\Program Files\SMT\MASTA 14.1.1')
print("✓ MASTA 초기화 완료")

# 단위 환산 상수 정의
MM = 1e-3
RAD = math.pi/180
RPM = 2*math.pi/60
print("✓ 단위 환산 상수 정의 완료 (MM, RAD, RPM)")
print("✓ MASTA IPC 준비 완료")
"""

            # 코드 실행
            result = self.python_repl.run(init_code)

            # 실행 결과 확인 (오류 메시지가 포함되어 있는지 체크)
            if result and any(keyword in result.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '✗']):
                return False, error_msg

            # 성공 시에만 initialized 플래그 설정
            self.is_initialized = True
            return True, result if result else "초기화 완료"

        except Exception as e:
            error_msg = f"MASTA 초기화 실패: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg

    def execute_code(self, code: str) -> str:
        """Python 코드 실행

        Returns:
            str: 실행 결과 (성공 시 "Successfully executed!" 포함, 실패 시 "Failed to execute" 포함)
        """
        if not self.is_initialized:
            raise RuntimeError("MASTA IPC가 초기화되지 않았습니다")

        try:
            result = self.python_repl.run(code)

            # 실행 결과에 오류가 포함되어 있는지 확인
            if result and any(keyword in result.lower() for keyword in ['error', 'exception', 'traceback', 'failed']):
                return f"Failed to execute. Error detected in output:\n{result}"

            return f"Successfully executed!\n\nStdout: {result if result else '(no output)'}"
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

def _save_model_snapshot(session: SessionData, action_name: str) -> dict:
    """
    모델의 현재 상태를 이미지로 저장하는 내부 헬퍼 함수

    Args:
        session: SessionData 객체
        action_name: 작업 이름 (예: "after_create_shaft", "after_update_gear")

    Returns:
        dict: 저장 결과 (success, image_path 등)
    """
    try:
        # 이미지 저장 경로 생성 (밀리초 포함으로 순서 명확화)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 밀리초까지 포함
        image_filename = f"{timestamp}_{action_name}.png"
        image_path = os.path.join(session.images_dir, image_filename)

        # 경로를 안전하게 처리 (백슬래시 이스케이프)
        safe_image_path = image_path.replace('\\', '\\\\')

        # 모델 시각화 코드 생성 및 실행
        show_code = generate_plot_code(session.assembly_name, safe_image_path)
        execution_result = session.execute_python_code(show_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result:
            return {
                "success": False,
                "error": f"스냅샷 저장 실패: {execution_result}"
            }

        # 파일 추적 목록에 추가
        session.add_file(image_path, "image")

        return {
            "success": True,
            "image_path": image_path,
            "action_name": action_name
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"스냅샷 저장 중 오류: {str(e)}"
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

        start_success, start_message = session.ipc_client.start()
        if not start_success:
            return {
                "success": False,
                "error": f"MASTA IPC 클라이언트 시작 실패: {start_message}",
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
from mastapy.system_model import Design

{session.design_name} = Design()
{session.assembly_name} = {session.design_name}.root_assembly

print(f"Design 객체 생성 완료: {session.design_name}")
print(f"Assembly 객체 생성 완료: {session.assembly_name}")
"""

        # 코드 실행
        execution_result = session.execute_python_code(design_code)

        # 실행 결과 확인 (오류 메시지가 포함되어 있는지 체크)
        if execution_result and any(keyword in execution_result.lower() for keyword in ['error', 'exception', 'traceback', 'failed', '✗']):
            return {
                "success": False,
                "error": f"Design 객체 생성 실패: {execution_result}",
                "session_id": new_session_id
            }

        session.is_initialized = True

        # 초기화 메시지 결합
        full_init_message = f"""
=== MASTA 초기화 결과 ===
{start_message}

=== Design 객체 생성 결과 ===
{execution_result}
"""

        return {
            "success": True,
            "session_id": new_session_id,
            "message": f"새 세션({new_session_id[:8]})이 생성되고 초기화되었습니다",
            "execution_result": full_init_message.strip(),
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
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0
) -> dict:
    """
    축을 생성하고 배치합니다.

    Args:
        session_id (str): 세션 ID (masta_initialize()로 생성된 ID 필수)
        shaft_name (str): 축 표시 이름 (editable_name으로 설정)
        length (float): 축 길이 (mm)
        position_x (float): X축 위치 (mm, 기본값: 0.0)
        position_y (float): Y축 위치 (mm, 기본값: 0.0)
        position_z (float): Z축 위치 (mm, 기본값: 0.0)

    Returns:
        dict: 축 생성 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - shaft_name: 생성된 축 이름 (str)
            - shaft_variable: Python 변수명 (str)
            - shaft_info: 축 정보 (dict)
            - execution_result: 실행 결과 (str)
            - total_shafts: 세션 내 전체 축 개수 (int)

    Note:
        - 사전에 masta_initialize()가 완료되어야 합니다
        - 축의 외경/내경은 이후 설정 가능합니다
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
        # Python 변수명 생성 (공백, 특수문자 제거)
        shaft_variable = f"shaft_{len(session.shafts) + 1}"

        # 축 생성 코드 (test.ipynb 패턴 참조)
        shaft_code = f"""
# 축 생성: {shaft_name}
{shaft_variable} = {session.assembly_name}.add_shaft({length}*MM)

# 축 이름 설정
{shaft_variable}.editable_name = "{shaft_name}"

# 축 위치 설정 (Vector3D 사용)
from mastapy._private._math.vector_3d import Vector3D
desired_position = Vector3D({position_x}, {position_y}, {position_z}) * MM
{shaft_variable}.set_position_of_component_and_connected_components(desired_position)

print(f"축 '{shaft_name}' 생성 완료")
print(f"  - 변수명: {shaft_variable}")
print(f"  - 길이: {length} mm")
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
            "variable": shaft_variable,
            "length": length,
            "position": [position_x, position_y, position_z]
        }
        session.shafts.append(shaft_info)

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"create_shaft_{shaft_name}")

        return {
            "success": True,
            "session_id": session_id,
            "shaft_name": shaft_name,
            "shaft_variable": shaft_variable,
            "shaft_info": shaft_info,
            "execution_result": execution_result,
            "total_shafts": len(session.shafts),
            "snapshot": snapshot_result
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"축 생성 중 오류: {str(e)}",
            "session_id": session_id
        }

@mcp.tool()
def update_shaft_specs(
    session_id: str,
    shaft_variable: str,
    length: float = None,
    outer_diameter: float = None,
    bore_diameter: float = None
) -> dict:
    """
    축의 제원을 변경합니다.

    IMPORTANT:
        - length는 기존 프로파일 포인트의 offset을 수정하여 변경합니다.
        - outer_diameter와 bore_diameter는 기존 프로파일 포인트의 diameter를 수정하여 변경합니다.
        - 기존 프로파일 포인트를 직접 수정하는 효율적인 방식입니다.

    Args:
        session_id (str): 세션 ID
        shaft_variable (str): 축 변수명 (예: "shaft_1")
        length (float): 축 길이 (mm)
        outer_diameter (float): 축 외경 (mm)
        bore_diameter (float): 축 내경 (mm)

    Returns:
        dict: 변경 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {"success": False, "error": "세션이 초기화되지 않았습니다.", "session_id": session_id}

        update_code = f"""
# 축 제원 변경: {shaft_variable}
try:
    if '{shaft_variable}' in locals() or '{shaft_variable}' in globals():
        shaft = {shaft_variable}

        # 기존 프로파일 포인트 가져오기
        outer_points = shaft.active_definition.outer_profile.points
        inner_points = shaft.active_definition.inner_profile.points

        # 기존 포인트가 충분한지 확인 (최소 2개 필요: 시작, 끝)
        if len(outer_points) < 2 or len(inner_points) < 2:
            raise ValueError("프로파일 포인트가 충분하지 않습니다. 최소 2개 필요")

        # 길이 변경
        if {length} != None:
            new_length = {length}*MM
            outer_points[-1].offset = new_length
            inner_points[-1].offset = new_length

        # 외경 변경 (모든 outer 포인트)
        if {outer_diameter} != None:
            new_od = {outer_diameter}*MM
            for point in outer_points:
                point.diameter = new_od

        # 내경 변경 (모든 inner 포인트)
        if {bore_diameter} != None:
            new_id = {bore_diameter}*MM
            for point in inner_points:
                point.diameter = new_id

        # 프로파일 유효성 검증
        shaft.active_definition.outer_profile.make_valid()
        shaft.active_definition.inner_profile.make_valid()

        print(f"축 '{{shaft.editable_name}}' 제원 변경 완료")
        """

        if length is not None:
            update_code += f"\n        print(f'  - 길이: {length} mm (변경 후: {{shaft.length*1000:.1f}} mm)')"
        if outer_diameter is not None:
            update_code += f"\n        print(f'  - 외경: {outer_diameter} mm')"
        if bore_diameter is not None:
            update_code += f"\n        print(f'  - 내경: {bore_diameter} mm')"

        update_code += f"""
    else:
        print(f"오류: 축 '{shaft_variable}'를 찾을 수 없습니다")
except Exception as e:
    print(f"제원 변경 중 오류: {{e}}")
    import traceback
    traceback.print_exc()
"""

        execution_result = session.execute_python_code(update_code)

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"update_shaft_{shaft_variable}")

        return {
            "success": True,
            "session_id": session_id,
            "shaft_variable": shaft_variable,
            "updated_specs": {
                "length": length,
                "outer_diameter": outer_diameter,
                "bore_diameter": bore_diameter
            },
            "execution_result": execution_result,
            "snapshot": snapshot_result
        }

    except Exception as e:
        return {"success": False, "error": str(e), "session_id": session_id}


@mcp.tool()
def move_shaft(
    session_id: str,
    shaft_variable: str,
    position_x: float,
    position_y: float,
    position_z: float
) -> dict:
    """
    축의 위치를 변경합니다.

    Args:
        session_id (str): 세션 ID
        shaft_variable (str): 축 변수명 (예: "shaft_1")
        position_x (float): X축 위치 (mm)
        position_y (float): Y축 위치 (mm)
        position_z (float): Z축 위치 (mm)

    Returns:
        dict: 이동 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {"success": False, "error": "세션이 초기화되지 않았습니다.", "session_id": session_id}

        move_code = f"""
# 축 위치 변경: {shaft_variable}
from mastapy._private._math.vector_3d import Vector3D

try:
    if '{shaft_variable}' in locals() or '{shaft_variable}' in globals():
        shaft = {shaft_variable}
        desired_position = Vector3D({position_x}, {position_y}, {position_z}) * MM
        shaft.set_position_of_component_and_connected_components(desired_position)

        print(f"축 '{{shaft.editable_name}}' 위치 변경 완료")
        print(f"  - 위치: ({position_x}, {position_y}, {position_z}) mm")
    else:
        print(f"오류: 축 '{shaft_variable}'를 찾을 수 없습니다")
except Exception as e:
    print(f"위치 변경 중 오류: {{e}}")
"""

        execution_result = session.execute_python_code(move_code)

        # 세션 추적 목록 업데이트
        for shaft_info in session.shafts:
            if shaft_info.get("variable") == shaft_variable:
                shaft_info["position"] = [position_x, position_y, position_z]
                break

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"move_shaft_{shaft_variable}")

        return {
            "success": True,
            "session_id": session_id,
            "shaft_variable": shaft_variable,
            "new_position": [position_x, position_y, position_z],
            "execution_result": execution_result,
            "snapshot": snapshot_result
        }

    except Exception as e:
        return {"success": False, "error": str(e), "session_id": session_id}


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

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"create_gear_{gear_pair_name}")

        return {
            "success": True,
            "session_id": session_id,
            "gear_pair_name": gear_pair_name,
            "gear_info": gear_info,
            "execution_result": execution_result,
            "total_gears": len(session.gears),
            "snapshot": snapshot_result
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
    기어를 축에 장착하거나 위치를 변경합니다.

    이 함수는 기어의 현재 장착 상태를 확인하고 다음과 같이 동작합니다:
    1. 기어가 장착되지 않은 경우: 새로 장착
    2. 같은 축에 이미 장착된 경우: 위치만 변경 (연결 유지)
    3. 다른 축에 장착된 경우: 기존 연결 제거 후 새 축에 장착

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

        # 기어 장착/위치 변경 코드
        mount_code = f"""
# 기어 장착/위치 변경: {gear_pair_name}
# 기어 쌍에서 피니언과 휠 참조
pinion_mount = {gear_pair_name}.cylindrical_gears[0]
wheel_mount = {gear_pair_name}.cylindrical_gears[1]

# 피니언 처리
if pinion_mount.is_mounted:
    # 이미 장착된 경우
    current_conn = pinion_mount.inner_connection
    current_shaft = current_conn.shaft

    if current_shaft.name == "{pinion_shaft_name}":
        # 같은 축: 위치만 변경 (연결의 AxialPosition 속성 수정 시도)
        try:
            # Connection의 wrapped 객체에서 AxialPosition 속성 찾기
            if hasattr(current_conn.wrapped, 'AxialPosition'):
                current_conn.wrapped.AxialPosition = {pinion_position}*MM
                print(f"[위치 변경] 피니언: {{current_shaft.name}}에서 {pinion_position}mm로 위치 변경")
            else:
                # AxialPosition이 없으면 재장착
                print(f"[재장착] 피니언: 위치 변경 불가, 재장착 수행")
                # 재장착은 MASTA API에서 자동으로 기존 연결을 처리
                {pinion_shaft_name}.mount_component(pinion_mount, {pinion_position}*MM)
                print(f"[재장착 완료] 피니언: {{current_shaft.name}}에 {pinion_position}mm 위치에 재장착")
        except Exception as e:
            print(f"[오류] 피니언 위치 변경 실패: {{e}}")
            # 오류 발생 시 재장착 시도
            {pinion_shaft_name}.mount_component(pinion_mount, {pinion_position}*MM)
            print(f"[재장착 완료] 피니언: {{current_shaft.name}}에 {pinion_position}*MM 위치에 재장착")
    else:
        # 다른 축: 재장착 (MASTA API가 자동으로 기존 연결 제거)
        print(f"[축 변경] 피니언: {{current_shaft.name}} -> {pinion_shaft_name}")
        {pinion_shaft_name}.mount_component(pinion_mount, {pinion_position}*MM)
        print(f"[장착 완료] 피니언: {pinion_shaft_name}에 {pinion_position}mm 위치에 장착")
else:
    # 처음 장착
    {pinion_shaft_name}.mount_component(pinion_mount, {pinion_position}*MM)
    print(f"[신규 장착] 피니언: {pinion_shaft_name}에 {pinion_position}mm 위치에 장착")

# 휠 처리
if wheel_mount.is_mounted:
    # 이미 장착된 경우
    current_conn = wheel_mount.inner_connection
    current_shaft = current_conn.shaft

    if current_shaft.name == "{wheel_shaft_name}":
        # 같은 축: 위치만 변경
        try:
            if hasattr(current_conn.wrapped, 'AxialPosition'):
                current_conn.wrapped.AxialPosition = {wheel_position}*MM
                print(f"[위치 변경] 휠: {{current_shaft.name}}에서 {wheel_position}mm로 위치 변경")
            else:
                # AxialPosition이 없으면 재장착
                print(f"[재장착] 휠: 위치 변경 불가, 재장착 수행")
                {wheel_shaft_name}.mount_component(wheel_mount, {wheel_position}*MM)
                print(f"[재장착 완료] 휠: {{current_shaft.name}}에 {wheel_position}mm 위치에 재장착")
        except Exception as e:
            print(f"[오류] 휠 위치 변경 실패: {{e}}")
            {wheel_shaft_name}.mount_component(wheel_mount, {wheel_position}*MM)
            print(f"[재장착 완료] 휠: {{current_shaft.name}}에 {wheel_position}mm 위치에 재장착")
    else:
        # 다른 축: 재장착
        print(f"[축 변경] 휠: {{current_shaft.name}} -> {wheel_shaft_name}")
        {wheel_shaft_name}.mount_component(wheel_mount, {wheel_position}*MM)
        print(f"[장착 완료] 휠: {wheel_shaft_name}에 {wheel_position}mm 위치에 장착")
else:
    # 처음 장착
    {wheel_shaft_name}.mount_component(wheel_mount, {wheel_position}*MM)
    print(f"[신규 장착] 휠: {wheel_shaft_name}에 {wheel_position}mm 위치에 장착")

print(f"\\n기어 장착/위치 변경 완료")
"""

        # 코드 실행
        execution_result = session.execute_python_code(mount_code)

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"mount_gear_{gear_pair_name}")

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
            "execution_result": execution_result,
            "snapshot": snapshot_result
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
def update_gear_specs(
    session_id: str,
    gear_pair_name: str,
    center_distance: float = None,
    normal_module: float = None,
    helix_angle: float = None,
    pressure_angle: float = None,
    pinion_teeth: int = None,
    wheel_teeth: int = None,
    pinion_face_width: float = None,
    wheel_face_width: float = None,
    pinion_profile_shift: float = None,
    wheel_profile_shift: float = None
) -> dict:
    """
    기어 쌍의 제원을 변경합니다.

    Args:
        session_id (str): 세션 ID
        gear_pair_name (str): 기어 쌍 이름
        center_distance (float): 중심거리 (mm, None이면 변경하지 않음)
        normal_module (float): 모듈 (mm, None이면 변경하지 않음)
        helix_angle (float): 헬리컬 각도 (도, None이면 변경하지 않음)
        pressure_angle (float): 압력각 (도, None이면 변경하지 않음)
        pinion_teeth (int): 피니언 잇수 (None이면 변경하지 않음)
        wheel_teeth (int): 휠 잇수 (None이면 변경하지 않음)
        pinion_face_width (float): 피니언 치폭 (mm, None이면 변경하지 않음)
        wheel_face_width (float): 휠 치폭 (mm, None이면 변경하지 않음)
        pinion_profile_shift (float): 피니언 전위계수 (nominal, None이면 변경하지 않음)
        wheel_profile_shift (float): 휠 전위계수 (nominal, None이면 변경하지 않음)

    Returns:
        dict: 변경 결과
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {"success": False, "error": "세션이 초기화되지 않았습니다.", "session_id": session_id}

        update_code = f"""
# 기어 제원 변경: {gear_pair_name}
try:
    if '{gear_pair_name}' in locals() or '{gear_pair_name}' in globals():
        gear_pair = {gear_pair_name}

        # 기어 쌍 기본 제원 변경
        """

        if normal_module is not None:
            update_code += f"\n        gear_pair.active_gear_set_design.normal_module = {normal_module} * MM"
        if helix_angle is not None:
            update_code += f"\n        gear_pair.active_gear_set_design.helix_angle = {helix_angle} * RAD"
        if pressure_angle is not None:
            update_code += f"\n        gear_pair.active_gear_set_design.normal_pressure_angle_maintain_transverse_profile = {pressure_angle} * RAD"

        update_code += f"""

        # 피니언과 휠 참조
        pinion = gear_pair.active_gear_set_design.cylindrical_gears[0]
        wheel = gear_pair.active_gear_set_design.cylindrical_gears[1]
        """

        if pinion_teeth is not None:
            update_code += f"\n        pinion.number_of_teeth = {pinion_teeth}"
        if wheel_teeth is not None:
            update_code += f"\n        wheel.number_of_teeth = {wheel_teeth}"
        if pinion_face_width is not None:
            update_code += f"\n        pinion.face_width = {pinion_face_width} * MM"
        if wheel_face_width is not None:
            update_code += f"\n        wheel.face_width = {wheel_face_width} * MM"
        if pinion_profile_shift is not None:
            update_code += f"\n        pinion.nominal_profile_shift_coefficient = {pinion_profile_shift}"
        if wheel_profile_shift is not None:
            update_code += f"\n        wheel.nominal_profile_shift_coefficient = {wheel_profile_shift}"

        update_code += f"""

        print(f"기어 쌍 '{{gear_pair.name}}' 제원 변경 완료")
        {"print(f'  - 중심거리: " + str(center_distance) + " mm')" if center_distance else ""}
        {"print(f'  - 모듈: " + str(normal_module) + " mm')" if normal_module else ""}
        {"print(f'  - 헬리컬각: " + str(helix_angle) + "°')" if helix_angle else ""}
        {"print(f'  - 압력각: " + str(pressure_angle) + "°')" if pressure_angle else ""}
        {"print(f'  - 피니언 잇수: " + str(pinion_teeth) + "')" if pinion_teeth else ""}
        {"print(f'  - 휠 잇수: " + str(wheel_teeth) + "')" if wheel_teeth else ""}
        {"print(f'  - 피니언 치폭: " + str(pinion_face_width) + " mm')" if pinion_face_width else ""}
        {"print(f'  - 휠 치폭: " + str(wheel_face_width) + " mm')" if wheel_face_width else ""}
        {"print(f'  - 피니언 전위계수: " + str(pinion_profile_shift) + "')" if pinion_profile_shift else ""}
        {"print(f'  - 휠 전위계수: " + str(wheel_profile_shift) + "')" if wheel_profile_shift else ""}
    else:
        print(f"오류: 기어 쌍 '{gear_pair_name}'를 찾을 수 없습니다")
except Exception as e:
    print(f"제원 변경 중 오류: {{e}}")
    import traceback
    traceback.print_exc()
"""

        execution_result = session.execute_python_code(update_code)

        # 세션 추적 목록 업데이트
        for gear_info in session.gears:
            if gear_info.get("name") == gear_pair_name:
                if center_distance is not None:
                    gear_info["center_distance"] = center_distance
                if normal_module is not None:
                    gear_info["normal_module"] = normal_module
                if helix_angle is not None:
                    gear_info["helix_angle"] = helix_angle
                if pressure_angle is not None:
                    gear_info["pressure_angle"] = pressure_angle
                if pinion_teeth is not None:
                    gear_info["pinion_teeth"] = pinion_teeth
                if wheel_teeth is not None:
                    gear_info["wheel_teeth"] = wheel_teeth
                if pinion_face_width is not None:
                    gear_info["pinion_face_width"] = pinion_face_width
                if wheel_face_width is not None:
                    gear_info["wheel_face_width"] = wheel_face_width
                if pinion_profile_shift is not None:
                    gear_info["pinion_profile_shift"] = pinion_profile_shift
                if wheel_profile_shift is not None:
                    gear_info["wheel_profile_shift"] = wheel_profile_shift
                break

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"update_gear_{gear_pair_name}")

        return {
            "success": True,
            "session_id": session_id,
            "gear_pair_name": gear_pair_name,
            "updated_specs": {
                "center_distance": center_distance,
                "normal_module": normal_module,
                "helix_angle": helix_angle,
                "pressure_angle": pressure_angle,
                "pinion_teeth": pinion_teeth,
                "wheel_teeth": wheel_teeth,
                "pinion_face_width": pinion_face_width,
                "wheel_face_width": wheel_face_width,
                "pinion_profile_shift": pinion_profile_shift,
                "wheel_profile_shift": wheel_profile_shift
            },
            "execution_result": execution_result,
            "snapshot": snapshot_result
        }

    except Exception as e:
        return {"success": False, "error": str(e), "session_id": session_id}


@mcp.tool()
def create_bearing(
    session_id: str,
    bearing_name: str,
    shaft_name: str,
    position: float,
    bearing_designation: str = None,
    auto_select_by_diameter: float = None
) -> dict:
    """
    베어링을 생성하고 축에 장착합니다.

    Args:
        session_id (str): 세션 ID
        bearing_name (str): 베어링 이름
        shaft_name (str): 베어링이 장착될 축 이름
        position (float): 베어링 장착 위치 (축 길이 방향, mm)
        bearing_designation (str): 베어링 designation (예: "6206")
        auto_select_by_diameter (float): 축 내경을 기준으로 자동으로 베어링 선택 (mm)
                                         이 값이 지정되면 bearing_designation은 무시됨

    Returns:
        dict: 베어링 생성 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - bearing_name: 베어링 이름 (str)
            - bearing_info: 베어링 정보 (dict)
            - execution_result: 실행 결과 (str)
            - total_bearings: 총 베어링 개수 (int)

    Note:
        - bearing_designation과 auto_select_by_diameter 중 하나는 반드시 지정해야 합니다
        - auto_select_by_diameter를 사용하면 내경에 가장 가까운 62xx 시리즈 베어링이 자동 선택됩니다
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        # 베어링 designation 결정
        if auto_select_by_diameter is not None:
            bearing_designation = get_nearest_bearing_code(auto_select_by_diameter)
            print(f"자동 선택: 내경 {auto_select_by_diameter}mm -> 베어링 {bearing_designation}")
        elif bearing_designation is None:
            bearing_designation = "6206"  # 기본값
            print(f"기본 베어링 사용: {bearing_designation}")

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
            "variable": bearing_name,  # 베어링 변수명 추가
            "shaft_name": shaft_name,
            "position": position,
            "designation": bearing_designation,
            "auto_selected": auto_select_by_diameter is not None
        }
        session.bearings.append(bearing_info)

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"create_bearing_{bearing_name}")

        return {
            "success": True,
            "session_id": session_id,
            "bearing_name": bearing_name,
            "bearing_info": bearing_info,
            "execution_result": execution_result,
            "total_bearings": len(session.bearings),
            "snapshot": snapshot_result
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
def update_bearing_specs(
    session_id: str,
    bearing_name: str,
    designation: str = None
) -> dict:
    """
    베어링의 제원(형번)을 변경합니다.

    set_detail_from_catalogue() 메서드를 재호출하여 베어링 형번을 변경합니다.

    Args:
        session_id (str): 세션 ID
        bearing_name (str): 베어링 이름
        designation (str): 새로운 베어링 형번 (예: "6204", None이면 변경하지 않음)

    Returns:
        dict: 변경 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - bearing_name: 베어링 이름 (str)
            - updated_specs: 변경된 제원 정보 (dict)
            - execution_result: 실행 결과 (str)
            - snapshot: 스냅샷 저장 결과 (dict)
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
                "session_id": session_id
            }

        # 베어링 정보 찾기
        bearing_info = None
        for bearing in session.bearings:
            if bearing.get("name") == bearing_name:
                bearing_info = bearing
                break

        if not bearing_info:
            return {
                "success": False,
                "error": f"베어링 '{bearing_name}'를 찾을 수 없습니다.",
                "session_id": session_id
            }

        bearing_variable = bearing_info.get("variable")

        # 변경할 내용이 없으면 오류 반환
        if designation is None:
            return {
                "success": False,
                "error": "변경할 제원을 하나 이상 지정해야 합니다.",
                "session_id": session_id
            }

        # 베어링 제원 변경 코드 생성
        update_code = f"""
# 베어링 제원 변경: {bearing_name}
from mastapy.bearings import BearingCatalog

try:
    if '{bearing_variable}' in locals() or '{bearing_variable}' in globals():
        bearing = {bearing_variable}

        # 베어링 형번 변경 (set_detail_from_catalogue 재호출)
        bearing.set_detail_from_catalogue(BearingCatalog.SKF, "{designation}")

        print(f"베어링 '{{bearing.editable_name}}' 제원 변경 완료")
        print(f"  - 새로운 형번: {designation}")
    else:
        print(f"오류: 베어링 '{bearing_variable}'를 찾을 수 없습니다")
except Exception as e:
    print(f"베어링 제원 변경 중 오류: {{e}}")
    import traceback
    traceback.print_exc()
"""

        # 코드 실행
        execution_result = session.execute_python_code(update_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result or "오류" in execution_result:
            return {
                "success": False,
                "error": f"베어링 제원 변경 실패: {execution_result}",
                "session_id": session_id
            }

        # 세션 추적 목록 업데이트
        if bearing_info:
            bearing_info["designation"] = designation

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"update_bearing_{bearing_name}")

        return {
            "success": True,
            "session_id": session_id,
            "bearing_name": bearing_name,
            "updated_specs": {
                "designation": designation
            },
            "execution_result": execution_result,
            "snapshot": snapshot_result
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
            "error": f"베어링 제원 변경 중 오류: {str(e)}",
            "session_id": session_id
        }


@mcp.tool()
def move_bearing(
    session_id: str,
    bearing_name: str,
    position: float
) -> dict:
    """
    베어링의 축 상 위치를 변경합니다.

    shaft.mount_component() 메서드를 재호출하여 베어링을 새로운 위치로 재장착합니다.

    Args:
        session_id (str): 세션 ID
        bearing_name (str): 베어링 이름
        position (float): 새로운 축 상 위치 (mm)

    Returns:
        dict: 변경 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - bearing_name: 베어링 이름 (str)
            - new_position: 새로운 위치 (float)
            - execution_result: 실행 결과 (str)
            - snapshot: 스냅샷 저장 결과 (dict)
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
                "session_id": session_id
            }

        # 베어링 정보 찾기
        bearing_info = None
        for bearing in session.bearings:
            if bearing.get("name") == bearing_name:
                bearing_info = bearing
                break

        if not bearing_info:
            return {
                "success": False,
                "error": f"베어링 '{bearing_name}'를 찾을 수 없습니다.",
                "session_id": session_id
            }

        bearing_variable = bearing_info.get("variable")
        shaft_name = bearing_info.get("shaft_name")

        # 베어링 위치 변경 코드 생성 (mount_component 재호출)
        move_code = f"""
# 베어링 위치 변경: {bearing_name}
try:
    if '{bearing_variable}' in locals() or '{bearing_variable}' in globals():
        bearing = {bearing_variable}

        # 축에 베어링을 새로운 위치로 재장착 (mount_component 재호출)
        {shaft_name}.mount_component(bearing, {position}*MM)

        print(f"베어링 '{{bearing.editable_name}}' 위치 변경 완료")
        print(f"  - 새로운 위치: {position} mm")
    else:
        print(f"오류: 베어링 '{bearing_variable}'를 찾을 수 없습니다")
except Exception as e:
    print(f"베어링 위치 변경 중 오류: {{e}}")
    import traceback
    traceback.print_exc()
"""

        # 코드 실행
        execution_result = session.execute_python_code(move_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result or "오류" in execution_result:
            return {
                "success": False,
                "error": f"베어링 위치 변경 실패: {execution_result}",
                "session_id": session_id
            }

        # 세션 추적 목록 업데이트
        if bearing_info:
            bearing_info["position"] = position

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"move_bearing_{bearing_name}")

        return {
            "success": True,
            "session_id": session_id,
            "bearing_name": bearing_name,
            "new_position": position,
            "execution_result": execution_result,
            "snapshot": snapshot_result
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
            "error": f"베어링 위치 변경 중 오류: {str(e)}",
            "session_id": session_id
        }


@mcp.tool()
def show_model(session_id: str, save_image: bool = True) -> dict:
    """
    생성된 MASTA 모델을 시각화합니다.

    Args:
        session_id (str): 세션 ID
        save_image (bool): 이미지를 파일로 저장할지 여부 (기본값: True)

    Returns:
        dict: 시각화 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - message: 결과 메시지 (str)
            - image_path: 저장된 이미지 경로 (str, save_image=True인 경우)
            - execution_result: 실행 결과 (str)
            - model_summary: 모델 요약 정보 (dict)
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요."
            }

        result = {
            "success": True,
            "session_id": session_id,
            "model_summary": {
                "shafts": len(session.shafts),
                "gears": len(session.gears),
                "bearings": len(session.bearings)
            }
        }

        if save_image:
            # 이미지 저장 경로 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_filename = f"model_view_{timestamp}.png"
            image_path = os.path.join(session.images_dir, image_filename)

            # 경로를 안전하게 처리 (백슬래시 이스케이프)
            safe_image_path = image_path.replace('\\', '\\\\')

            # 모델 시각화 코드 생성 및 실행
            show_code = generate_plot_code(session.assembly_name, safe_image_path)
            execution_result = session.execute_python_code(show_code)

            # 실행 결과 확인
            if "Failed to execute" in execution_result:
                return {
                    "success": False,
                    "error": f"모델 시각화 실패: {execution_result}",
                    "session_id": session_id
                }

            # 파일 추적 목록에 추가
            session.add_file(image_path, "image")

            result["message"] = "모델 시각화 및 이미지 저장 완료"
            result["image_path"] = image_path
            result["execution_result"] = execution_result
        else:
            # 화면에만 표시 (저장하지 않음)
            show_code = f"""
import matplotlib.pyplot as plt

# MASTA 모델 3D 뷰 시각화
plt.figure(figsize=(12, 12))

# 3개의 서브플롯 생성
plt.subplot(1, 3, 1)
plt.imshow({session.assembly_name}.three_d_isometric_view)
plt.title('Isometric View')
plt.axis('off')

plt.subplot(1, 3, 2)
plt.imshow({session.assembly_name}.three_d_view_orientated_in_xz_plane_with_y_axis_pointing_into_the_screen)
plt.title('XZ Plane View')
plt.axis('off')

plt.subplot(1, 3, 3)
plt.imshow({session.assembly_name}.three_d_view_orientated_in_xy_plane_with_z_axis_pointing_into_the_screen)
plt.title('XY Plane View')
plt.axis('off')

plt.tight_layout()
plt.show()
print("모델 시각화 완료 (화면 표시)")
"""
            execution_result = session.execute_python_code(show_code)

            result["message"] = "모델 시각화 완료 (화면 표시)"
            result["execution_result"] = execution_result

        return result

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
def save_masta_file(session_id: str, file_name: str = None) -> dict:
    """
    MASTA Design을 파일로 저장합니다.

    Args:
        session_id (str): 세션 ID
        file_name (str): 저장할 파일 이름 (확장자 제외, None이면 자동 생성)

    Returns:
        dict: 저장 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - file_path: 저장된 파일 경로 (str)
            - file_name: 파일 이름 (str)
            - execution_result: 실행 결과 (str)
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
                "session_id": session_id
            }

        # 파일 이름 생성
        if file_name is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"masta_design_{timestamp}"

        # .masta 확장자 추가 (없는 경우)
        if not file_name.endswith('.masta'):
            file_name += '.masta'

        # 파일 경로 생성
        file_path = os.path.join(session.modelings_dir, file_name)
        safe_file_path = file_path.replace('\\', '\\\\')

        # MASTA 파일 저장 코드
        save_code = f"""
# MASTA 파일 저장
try:
    # Design.save(file_name: str, save_results: bool) -> Status
    status = {session.design_name}.save(r'{safe_file_path}', False)
    print(f"MASTA 파일 저장 완료: {file_path}")
    print(f"저장 상태: {{status}}")
except Exception as e:
    print(f"MASTA 파일 저장 실패: {{e}}")
    import traceback
    traceback.print_exc()
"""

        # 코드 실행
        execution_result = session.execute_python_code(save_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result or "저장 실패" in execution_result:
            return {
                "success": False,
                "error": f"MASTA 파일 저장 실패: {execution_result}",
                "session_id": session_id
            }

        # 파일 추적 목록에 추가
        session.add_file(file_path, "masta")

        return {
            "success": True,
            "session_id": session_id,
            "file_path": file_path,
            "file_name": file_name,
            "execution_result": execution_result,
            "message": f"MASTA 파일이 저장되었습니다: {file_name}"
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
            "error": f"MASTA 파일 저장 중 오류: {str(e)}",
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
def calculate_module_from_center_distance(
    center_distance: float,
    pinion_teeth: int,
    wheel_teeth: int,
    helix_angle: float = 0.0
) -> dict:
    """
    중심거리, 잇수, 헬리컬 각도로부터 노멀 모듈을 계산합니다.

    Args:
        center_distance (float): 중심거리 (mm)
        pinion_teeth (int): 피니언 잇수
        wheel_teeth (int): 휠 잇수
        helix_angle (float): 헬리컬 각도 (도, 기본값: 0.0)

    Returns:
        dict: 계산 결과
            - success: 성공 여부 (bool)
            - normal_module: 계산된 노멀 모듈 (float, mm)
            - input_parameters: 입력 파라미터 정보 (dict)
    """
    try:
        normal_module = calculate_normal_module(
            center_distance, pinion_teeth, wheel_teeth, helix_angle
        )

        return {
            "success": True,
            "normal_module": round(normal_module, 6),
            "input_parameters": {
                "center_distance": center_distance,
                "pinion_teeth": pinion_teeth,
                "wheel_teeth": wheel_teeth,
                "helix_angle": helix_angle,
                "total_teeth": pinion_teeth + wheel_teeth,
                "gear_ratio": wheel_teeth / pinion_teeth
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"모듈 계산 중 오류: {str(e)}"
        }


@mcp.tool()
def find_bearing_by_diameter(inner_diameter: float) -> dict:
    """
    축 내경에 가장 가까운 62xx 시리즈 베어링 형번을 찾습니다.

    Args:
        inner_diameter (float): 베어링 내경 (mm)

    Returns:
        dict: 베어링 정보
            - success: 성공 여부 (bool)
            - bearing_code: 베어링 형번 (str, 예: "6206")
            - inner_diameter: 입력된 내경 (float)
            - matched_diameter: 매칭된 표준 내경 (float)
            - is_exact_match: 정확히 일치하는지 여부 (bool)
    """
    try:
        bearing_code = get_nearest_bearing_code(inner_diameter)

        # 표준 내경 목록
        standard_diameters = {
            "6200": 10, "6201": 12, "6202": 15, "6203": 17, "6204": 20,
            "6205": 25, "6206": 30, "6207": 35, "6208": 40, "6209": 45,
            "6210": 50, "6211": 55, "6212": 60, "6213": 65, "6214": 70,
            "6215": 75, "6216": 80, "6217": 85, "6218": 90, "6219": 95,
            "6220": 100
        }

        matched_diameter = standard_diameters.get(bearing_code, inner_diameter)
        is_exact_match = (matched_diameter == inner_diameter)

        return {
            "success": True,
            "bearing_code": bearing_code,
            "inner_diameter": inner_diameter,
            "matched_diameter": matched_diameter,
            "is_exact_match": is_exact_match
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"베어링 검색 중 오류: {str(e)}"
        }


@mcp.tool()
def delete_component(
    session_id: str,
    component_name: str
) -> dict:
    """
    지정된 컴포넌트(축, 기어, 베어링 등)를 삭제합니다.

    Args:
        session_id (str): 세션 ID
        component_name (str): 삭제할 컴포넌트 변수 이름

    Returns:
        dict: 삭제 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - component_name: 삭제된 컴포넌트 이름 (str)
            - execution_result: 실행 결과 (str)

    Note:
        - 삭제할 컴포넌트는 반드시 존재해야 합니다
        - 삭제 후 해당 컴포넌트 변수는 사용할 수 없습니다
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
                "session_id": session_id
            }

        # 컴포넌트 삭제 코드
        delete_code = f"""
# 컴포넌트 삭제: {component_name}
try:
    # 컴포넌트가 존재하는지 확인
    if '{component_name}' not in locals() and '{component_name}' not in globals():
        print(f"오류: 컴포넌트 '{component_name}'를 찾을 수 없습니다")
    else:
        # Design에서 컴포넌트 삭제
        component_to_delete = {component_name}

        # MASTA API의 delete 메서드 호출
        if hasattr(component_to_delete, 'delete'):
            component_to_delete.delete()
            print(f"컴포넌트 '{component_name}' 삭제 완료 (delete 메서드 사용)")
        elif hasattr({session.design_name}, 'delete_entity'):
            {session.design_name}.delete_entity(component_to_delete)
            print(f"컴포넌트 '{component_name}' 삭제 완료 (delete_entity 사용)")
        elif hasattr({session.assembly_name}, 'remove_component'):
            {session.assembly_name}.remove_component(component_to_delete)
            print(f"컴포넌트 '{component_name}' 삭제 완료 (remove_component 사용)")
        else:
            print(f"경고: 적절한 삭제 메서드를 찾을 수 없습니다")

        # 변수 삭제
        del {component_name}
        print(f"변수 '{component_name}' 삭제 완료")

except NameError:
    print(f"오류: 컴포넌트 '{component_name}'가 정의되지 않았습니다")
except Exception as e:
    print(f"삭제 중 오류 발생: {{e}}")
    import traceback
    traceback.print_exc()
"""

        # 코드 실행
        execution_result = session.execute_python_code(delete_code)

        # 실행 결과 확인
        if "Failed to execute" in execution_result or "오류" in execution_result:
            return {
                "success": False,
                "error": f"컴포넌트 삭제 실패: {execution_result}",
                "session_id": session_id,
                "component_name": component_name
            }

        # 세션 추적 목록에서도 제거 (variable 기준)
        session.shafts = [s for s in session.shafts if s.get("variable") != component_name]
        session.gears = [g for g in session.gears if g.get("variable") != component_name and g.get("name") != component_name]
        session.bearings = [b for b in session.bearings if b.get("name") != component_name]

        # 모델 스냅샷 저장
        snapshot_result = _save_model_snapshot(session, f"delete_{component_name}")

        return {
            "success": True,
            "session_id": session_id,
            "component_name": component_name,
            "execution_result": execution_result,
            "snapshot": snapshot_result
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
            "error": f"컴포넌트 삭제 중 오류: {str(e)}",
            "session_id": session_id
        }


@mcp.tool()
def clear_all_components(session_id: str) -> dict:
    """
    세션의 모든 컴포넌트를 삭제하고 깨끗한 상태로 초기화합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 초기화 결과
            - success: 성공 여부 (bool)
            - session_id: 세션 ID (str)
            - deleted_components: 삭제된 컴포넌트 수 (dict)
            - execution_result: 실행 결과 (str)

    Note:
        - Design과 Assembly 객체는 유지되고 내부 컴포넌트만 삭제됩니다
        - 이 작업은 되돌릴 수 없습니다
    """
    try:
        session = get_session(session_id)

        if not session.is_initialized:
            return {
                "success": False,
                "error": "세션이 초기화되지 않았습니다. masta_initialize()를 먼저 호출하세요.",
                "session_id": session_id
            }

        deleted_count = {
            "shafts": len(session.shafts),
            "gears": len(session.gears),
            "bearings": len(session.bearings)
        }

        # 모든 컴포넌트 삭제 코드
        clear_code = f"""
# 모든 컴포넌트 삭제
deleted_items = []

try:
    # Assembly의 모든 컴포넌트 가져오기
    if hasattr({session.assembly_name}, 'components'):
        components = list({session.assembly_name}.components)
        print(f"발견된 컴포넌트 수: {{len(components)}}")

        for component in components:
            try:
                component_name = component.name if hasattr(component, 'name') else str(component)

                # 컴포넌트 삭제 시도
                if hasattr(component, 'delete'):
                    component.delete()
                    deleted_items.append(component_name)
                elif hasattr({session.assembly_name}, 'remove_component'):
                    {session.assembly_name}.remove_component(component)
                    deleted_items.append(component_name)

            except Exception as e:
                print(f"컴포넌트 삭제 실패 ({{component_name}}): {{e}}")

    # 추가로 특정 컴포넌트 타입별로 삭제 시도
    if hasattr({session.assembly_name}, 'shafts'):
        shafts = list({session.assembly_name}.shafts)
        for shaft in shafts:
            try:
                if hasattr(shaft, 'delete'):
                    shaft.delete()
                    deleted_items.append(f"shaft_{{shaft.name if hasattr(shaft, 'name') else 'unknown'}}")
            except:
                pass

    print(f"\\n총 {{len(deleted_items)}}개 컴포넌트 삭제 완료")
    print("삭제된 컴포넌트:", deleted_items)

except Exception as e:
    print(f"전체 삭제 중 오류: {{e}}")
    import traceback
    traceback.print_exc()
"""

        # 코드 실행
        execution_result = session.execute_python_code(clear_code)

        # 세션 추적 목록 초기화
        session.shafts.clear()
        session.gears.clear()
        session.bearings.clear()

        return {
            "success": True,
            "session_id": session_id,
            "deleted_components": deleted_count,
            "execution_result": execution_result,
            "message": f"총 {sum(deleted_count.values())}개 컴포넌트 삭제 완료"
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
            "error": f"컴포넌트 전체 삭제 중 오류: {str(e)}",
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
    print("=" * 80)
    print("MASTA Tools MCP Server - 통합 테스트 모드")
    print("=" * 80)

    # 1. 초기화
    print("\n[1단계] MASTA 초기화")
    print("-" * 80)
    init_result = masta_initialize()
    print(f"초기화 결과: {init_result['success']}")

    if not init_result['success']:
        print(f"오류: {init_result.get('error')}")
        exit(1)

    session_id = init_result['session_id']
    print(f"세션 ID: {session_id[:8]}...")

    # ========== 축(Shaft) 테스트 ==========
    print("\n" + "=" * 80)
    print("축(Shaft) 테스트: 생성 → 제원 변경 → 이동 → 삭제")
    print("=" * 80)

    # 2. 축 생성
    print("\n[2-1] 축 생성")
    shaft_result = create_shaft(
        session_id=session_id,
        shaft_name="TestShaft_1",
        length=160,
        position_x=0,
        position_y=0,
        position_z=0
    )
    print(f"[OK] 축 생성: {shaft_result['shaft_variable']}")
    print(f"결과: {shaft_result}")

    # 3. 축 제원 변경
    print("\n[2-2] 축 제원 변경")
    update_shaft_result = update_shaft_specs(
        session_id=session_id,
        shaft_variable=shaft_result['shaft_variable'],
        length=200,
        outer_diameter=50,
        bore_diameter=10
    )
    print(f"[OK] 축 제원 변경 완료")
    print(f"결과: {update_shaft_result}")

    # 4. 축 이동
    print("\n[2-3] 축 위치 변경")
    move_shaft_result = move_shaft(
        session_id=session_id,
        shaft_variable=shaft_result['shaft_variable'],
        position_x=10,
        position_y=5,
        position_z=0
    )
    print(f"[OK] 축 위치 변경 완료")
    print(f"결과: {move_shaft_result}")

    # 5. 축 삭제
    print("\n[2-4] 축 삭제")
    delete_shaft_result = delete_component(
        session_id=session_id,
        component_name=shaft_result['shaft_variable']
    )
    print(f"[OK] 축 삭제 완료")
    print(f"결과: {delete_shaft_result}")

    status_after_shaft = get_session_status(session_id)
    print(f"→ 축 삭제 후 컴포넌트 수: {status_after_shaft['component_count']}")

    # ========== 기어(Gear) 테스트 ==========
    print("\n" + "=" * 80)
    print("기어(Gear) 테스트: 생성 → 제원 변경 → 이동 → 삭제")
    print("=" * 80)

    # 기어 테스트를 위해 축 2개 재생성
    print("\n[3-0] 기어 장착용 축 생성")
    shaft1_result = create_shaft(
        session_id=session_id,
        shaft_name="GearShaft_1",
        length=160,
        position_x=0,
        position_y=0,
        position_z=0
    )
    shaft2_result = create_shaft(
        session_id=session_id,
        shaft_name="GearShaft_2",
        length=140,
        position_x=90,
        position_y=31.618,
        position_z=0
    )
    print(f"[OK] 축 2개 생성: {shaft1_result['shaft_variable']}, {shaft2_result['shaft_variable']}")
    print(f"결과 1: {shaft1_result}")
    print(f"결과 2: {shaft2_result}")

    # 6. 기어 쌍 생성
    print("\n[3-1] 기어 쌍 생성")
    gear_result = create_gear_pair(
        session_id=session_id,
        gear_pair_name="test_gear_pair",
        center_distance=45,
        pinion_teeth=20,
        wheel_teeth=40,
        normal_module=2.0,
        helix_angle=0.0,
        pressure_angle=20.0
    )
    print(f"[OK] 기어 쌍 생성: {gear_result['gear_pair_name']}")
    print(f"결과: {gear_result}")

    # 7. 기어 제원 변경
    print("\n[3-2] 기어 제원 변경")
    update_gear_result = update_gear_specs(
        session_id=session_id,
        gear_pair_name=gear_result['gear_pair_name'],
        normal_module=2.5,
        pinion_teeth=22,
        wheel_teeth=44,
        pinion_face_width=25.0,
        wheel_face_width=25.0,
        pinion_profile_shift=0.3,
        wheel_profile_shift=0.2
    )
    print(f"[OK] 기어 제원 변경 완료")
    print(f"결과: {update_gear_result}")

    # 8. 기어 장착
    print("\n[3-3] 기어 축에 장착")
    mount_gear_result = mount_gear_on_shaft(
        session_id=session_id,
        gear_pair_name=gear_result['gear_pair_name'],
        pinion_shaft_name=shaft1_result['shaft_variable'],
        wheel_shaft_name=shaft2_result['shaft_variable'],
        pinion_position=80,
        wheel_position=70
    )
    print(f"[OK] 기어 장착 완료")
    print(f"결과: {mount_gear_result}")

    # 9. 기어 위치 변경 (재장착)
    print("\n[3-4] 기어 위치 변경 (재장착)")
    remount_gear_result = mount_gear_on_shaft(
        session_id=session_id,
        gear_pair_name=gear_result['gear_pair_name'],
        pinion_shaft_name=shaft1_result['shaft_variable'],
        wheel_shaft_name=shaft2_result['shaft_variable'],
        pinion_position=100,
        wheel_position=90
    )
    print(f"[OK] 기어 위치 변경 완료")
    print(f"결과: {remount_gear_result}")

    # 9-1. 기어 모델 파일 저장 (자동 파일명)
    print("\n[3-4-1] 기어 모델 MASTA 파일 저장 (자동 파일명)")
    save_gear_result = save_masta_file(
        session_id=session_id
    )
    print(f"[OK] 기어 모델 파일 저장 완료")
    print(f"결과: {save_gear_result}")

    # 10. 기어 삭제
    print("\n[3-5] 기어 삭제")
    delete_gear_result = delete_component(
        session_id=session_id,
        component_name=gear_result['gear_pair_name']
    )
    print(f"[OK] 기어 삭제 완료")
    print(f"결과: {delete_gear_result}")

    status_after_gear = get_session_status(session_id)
    print(f"→ 기어 삭제 후 컴포넌트 수: {status_after_gear['component_count']}")

    # ========== 베어링(Bearing) 테스트 ==========
    print("\n" + "=" * 80)
    print("베어링(Bearing) 테스트: 생성 → 제원 변경 → 이동 → 삭제")
    print("=" * 80)

    # 10. 베어링 생성 (자동 선택)
    print("\n[4-1] 베어링 생성")
    bearing_result = create_bearing(
        session_id=session_id,
        bearing_name="test_bearing",
        shaft_name=shaft1_result['shaft_variable'],
        position=40,
        auto_select_by_diameter=30
    )
    print(f"[OK] 베어링 생성: {bearing_result['bearing_name']}")
    print(f"결과: {bearing_result}")

    # 11. 베어링 제원 변경 (update_bearing_specs 사용)
    print("\n[4-2] 베어링 제원 변경 (designation 변경)")
    bearing_update_result = update_bearing_specs(
        session_id=session_id,
        bearing_name=bearing_result['bearing_name'],
        designation="6208"  # 자동 선택된 형번 -> 6208로 변경
    )
    print(f"[OK] 베어링 제원 변경 완료 (6208)")
    print(f"결과: {bearing_update_result}")

    # 12. 베어링 위치 변경 (move_bearing 사용)
    print("\n[4-3] 베어링 위치 변경")
    bearing_move_result = move_bearing(
        session_id=session_id,
        bearing_name=bearing_result['bearing_name'],
        position=60  # 40 -> 60으로 이동
    )
    print(f"[OK] 베어링 위치 변경 완료")
    print(f"결과: {bearing_move_result}")

    # 12-1. 베어링 포함 모델 파일 저장 (지정 파일명)
    print("\n[4-3-1] 베어링 포함 모델 MASTA 파일 저장 (지정 파일명)")
    save_bearing_result = save_masta_file(
        session_id=session_id,
        file_name="gear_with_bearing_model"
    )
    print(f"[OK] 베어링 포함 모델 파일 저장 완료")
    print(f"결과: {save_bearing_result}")

    # 13. 베어링 삭제
    print("\n[4-4] 베어링 삭제")
    delete_bearing_result = delete_component(
        session_id=session_id,
        component_name=bearing_result['bearing_name']
    )
    print(f"[OK] 베어링 삭제 완료")
    print(f"결과: {delete_bearing_result}")

    status_after_bearing = get_session_status(session_id)
    print(f"→ 베어링 삭제 후 컴포넌트 수: {status_after_bearing['component_count']}")

    # ========== 최종 정리 ==========
    print("\n" + "=" * 80)
    print("최종 세션 정리")
    print("=" * 80)

    # 14. 최종 세션 상태 확인
    print("\n[5-1] 최종 세션 상태 확인")
    final_status = get_session_status(session_id)
    print(f"→ 최종 컴포넌트 수: {final_status['component_count']}")
    print(f"결과: {final_status}")

    # # 15. 세션 정리
    # print("\n[5-2] 세션 정리")
    # cleanup_result = cleanup_session(session_id)
    # print(f"[OK] 세션 정리 완료: {cleanup_result['success']}")
    # print(f"결과: {cleanup_result}")

    print("\n" + "=" * 80)
    print("전체 테스트 완료!")
    print("=" * 80)

    # 서버 실행 (필요시 주석 해제)
    # mcp.run()