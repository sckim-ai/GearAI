import streamlit as st
import re

# 수식 변환 함수
def convert_math_notation(text):
    # [수식] 형태를 $$수식$$ 형태로 변환
    text = re.sub(r'\[\s*(.*?)\s*\]', r'$$\1$$', text, flags=re.DOTALL)
    return text

st.title("LaTeX 렌더링 테스트")

# 기본 LaTeX 수식 테스트
st.header("기본 LaTeX 수식")
st.write(r"인라인 수식: $\sigma_H = Z_E \cdot \sqrt{\frac{F_t \cdot (u+1)}{b \cdot d \cdot u}}$")
st.write(r"블록 수식: $$\sigma_H = Z_E \cdot \sqrt{\frac{F_t \cdot (u+1)}{b \cdot d \cdot u}}$$")

# 사용자 입력 수식 테스트
st.header("수식 변환 테스트")
user_input = st.text_area("수식 입력 ([ ] 형태로 입력):", value="[ \\sigma_H = Z_E \\cdot \\sqrt{\\frac{F_t \\cdot (u+1)}{b \\cdot d \\cdot u}} ]")

if user_input:
    # 변환 전
    st.subheader("변환 전:")
    st.write(user_input)
    
    # 변환 후
    converted = convert_math_notation(user_input)
    st.subheader("변환 후:")
    st.write(converted)
    
    # 마크다운 렌더링
    st.subheader("마크다운 렌더링:")
    st.markdown(converted)

# 추가 테스트 옵션
st.header("다양한 렌더링 방식")
test_math = r"\sigma_H = Z_E \cdot \sqrt{\frac{F_t \cdot (u+1)}{b \cdot d \cdot u}}"

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("기본 마크다운")
    st.markdown(f"$${test_math}$$")
with col2:
    st.subheader("latex=True 옵션")
    st.latex(test_math)
with col3:
    st.subheader("직접 HTML")
    st.markdown(f"""
    <span class="katex-display">
        <span class="katex">
            {test_math}
        </span>
    </span>
    """, unsafe_allow_html=True) 