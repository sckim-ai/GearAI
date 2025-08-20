import streamlit as st
from services.agent_service import AgentService
import asyncio
import nest_asyncio
import os
import time

# 1. Streamlit 초기화
# asyncio 중첩 실행 허용
nest_asyncio.apply()

# 페이지 설정
st.set_page_config(page_title="AI Agent Chat", layout="wide")

# Session state 설정 (사용할 변수 선언과 유사, dict 형태로 사용)
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_settings" not in st.session_state:
    st.session_state.agent_settings = {}

# 2. 에이전트 서비스 초기화 - 캐시 방지를 위해 수정
@st.cache_resource
def get_cached_agent_service():
    return AgentService()

# 설정이 변경되었을 때만 새로 생성
def get_agent_service():
    # 설정 변경 감지
    current_settings = st.session_state.get('agent_settings', {})
    
    if 'last_settings' not in st.session_state or \
       st.session_state.last_settings != current_settings:
        
        # 설정이 변경되었으면 캐시 무효화
        get_cached_agent_service.clear()
        st.session_state.last_settings = current_settings.copy()
    
    return get_cached_agent_service()

# 캐시를 피하기 위한 타임스탬프 추가
agent_service = get_agent_service()



# 사이드바 설정
st.sidebar.title("🔧 설정")
agent_type = st.sidebar.selectbox(
    "AI Agent 선택",
    agent_service.get_available_agents()
)

# 에이전트 설정 표시
agent_config = agent_service.get_agent_config(agent_type)
if agent_config:
    st.sidebar.subheader("에이전트 설정")
    # 에이전트 타입에 따른 설정 초기화
    if agent_type not in st.session_state.agent_settings:
        st.session_state.agent_settings[agent_type] = agent_config.copy()
    
    updated_config = {}
    
    # GPT 에이전트 설정
    if agent_type == "Single LLM":
        # 모델 선택
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"]
        selected_model = st.sidebar.selectbox(
            "모델 선택",
            models,
            index=models.index(st.session_state.agent_settings[agent_type].get("model", "gpt-4o-mini"))
            if st.session_state.agent_settings[agent_type].get("model") in models else 0
        )
        updated_config["model"] = selected_model

        # 온도(temperature) 설정
        selected_temp = st.sidebar.slider(
            "온도(Temperature)", 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.agent_settings[agent_type].get("temperature", 0.7),
            step=0.1
        )

        if selected_model == "o4-mini":
            selected_temp = 1.0 # o4-mini는 온도 1.0 고정   
        
        updated_config["temperature"] = selected_temp
        
    # Chain 에이전트 설정
    elif agent_type == "chain":
        # 모델 선택
        models = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"]
        selected_model = st.sidebar.selectbox(
            "모델 선택",
            models,
            index=models.index(st.session_state.agent_settings[agent_type].get("model", "gpt-4o-mini"))
            if st.session_state.agent_settings[agent_type].get("model") in models else 0
        )
        updated_config["model"] = selected_model
        # 체인 길이 설정
        selected_length = st.sidebar.slider(
            "체인 길이", 
            min_value=1, 
            max_value=5, 
            value=st.session_state.agent_settings[agent_type].get("chain_length", 3),
            step=1
        )
        updated_config["chain_length"] = selected_length
    
    # 설정 업데이트
    st.session_state.agent_settings[agent_type].update(updated_config)
    
    agent_service.agents[agent_type].update_config(st.session_state.agent_settings[agent_type])
    
# 메인 채팅 인터페이스
st.title("AI Agent Chat")

# 기존 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if user_input := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    # 에이전트 응답 처리
    try:
        # 어시스턴트 메시지 컨테이너 생성
        with st.chat_message("assistant"):
            # 응답 컨테이너 생성
            response_placeholder = st.empty()
            
            # 스피너와 응답 표시
            with st.spinner("AI가 응답을 생성하고 있습니다..."):
                # 현재 설정 가져오기
                current_config = st.session_state.agent_settings[agent_type]
                
                try:
                    # 결과를 누적할 변수를 리스트로 변경 (파이썬에서 리스트는 가변객체라 nonlocal 없이도 변경 가능)
                    response_parts = []
                    
                    # 콜백 함수 정의
                    def update_response(chunk):
                        response_parts.append(chunk)
                        # 현재까지의 전체 응답 표시
                        response_placeholder.markdown("".join(response_parts))
                    
                    # 비동기 함수를 동기적으로 실행
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(
                        agent_service.process_with_callback(
                            agent_type, 
                            user_input, 
                            update_response
                        )
                    )
                    
                    # 최종 응답 조합
                    response_text = "".join(response_parts)
                    
                except Exception as e:
                    st.error(f"처리 중 오류 발생: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
                    response_text = f"오류가 발생했습니다: {str(e)}"
            
            # 최종 응답을 세션 상태에 추가
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )
        
    except Exception as e:
        st.error(f"에러 발생: {str(e)}") 