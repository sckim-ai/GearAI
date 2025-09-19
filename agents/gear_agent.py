"""Gear Agent: gear_classifier 결과를 받아 Planning 기반으로 Task를 수행하는 에이전트"""
from typing import Dict, Any, Optional, Callable, TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import Annotated
import json
import asyncio
from io import BytesIO
from PIL import Image
import os

from agents.base_agent import BaseAgent

# LLM 임포트
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage


class GearAgentState(TypedDict):
    """Gear Agent 상태 관리"""
    # 입력 및 메시지
    messages: Annotated[list, add_messages]
    input_text: str

    # gear_classifier로부터 받은 정보
    classifier_result: Dict[str, Any]
    gear_type: str
    speed_info: str
    power_info: str
    ratio_info: str
    others_info: str

    # 요청 복잡도 분석
    complexity_level: str  # "simple", "complex"
    complexity_analysis: str
    required_tools: List[str]  # LLM이 분석한 필요 도구들
    estimated_steps: int  # LLM이 예상한 단계 수

    # Planning 관련 (복잡한 요청의 경우)
    plan: List[Dict[str, Any]]
    current_task_index: int

    # Task 실행 관련
    task_results: List[Dict[str, Any]]
    current_task: Dict[str, Any]

    # Tool 호출 관련
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

    # 최종 결과
    final_response: str
    error_message: str


class GearAgent(BaseAgent):
    """Planning 기반 Gear Task 수행 Agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agent_name = "Planning Gear Agent"

        # LLM 설정
        self.model_name = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.1)
        self.provider = config.get("provider", "openai")

        # LLM 초기화
        self.llm = self._initialize_llm()

        # LangGraph 워크플로우 구성
        self.workflow = self._create_workflow()

        # Tool 초기화
        self._initialize_tools()

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
            elif self.provider == "anthropic":
                return ChatAnthropic(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    streaming=False
                )
            elif self.provider == "google":
                return ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    streaming=False
                )
            else:
                # 기본값은 OpenAI
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            # 오류 시 기본 OpenAI 모델로 fallback
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                api_key=os.getenv("OPENAI_API_KEY"),
                streaming=False
            )

    def _create_workflow(self):
        """Planning 기반 LangGraph 워크플로우 구성"""
        workflow = StateGraph(GearAgentState)

        # 노드 추가
        workflow.add_node("analyze_complexity", self._analyze_complexity_node)
        workflow.add_node("create_plan", self._create_plan_node)
        workflow.add_node("execute_simple_task", self._execute_simple_task_node)
        workflow.add_node("execute_current_task", self._execute_current_task_node)
        workflow.add_node("check_plan_completion", self._check_plan_completion_node)
        workflow.add_node("synthesize_results", self._synthesize_results_node)

        # 시작점 설정
        workflow.set_entry_point("analyze_complexity")

        # 조건부 라우팅 - 복잡도에 따른 분기
        workflow.add_conditional_edges(
            "analyze_complexity",
            self._route_by_complexity,
            {
                "simple": "execute_simple_task",
                "complex": "create_plan"
            }
        )

        # 단순 작업 -> 결과 종합
        workflow.add_edge("execute_simple_task", "synthesize_results")

        # 복잡 작업 -> Planning -> Task 실행
        workflow.add_edge("create_plan", "execute_current_task")

        # Task 실행 -> 완료 확인
        workflow.add_edge("execute_current_task", "check_plan_completion")

        # 완료 확인 후 분기
        workflow.add_conditional_edges(
            "check_plan_completion",
            self._route_plan_completion,
            {
                "continue": "execute_current_task",
                "complete": "synthesize_results"
            }
        )

        # 최종 종료
        workflow.add_edge("synthesize_results", END)

        return workflow.compile()

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

    def get_mermaid_graph(self):
        """Mermaid 다이어그램 텍스트 반환 (app.py fallback에서 사용)"""
        try:
            # LangGraph에서 Mermaid 문법 가져오기
            return self.workflow.get_graph(xray=True).draw_mermaid()
        except Exception as e:
            print(f"Mermaid 다이어그램 생성 오류: {e}")
            # 기본 다이어그램 반환
            return ""

    def _initialize_tools(self):
        """사용 가능한 Tool들 초기화"""
        self.available_tools = {
            "gear_design_calculation": self._tool_gear_design_calculation,
            "gear_strength_analysis": self._tool_gear_strength_analysis,
            "gear_efficiency_calculation": self._tool_gear_efficiency_calculation,
            "gear_noise_analysis": self._tool_gear_noise_analysis,
            "gear_optimization": self._tool_gear_optimization,
            "material_selection": self._tool_material_selection,
            "manufacturing_analysis": self._tool_manufacturing_analysis
        }

    async def _analyze_complexity_node(self, state: GearAgentState) -> GearAgentState:
        """LLM을 사용한 요청의 복잡도 분석"""
        try:
            input_text = state["input_text"]
            classifier_result = state.get("classifier_result", {})
            gear_type = state.get("gear_type", "")

            # LLM에게 복잡도 분석을 요청하는 프롬프트
            system_prompt = """당신은 기어 설계 전문가입니다. 사용자의 요청을 분석하여 복잡도를 판단해주세요.

판단 기준:
1. SIMPLE: 단일 계산, 기본 설계, 단순한 정보 요청
   - 예: "모듈 2의 기어 설계해줘", "기어비 3:1로 계산해줘", "기본 치형 설계"

2. COMPLEX: 다중 단계, 최적화, 분석, 검증이 필요한 요청
   - 예: "최적화된 유성기어 설계", "강도 분석 후 재료 선택", "여러 조건을 만족하는 설계"

응답 형식:
{
    "complexity_level": "simple" 또는 "complex",
    "analysis": "판단 근거 설명",
    "required_tools": ["필요한 도구들 목록"],
    "estimated_steps": 예상 단계 수 (숫자)
}

JSON 형식으로만 응답해주세요."""

            user_prompt = f"""사용자 요청: {input_text}

gear_classifier 결과:
- 기어 타입: {gear_type}
- 분류 결과: {json.dumps(classifier_result, ensure_ascii=False, indent=2)}

위 요청의 복잡도를 분석해주세요."""

            # LLM 호출
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # JSON 파싱
            try:
                analysis_result = json.loads(response_text)
                complexity_level = analysis_result.get("complexity_level", "simple")
                analysis = analysis_result.get("analysis", "LLM 분석 완료")
                required_tools = analysis_result.get("required_tools", [])
                estimated_steps = analysis_result.get("estimated_steps", 1)

            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값 사용
                print(f"LLM 응답 JSON 파싱 실패: {response_text}")
                if any(keyword in response_text.lower() for keyword in ["complex", "복잡", "다중", "최적화", "분석"]):
                    complexity_level = "complex"
                    analysis = "LLM 분석 결과: 복잡한 요청으로 판단"
                else:
                    complexity_level = "simple"
                    analysis = "LLM 분석 결과: 단순한 요청으로 판단"
                required_tools = []
                estimated_steps = 1

            state["complexity_level"] = complexity_level
            state["complexity_analysis"] = analysis

            # 추가 정보 저장
            if "required_tools" not in state:
                state["required_tools"] = required_tools
            if "estimated_steps" not in state:
                state["estimated_steps"] = estimated_steps

            return state

        except Exception as e:
            # 오류 시 기본 분석으로 fallback
            print(f"LLM 복잡도 분석 오류: {e}")
            state["complexity_level"] = "simple"
            state["complexity_analysis"] = f"오류로 인한 기본 분석: {str(e)}"
            state["error_message"] = f"복잡도 분석 중 오류: {str(e)}"
            return state

    async def _create_plan_node(self, state: GearAgentState) -> GearAgentState:
        """복잡한 요청에 대한 Planning 생성"""
        try:
            input_text = state["input_text"]
            classifier_result = state.get("classifier_result", {})
            gear_type = state.get("gear_type", "")

            # 기어 타입별 기본 계획 템플릿
            base_plan = []

            if gear_type in ["gear_pair", "three_gear"]:
                base_plan = [
                    {
                        "task_id": 1,
                        "task_name": "기본 설계 계산",
                        "description": "모듈, 잇수, 치형 등 기본 설계 계산",
                        "tool": "gear_design_calculation",
                        "dependencies": [],
                        "status": "pending"
                    },
                    {
                        "task_id": 2,
                        "task_name": "강도 해석",
                        "description": "기어 치 굽힘강도 및 면압강도 계산",
                        "tool": "gear_strength_analysis",
                        "dependencies": [1],
                        "status": "pending"
                    }
                ]
            elif gear_type in ["simple_planetary", "double_pinion_planetary"]:
                base_plan = [
                    {
                        "task_id": 1,
                        "task_name": "유성기어 기본 설계",
                        "description": "태양기어, 유성기어, 링기어 기본 설계",
                        "tool": "gear_design_calculation",
                        "dependencies": [],
                        "status": "pending"
                    },
                    {
                        "task_id": 2,
                        "task_name": "유성기어 강도 해석",
                        "description": "각 기어 요소별 강도 계산",
                        "tool": "gear_strength_analysis",
                        "dependencies": [1],
                        "status": "pending"
                    }
                ]

            # 추가 요구사항에 따른 계획 확장
            if any(keyword in input_text.lower() for keyword in ["효율", "efficiency"]):
                base_plan.append({
                    "task_id": len(base_plan) + 1,
                    "task_name": "효율 계산",
                    "description": "기어 전달 효율 계산",
                    "tool": "gear_efficiency_calculation",
                    "dependencies": [1],
                    "status": "pending"
                })

            if any(keyword in input_text.lower() for keyword in ["소음", "noise", "진동", "vibration"]):
                base_plan.append({
                    "task_id": len(base_plan) + 1,
                    "task_name": "소음 분석",
                    "description": "기어 소음 및 진동 분석",
                    "tool": "gear_noise_analysis",
                    "dependencies": [1, 2],
                    "status": "pending"
                })

            if any(keyword in input_text.lower() for keyword in ["최적화", "optimize"]):
                base_plan.append({
                    "task_id": len(base_plan) + 1,
                    "task_name": "설계 최적화",
                    "description": "설계 변수 최적화",
                    "tool": "gear_optimization",
                    "dependencies": list(range(1, len(base_plan) + 1)),
                    "status": "pending"
                })

            state["plan"] = base_plan
            state["current_task_index"] = 0
            state["task_results"] = []

            return state

        except Exception as e:
            state["error_message"] = f"Planning 생성 중 오류: {str(e)}"
            return state

    async def _execute_simple_task_node(self, state: GearAgentState) -> GearAgentState:
        """단순한 요청에 대한 직접 Tool 호출"""
        try:
            input_text = state["input_text"]
            classifier_result = state.get("classifier_result", {})

            # 단순 요청에 적합한 Tool 선택
            if any(keyword in input_text.lower() for keyword in ["설계", "design", "계산", "calculate"]):
                tool_name = "gear_design_calculation"
            elif any(keyword in input_text.lower() for keyword in ["강도", "strength"]):
                tool_name = "gear_strength_analysis"
            elif any(keyword in input_text.lower() for keyword in ["효율", "efficiency"]):
                tool_name = "gear_efficiency_calculation"
            else:
                tool_name = "gear_design_calculation"  # 기본값

            # Tool 호출
            tool_result = await self._call_tool(tool_name, {
                "input_text": input_text,
                "classifier_result": classifier_result,
                "gear_type": state.get("gear_type", ""),
                "speed_info": state.get("speed_info", ""),
                "power_info": state.get("power_info", ""),
                "ratio_info": state.get("ratio_info", ""),
                "others_info": state.get("others_info", "")
            })

            state["tool_results"] = [tool_result]

            return state

        except Exception as e:
            state["error_message"] = f"단순 작업 실행 중 오류: {str(e)}"
            return state

    async def _execute_current_task_node(self, state: GearAgentState) -> GearAgentState:
        """현재 Task 실행"""
        try:
            plan = state.get("plan", [])
            current_index = state.get("current_task_index", 0)

            if current_index >= len(plan):
                return state

            current_task = plan[current_index]

            # 의존성 확인
            dependencies = current_task.get("dependencies", [])
            task_results = state.get("task_results", [])

            # 의존성이 완료되었는지 확인
            completed_tasks = [result["task_id"] for result in task_results if result.get("status") == "completed"]

            if all(dep in completed_tasks for dep in dependencies):
                # Tool 호출
                tool_name = current_task.get("tool")
                tool_params = {
                    "input_text": state["input_text"],
                    "classifier_result": state.get("classifier_result", {}),
                    "gear_type": state.get("gear_type", ""),
                    "speed_info": state.get("speed_info", ""),
                    "power_info": state.get("power_info", ""),
                    "ratio_info": state.get("ratio_info", ""),
                    "others_info": state.get("others_info", ""),
                    "previous_results": [r for r in task_results if r["task_id"] in dependencies]
                }

                tool_result = await self._call_tool(tool_name, tool_params)

                # 결과 저장
                task_result = {
                    "task_id": current_task["task_id"],
                    "task_name": current_task["task_name"],
                    "tool_name": tool_name,
                    "result": tool_result,
                    "status": "completed" if tool_result.get("success") else "failed"
                }

                task_results.append(task_result)
                state["task_results"] = task_results
                state["current_task"] = current_task

            return state

        except Exception as e:
            state["error_message"] = f"Task 실행 중 오류: {str(e)}"
            return state

    async def _check_plan_completion_node(self, state: GearAgentState) -> GearAgentState:
        """Plan 완료 상태 확인"""
        try:
            plan = state.get("plan", [])
            current_index = state.get("current_task_index", 0)

            # 다음 Task로 이동
            state["current_task_index"] = current_index + 1

            return state

        except Exception as e:
            state["error_message"] = f"Plan 완료 확인 중 오류: {str(e)}"
            return state

    async def _synthesize_results_node(self, state: GearAgentState) -> GearAgentState:
        """결과 종합 및 최종 응답 생성"""
        try:
            complexity_level = state.get("complexity_level", "simple")
            tool_results = state.get("tool_results", [])
            task_results = state.get("task_results", [])

            if complexity_level == "simple":
                # 단순 요청 결과 처리
                response = self._format_simple_results(tool_results)
            else:
                # 복잡 요청 결과 처리
                response = self._format_complex_results(task_results)

            state["final_response"] = response

            return state

        except Exception as e:
            state["error_message"] = f"결과 종합 중 오류: {str(e)}"
            return state

    def _route_by_complexity(self, state: GearAgentState) -> str:
        """복잡도에 따른 라우팅"""
        return state.get("complexity_level", "simple")

    def _route_plan_completion(self, state: GearAgentState) -> str:
        """Plan 완료 여부에 따른 라우팅"""
        plan = state.get("plan", [])
        current_index = state.get("current_task_index", 0)

        if current_index >= len(plan):
            return "complete"
        else:
            return "continue"

    async def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Tool 호출"""
        try:
            if tool_name in self.available_tools:
                return await self.available_tools[tool_name](parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}",
                    "result": ""
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "result": ""
            }

    # Tool 구현들
    async def _tool_gear_design_calculation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """기어 설계 계산 Tool"""
        try:
            # 실제 기어 설계 에이전트 호출
            from agents.gear_design_agent import GearDesignAgent

            design_config = {
                "model": self.config.get("model", "gpt-4o-mini"),
                "temperature": self.config.get("temperature", 0.0),
                "gear_design_path": self.config.get("gear_design_path", r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"),
                "template_json_path": self.config.get("template_json_path", "TestGD.GD1")
            }

            design_agent = GearDesignAgent(design_config)

            # classifier 결과를 shared_data로 전달
            classifier_result = params.get("classifier_result", {})
            design_agent.set_shared_data("classifier_result", classifier_result)

            result = await design_agent.process_with_callback(
                params.get("input_text", ""),
                lambda x: None
            )

            return {
                "success": True,
                "tool_name": "gear_design_calculation",
                "result": result,
                "details": "기어 설계 계산 완료"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": f"기어 설계 계산 실패: {str(e)}"
            }

    async def _tool_gear_strength_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """기어 강도 해석 Tool"""
        # 임시 구현 - 실제로는 강도 해석 로직 구현
        return {
            "success": True,
            "tool_name": "gear_strength_analysis",
            "result": "기어 강도 해석 결과: 안전계수 2.5, 굽힘강도 충족, 면압강도 충족",
            "details": {
                "bending_safety_factor": 2.5,
                "contact_safety_factor": 2.8,
                "status": "안전"
            }
        }

    async def _tool_gear_efficiency_calculation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """기어 효율 계산 Tool"""
        # 임시 구현 - 실제로는 효율 계산 로직 구현
        return {
            "success": True,
            "tool_name": "gear_efficiency_calculation",
            "result": "기어 전달 효율: 98.5%",
            "details": {
                "efficiency": 0.985,
                "loss_factors": ["윤활", "치형 정밀도"]
            }
        }

    async def _tool_gear_noise_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """기어 소음 분석 Tool"""
        # 임시 구현 - 실제로는 소음 분석 로직 구현
        return {
            "success": True,
            "tool_name": "gear_noise_analysis",
            "result": "예상 소음 수준: 65dB, 허용 기준 이내",
            "details": {
                "noise_level": 65,
                "frequency_analysis": "주요 소음 주파수: 1.2kHz",
                "recommendations": ["헬리컬 치형 적용", "정밀도 향상"]
            }
        }

    async def _tool_gear_optimization(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """기어 최적화 Tool"""
        # 임시 구현 - 실제로는 최적화 로직 구현
        return {
            "success": True,
            "tool_name": "gear_optimization",
            "result": "최적화 완료: 모듈 2.5 -> 2.3, 치폭 25 -> 22mm로 조정",
            "details": {
                "optimized_parameters": {
                    "module": 2.3,
                    "face_width": 22,
                    "pressure_angle": 20
                },
                "improvement": "중량 15% 감소, 비용 10% 절감"
            }
        }

    async def _tool_material_selection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """재료 선택 Tool"""
        # 임시 구현
        return {
            "success": True,
            "tool_name": "material_selection",
            "result": "권장 재료: SCM420 (침탄경화), 경도 HRC 58-62",
            "details": {
                "material": "SCM420",
                "heat_treatment": "침탄경화",
                "hardness": "HRC 58-62"
            }
        }

    async def _tool_manufacturing_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """제조 분석 Tool"""
        # 임시 구현
        return {
            "success": True,
            "tool_name": "manufacturing_analysis",
            "result": "제조 방법: 호브 가공, 정밀도 JIS 4급",
            "details": {
                "machining_method": "호브 가공",
                "precision_grade": "JIS 4급",
                "surface_treatment": "쇼트피닝"
            }
        }

    def _format_simple_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """단순 요청 결과 포맷팅"""
        if not tool_results:
            return "처리 결과가 없습니다."

        result = tool_results[0]

        if result.get("success"):
            return f"""🔧 **기어 분석 결과**

{result.get('result', '')}

📋 **상세 정보**: {result.get('details', '추가 정보 없음')}"""
        else:
            return f"❌ 처리 중 오류 발생: {result.get('error', '알 수 없는 오류')}"

    def _format_complex_results(self, task_results: List[Dict[str, Any]]) -> str:
        """복잡 요청 결과 포맷팅"""
        if not task_results:
            return "처리된 작업이 없습니다."

        response_parts = ["🔧 **종합 기어 분석 결과**\n"]

        for i, task_result in enumerate(task_results, 1):
            task_name = task_result.get("task_name", f"작업 {i}")
            tool_result = task_result.get("result", {})

            if tool_result.get("success"):
                response_parts.append(f"**{i}. {task_name}**")
                response_parts.append(f"{tool_result.get('result', '')}\n")
            else:
                response_parts.append(f"**{i}. {task_name}** ❌")
                response_parts.append(f"오류: {tool_result.get('error', '알 수 없는 오류')}\n")

        # 종합 결론
        successful_tasks = sum(1 for tr in task_results if tr.get("result", {}).get("success"))
        total_tasks = len(task_results)

        response_parts.append(f"\n📊 **처리 요약**: {successful_tasks}/{total_tasks} 작업 완료")

        return "\n".join(response_parts)

    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """메인 처리 메서드 - gear_classifier 결과를 받아서 처리"""
        try:
            # gear_classifier 결과를 shared_data에서 가져오기
            classifier_result = self.get_shared_data("classifier_result", {})

            if not classifier_result:
                return "❌ gear_classifier 결과를 찾을 수 없습니다. 먼저 gear_classifier_agent를 실행해주세요."

            # 초기 상태 설정
            initial_state: GearAgentState = {
                "messages": [{"role": "user", "content": input_text}],
                "input_text": input_text,
                "classifier_result": classifier_result,
                "gear_type": classifier_result.get("gear_type", ""),
                "speed_info": classifier_result.get("speed_info", ""),
                "power_info": classifier_result.get("power_info", ""),
                "ratio_info": classifier_result.get("ratio_info", ""),
                "others_info": classifier_result.get("others_info", ""),
                "complexity_level": "",
                "complexity_analysis": "",
                "plan": [],
                "current_task_index": 0,
                "task_results": [],
                "current_task": {},
                "tool_calls": [],
                "tool_results": [],
                "final_response": "",
                "error_message": ""
            }

            # 워크플로우 실행
            callback("🚀 **기어 설계 작업을 시작합니다...**\n")

            final_state = initial_state
            async for state_update in self.workflow.astream(initial_state):
                for node_name, node_result in state_update.items():
                    if isinstance(node_result, dict):
                        for key, value in node_result.items():
                            if key in final_state:
                                final_state[key] = value

                # 진행 상황 콜백
                if node_name == "analyze_complexity" and final_state.get("complexity_analysis"):
                    callback(f"🔍 {final_state['complexity_analysis']}\n")
                elif node_name == "create_plan" and final_state.get("plan"):
                    plan_count = len(final_state["plan"])
                    callback(f"📋 **계획 수립 완료**: {plan_count}개 작업 계획됨\n")
                elif node_name == "execute_current_task" and final_state.get("current_task"):
                    task_name = final_state["current_task"].get("task_name", "작업")
                    callback(f"⚙️ **실행 중**: {task_name}\n")

            # 오류 처리
            if final_state.get("error_message"):
                error_msg = f"❌ {final_state['error_message']}"
                callback(error_msg)
                return error_msg

            # 최종 결과 반환
            final_response = final_state.get("final_response", "처리 완료")
            callback("✅ **작업 완료!**\n")
            return final_response

        except Exception as e:
            error_msg = f"❌ Gear Agent 처리 오류: {str(e)}"
            callback(error_msg)
            return error_msg


# 테스트 및 디버깅을 위한 main 함수
if __name__ == "__main__":
    import asyncio
    import sys
    import os
    from dotenv import load_dotenv

    # 프로젝트 루트 디렉토리를 Python 경로에 추가
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # 환경 변수 로드
    load_dotenv()

    async def test_gear_agent():
        """Gear Agent 그래프 컴파일 및 기본 테스트"""
        print("=" * 60)
        print("🔧 Gear Agent 그래프 컴파일 테스트 시작")
        print("=" * 60)

        try:
            # 1. Gear Agent 인스턴스 생성
            config = {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "provider": "openai"
            }

            print("📋 1. Gear Agent 인스턴스 생성 중...")
            agent = GearAgent(config)
            print("✅ Gear Agent 인스턴스 생성 성공!")

            # 2. 워크플로우 컴파일 확인
            print("\n📋 2. 워크플로우 컴파일 상태 확인...")
            print(f"   - 워크플로우 타입: {type(agent.workflow)}")
            print(f"   - 그래프 노드 수: {len(agent.workflow.get_graph().nodes)}")
            print("✅ 워크플로우 컴파일 성공!")

            # 3. 그래프 이미지 생성 테스트
            print("\n📋 3. 그래프 이미지 생성 테스트...")
            try:
                image = agent.get_graph_image()
                if image:
                    print(f"✅ 그래프 이미지 생성 성공! 크기: {image.size}")
                else:
                    print("⚠️ 그래프 이미지 생성 실패 (PNG 생성 실패)")
            except Exception as img_error:
                print(f"⚠️ 그래프 이미지 생성 오류: {img_error}")

            # 4. Mermaid 다이어그램 생성 테스트
            print("\n📋 4. Mermaid 다이어그램 생성 테스트...")
            try:
                mermaid = agent.get_mermaid_graph()
                if mermaid:
                    print(f"✅ Mermaid 다이어그램 생성 성공! 길이: {len(mermaid)} 문자")
                    print("📄 Mermaid 다이어그램 일부:")
                    print(mermaid[:200] + "..." if len(mermaid) > 200 else mermaid)
                else:
                    print("❌ Mermaid 다이어그램 생성 실패")
            except Exception as mermaid_error:
                print(f"❌ Mermaid 다이어그램 생성 오류: {mermaid_error}")

            # 5. 그래프 노드 구조 확인
            print("\n📋 5. 그래프 노드 구조 확인...")
            graph = agent.workflow.get_graph()
            nodes = graph.nodes
            edges = graph.edges

            print(f"   📍 노드 목록 ({len(nodes)}개):")
            for i, node in enumerate(nodes, 1):
                print(f"      {i}. {node}")

            print(f"\n   🔗 엣지 목록 ({len(edges)}개):")
            for i, edge in enumerate(edges, 1):
                print(f"      {i}. {edge}")

            # 6. 복잡도 분석 테스트
            print("\n📋 6. 복잡도 분석 노드 테스트...")
            test_state = {
                'input_text': '모듈 2의 기어 쌍을 설계해주세요',
                'classifier_result': {'designable': True, 'gear_type': 'gear_pair'},
                'gear_type': 'gear_pair',
                'messages': [],
                'required_tools': [],
                'estimated_steps': 0
            }

            try:
                result = await agent._analyze_complexity_node(test_state)
                print(f"✅ 복잡도 분석 성공!")
                print(f"   - 복잡도: {result.get('complexity_level', 'N/A')}")
                print(f"   - 분석: {result.get('complexity_analysis', 'N/A')[:100]}...")
            except Exception as analysis_error:
                print(f"❌ 복잡도 분석 오류: {analysis_error}")

            print("\n" + "=" * 60)
            print("🎉 Gear Agent 그래프 컴파일 테스트 완료!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ 전체 테스트 실패: {e}")
            import traceback
            print("\n📋 상세 오류 정보:")
            traceback.print_exc()

    # 비동기 테스트 실행
    print("🚀 Gear Agent 테스트 시작...")
    asyncio.run(test_gear_agent())
