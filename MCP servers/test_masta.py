# MASTA 초기화
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
    print(f"MASTA 모듈 임포트 실패: {e}")
    print("MASTA가 설치되어 있는지 확인하세요.")