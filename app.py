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
st.set_page_config(page_title="Gear AI Agent Chat", layout="wide")

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
st.sidebar.subheader("에이전트 설정")
agent_type = st.sidebar.selectbox(
    "에이전트 선택",
    agent_service.get_available_agents()
)

# 에이전트 설정 표시
agent_config = agent_service.get_agent_config(agent_type)
if agent_config:
    st.sidebar.subheader("LLM 모델 설정")
    # 에이전트 타입에 따른 설정 초기화
    if agent_type not in st.session_state.agent_settings:
        st.session_state.agent_settings[agent_type] = agent_config.copy()
    
    updated_config = {}
    
    # Chat 에이전트 설정
    if agent_type == "Chatbot":
        # 프로바이더 선택
        providers = {
            "OpenAI": "openai",
            "Anthropic": "anthropic", 
            "Google": "google"
        }
        
        selected_provider_name = st.sidebar.selectbox(
            "LLM 프로바이더",
            list(providers.keys()),
            index=list(providers.values()).index(
                st.session_state.agent_settings[agent_type].get("provider", "openai")
            ) if st.session_state.agent_settings[agent_type].get("provider") in providers.values() else 0
        )
        selected_provider = providers[selected_provider_name]
        updated_config["provider"] = selected_provider
        
        # 프로바이더별 모델 선택
        if selected_provider == "openai":
            models = ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini"]
        elif selected_provider == "anthropic":
            models = ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]
        elif selected_provider == "google":
            models = ["gemini-2.5-pro", "gemini-2.5-flash"]
        else:
            models = ["gpt-5"]  # 기본값
            
        selected_model = st.sidebar.selectbox(
            "모델 선택",
            models,
            index=models.index(st.session_state.agent_settings[agent_type].get("model", models[0]))
            if st.session_state.agent_settings[agent_type].get("model") in models else 0
        )
        updated_config["model"] = selected_model

        # 온도(temperature) 설정
        selected_temp = st.sidebar.slider(
            "온도(Temperature)", 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.agent_settings[agent_type].get("temperature", 0.0),
            step=0.1
        )

        # # o1 모델들은 온도 설정이 고정됨
        # if "o1" in selected_model:
        #     selected_temp = 1.0
        #     st.sidebar.info("o1 모델은 온도가 1.0으로 고정됩니다.")
        
        updated_config["temperature"] = selected_temp
        
        # API 키 상태 표시
        st.sidebar.subheader("API 키 상태")
        if selected_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            st.sidebar.write("🔑 OpenAI:", "✅ 설정됨" if api_key else "❌ 미설정")
        elif selected_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY") 
            st.sidebar.write("🔑 Anthropic:", "✅ 설정됨" if api_key else "❌ 미설정")
        elif selected_provider == "google":
            api_key = os.getenv("GEMINI_API_KEY")
            st.sidebar.write("🔑 Google:", "✅ 설정됨" if api_key else "❌ 미설정")
            
    
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