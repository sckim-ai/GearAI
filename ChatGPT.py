import streamlit as st
from utils2 import llm_call, prompt_chain_workflow, run_router_workflow
from utils2 import llm_call_async, run_Parallelization, orchestrate_task
from openai.types.responses import ResponseTextDeltaEvent
import asyncio
import json
from agents.mcp import MCPServerStdio
from agents.agent import Agent
import sys

# Windows 호환성
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# MCP 서버 설정
async def setup_mcp_servers():
    servers = []
    
    # mcp.json 파일에서 설정 읽기
    with open('mcp.json', 'r') as f:
        config = json.load(f)
    
    # 구성된 MCP 서버들을 순회
    for server_name, server_config in config.get('mcpServers', {}).items():
        mcp_server = MCPServerStdio(
            params={
                "command": server_config.get("command"),
                "args": server_config.get("args", [])
            },
            cache_tools_list=True
        )
        await mcp_server.connect()
        servers.append(mcp_server)

    return servers

# 에이전트 설정
async def setup_agent():
    # 서버가 이미 존재하는지 확인하고, 없으면 생성
    mcp_servers = await setup_mcp_servers()
    
    agent = Agent(
        name="Assistant",
        instructions="너는 유튜브 컨텐츠 분석을 도와주는 에이전트야",
        model="gpt-4o-mini",
        mcp_servers=mcp_servers
    )
    return agent,mcp_servers

# 페이지 설정
st.set_page_config(page_title="ChatGPT", layout="wide")

# 세션 상태에서 대화 기록을 관리
SYSTEM_MESSAGE = [
    {
        "role": "system",
        "content": (
            "아래의 대화는 이전부터 진행되었으며, 현재까지 기록된 실제 대화 내역입니다. "
            "따라서 사용자가 과거의 메시지나 맥락을 언급하면, 지금까지 받은 메시지가 이전 메시지가 저장된 기록임을 인지하고 자연스럽게 응답해야 합니다."
        ),
    },
    {
        "role": "assistant",
        "content": (
            "무엇을 도와드릴까요?"
        ),
    }    
]

# 세션 상태에서 대화 기록을 관리
if "messages" not in st.session_state:
    st.session_state.messages = SYSTEM_MESSAGE  # 시스템 메시지 포함


# 사이드바에 OpenAI 모델 설정 옵션 추가
st.sidebar.title("🔧 설정")
AI_model = st.sidebar.selectbox("AI Agent 선택", ["Pure GPT", "Promt chaining", "Routing", "Parallelization", "Orchestrator", "Evaluator optimizer"])
GPT_model = st.sidebar.selectbox("모델 선택", ["gpt-4o-mini", "gpt-4o"])
temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.7)

# 채팅 인터페이스 UI
st.title("💬 ChatGPT")

# 기존 대화 표시
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# 사용자 입력
user_input = st.chat_input("메시지를 입력하세요...")

if user_input:
    # 사용자 메시지 저장 및 출력
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # GPT 응답 요청
    promt = []
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        promt.append({
            "role": role,
            "content": content
        })
    
    responses = []
    with st.spinner("GPT가 답변을 생성 중..."):
        if AI_model == "Pure GPT":
            response = llm_call(
                promt=promt,
                model=GPT_model,            
                temperature=temperature
            )
        
        elif AI_model == "Promt chaining":
            responses = prompt_chain_workflow(promt)
        
        elif AI_model == "Routing":
            responses = run_router_workflow(promt)

        elif AI_model == "Parallelization":
            responses = asyncio.run(run_Parallelization(promt))

        elif AI_model == "Orchestrator":
            response = asyncio.run(orchestrate_task(promt))

    # GPT 응답 저장 및 출력
    if len(responses) == 0:        
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
    else:
        for response in responses:
            st.session_state.messages.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
