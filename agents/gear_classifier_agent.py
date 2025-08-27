from typing import Dict, Any, Callable
import sys
import os
import asyncio
from io import BytesIO
from PIL import Image

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from .base_agent import BaseAgent
import streamlit as st
import time
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv()

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

# LangChain imports  
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# State 정의
class GearClassifierState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    classification: str  # "gear_related", "not_gear_related"
    gear_type: str  # "designable", "not_designable"
    detected_gear_type: str  # "gear_pair", "three_gear", "simple_planetary", "double_pinion_planetary", "unknown"
    response: str

class GearClassifierAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.7)
        self.provider = config.get("provider", "openai")
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()
        
    def _initialize_llm(self):
        """LLM 모델 초기화"""
        try:
            if self.provider == "openai":
                return ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
            else:
                # 기본값은 OpenAI
                return ChatOpenAI(
                    model="gpt-5-mini",
                    temperature=0.0,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            return ChatOpenAI(
                model="gpt-5-mini",
                temperature=0.0,
                api_key=os.getenv("OPENAI_API_KEY"),
                streaming=False
            )
    
    def _classify_input(self, state: GearClassifierState) -> GearClassifierState:
        """사용자 입력이 기어 설계 관련인지 분류"""
        
        system_prompt = """당신은 기어 설계 관련 질문을 분류하는 전문가입니다.
        
사용자의 입력이 다음과 같은 기어 설계 관련 내용인지 판단해주세요:
- 기어 치형설계
- 기어 강도평가
- 기어 효율계산
- 기어 소음개선
- 기어 설계 최적화

다음 중 하나로만 응답하세요:
- "GEAR_RELATED": 기어 설계와 관련된 질문
- "NOT_GEAR_RELATED": 기어 설계와 관련없는 질문

응답 예시:
사용자 입력: "기어비 계산 방법을 알려주세요"
응답: GEAR_RELATED

사용자 입력: "오늘 날씨는 어때요?"
응답: NOT_GEAR_RELATED
"""

        chat_template = ChatPromptTemplate.from_messages(
            [
                # role, message
                ("system", system_prompt),
                ("human", "사용자 입력: {user_input}"),
            ]
)
        
        try:
            chain = chat_template | self.llm
            response_chain = chain.invoke({"user_input": state["user_input"]})
            classification_result = response_chain.content.strip()

            print(f"분류 결과: {classification_result}")

            if not "NOT_GEAR_RELATED" in classification_result:
                state["classification"] = "gear_related"
            else:
                state["classification"] = "not_gear_related"
                
        except Exception as e:
            print(f"분류 중 오류 발생: {e}")
            # 오류 시 기본적으로 기어 관련으로 처리
            state["classification"] = "gear_related"
        
        return state
    
    def _classify_gear_type(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계 가능 여부 및 기어 타입 분류"""
        
        system_prompt = """당신은 기어 설계 타입을 분류하는 전문가입니다.

사용자의 입력에서 다음 중 어떤 기어 타입에 해당하는지 판단해주세요:

설계 가능한 기어 타입 (인볼류트 치형):
1. "GEAR_PAIR" - 기어 쌍 (2개 기어가 맞물리는 구조)
2. "THREE_GEAR" - 3단 기어 (3개 기어가 연결된 구조) 
3. "SIMPLE_PLANETARY" - 단순 유성기어 (태양기어, 유성기어, 링기어)
4. "DOUBLE_PINION_PLANETARY" - 이중 피니언 유성기어 (2단계 유성기어 시스템)

설계 불가능한 경우:
5. "UNKNOWN" - 위 타입에 해당하지 않거나 명확하지 않은 경우

다음 중 하나로만 응답하세요:
GEAR_PAIR, THREE_GEAR, SIMPLE_PLANETARY, DOUBLE_PINION_PLANETARY, UNKNOWN

응답 예시:
사용자 입력: "두 개의 기어 맞물림 설계해주세요"
응답: GEAR_PAIR

사용자 입력: "유성기어 설계 도움"  
응답: SIMPLE_PLANETARY

사용자 입력: "웜기어 설계"
응답: UNKNOWN
"""

        chat_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "사용자 입력: {user_input}"),
        ])
        
        try:
            chain = chat_template | self.llm
            response_chain = chain.invoke({"user_input": state["user_input"]})
            gear_type_result = response_chain.content.strip()

            print(f"기어 타입 분류 결과: {gear_type_result}")

            # 설계 가능한 기어 타입들
            designable_types = ["GEAR_PAIR", "THREE_GEAR", "SIMPLE_PLANETARY", "DOUBLE_PINION_PLANETARY"]
            
            if gear_type_result in designable_types:
                state["gear_type"] = "designable"
                state["detected_gear_type"] = gear_type_result.lower()
            else:
                state["gear_type"] = "not_designable"
                state["detected_gear_type"] = "unknown"
                
        except Exception as e:
            print(f"기어 타입 분류 중 오류 발생: {e}")
            # 오류 시 기본적으로 설계 불가능으로 처리
            state["gear_type"] = "not_designable"
            state["detected_gear_type"] = "unknown"
        
        return state

    def _handle_designable_gear(self, state: GearClassifierState) -> GearClassifierState:
        """설계 가능한 기어 처리"""
        gear_type_names = {
            "gear_pair": "기어 쌍",
            "three_gear": "3단 기어",
            "simple_planetary": "단순 유성기어",
            "double_pinion_planetary": "이중 피니언 유성기어"
        }
        
        gear_name = gear_type_names.get(state["detected_gear_type"], "인식된 기어")
        
        state["response"] = f"""✅ {gear_name} 설계가 가능합니다!

🔧 감지된 기어 타입: {gear_name}
📋 요청사항: {state['user_input']}

다음 단계로 기어 설계 사양을 생성하겠습니다..."""
        return state

    def _handle_non_designable_gear(self, state: GearClassifierState) -> GearClassifierState:
        """설계 불가능한 기어 처리"""  
        
        # Streamlit 세션 상태에 선택 옵션 표시 플래그 설정
        if 'st' in globals():
            import streamlit as st
            st.session_state.show_gear_options = True
            st.session_state.gear_selection_made = False
        
        state["response"] = f"""❌ 죄송합니다. 현재 요청하신 기어는 설계가 어렵습니다.

📝 요청사항: {state['user_input']}

🔧 **설계 가능한 기어 타입을 선택해 주세요:**"""
        return state
    
    def _handle_non_gear_related(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계와 관련없는 질문 처리"""
        state["response"] = """안녕하세요. 저는 기어 설계 전문 AI Agent입니다. 

다음과 같은 기어 설계 관련 요청에 도움을 드릴 수 있습니다:
- 기어 치형설계
- 기어 강도평가
- 기어 효율계산
- 기어 소음개선
- 기어 설계 최적화

기어 설계에 도움이 필요하시면 언제든 요청해 주세요!"""
        return state
    
    def _route_classification(self, state: GearClassifierState) -> str:
        """분류 결과에 따라 라우팅"""
        if state["classification"] == "gear_related":
            return "classify_gear_type"
        else:
            return "not_gear_related"
    
    def _route_gear_type(self, state: GearClassifierState) -> str:
        """기어 타입에 따라 라우팅"""
        if state["gear_type"] == "designable":
            return "designable_gear"
        else:
            return "not_designable_gear"
    
    def _build_graph(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GearClassifierState)
        
        # 노드 추가
        workflow.add_node("classify", self._classify_input)
        workflow.add_node("classify_gear_type", self._classify_gear_type)
        workflow.add_node("designable_gear", self._handle_designable_gear)
        workflow.add_node("not_designable_gear", self._handle_non_designable_gear)
        workflow.add_node("not_gear_related", self._handle_non_gear_related)
        
        # 시작점 설정
        workflow.set_entry_point("classify")
        
        # 조건부 라우팅 - 첫 번째 분류 (기어 관련 여부)
        workflow.add_conditional_edges(
            "classify",
            self._route_classification,
            {
                "classify_gear_type": "classify_gear_type",
                "not_gear_related": "not_gear_related"
            }
        )
        
        # 조건부 라우팅 - 두 번째 분류 (기어 타입)
        workflow.add_conditional_edges(
            "classify_gear_type",
            self._route_gear_type,
            {
                "designable_gear": "designable_gear",
                "not_designable_gear": "not_designable_gear"
            }
        )
        
        # 종료점 설정
        workflow.add_edge("designable_gear", END)
        workflow.add_edge("not_designable_gear", END)
        workflow.add_edge("not_gear_related", END)
        
        return workflow.compile()
    
    def get_graph_image(self):
        """LangGraph에서 그래프 이미지를 생성하여 반환"""
        try:
            # LangGraph의 get_graph(xray=True).draw_mermaid_png() 사용
            png_data = self.graph.get_graph(xray=True).draw_mermaid_png()
            
            # PNG 데이터를 PIL Image로 변환
            image = Image.open(BytesIO(png_data))
            return image
        except Exception as e:
            print(f"그래프 이미지 생성 오류: {e}")
            return None
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정을 업데이트하고 내부 변수를 갱신합니다."""
        super().update_config(new_config)
        old_provider = self.provider
        old_model = self.model_name
        
        self.model_name = self.config.get("model", "gpt-5-mini")
        self.temperature = self.config.get("temperature", 0.0)
        self.provider = self.config.get("provider", "openai")
        
        # 모델이나 프로바이더가 변경된 경우 LLM 재초기화
        if old_provider != self.provider or old_model != self.model_name:
            self.llm = self._initialize_llm()
            self.graph = self._build_graph()
    
    @traceable
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """콜백 방식으로 처리합니다."""
        try:
            # 사용자 메시지 추가
            self.add_message("user", input_text)
            
            # 초기 상태 설정
            initial_state = {
                "messages": [],
                "user_input": input_text,
                "classification": "",
                "gear_type": "",
                "detected_gear_type": "",
                "response": ""
            }
            
            # 그래프 실행
            result = await asyncio.to_thread(self.graph.invoke, initial_state)
            
            # 결과 처리
            response_text = result["response"]
            
            # 콜백 함수 호출
            callback(response_text)
            
            # 최종 응답을 메시지에 추가
            self.add_message("assistant", response_text)
            return response_text
        
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            callback(error_msg)
            self.add_message("assistant", error_msg)
            return error_msg