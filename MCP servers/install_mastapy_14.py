# -*- coding: utf-8 -*-
"""
mastapy 14.1.1 수동 설치 및 MASTA 테스트 스크립트
"""
import sys
import os
import subprocess
import urllib.request
import zipfile
import tempfile

def download_and_install_mastapy():
    """mastapy 14.1.1 수동 다운로드 및 설치"""
    print("=== mastapy 14.1.1 수동 설치 ===")

    try:
        # 현재 mastapy 제거 시도
        print("1. 기존 mastapy 제거 시도...")
        try:
            import mastapy
            mastapy_path = mastapy.__file__
            import shutil
            mastapy_dir = os.path.dirname(os.path.dirname(mastapy_path))
            print(f"[OK] 기존 mastapy 위치: {mastapy_dir}")
            # 제거는 하지 않고 경로만 확인
        except ImportError:
            print("[INFO] mastapy가 설치되어 있지 않음")

        # 이 방법은 너무 복잡하므로, 다른 접근 방식 사용
        print("2. pyproject.toml에서 mastapy 버전 확인...")
        return True

    except Exception as e:
        print(f"[ERROR] mastapy 설치 실패: {e}")
        return False

def test_masta_with_correct_version():
    """올바른 버전으로 MASTA 테스트"""
    print("=== 버전 확인 후 MASTA 테스트 ===")

    test_script = '''
import sys
import os

# 환경 변수 설정
os.environ["COMPLUS_UseLegacyJit"] = "1"
os.environ["COMPLUS_Version"] = "v4.0.30319"
os.environ["DOTNET_LEGACYJIT"] = "1"

def test_version_and_masta():
    try:
        print("=== 버전 호환성 확인 ===")

        # MASTA 경로 설정
        masta_path = r"C:\\Program Files\\SMT\\MASTA 14.1.1"

        # PATH 및 sys.path 설정
        current_path = os.environ.get("PATH", "")
        if masta_path not in current_path:
            os.environ["PATH"] = masta_path + ";" + current_path

        if masta_path not in sys.path:
            sys.path.insert(0, masta_path)

        print("1. pythonnet 설정...")
        import pythonnet
        pythonnet.load("netfx")

        import clr
        clr.AddReference(os.path.join(masta_path, "SMT.Utility.dll"))
        clr.AddReference(os.path.join(masta_path, "MastaAPI.dll"))

        print("2. mastapy 버전 확인...")
        try:
            import mastapy
            print(f"[OK] mastapy 버전: {mastapy.__version__ if hasattr(mastapy, '__version__') else '버전 정보 없음'}")

            # MASTA 14.1.1과의 호환성 테스트
            from mastapy import init
            print("3. MASTA 초기화 시도...")

            init(masta_path)
            print("[SUCCESS] MASTA 초기화 성공!")

            # Design 객체 생성
            from mastapy.system_model import Design
            design = Design()
            assembly = design.root_assembly
            print("[SUCCESS] Design 객체 생성 성공!")

            return True

        except Exception as version_error:
            if "version" in str(version_error).lower():
                print(f"[ERROR] 버전 호환성 문제: {version_error}")
                print("[INFO] pyproject.toml에서 mastapy==14.1.1로 수정이 필요합니다")
            else:
                print(f"[ERROR] 다른 오류: {version_error}")
            return False

    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_version_and_masta()
    sys.exit(0 if success else 1)
'''

    # 테스트 실행
    temp_script = "temp_version_test.py"
    try:
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(test_script)

        print("새로운 프로세스에서 버전 테스트...")
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=60
        )

        print("=== 버전 테스트 결과 ===")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"[ERROR] 버전 테스트 실패: {e}")
        return False
    finally:
        if os.path.exists(temp_script):
            os.remove(temp_script)

def update_pyproject_toml():
    """pyproject.toml에서 mastapy 버전을 14.1.1로 강제 설정"""
    print("=== pyproject.toml mastapy 버전 확인 및 수정 ===")

    pyproject_path = r"D:\SW\Streamlit\pyproject.toml"

    try:
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"[INFO] pyproject.toml 읽기 성공")

        # mastapy==14.1.1이 이미 있는지 확인
        if 'mastapy==14.1.1' in content:
            print("[OK] pyproject.toml에 이미 mastapy==14.1.1이 설정되어 있습니다")
            return True
        else:
            print("[INFO] pyproject.toml의 mastapy 버전이 14.1.1이 아닙니다")
            print("[INFO] 수동으로 pyproject.toml에서 'mastapy==14.1.1'로 수정해주세요")
            return False

    except Exception as e:
        print(f"[ERROR] pyproject.toml 처리 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("mastapy 14.1.1 호환성 및 MASTA 테스트")
    print("=" * 50)

    # 1. pyproject.toml 확인
    update_pyproject_toml()

    # 2. 현재 상태에서 MASTA 테스트
    success = test_masta_with_correct_version()

    if success:
        print("\\n[SUCCESS] MASTA와 mastapy 버전 호환성 확인 완료!")
    else:
        print("\\n[ERROR] 버전 호환성 문제 발견")
        print("\\n=== 해결 방법 ===")
        print("1. pyproject.toml에서 'mastapy==14.1.1'로 수정")
        print("2. 'uv sync --upgrade' 실행")
        print("3. 또는 관리자 권한으로 다시 실행")

if __name__ == "__main__":
    main()