# -*- coding: utf-8 -*-
"""
MASTA .NET 런타임 충돌 해결을 위한 종합 스크립트
"""
import sys
import os
import subprocess
import shutil
from pathlib import Path

def create_comprehensive_config():
    """포괄적인 config 파일 생성"""
    print("=== 포괄적인 .NET 설정 파일 생성 ===")

    # 더 강력한 .NET 설정
    config_content = """<?xml version="1.0"?>
<configuration>
  <startup>
    <supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.0"/>
    <supportedRuntime version="v2.0.50727"/>
  </startup>
  <runtime>
    <useLegacyV2RuntimeActivationPolicy enabled="true"/>
    <loadFromRemoteSources enabled="true"/>
    <NetFx40_LegacySecurityPolicy enabled="true"/>
    <assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1">
      <probing privatePath="bin;lib"/>
    </assemblyBinding>
  </runtime>
  <appSettings>
    <add key="COMPLUS_UseLegacyJit" value="1"/>
    <add key="COMPLUS_Version" value="v4.0.30319"/>
    <add key="DOTNET_LEGACYJIT" value="1"/>
  </appSettings>
</configuration>"""

    created_files = []

    try:
        # 1. 현재 디렉토리에 app.config
        app_config_path = "app.config"
        with open(app_config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        created_files.append(app_config_path)
        print(f"[OK] {app_config_path} 생성")

        # 2. Python 실행 파일과 같은 이름의 config
        python_exe = sys.executable
        python_config_path = python_exe + ".config"

        try:
            with open(python_config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            created_files.append(python_config_path)
            print(f"[OK] {python_config_path} 생성")
        except PermissionError:
            print(f"[WARNING] 권한 부족: {python_config_path}")

        # 3. 현재 스크립트 이름.exe.config
        current_script = sys.argv[0]
        if current_script.endswith('.py'):
            script_config = current_script.replace('.py', '.exe.config')
            with open(script_config, 'w', encoding='utf-8') as f:
                f.write(config_content)
            created_files.append(script_config)
            print(f"[OK] {script_config} 생성")

        return created_files

    except Exception as e:
        print(f"[ERROR] 설정 파일 생성 실패: {e}")
        return created_files

def set_environment_variables():
    """환경 변수 설정"""
    print("=== 환경 변수 설정 ===")

    env_vars = {
        "COMPLUS_UseLegacyJit": "1",
        "COMPLUS_Version": "v4.0.30319",
        "DOTNET_LEGACYJIT": "1",
        "COMPlus_legacyCorruptedStateExceptionsPolicy": "1",
        "PYTHONNET_SHUTDOWN_MODE": "Normal"
    }

    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"[OK] {key} = {value}")

def test_masta_with_fresh_process():
    """완전히 새로운 프로세스에서 MASTA 테스트"""
    print("=== 새로운 프로세스에서 MASTA 테스트 ===")

    # 새 프로세스용 테스트 스크립트
    test_script = '''
import sys
import os

# 환경 변수 설정
os.environ["COMPLUS_UseLegacyJit"] = "1"
os.environ["COMPLUS_Version"] = "v4.0.30319"
os.environ["DOTNET_LEGACYJIT"] = "1"
os.environ["COMPlus_legacyCorruptedStateExceptionsPolicy"] = "1"
os.environ["PYTHONNET_SHUTDOWN_MODE"] = "Normal"

def test_clean_masta():
    try:
        print("=== 깨끗한 프로세스에서 MASTA 테스트 ===")

        # pythonnet 임포트 전에 설정
        import pythonnet
        print("[OK] pythonnet 임포트 성공")

        # .NET Framework 명시적 로드
        try:
            pythonnet.load("netfx")
            print("[OK] .NET Framework 런타임 로드 성공")
        except Exception as e:
            print(f"[WARNING] .NET Framework 로드 실패: {e}")
            try:
                pythonnet.load("coreclr")
                print("[OK] .NET Core 런타임 로드 성공")
            except Exception as e2:
                print(f"[ERROR] 모든 런타임 로드 실패: {e2}")
                return False

        # MASTA 임포트
        import mastapy
        from mastapy import init
        print("[OK] mastapy 임포트 성공")

        # MASTA 초기화
        masta_path = r"C:\\Program Files\\SMT\\MASTA 14.1.1"
        init(masta_path)
        print("[SUCCESS] MASTA 초기화 성공!")

        # Design 객체 생성 테스트
        from mastapy.system_model import Design
        design = Design()
        assembly = design.root_assembly
        print("[SUCCESS] Design 및 Assembly 객체 생성 성공!")

        return True

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    success = test_clean_masta()
    sys.exit(0 if success else 1)
'''

    # 임시 스크립트 생성
    temp_script = "temp_clean_masta_test.py"
    try:
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(test_script)

        # 새 프로세스 실행
        print("새로운 Python 프로세스 시작...")
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd()
        )

        print("=== 새 프로세스 실행 결과 ===")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        success = result.returncode == 0
        print(f"=== 결과: {'성공' if success else '실패'} (exit code: {result.returncode}) ===")

        return success

    except subprocess.TimeoutExpired:
        print("[ERROR] 프로세스 실행 타임아웃 (60초)")
        return False
    except Exception as e:
        print(f"[ERROR] 프로세스 실행 중 오류: {e}")
        return False
    finally:
        # 임시 파일 정리
        if os.path.exists(temp_script):
            os.remove(temp_script)

def main():
    """메인 함수"""
    print("MASTA .NET 런타임 충돌 종합 해결 스크립트")
    print("=" * 50)

    # 1. 설정 파일 생성
    created_files = create_comprehensive_config()

    # 2. 환경 변수 설정
    set_environment_variables()

    # 3. 새 프로세스에서 테스트
    success = test_masta_with_fresh_process()

    if success:
        print("\n[SUCCESS] MASTA .NET 런타임 충돌 해결 완료!")
        print("생성된 설정 파일들:")
        for file in created_files:
            print(f"  - {file}")
    else:
        print("\n[ERROR] MASTA 초기화 여전히 실패")
        print("\n=== 추가 해결 방안 ===")
        print("1. 관리자 권한으로 실행")
        print("2. Python 버전 다운그레이드 (3.8-3.10)")
        print("3. .NET Framework 4.8 재설치")
        print("4. Visual C++ Redistributable 2019-2022 설치")
        print("5. MASTA 최신 버전으로 업데이트")

if __name__ == "__main__":
    main()