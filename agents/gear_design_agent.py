"""
기어 설계 에이전트
gear_classifier_agent로부터 수집된 정보를 활용해서 실제 기어 설계를 수행
LangGraph 기반 워크플로우 구현
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, TypedDict, Annotated
import datetime
import re
from io import BytesIO
from PIL import Image

# 상위 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from gear_design_manager import GearDesignManager
from utils.llm import llm_call

# LangGraph 관련 imports
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class GearDesignState(TypedDict):
    """기어 설계 상태를 정의하는 TypedDict"""
    messages: Annotated[list, add_messages]
    user_input: str  # 사용자 입력

    # 파싱된 기어 정보
    gear_type: str  # gear_pair, three_gear, simple_planetary, double_pinion_planetary
    speed_info: str  # 속도 정보
    power_info: str  # 파워/토크 정보
    ratio_info: str  # 기어비/잇수 정보  
    others_info: str  # 추가 기어 정보
    
    # 설계 프로세스 상태
    gear_info_parsed: bool  # 기어 정보 파싱 완료 여부
    specs_displayed: bool  # 기어 제원 표시 완료 여부
    user_approved: bool  # 사용자 승인 여부
    user_requested_changes: bool  # 사용자 수정 요청 여부
    config_modified: bool  # JSON 설정 수정 완료 여부
    manager_initialized: bool  # GearDesignManager 초기화 완료 여부
    geometry_calculated: bool  # 기하학적 계산 완료 여부
    rating_calculated: bool  # 강도 평가 계산 완료 여부
    design_completed: bool  # 전체 설계 완료 여부
    
    # 설계 데이터 및 결과
    template_config: Dict[str, Any]  # 원본 템플릿 설정
    modified_config: Dict[str, Any]  # 수정된 설정
    gear_specs_summary: str  # 기어 제원 요약 (사용자에게 표시용)
    user_feedback: str  # 사용자 피드백/수정 요청
    geometry_result: Any  # 기하학적 계산 결과
    rating_result: Any  # 강도 평가 결과
    messages_from_calc: str  # 계산에서 나온 메시지들
    image_path: str  # 기어 이미지 경로
    
    # 오류 및 응답
    error_occurred: bool  # 오류 발생 여부
    error_message: str  # 오류 메시지
    response: str  # 최종 응답


class GearDesignAgent(BaseAgent):
    """기어 설계 에이전트 - LangGraph 기반"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 경로 설정
        self.gear_design_path = config.get(
            'gear_design_path', 
            r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"
        )
        self.template_json_path = config.get(
            'template_json_path',
            str(Path(__file__).parent.parent / "TestGD.GD1")
        )
        
        # GearDesignManager 초기화는 필요시에만 수행
        self.manager = None
        
        # 결과 저장 경로
        self.output_dir = Path(__file__).parent.parent
        
        # 진행 상황 메시지 저장
        self.progress_messages = []
        
        # LangChain LLM 초기화
        self.model_name = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.0)
        self.llm = self._initialize_llm()
        
        # LangGraph 워크플로우 구성
        self.graph = self._build_graph()
        
    def _initialize_llm(self):
        """LangChain LLM 초기화"""
        try:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                streaming=True
            )
        except Exception as e:
            print(f"LLM 초기화 실패: {e}")
            return None
        
    def initialize_gear_manager(self):
        """GearDesignManager 초기화"""
        if self.manager is None:
            try:
                self.manager = GearDesignManager(
                    self.gear_design_path,
                    self.template_json_path
                )
                
                # Form 초기화
                if not self.manager.initialize_form():
                    raise Exception("Form 초기화 실패")
                    
                # 기본 템플릿 로드
                self.template_config = self.load_template_config()
                
                return True
            except Exception as e:
                print(f"GearDesignManager 초기화 실패: {e}")
                return False
        return True
    
    def load_template_config(self) -> Dict[str, Any]:
        """템플릿 JSON 설정 파일 로드"""
        try:
            with open(self.template_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"템플릿 설정 로드 실패: {e}")
            return {}
    
    async def process_with_callback(self, user_input: str, callback=None) -> str:
        """사용자 입력을 받아서 LangGraph 워크플로우를 실행"""
        try:
            # 진행 상황 초기화
            self.progress_messages = []            

            # 사용자 메시지 추가
            self.add_message("user", user_input)            

            # 콜백 함수 저장
            self.callback = callback
            
            # 초기 상태 생성
            initial_state: GearDesignState = {
                "user_input": user_input,
                "messages": self.messages.copy(),
                
                # 파싱된 기어 정보 초기화
                "gear_type": "",
                "speed_info": "",
                "power_info": "",
                "ratio_info": "",
                "others_info": "",
                
                # 설계 프로세스 상태 초기화
                "gear_info_parsed": False,
                "specs_displayed": False,
                "user_approved": False,
                "user_requested_changes": False,
                "config_modified": False,
                "manager_initialized": False,
                "geometry_calculated": False,
                "rating_calculated": False,
                "design_completed": False,
                
                # 설계 데이터 및 결과 초기화
                "template_config": {},
                "modified_config": {},
                "gear_specs_summary": "",
                "user_feedback": "",
                "geometry_result": None,
                "rating_result": None,
                "messages_from_calc": "",
                "image_path": "",
                
                # 오류 및 응답 초기화
                "error_occurred": False,
                "error_message": "",
                "response": ""
            }
            
            # 진행 상황 알림
            if callback:
                callback("🚀 **기어 설계 워크플로우를 시작합니다...**\\n\\n")
            
            # LangGraph 워크플로우 실행
            result = self.graph.invoke(initial_state)            
            
            # state 저장 (gear_agent에서 접근할 수 있도록)
            self.state = result
            
            # 오류 발생 여부 확인 및 처리
            if result.get("error_occurred", False):
                error_msg = result.get("error_message", "알 수 없는 오류")
                response_text = f"❌ 기어 설계 중 오류가 발생했습니다: {error_msg}"
                if callback:
                    callback(response_text)
                self.add_message("assistant", response_text)
                return response_text
            
            # 정상 처리된 경우
            response_text = result.get("response", "")
            
            # 최종 응답을 메시지에 추가
            self.add_message("assistant", response_text)

            # 최종 응답 반환
            return response_text
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ 기어 설계 워크플로우 실행 중 오류 발생: {str(e)}\n{error_detail}"
            if callback:
                callback(error_msg)
            self.add_message("assistant", error_msg)
            return error_msg
    
    # ===========================================
    # LangGraph 노드 메서드들
    # ===========================================
    
    def _receive_gear_info_node(self, state: GearDesignState) -> GearDesignState:
        """1단계: gear_classifier_agent로부터 기어 정보 수신"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("📥 **1단계:** 기어 설계 정보 수신 중...")
            
            if self.callback:
                self.callback("📥 **기어 정보 수신 중**\n\n" \
                "gear_classifier_agent로부터 설계 정보를 받고 있습니다...")
            
            # shared_data에서 classifier 결과 확인
            if self.has_shared_data("classifier_result"):
                # shared_data에서 classifier 결과 가져오기
                classifier_data = self.get_shared_data("classifier_result")
                
                # classifier 결과에서 정보 직접 매핑
                state["gear_type"] = classifier_data.get("gear_type", "")
                state["speed_info"] = classifier_data.get("speed_info", "")
                state["power_info"] = classifier_data.get("power_info", "")
                state["ratio_info"] = classifier_data.get("ratio_info", "")
                state["others_info"] = classifier_data.get("others_info", "")

                if classifier_data.get("others_info", "") == "none":
                    state["gear_info_parsed"] = True
                    self.progress_messages.append("✅ **1단계 완료:** shared_data에서 classifier 결과 수신 성공")

                else:
                    state["gear_info_parsed"] = False   
                    self.progress_messages.append("✅ **1단계 종료:** shared_data에서 classifier 결과 수신 실패")              
                    
            else:
                state["gear_info_parsed"] = False   
                self.progress_messages.append("✅ **1단계 종료:** shared_data에서 classifier 결과 수신 실패")         
            
        except Exception as e:
            error_msg = f"기어 정보 수신 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **1단계 오류:** {error_msg}")
        
        return state
    
    def _display_gear_specs_node(self, state: GearDesignState) -> GearDesignState:
        """2단계: 기어 제원 표시 및 사용자 승인 요청"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("📋 **2단계:** 기어 제원 생성 및 표시 중...")
            
            if self.callback:
                self.callback("📋 **기어 제원 준비 중**\\n\\n수신된 정보를 바탕으로 기어 제원을 생성하고 있습니다...")
            
            # 기어 제원 요약 생성
            gear_specs = self._generate_gear_specs_summary(state)
            state["gear_specs_summary"] = gear_specs
            state["specs_displayed"] = True
            
            # 사용자에게 제원 표시 및 승인 요청
            approval_message = f"""🔧 **기어 설계 제원 확인**

{gear_specs}

📝 **승인 또는 수정 요청:**
- **승인**: "승인" 또는 "확인" 또는 "진행" 입력
- **수정**: 수정하고 싶은 내용을 구체적으로 입력해 주세요
  예: "모듈을 3.0으로 변경", "기어비를 4:1로 수정", "압력각을 25도로 변경"

**어떻게 하시겠습니까?**"""
            
            state["response"] = approval_message
            
            self.progress_messages.append("✅ **2단계 완료:** 기어 제원 표시 및 승인 대기")
            
        except Exception as e:
            error_msg = f"기어 제원 표시 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **2단계 오류:** {error_msg}")
        
        return state
    
    def _generate_gear_specs_summary(self, state: GearDesignState) -> str:
        """기어 제원 요약 생성"""
        try:
            gear_type_names = {
                "gear_pair": "기어 쌍",
                "three_gear": "3단 기어",
                "simple_planetary": "단순 유성기어",
                "double_pinion_planetary": "이중 피니언 유성기어"
            }
            
            gear_name = gear_type_names.get(state.get("gear_type", ""), "기어")
            
            specs_lines = [
                f"🔧 **기어 타입**: {gear_name}",
                ""
            ]
            
            # 작동 조건
            specs_lines.append("⚡ **작동 조건:**")
            if state.get("speed_info"):
                specs_lines.append(f"  • 속도: {state['speed_info']}")
            if state.get("power_info"):
                specs_lines.append(f"  • 파워/토크: {state['power_info']}")
            
            specs_lines.append("")
            
            # 기어 제원
            specs_lines.append("⚙️ **기어 제원:**")
            if state.get("ratio_info"):
                specs_lines.append(f"  • 기어비/잇수: {state['ratio_info']}")
            
            # 추가 제원에서 개별 항목 추출
            if state.get("others_info"):
                others = state["others_info"]
                
                # 모듈 정보 추출
                module_match = re.search(r'모듈\s*([0-9.]+)', others)
                if module_match:
                    specs_lines.append(f"  • 모듈: {module_match.group(1)} mm")
                else:
                    specs_lines.append("  • 모듈: 6.0 mm (기본값)")
                
                # 압력각 정보 추출
                pressure_angle_match = re.search(r'압력각\s*([0-9.]+)', others)
                if pressure_angle_match:
                    specs_lines.append(f"  • 압력각: {pressure_angle_match.group(1)}°")
                else:
                    specs_lines.append("  • 압력각: 20° (기본값)")
                
                # 치폭 정보 추출
                face_width_match = re.search(r'치폭\s*([0-9.]+)', others)
                if face_width_match:
                    specs_lines.append(f"  • 치폭: {face_width_match.group(1)} mm")
                else:
                    specs_lines.append("  • 치폭: 44 mm (기본값)")
                
                # 재료 정보 추출
                material_match = re.search(r'재료\s*([A-Za-z0-9\s가-힣]+)', others)
                if material_match:
                    specs_lines.append(f"  • 재료: {material_match.group(1)}")
                else:
                    specs_lines.append("  • 재료: DIN 18CrNiMo7 (기본값)")
            else:
                # 기본값들 표시
                specs_lines.extend([
                    "  • 모듈: 6.0 mm (기본값)",
                    "  • 압력각: 20° (기본값)", 
                    "  • 치폭: 44 mm (기본값)",
                    "  • 재료: DIN 18CrNiMo7 (기본값)"
                ])
            
            specs_lines.append("")
            specs_lines.append("🏭 **윤활:** Oil: Kluberoil GEM 1-220 N (기본값)")
            
            return "\\n".join(specs_lines)
            
        except Exception as e:
            print(f"기어 제원 요약 생성 오류: {e}")
            return "기어 제원 생성 중 오류가 발생했습니다."
    
    def _process_user_response_node(self, state: GearDesignState) -> GearDesignState:
        """3단계: 사용자 응답 처리 (승인 또는 수정 요청)"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("👤 **3단계:** 사용자 응답 처리 중...")
            
            if self.callback:
                self.callback("👤 **사용자 응답 분석 중**\\n\\n사용자의 승인 또는 수정 요청을 분석하고 있습니다...")
            
            # 사용자 피드백 저장
            user_input = state["user_input"]
            state["user_feedback"] = user_input
            
            # LLM을 사용해서 사용자 의도 분석
            system_prompt = f"""
사용자의 응답을 분석해서 승인인지 수정 요청인지 판단하세요.
현재 표시된 기어 제원:
{state.get('gear_specs_summary', '')}

사용자 응답을 분석해서 다음 JSON 형태로 반환하세요:
{{
  "intent": "approve|modify", 
  "modifications": "수정 내용 (approve인 경우 빈 문자열)"
}}

승인 키워드: 승인, 확인, 진행, OK, ok, 좋습니다, 맞습니다
수정 키워드: 변경, 수정, 바꾸기, 다르게, 틀린
"""
            
            prompt = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"사용자 응답: {user_input}"}
            ]
            
            response = llm_call(prompt=prompt, model="gpt-4o-mini")
            response = re.sub(r'```json\\s*|\\s*```', '', response).strip()
            
            intent_info = json.loads(response)
            
            if intent_info.get("intent") == "approve":
                state["user_approved"] = True
                state["user_requested_changes"] = False
                self.progress_messages.append("✅ **3단계 완료:** 사용자 승인 확인")
            else:
                state["user_approved"] = False
                state["user_requested_changes"] = True
                # 수정 요청 내용을 저장
                modifications = intent_info.get("modifications", user_input)
                state["user_feedback"] = modifications
                self.progress_messages.append("🔄 **3단계 완료:** 사용자 수정 요청 확인")
            
        except Exception as e:
            error_msg = f"사용자 응답 처리 오류: {e}"
            print(error_msg)
            # 오류 시 기본적으로 승인으로 처리
            state["user_approved"] = True
            state["user_requested_changes"] = False
            self.progress_messages.append(f"⚠️ **3단계 경고:** {error_msg} - 승인으로 처리")
        
        return state
    
    def _handle_modifications_node(self, state: GearDesignState) -> GearDesignState:
        """4단계: 사용자 수정 요청 처리"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("🔧 **4단계:** 기어 제원 수정 중...")
            
            if self.callback:
                self.callback("🔧 **기어 제원 수정 중**\\n\\n사용자 요청에 따라 기어 제원을 수정하고 있습니다...")
            
            # 수정 요청 내용 분석 및 적용
            modifications = state.get("user_feedback", "")
            
            # 기존 정보 업데이트
            self._apply_user_modifications(state, modifications)
            
            # 수정된 제원 요약 재생성
            updated_specs = self._generate_gear_specs_summary(state)
            state["gear_specs_summary"] = updated_specs
            
            # 수정된 제원을 다시 표시
            approval_message = f"""🔧 **수정된 기어 설계 제원**

{updated_specs}

📝 **재승인 또는 추가 수정:**
- **승인**: "승인" 또는 "확인" 또는 "진행" 입력
- **추가 수정**: 추가로 수정하고 싶은 내용을 입력해 주세요

**수정된 제원으로 진행하시겠습니까?**"""
            
            state["response"] = approval_message
            state["user_requested_changes"] = False  # 수정 완료
            
            self.progress_messages.append("✅ **4단계 완료:** 기어 제원 수정 완료")
            
        except Exception as e:
            error_msg = f"수정 처리 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **4단계 오류:** {error_msg}")
        
        return state
    
    def _apply_user_modifications(self, state: GearDesignState, modifications: str):
        """사용자 수정 요청을 상태에 적용"""
        try:
            # 모듈 수정
            module_match = re.search(r'모듈.*?([0-9.]+)', modifications)
            if module_match:
                new_module = module_match.group(1)
                # others_info에 반영
                current_others = state.get("others_info", "")
                if re.search(r'모듈\s*[0-9.]+', current_others):
                    state["others_info"] = re.sub(r'모듈\s*[0-9.]+', f'모듈 {new_module}', current_others)
                else:
                    state["others_info"] = f"{current_others}, 모듈 {new_module}".strip(", ")
            
            # 기어비 수정
            ratio_match = re.search(r'기어비.*?([0-9.:]+)', modifications)
            if ratio_match:
                new_ratio = ratio_match.group(1)
                state["ratio_info"] = f"기어비: {new_ratio}"
            
            # 압력각 수정
            pressure_match = re.search(r'압력각.*?([0-9.]+)', modifications)
            if pressure_match:
                new_pressure = pressure_match.group(1)
                current_others = state.get("others_info", "")
                if re.search(r'압력각\s*[0-9.]+', current_others):
                    state["others_info"] = re.sub(r'압력각\s*[0-9.]+', f'압력각 {new_pressure}', current_others)
                else:
                    state["others_info"] = f"{current_others}, 압력각 {new_pressure}".strip(", ")
            
            # 치폭 수정
            face_width_match = re.search(r'치폭.*?([0-9.]+)', modifications)
            if face_width_match:
                new_face_width = face_width_match.group(1)
                current_others = state.get("others_info", "")
                if re.search(r'치폭\s*[0-9.]+', current_others):
                    state["others_info"] = re.sub(r'치폭\s*[0-9.]+', f'치폭 {new_face_width}', current_others)
                else:
                    state["others_info"] = f"{current_others}, 치폭 {new_face_width}".strip(", ")
                    
        except Exception as e:
            print(f"수정 적용 오류: {e}")
    
    def _initialize_manager_node(self, state: GearDesignState) -> GearDesignState:
        """2단계: GearDesignManager 초기화 및 템플릿 로드"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("⚙️ **2단계:** 기어 설계 시스템 초기화 중...")
            
            if self.callback:
                self.callback("⚙️ **시스템 초기화 중**\\n\\nGearDesignManager를 초기화하고 템플릿을 로드하고 있습니다...")
            
            # GearDesignManager 초기화
            if not self.initialize_gear_manager():
                raise Exception("GearDesignManager 초기화 실패")
            
            # 템플릿 설정 로드
            template_config = self.load_template_config()
            if not template_config:
                raise Exception("템플릿 설정 로드 실패")
            
            state["template_config"] = template_config
            state["manager_initialized"] = True
            
            self.progress_messages.append("✅ **2단계 완료:** 시스템 초기화 성공")
            
        except Exception as e:
            error_msg = f"시스템 초기화 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **2단계 오류:** {error_msg}")
        
        return state
    
    def _modify_config_node(self, state: GearDesignState) -> GearDesignState:
        """3단계: 기어 정보를 바탕으로 JSON 설정 수정"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("🔧 **3단계:** 설계 파라미터 설정 중...")
            
            if self.callback:
                self.callback("🔧 **설계 파라미터 설정 중**\\n\\n기어 정보를 바탕으로 JSON 설정을 수정하고 있습니다...")
            
            # JSON 설정 수정
            modified_config = self.modify_config_from_gear_info(state)
            
            state["modified_config"] = modified_config
            state["config_modified"] = True
            
            self.progress_messages.append("✅ **3단계 완료:** 설계 파라미터 설정 완료")
            
        except Exception as e:
            error_msg = f"설정 수정 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **3단계 오류:** {error_msg}")
        
        return state
    
    def _perform_calculation_node(self, state: GearDesignState) -> GearDesignState:
        """4단계: 기어 설계 계산 수행 (기하학적 계산 + 강도 평가)"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("📊 **4단계:** 기어 설계 계산 수행 중...")
            
            if self.callback:
                self.callback("📊 **기어 계산 수행 중**\\n\\n기하학적 계산 및 강도 평가를 수행하고 있습니다...")
            
            # 1. 설정 로드 및 검증
            if not self.manager.load_and_validate_config(state["modified_config"]):
                raise Exception("설정 로드 및 검증 실패")
            
            # 2. 기하학적 계산
            geometry_result = self.manager.calculate_geometry()
            if not geometry_result:
                raise Exception("기하학적 계산 실패")
            
            state["geometry_result"] = geometry_result
            state["geometry_calculated"] = True
            
            # 3. 하중 계산
            rating_result = self.manager.calculate_load_case(geometry_result)
            if not rating_result:
                raise Exception("하중 계산 실패")
            
            state["rating_result"] = rating_result
            state["rating_calculated"] = True
            
            # 4. 메시지 추출
            messages = self.manager.get_messages()
            state["messages_from_calc"] = messages or ""
            
            self.progress_messages.append("✅ **4단계 완료:** 기어 설계 계산 성공")
            
        except Exception as e:
            error_msg = f"기어 설계 계산 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            self.progress_messages.append(f"❌ **4단계 오류:** {error_msg}")
        
        return state
    
    def _generate_results_node(self, state: GearDesignState) -> GearDesignState:
        """5단계: 결과 생성 (이미지 생성 + 최종 보고서)"""
        try:
            # 진행 상황 저장
            self.progress_messages.append("🎨 **5단계:** 결과 생성 중...")
            
            if self.callback:
                self.callback("🎨 **결과 생성 중**\\n\\n기어 이미지 생성 및 최종 보고서를 작성하고 있습니다...")
            
            # 1. 기어 이미지 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.output_dir / f"gear_image_{timestamp}.png"
            image_success = self.manager.get_gearimage(str(image_path))
            
            if image_success:
                state["image_path"] = str(image_path)
            
            # 2. 최종 결과 포맷팅
            result_summary = self.format_design_results(
                state["geometry_result"], 
                state["rating_result"], 
                state["messages_from_calc"], 
                str(image_path) if image_success else None
            )
            
            state["response"] = result_summary
            state["design_completed"] = True
            
            self.progress_messages.append("✅ **5단계 완료:** 기어 설계 완료!")
            
        except Exception as e:
            error_msg = f"결과 생성 오류: {e}"
            print(error_msg)
            state["error_occurred"] = True
            state["error_message"] = error_msg
            state["response"] = f"❌ 기어 설계 중 오류 발생: {error_msg}"
            self.progress_messages.append(f"❌ **5단계 오류:** {error_msg}")
        
        return state
    
    # ===========================================
    # 라우팅 메서드들
    # ===========================================
    
    def _route_after_receive(self, state: GearDesignState) -> str:
        """기어 정보 수신 후 라우팅"""
        if state.get("error_occurred", False):
            return END
        elif state.get("gear_info_parsed", False):
            return "display_specs"
        else:
            return END
    
    def _route_after_display(self, state: GearDesignState) -> str:
        """제원 표시 후 라우팅 - 사용자 응답 대기"""
        if state.get("error_occurred", False):
            return END
        elif state.get("specs_displayed", False):
            return "process_user_response"
        else:
            return END
    
    def _route_after_user_response(self, state: GearDesignState) -> str:
        """사용자 응답 처리 후 라우팅"""
        if state.get("error_occurred", False):
            return END
        elif state.get("user_approved", False):
            return "initialize_manager"
        elif state.get("user_requested_changes", False):
            return "handle_modifications"
        else:
            return END
    
    def _route_after_modifications(self, state: GearDesignState) -> str:
        """수정 처리 후 라우팅 - 다시 사용자 응답 대기"""
        if state.get("error_occurred", False):
            return END
        else:
            return "process_user_response"
    
    def _route_after_initialization(self, state: GearDesignState) -> str:
        """초기화 완료 후 라우팅"""
        if state.get("error_occurred", False):
            return END
        elif state.get("manager_initialized", False):
            return "modify_config"
        else:
            return END
    
    def _route_after_config_modification(self, state: GearDesignState) -> str:
        """설정 수정 완료 후 라우팅"""
        if state.get("error_occurred", False):
            return END
        elif state.get("config_modified", False):
            return "perform_calculation"
        else:
            return END
    
    def _route_after_calculation(self, state: GearDesignState) -> str:
        """계산 완료 후 라우팅"""
        if state.get("error_occurred", False):
            return END
        elif state.get("rating_calculated", False):
            return "generate_results"
        else:
            return END
    
    # ===========================================
    # 워크플로우 구성
    # ===========================================
    
    def _build_graph(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(GearDesignState)
        
        # 노드 추가
        workflow.add_node("receive_gear_info", self._receive_gear_info_node)
        workflow.add_node("display_specs", self._display_gear_specs_node)
        workflow.add_node("process_user_response", self._process_user_response_node)
        workflow.add_node("handle_modifications", self._handle_modifications_node)
        workflow.add_node("initialize_manager", self._initialize_manager_node)
        workflow.add_node("modify_config", self._modify_config_node)
        workflow.add_node("perform_calculation", self._perform_calculation_node)
        workflow.add_node("generate_results", self._generate_results_node)
        # 시작점 설정
        workflow.set_entry_point("receive_gear_info")
        
        # 조건부 라우팅 설정
        workflow.add_conditional_edges(
            "receive_gear_info",
            self._route_after_receive,
            {
                "display_specs": "display_specs"
            }
        )
        
        workflow.add_conditional_edges(
            "display_specs",
            self._route_after_display,
            {
                "process_user_response": "process_user_response"
            }
        )
        
        workflow.add_conditional_edges(
            "process_user_response",
            self._route_after_user_response,
            {
                "initialize_manager": "initialize_manager",
                "handle_modifications": "handle_modifications"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_modifications",
            self._route_after_modifications,
            {
                "process_user_response": "process_user_response"
            }
        )
        
        workflow.add_conditional_edges(
            "initialize_manager",
            self._route_after_initialization,
            {
                "modify_config": "modify_config"
            }
        )
        
        workflow.add_conditional_edges(
            "modify_config",
            self._route_after_config_modification,
            {
                "perform_calculation": "perform_calculation"
            }
        )
        
        workflow.add_conditional_edges(
            "perform_calculation",
            self._route_after_calculation,
            {
                "generate_results": "generate_results"
            }
        )
        
        # generate_results는 END로 직접 연결
        workflow.add_edge("generate_results", END)
        
        return workflow.compile()

    # ===========================================
    # 기존 헬퍼 메서드들 (상태 기반으로 수정)
    # ===========================================
    
    def modify_config_from_gear_info(self, state: GearDesignState) -> Dict[str, Any]:
        """기어 정보를 바탕으로 JSON 설정을 수정"""
        modified_config = state["template_config"].copy()
        
        try:
            # 1. 기어 타입 설정 (GearTypeNum)
            gear_type_map = {
                "gear_pair": 0,
                "three_gear": 1,
                "simple_planetary": 2,
                "double_pinion_planetary": 3
            }
            
            gear_type = state.get("gear_type", "gear_pair")
            if gear_type in gear_type_map:
                modified_config["Basic Data"]["GearTypeNum"] = gear_type_map[gear_type]
            
            # 2. 기어비/잇수 정보 처리
            ratio_info = state.get("ratio_info", "")
            if ratio_info:
                self.apply_ratio_info(modified_config, ratio_info, gear_type)
            
            # 3. 파워/속도 정보를 Load spectrum에 반영
            power_info = state.get("power_info", "")
            speed_info = state.get("speed_info", "")
            if power_info or speed_info:
                self.apply_load_spectrum(modified_config, power_info, speed_info)
            
            # 4. 추가 정보 처리 (모듈, 치폭 등)
            others_info = state.get("others_info", "")
            if others_info:
                self.apply_others_info(modified_config, others_info)
            
            # 5. CDMethod를 1로 설정 (중심거리 자동계산)
            modified_config["Basic Data"]["CDMethod"] = 1
            
            return modified_config
            
        except Exception as e:
            print(f"설정 수정 오류: {e}")
            return state["template_config"]
    
    def apply_ratio_info(self, config: Dict[str, Any], ratio_info: str, gear_type: str):
        """기어비/잇수 정보를 JSON에 반영"""
        try:
            # 기어비 패턴 매칭
            gear_ratio_pattern = r'기어비[:\s]*([0-9.]+)'
            ratio_pattern = r'([0-9]+)[:\s]*([0-9]+)'
            teeth_pattern = r'[zZ]?1[:\s]*([0-9]+)[,\s]*[zZ]?2[:\s]*([0-9]+)'
            
            if re.search(gear_ratio_pattern, ratio_info):
                # 기어비 정보
                match = re.search(gear_ratio_pattern, ratio_info)
                if match:
                    ratio = float(match.group(1))
                    if gear_type == "gear_pair":
                        # 기본적인 잇수 설정 (ratio 기준)
                        z1 = 25  # 기본값
                        z2 = int(z1 * ratio)
                        config["Basic Data"]["z1"] = str(z1)
                        config["Basic Data"]["z2"] = str(z2)
            
            elif re.search(teeth_pattern, ratio_info):
                # 잇수 정보
                match = re.search(teeth_pattern, ratio_info)
                if match:
                    z1 = int(match.group(1))
                    z2 = int(match.group(2))
                    config["Basic Data"]["z1"] = str(z1)
                    config["Basic Data"]["z2"] = str(z2)
            
            elif re.search(ratio_pattern, ratio_info):
                # 일반적인 비율 정보
                match = re.search(ratio_pattern, ratio_info)
                if match:
                    z1 = int(match.group(1))
                    z2 = int(match.group(2))
                    config["Basic Data"]["z1"] = str(z1)
                    config["Basic Data"]["z2"] = str(z2)
                    
        except Exception as e:
            print(f"기어비 정보 적용 오류: {e}")
    
    def apply_load_spectrum(self, config: Dict[str, Any], power_info: str, speed_info: str):
        """파워/속도 정보를 Load spectrum에 반영"""
        try:
            # 기존 Load spectrum 파싱
            load_spectrum_str = config["Rating"]["Load spectrum"]
            load_spectrum = json.loads(load_spectrum_str)
            
            if not load_spectrum:
                # 기본 Load spectrum 생성
                load_spectrum = [{
                    "Duration\\r[hr]": "20000.0",
                    "Temp.\\r[deg]": "80.0",
                    "\\rSpeed1\\r[rpm]": None,
                    "Gear 1\\rTorque1\\r[N.m]": None,
                    "\\rPower1\\r[kW]": None,
                    "\\rSpeed2\\r[rpm]": None,
                    "Gear 2\\rTorque2\\r[N.m]": None,
                    "\\rPower2\\r[kW]": None,
                    "\\rSpeed3\\r[rpm]": None,
                    "Gear 3\\rTorque3\\r[N.m]": None,
                    "\\rPower3\\r[kW]": None
                }]
            
            # 속도 정보 추출 및 적용
            if speed_info:
                speed_matches = re.findall(r'([0-9.]+)\\s*rpm', speed_info, re.IGNORECASE)
                if speed_matches:
                    load_spectrum[0]["\\rSpeed1\\r[rpm]"] = speed_matches[0]
            
            # 파워 정보 추출 및 적용
            if power_info:
                power_matches = re.findall(r'([0-9.]+)\\s*([kmKM]?[wW])', power_info)
                if power_matches:
                    power_value = float(power_matches[0][0])
                    unit = power_matches[0][1].lower()
                    if unit == 'kw':
                        power_value = power_value  # 이미 kW
                    elif unit == 'w':
                        power_value = power_value / 1000  # W를 kW로 변환
                    
                    load_spectrum[0]["\\rPower1\\r[kW]"] = str(power_value)
            
            # 토크 정보 추출 및 적용
            torque_matches = re.findall(r'([0-9.]+)\\s*([nN]\\s*[mM])', power_info)
            if torque_matches:
                torque_value = float(torque_matches[0][0])
                load_spectrum[0]["Gear 1\\rTorque1\\r[N.m]"] = str(torque_value)
            
            # 수정된 Load spectrum을 다시 JSON 문자열로 변환
            config["Rating"]["Load spectrum"] = json.dumps(load_spectrum, ensure_ascii=False)
            
        except Exception as e:
            print(f"Load spectrum 적용 오류: {e}")
    
    def apply_others_info(self, config: Dict[str, Any], others_info: str):
        """추가 정보 (모듈, 치폭 등)를 JSON에 반영"""
        try:
            # 모듈 정보 추출
            module_match = re.search(r'모듈\\s*([0-9.]+)', others_info)
            if module_match:
                module_value = module_match.group(1)
                config["Basic Data"]["Normal Module"] = module_value
            
            # 치폭 정보 추출
            face_width_match = re.search(r'치폭\\s*([0-9.]+)', others_info)
            if face_width_match:
                face_width_value = face_width_match.group(1)
                config["Basic Data"]["b1"] = face_width_value
                config["Basic Data"]["b2"] = face_width_value
            
            # 압력각 정보 추출
            pressure_angle_match = re.search(r'압력각\\s*([0-9.]+)', others_info)
            if pressure_angle_match:
                pressure_angle_value = pressure_angle_match.group(1)
                config["Basic Data"]["Pressure angle"] = pressure_angle_value
                
        except Exception as e:
            print(f"추가 정보 적용 오류: {e}")
    
    def perform_gear_design(self, modified_config: Dict[str, Any]) -> str:
        """기어 설계 계산 수행"""
        try:
            # 1. 설정 로드 및 검증
            if not self.manager.load_and_validate_config(modified_config):
                return "❌ 설정 로드 및 검증에 실패했습니다."
            
            # 2. 기하학적 계산
            geometry_result = self.manager.calculate_geometry()
            if not geometry_result:
                return "❌ 기하학적 계산에 실패했습니다."
            
            # 3. 하중 계산
            rating_result = self.manager.calculate_load_case(geometry_result)
            if not rating_result:
                return "❌ 하중 계산에 실패했습니다."
            
            # 4. 메시지 추출
            messages = self.manager.get_messages()
            
            # 5. 기어 이미지 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.output_dir / f"gear_image_{timestamp}.png"
            image_success = self.manager.get_gearimage(str(image_path))
            
            # 6. 결과 정리
            result_summary = self.format_design_results(
                geometry_result, rating_result, messages, 
                str(image_path) if image_success else None
            )
            
            return result_summary
            
        except Exception as e:
            return f"❌ 기어 설계 계산 중 오류 발생: {str(e)}"
    
    def format_design_results(self, geometry_result, rating_result, messages, image_path=None) -> str:
        """설계 결과를 포맷팅"""
        try:
            result_lines = [
                "✅ **기어 설계 완료!**\\n",
                "📊 **설계 결과 요약:**",
                ""
            ]
            
            # 메시지에서 주요 정보 추출
            if messages:
                result_lines.append("🔧 **계산 결과:**")
                # 메시지를 파싱해서 주요 정보만 추출
                key_info = self.extract_key_info_from_messages(messages)
                result_lines.extend(key_info)
                result_lines.append("")
            
            # 이미지 경로 추가
            if image_path and os.path.exists(image_path):
                result_lines.append(f"🖼️ **기어 이미지**: {image_path}")
                result_lines.append("")
            
            result_lines.extend([
                "✨ **설계가 성공적으로 완료되었습니다!**",
                "상세한 설계 데이터는 생성된 파일들을 확인해주세요."
            ])
            
            return "\\n".join(result_lines)
            
        except Exception as e:
            return f"결과 포맷팅 중 오류 발생: {str(e)}"
    
    def extract_key_info_from_messages(self, messages: str) -> List[str]:
        """메시지에서 핵심 정보 추출"""
        key_info = []
        try:
            # 메시지를 줄별로 분리
            lines = messages.split('\\n')
            
            for line in lines:
                # 중요한 정보가 포함된 라인 필터링
                if any(keyword in line for keyword in [
                    '중심거리', 'Center distance', 
                    '기어비', 'Gear ratio',
                    '안전계수', 'Safety factor',
                    '모듈', 'Module',
                    '잇수', 'Teeth'
                ]):
                    key_info.append(f"  • {line.strip()}")
                    
            if not key_info:
                key_info.append("  • 계산이 성공적으로 완료되었습니다.")
                
        except Exception as e:
            key_info = [f"  • 메시지 파싱 오류: {str(e)}"]
            
        return key_info
    
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