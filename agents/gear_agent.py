"""
MCP Tool 기반 Gear Agent: 사용자 요청에 따라 적절한 MCP Tool을 호출하여 기어 설계 수행
- 사용자 요청 분석 → MCP Tool 호출 → 결과 처리 → 추가 Tool 호출 → 만족도 판단 → 답변 전달
- 체인 방식으로 여러 MCP Tool을 연속 호출하여 복합적인 기어 설계 작업 수행
"""
from typing import Dict, Any, Optional, AsyncGenerator, Callable, List
import asyncio
import json
import re
from datetime import datetime

from agents.base_agent import BaseAgent


class MCPToolCall:
    """MCP Tool 호출 정보"""
    def __init__(self, tool_name: str, parameters: Dict[str, Any], purpose: str):
        self.tool_name = tool_name
        self.parameters = parameters
        self.purpose = purpose
        self.result = None
        self.success = False
        self.error_message = ""
        
class GearAgentState:
    """Gear Agent 상태 관리"""
    def __init__(self):
        self.input_text = ""
        self.current_step = ""
        self.mcp_call_history: List[MCPToolCall] = []
        self.intermediate_results: List[Dict[str, Any]] = []
        self.user_satisfaction_level = 0  # 0-100 점수
        self.needs_additional_processing = True
        self.final_result = ""
        self.error_message = ""


class GearAgent(BaseAgent):
    """MCP Tool 호출 기반 Gear Agent"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.agent_name = "MCP Gear Agent"
        self.state = GearAgentState()
        
        # MCP Tool 설정
        self.available_mcp_tools = {
            "gear_classifier": "기어 분류 및 사양 추출",
            "gear_design": "기어 설계 계산 및 검증",
            "gear_analysis": "기어 강도 및 성능 분석",
            "gear_optimization": "기어 최적화 및 개선",
            "gear_validation": "기어 설계 검증 및 표준 준수"
        }
        
        # 만족도 판단 임계값
        self.satisfaction_threshold = 80
        
    async def _analyze_user_request(self, input_text: str) -> List[str]:
        """사용자 요청을 분석하여 필요한 MCP Tool 목록 반환"""
        try:
            # 기어 관련 키워드 및 의도 분석
            gear_keywords = {
                "분류": ["분류", "종류", "타입", "유형", "구분"],
                "설계": ["설계", "계산", "치수", "모듈", "잇수", "피치"],
                "분석": ["강도", "응력", "안전율", "수명", "성능", "분석"],
                "최적화": ["최적화", "개선", "효율", "향상"],
                "검증": ["검증", "확인", "검토", "표준", "규격"]
            }
            
            needed_tools = []
            input_lower = input_text.lower()
            
            for category, keywords in gear_keywords.items():
                if any(keyword in input_lower for keyword in keywords):
                    if category == "분류":
                        needed_tools.append("gear_classifier")
                    elif category == "설계":
                        needed_tools.append("gear_design")
                    elif category == "분석":
                        needed_tools.append("gear_analysis")
                    elif category == "최적화":
                        needed_tools.append("gear_optimization")
                    elif category == "검증":
                        needed_tools.append("gear_validation")
            
            # 기본적으로 classifier는 항상 포함
            if not needed_tools or "gear_classifier" not in needed_tools:
                needed_tools.insert(0, "gear_classifier")
                
            # 설계가 필요하면 design도 포함
            if any(keyword in input_lower for keyword in ["설계", "계산", "치수"]):
                if "gear_design" not in needed_tools:
                    needed_tools.append("gear_design")
            
            return list(dict.fromkeys(needed_tools))  # 중복 제거
            
        except Exception as e:
            print(f"요청 분석 오류: {e}")
            return ["gear_classifier"]  # 기본값

    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any], purpose: str, callback: Callable[[str], None]) -> MCPToolCall:
        """MCP Tool 호출 및 결과 처리"""
        tool_call = MCPToolCall(tool_name, parameters, purpose)
        
        try:
            callback(f"🔧 {purpose} 시작 중...")
            
            # MCP Tool 호출 시뮬레이션 (실제로는 MCP 서버 호출)
            if tool_name == "gear_classifier":
                result = await self._simulate_gear_classifier(parameters)
            elif tool_name == "gear_design":
                result = await self._simulate_gear_design(parameters)
            elif tool_name == "gear_analysis":
                result = await self._simulate_gear_analysis(parameters)
            elif tool_name == "gear_optimization":
                result = await self._simulate_gear_optimization(parameters)
            elif tool_name == "gear_validation":
                result = await self._simulate_gear_validation(parameters)
            else:
                raise ValueError(f"알 수 없는 MCP Tool: {tool_name}")
            
            tool_call.result = result
            tool_call.success = True
            callback(f"✅ {purpose} 완료")
            
        except Exception as e:
            tool_call.error_message = str(e)
            tool_call.success = False
            callback(f"❌ {purpose} 실패: {str(e)}")
        
        return tool_call

    async def _simulate_gear_classifier(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """기어 분류기 MCP Tool 시뮬레이션"""
        await asyncio.sleep(1)  # 처리 시간 시뮬레이션
        return {
            "gear_type": "spur_gear",
            "application": "power_transmission",
            "requirements": {
                "module": 2.0,
                "teeth_count": 20,
                "pressure_angle": 20,
                "material": "steel"
            },
            "confidence": 0.95
        }

    async def _simulate_gear_design(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """기어 설계 MCP Tool 시뮬레이션"""
        await asyncio.sleep(2)  # 처리 시간 시뮬레이션
        return {
            "design_parameters": {
                "module": 2.0,
                "teeth_count": 20,
                "pitch_diameter": 40.0,
                "addendum": 2.0,
                "dedendum": 2.5,
                "tooth_thickness": 3.14
            },
            "geometry": {
                "outside_diameter": 44.0,
                "root_diameter": 35.0,
                "center_distance": 40.0
            },
            "manufacturing": {
                "precision_grade": "ISO 6",
                "surface_roughness": "Ra 1.6"
            }
        }

    async def _simulate_gear_analysis(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """기어 분석 MCP Tool 시뮬레이션"""
        await asyncio.sleep(1.5)  # 처리 시간 시뮬레이션
        return {
            "stress_analysis": {
                "bending_stress": 150.5,
                "contact_stress": 800.2,
                "safety_factor_bending": 2.8,
                "safety_factor_contact": 1.9
            },
            "performance": {
                "efficiency": 0.985,
                "power_rating": 15.2,
                "max_torque": 150.0
            },
            "life_prediction": {
                "cycles_to_failure": 1000000,
                "estimated_life_hours": 8760
            }
        }

    async def _simulate_gear_optimization(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """기어 최적화 MCP Tool 시뮬레이션"""
        await asyncio.sleep(2.5)  # 처리 시간 시뮬레이션
        return {
            "optimized_parameters": {
                "module": 1.8,  # 최적화된 값
                "teeth_count": 22,
                "face_width": 25.0,
                "material_grade": "AISI 4140"
            },
            "improvement": {
                "weight_reduction": 0.12,
                "efficiency_gain": 0.02,
                "cost_reduction": 0.08
            },
            "optimization_criteria": [
                "minimize_weight",
                "maximize_efficiency",
                "reduce_cost"
            ]
        }

    async def _simulate_gear_validation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """기어 검증 MCP Tool 시뮬레이션"""
        await asyncio.sleep(1)  # 처리 시간 시뮬레이션
        return {
            "standard_compliance": {
                "iso_6336": True,
                "agma_2001": True,
                "din_3990": True
            },
            "validation_results": {
                "geometry_check": "PASS",
                "strength_check": "PASS",
                "manufacturing_feasibility": "PASS",
                "quality_grade": "A"
            },
            "recommendations": [
                "설계가 모든 표준을 만족합니다",
                "제조 가능성이 높습니다",
                "추가 최적화 가능"
            ]
        }

    async def _evaluate_user_satisfaction(self) -> int:
        """사용자 요청 만족도 평가 (0-100 점수)"""
        try:
            satisfaction_score = 0
            
            # MCP Tool 호출 성공률 평가 (40점)
            if self.state.mcp_call_history:
                success_rate = sum(1 for call in self.state.mcp_call_history if call.success) / len(self.state.mcp_call_history)
                satisfaction_score += int(success_rate * 40)
            
            # 결과의 완전성 평가 (30점)
            if self.state.intermediate_results:
                completeness = min(len(self.state.intermediate_results) / 3, 1.0)  # 3개 이상 결과면 완전
                satisfaction_score += int(completeness * 30)
            
            # 오류 없음 보너스 (20점)
            if not self.state.error_message:
                satisfaction_score += 20
            
            # 추가 처리 필요성 평가 (10점)
            if not self.state.needs_additional_processing:
                satisfaction_score += 10
            
            return min(satisfaction_score, 100)
            
        except Exception as e:
            print(f"만족도 평가 오류: {e}")
            return 0

    async def _determine_next_tool(self, current_results: List[Dict[str, Any]]) -> Optional[str]:
        """현재 결과를 바탕으로 다음에 호출할 MCP Tool 결정"""
        try:
            # 이미 호출된 도구 목록
            called_tools = [call.tool_name for call in self.state.mcp_call_history if call.success]
            
            # 분류가 완료되었고 설계가 필요한 경우
            if "gear_classifier" in called_tools and "gear_design" not in called_tools:
                return "gear_design"
            
            # 설계가 완료되었고 분석이 필요한 경우
            if "gear_design" in called_tools and "gear_analysis" not in called_tools:
                # 사용자 요청에 강도나 성능 키워드가 있으면 분석 수행
                if any(keyword in self.state.input_text.lower() for keyword in ["강도", "응력", "성능", "분석"]):
                    return "gear_analysis"
            
            # 기본 설계가 완료되었고 최적화가 요청된 경우
            if "gear_design" in called_tools and "gear_optimization" not in called_tools:
                if any(keyword in self.state.input_text.lower() for keyword in ["최적화", "개선", "효율"]):
                    return "gear_optimization"
            
            # 모든 계산이 완료되었고 검증이 필요한 경우
            if len(called_tools) >= 2 and "gear_validation" not in called_tools:
                if any(keyword in self.state.input_text.lower() for keyword in ["검증", "확인", "표준", "규격"]):
                    return "gear_validation"
            
            return None  # 추가 도구 불필요
            
        except Exception as e:
            print(f"다음 도구 결정 오류: {e}")
            return None

    async def _generate_final_response(self) -> str:
        """최종 응답 생성"""
        try:
            if self.state.error_message:
                return f"❌ 오류 발생: {self.state.error_message}"
            
            if not self.state.mcp_call_history:
                return "❓ MCP Tool 호출 기록이 없습니다."
            
            # 성공한 호출들의 결과 정리
            successful_results = []
            for call in self.state.mcp_call_history:
                if call.success and call.result:
                    successful_results.append({
                        "tool": call.tool_name,
                        "purpose": call.purpose,
                        "result": call.result
                    })
            
            # 최종 보고서 생성
            final_response = f"""
🔧 **MCP 기반 기어 설계 완료**

## 📋 실행된 작업
{chr(10).join(f"✅ {result['purpose']}" for result in successful_results)}

## 📊 주요 결과
"""
            
            # 각 도구별 결과 요약
            for result in successful_results:
                final_response += f"\n### {result['tool'].replace('_', ' ').title()}\n"
                if isinstance(result['result'], dict):
                    for key, value in result['result'].items():
                        if isinstance(value, dict):
                            final_response += f"- **{key}**: {len(value)} 항목\n"
                        else:
                            final_response += f"- **{key}**: {value}\n"
                else:
                    final_response += f"{result['result']}\n"
            
            # 만족도 점수 추가
            satisfaction = self.state.user_satisfaction_level
            final_response += f"\n## 🎯 작업 만족도: {satisfaction}/100\n"
            
            if satisfaction >= self.satisfaction_threshold:
                final_response += "✅ 사용자 요구사항이 충분히 충족되었습니다.\n"
            else:
                final_response += "⚠️ 추가 작업이 필요할 수 있습니다.\n"
                
            final_response += f"\n**완료 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            return final_response
            
        except Exception as e:
            return f"❌ 최종 응답 생성 오류: {str(e)}"

    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """MCP Tool 체인 호출 기반 메인 처리 메서드"""
        try:
            # 상태 초기화
            self.state = GearAgentState()
            self.state.input_text = input_text
            
            callback(f"🔍 사용자 요청 분석: {input_text[:100]}...")
            
            # 1단계: 요청 분석 및 필요한 MCP Tool 결정
            needed_tools = await self._analyze_user_request(input_text)
            callback(f"📋 필요한 MCP Tool: {', '.join(needed_tools)}")
            
            # 2단계: MCP Tool 순차 호출
            for tool_name in needed_tools:
                purpose = self.available_mcp_tools.get(tool_name, "알 수 없는 작업")
                
                # 이전 결과를 바탕으로 파라미터 구성
                parameters = {
                    "input_text": input_text,
                    "previous_results": self.state.intermediate_results
                }
                
                # MCP Tool 호출
                tool_call = await self._call_mcp_tool(tool_name, parameters, purpose, callback)
                self.state.mcp_call_history.append(tool_call)
                
                if tool_call.success:
                    self.state.intermediate_results.append(tool_call.result)
                else:
                    self.state.error_message = tool_call.error_message
                    break
                
                # 만족도 중간 평가
                current_satisfaction = await self._evaluate_user_satisfaction()
                self.state.user_satisfaction_level = current_satisfaction
                
                # 추가 처리 필요성 판단
                next_tool = await self._determine_next_tool(self.state.intermediate_results)
                if next_tool and next_tool not in needed_tools:
                    needed_tools.append(next_tool)
                    callback(f"🔄 추가 작업 발견: {self.available_mcp_tools.get(next_tool, next_tool)}")
            
            # 3단계: 최종 만족도 평가
            final_satisfaction = await self._evaluate_user_satisfaction()
            self.state.user_satisfaction_level = final_satisfaction
            
            # 만족도가 임계값 이하면 추가 처리 제안
            if final_satisfaction < self.satisfaction_threshold:
                self.state.needs_additional_processing = True
                callback(f"⚠️ 만족도 {final_satisfaction}/100 - 추가 작업을 권장합니다.")
            else:
                self.state.needs_additional_processing = False
                callback(f"✅ 만족도 {final_satisfaction}/100 - 요구사항이 충족되었습니다.")
            
            # 4단계: 최종 결과 생성 및 반환
            self.state.final_result = await self._generate_final_response()
            return self.state.final_result
            
        except Exception as e:
            error_msg = f"❌ MCP Gear Agent 처리 오류: {str(e)}"
            callback(error_msg)
            return error_msg

    def get_status_summary(self) -> Dict[str, Any]:
        """현재 상태 요약 정보 반환"""
        return {
            "agent_name": self.agent_name,
            "current_step": self.state.current_step,
            "mcp_calls_completed": len([call for call in self.state.mcp_call_history if call.success]),
            "mcp_calls_failed": len([call for call in self.state.mcp_call_history if not call.success]),
            "user_satisfaction": self.state.user_satisfaction_level,
            "needs_additional_processing": self.state.needs_additional_processing,
            "available_tools": list(self.available_mcp_tools.keys()),
            "completion_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_mcp_call_history(self) -> List[Dict[str, Any]]:
        """MCP Tool 호출 기록 반환"""
        return [
            {
                "tool_name": call.tool_name,
                "purpose": call.purpose,
                "success": call.success,
                "error_message": call.error_message if not call.success else None,
                "result_summary": str(call.result)[:100] + "..." if call.result else None
            }
            for call in self.state.mcp_call_history
        ]