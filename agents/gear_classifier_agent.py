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
    speed_info: str # 상세 속도 정보
    has_power_info: bool  # 입출력 파워 정보 유무
    power_info: str # 상세 파워 정보
    has_ratio_info: bool  # 기어비 또는 기어 잇수 정보 유무
    ratio_info: str # 상세 기어비/잇수 정보
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
        
        # 진행 상황을 저장할 리스트 (스레드 안전)
        self.progress_messages = []
        self.progress_lock = asyncio.Lock()
        
    def _initialize_llm(self):
        """LLM 모델 초기화"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OPENAI_API_KEY가 설정되지 않았습니다.")
                
            print(f"LLM 초기화 - Provider: {self.provider}, Model: {self.model_name}, Temperature: {self.temperature}")
            
            if self.provider == "openai":
                return ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=api_key,
                    streaming=False
                )
            else:
                # 기본값은 OpenAI
                return ChatOpenAI(
                    model="gpt-4o-mini",  # 유효한 모델명으로 변경
                    temperature=0.0,
                    api_key=api_key,
                    streaming=False
                )
        except Exception as e:
            import traceback
            error_detail = f"LLM 초기화 오류: {str(e)}\n상세: {traceback.format_exc()}"
            print(error_detail)
            # 폴백으로 기본 모델 시도
            try:
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.0,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
            except Exception as e2:
                print(f"폴백 LLM 초기화도 실패: {e2}")
                raise e  # 원본 에러 다시 던지기
    
    def _classify_input(self, state: GearClassifierState) -> GearClassifierState:
        """사용자 입력이 기어 설계 관련인지 분류"""
        
        # 진행 상황 저장 (Streamlit 컨텍스트 밖에서 안전)
        self.progress_messages.append("🔍 **1단계:** 입력 내용 분석 중...")
        
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
            self.progress_messages.append("🔍 **1단계 완료:** 기어 설계 요청으로 분류됨\n\n")
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
                self.progress_messages.append("🔍 **1단계 완료:** 기어 설계 요청으로 분류됨\n\n")
            else:
                state["classification"] = "not_gear_related"
                self.progress_messages.append("🔍 **1단계 완료:** 기어 설계와 관련없는 요청으로 분류됨\n\n")
                
        except Exception as e:
            import traceback
            error_detail = f"분류 중 오류 발생: {str(e)}\n상세: {traceback.format_exc()}"
            print(error_detail)
            self.progress_messages.append(f"🔍 **1단계 오류:** {str(e)}\n\n")
            # 오류 시 기본적으로 기어 관련으로 처리
            state["classification"] = "gear_related"
        
        return state
    
    def _classify_gear_type(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계 가능 여부 및 기어 타입 분류"""
        
        # 진행 상황 저장
        self.progress_messages.append("⚙️ **2단계:** 기어 타입 분석 중...")
        
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
                gear_type_names = {
                    "GEAR_PAIR": "기어 쌍",
                    "THREE_GEAR": "3단 기어", 
                    "SIMPLE_PLANETARY": "단순 유성기어",
                    "DOUBLE_PINION_PLANETARY": "이중 피니언 유성기어"
                }
                gear_name = gear_type_names.get(gear_type_result, gear_type_result)
                self.progress_messages.append(f"⚙️ **2단계 완료:** {gear_name} 타입으로 인식됨\n\n")
            else:
                state["gear_type"] = "not_designable"
                state["detected_gear_type"] = "unknown"
                self.progress_messages.append("⚙️ **2단계 완료:** 설계 불가능한 기어 타입으로 분류됨\n\n")
                
        except Exception as e:
            import traceback
            error_detail = f"기어 타입 분류 중 오류 발생: {str(e)}\n상세: {traceback.format_exc()}"
            print(error_detail)
            self.progress_messages.append(f"⚙️ **2단계 오류:** {str(e)}\n\n")
            # 오류 시 기본적으로 설계 불가능으로 처리
            state["gear_type"] = "not_designable"
            state["detected_gear_type"] = "unknown"
        
        return state

    def _check_required_info(self, state: GearClassifierState) -> GearClassifierState:
        """필수 설계 정보(Power, 기어비/잇수) 확인"""
        
        # 진행 상황 저장
        self.progress_messages.append("📋 **3단계:** 필수 설계 정보 확인 중...")
        
        system_prompt = """당신은 기어 설계에 필요한 정보를 확인하는 전문가입니다.

사용자의 입력에서 다음 정보가 포함되어 있는지 확인해주세요:

1. **입출력 파워 정보**:     
   1) CASE1: Gear Pair 인 경우 아래의 정보가 모두 포함되어야 함
    - Gear1/Gear2 속도 중 1개 (Gear1/Gear2 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2 파워 중 1개, 또는 Gear1/Gear2 토크 중 1개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2는 사용자의 어휘에 따라 입력/출력 기어 or Pinion/Wheel 기어 등으로 불릴 수 있음
    - 예시1: 입력속도 1000 rpm, 출력토크 50Nm -> OK
    - 예시2: 입력속도 1000 rpm, 출력속도 500 rpm, 출력토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: 입력속도 1000 rpm, 입력파워 100W, 출력토크 50Nm -> NG (입력 파워와 토크 모두 주어짐)

   2) CASE2: Three Gear 
    - Gear1/Gear2/Gear3 의 속도 중 1개 (입/출력 속도가 모두 주어진 경우 기어비와 상충되기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3 의 파워 중 2개, 또는 토크 중 2개 (파워와 토크는 상호 변환 가능. 둘 다 주어지는 경우 상충될 수 있기 때문에 권장하지 않음)
    - Gear1/Gear2/Gear3은 사용자의 어휘에 따라 입력/아이들러/출력 기어 or Pinion/Idler/Wheel 기어 등으로 불릴 수 있음
    - 예시1: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 토크 50Nm -> OK
    - 예시2: Gear1 속도 1000 rpm, Gear2 속도 500 rpm, Gear3 토크 50Nm -> NG (입출력 속도 모두 주어짐)
    - 예시3: Gear1 속도 1000 rpm, Gear2 파워 100W, Gear3 파워 50W -> NG (입력 파워와 토크 모두 주어짐)

   3) CASE3: Simple Planetary, Double Pinion Planetary
    - Sun/Carrier/Ring 의 속도 중 2개 (유성기어의 속도는 3개의 입력 중 2개로 결정되기 때문에 반드시 2개 입력 필요)
    - Sun/Carrier/Ring 의 파워 중 1개, 또는 토크 중 1개 (유성기어의 파워 또는 토크는 1개의 입력과 입력된 속도로 나머지가 모두 계산됨)

    ### 입출력 작동조건 단위 (사용자가 단위계를 입력하지 않은 경우 아래 단위로 간주함)
    - 속도 단위: "rpm" (예: "1000rpm", "3600rpm" 등)
    - 파워 단위: "kW" (예: "100 kW", "5kW" 등) 
    - 토크 단위: "Nm" (예: "50Nm", "200Nm" 등)

2. **기어비 또는 기어 잇수 정보**:
   - 기어비 (예: "3:1", "감속비 10", "기어비 2.5")
   - 기어 잇수 (예: "20치", "30개 이", "teeth 40")

아래 규칙에 따라 답변포멧 형식으로만 응답하세요:
 - 규칙1. 모든 INFO는 YES or NO로 답변한다.
 - 규칙2. 모든 INFO는 YES or NO 뒤의 괄호()안에 상세 정보를 입력하여 답변한다.
 - 규칙3. SPEED_INFO는 답변이 YES인 경우 다음의 형식으로 상세 정보를 기입한다. -> (GEAR1: 속도 [단위], GEAR2: 속도 [단위], ... )
 - 규칙4. POWER_INFO는 답변이 YES인 경우 다음의 형식으로 상세 정보를 기입한다. -> (GEAR1: 출력or토크 [단위], GEAR2: 출력or토크 [단위], ... )
 - 규칙5. RATIO_INFO는 답변이 YES인 경우 다음의 형식으로 상세 정보를 기입한다. -> (기어비: 3) 또는 (Z1: 잇수, Z2: 잇수, ...)
 - 규칙5. 모든 INFO는 답변이 NO 인 경우 괄호()안에 상세 이유를 기입한다.

## 답변포멧
SPEED_INFO: YES or NO (상세정보, 포멧은 규칙 참조)
POWER_INFO: YES or NO (상세정보, 포멧은 규칙 참조)
RATIO_INFO: YES or NO (상세정보, 포멧은 규칙 참조)

## 응답 예시:
사용자 입력: "100W에서 기어비 3:1로 기어쌍 설계해주세요"
응답: 
SPEED_INFO: NO (속도 정보 누락)   
POWER_INFO: NO (파워 전달 기어명칭 정보 누락)
RATIO_INFO: YES (기어비: 3)

사용자 입력: "출력속도 200 rpm, 기어 잇수 23:41로 기어쌍 설계해주세요"
응답: 
SPEED_INFO: YES (GEAR2: 200 [rpm])
POWER_INFO: NO (파워 정보 누락)
RATIO_INFO: YES (Z1: 23, Z2: 41)

사용자 입력: "입력파워 100kW, 입력속도 1000 rpm, 기어비 3:1로 기어쌍 설계해주세요"
응답: 
SPEED_INFO: YES (GEAR1: 1000 [rpm])
POWER_INFO: YES (GEAR1: 100 [kW])
RATIO_INFO: YES (기어비: 3)

사용자 입력: "기어쌍 설계 부탁드립니다"
응답:
SPEED_INFO: NO (속도 정보 누락)
POWER_INFO: NO (파워 정보 누락) 
RATIO_INFO: NO (기어비 정보 누락)
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

            # 상세 정보 추출 및 저장
            import re
            
            # 속도 정보 확인 및 추출
            speed_match = re.search(r'SPEED_INFO:\s*(YES|NO)\s*\((.*?)\)', info_check_result, re.DOTALL)
            if speed_match:
                state["has_speed_info"] = speed_match.group(1) == "YES"
                state["speed_info"] = speed_match.group(2).strip() if speed_match.group(1) == "YES" else ""
            else:
                state["has_speed_info"] = False
                state["speed_info"] = ""
            
            # 파워 정보 확인 및 추출
            power_match = re.search(r'POWER_INFO:\s*(YES|NO)\s*\((.*?)\)', info_check_result, re.DOTALL)
            if power_match:
                state["has_power_info"] = power_match.group(1) == "YES"
                state["power_info"] = power_match.group(2).strip() if power_match.group(1) == "YES" else ""
            else:
                state["has_power_info"] = False
                state["power_info"] = ""
            
            # 기어비/잇수 정보 확인 및 추출  
            ratio_match = re.search(r'RATIO_INFO:\s*(YES|NO)\s*\((.*?)\)', info_check_result, re.DOTALL)
            if ratio_match:
                state["has_ratio_info"] = ratio_match.group(1) == "YES"
                state["ratio_info"] = ratio_match.group(2).strip() if ratio_match.group(1) == "YES" else ""
            else:
                state["has_ratio_info"] = False
                state["ratio_info"] = ""
            
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
                self.progress_messages.append("📋 **3단계 완료:** 모든 필수 정보가 확인됨 ✅\n\n")
            elif len(missing_items) == 1:
                state["missing_info"] = missing_items[0]
                self.progress_messages.append(f"📋 **3단계 완료:** {missing_items[0]} 정보가 누락됨 ⚠️\n\n")
            elif len(missing_items) == 2:
                state["missing_info"] = "_".join(missing_items)
                self.progress_messages.append(f"📋 **3단계 완료:** {missing_items[0]}, {missing_items[1]} 정보가 누락됨 ⚠️\n\n")
            else:  # 모든 정보 누락
                state["missing_info"] = "all"
                self.progress_messages.append("📋 **3단계 완료:** 모든 설계 정보가 누락됨 ⚠️\n\n")
                
        except Exception as e:
            import traceback
            error_detail = f"필수 정보 확인 중 오류 발생: {str(e)}\n상세: {traceback.format_exc()}"
            print(error_detail)
            self.progress_messages.append(f"📋 **3단계 오류:** {str(e)}\n\n")
            # 오류 시 모든 정보가 없다고 가정
            state["has_speed_info"] = False
            state["speed_info"] = ""
            state["has_power_info"] = False
            state["power_info"] = ""
            state["has_ratio_info"] = False
            state["ratio_info"] = ""
            state["missing_info"] = "all"
        
        return state

    def _handle_complete_info(self, state: GearClassifierState) -> GearClassifierState:
        """모든 필수 정보가 있는 경우 처리"""
        
        # 진행 상황 저장
        self.progress_messages.append("🎯 **4단계:** 최종 응답 생성 중...")
        
        gear_type_names = {
            "gear_pair": "기어 쌍",
            "three_gear": "3단 기어",
            "simple_planetary": "단순 유성기어",
            "double_pinion_planetary": "이중 피니언 유성기어"
        }
        
        gear_name = gear_type_names.get(state["detected_gear_type"], "인식된 기어")
        
        # _check_required_info에서 이미 추출된 상세 정보 사용
        speed_info = state["speed_info"] if state["speed_info"] else "명시됨"
        power_info = state["power_info"] if state["power_info"] else "명시됨"
        ratio_info = state["ratio_info"] if state["ratio_info"] else "명시됨"
        
        state["response"] = f"""✅ {gear_name} 설계에 필요한 모든 정보가 확인되었습니다!

📊 **확인된 설계 정보**:
🔧 **설계 타입**: {gear_name}
📋 **요청사항**: {state['user_input']}

🏃 **속도 정보**: {speed_info}
⚡ **파워/토크 정보**: {power_info}  
⚙️ **기어비/잇수 정보**: {ratio_info}

다음 단계로 상세 기어 설계 사양을 생성하겠습니다..."""
        
        return state
    
    def _extract_specific_info(self, user_input: str) -> dict:
        """사용자 입력에서 구체적인 수치 정보를 LLM으로 추출"""
        
        system_prompt = """당신은 기어 설계 정보를 추출하는 전문가입니다. 
주어진 텍스트에서 다음 정보를 정확히 추출해주세요:

1. **속도 정보**: 
   - rpm, 분당회전수, rotation speed 등 모든 속도 관련 표현
   - 어떤 기어인지 명시 (입력/출력, Sun/Carrier/Ring, 기어1/2/3, 피니언 등)
   - 예시: "입력: 1000rpm", "Sun기어: 1200rpm", "출력: 500rpm"

2. **파워/토크 정보**:
   - kW, W, Nm, power, torque 등 모든 파워/토크 관련 표현 
   - 어떤 기어인지 명시 (입력/출력, Sun/Carrier/Ring, 기어1/2/3 등)
   - 예시: "입력: 100kW", "출력: 500Nm", "Ring기어: 2kW"

3. **기어비/잇수 정보**:
   - 기어비, 감속비, 증속비, 잇수, teeth 등 모든 비율/잇수 관련 표현
   - 어떤 기어인지 명시 (Sun/Ring/피니언 등의 잇수)
   - 예시: "기어비 3:1", "감속비 10", "Sun기어: 30치", "피니언: 15치"

**응답 형식** (JSON):
{
  "speed": ["입력: 1000rpm", "출력: 500rpm"],
  "power": ["입력: 100kW", "출력: 500Nm"], 
  "ratio": ["기어비 3:1", "Sun기어: 30치"]
}

**중요 사항**:
- 다양한 언어 표현 (한국어, 영어, 수치 표기법) 모두 처리
- 기어 유형이 명시되지 않은 경우 수치만 기록
- 없는 정보는 빈 배열로 반환
- 중복 제거하여 고유한 값만 포함"""

        try:
            from langchain_core.prompts import ChatPromptTemplate
            
            chat_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "다음 텍스트에서 기어 설계 정보를 추출해주세요:\n\n{text}")
            ])
            
            chain = chat_template | self.llm
            response = chain.invoke({"text": user_input})
            
            # LLM 응답에서 JSON 추출
            response_text = response.content.strip()
            print(f"LLM 정보 추출 응답: {response_text}")
            
            # JSON 파싱 시도
            import json
            import re
            
            # JSON 블록 찾기
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # JSON 블록이 없으면 전체에서 JSON 찾기
                json_match = re.search(r'(\{[^{}]*"speed"[^{}]*\})', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response_text
            
            try:
                extracted_data = json.loads(json_str)
                
                # 결과 검증 및 정리
                result = {
                    "speed": ", ".join(extracted_data.get("speed", [])) if extracted_data.get("speed") else "",
                    "power": ", ".join(extracted_data.get("power", [])) if extracted_data.get("power") else "",
                    "ratio": ", ".join(extracted_data.get("ratio", [])) if extracted_data.get("ratio") else ""
                }
                
                print(f"추출된 정보: {result}")
                return result
                
            except json.JSONDecodeError:
                print(f"JSON 파싱 오류, 폴백 정규식 방식 사용")
                # JSON 파싱 실패 시 폴백으로 정규식 방식 사용
                return self._extract_info_with_regex(user_input)
                
        except Exception as e:
            print(f"LLM 정보 추출 중 오류: {e}")
            # LLM 호출 실패 시 폴백으로 정규식 방식 사용
            return self._extract_info_with_regex(user_input)
    
    def _extract_info_with_regex(self, user_input: str) -> dict:
        """정규식을 사용한 폴백 정보 추출 방식"""
        import re
        
        extracted = {
            "speed": [],
            "power": [],
            "ratio": []
        }
        
        # 간단한 정규식 패턴들 (주요 패턴만)
        speed_patterns = [
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*rpm', ""),
            (r'입력\s*속도\s*(\d+(?:,\d{3})*(?:\.\d+)?)', "입력"),
            (r'출력\s*속도\s*(\d+(?:,\d{3})*(?:\.\d+)?)', "출력")
        ]
        
        power_patterns = [
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*kW', "", "kW"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*W', "", "W"),
            (r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*Nm', "", "Nm")
        ]
        
        ratio_patterns = [
            (r'(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)', "", "ratio"),
            (r'(\d+(?:\.\d+)?)\s*치', "", "teeth")
        ]
        
        # 속도 추출
        for pattern, gear_type in speed_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for match in matches:
                clean_match = match.replace(',', '')
                if gear_type:
                    extracted["speed"].append(f"{gear_type}: {clean_match}rpm")
                else:
                    extracted["speed"].append(f"{clean_match}rpm")
        
        # 파워/토크 추출
        for pattern, gear_type, unit in power_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for match in matches:
                clean_match = match.replace(',', '')
                if gear_type:
                    extracted["power"].append(f"{gear_type}: {clean_match}{unit}")
                else:
                    extracted["power"].append(f"{clean_match}{unit}")
        
        # 기어비/잇수 추출
        for pattern, gear_type, info_type in ratio_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if info_type == "ratio" and ':' in pattern:
                for match in matches:
                    if isinstance(match, tuple):
                        extracted["ratio"].append(f"기어비 {match[0]}:{match[1]}")
            else:
                for match in matches:
                    if info_type == "teeth":
                        extracted["ratio"].append(f"{match}치")
        
        # 결과 정리
        result = {
            "speed": ", ".join(list(set(extracted["speed"]))) if extracted["speed"] else "",
            "power": ", ".join(list(set(extracted["power"]))) if extracted["power"] else "",
            "ratio": ", ".join(list(set(extracted["ratio"]))) if extracted["ratio"] else ""
        }
        
        return result

    def _handle_missing_info(self, state: GearClassifierState) -> GearClassifierState:
        """필수 정보가 누락된 경우 처리"""
        
        # 진행 상황 저장
        self.progress_messages.append("🎯 **4단계:** 누락 정보 안내 응답 생성 중...")
        
        gear_type_names = {
            "gear_pair": "기어 쌍",
            "three_gear": "3단 기어", 
            "simple_planetary": "단순 유성기어",
            "double_pinion_planetary": "이중 피니언 유성기어"
        }
        
        gear_name = gear_type_names.get(state["detected_gear_type"], "인식된 기어")
        
        # 누락된 정보의 상세 사유를 포함하여 메시지 생성
        missing_details = []
        
        if not state["has_speed_info"]:
            speed_reason = state.get("speed_info", "속도 정보 누락")
            missing_details.append(f"**🏃 속도 정보**: {speed_reason}")
        
        if not state["has_power_info"]:
            power_reason = state.get("power_info", "파워/토크 정보 누락")
            missing_details.append(f"**⚡ 파워/토크 정보**: {power_reason}")
        
        if not state["has_ratio_info"]:
            ratio_reason = state.get("ratio_info", "기어비/잇수 정보 누락")
            missing_details.append(f"**⚙️ 기어비/잇수 정보**: {ratio_reason}")
        
        # 누락된 정보 개수에 따른 예시 생성
        missing_count = len(missing_details)
        if missing_count == 3:
            examples = """
📋 **종합 입력 예시**:
• "1000rpm 입력속도, 100W 파워로 기어비 3:1인 기어쌍 설계"
• "입력속도 1800rpm, 출력토크 50Nm, 감속비 5인 유성기어 설계"
• "선기어 속도 1000rpm, 캐리어 속도 500rpm, Ring 출력 2kW인 유성기어 설계\""""
        elif missing_count == 2:
            if not state["has_speed_info"] and not state["has_power_info"]:
                examples = """
📋 **속도/파워 정보 예시**:
• 속도: "1000rpm", "1800rpm" (입력 또는 출력)
• 파워: "100W", "2kW" / 토크: "50Nm", "200Nm\""""
            elif not state["has_speed_info"] and not state["has_ratio_info"]:
                examples = """
📋 **속도/기어비 정보 예시**:
• 속도: "1000rpm", "1800rpm"
• 기어비: "3:1", "감속비 5" / 잇수: "20치", "40치\""""
            else:  # power와 ratio 누락
                examples = """
📋 **파워/기어비 정보 예시**:
• 파워: "100W", "2kW" / 토크: "50Nm", "200Nm"
• 기어비: "3:1", "감속비 5" / 잇수: "20치", "40치\""""
        else:  # 1개 누락
            if not state["has_speed_info"]:
                examples = """
📋 **속도 정보 예시**:
• 입력/출력 속도: "1000rpm", "1800rpm"
• 유성기어의 경우: "Sun속도 1000rpm", "Carrier속도 500rpm\""""
            elif not state["has_power_info"]:
                examples = """
📋 **파워/토크 정보 예시**:
• 파워: "100W", "2kW"
• 토크: "50Nm", "200Nm\""""
            else:  # ratio 누락
                examples = """
📋 **기어비/잇수 정보 예시**:
• 기어비: "3:1", "감속비 5", "기어비 2.5"
• 기어 잇수: "20치", "40치", "60치\""""

        state["response"] = f"""⚠️ {gear_name} 설계를 위해 추가 정보가 필요합니다.

🔧 **설계 타입**: {gear_name}
📝 **현재 요청**: {state['user_input']}

❌ **누락된 정보 상세**:
{chr(10).join(missing_details)}

{examples}

위 정보를 포함하여 다시 요청해 주세요! 🙂"""
        
        return state

    def _handle_non_designable_gear(self, state: GearClassifierState) -> GearClassifierState:
        """설계 불가능한 기어 처리"""  
        
        # 진행 상황 저장
        self.progress_messages.append("🎯 **최종:** 설계 가능한 기어 옵션 안내 중...")
        
        # 특별한 응답 플래그를 포함하여 app.py에서 UI를 표시하도록 함
        state["response"] = f"""기어설계 AI Agent가 설계 가능한 기어는 다음과 같습니다.

🔧 **설계 가능한 기어 타입을 선택해 주세요:**

[SHOW_GEAR_OPTIONS]"""
        return state
    
    def _handle_non_gear_related(self, state: GearClassifierState) -> GearClassifierState:
        """기어 설계와 관련없는 질문 처리"""
        
        # 진행 상황 저장
        self.progress_messages.append("🎯 **최종:** 기어 설계 관련 안내 응답 생성 중...")
        
        state["response"] = """안녕하세요. 저는 기어 설계 전문 AI Agent입니다. 

다음과 같은 기어 설계 관련 요청에 도움을 드릴 수 있습니다:
- 기어 치형설계
- 기어 강도평가
- 기어 효율계산
- 기어 소음개선
- 기어 설계 최적화

- 설계 가능 기어 타입: 인볼류트 치형의 기어 쌍, 3단 기어, 단순 유성기어, 더블 피니언 유성기어
- 설계 불가능 기어 타입: 웜기어, 베벨기어, 스퍼기어 등 기타 특수 기어
- 설계를 위한 필수요구 조건: 입출력 속도, 입출력 파워/토크, 기어비/잇수 정보

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
            # 진행 상황 초기화
            self.progress_messages = []
            
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
                "speed_info": "",
                "has_power_info": False,
                "power_info": "",
                "has_ratio_info": False,
                "ratio_info": "",
                "missing_info": "",
                "response": ""
            }
            
            # 처리 시작 알림
            callback("🚀 **기어 설계 요청 분석을 시작합니다...**\n\n")
            
            print(f"그래프 실행 시작 - 입력: {input_text}")
            print(f"초기 상태: {initial_state}")
            
            # 진행 상황을 주기적으로 업데이트하기 위한 태스크 생성
            progress_task = asyncio.create_task(self._update_progress_periodically(callback))
            
            # 그래프 실행
            try:
                result = await asyncio.to_thread(self.graph.invoke, initial_state)
                print(f"그래프 실행 완료 - 결과: {result}")
            except Exception as graph_error:
                print(f"그래프 실행 중 오류: {graph_error}")
                import traceback
                print(f"그래프 실행 오류 상세: {traceback.format_exc()}")
                raise graph_error
            finally:
                # 진행 상황 업데이트 태스크 종료
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
            
            # 결과 처리
            response_text = result["response"]
            
            # 최종 진행 상황과 결과 표시
            all_progress = "".join(self.progress_messages)
            final_display = f"{all_progress}\n🎉 **분석 완료!** 결과를 표시합니다:\n\n---\n\n{response_text}"
            callback(final_display)
            
            # 최종 응답을 메시지에 추가
            self.add_message("assistant", response_text)
            return response_text
        
        except Exception as e:
            import traceback
            error_msg = f"오류 발생: {str(e)}\n\n상세 오류:\n{traceback.format_exc()}"
            print(f"gear_classifier_agent 오류: {error_msg}")  # 콘솔에 출력
            callback(error_msg)
            self.add_message("assistant", error_msg)
            return error_msg
    
    async def _update_progress_periodically(self, callback):
        """진행 상황을 주기적으로 업데이트"""
        last_message_count = 0
        try:
            while True:
                await asyncio.sleep(0.5)  # 0.5초마다 체크
                
                if len(self.progress_messages) > last_message_count:
                    # 새로운 진행 메시지가 있으면 업데이트
                    current_progress = "".join(self.progress_messages)
                    callback(current_progress)
                    last_message_count = len(self.progress_messages)
        except asyncio.CancelledError:
            # 정상적인 종료
            pass