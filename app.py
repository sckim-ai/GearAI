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
    if agent_type == "Chatbot" or agent_type == "Gear Classifier":
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
    
# 메인 레이아웃 설정
col1, col2 = st.columns([2, 1])

with col1:
    # 메인 채팅 인터페이스
    st.title("AI Agent Chat")

    # 기존 대화 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 기어 선택 옵션 표시 (Gear Classifier Agent에서 not designable일 때)
    if st.session_state.get("show_gear_options", False) and not st.session_state.get("gear_selection_made", False):
        st.markdown("---")
        
        gear_options = {
            "기어 쌍 (Gear Pair)": "두 개의 기어가 맞물리는 기본 구조로 설계해 주세요",
            "3단 기어 (Three Gear)": "세 개의 기어가 연결된 구조로 설계해 주세요", 
            "단순 유성기어 (Simple Planetary)": "태양기어, 유성기어, 링기어로 구성된 유성기어로 설계해 주세요",
            "이중 피니언 유성기어 (Double Pinion Planetary)": "2단계 유성기어 시스템으로 설계해 주세요"
        }
        
        st.markdown("### 🔧 설계 가능한 기어 타입 선택")
        
        # 버튼 그리드 생성
        col1_opt, col2_opt = st.columns(2)
        
        with col1_opt:
            if st.button("🔧 기어 쌍 (Gear Pair)", key="gear_pair_btn", use_container_width=True):
                selected_option = gear_options["기어 쌍 (Gear Pair)"]
                st.session_state.messages.append({"role": "user", "content": selected_option})
                st.session_state.show_gear_options = False
                st.session_state.gear_selection_made = True
                st.session_state.process_gear_selection = selected_option
                st.rerun()
                
            if st.button("🌍 단순 유성기어 (Simple Planetary)", key="simple_planetary_btn", use_container_width=True):
                selected_option = gear_options["단순 유성기어 (Simple Planetary)"]
                st.session_state.messages.append({"role": "user", "content": selected_option})
                st.session_state.show_gear_options = False
                st.session_state.gear_selection_made = True
                st.session_state.process_gear_selection = selected_option
                st.rerun()
        
        with col2_opt:
            if st.button("⚙️ 3단 기어 (Three Gear)", key="three_gear_btn", use_container_width=True):
                selected_option = gear_options["3단 기어 (Three Gear)"]
                st.session_state.messages.append({"role": "user", "content": selected_option})
                st.session_state.show_gear_options = False
                st.session_state.gear_selection_made = True
                st.session_state.process_gear_selection = selected_option
                st.rerun()
                
            if st.button("🔄 이중 피니언 유성기어 (Double Pinion)", key="double_pinion_btn", use_container_width=True):
                selected_option = gear_options["이중 피니언 유성기어 (Double Pinion Planetary)"]
                st.session_state.messages.append({"role": "user", "content": selected_option})
                st.session_state.show_gear_options = False
                st.session_state.gear_selection_made = True
                st.session_state.process_gear_selection = selected_option
                st.rerun()
        
        # 대화 종료 옵션
        if st.button("❌ 대화 종료", key="end_conversation_btn", use_container_width=True):
            st.session_state.messages.append({"role": "assistant", "content": "대화를 종료합니다. 기어 설계가 필요하시면 언제든 다시 문의해 주세요! 😊"})
            st.session_state.show_gear_options = False
            st.session_state.gear_selection_made = True
            st.rerun()
        
        st.markdown("---")
    
    # 기어 선택 옵션 처리 (자동 응답)
    if st.session_state.get("process_gear_selection"):
        user_input = st.session_state.process_gear_selection
        st.session_state.process_gear_selection = None  # 플래그 초기화
        
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
                        # 진행 상황과 최종 응답을 분리하여 표시
                        progress_parts = []
                        response_parts = []
                        is_final_response = [False]  # 리스트로 변경하여 nonlocal 문제 해결
                        
                        # 진행 상황 표시용 컨테이너 생성
                        progress_container = st.empty()
                        
                        # 콜백 함수 정의
                        def update_response(chunk):
                            # 구분자로 최종 응답 시작점 확인
                            if "🎉 **분석 완료!**" in chunk:
                                is_final_response[0] = True
                                progress_parts.append(chunk)
                                # 진행 상황 최종 업데이트
                                progress_container.markdown("".join(progress_parts))
                                return
                            elif "---" in chunk and is_final_response[0]:
                                # 구분선 이후는 최종 응답
                                return
                            
                            if not is_final_response[0]:
                                # 진행 상황 업데이트
                                progress_parts.append(chunk)
                                progress_container.markdown("".join(progress_parts))
                            else:
                                # 최종 응답 업데이트
                                response_parts.append(chunk)
                                # 진행 상황과 최종 응답을 함께 표시
                                combined_content = "".join(progress_parts) + "\n" + "".join(response_parts)
                                response_placeholder.markdown(combined_content)
                        
                        # 비동기 함수를 동기적으로 실행
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(
                            agent_service.process_with_callback(
                                agent_type, 
                                user_input, 
                                update_response
                            )
                        )
                        
                        # 최종 응답 조합 (진행 상황 포함)
                        if response_parts:
                            response_text = "".join(response_parts)
                        else:
                            # 최종 응답이 없는 경우 진행 상황만 저장
                            response_text = "".join(progress_parts)
                        
                        # 기어 선택 옵션 플래그 확인
                        if "[SHOW_GEAR_OPTIONS]" in response_text:
                            st.session_state.show_gear_options = True
                            st.session_state.gear_selection_made = False
                            # 플래그 제거
                            response_text = response_text.replace("[SHOW_GEAR_OPTIONS]", "")
                        
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
        
        # 페이지 새로고침으로 새 메시지를 올바른 위치에 표시
        st.rerun()
    
    # 사용자 입력 처리 (중앙 컬럼 하단)
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
                        # 진행 상황과 최종 응답을 분리하여 표시
                        progress_parts = []
                        response_parts = []
                        is_final_response = [False]  # 리스트로 변경하여 nonlocal 문제 해결
                        
                        # 진행 상황 표시용 컨테이너 생성
                        progress_container = st.empty()
                        
                        # 콜백 함수 정의
                        def update_response(chunk):
                            # 구분자로 최종 응답 시작점 확인
                            if "🎉 **분석 완료!**" in chunk:
                                is_final_response[0] = True
                                progress_parts.append(chunk)
                                # 진행 상황 최종 업데이트
                                progress_container.markdown("".join(progress_parts))
                                return
                            elif "---" in chunk and is_final_response[0]:
                                # 구분선 이후는 최종 응답
                                return
                            
                            if not is_final_response[0]:
                                # 진행 상황 업데이트
                                progress_parts.append(chunk)
                                progress_container.markdown("".join(progress_parts))
                            else:
                                # 최종 응답 업데이트
                                response_parts.append(chunk)
                                # 진행 상황과 최종 응답을 함께 표시
                                combined_content = "".join(progress_parts) + "\n" + "".join(response_parts)
                                response_placeholder.markdown(combined_content)
                        
                        # 비동기 함수를 동기적으로 실행
                        loop = asyncio.get_event_loop()
                        loop.run_until_complete(
                            agent_service.process_with_callback(
                                agent_type, 
                                user_input, 
                                update_response
                            )
                        )
                        
                        # 최종 응답 조합 (진행 상황 포함)
                        if response_parts:
                            response_text = "".join(response_parts)
                        else:
                            # 최종 응답이 없는 경우 진행 상황만 저장
                            response_text = "".join(progress_parts)
                        
                        # 기어 선택 옵션 플래그 확인
                        if "[SHOW_GEAR_OPTIONS]" in response_text:
                            st.session_state.show_gear_options = True
                            st.session_state.gear_selection_made = False
                            # 플래그 제거
                            response_text = response_text.replace("[SHOW_GEAR_OPTIONS]", "")
                        
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
        
        # 페이지 새로고침으로 새 메시지를 올바른 위치에 표시
        st.rerun()

# 오른쪽 사이드바
with col2:
    st.header("🔍 워크플로우 시각화")
    
    # LangGraph가 있는 에이전트만 시각화
    if agent_type == "Gear Classifier":
        try:
            # 에이전트에서 그래프 이미지 가져오기
            selected_agent = agent_service.agents[agent_type]
            if hasattr(selected_agent, 'get_graph_image'):
                st.markdown("### 에이전트 워크플로우")
                
                # LangGraph의 그래프 이미지 시도
                try:
                    graph_image = selected_agent.get_graph_image()
                    if graph_image is not None:
                        # PIL Image이나 다른 형태의 이미지 객체를 Streamlit에서 표시
                        st.image(graph_image, caption="LangGraph 워크플로우", use_container_width=True)
                    else:
                        raise Exception("그래프 이미지 생성 실패")
                        
                except Exception as graph_error:
                    # 그래프 이미지 생성 실패 시 Mermaid fallback
                    st.warning("그래프 이미지 생성에 실패했습니다. Mermaid 다이어그램을 표시합니다.")
                    if hasattr(selected_agent, 'get_mermaid_graph'):
                        mermaid_graph = selected_agent.get_mermaid_graph()
                        st.markdown(f"""
                        ```mermaid
                        {mermaid_graph}
                        ```
                        """)
                    else:
                        st.error(f"워크플로우 시각화 오류: {str(graph_error)}")
            else:
                st.info("이 에이전트는 워크플로우 시각화를 지원하지 않습니다.")
        except Exception as e:
            st.error(f"워크플로우 시각화 오류: {str(e)}")
    else:
        st.info("LangGraph 기반 에이전트를 선택하면 워크플로우를 확인할 수 있습니다.")
        
    # 에이전트 상태 정보
    st.markdown("### 📊 에이전트 정보")
    st.write(f"**선택된 에이전트:** {agent_type}")
    if agent_type in st.session_state.agent_settings:
        config = st.session_state.agent_settings[agent_type]
        st.write(f"**모델:** {config.get('model', 'N/A')}")
        st.write(f"**온도:** {config.get('temperature', 'N/A')}")
        st.write(f"**프로바이더:** {config.get('provider', 'N/A')}")
    
    # 대화 통계
    st.markdown("### 💬 대화 통계")
    user_messages = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
    assistant_messages = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
    st.write(f"**사용자 메시지:** {user_messages}")
    st.write(f"**AI 응답:** {assistant_messages}")
    
    # 메시지 히스토리 확인 버튼
    if st.button("📋 메시지 히스토리 보기"):
        st.session_state.show_message_history = not st.session_state.get("show_message_history", False)
    
    # 메시지 히스토리 표시
    if st.session_state.get("show_message_history", False):
        st.markdown("#### 전체 메시지 히스토리")
        with st.expander("메시지 목록", expanded=True):
            if st.session_state.messages:
                for i, message in enumerate(st.session_state.messages):
                    role_icon = "👤" if message["role"] == "user" else "🤖"
                    role_text = "사용자" if message["role"] == "user" else "AI"
                    
                    # 메시지 내용 미리보기 (첫 50자만)
                    preview = message["content"][:50] + "..." if len(message["content"]) > 50 else message["content"]
                    
                    with st.container():
                        st.write(f"{role_icon} **{role_text} #{i+1}**")
                        st.text_area(
                            label="",
                            value=message["content"],
                            height=100,
                            disabled=True,
                            key=f"msg_{i}",
                            label_visibility="collapsed"
                        )
                        st.markdown("---")
            else:
                st.info("아직 메시지가 없습니다.")
    
    # 대화 초기화 버튼
    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.session_state.show_message_history = False
        st.session_state.show_gear_options = False
        st.session_state.gear_selection_made = False
        # 선택된 에이전트의 메시지 히스토리도 초기화
        if agent_type in agent_service.agents:
            agent_service.agents[agent_type].clear_messages()
        st.rerun() 