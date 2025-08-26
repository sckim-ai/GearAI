from typing import Dict, Any, Callable
import sys
import os
import asyncio

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

# State 정의
class GearClassifierState(TypedDict):
    messages: Annotated[list, add_messages]
    user_input: str
    classification: str  # "gear_related", "not_gear_related"
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
                    model="gpt-4o-mini",
                    temperature=0.7,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=os.getenv("OPENAI_API_KEY"),
                streaming=False
            )
    
    def _classify_input(self, state: GearClassifierState) -> GearClassifierState:
        """사용자 입력이 기어 설계 관련인지 분류"""
        
        system_prompt = """당신은 기어 설계 관련 질문을 분류하는 전문가입니다.
        
사용자의 입력이 다음과 같은 기어 설계 관련 내용인지 판단해주세요:
- 기어 설계, 계산, 치수
- 기어의 종류, 특성, 재료
- 기어박스, 변속기 설계
- 회전력, 토크, 속도비 계산
- 기어 제조, 가공 방법
- 기어 관련 공학적 문제

다음 중 하나로만 응답하세요:
- "GEAR_RELATED": 기어 설계와 관련된 질문
- "NOT_GEAR_RELATED": 기어 설계와 관련없는 질문

응답 예시:
사용자 입력: "기어비 계산 방법을 알려주세요"
응답: GEAR_RELATED

사용자 입력: "오늘 날씨는 어때요?"
응답: NOT_GEAR_RELATED
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"사용자 입력: {state['user_input']}")
        ]
        
        try:
            response = self.llm.invoke(messages)
            classification_result = response.content.strip()
            
            if "GEAR_RELATED" in classification_result:
                state["classification"] = "gear_related"
            else:
                state["classification"] = "not_gear_related"
                
        except Exception as e:
            print(f"분류 중 오류 발생: {e}")
            # 오류 시 기본적으로 기어 관련으로 처리
            state["classification"] = "gear_related"
        
        return state
    
    def _handle_gear_related(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계 관련 질문 처리"""
        state["response"] = f"기어 설계 관련 질문을 확인했습니다: '{state['user_input']}'\n\n다음 단계로 진행합니다..."
        return state
    
    def _handle_non_gear_related(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계와 관련없는 질문 처리"""
        state["response"] = """죄송합니다. 저는 기어 설계 전문 AI입니다. 

다음과 같은 기어 관련 질문에 도움을 드릴 수 있습니다:
- 기어 설계 및 계산
- 기어비, 토크, 속도 계산
- 기어 종류 및 특성
- 기어박스 설계
- 기어 재료 및 제조 방법

기어 설계에 관한 질문이 있으시면 언제든 문의해 주세요!"""
        return state
    
    def _route_classification(self, state: GearClassifierState) -> str:
        """분류 결과에 따라 라우팅"""
        if state["classification"] == "gear_related":
            return "gear_related"
        else:
            return "not_gear_related"
    
    def _build_graph(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GearClassifierState)
        
        # 노드 추가
        workflow.add_node("classify", self._classify_input)
        workflow.add_node("gear_related", self._handle_gear_related)
        workflow.add_node("not_gear_related", self._handle_non_gear_related)
        
        # 시작점 설정
        workflow.set_entry_point("classify")
        
        # 조건부 라우팅
        workflow.add_conditional_edges(
            "classify",
            self._route_classification,
            {
                "gear_related": "gear_related",
                "not_gear_related": "not_gear_related"
            }
        )
        
        # 종료점 설정
        workflow.add_edge("gear_related", END)
        workflow.add_edge("not_gear_related", END)
        
        return workflow.compile()
    
    def update_config(self, new_config: Dict[str, Any]):
        """설정을 업데이트하고 내부 변수를 갱신합니다."""
        super().update_config(new_config)
        old_provider = self.provider
        old_model = self.model_name
        
        self.model_name = self.config.get("model", "gpt-4o-mini")
        self.temperature = self.config.get("temperature", 0.7)
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