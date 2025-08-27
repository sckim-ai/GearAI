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
    has_speed_info: bool  # 입출력 속도 정보 유무
    has_power_info: bool  # 입출력 파워 정보 유무
    has_ratio_info: bool  # 기어비 또는 기어 잇수 정보 유무
    missing_info: str  # "power", "ratio", "both", "none"
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
        
        # 먼저 사용자가 선택 옵션에서 designable gear를 선택했는지 확인
        designable_gear_keywords = [
            "두 개의 기어가 맞물리는 기본 구조로 설계해 주세요",
            "세 개의 기어가 연결된 구조로 설계해 주세요",
            "태양기어, 유성기어, 링기어로 구성된 유성기어로 설계해 주세요",
            "2단계 유성기어 시스템으로 설계해 주세요"
        ]
        
        # 사용자가 선택 옵션에서 designable gear를 선택한 경우
        if any(keyword in state["user_input"] for keyword in designable_gear_keywords):
            state["classification"] = "gear_related"
            print("사용자가 선택 옵션에서 designable gear를 선택함")
            return state
        
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

        # 메시지 히스토리가 있는 경우와 없는 경우를 구분하여 처리
        if state["messages"] and len(state["messages"]) > 1:
            # 대화 히스토리가 있는 경우 - 전체 컨텍스트 포함
            chat_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt + "\n\n이전 대화 맥락을 고려하여 현재 사용자 입력을 분류해주세요."),
                    MessagesPlaceholder("conversation_history"),
                    ("human", "현재 사용자 입력: {user_input}"),
                ]
            )
        else:
            # 첫 번째 메시지인 경우 - 기존 방식 유지
            chat_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "사용자 입력: {user_input}"),
                ]
            )
        
        try:
            chain = chat_template | self.llm
            # 메시지 히스토리 포함하여 invoke
            if state["messages"] and len(state["messages"]) > 1:
                # 마지막 사용자 메시지를 제외한 이전 대화 히스토리
                conversation_history = state["messages"][:-1]
                response_chain = chain.invoke({
                    "user_input": state["user_input"],
                    "conversation_history": conversation_history
                })
            else:
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
사용자 입력: "두 개의 기어가 맞물리는 기어 한 쌍을 설계해주세요"
응답: GEAR_PAIR

사용자 입력: "유성기어 설계 도움"  
응답: SIMPLE_PLANETARY

사용자 입력: "웜기어 설계"
응답: UNKNOWN

사용자 입력: "기어 설계 해줘"
응답: UNKNOWN
"""

        # 메시지 히스토리 고려한 템플릿 생성
        if state["messages"] and len(state["messages"]) > 1:
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt + "\n\n이전 대화 맥락을 고려하여 기어 타입을 분류해주세요."),
                MessagesPlaceholder("conversation_history"),
                ("human", "현재 사용자 입력: {user_input}"),
            ])
        else:
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "사용자 입력: {user_input}"),
            ])
        
        try:
            chain = chat_template | self.llm
            # 메시지 히스토리 포함하여 invoke
            if state["messages"] and len(state["messages"]) > 1:
                conversation_history = state["messages"][:-1]
                response_chain = chain.invoke({
                    "user_input": state["user_input"],
                    "conversation_history": conversation_history
                })
            else:
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

    def _check_required_info(self, state: GearClassifierState) -> GearClassifierState:
        """필수 설계 정보(Power, 기어비/잇수) 확인"""
        
        system_prompt = """당신은 기어 설계에 필요한 정보를 확인하는 전문가입니다.

사용자의 입력에서 다음 정보가 포함되어 있는지 확인해주세요:

1. **입출력 파워 정보**:     
   1) CASE1: Gear Pair 인 경우 아래의 정보가 모두 포함되어야 함
    - 입/출력 속도 중 1개 (입/출력 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - 입/출력 파워 중 1개, 또는 입/출력 토크 중 1개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - 예시1: 입력속도 1000 rpm, 출력토크 50Nm -> OK
    - 예시2: 입력속도 1000 rpm, 출력속도 500 rpm, 출력토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: 입력속도 1000 rpm, 입력파워 100W, 출력토크 50Nm -> NG (입력 파워와 토크 모두 주어짐)

   2) CASE2: Three Gear 
    - Gear1/Gear2/Gear3 의 입력 속도 중 1개 (입/출력 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3 의 입력 파워 중 2개, 또는 토크 중 2개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - 예시1: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 토크 50Nm -> OK
    - 예시2: Gear1 속도 1000 rpm, Gear2 속도 500 rpm, Gear3 토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 파워 50W -> NG (입력 파워와 토크 모두 주어짐)

   3) CASE3: Simple Planetary, Double Pinion Planetary
    - Sun/Carrier/Ring 의 입력 속도 중 2개 (유성기어의 속도는 3개의 입력 중 2개로 결정되기 때문에 반드시 2개 입력 필요)
    - Sun/Carrier/Ring 의 입력 파워 중 1개, 또는 토크 중 1개 (유성기어의 파워 또는 토크는 1개의 입력과 입력된 속도로 나머지가 모두 계산됨)

    ### 입출력 작동조건 단위 (아래 단위가 아닌 경우 환산된 정보가 포함되어야 함)
    - 속도 단위: "rpm" (예: "1000rpm", "3600rpm" 등)
    - 파워 단위: "kW" (예: "100 kW", "5kW" 등) 
    - 토크 단위: "Nm" (예: "50Nm", "200Nm" 등)

   - 
   - 예: "100W", "50kW", "1000rpm", "200Nm" 등

2. **기어비 또는 기어 잇수 정보**:
   - 기어비 (예: "3:1", "감속비 10", "기어비 2.5")
   - 기어 잇수 (예: "20치", "30개 이", "teeth 40")

다음 형식으로만 응답하세요:
SPEED_INFO: YES 또는 NO
POWER_INFO: YES 또는 NO
RATIO_INFO: YES 또는 NO

응답 예시:
사용자 입력: "100W에서 기어비 3:1로 기어쌍 설계해주세요"
응답: 
SPEED_INFO: NO    
POWER_INFO: YES
RATIO_INFO: YES

사용자 입력: "기어쌍 설계 부탁드립니다"
응답:
SPEED_INFO: NO
POWER_INFO: NO  
RATIO_INFO: NO
"""

        # 메시지 히스토리 고려한 템플릿 생성
        if state["messages"] and len(state["messages"]) > 1:
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt + "\n\n이전 대화 맥락을 고려하여 필수 정보를 확인해주세요. 이전 메시지에서 언급된 파워나 기어비 정보도 포함하여 판단해주세요."),
                MessagesPlaceholder("conversation_history"),
                ("human", "현재 사용자 입력: {user_input}"),
            ])
        else:
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "사용자 입력: {user_input}"),
            ])
        
        try:
            chain = chat_template | self.llm
            # 메시지 히스토리 포함하여 invoke
            if state["messages"] and len(state["messages"]) > 1:
                conversation_history = state["messages"][:-1]
                response_chain = chain.invoke({
                    "user_input": state["user_input"],
                    "conversation_history": conversation_history
                })
            else:
                response_chain = chain.invoke({"user_input": state["user_input"]})
            info_check_result = response_chain.content.strip()

            print(f"필수 정보 확인 결과: {info_check_result}")

            # 속도 정보 확인
            state["has_speed_info"] = "SPEED_INFO: YES" in info_check_result
            
            # 파워 정보 확인
            state["has_power_info"] = "POWER_INFO: YES" in info_check_result
            
            # 기어비/잇수 정보 확인  
            state["has_ratio_info"] = "RATIO_INFO: YES" in info_check_result
            
            # 누락된 정보 분류 - speed, power, ratio 모두 고려
            missing_items = []
            if not state["has_speed_info"]:
                missing_items.append("speed")
            if not state["has_power_info"]:
                missing_items.append("power")
            if not state["has_ratio_info"]:
                missing_items.append("ratio")
            
            if len(missing_items) == 0:
                state["missing_info"] = "none"
            elif len(missing_items) == 1:
                state["missing_info"] = missing_items[0]
            elif len(missing_items) == 2:
                state["missing_info"] = "_".join(missing_items)
            else:  # 모든 정보 누락
                state["missing_info"] = "all"
                
        except Exception as e:
            print(f"필수 정보 확인 중 오류 발생: {e}")
            # 오류 시 모든 정보가 없다고 가정
            state["has_speed_info"] = False
            state["has_power_info"] = False
            state["has_ratio_info"] = False
            state["missing_info"] = "all"
        
        return state

    def _handle_complete_info(self, state: GearClassifierState) -> GearClassifierState:
        """모든 필수 정보가 있는 경우 처리"""
        gear_type_names = {
            "gear_pair": "기어 쌍",
            "three_gear": "3단 기어",
            "simple_planetary": "단순 유성기어",
            "double_pinion_planetary": "이중 피니언 유성기어"
        }
        
        gear_name = gear_type_names.get(state["detected_gear_type"], "인식된 기어")
        
        state["response"] = f"""✅ {gear_name} 설계에 필요한 모든 정보가 확인되었습니다!

🔧 **설계 타입**: {gear_name}\n\r
📋 **요청사항**: {state['user_input']}\n\r
🏃 **속도 정보**: 포함됨\n\r
⚡ **파워/토크 정보**: 포함됨\n\r
⚙️ **기어비/잇수 정보**: 포함됨

다음 단계로 상세 기어 설계 사양을 생성하겠습니다..."""
        return state

    def _handle_missing_info(self, state: GearClassifierState) -> GearClassifierState:
        """필수 정보가 누락된 경우 처리"""
        gear_type_names = {
            "gear_pair": "기어 쌍",
            "three_gear": "3단 기어", 
            "simple_planetary": "단순 유성기어",
            "double_pinion_planetary": "이중 피니언 유성기어"
        }
        
        gear_name = gear_type_names.get(state["detected_gear_type"], "인식된 기어")
        
        # 누락된 정보에 따른 메시지 생성
        missing_items = []
        if not state["has_speed_info"]:
            missing_items.append("속도")
        if not state["has_power_info"]:
            missing_items.append("파워/토크")
        if not state["has_ratio_info"]:
            missing_items.append("기어비/잇수")
        
        if len(missing_items) == 3:
            missing_text = "**속도 정보**, **파워/토크 정보**, **기어비/잇수 정보**가"
            examples = """
📋 **종합 입력 예시**:
• "1000rpm 입력속도, 100W 파워로 기어비 3:1인 기어쌍 설계"
• "입력속도 1500rpm, 출력토크 50Nm, 감속비 10인 유성기어 설계"
• "Sun속도 1000rpm, Carrier속도 500rpm, Ring파워 2kW인 유성기어 설계\""""
        elif len(missing_items) == 2:
            missing_text = f"**{missing_items[0]} 정보**와 **{missing_items[1]} 정보**가"
            if "속도" in missing_items and "파워/토크" in missing_items:
                examples = """
📋 **속도/파워 정보 예시**:
• 속도: "1000rpm", "3600rpm" (입력 또는 출력)
• 파워: "100W", "5kW" / 토크: "50Nm", "200Nm\""""
            elif "속도" in missing_items and "기어비/잇수" in missing_items:
                examples = """
📋 **속도/기어비 정보 예시**:
• 속도: "1000rpm", "3600rpm"
• 기어비: "3:1", "감속비 10" / 잇수: "20치", "40 teeth\""""
            else:  # 파워/토크와 기어비/잇수
                examples = """
📋 **파워/기어비 정보 예시**:
• 파워: "100W", "5kW" / 토크: "50Nm", "200Nm"
• 기어비: "3:1", "감속비 10" / 잇수: "20치", "40 teeth\""""
        else:  # 1개 누락
            missing_text = f"**{missing_items[0]} 정보**가"
            if missing_items[0] == "속도":
                examples = """
📋 **속도 정보 예시**:
• 입력/출력 속도: "1000rpm", "3600rpm"
• 유성기어의 경우: "Sun속도 1000rpm", "Carrier속도 500rpm\""""
            elif missing_items[0] == "파워/토크":
                examples = """
📋 **파워/토크 정보 예시**:
• 파워: "100W", "5kW"  
• 토크: "50Nm", "200Nm\""""
            else:  # 기어비/잇수
                examples = """
📋 **기어비/잇수 정보 예시**:
• 기어비: "3:1", "감속비 10", "기어비 2.5"
• 기어 잇수: "20치", "30개 이", "40 teeth\""""

        state["response"] = f"""⚠️ {gear_name} 설계를 위해 추가 정보가 필요합니다.

🔧 **설계 타입**: {gear_name}
📝 **현재 요청**: {state['user_input']}

❌ **누락된 정보**: {missing_text} 필요합니다.
{examples}

위 정보를 포함하여 다시 요청해 주세요! 🙂"""
        
        return state

    def _handle_non_designable_gear(self, state: GearClassifierState) -> GearClassifierState:
        """설계 불가능한 기어 처리"""  
        
        # 특별한 응답 플래그를 포함하여 app.py에서 UI를 표시하도록 함
        state["response"] = f"""기어설계 AI Agent가 설계 가능한 기어는 다음과 같습니다.

🔧 **설계 가능한 기어 타입을 선택해 주세요:**

[SHOW_GEAR_OPTIONS]"""
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
            return "check_required_info"
        else:
            return "not_designable_gear"
    
    def _route_required_info(self, state: GearClassifierState) -> str:
        """필수 정보 확인 결과에 따라 라우팅"""
        if state["missing_info"] == "none":
            return "complete_info"
        else:
            return "missing_info"
    
    def _build_graph(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GearClassifierState)
        
        # 노드 추가
        workflow.add_node("classify", self._classify_input)
        workflow.add_node("classify_gear_type", self._classify_gear_type)
        workflow.add_node("check_required_info", self._check_required_info)
        workflow.add_node("complete_info", self._handle_complete_info)
        workflow.add_node("missing_info", self._handle_missing_info)
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
                "check_required_info": "check_required_info",
                "not_designable_gear": "not_designable_gear"
            }
        )
        
        # 조건부 라우팅 - 세 번째 분류 (필수 정보 확인)
        workflow.add_conditional_edges(
            "check_required_info",
            self._route_required_info,
            {
                "complete_info": "complete_info",
                "missing_info": "missing_info"
            }
        )
        
        # 종료점 설정
        workflow.add_edge("complete_info", END)
        workflow.add_edge("missing_info", END)
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
            
            # 초기 상태 설정 - 전체 메시지 히스토리 포함
            initial_state = {
                "messages": self.messages.copy(),  # 전체 메시지 히스토리 사용
                "user_input": input_text,
                "classification": "",
                "gear_type": "",
                "detected_gear_type": "",
                "has_speed_info": False,
                "has_power_info": False,
                "has_ratio_info": False,
                "missing_info": "",
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