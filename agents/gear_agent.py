"""
Gear Agent: gear_classifier와 gear_design_agent를 MCP로 통합 관리하는 상위 에이전트
사용자 요청에 따라 기어 분류 → 기어 설계 → 사용자 승인 → 계산 수행 워크플로우를 관리
"""
from typing import Dict, Any, Optional, AsyncGenerator, Callable, TypedDict, List
from langgraph.graph import StateGraph, END
import asyncio
import json
import re
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.gear_classifier_agent import GearClassifierAgent
from agents.gear_design_agent import GearDesignAgent


class GearAgentState(TypedDict):
    """Gear Agent 상태 관리"""
    # 입력 및 기본 정보
    input_text: str
    current_step: str
    
    # Classifier 관련 상태
    classifier_completed: bool
    classification_result: Dict[str, Any]
    
    # Design 관련 상태  
    design_available: bool
    design_completed: bool
    design_result: Dict[str, Any]
    
    # 사용자 상호작용
    awaiting_user_approval: bool
    user_approved: bool
    specs_summary: str
    user_feedback: str
    
    # 결과 및 메시지
    final_result: str
    messages: List[str]
    error_message: str


class GearAgent(BaseAgent):
    """MCP 기반 통합 Gear Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agent_name = "Gear Agent"
        
        # 하위 에이전트 초기화
        classifier_config = {
            "model": config.get("model", "gpt-5-mini"),
            "temperature": config.get("temperature", 0.0)
        }
        self.gear_classifier = GearClassifierAgent(classifier_config)
        
        design_config = {
            "model": config.get("model", "gpt-5-mini"),
            "temperature": config.get("temperature", 0.0),
            "gear_design_path": config.get("gear_design_path", r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"),
            "template_json_path": config.get("template_json_path", "TestGD.GD1")
        }
        self.gear_design = GearDesignAgent(design_config)
        
        # LangGraph 워크플로우 구성
        self.workflow = self._create_workflow()
        
    def _create_workflow(self) -> StateGraph:
        """MCP 기반 워크플로우 구성"""
        workflow = StateGraph(GearAgentState)
        
        # 노드 추가
        workflow.add_node("analyze_request", self._analyze_request_node)
        workflow.add_node("run_classifier", self._run_classifier_node)
        workflow.add_node("prepare_design", self._prepare_design_node)  
        workflow.add_node("await_approval", self._await_approval_node)
        workflow.add_node("process_approval", self._process_approval_node)
        workflow.add_node("run_calculation", self._run_calculation_node)
        workflow.add_node("generate_final_result", self._generate_final_result_node)
        
        # 시작점 설정
        workflow.set_entry_point("analyze_request")
        
        # 엣지 및 조건부 라우팅 설정
        workflow.add_conditional_edges(
            "analyze_request",
            self._route_after_analysis,
            {
                "run_classifier": "run_classifier",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "run_classifier", 
            self._route_after_classifier,
            {
                "prepare_design": "prepare_design",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "prepare_design",
            self._route_after_design_prep,
            {
                "await_approval": "await_approval",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "await_approval",
            self._route_after_await,
            {
                "process_approval": "process_approval",
                "continue_waiting": "await_approval"
            }
        )
        
        workflow.add_conditional_edges(
            "process_approval",
            self._route_after_approval,
            {
                "run_calculation": "run_calculation",
                "await_approval": "await_approval",
                "error": END
            }
        )
        
        workflow.add_edge("run_calculation", "generate_final_result")
        workflow.add_edge("generate_final_result", END)
        
        return workflow.compile()
        
    async def _analyze_request_node(self, state: GearAgentState) -> GearAgentState:
        """사용자 요청 분석"""
        try:
            input_text = state["input_text"]
            
            # 기어 관련 키워드 분석
            gear_keywords = [
                "기어", "gear", "치차", "톱니바퀴", "모듈", "잇수", "피치", 
                "압력각", "치형", "강도", "설계", "계산", "분석"
            ]
            
            is_gear_request = any(keyword in input_text.lower() for keyword in gear_keywords)
            
            if not is_gear_request:
                state["error_message"] = "기어 관련 요청이 아닙니다. 기어 설계나 분석 관련 내용을 입력해주세요."
                return state
                
            state["current_step"] = "분석 완료"
            state["messages"] = [f"🔍 사용자 요청을 분석했습니다: {input_text[:100]}..."]
            
            return state
            
        except Exception as e:
            state["error_message"] = f"요청 분석 중 오류 발생: {str(e)}"
            return state
            
    async def _run_classifier_node(self, state: GearAgentState) -> GearAgentState:
        """기어 분류기 실행"""
        try:
            input_text = state["input_text"]
            
            # MCP를 통한 classifier 호출
            classification_result = await self._call_classifier_mcp(input_text)
            
            if classification_result:
                state["classifier_completed"] = True
                state["classification_result"] = classification_result
                state["current_step"] = "기어 분류 완료"
                state["messages"].append("✅ 기어 분류가 완료되었습니다.")
            else:
                state["error_message"] = "기어 분류에 실패했습니다."
                
            return state
            
        except Exception as e:
            state["error_message"] = f"기어 분류 중 오류 발생: {str(e)}"
            return state
            
    async def _prepare_design_node(self, state: GearAgentState) -> GearAgentState:
        """기어 설계 준비 및 제원 표시"""
        try:
            classification_result = state["classification_result"]
            
            # MCP를 통한 design agent 호출 (제원 표시까지만)
            design_prep_result = await self._call_design_prep_mcp(classification_result)
            
            if design_prep_result:
                state["design_available"] = True
                state["specs_summary"] = design_prep_result.get("specs_summary", "")
                state["current_step"] = "기어 제원 준비 완료"
                state["messages"].append("📋 기어 제원이 준비되었습니다. 사용자 승인을 기다립니다.")
            else:
                state["error_message"] = "기어 설계 준비에 실패했습니다."
                
            return state
            
        except Exception as e:
            state["error_message"] = f"기어 설계 준비 중 오류 발생: {str(e)}"
            return state
            
    async def _await_approval_node(self, state: GearAgentState) -> GearAgentState:
        """사용자 승인 대기"""
        try:
            if not state.get("awaiting_user_approval", False):
                # 첫 승인 요청
                state["awaiting_user_approval"] = True
                approval_message = f"""
🔧 **기어 설계 제원 확인**

{state.get('specs_summary', '기어 제원을 준비 중입니다...')}

**다음 중 선택해주세요:**
1. **승인** - 위 제원으로 계산을 진행합니다
2. **수정 요청** - 특정 값들을 수정하고 싶습니다

승인하시려면 "승인" 또는 "계산 진행"이라고 입력해주세요.
수정하시려면 "수정: [구체적인 수정 내용]"이라고 입력해주세요.
"""
                state["messages"].append(approval_message)
                state["current_step"] = "사용자 승인 대기 중"
                
            return state
            
        except Exception as e:
            state["error_message"] = f"승인 대기 중 오류 발생: {str(e)}"
            return state
            
    async def _process_approval_node(self, state: GearAgentState) -> GearAgentState:
        """사용자 승인/수정 처리"""
        try:
            user_feedback = state.get("user_feedback", "").strip().lower()
            
            # 승인 패턴 검사
            approval_patterns = [r"승인", r"계산.*진행", r"ok", r"확인", r"진행"]
            is_approved = any(re.search(pattern, user_feedback) for pattern in approval_patterns)
            
            # 수정 요청 패턴 검사
            modification_patterns = [r"수정", r"변경", r"바꾸", r"조정"]
            is_modification = any(re.search(pattern, user_feedback) for pattern in modification_patterns)
            
            if is_approved:
                state["user_approved"] = True
                state["awaiting_user_approval"] = False
                state["current_step"] = "사용자 승인 완료"
                state["messages"].append("✅ 사용자가 제원을 승인했습니다. 계산을 시작합니다.")
                
            elif is_modification:
                # 수정 요청 처리
                modification_result = await self._handle_modification_mcp(user_feedback, state)
                if modification_result:
                    state["specs_summary"] = modification_result.get("updated_specs", state["specs_summary"])
                    state["messages"].append("🔄 제원이 수정되었습니다. 다시 확인해주세요.")
                    # 다시 승인 대기 상태로
                    state["awaiting_user_approval"] = True
                else:
                    state["error_message"] = "수정 처리에 실패했습니다."
                    
            else:
                # 명확하지 않은 응답
                state["messages"].append("❓ 승인 또는 수정 요청을 명확히 해주세요. ('승인' 또는 '수정: [내용]')")
                state["awaiting_user_approval"] = True
                
            return state
            
        except Exception as e:
            state["error_message"] = f"승인 처리 중 오류 발생: {str(e)}"
            return state
            
    async def _run_calculation_node(self, state: GearAgentState) -> GearAgentState:
        """최종 기어 계산 실행"""
        try:
            # MCP를 통한 설계 계산 실행
            calculation_result = await self._call_design_calculation_mcp(state)
            
            if calculation_result:
                state["design_completed"] = True
                state["design_result"] = calculation_result
                state["current_step"] = "기어 계산 완료"
                state["messages"].append("⚙️ 기어 설계 계산이 완료되었습니다.")
            else:
                state["error_message"] = "기어 계산에 실패했습니다."
                
            return state
            
        except Exception as e:
            state["error_message"] = f"기어 계산 중 오류 발생: {str(e)}"
            return state
            
    async def _generate_final_result_node(self, state: GearAgentState) -> GearAgentState:
        """최종 결과 생성"""
        try:
            classification_result = state.get("classification_result", {})
            design_result = state.get("design_result", {})
            
            # 최종 결과 포맷팅
            final_result = f"""
🔧 **기어 설계 완료 보고서**

## 📊 분류 결과
{json.dumps(classification_result, ensure_ascii=False, indent=2)}

## ⚙️ 설계 결과  
{json.dumps(design_result, ensure_ascii=False, indent=2)}

## 📝 처리 단계
{chr(10).join(f"- {msg}" for msg in state.get('messages', []))}

**완료 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            state["final_result"] = final_result
            state["current_step"] = "전체 작업 완료"
            
            return state
            
        except Exception as e:
            state["error_message"] = f"결과 생성 중 오류 발생: {str(e)}"
            return state
    
    # 라우팅 함수들
    def _route_after_analysis(self, state: GearAgentState) -> str:
        return "error" if state.get("error_message") else "run_classifier"
        
    def _route_after_classifier(self, state: GearAgentState) -> str:
        return "error" if state.get("error_message") else "prepare_design"
        
    def _route_after_design_prep(self, state: GearAgentState) -> str:
        return "error" if state.get("error_message") else "await_approval"
        
    def _route_after_await(self, state: GearAgentState) -> str:
        return "process_approval" if state.get("user_feedback") else "continue_waiting"
        
    def _route_after_approval(self, state: GearAgentState) -> str:
        if state.get("error_message"):
            return "error"
        elif state.get("user_approved"):
            return "run_calculation"
        else:
            return "await_approval"
    
    # MCP 호출 메서드들
    async def _call_classifier_mcp(self, input_text: str) -> Optional[Dict[str, Any]]:
        """MCP를 통한 분류기 호출"""
        try:
            result = await self.gear_classifier.process_with_callback(
                input_text, 
                lambda x: None  # 임시 콜백
            )
            
            # 결과에서 상태 정보 추출
            if hasattr(self.gear_classifier, 'state') and self.gear_classifier.state:
                return self.gear_classifier.state
            return {"result": result}
            
        except Exception as e:
            print(f"Classifier MCP 호출 오류: {e}")
            return None
            
    async def _call_design_prep_mcp(self, classification_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """MCP를 통한 설계 준비 호출"""
        try:
            # gear_classifier_agent의 state를 JSON으로 변환하여 전달
            # gear_design_agent에서 파싱할 수 있도록 state 구조 그대로 전달
            prep_input = json.dumps(classification_result, ensure_ascii=False)
            
            # 제원 표시 단계까지만 실행하도록 설정
            result = await self.gear_design.process_with_callback(
                prep_input,
                lambda x: None  # 임시 콜백
            )
            
            # design agent의 상태에서 specs 정보 추출
            if hasattr(self.gear_design, 'state') and self.gear_design.state:
                return {
                    "specs_summary": self.gear_design.state.get("gear_specs_summary", ""),
                    "result": result
                }
            return {"specs_summary": str(result)}
            
        except Exception as e:
            print(f"Design prep MCP 호출 오류: {e}")
            return None
            
    async def _handle_modification_mcp(self, user_feedback: str, state: GearAgentState) -> Optional[Dict[str, Any]]:
        """MCP를 통한 수정 처리 호출"""
        try:
            # 수정 요청을 design agent에 전달
            modification_input = {
                "type": "modification",
                "feedback": user_feedback,
                "current_specs": state.get("specs_summary", "")
            }
            
            result = await self.gear_design.process_with_callback(
                json.dumps(modification_input, ensure_ascii=False),
                lambda x: None  # 임시 콜백
            )
            
            return {"updated_specs": str(result)}
            
        except Exception as e:
            print(f"Modification MCP 호출 오류: {e}")
            return None
            
    async def _call_design_calculation_mcp(self, state: GearAgentState) -> Optional[Dict[str, Any]]:
        """MCP를 통한 최종 계산 호출"""
        try:
            # 승인된 제원으로 최종 계산 실행
            calc_input = {
                "type": "final_calculation",
                "approved_specs": state.get("specs_summary", ""),
                "classification_result": state.get("classification_result", {})
            }
            
            result = await self.gear_design.process_with_callback(
                json.dumps(calc_input, ensure_ascii=False),
                lambda x: None  # 임시 콜백
            )
            
            if hasattr(self.gear_design, 'state') and self.gear_design.state:
                return self.gear_design.state
            return {"calculation_result": result}
            
        except Exception as e:
            print(f"Calculation MCP 호출 오류: {e}")
            return None
    
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """메인 처리 메서드 - 사용자 상호작용 포함"""
        try:
            # 사용자 응답 처리 (기존 워크플로우 재개)
            if hasattr(self, '_current_state') and self._current_state.get("awaiting_user_approval"):
                self._current_state["user_feedback"] = input_text
                return await self._continue_workflow(callback)
            
            # 초기 상태 설정
            initial_state: GearAgentState = {
                "input_text": input_text,
                "current_step": "시작",
                "classifier_completed": False,
                "classification_result": {},
                "design_available": False,
                "design_completed": False,
                "design_result": {},
                "awaiting_user_approval": False,
                "user_approved": False,
                "specs_summary": "",
                "user_feedback": "",
                "final_result": "",
                "messages": [],
                "error_message": ""
            }
            
            # 현재 상태 저장 (사용자 응답 처리용)
            self._current_state = initial_state
            
            # 워크플로우 실행 - 승인 대기까지
            async for state_update in self.workflow.astream(initial_state):
                for key, value in state_update.items():
                    if key in self._current_state:
                        self._current_state[key] = value
                
                # 현재 상태 콜백으로 전달
                if self._current_state.get("messages"):
                    latest_messages = self._current_state["messages"]
                    # 새 메시지만 전송 (중복 방지)
                    if not hasattr(self, '_last_message_count'):
                        self._last_message_count = 0
                    
                    for i in range(self._last_message_count, len(latest_messages)):
                        callback(latest_messages[i])
                    self._last_message_count = len(latest_messages)
                        
                # 오류 발생시 중단
                if self._current_state.get("error_message"):
                    error_msg = f"❌ 오류: {self._current_state['error_message']}"
                    callback(error_msg)
                    return error_msg
                    
                # 사용자 승인 대기 상태면 일시 중단
                if self._current_state.get("awaiting_user_approval") and not self._current_state.get("user_feedback"):
                    break
                    
            # 사용자 승인 대기 상태라면 대기 메시지 반환
            if self._current_state.get("awaiting_user_approval"):
                return "사용자 승인을 기다리는 중입니다. 위 제원을 확인하고 '승인' 또는 '수정: [내용]'을 입력해주세요."
                
            # 완료된 경우 최종 결과 반환
            return self._current_state.get("final_result", "처리 완료")
            
        except Exception as e:
            error_msg = f"Gear Agent 처리 중 오류 발생: {str(e)}"
            callback(error_msg)
            return error_msg
            
    def handle_user_response(self, user_input: str, callback: Callable[[str], None]) -> str:
        """사용자 응답 처리를 위한 별도 메서드"""
        try:
            # 현재 상태에 사용자 피드백 추가
            if hasattr(self, '_current_state'):
                self._current_state["user_feedback"] = user_input
                
                # 워크플로우 재개
                return asyncio.run(self._continue_workflow(callback))
            else:
                return "현재 진행 중인 작업이 없습니다."
                
        except Exception as e:
            error_msg = f"사용자 응답 처리 중 오류: {str(e)}"
            callback(error_msg)
            return error_msg
            
    async def _continue_workflow(self, callback: Callable[[str], None]) -> str:
        """워크플로우 재개"""
        try:
            async for state_update in self.workflow.astream(self._current_state):
                for key, value in state_update.items():
                    if key in self._current_state:
                        self._current_state[key] = value
                
                # 새 메시지만 콜백으로 전달
                if self._current_state.get("messages"):
                    latest_messages = self._current_state["messages"]
                    for i in range(self._last_message_count, len(latest_messages)):
                        callback(latest_messages[i])
                    self._last_message_count = len(latest_messages)
                        
                if self._current_state.get("error_message"):
                    callback(f"❌ 오류: {self._current_state['error_message']}")
                    return self._current_state["error_message"]
                    
                # 다시 승인 대기가 되면 중단
                if self._current_state.get("awaiting_user_approval") and not self._current_state.get("user_approved"):
                    break
                    
            # 최종 완료 확인
            if self._current_state.get("design_completed"):
                return self._current_state.get("final_result", "기어 설계가 완료되었습니다.")
            elif self._current_state.get("awaiting_user_approval"):
                return "다시 승인을 기다리는 중입니다. 제원을 확인하고 '승인' 또는 '수정: [내용]'을 입력해주세요."
            else:
                return self._current_state.get("final_result", "처리 완료")
            
        except Exception as e:
            return f"워크플로우 재개 중 오류: {str(e)}"