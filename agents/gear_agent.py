"""Gear Agent: langgraph + MCP tool 기반 통합 기어 에이전트
MCP tool을 통해 gear_classifier와 gear_design_agent를 호출하여 응답하거나, 단순 질문은 직접 답변
"""
from typing import Dict, Any, Optional, Callable, TypedDict, List
from langgraph.graph import StateGraph, END
import json
from io import BytesIO
from PIL import Image

from agents.base_agent import BaseAgent


class GearAgentState(TypedDict):
    """Gear Agent 상태 관리"""
    # 입력 및 메시지
    messages: List[Dict[str, str]]
    input_text: str
    
    # Tool 호출 관련
    tool_results: List[Dict[str, Any]]
    
    # 분석 결과
    is_gear_related: bool
    needs_tools: bool
    analysis_result: str
    
    # 최종 결과
    final_response: str
    error_message: str


class GearAgent(BaseAgent):
    """Langgraph + MCP Tool 기반 통합 Gear Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agent_name = "Gear Agent"
        
        
        # LangGraph 워크플로우 구성
        self.workflow = self._create_workflow()
        
    def _create_workflow(self) -> StateGraph:
        """Langgraph + MCP Tool 워크플로우 구성"""
        workflow = StateGraph(GearAgentState)
        
        # 노드 추가
        workflow.add_node("analyze_input", self._analyze_input_node)
        workflow.add_node("call_tools", self._call_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)
        
        # 시작점 설정
        workflow.set_entry_point("analyze_input")
        
        # 조건부 라우팅
        workflow.add_conditional_edges(
            "analyze_input",
            self._should_use_tools,
            {
                "tools": "call_tools",
                "direct_response": "generate_response"
            }
        )
        
        workflow.add_edge("call_tools", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
        
    async def _analyze_input_node(self, state: GearAgentState) -> GearAgentState:
        """입력 분석 및 도구 사용 여부 결정"""
        try:
            input_text = state["input_text"]
            
            # 기어 관련 키워드 분석
            gear_keywords = [
                "기어", "gear", "치차", "톱니바퀴", "모듈", "잇수", "피치", 
                "압력각", "치형", "강도", "설계", "계산", "분석", "스퍼기어", "헬리컬"
            ]
            
            is_gear_related = any(keyword in input_text.lower() for keyword in gear_keywords)
            state["is_gear_related"] = is_gear_related
            
            # 도구가 필요한 작업인지 판단
            tool_required_keywords = [
                "설계", "계산", "분석", "강도", "검증", "최적화", 
                "design", "calculate", "analyze", "strength", "optimize"
            ]
            
            needs_tools = any(keyword in input_text.lower() for keyword in tool_required_keywords)
            state["needs_tools"] = needs_tools and is_gear_related
            
            # 분석 결과 저장
            if is_gear_related and needs_tools:
                state["analysis_result"] = "기어 관련 계산/분석 작업 - MCP 도구 사용 필요"
            elif is_gear_related:
                state["analysis_result"] = "기어 관련 일반 질문 - 직접 답변 가능"
            else:
                state["analysis_result"] = "기어와 관련 없는 질문 - 기어 전문 에이전트 범위 외"
            
            return state
            
        except Exception as e:
            state["error_message"] = f"입력 분석 중 오류 발생: {str(e)}"
            return state
    
    async def _call_tools_node(self, state: GearAgentState) -> GearAgentState:
        """MCP Tools 호출 노드"""
        try:
            # MCP client 초기화 확인
            if not hasattr(self, '_mcp_client'):
                await self._initialize_mcp_client()
            
            tool_results = []
            input_text = state["input_text"]
            
            # 순차적으로 필요한 도구들 호출
            if state.get("needs_tools", False):
                # 1. 먼저 classifier 호출
                classifier_result = await self._call_mcp_tool("gear_classifier", {
                    "query": input_text,
                    "analysis_depth": "detailed"
                })
                
                if classifier_result and classifier_result.get("success"):
                    tool_results.append({
                        "tool_name": "gear_classifier",
                        "status": "success",
                        "classification": classifier_result.get("data", {}),
                        "message": "기어 분류 완료"
                    })
                    
                    # 2. classifier 결과를 바탕으로 design agent 호출
                    design_params = {
                        "raw_input": input_text,
                        "classification_result": classifier_result.get("data", {})
                    }
                    
                    design_result = await self._call_mcp_tool("gear_design", design_params)
                    
                    if design_result and design_result.get("success"):
                        tool_results.append({
                            "tool_name": "gear_design", 
                            "status": "success",
                            "design_results": design_result.get("data", {}),
                            "message": "기어 설계 계산 완료"
                        })
                    else:
                        tool_results.append({
                            "tool_name": "gear_design",
                            "status": "error", 
                            "error": design_result.get("error", "설계 계산 실패")
                        })
                        
                else:
                    tool_results.append({
                        "tool_name": "gear_classifier",
                        "status": "error",
                        "error": classifier_result.get("error", "분류 실패")
                    })
            
            state["tool_results"] = tool_results
            return state
            
        except Exception as e:
            state["error_message"] = f"Tool 호출 중 오류 발생: {str(e)}"
            return state
            
    async def _generate_response_node(self, state: GearAgentState) -> GearAgentState:
        """최종 응답 생성"""
        try:
            # Tool 결과가 있는 경우 처리
            if state.get("tool_results"):
                # Tool 결과를 종합하여 응답 생성
                response = self._process_tool_results(state["tool_results"])
            else:
                # 직접 응답 생성
                response = await self._generate_direct_response(state["input_text"], state.get("is_gear_related", False))
            
            state["final_response"] = response
            return state
            
        except Exception as e:
            state["error_message"] = f"응답 생성 중 오류 발생: {str(e)}"
            return state
            
        
    def _should_use_tools(self, state: GearAgentState) -> str:
        """Tool 사용 여부 결정"""
        if state.get("needs_tools", False):
            return "tools"
        else:
            return "direct_response"
            
    def _process_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Tool 실행 결과를 처리하여 응답 생성"""
        try:
            responses = []
            
            for result in tool_results:
                if result.get("status") == "success":
                    tool_name = result.get("tool_name", "unknown")
                    
                    if tool_name == "gear_classifier":
                        classification = result.get("classification", {})
                        responses.append(f"🔍 **기어 분류 결과:**\n- 기어 타입: {classification.get('gear_type', 'N/A')}\n- 분석 유형: {classification.get('analysis_type', 'N/A')}")
                    
                    elif tool_name == "gear_design":
                        design_results = result.get("design_results", {})
                        responses.append(f"⚙️ **기어 설계 결과:**\n- 모듈: {design_results.get('module', 'N/A')}\n- 잇수: {design_results.get('teeth_count', 'N/A')}\n- 압력각: {design_results.get('pressure_angle', 'N/A')}°\n- 안전계수: {design_results.get('safety_factor', 'N/A')}")
                
                else:
                    responses.append(f"❌ {result.get('tool_name', 'Tool')} 실행 중 오류: {result.get('error', 'Unknown error')}")
            
            return "\n\n".join(responses) if responses else "도구 실행 결과를 처리할 수 없습니다."
            
        except Exception as e:
            return f"결과 처리 중 오류 발생: {str(e)}"
            
    async def _generate_direct_response(self, input_text: str, is_gear_related: bool) -> str:
        """직접 응답 생성 (도구 없이)"""
        try:
            if not is_gear_related:
                return "죄송합니다. 저는 기어 설계 및 분석 전문 에이전트입니다. 기어와 관련된 질문을 해주세요."
            
            # 기어 관련 일반 질문에 대한 직접 응답
            if any(keyword in input_text.lower() for keyword in ["what", "뭐", "무엇", "설명"]):
                return """
🔧 **기어(Gear) 기본 정보**

기어는 회전 운동을 전달하거나 속도/토크를 변환하는 기계 요소입니다.

**주요 기어 종류:**
- 스퍼 기어(Spur Gear): 직선 치형
- 헬리컬 기어(Helical Gear): 나선 치형  
- 베벨 기어(Bevel Gear): 원추형
- 웜 기어(Worm Gear): 나사형

**기본 설계 변수:**
- 모듈(Module): 기어 크기의 기준
- 잇수(Teeth Count): 기어 이의 개수
- 압력각(Pressure Angle): 치형 각도
- 페이스폭(Face Width): 기어 폭

구체적인 설계나 계산이 필요하시면 상세한 요구사항을 알려주세요.
"""
            
            return "기어 관련 질문을 해주셨네요. 더 구체적인 설계나 계산이 필요하시면 자세한 요구사항을 알려주세요."
            
        except Exception as e:
            return f"응답 생성 중 오류 발생: {str(e)}"
    
    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """MCP client를 통해 실제 tool을 호출하는 메서드"""
        try:
            # MCP client 설정 확인
            if not hasattr(self, '_mcp_client'):
                await self._initialize_mcp_client()
            
            # Tool별 MCP 호출
            if tool_name == "gear_classifier":
                # gear_classifier_agent의 MCP 서버 호출
                return await self._call_gear_classifier_mcp(parameters)
            
            elif tool_name == "gear_design":
                # gear_design_agent의 MCP 서버 호출  
                return await self._call_gear_design_mcp(parameters)
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"MCP tool call failed: {str(e)}"
            }
    
    async def _initialize_mcp_client(self):
        """MCP client 초기화"""
        try:
            # 임시로 기존 agent들을 직접 호출하는 방식으로 구현
            # 실제 MCP 서버가 구축되면 이 부분을 교체
            from agents.gear_classifier_agent import GearClassifierAgent
            from agents.gear_design_agent import GearDesignAgent
            
            classifier_config = {
                "model": self.config.get("model", "gpt-4o-mini"),
                "temperature": self.config.get("temperature", 0.0)
            }
            self._classifier_agent = GearClassifierAgent(classifier_config)
            
            design_config = {
                "model": self.config.get("model", "gpt-4o-mini"), 
                "temperature": self.config.get("temperature", 0.0),
                "gear_design_path": self.config.get("gear_design_path", r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"),
                "template_json_path": self.config.get("template_json_path", "TestGD.GD1")
            }
            self._design_agent = GearDesignAgent(design_config)
            
            # shared_data 공유 설정
            self._design_agent.shared_data = self._classifier_agent.shared_data
            
            self._mcp_client = True  # 초기화 완료 표시
            
        except Exception as e:
            print(f"MCP client 초기화 실패: {e}")
            self._mcp_client = None
    
    async def _call_gear_classifier_mcp(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """gear_classifier_agent MCP 호출"""
        try:
            query = parameters.get("query", "")
            
            # classifier agent 호출
            result = await self._classifier_agent.process_with_callback(
                query,
                lambda x: None  # 임시 콜백
            )
            
            # 결과에서 상태 정보 추출
            classification_data = {}
            if hasattr(self._classifier_agent, 'state') and self._classifier_agent.state:
                classification_data = self._classifier_agent.state
            
            return {
                "success": True,
                "data": {
                    "result": result,
                    "classification": classification_data,
                    "processed_query": query
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gear classifier MCP call failed: {str(e)}"
            }
    
    async def _call_gear_design_mcp(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """gear_design_agent MCP 호출"""
        try:
            # parameters에서 입력 데이터 추출
            raw_input = parameters.get("raw_input", "")
            params_dict = parameters.get("parameters", {})
            
            input_text = raw_input if raw_input else json.dumps(params_dict, ensure_ascii=False)
            
            # design agent 호출
            result = await self._design_agent.process_with_callback(
                input_text,
                lambda x: None  # 임시 콜백
            )
            
            # 결과에서 상태 정보 추출
            design_data = {}
            if hasattr(self._design_agent, 'state') and self._design_agent.state:
                design_data = self._design_agent.state
            
            return {
                "success": True,
                "data": {
                    "result": result,
                    "design_details": design_data,
                    "processed_input": input_text
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Gear design MCP call failed: {str(e)}"
            }
    
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """메인 처리 메서드"""
        try:
            # 초기 상태 설정
            initial_state: GearAgentState = {
                "messages": [{"role": "user", "content": input_text}],
                "input_text": input_text,
                "tool_results": [],
                "is_gear_related": False,
                "needs_tools": False,
                "analysis_result": "",
                "final_response": "",
                "error_message": ""
            }
            
            # 워크플로우 실행
            final_state = initial_state
            async for state_update in self.workflow.astream(initial_state):
                # state_update가 단일 노드 결과인 경우 처리
                for node_name, node_result in state_update.items():
                    if isinstance(node_result, dict):
                        # 노드 결과로 상태 업데이트
                        for key, value in node_result.items():
                            if key in final_state:
                                final_state[key] = value
                
                # 중간 진행사항 콜백
                if final_state.get("analysis_result") and not hasattr(self, '_analysis_sent'):
                    callback(f"🔍 {final_state['analysis_result']}")
                    self._analysis_sent = True
            
            # 오류 처리
            if final_state and final_state.get("error_message"):
                error_msg = f"❌ {final_state['error_message']}"
                callback(error_msg)
                return error_msg
            
            # 최종 결과 반환
            final_response = final_state.get("final_response", "처리 완료") if final_state else "처리 실패"
            return final_response
            
        except Exception as e:
            error_msg = f"Gear Agent 처리 중 오류 발생: {str(e)}"
            callback(error_msg)
            return error_msg
        finally:
            # 분석 플래그 리셋
            if hasattr(self, '_analysis_sent'):
                delattr(self, '_analysis_sent')
    
    def get_graph_image(self):
        """LangGraph에서 그래프 이미지를 생성하여 반환"""
        try:
            # LangGraph의 get_graph(xray=True).draw_mermaid_png() 사용
            png_data = self.workflow.get_graph(xray=True).draw_mermaid_png()
            
            # PNG 데이터를 PIL Image로 변환
            image = Image.open(BytesIO(png_data))
            return image
        except Exception as e:
            print(f"그래프 이미지 생성 오류: {e}")
            return None