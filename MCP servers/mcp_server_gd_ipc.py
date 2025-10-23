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
from typing import Dict, Optional
import pandas as pd

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import llm_call, remove_code_block_llm  # LLM 호출 함수 임포트

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("GearDesign_IPC_agent")

# GearDesign.exe 경로 설정
gear_design_exe_path = r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows\GearDesign.exe"


class GearDesignIPC:
    """GearDesign과 프로세스 간 통신(IPC)을 담당하는 클래스"""

    def __init__(self, exe_path: str, progress_callback=None):
        """
        Args:
            exe_path: GearDesign.exe 실행 파일 경로
            progress_callback: 진행 상황 콜백 함수 (선택)
                               함수 시그니처: callback(message: str, percentage: int)
        """
        self.exe_path = Path(exe_path)
        self.process: Optional[subprocess.Popen] = None
        self.progress_callback = progress_callback

    def start(self) -> bool:
        """GearDesign 프로세스를 IPC 모드로 시작"""

        if not self.exe_path.exists():
            print(f"오류: 실행 파일을 찾을 수 없습니다: {self.exe_path}")
            return False

        try:
            self.process = subprocess.Popen(
                [str(self.exe_path.absolute()), "--ipc-mode"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',  # UTF-8 인코딩 명시
                errors='replace',   # 디코딩 오류 시 대체 문자 사용
                bufsize=1,
                cwd=str(self.exe_path.parent.absolute())
            )
            print(f"프로세스 시작 (PID: {self.process.pid})")

            # ⭐ stderr 모니터링 스레드 시작
            stderr_thread = threading.Thread(target=self._monitor_stderr, daemon=True)
            stderr_thread.start()

            # stderr 읽기 (디버그 메시지 확인)
            time.sleep(1)

            # 프로세스 상태 확인
            if self.process.poll() is not None:
                stderr_output = self.process.stderr.read()
                stdout_output = self.process.stdout.read()
                print(f"프로세스 종료됨")
                print(f"STDERR: {stderr_output}")
                print(f"STDOUT: {stdout_output}")
                return False

            return True

        except Exception as e:
            print(f"프로세스 시작 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _monitor_stderr(self):
        """stderr를 별도 스레드에서 모니터링하여 디버그 메시지 출력"""
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stderr.readline()
                if line:
                    print(f"[.NET DEBUG] {line.rstrip()}")
        except Exception as e:
            print(f"[ERROR] stderr 모니터링 오류: {e}")

    def _send_command(self, command: Dict[str, any]) -> Dict[str, any]:
        """명령을 전송하고 응답 받기 (진행 상황 지원)"""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("GearDesign 프로세스가 실행 중이지 않습니다")

        # 명령 전송
        command_str = json.dumps(command) + "\n"
        self.process.stdin.write(command_str)
        self.process.stdin.flush()

        # 응답 받기 (여러 줄 가능 - progress 메시지 처리)
        while True:
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("프로세스로부터 응답이 없습니다")

            try:
                response = json.loads(response_line)
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류: {response_line}")
                raise RuntimeError(f"잘못된 JSON 응답: {e}")

            # 메시지 타입 확인
            msg_type = response.get("type", "result")

            if msg_type == "progress":
                # 진행 상황 메시지 처리
                message = response.get('message', '')
                percentage = response.get('percentage', 0)

                if self.progress_callback:
                    # 사용자 정의 콜백 함수 호출
                    try:
                        self.progress_callback(message=message, percentage=percentage)
                    except Exception as e:
                        print(f"콜백 함수 실행 오류: {e}")
                else:
                    # 기본 출력
                    print(f"[진행 {percentage}%] {message}")

                continue  # 다음 줄 읽기

            elif msg_type == "result":
                # 최종 결과 반환
                return response

            else:
                # 알 수 없는 타입 또는 type 필드 없음 (하위 호환성)
                return response

    def load_and_validate_config(self, config_data: Dict[str, any]) -> Dict[str, any]:
        """설정 데이터 로드"""
        command = {
            "action": "load_and_validate_config",
            "config": config_data
        }
        return self._send_command(command)

    def calc_geometry(self) -> Dict[str, any]:
        """기어 치형 기하학적 계산"""
        command = {
            "action": "calc_geometry",
        }
        return self._send_command(command)

    def calc_loadcase(self, geometry_data: Dict[str, any]) -> Dict[str, any]:
        """기어 하중 계산"""
        command = {
            "action": "calc_loadcase",
            "geometry_data": geometry_data
        }
        return self._send_command(command)

    def calculate(self) -> Dict[str, any]:
        """기어 치형 기하학적 계산 및 하중 계산 통합 수행"""
        command = {"action": "calculate"}
        return self._send_command(command)

    def get_messages(self) -> Dict[str, any]:
        """계산 메시지 가져오기"""
        command = {"action": "get_messages"}
        return self._send_command(command)

    def save_2D_image(self, path: str) -> Dict[str, any]:
        """기어 2D 이미지 저장"""
        command = {
            "action": "save_2D_image",
            "path": path
        }
        return self._send_command(command)

    def save_3d_modeling(self, path: str) -> Dict[str, any]:
        """3D 모델링 저장"""
        command = {
            "action": "save_3d_modeling",
            "path": path
        }
        return self._send_command(command)

    def save_3d_image(self, path: str, width: int = 800, height: int = 600) -> Dict[str, any]:
        """3D 이미지 저장"""
        command = {
            "action": "save_3d_image",
            "path": path,
            "width": width,
            "height": height
        }
        return self._send_command(command)

    def save_report(self, path: str, config_data: Dict[str, any]) -> Dict[str, any]:
        """보고서 저장"""
        command = {
            "action": "save_report",
            "path": path,
            "config": config_data
        }
        
        return self._send_command(command)

    def get_all_results_summary(self, config_data: Dict[str, any]) -> Dict[str, any]:
        """모든 계산 결과 요약 조회"""
        command = {
            "action": "get_all_results_summary",
            "results": config_data
        }
        return self._send_command(command)

    def get_default_config(self) -> Dict[str, any]:
        """기본 설정 데이터 가져오기"""
        command = {"action": "get_default_config"}
        return self._send_command(command)

    def simple_sizing_gearpair_get_input(self) -> Dict[str, any]:
        """SimpleSizing - Gear Pair 계산 수행을 위한 입력값 추출"""
        command = {
            "action": "simple_sizing_gearpair_get_input",
        }
        return self._send_command(command)

    def simple_sizing_gearpair(self, modify_data: Dict[str, any]) -> Dict[str, any]:
        """SimpleSizing - Gear Pair 계산 수행"""
        command = {
            "action": "simple_sizing_gearpair",
            "modify_data": modify_data
        }
        return self._send_command(command)

    def apply_simplesizing_case(self, case_data: Dict[str, any]) -> Dict[str, any]:
        """SimpleSizing 결과 케이스를 현재 기어 데이터에 적용"""
        command = {
            "action": "apply_simplesizing_case",
            "case_data": case_data
        }
        return self._send_command(command)

    def calculate_facewidth_for_ep_beta(
        self,
        target_overlap_ratio: float,
        helix_angle_deg: float,
        normal_module: float
    ) -> Dict[str, any]:
        """목표 겹침비율(εβ)을 달성하기 위한 치폭 계산"""
        command = {
            "action": "calculate_facewidth_for_ep_beta",
            "target_overlap_ratio": target_overlap_ratio,
            "helix_angle_deg": helix_angle_deg,
            "normal_module": normal_module
        }
        return self._send_command(command)

    def calculate_helixangle_for_ep_beta(
        self,
        target_overlap_ratio: float,
        face_width: float,
        normal_module: float
    ) -> Dict[str, any]:
        """목표 겹침비율(εβ)을 달성하기 위한 헬릭스각 계산"""
        command = {
            "action": "calculate_helixangle_for_ep_beta",
            "target_overlap_ratio": target_overlap_ratio,
            "face_width": face_width,
            "normal_module": normal_module
        }
        return self._send_command(command)

    def stop(self):
        """프로세스 종료"""
        if self.process:
            try:
                command = {"action": "exit"}
                command_str = json.dumps(command) + "\n"
                self.process.stdin.write(command_str)
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except:
                self.process.terminate()
                self.process.wait(timeout=2)
            print("GearDesign IPC 프로세스 종료됨")

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
        self.default_data = None
        self.changed_data = None
        self.gd_results = None  # 전체 계산 결과 (Python dict)
        self.simplesizing_input = None  # SimpleSizing 입력 데이터
        self.simplesizing_results = None  # SimpleSizing 결과 데이터
        self.ipc_client: Optional[GearDesignIPC] = None
        self.created_at = datetime.datetime.now()
        self.last_accessed = datetime.datetime.now()

        # 세션별 출력 폴더 경로
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs", session_id)
        self.images_dir = os.path.join(self.output_dir, "images")
        self.reports_dir = os.path.join(self.output_dir, "reports")
        self.modelings_dir = os.path.join(self.output_dir, "modelings")
        self.files = []  # 생성된 파일 목록 추적

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
                print(f"세션 {self.session_id} IPC 프로세스 종료됨")
            except Exception as e:
                print(f"IPC 프로세스 종료 중 오류: {str(e)}")


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
        # IPC 프로세스 정리
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


@mcp.tool()
def initialize() -> dict:
    """
    기어 설계를 위한 도구 및 데이터를 초기화합니다.

    이 함수는 새로운 세션을 자동으로 생성하고 IPC를 통해 GearDesign 프로세스를 시작합니다.
    초기화가 완료되면 반환된 session_id를 사용하여 다른 기어 관련 함수들을 호출할 수 있습니다.

    Returns:
        dict: 초기화 결과
            - 성공 시: {"success": True, "message": "초기화 완료", "session_id": "새로생성된세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지"}

    Note:
        - 매번 새로운 세션을 생성하므로 독립적인 작업 공간을 제공합니다
        - 반환된 session_id를 다른 모든 함수 호출에 사용해야 합니다
        - 이 함수는 기어 설계 작업을 시작하는 첫 번째 함수입니다
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
        session.ipc_client = GearDesignIPC(gear_design_exe_path)

        if not session.ipc_client.start():
            return {
                "success": False,
                "error": "GearDesign IPC 프로세스 시작 실패",
                "session_id": new_session_id
            }

        # 기본 설정 데이터 로드
        # .NET에 get_default_config action이 없는 경우를 대비해 빈 dict로 초기화
        try:
            response = session.ipc_client.get_default_config()
            if response.get("success", False):
                session.default_data = response.get("config", {})
            else:
                # action이 구현되지 않은 경우 빈 dict 사용
                print(f"경고: get_default_config 실패, 빈 설정으로 시작: {response.get('error', 'Unknown')}")
                session.default_data = {}
        except Exception as e:
            print(f"경고: get_default_config 호출 실패, 빈 설정으로 시작: {e}")
            session.default_data = {}

        session.changed_data = session.default_data.copy() if session.default_data else {}

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
        # 오류 발생 시 IPC 프로세스 정리
        if session.ipc_client:
            session.ipc_client.stop()

        return {
            "success": False,
            "error": f"초기화 중 오류 발생: {str(e)}",
            "session_id": new_session_id
        }

@mcp.tool()
def load_GearDesign_data(file_path: str, session_id: str) -> dict:
    """
    사용자가 업로드한 JSON 파일로부터 기어 설계 데이터를 초기화합니다.

    이 함수는 사용자가 업로드한 JSON 파일을 읽어 검증하고 세션에 로드합니다.
    파일이 존재하지 않거나 데이터가 유효하지 않으면 오류 메시지를 반환합니다.

    Args:
        file_path (str): 사용자가 업로드한 JSON 파일의 절대 또는 상대 경로
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 처리 결과
            - 성공 시: {"success": True, "message": "데이터 로드 및 검증 완료", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - JSON 파일은 UTF-8 인코딩이어야 합니다
        - 파일 내용은 JSON 호환 딕셔너리여야 합니다
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
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    # 파일 존재 여부 확인
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"파일을 찾을 수 없습니다: {file_path}",
            "session_id": session.session_id
        }

    # # 파일 확장자 확인
    # if not file_path.lower().endswith('.json'):
    #     return {
    #         "success": False,
    #         "error": "JSON 파일만 지원됩니다",
    #         "session_id": session.session_id
    #     }

    # JSON 파일 읽기
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            user_data_dict = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 파싱 오류: {str(e)}",
            "session_id": session.session_id
        }
    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "파일 인코딩 오류 (UTF-8 인코딩을 사용하세요)",
            "session_id": session.session_id
        }
    except PermissionError:
        return {
            "success": False,
            "error": f"파일 접근 권한이 없습니다: {file_path}",
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"파일 읽기 오류: {str(e)}",
            "session_id": session.session_id
        }

    # 데이터 타입 확인
    if not isinstance(user_data_dict, dict):
        return {
            "success": False,
            "error": "JSON 파일 내용은 객체(딕셔너리)여야 합니다",
            "session_id": session.session_id
        }

    # IPC를 통해 데이터 검증 및 로드
    try:
        ipc_response = session.ipc_client.load_and_validate_config(user_data_dict)
        
        if ipc_response.get("success", False):
            # 기존 데이터를 사용자 데이터로 변환
            session.changed_data = user_data_dict
            
            return {
                "success": True,
                "message": "사용자 데이터 로드 및 검증 완료",
                "loaded_file": os.path.basename(file_path),
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "error": f"데이터 검증 실패: {ipc_response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"처리 중 오류 발생: {str(e)}",
            "session_id": session.session_id
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
        - 기어비는 기어 타입에 따라 잇수비로 결정됩니다. 이에 대한 상세 내용은 아래와 같습니다.
            1) Gear pair: z2 / z1,
            2) Three gear: z3 / z1,
            3) Planetary: z3 / z1 (링기어 잇수 / 선기어 잇수),
            4) Double pinion planetary: z3 / z1 (링기어 잇수 / 선기어 잇수)
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
    system_prompt = """
# 역할
당신은 기어 설계 JSON 데이터 수정 전문가입니다.

# 목적
사용자의 자연어 요청을 분석하여 기어 설계 JSON 데이터의 필요한 값만 정확히 변경합니다.

# 입력 데이터 구조 이해
1. **메타데이터**: Key가 '$'로 시작 (예: "$Normal Module", "$z1")
   - 메타데이터는 해당 값의 의미/단위를 설명합니다
   
2. **실제 데이터**: '$' 없는 일반 Key
   - 이 값들만 수정 대상입니다
   - 메타데이터가 없는 Key 값은 수정 대상이 아닙니다

# 수정 규칙

## 1. 변경 대상 식별
- 사용자 요청을 분석하여 변경해야 할 정확한 Key와 경로를 찾습니다
- 메타데이터($로 시작)를 참고하되, 절대 메타데이터를 변경하지 않습니다

## 2. 중심거리 자동계산 트리거
다음 매크로 기어 제원이 변경되면 **반드시 "CDMethod": 1** 추가 (단, 사용자가 명시적으로 중심거리를 지정한 경우 제외):
- 잇수 (z1, z2, z3, z4)
- 모듈 (Normal Module, Axial Module)
- 헬리컬각 (Helix Angle)
- 압력각 (Pressure Angle)
- 전위계수 (x1, x2, x3, x4)

## 3. 기어비 변경 요청
- 기어비는 기어 타입에 따라 잇수비로 결정됩니다. 따라서 사용자가 기어비 변경을 요청하면 기어 잇수를 적절히 변경해야 합니다. 
- 기어타입에 따른 기어비 계산 상세 내용은 아래와 같습니다.
    1) Gear pair: z2 / z1,
    2) Three gear: z3 / z1,
    3) Planetary: z3 / z1 (링기어 잇수 / 선기어 잇수),
    4) Double pinion planetary: z3 / z1 (링기어 잇수 / 선기어 잇수)

## 4. 작동조건 변경 요청
- 작동조건(시간, 온도, 토크, 속도 등) 변경 시 'Rating.Load spectrum' 의 해당 값만 수정합니다
- 시간, 온도 조건은 사용자가 별도로 변경 요청을 하지 않으면 기본 값을 활용하되, 변경 요청 시 해당 값을 변경합니다.
- 기어타입에 따라 토크/속도 조건은 아래의 규칙을 준수하여 변경해야 함 
   1) CASE1: Gear Pair 인 경우 아래의 정보가 모두 포함되어야 함
    - Gear1/Gear2 속도 중 1개 (Gear1/Gear2 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2 파워 중 1개, 또는 Gear1/Gear2 토크 중 1개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2는 사용자의 어휘에 따라 입력/출력 기어 or Pinion/Wheel 기어 등으로 불릴 수 있음
    - 예시1: 입력속도 1000 rpm, 출력토크 50Nm -> OK
    - 예시2: 입력속도 1000 rpm, 출력속도 500 rpm, 출력토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: 입력속도 1000 rpm, 입력파워 100W, 출력토크 50Nm -> NG (입력 파워와 토크 모두 주어짐)

   2) CASE2: Three Gear 
    - Gear1/Gear2/Gear3 의 속도 중 1개 (입/출력 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3 의 파워 중 2개, 또는 토크 중 2개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3은 사용자의 어휘에 따라 입력/아이들러/출력 기어 or Pinion/Idler/Wheel 기어 등으로 불릴 수 있음
    - 예시1: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 토크 50Nm -> OK
    - 예시2: Gear1 속도 1000 rpm, Gear2 속도 500 rpm, Gear3 토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 파워 50W -> NG (입력 파워와 토크 모두 주어짐)

   3) CASE3: Simple Planetary, Double Pinion Planetary
    - Sun/Carrier/Ring 의 속도 중 2개 (유성기어의 속도는 3개의 입력 중 2개로 결정되기 때문에 반드시 2개 입력 필요)
    - Sun/Carrier/Ring 의 파워 중 1개, 또는 토크 중 1개 (유성기어의 파워 또는 토크는 1개의 입력과 입력된 속도로 나머지가 모두 계산됨)

    ### 입출력 작동조건 단위 (사용자가 단위계를 입력하지 않은 경우 아래 단위로 간주함)
    - 시간 단위: "hr" (예: "100 hr", "5000 시간" 등)
    - 속도 단위: "rpm" (예: "1000rpm", "3600rpm" 등)
    - 파워 단위: "kW" (예: "100 kW", "5kW" 등) 
    - 토크 단위: "Nm" (예: "50Nm", "200Nm" 등)

## 5. 출력 형식
- **표준 JSON 형식** (중첩 구조 포함)
- **변경된 항목만** 포함
- 상위 경로를 포함한 Key 이름은 원본과 정확히 일치
- Value는 적절한 데이터 타입 (숫자는 number, 문자는 string)

# 출력 예시
```json
{
  "Basic Data": {
    "Normal Module": 3.0,
    "z1": 20,
    "z2": 60,
    "CDMethod": 1
  }  
}
```
"""

    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"사용자 요청: {user_message}\n현재 데이터: {json.dumps(session.changed_data, ensure_ascii=False)}"}
    ]

    try:
        # LLM 호출하여 변경데이터 추출
        response = llm_call(prompt=prompt, model="gpt-5-mini")
        modified_data = remove_code_block_llm(response)
        modified_data = json.loads(modified_data)

        # 기존 데이터에 변경사항 적용 및 추적
        update_result = recursive_update(session.changed_data, modified_data)

        # 변경 내역 요약
        change_summary = []
        if update_result["updated"]:
            change_summary.append(f"✅ 변경됨: {len(update_result['updated'])}개")
            for path, old, new in update_result["updated"]:
                change_summary.append(f"  - {path}: {old} → {new}")

        if update_result["not_found"]:
            change_summary.append(f"⚠️ 경로 불일치 (새로 추가됨): {len(update_result['not_found'])}개")
            for path, val in update_result["not_found"]:
                change_summary.append(f"  - {path}: {val} (경로가 기존 데이터에 존재하지 않아 새로 추가됨)")

        if update_result["unchanged"]:
            change_summary.append(f"ℹ️ 변경 없음 (동일한 값): {len(update_result['unchanged'])}개")
            for path, val in update_result["unchanged"]:
                change_summary.append(f"  - {path}: {val}")

        # print("\n".join(change_summary))

        # ⭐ 변경 성공 여부 판정: 경로 불일치만 실패로 처리
        has_not_found = len(update_result["not_found"]) > 0

        if has_not_found:
            # 경로 불일치가 있으면 실패
            return {
                "success": False,
                "message": f"경로 불일치: LLM이 반환한 {len(update_result['not_found'])}개 항목이 기존 데이터 구조에 존재하지 않습니다",
                "modified_data": modified_data,
                "change_summary": "\n".join(change_summary),
                "update_details": update_result,
                "session_id": session.session_id
            }

        # 데이터 검증 및 로드
        ipc_response = session.ipc_client.load_and_validate_config(session.changed_data)

        if ipc_response.get("success", False):
            # 메시지 결정
            has_updates = len(update_result["updated"]) > 0
            if has_updates:
                message = f"데이터 수정 및 검증 완료 ({len(update_result['updated'])}개 항목 변경됨)"
            else:
                message = "요청한 값이 이미 설정되어 있습니다 (변경 없음)"

            return {
                "success": True,
                "message": message,
                "modified_data": modified_data,
                "change_summary": "\n".join(change_summary),
                "update_details": update_result,
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "message": f"데이터 검증 실패: {ipc_response.get('error', 'Unknown error')}",
                "modified_data": modified_data,
                "change_summary": "\n".join(change_summary),
                "update_details": update_result,
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

# 재귀적으로 dict를 업데이트하는 함수 (변경 추적 포함)
def recursive_update(d, u, path=""):
    """
    재귀적으로 dict를 업데이트하고 변경 내역을 추적합니다.

    Args:
        d: 업데이트할 대상 dict
        u: 업데이트 내용 dict
        path: 현재 경로 (추적용)

    Returns:
        dict: 변경 내역
            - updated: [(경로, 이전값, 새값), ...]
            - not_found: [(경로, 시도한값), ...]
            - unchanged: [(경로, 값), ...]
    """
    result = {
        "updated": [],      # 성공적으로 업데이트된 경로
        "not_found": [],    # 경로를 찾지 못한 키
        "unchanged": []     # 값이 같아서 변경하지 않은 경로
    }

    for k, v in u.items():
        current_path = f"{path}.{k}" if path else k

        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            # 중첩된 dict인 경우 재귀 호출
            sub_result = recursive_update(d[k], v, current_path)
            # 하위 결과 병합
            result["updated"].extend(sub_result["updated"])
            result["not_found"].extend(sub_result["not_found"])
            result["unchanged"].extend(sub_result["unchanged"])
        elif k in d:
            # 키가 존재하는 경우
            old_value = d[k]
            if old_value == v:
                result["unchanged"].append((current_path, v))
            else:
                d[k] = v
                result["updated"].append((current_path, old_value, v))
        else:
            # 키가 존재하지 않는 경우 (새로 추가)
            d[k] = v
            result["not_found"].append((current_path, v))

    return result

@mcp.tool()
def calc_geometry(session_id: str) -> dict:
    """
    기어 치형의 기하학적 계산을 수행합니다. (이전 수행 결과 message는 삭제됩니다.)

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
        - 기하학적 계산만 수행하며, 하중 계산은 calc_load_case()로 별도 수행
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
        # IPC를 통해 기하학적 계산만 수행
        response = session.ipc_client.calc_geometry()

        if not response.get("success", False):
            return {
                "success": False,
                "error": f"기하학적 계산 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

        # 기하학적 계산 결과 저장
        geometry_results = response.get("results", {})
        session.gd_results = geometry_results

        # 반환값 생성
        return {
            "success": True,
            "message": "치형 계산이 완료되었습니다.",
            "session_id": session.session_id
        }            

    except Exception as e:
        return {
            "error": f"기하학적 계산 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def get_geometry_results(session_id: str) -> dict:
    """
    기어 치형의 기하학적 계산 결과를 전달합니다. (calc_geometry() 이후 호출)

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 기하학적 계산 결과
            - "Geometry": 기하학적 계산 결과 데이터
            - "session_id": 세션 ID
            - "error": 오류 메시지 (실패 시)

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

    # 결과 반환
    if isinstance(session.gd_results, dict) and "Geometry" in session.gd_results:
        geometry_data = session.gd_results["Geometry"]

        # Geometry가 dict인 경우
        if isinstance(geometry_data, dict):
            output = geometry_data.copy()
            output["session_id"] = session.session_id
            return output
        # Geometry가 list나 다른 타입인 경우
        else:
            return {
                "Geometry": geometry_data,
                "session_id": session.session_id
            }
    else:
        return {
            "error": "유효하지 않은 기하학적 계산 결과입니다.",
            "session_id": session.session_id
        }


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
    if session.gd_results is None:
        return {
            "error": "기하학적 계산이 먼저 수행되어야 합니다. calc_geometry() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    try:
        # IPC를 통해 하중 계산 수행
        response = session.ipc_client.calc_loadcase(session.gd_results)

        if not response.get("success", False):
            return {
                "success": False,
                "error": f"하중 계산 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

        # 하중 계산 결과 저장
        loadcase_results = response.get("results", {})

        # 전체 결과 업데이트
        session.gd_results = loadcase_results

        messages = {
            "success": True,
            "message": response.get("messages", []),
            "session_id": session.session_id
        }

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

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 실행 메시지 정보
            - 성공 시: 메시지 데이터를 포함하는 딕셔너리
            - 실패 시: {"error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 계산이 완료된 후에 호출해야 합니다
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
        response = session.ipc_client.get_messages()

        if not response.get("success", False):
            return {
                "error": f"메시지 조회 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

        return {
            "success": True,
            "messages": response.get("messages", []),
            "session_id": session.session_id
        }

    except Exception as e:
        return {
            "error": f"메시지 조회 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def get_2D_image(session_id: str) -> dict:
    """
    기어 치물림 2D 이미지를 생성하고 파일로 저장합니다.

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
            "error": "계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_image_{timestamp}.png"
        output_file = os.path.join(session.images_dir, filename)

        response = session.ipc_client.save_2D_image(output_file)

        if response.get("success", False):
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
                "error": f"이미지 추출 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"이미지 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def get_3d_image(session_id: str, width: int = 800, height: int = 600) -> dict:
    """
    기어 3D 이미지를 생성하고 파일로 저장합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).
        width (int): 이미지 폭 (기본값: 800)
        height (int): 이미지 높이 (기본값: 600)

    Returns:
        dict: 3D 이미지 생성 결과
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
            "error": "계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_3d_image_{timestamp}.png"
        output_file = os.path.join(session.images_dir, filename)

        response = session.ipc_client.save_3d_image(output_file, width, height)

        if response.get("success", False):
            if os.path.exists(output_file):
                session.add_file(output_file, "3d_image")

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
                    "error": "3D 이미지 파일이 생성되지 않았습니다",
                    "session_id": session.session_id
                }
        else:
            return {
                "success": False,
                "error": f"3D 이미지 추출 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"3D 이미지 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def get_3d_modeling(session_id: str) -> dict:
    """
    기어 3D 모델링 파일(STEP)을 생성하고 저장합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 3D 모델링 생성 결과
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
            "error": "계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_3d_model_{timestamp}.step"
        output_file = os.path.join(session.modelings_dir, filename)

        response = session.ipc_client.save_3d_modeling(output_file)

        if response.get("success", False):
            if os.path.exists(output_file):
                session.add_file(output_file, "3d_model")

                return {
                    "success": True,
                    "path": output_file,
                    "filename": filename,
                    "size": os.path.getsize(output_file),
                    "session_id": session.session_id,
                    "relative_path": f"outputs/{session.session_id}/{filename}"
                }
            else:
                return {
                    "success": False,
                    "error": "3D 모델링 파일이 생성되지 않았습니다",
                    "session_id": session.session_id
                }
        else:
            return {
                "success": False,
                "error": f"3D 모델링 추출 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"3D 모델링 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def get_allresults_summary(session_id: str) -> dict:
    """
    기어 설계의 모든 계산 결과를 요약하여 반환합니다.

    기하학적 계산과 하중 계산의 결과를 종합하여 핵심 정보를 JSON 형태로 제공합니다.
    반환된 요약 정보는 LLM이 직접 읽고 사용자에게 계산 결과에 대해 항상 표 형태로 표시해야 합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 계산 결과 요약
            {
                "success": True,
                "summary": {
                    "$테이블명1": "테이블1에 대한 설명 또는 메타정보",
                    "테이블명1": {
                        "columns": ["컬럼명1", "컬럼명2", ...],
                        "rowHeaders": ["행헤더1", "행헤더2", ...],
                        "rows": [
                            ["값1", "값2", ...],
                            ["값1", "값2", ...],
                            ...
                        ]
                    },
                    "$테이블명2": "테이블2 설명",
                    "테이블명2": {...},
                    ...
                },
                "session_id": "세션ID"
            }

            - $ 접두사가 있는 키: 해당 테이블에 대한 메타데이터 (테이블과 같은 레벨)
            - $ 없는 키: 실제 계산 데이터 테이블 (columns, rowHeaders, rows 구조)
            - rows: 2차원 배열 형태 (각 행은 columns 순서와 일치하는 값들의 배열)

    Note:
        - **필수 전제조건**: initialize() → calc_geometry() → calc_load_case() 순서대로 실행
        - calc_load_case() 없이 호출하면 오류 발생
        - 반환되는 테이블 구조는 기어 타입에 따라 다를 수 있음
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
            "error": "계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }
    
    if "LC" not in session.gd_results:
        return {
            "success": False,
            "error": "하중 계산이 먼저 수행되어야 합니다. calc_load_case()를 호출하세요",
            "session_id": session.session_id
        }

    try:
        try:
            response = session.ipc_client.get_all_results_summary(session.gd_results)

            if response.get("success", False):
                # 원본 데이터 그대로 반환 (LLM이 직접 읽고 처리)
                response["session_id"] = session.session_id
                return response
            else:
                # action이 구현되지 않은 경우 세션 데이터에서 직접 추출
                print(f"경고: get_all_results_summary 실패, 세션 데이터에서 추출: {response.get('error', 'Unknown')}")
                raise Exception("Fallback to session data")

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
        - 사전에 초기화와 계산이 모두 완료되어야 합니다
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
            "error": "계산이 먼저 수행되어야 합니다",
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

        response = session.ipc_client.save_report(output_file, session.gd_results)

        if response.get("success", False):
            if os.path.exists(output_file):
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
                "error": f"기어 보고서 추출 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"보고서 생성 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def simple_sizing_gearpair(user_message: str, session_id: str) -> dict:
    """
    사용자 요구에 따라 적절한 Gear pair 제원을 선정하기 위한 Sizing을 수행합니다.
    Sizing은 최적화는 아니지만, 다양한 제원에 대해 case study를 수행하여 적절한 기어쌍 제원을 도출하는 것을 목표로 합니다.

    현재 세션의 기어 데이터를 바탕으로 사용자 요구에 따라 간단한 기어쌍 사이징을 수행하고,
    결과를 세션에 저장합니다.
    사용자 메세지는 이전 대화를 기반으로 자연어로 주요사항을 요약해서 입력합니다. 

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 사이징 결과
            - 성공 시: {"success": True, "message": "사이징이 완료되었습니다", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 이 함수는 간단한 사이징만 수행하며, 상세한 설계 검증은 포함하지 않습니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    # 1. 초기화 상태 확인
    if not session.is_initialized:
        return {
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }    

    try:
        # 2. 사이징 입력 데이터 생성
        sizinginput = session.ipc_client.simple_sizing_gearpair_get_input()

        if not sizinginput.get("success", False):
            return {
                "success": False,
                "error": f"사이징 입력 데이터 생성 실패: {sizinginput.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }
        
        simplesizing_input = sizinginput.get("inputs", {})
        print(f"Initial simplesizing input: {simplesizing_input}")
        # 3. 사용자 메시지를 기반으로 입력 데이터 수정
        ## 기존 데이터와 사용자 메시지를 LLM에 전달하여 변경된 데이터 추출
        system_prompt = """
# 역할
당신은 기어쌍의 simple sizing을 위한 설계 JSON 데이터 수정 전문가입니다.
# 목적
사용자의 자연어 요청을 분석하여 기어 설계 JSON 데이터의 필요한 값만 정확히 변경합니다.
# 입력 데이터 구조 이해
1. **메타데이터**: Key가 '$'로 시작 (예: "$Normal Module", "$z1")
   - 메타데이터는 해당 값의 의미/단위를 설명합니다
2. **실제 데이터**: '$' 없는 일반 Key
   - 이 값들만 수정 대상입니다
3. **SimpleSizing이 탐색하는 설계 파라미터** (최소/최대 범위 내 조합 생성):
   - **모듈 (m_n)**: 최소값 ~ 최대값 범위
   - **잇수 (z_pinion)**: 최소값 ~ 최대값 범위
4. **SimpleSizing에서 고정되는 파라미터** (입력값 그대로 사용):
   - **치폭 (Facewidth)**: 단일 고정값
   - **압력각 (α_n)**: 단일 고정값
   - **헬리컬각 (β)**: 단일 고정값
# 수정 규칙
## 1. 변경 대상 식별
- 사용자 요청을 분석하여 변경해야 할 정확한 Key를 찾습니다
- 메타데이터($로 시작)를 참고하되, 절대 메타데이터를 변경하지 않습니다
## 2. 출력 형식
- **표준 JSON 형식** (중첩 구조 포함)
- **변경된 항목만** 포함
- Key 이름은 원본과 정확히 일치
- Value는 적절한 데이터 타입 (숫자는 number, 문자는 string)
# 출력 예시
```json
{
    "target_GR": 3.0, 
    "face_width": 20,
    "helix_angle": 10,
    "maxcases": 1000
}
```
        """
        prompt = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"사용자 요청: {user_message}\nsimple_sizing 입력 데이터: {json.dumps(simplesizing_input, ensure_ascii=False)}"}
        ]

        ## LLM 호출하여 변경데이터 추출
        llm_response = llm_call(prompt=prompt, model="gpt-5-mini")
        modified_data = remove_code_block_llm(llm_response)
        modified_data = json.loads(modified_data)

        # 4. 기존 데이터에 변경사항 적용 및 추적
        update_result = recursive_update(simplesizing_input, modified_data)

        # 변경 내역 출력
        change_summary = []
        if update_result["updated"]:
            change_summary.append(f"✅ SimpleSizing 입력 변경됨: {len(update_result['updated'])}개")
            for path, old, new in update_result["updated"]:
                change_summary.append(f"  - {path}: {old} → {new}")

        if update_result["not_found"]:
            change_summary.append(f"⚠️ 경로 불일치 (새로 추가됨): {len(update_result['not_found'])}개")
            for path, val in update_result["not_found"]:
                change_summary.append(f"  - {path}: {val}")

        if update_result["unchanged"]:
            change_summary.append(f"ℹ️ 변경 없음: {len(update_result['unchanged'])}개")

        # ⭐ 변경 성공 여부 판정: 경로 불일치만 실패로 처리
        has_not_found = len(update_result["not_found"]) > 0

        if has_not_found:
            # 경로 불일치가 있으면 실패
            return {
                "success": False,
                "error": f"경로 불일치: LLM이 반환한 {len(update_result['not_found'])}개 항목이 SimpleSizing 입력 구조에 존재하지 않습니다",
                "change_summary": "\n".join(change_summary),
                "update_details": update_result,
                "session_id": session.session_id
            }

        response = session.ipc_client.simple_sizing_gearpair(simplesizing_input)

        if response.get("success", False):
            # 사이징 결과를 pandas DataFrame으로 변환하여 저장
            filtered_results_data = response.get("filtered_results", {})

            try:
                # .NET DataTable → pandas DataFrame 변환
                if filtered_results_data and isinstance(filtered_results_data, list):
                    session.simplesizing_results = pd.DataFrame(filtered_results_data)
                elif filtered_results_data and isinstance(filtered_results_data, dict):
                    # dict 형태인 경우 (단일 레코드 또는 특정 구조)
                    session.simplesizing_results = pd.DataFrame([filtered_results_data])
                else:
                    session.simplesizing_results = pd.DataFrame()  # 빈 DataFrame

            except Exception as e:
                session.simplesizing_results = filtered_results_data

            # 메시지 결정
            has_updates = len(update_result["updated"]) > 0
            if has_updates:
                message = f"사이징이 완료되었습니다 ({len(update_result['updated'])}개 항목 변경됨)"
            else:
                message = "요청한 값이 이미 설정되어 있습니다 (변경 없음)"

            return {
                "success": True,
                "message": message,
                "session_id": session.session_id,
                "result_rows": len(session.simplesizing_results) if isinstance(session.simplesizing_results, pd.DataFrame) else None,
                "change_summary": "\n".join(change_summary),
                "update_details": update_result
            }
        else:
            return {
                "success": False,
                "error": f"사이징 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"사이징 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_simplesizing_results(session_id: str, return_all: bool = False, top_n: int = 100) -> dict:
    """
    SimpleSizing 계산 결과를 DataFrame 형태로 반환합니다.

    Args:
        session_id (str): 세션 ID
        return_all (bool, optional): True이면 모든 결과 반환, False이면 top_n개만 반환 (기본값: False)
        top_n (int, optional): return_all이 False일 때 반환할 결과 개수 (기본값: 100)

    Returns:
        dict: SimpleSizing 결과
            - success: 성공 여부
            - results: DataFrame을 dict로 변환한 결과
            - shape: (rows, columns)
            - total_rows: 전체 결과 행 수
            - returned_rows: 실제 반환된 행 수
            - session_id: 세션 ID
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
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    if session.simplesizing_results is None:
        return {
            "success": False,
            "error": "SimpleSizing 계산이 먼저 수행되어야 합니다",
            "session_id": session.session_id
        }

    try:
        if isinstance(session.simplesizing_results, pd.DataFrame):
            df = session.simplesizing_results
            total_rows = len(df)

            # return_all이 False이면 상위 top_n개만 선택
            if not return_all and top_n > 0:
                df = df.head(top_n)

            # row index를 컬럼으로 추가
            df = df.reset_index()

            # DataFrame을 dict로 변환 (records 형태)
            results_dict = df.to_dict('records')

            return {
                "success": True,
                "results": results_dict,
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "total_rows": total_rows,
                "returned_rows": len(df),
                "columns": list(df.columns),
                "session_id": session.session_id
            }
        else:
            # DataFrame이 아닌 경우 (dict로 저장된 경우)
            return {
                "success": True,
                "results": session.simplesizing_results,
                "session_id": session.session_id,
                "note": "결과가 DataFrame이 아닌 dict 형태로 저장되어 있습니다"
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"결과 조회 중 오류: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def apply_simplesizing_case(row_index: int, session_id: str) -> dict:
    """
    SimpleSizing 결과의 특정 케이스를 현재 기어 데이터에 적용합니다.

    이 함수는 SimpleSizing 결과 DataFrame에서 사용자가 선택한 행(케이스)의 데이터를
    IPC를 통해 GearDesign에 전달하여 현재 기어 설계 데이터에 적용합니다.

    Args:
        row_index (int): SimpleSizing 결과 DataFrame의 행 인덱스 (0부터 시작)
                        예: get_simplesizing_results()로 조회한 결과에서 3번째 케이스를 선택하려면 row_index=2
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 적용 결과
            - 성공 시: {
                "success": True,
                "message": "케이스가 적용되었습니다",
                "applied_data": {...},  # 적용된 데이터 (모듈, 잇수 등)
                "session_id": "세션ID"
              }
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 simple_sizing_gearpair()가 완료되어야 합니다
        - 적용 후에는 calc_geometry() → calc_load_case()를 수행하여 최종 검증해야 합니다
        - row_index는 0부터 시작하며, get_simplesizing_results()의 results 리스트 인덱스와 일치합니다
        - C# 측에서 updated_config를 반환해야 changed_data가 정확히 동기화됩니다

    Example:
        # SimpleSizing 수행
        simple_sizing_gearpair("기어비 3, 저소음", session_id)

        # 결과 조회
        results = get_simplesizing_results(session_id, False, 20)

        # 사용자가 2번 케이스(인덱스 1) 선택
        apply_result = apply_simplesizing_case(1, session_id)

        # 적용 후 계산
        calc_geometry(session_id)
        calc_load_case(session_id)
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
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    if session.simplesizing_results is None:
        return {
            "success": False,
            "error": "SimpleSizing 계산이 먼저 수행되어야 합니다. simple_sizing_gearpair() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    try:
        # DataFrame에서 특정 row 추출
        if isinstance(session.simplesizing_results, pd.DataFrame):
            df = session.simplesizing_results

            if row_index < 0 or row_index >= len(df):
                return {
                    "success": False,
                    "error": f"잘못된 인덱스: {row_index} (유효 범위: 0~{len(df)-1})",
                    "session_id": session.session_id
                }

            # 선택된 row의 데이터를 dict로 변환
            # DataFrame 컬럼명과 C# SimpleSizingCase.FromDictionary() 키가 일치하므로 직접 전달
            selected_row = df.iloc[row_index].to_dict()

            # IPC를 통해 C#에 전달하고 적용
            response = session.ipc_client.apply_simplesizing_case(selected_row)

            if response.get("success", False):
                # C#에서 변경된 config 데이터 반환받아 업데이트
                updated_config = response.get("updated_config")

                if updated_config:
                    # GearDesign에서 반환한 전체 config로 changed_data 업데이트
                    session.changed_data = updated_config

                    return {
                        "success": True,
                        "message": f"{row_index}번 케이스가 적용되었습니다",
                        "applied_data": selected_row,
                        "session_id": session.session_id
                    }
                else:
                    # updated_config가 없으면 경고 (하위 호환성)
                    return {
                        "success": True,
                        "message": f"{row_index}번 케이스가 적용되었습니다 (config 업데이트 없음)",
                        "applied_data": selected_row,
                        "session_id": session.session_id,
                        "warning": "C#에서 updated_config를 반환하지 않았습니다. Program.cs 업데이트가 필요합니다."
                    }
            else:
                return {
                    "success": False,
                    "error": f"케이스 적용 실패: {response.get('error', 'Unknown error')}",
                    "session_id": session.session_id
                }
        else:
            return {
                "success": False,
                "error": "SimpleSizing 결과가 DataFrame이 아닙니다",
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"케이스 적용 중 오류: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def calculate_facewidth_for_ep_beta(
    target_overlap_ratio: float,
    helix_angle_deg: float,
    normal_module: float,
    session_id: str
) -> dict:
    """
    목표 겹침비율(εβ)을 달성하기 위한 치폭(Face Width)을 계산합니다.

    헬리컬 기어에서 겹침비율(εβ)은 소음과 진동 성능에 중요한 영향을 미칩니다.
    이 함수는 원하는 겹침비율을 달성하기 위해 필요한 치폭을 계산합니다.

    계산 공식:
        εβ = (b × sin(β)) / (π × mn)
        따라서, b = (εβ × π × mn) / sin(β)

    Args:
        target_overlap_ratio (float): 목표 겹침비율(εβ). 일반적으로 1.0 이상 권장 (저소음: 1.2~1.5)
        helix_angle_deg (float): 헬릭스각(β) [도]. 0이 아닌 값이어야 함
        normal_module (float): 법선 모듈(mn) [mm]. 0보다 큰 값
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 계산 결과
            - 성공 시: {
                "success": True,
                "face_width": 계산된_치폭(mm),
                "inputs": {입력값_정보},
                "session_id": "세션ID"
              }
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 헬릭스각이 0에 가까우면 계산이 불가능합니다 (spur gear에는 적용 불가)
        - 겹침비율이 클수록 더 큰 치폭이 필요합니다
        - 계산된 치폭이 기어 크기에 비해 과도하게 크거나 작을 수 있으므로 검증이 필요합니다

    Example:
        # εβ = 1.3, β = 25°, mn = 2.5mm일 때 필요한 치폭 계산
        result = calculate_facewidth_for_ep_beta(1.3, 25.0, 2.5, session_id)
        # result["face_width"] ≈ 24.2mm
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
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    try:
        response = session.ipc_client.calculate_facewidth_for_ep_beta(
            target_overlap_ratio,
            helix_angle_deg,
            normal_module
        )

        if response.get("success", False):
            return {
                "success": True,
                "face_width": response.get("face_width"),
                "inputs": response.get("inputs"),
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"치폭 계산 중 오류: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def calculate_helixangle_for_ep_beta(
    target_overlap_ratio: float,
    face_width: float,
    normal_module: float,
    session_id: str
) -> dict:
    """
    목표 겹침비율(εβ)을 달성하기 위한 헬릭스각(β)을 계산합니다.

    헬리컬 기어에서 겹침비율(εβ)은 소음과 진동 성능에 중요한 영향을 미칩니다.
    이 함수는 주어진 치폭에서 원하는 겹침비율을 달성하기 위해 필요한 헬릭스각을 계산합니다.

    계산 공식:
        εβ = (b × sin(β)) / (π × mn)
        따라서, β = arcsin((εβ × π × mn) / b)

    Args:
        target_overlap_ratio (float): 목표 겹침비율(εβ). 일반적으로 1.0 이상 권장 (저소음: 1.2~1.5)
        face_width (float): 치폭(b) [mm]. 0보다 큰 값
        normal_module (float): 법선 모듈(mn) [mm]. 0보다 큰 값
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 계산 결과
            - 성공 시: {
                "success": True,
                "helix_angle_deg": 계산된_헬릭스각(도),
                "inputs": {입력값_정보},
                "session_id": "세션ID"
              }
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - sin(β)의 범위는 [-1, 1]이므로, 계산 불가능한 조합이 있을 수 있습니다
        - 치폭이 너무 작거나 목표 겹침비율이 너무 크면 계산이 불가능합니다
        - 일반적인 헬릭스각 범위는 15°~35° 입니다

    Example:
        # εβ = 1.3, b = 25mm, mn = 2.5mm일 때 필요한 헬릭스각 계산
        result = calculate_helixangle_for_ep_beta(1.3, 25.0, 2.5, session_id)
        # result["helix_angle_deg"] ≈ 23.5°
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
            "error": "초기화되지 않음. initialize() 함수를 먼저 호출하세요.",
            "session_id": session.session_id
        }

    try:
        response = session.ipc_client.calculate_helixangle_for_ep_beta(
            target_overlap_ratio,
            face_width,
            normal_module
        )

        if response.get("success", False):
            return {
                "success": True,
                "helix_angle_deg": response.get("helix_angle_deg"),
                "inputs": response.get("inputs"),
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "session_id": session.session_id
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"헬릭스각 계산 중 오류: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def save_GearDesignData(session_id: str) -> dict:
    """
    현재 기어 설계 데이터를 JSON 파일로 저장합니다.

    Args:
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 저장 결과
            - 성공 시: {"success": True, "path": "파일경로", "filename": "파일명", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 저장된 파일은 세션의 출력 디렉토리에 위치합니다
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

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gear_design_data_{timestamp}.json"
        output_file = os.path.join(session.output_dir, filename)

        # 현재 변경된 데이터를 JSON 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(session.changed_data, f, ensure_ascii=False, indent=4)

        # 생성된 파일을 세션에 추가
        session.add_file(output_file, "data")

        return {
            "success": True,
            "path": output_file,
            "filename": filename,
            "size": os.path.getsize(output_file),
            "session_id": session.session_id,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"파일 저장 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }


@mcp.tool()
def load_GearDesignData(file_path: str, session_id: str) -> dict:
    """
    JSON 파일에서 기어 설계 데이터를 불러와 현재 세션에 적용합니다.

    Args:
        file_path (str): 불러올 JSON 파일의 경로
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수).

    Returns:
        dict: 불러오기 결과
            - 성공 시: {"success": True, "message": "데이터가 성공적으로 로드되었습니다", "session_id": "세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 초기화가 완료되어야 합니다
        - 파일 경로는 서버에서 접근 가능한 위치여야 합니다
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

    if not os.path.isfile(file_path):
        return {
            "success": False,
            "error": f"파일을 찾을 수 없음: {file_path}",
            "session_id": session.session_id
        }

    try:
        # JSON 파일에서 데이터 로드
        with open(file_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        # 데이터 검증 및 로드
        response = session.ipc_client.load_and_validate_config(loaded_data)

        if response.get("success", False):
            session.changed_data = loaded_data  # 세션 데이터 업데이트
            return {
                "success": True,
                "message": "데이터가 성공적으로 로드되었습니다",
                "session_id": session.session_id
            }
        else:
            return {
                "success": False,
                "error": f"데이터 검증 실패: {response.get('error', 'Unknown error')}",
                "session_id": session.session_id
            }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 파싱 오류: {str(e)}",
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

        # IPC 프로세스 정리
        session.cleanup_ipc()

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
   
    print("Starting MCP server (IPC mode)...")
    print(f"GearDesign.exe 경로: {gear_design_exe_path}")
    print(f"세션 타임아웃: {SESSION_TIMEOUT}초")
    print("백그라운드 세션 정리 스레드 시작됨")

    # 진행 상황 콜백 함수 정의
    def on_progress(message, percentage):
        print(f"  📊 진행: [{percentage:3d}%] {message}")

    # # ============================================================
    # # SimpleSizing 전체 워크플로우 테스트
    # # ============================================================

    # print("\n" + "="*60)
    # print("SimpleSizing 워크플로우 테스트 시작")
    # print("="*60)

    # # 1. 세션 초기화
    # print("\n[1/8] 세션 초기화...")
    # result = initialize()

    # if not result.get("success"):
    #     print(f"❌ 초기화 실패: {result.get('error')}")
    #     exit(1)

    # session_id = result["session_id"]
    # print(f"✅ 세션 생성 완료: {session_id}")

    # # 진행 상황 콜백 등록
    # session = get_session(session_id)
    # session.ipc_client.progress_callback = on_progress

    # # 2. 기본 데이터 설정 (기어비, 작동조건 등)
    # print("\n[2/8] 기본 기어 데이터 설정...")
    # modify_result = modify_gear_data(
    #     "기어비 3, 입력 토크 100 Nm, 입력 회전수 1500 rpm으로 설정해줘",
    #     session_id
    # )
    # if modify_result.get("success"):
    #     print(f"✅ 데이터 설정 완료")
    #     print(f"   변경사항: {modify_result.get('change_summary', 'N/A')}")
    # else:
    #     print(f"❌ 데이터 설정 실패: {modify_result.get('error')}")

    # # 3. SimpleSizing 실행
    # print("\n[3/8] SimpleSizing 실행 중...")
    # simplesizing_result = simple_sizing_gearpair(
    #     "기어비 3, 저소음 설계를 원해. 모듈은 2~4 사이로 찾아줘. 치폭은 30mm로 해줘.",
    #     session_id
    # )

    # if not simplesizing_result.get("success"):
    #     print(f"❌ SimpleSizing 실패: {simplesizing_result.get('error')}")
    #     exit(1)

    # print(f"✅ SimpleSizing 완료")
    # print(f"   생성된 케이스 수: {simplesizing_result.get('result_rows', 0)}")

    # # 4. SimpleSizing 결과 조회
    # print("\n[4/8] SimpleSizing 결과 조회...")
    # sizing_results = get_simplesizing_results(session_id, return_all=False, top_n=10)
    # print(sizing_results)
    # if not sizing_results.get("success"):
    #     print(f"❌ 결과 조회 실패: {sizing_results.get('error')}")
    #     exit(1)

    # results_df = sizing_results.get("results", [])
    # print(f"✅ 결과 조회 완료: {len(results_df)}개 케이스")

    # # 결과 표시 (상위 5개, Rank 1 우선)
    # print("\n   [SimpleSizing 결과 - Rank 기준 정렬, PPTE 오름차순]")
    # print("   " + "-"*80)
    # if len(results_df) > 0:
    #     import pandas as pd
    #     df = pd.DataFrame(results_df)
    #     # Rank 1차, PPTE 2차 정렬 (올바른 컬럼명 사용)
    #     df_sorted = df.sort_values(['Rank', 'max. PPTE (μm)'], ascending=[True, True])
    #     print(df_sorted[['Rank', 'm_n [mm]', 'z1', 'z2', 'max. PPTE (μm)', 'total mass (kg)', 'efficiency (%)']].head(5).to_string(index=True))
    #     print("   " + "-"*80)

    #     # 5. 첫 번째 케이스 적용 (Rank 1 중 PPTE 최소)
    #     # df_sorted의 첫 번째 행의 원본 인덱스 사용
    #     selected_original_index = df_sorted.index[0]  # 정렬된 DataFrame의 첫 번째 행의 원본 인덱스
    #     print(f"\n[5/8] SimpleSizing 케이스 적용 (원본 index={selected_original_index})...")
    #     print(f"   선택된 케이스: Rank={df_sorted.iloc[0]['Rank']}, "
    #           f"Module={df_sorted.iloc[0]['m_n [mm]']}, "
    #           f"z1={int(df_sorted.iloc[0]['z1'])}, "
    #           f"z2={int(df_sorted.iloc[0]['z2'])}, "
    #           f"PPTE={df_sorted.iloc[0]['max. PPTE (μm)']:.4f} μm")

    #     apply_result = apply_simplesizing_case(selected_original_index, session_id)

    #     if not apply_result.get("success"):
    #         print(f"❌ 케이스 적용 실패: {apply_result.get('error')}")
    #         exit(1)

    #     print(f"✅ 케이스 적용 완료")
    #     print(f"   메시지: {apply_result.get('message')}")
    # else:
    #     print("   결과 없음")
    #     exit(1)

    # # 6. Geometry 계산
    # print("\n[6/8] Geometry 계산 중...")
    # geo_result = calc_geometry(session_id)

    # if not geo_result.get("success"):
    #     print(f"❌ Geometry 계산 실패: {geo_result.get('error')}")
    #     exit(1)

    # print(f"✅ Geometry 계산 완료")

    # # 7. Load Case 계산
    # print("\n[7/8] Load Case 계산 중...")
    # calc_result = calc_load_case(session_id)

    # if not calc_result.get("success"):
    #     print(f"❌ Load Case 계산 실패: {calc_result.get('error')}")
    #     exit(1)

    # print(f"✅ Load Case 계산 완료")
    # if calc_result.get("messages"):
    #     print(f"   메시지: {calc_result['messages'][:200]}...")

    # # 8. 최종 결과 요약
    # print("\n[8/8] 최종 결과 요약 조회...")
    # summary = get_allresults_summary(session_id)

    # if not summary.get("success"):
    #     print(f"❌ 결과 요약 실패: {summary.get('error')}")
    #     exit(1)

    # print(f"✅ 결과 요약 완료")
    # summary_data = summary.get("summary", {})
    # print("\n   [최종 계산 결과]")
    # print("   " + "-"*80)
    # for key, value in list(summary_data.items())[:10]:
    #     print(f"   {key}: {value}")
    # print("   " + "-"*80)

    # print("\n" + "="*60)
    # print("SimpleSizing 워크플로우 테스트 완료! ✅")
    # print("="*60)

    # 기존 워크플로우 테스트는 주석 처리
    # responce = modify_gear_data("기어1의 잇수를 20에서 30으로 변경하고, 모듈을 2.5로 설정해줘", session_id)
    # load = load_GearDesignData(r":\SW\GearDesign\GearDesign\Example\Ex3-Three gear.GD1", session_id)
    # geo_result2 = get_geometry_results(session_id)
    # message = get_messages(session_id)
    # image2d = get_2D_image(session_id)
    # image3d = get_3d_image(session_id)
    # model3d = get_3d_modeling(session_id)
    # report = get_gear_report(session_id)
    # save_data = save_GearDesignData(session_id)

    asyncio.run(mcp.run())
