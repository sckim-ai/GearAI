import subprocess
import json
from typing import Optional, Dict, Any
from pathlib import Path



class GearDesignIPC:
    """GearDesign과 프로세스 간 통신(IPC)을 담당하는 클래스"""
    
    def __init__(self, exe_path: str):
        """
        Args:
            exe_path: GearDesign.exe 실행 파일 경로
        """
        self.exe_path = Path(exe_path)
        self.process: Optional[subprocess.Popen] = None
        
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
                bufsize=1,
                cwd=str(self.exe_path.parent.absolute())
            )
            print(f"프로세스 시작 (PID: {self.process.pid})")
            
            # stderr 읽기 (디버그 메시지 확인)
            import time
            time.sleep(1)
            
            # 프로세스 상태 확인
            if self.process.poll() is not None:
                stderr_output = self.process.stderr.read()
                stdout_output = self.process.stdout.read()
                print(f"프로세스 종료됨")
                print(f"STDERR: {stderr_output}")
                print(f"STDOUT: {stdout_output}")
                return False
            
            print("IPC 모드 대기 중...")
            return True
            
        except Exception as e:
            print(f"프로세스 시작 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """명령을 전송하고 응답 받기"""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("GearDesign 프로세스가 실행 중이지 않습니다")
        
        # 명령 전송
        command_str = json.dumps(command) + "\n"
        self.process.stdin.write(command_str)
        self.process.stdin.flush()
        
        # 응답 받기
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("프로세스로부터 응답이 없습니다")
        
        return json.loads(response_line)
    
    def load_config(self, config_data: Dict[str, Any]) -> bool:
        """설정 데이터 로드"""
        command = {
            "action": "load_and_validate_config",
            "config": config_data
        }
        response = self._send_command(command)
        return response.get("success", False)
    
    def calculate(self) -> bool:
        """기하학적 계산 및 하중 계산 수행"""
        command = {"action": "calculate"}
        response = self._send_command(command)
        return response.get("success", False)
    
    def save_3d_modeling(self, path: str) -> bool:
        """3D 모델링 저장"""
        command = {
            "action": "save_3d_modeling",
            "path": path
        }
        response = self._send_command(command)
        
        if not response.get("success", False):
            error = response.get("error", "Unknown error")
            print(f"3D 모델링 저장 실패: {error}")
        
        return response.get("success", False)
    
    def save_3d_image(self, path: str, width: int = 800, height: int = 600) -> bool:
        """3D 이미지 저장"""
        command = {
            "action": "save_3d_image",
            "path": path,
            "width": width,
            "height": height
        }
        response = self._send_command(command)
        return response.get("success", False)
    
    def save_report(self, path: str, config_data: Dict[str, Any]) -> bool:
        """보고서 저장"""
        command = {
            "action": "save_report",
            "path": path,
            "config": config_data
        }
        response = self._send_command(command)
        return response.get("success", False)
    
    def stop(self):
        """프로세스 종료"""
        if self.process:
            self.process.stdin.close()
            self.process.wait(timeout=5)
            print("GearDesign IPC 프로세스 종료됨")
    
    def __enter__(self):
        """컨텍스트 매니저 진입"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.stop()


# 사용 예시
if __name__ == "__main__":
    exe_path = r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows\GearDesign.exe"
    
    with GearDesignIPC(exe_path) as ipc:
        # 설정 로드
        config = {
            "module": 2.5,
            "teeth": 20,
            # ... 기타 설정
        }
        ipc.load_config(config)
        
        # 계산
        ipc.calculate()
        
        # 3D 모델링 저장
        success = ipc.save_3d_modeling("output.step")
        print(f"저장 결과: {success}")