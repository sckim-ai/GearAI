# from clr_loader import get_netfx
# from pythonnet import load

# # config 파일을 명시적으로 지정
# runtime = get_netfx(
#     config_file=r"D:\SW\Streamlit\.venv\Scripts\python.exe.config"
# )
# load(runtime=runtime)

import clr
import mastapy as mp

mp.init(r'C:\Program Files\SMT\MASTA 14.1.1')

from mastapy.system_model import Design    
print("MASTA 모듈 임포트 성공")