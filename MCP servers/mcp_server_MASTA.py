# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path
import datetime
import json
import asyncio
import uuid
import threading
import time
from typing import Dict, Optional, Union
import math

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

# LangChain 관련 임포트
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.output_parsers.openai_tools import JsonOutputToolsParser
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_experimental.utilities import PythonREPL
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.runnables import RunnableConfig

from mcp.server.fastmcp import FastMCP

# API Key 정보 로드
load_dotenv()

mcp = FastMCP("MASTA_agent")

# 세션 데이터 클래스
class SessionData:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.is_initialized = False
        self.gearbox_data = None
        self.design_result = None
        self.code_result = None
        self.workflow = None
        self.graph = None
        self.config = None
        self.created_at = datetime.datetime.now()
        self.last_accessed = datetime.datetime.now()

        # 세션별 출력 폴더 경로
        self.output_dir = os.path.join(os.path.dirname(__file__), "outputs", session_id)
        self.images_dir = os.path.join(self.output_dir, "images")
        self.reports_dir = os.path.join(self.output_dir, "reports")
        self.files = []  # 생성된 파일 목록 추적

    def update_access_time(self):
        self.last_accessed = datetime.datetime.now()

    def create_output_directories(self):
        """세션별 출력 디렉토리 생성"""
        try:
            os.makedirs(self.images_dir, exist_ok=True)
            os.makedirs(self.reports_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"출력 디렉토리 생성 실패: {str(e)}")
            return False

    def add_file(self, file_path: str, file_type: str):
        """생성된 파일을 추적 목록에 추가"""
        self.files.append({
            "path": file_path,
            "type": file_type,
            "created_at": datetime.datetime.now().isoformat()
        })

    def cleanup_files(self):
        """세션 종료 시 생성된 파일들 정리"""
        import shutil
        try:
            if os.path.exists(self.output_dir):
                shutil.rmtree(self.output_dir)
                print(f"세션 {self.session_id} 파일들이 정리되었습니다")
        except Exception as e:
            print(f"파일 정리 중 오류: {str(e)}")

# 전역 세션 관리자
session_manager: Dict[str, SessionData] = {}
SESSION_TIMEOUT = 3600  # 1시간

# 세션 관리 함수들
def get_session(session_id: str) -> SessionData:
    """기존 세션 데이터를 가져옴 (존재하지 않으면 오류)"""
    if session_id not in session_manager:
        raise ValueError(f"세션 '{session_id}'를 찾을 수 없습니다. initialize()을 먼저 호출하세요.")

    session = session_manager[session_id]
    session.update_access_time()
    return session

def create_new_session(session_id: str) -> SessionData:
    """새로운 세션을 생성"""
    if session_id in session_manager:
        raise ValueError(f"세션 '{session_id}'가 이미 존재합니다.")

    session = SessionData(session_id)
    session_manager[session_id] = session
    return session

def cleanup_expired_sessions():
    """만료된 세션 정리"""
    current_time = datetime.datetime.now()
    expired_sessions = []

    for session_id, session in session_manager.items():
        if (current_time - session.last_accessed).seconds > SESSION_TIMEOUT:
            expired_sessions.append((session_id, session))

    for session_id, session in expired_sessions:
        # 파일들 정리
        session.cleanup_files()
        # 세션 삭제
        del session_manager[session_id]
        print(f"세션 만료로 정리됨: {session_id}")

def get_session_info() -> dict:
    """현재 활성 세션 정보 반환"""
    return {
        "active_sessions": len(session_manager),
        "sessions": [
            {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_accessed": session.last_accessed.isoformat(),
                "is_initialized": session.is_initialized
            }
            for session in session_manager.values()
        ]
    }

# Pydantic 모델 정의
class GearBoxData(BaseModel):
    """기어박스 설계 시 필요한 필수 정보"""
    life_hours: float = Field(..., description="요구수명 (단위: hr)")
    input_speed: float = Field(..., description="입력속도 (단위: RPM)")
    load_torque: float = Field(..., description="부하토크 (단위: N.m)")
    operating_temp: float = Field(..., description="작동온도 (단위: deg)")
    gear_ratio: float = Field(..., description="입출력 기어비")

class AdditionalQuestion(BaseModel):
    """ 기어박스 설계 시 필요한 정보를 유저에게 요청 """
    question: str = Field(..., description="기어박스 설계 시 필요한 정보를 요청하기 위한 추가적인 질문")

class GearBoxChatBotResponse(BaseModel):
    """ 챗봇의 응답값 """
    response: Union[AdditionalQuestion, GearBoxData] = Field(..., description="챗봇의 응답")

# LangGraph State 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]
    info: GearBoxData

def create_workflow():
    """MASTA 워크플로우 생성"""

    # LLM 초기화
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm2 = ChatOpenAI(model="gpt-4o", temperature=0)

    # 프롬프트 정의
    prompt1 = ChatPromptTemplate.from_messages([
        ("system", """
        # 당신은 기어박스 설계를 위한 정보수집자로, 기계 설계 및 동력 전달 시스템에 대한 전문 지식을 보유하고 있습니다.
        # 당신은 사용자로부터 기어박스 설계에 필요한 정보를 명확하고 체계적으로 추출합니다.
        # 사용자가 제공한 필수 정보 항목들이 모두 입력되었는지 확인한 후, 누락된 항목이 있을 경우 추가 요청하여 정보를 수집합니다. 필수 정보는 다음과 같습니다:

            1) 요구수명 (단위: hr)
            2) 입력속도 (단위: RPM)
            3) 부하토크 (단위: N.m)
            4) 작동온도 (단위: deg)
            5) 입출력 기어비

        # 필수 정보가 모두 입력될 때까지 반복적으로 요청하여 기어박스 설계를 원활하게 수행합니다.
        # 누락된 정보는 하나씩 요청하지 말고 한꺼번에 요청하세요.
        # 함부로 추측하여 정보를 입력하지 마세요.
        # 답변은 간결하고 명확하게 전달하며, 기어박스 설계에 불필요한 정보를 배제합니다.
        """),
        ("ai", """안녕하세요! 기어박스 설계를 도와드리겠습니다. 아래의 정보를 입력해주세요!
            1) 요구수명 (단위: hr)
            2) 입력속도 (단위: RPM)
            3) 부하토크 (단위: N.m)
            4) 작동온도 (단위: deg)
            5) 입출력 기어비
        """),
        ("placeholder", "{messages}"),
    ])

    prompt2 = ChatPromptTemplate.from_messages([
        ("system", """
        # 당신은 숙련된 기어박스 설계자로, 기계 설계 및 동력 전달 시스템에 대한 전문 지식을 보유하고 있습니다.
        # 당신은 사용자로부터 기어박스 설계에 필요한 정보를 명확하고 체계적으로 추출하고 추출된 정보로 기어박스를 설계합니다.
        # 당신에게 전달될 필수 정보는 아래의 5가지입니다.

            1) 요구수명 (단위: hr)
            2) 입력속도 (단위: RPM)
            3) 부하토크 (단위: N.m)
            4) 작동온도 (단위: deg)
            5) 입출력 기어비

        # 필수 정보가 모두 수집되면 사용자로부터 입력된 정보를 기반으로 기어박스를 설계합니다.
        # 설계를 위해 반드시 지켜야하는 프로세스는 아래와 같습니다.
        # 각 프로세스는 단계별로 수행되어야 합니다.

            1) 입력된 기어비를 분석하여 필요한 평기어 쌍의 개수를 결정합니다.
                - 기어 한쌍의 최대 허용 기어비는 [4] 입니다.
                - 기어비를 여러 개의 기어 쌍으로 분배할 경우 각 기어 쌍의 기어비는 비슷한 수준으로 분배합니다.
            2) 입력된 요구수명, 속도, 토크를 활용하여 평기어 쌍을 설계합니다.
            3) 기어가 장착되기 위해 필요한 축의 수를 결정합니다.
            4) 축의 길이와 직경을 결정합니다.
            5) 축의 위치를 결정합니다. (xyz 좌표)
            6) 축의 기어 장착 위치를 결정합니다.
            7) 축을 안정적으로 지지하기 위한 베어링의 갯수를 결정합니다.
            8) 축을 안정적으로 지지하기 위한 베어링의 장착 위치를 결정합니다.

        # 설계 후 [Code Generator]에게 각 프로세스 별로 구분하여 도출된 설계결과를 전달합니다.
        # 답변은 간결하고 명확하게 전달하며, 기어박스 설계에 불필요한 정보를 배제합니다.
        """),
        ("placeholder", "{messages}"),
    ])

    prompt3 = ChatPromptTemplate.from_messages([
        ("system", """
        # This GPT assists users in generating API code for running software (SW) that focuses on designing gearboxes, with a specialization in Python-based API code.
        # All code snippets include the following initialization block for mastapy before any other API functionality:

        ```python
        # mastapy 초기화
        import math
        import Utility
        import mastapy
        from mastapy import init

        init(r'C:\\Program Files\\SMT\\MASTA 13.0.3')

        # 새로운 Design 작성
        from mastapy.system_model import Design

        my_design = Design()

        # Root assembly 변수에 할당
        assembly = my_design.root_assembly

        # 단위 환산 준비
        MM = 1e-3
        RAD = math.pi/180
        RPM = 2*math.pi/60
        ```

        # 기어박스 모델링은 아래의 순서에 따라 순서대로 코드를 생성해주세요.
        1) 기어 생성
        2) 기어 제원 수정
        3) 축 생성
        4) 축 배치
        5) 기어 배치
        6) 베어링 생성
        7) 베어링 배치
        8) 베어링 designation 설정
        9) 모델 이미지 보여주기

        # The end of your code should always include the following code:
        ```python
        Utility.plot_images(assembly=assembly)
        ```

        This GPT ensures SI units, maintainable code, and compatibility with mastapy.

        if the python code is generated, call to execute python code.
        """),
        ("placeholder", "{messages}"),
    ])

    # 체인 정의
    llm_with_tool1 = llm.with_structured_output(GearBoxChatBotResponse)
    chain1 = prompt1 | llm_with_tool1
    chain2 = prompt2 | llm2

    # 파이썬 실행 도구
    repl = PythonREPL()

    @tool
    def python_repl_tool(code: str):
        """Call to execute python code."""
        try:
            result = repl.run(code)
        except BaseException as e:
            return f"Failed to execute. Error: {repr(e)}"
        result_str = f"Successfully executed!\n\nStdout: {result}"
        return result_str + "\n\nIf you have completed all tasks, respond with FINAL ANSWER."

    tools = [python_repl_tool]
    tool_node = ToolNode(tools)

    llm_with_tool2 = llm2.bind_tools([python_repl_tool])
    chain3 = prompt3 | llm_with_tool2

    # 워크플로우 생성
    workflow = StateGraph(State)

    # 노드 함수 정의
    def chatbot(state: State):
        messages = state["messages"]
        response = chain1.invoke({"messages": messages})

        if isinstance(response.response, GearBoxData):
            return {
                "messages": messages,
                "info": response.response
            }
        else:
            messages.append(AIMessage(content=response.response.question))
            return {
                "messages": messages,
                "info": None
            }

    def stop_agent_cond(state: State):
        if state.get('info') is not None:
            return 'next'
        else:
            return 'end'

    def SummaryNode(state: State):
        messages = state["messages"]
        info = state["info"]

        messages.append(AIMessage(content=f"""기어박스 설계를 위한 정보수집이 완료되었습니다.
==================================
요구수명 : {info.life_hours} [hr]
입력속도 : {info.input_speed} [rpm]
부하토크 : {info.load_torque} [N.m]
작동온도 : {info.operating_temp} [deg]
요구기어비 : {info.gear_ratio}
"""))
        return {
            "messages": messages,
            "info": info
        }

    def Designer(state: State):
        messages = state["messages"]
        response = chain2.invoke({"messages": messages})
        return {"messages": [response]}

    def codeGen(state: State):
        messages = state["messages"]
        response = chain3.invoke({"messages": messages})
        return {"messages": [response]}

    def route_tools(state: State):
        if messages := state.get("messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
            return "tools"
        return END

    # 노드 추가
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("Summary", SummaryNode)
    workflow.add_node("Designer", Designer)
    workflow.add_node("CodeGen", codeGen)
    workflow.add_node("tools", tool_node)

    # 엣지 추가
    workflow.add_conditional_edges(
        "chatbot",
        stop_agent_cond,
        {'next': "Summary", "end": END}
    )
    workflow.add_conditional_edges(
        source="CodeGen",
        path=route_tools,
        path_map={"tools": "tools", END: END},
    )

    workflow.add_edge(START, "chatbot")
    workflow.add_edge("Summary", "Designer")
    workflow.add_edge("Designer", "CodeGen")
    workflow.add_edge("tools", "CodeGen")

    return workflow

# MCP 툴 함수들
@mcp.tool()
def initialize() -> dict:
    """
    MASTA 기어박스 설계를 위한 LangGraph 워크플로우를 초기화합니다.

    이 함수는 새로운 세션을 자동으로 생성하고 MASTA 기어박스 설계 시스템을 초기화합니다.
    초기화가 완료되면 반환된 session_id를 사용하여 다른 함수들을 호출할 수 있습니다.

    Returns:
        dict: 초기화 결과
            - 성공 시: {"success": True, "message": "초기화 완료", "session_id": "새로생성된세션ID"}
            - 실패 시: {"success": False, "error": "오류 메시지"}

    Note:
        - 매번 새로운 세션을 생성하므로 독립적인 작업 공간을 제공합니다
        - 반환된 session_id를 다른 모든 함수 호출에 사용해야 합니다
        - 이 함수는 MASTA 기어박스 설계 작업을 시작하는 첫 번째 함수입니다
    """
    new_session_id = str(uuid.uuid4())

    try:
        session = create_new_session(new_session_id)
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": new_session_id
        }

    try:
        # 워크플로우 생성 및 컴파일
        workflow = create_workflow()
        memory = MemorySaver()
        graph = workflow.compile(checkpointer=memory)

        # 설정 생성
        config = RunnableConfig(
            recursion_limit=10,
            configurable={"thread_id": new_session_id},
        )

        # 세션에 저장
        session.workflow = workflow
        session.graph = graph
        session.config = config

        # 세션별 출력 디렉토리 생성
        if not session.create_output_directories():
            return {
                "success": False,
                "error": "출력 디렉토리 생성 실패",
                "session_id": new_session_id
            }

        session.is_initialized = True

        return {
            "success": True,
            "message": f"새 세션({new_session_id[:8]})이 생성되고 초기화되었습니다",
            "session_id": new_session_id,
            "output_directory": session.output_dir,
            "status": "initialized"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"초기화 중 오류 발생: {str(e)}",
            "session_id": new_session_id
        }

@mcp.tool()
def process_gearbox_request(user_message: str, session_id: str) -> dict:
    """
    사용자의 기어박스 설계 요청을 처리합니다.

    이 함수는 LangGraph 워크플로우를 통해 사용자 메시지를 처리하고,
    기어박스 설계 정보 수집, 설계, 코드 생성 과정을 수행합니다.

    Args:
        user_message (str): 기어박스 설계 관련 사용자 메시지
        session_id (str): 세션 ID (initialize()으로 생성된 ID 필수)

    Returns:
        dict: 처리 결과
            - 성공 시: 워크플로우 실행 결과와 메시지들
            - 실패 시: {"error": "오류 메시지", "session_id": "세션ID"}

    Note:
        - 사전에 initialize() 호출이 완료되어야 합니다
        - 워크플로우는 정보수집 → 요약 → 설계 → 코드생성 → 실행 순으로 진행됩니다
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    try:
        # 워크플로우 실행
        events = []
        for event in session.graph.stream(
            {
                "messages": [("user", user_message)]
            },
            session.config
        ):
            events.append(event)

        return {
            "success": True,
            "message": "워크플로우 실행 완료",
            "events": events,
            "session_id": session.session_id
        }

    except Exception as e:
        return {
            "error": f"워크플로우 실행 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

@mcp.tool()
def get_session_messages(session_id: str) -> dict:
    """
    세션의 대화 메시지 히스토리를 조회합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 메시지 히스토리 또는 오류 정보
    """
    try:
        session = get_session(session_id)
    except ValueError as e:
        return {
            "error": str(e),
            "session_id": session_id
        }

    if not session.is_initialized:
        return {
            "error": "초기화되지 않음",
            "session_id": session.session_id
        }

    try:
        # 그래프 상태에서 메시지 가져오기
        state = session.graph.get_state(session.config)
        messages = state.values.get("messages", [])

        return {
            "success": True,
            "messages": [{"role": msg.type if hasattr(msg, 'type') else "unknown",
                         "content": msg.content if hasattr(msg, 'content') else str(msg)}
                        for msg in messages],
            "message_count": len(messages),
            "session_id": session.session_id
        }
    except Exception as e:
        return {
            "error": f"메시지 조회 중 오류 발생: {str(e)}",
            "session_id": session.session_id
        }

# 세션 관리 관련 MCP 툴 추가
@mcp.tool()
def get_active_sessions() -> dict:
    """
    현재 활성 세션들의 정보를 반환합니다.

    Returns:
        dict: 세션 정보
            - active_sessions: 활성 세션 수
            - sessions: 각 세션의 상세 정보 리스트
    """
    return get_session_info()

@mcp.tool()
def get_session_files(session_id: str) -> dict:
    """
    세션에서 생성된 파일 목록을 반환합니다.

    Args:
        session_id (str): 세션 ID

    Returns:
        dict: 파일 목록 정보
    """
    try:
        session = get_session(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "files": session.files,
            "file_count": len(session.files)
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

def cleanup_sessions() -> dict:
    """
    만료된 세션들을 정리합니다.

    Returns:
        dict: 정리 결과
    """
    before_count = len(session_manager)
    cleanup_expired_sessions()
    after_count = len(session_manager)
    cleaned_count = before_count - after_count

    return {
        "cleaned_sessions": cleaned_count,
        "remaining_sessions": after_count,
        "message": f"{cleaned_count}개의 만료된 세션이 정리되었습니다"
    }

def delete_session(session_id: str) -> dict:
    """
    특정 세션을 강제로 삭제합니다.

    Args:
        session_id (str): 삭제할 세션 ID

    Returns:
        dict: 삭제 결과
    """
    if session_id in session_manager:
        session = session_manager[session_id]
        session.cleanup_files()
        del session_manager[session_id]

        return {
            "success": True,
            "message": f"세션 {session_id}와 관련 파일들이 삭제되었습니다"
        }
    else:
        return {
            "success": False,
            "error": f"세션 {session_id}를 찾을 수 없습니다"
        }

# 주기적 세션 정리를 위한 백그라운드 스레드
def periodic_cleanup():
    """주기적으로 만료된 세션을 정리하는 함수"""
    while True:
        time.sleep(300)  # 5분마다 실행
        try:
            cleanup_expired_sessions()
        except Exception as e:
            print(f"세션 정리 중 오류 발생: {str(e)}")

# 백그라운드 정리 스레드 시작
cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    print("Starting MASTA MCP server...")
    print(f"세션 타임아웃: {SESSION_TIMEOUT}초")
    print("백그라운드 세션 정리 스레드 시작됨")
    mcp.run()