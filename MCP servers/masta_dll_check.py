# -*- coding: utf-8 -*-
"""
MASTA DLL 파일 확인 및 SMT.Utility.dll 문제 해결 스크립트
"""
import sys
import os
import subprocess
from pathlib import Path

def check_masta_installation():
    """MASTA 설치 및 DLL 파일 확인"""
    print("=== MASTA 설치 및 DLL 파일 확인 ===")

    masta_path = r"C:\Program Files\SMT\MASTA 14.1.1"

    if not os.path.exists(masta_path):
        print(f"[ERROR] MASTA 설치 경로가 없습니다: {masta_path}")
        return False

    print(f"[OK] MASTA 설치 경로 확인: {masta_path}")

    # 중요한 DLL 파일들 확인
    required_dlls = [
        "SMT.Utility.dll",
        "Utility.dll",
        "SMT.MastaAPI.dll",
        "MastaAPI.dll",
        "SMT.MastaAPI.UtilityMethods.dll"
    ]

    found_dlls = []
    missing_dlls = []

    for dll in required_dlls:
        dll_path = os.path.join(masta_path, dll)
        if os.path.exists(dll_path):
            found_dlls.append(dll)
            print(f"[OK] {dll} 발견")
        else:
            missing_dlls.append(dll)
            print(f"[MISSING] {dll} 없음")

    # 실제 DLL 파일 목록 확인
    print("\n=== MASTA 디렉토리 DLL 파일 목록 ===")
    try:
        dll_files = [f for f in os.listdir(masta_path) if f.endswith('.dll')]
        for dll in sorted(dll_files):
            print(f"  - {dll}")
    except Exception as e:
        print(f"[ERROR] 디렉토리 읽기 실패: {e}")

    return len(found_dlls) > 0

def test_masta_with_dll_fix():
    """SMT.Utility.dll 문제 해결 후 MASTA 테스트"""
    print("=== SMT.Utility.dll 문제 해결 후 MASTA 테스트 ===")

    # 새 프로세스용 테스트 스크립트 (DLL 경로 추가)
    test_script = '''
import sys
import os
from pathlib import Path

# 환경 변수 설정
os.environ["COMPLUS_UseLegacyJit"] = "1"
os.environ["COMPLUS_Version"] = "v4.0.30319"
os.environ["DOTNET_LEGACYJIT"] = "1"
os.environ["COMPlus_legacyCorruptedStateExceptionsPolicy"] = "1"
os.environ["PYTHONNET_SHUTDOWN_MODE"] = "Normal"

def test_masta_with_path_fix():
    try:
        print("=== SMT.Utility.dll 경로 수정 후 MASTA 테스트 ===")

        # MASTA 경로를 PATH에 추가
        masta_path = r"C:\\Program Files\\SMT\\MASTA 14.1.1"
        current_path = os.environ.get("PATH", "")
        if masta_path not in current_path:
            os.environ["PATH"] = masta_path + ";" + current_path
            print(f"[OK] MASTA 경로를 PATH에 추가: {masta_path}")

        # Python path에도 추가
        if masta_path not in sys.path:
            sys.path.insert(0, masta_path)
            print(f"[OK] MASTA 경로를 sys.path에 추가: {masta_path}")

        # pythonnet 임포트 및 설정
        import pythonnet
        print("[OK] pythonnet 임포트 성공")

        # .NET Framework 로드
        try:
            pythonnet.load("netfx")
            print("[OK] .NET Framework 런타임 로드 성공")
        except Exception as e:
            print(f"[WARNING] .NET Framework 로드 실패: {e}")

        # CLR 참조 추가 (SMT.Utility.dll 직접 로드 시도)
        try:
            import clr
            print("[OK] CLR 임포트 성공")

            # MASTA DLL 파일들을 CLR에 추가
            dll_files = [
                "SMT.Utility.dll",
                "SMT.MastaAPI.dll",
                "MastaAPI.dll"
            ]

            for dll in dll_files:
                dll_full_path = os.path.join(masta_path, dll)
                if os.path.exists(dll_full_path):
                    try:
                        clr.AddReference(dll_full_path)
                        print(f"[OK] {dll} CLR에 추가 성공")
                    except Exception as e:
                        print(f"[WARNING] {dll} CLR 추가 실패: {e}")
                        # dll 이름만으로 시도
                        try:
                            clr.AddReference(dll.replace('.dll', ''))
                            print(f"[OK] {dll} 이름으로 CLR에 추가 성공")
                        except Exception as e2:
                            print(f"[ERROR] {dll} 완전 실패: {e2}")

        except Exception as e:
            print(f"[ERROR] CLR 설정 실패: {e}")

        # MASTA 임포트 및 초기화
        print("\\n=== MASTA 임포트 및 초기화 ===")
        import mastapy
        from mastapy import init
        print("[OK] mastapy 임포트 성공")

        # 초기화 시도
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
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_masta_with_path_fix()
    sys.exit(0 if success else 1)
'''

    # 임시 스크립트 생성 및 실행
    temp_script = "temp_dll_fix_test.py"
    try:
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(test_script)

        print("새로운 Python 프로세스에서 DLL 경로 수정 테스트...")
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd()
        )

        print("=== DLL 수정 테스트 결과 ===")
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
        if os.path.exists(temp_script):
            os.remove(temp_script)

def main():
    """메인 함수"""
    print("MASTA SMT.Utility.dll 문제 해결 스크립트")
    print("=" * 50)

    # 1. MASTA 설치 및 DLL 확인
    if not check_masta_installation():
        print("[ERROR] MASTA 설치 확인 실패")
        return

    # 2. DLL 경로 수정 후 테스트
    success = test_masta_with_dll_fix()

    if success:
        print("\\n[SUCCESS] SMT.Utility.dll 문제 해결 완료!")
    else:
        print("\\n[ERROR] SMT.Utility.dll 문제 해결 실패")
        print("\\n=== 추가 해결 방안 ===")
        print("1. 관리자 권한으로 실행")
        print("2. MASTA 설치 재확인")
        print("3. DLL 파일 차단 해제 (속성 → 차단 해제)")
        print("4. Windows Defender 예외 추가")

if __name__ == "__main__":
    main()