# AgentService: 여러 에이전트 인스턴스를 관리하고, 선택하여 호출하는 관리자/중개자 역할
# 각 에이전트는 BaseAgent를 상속받아, 실제 처리 로직(process_with_callback 등)을 구현함
from typing import Dict, Any, Optional, AsyncGenerator, Callable, List
import sys
import os
import asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.base_agent import BaseAgent
from agents.chat_agent import ChatAgent
from agents.gear_classifier_agent import GearClassifierAgent
from agents.gear_design_agent import GearDesignAgent
from agents.gear_agent import GearAgent

class AgentService:
    """
    역할:
    - 여러 에이전트 인스턴스(GPT, DeepResearch 등)를 관리
    - 사용자가 선택한 에이전트에 입력과 콜백을 전달하여 실제 처리는 각 에이전트가 담당
    - 에이전트의 행동(응답 생성)은 BaseAgent의 process_with_callback에 위임
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """기본 에이전트들을 초기화합니다."""
        
        # Chat 에이전트 설정
        chat_config = {
            "model": "gpt-5-mini",
            "temperature": 0.1
        }
        self.register_agent("Chatbot", ChatAgent(chat_config))
        
        # Gear Classifier 에이전트 설정
        gear_config = {
            "model": "gpt-5-mini",
            "temperature": 0.1
        }
        self.register_agent("Gear Classifier", GearClassifierAgent(gear_config))
        
        # Gear Design 에이전트 설정
        gear_design_config = {
            "model": "gpt-5-mini",
            "temperature": 0.0,
            "gear_design_path": r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows",
            "template_json_path": str(os.path.join(project_root, "TestGD.GD1"))
        }
        self.register_agent("Gear Design", GearDesignAgent(gear_design_config))
        
        # 통합 Gear 에이전트 설정 (MCP 기반)
        gear_agent_config = {
            "model": "gpt-5-mini",
            "temperature": 0.0,
            "gear_design_path": r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows",
            "template_json_path": str(os.path.join(project_root, "TestGD.GD1"))
        }
        self.register_agent("Gear Agent", GearAgent(gear_agent_config)) 
        
    def register_agent(self, name: str, agent: BaseAgent):
        """새로운 에이전트를 등록합니다."""
        self.agents[name] = agent
        
    async def process_with_callback(self, agent_name: str, input_text: str, callback: Callable[[str], None]) -> str:
        """
        지정된 에이전트로 입력을 처리하고 콜백으로 결과를 반환합니다.
        - 에이전트의 실제 처리 로직은 BaseAgent의 process_with_callback에 위임
        - AgentService는 에이전트 선택 및 호출만 담당
        - gear_classifier_agent의 perform_design 결과 시 gear_agent 자동 연결
        """
        if agent_name not in self.agents:
            error_msg = f"알 수 없는 에이전트 타입: {agent_name}"
            callback(error_msg)
            return error_msg

        try:
            agent = self.agents[agent_name]
            result = await agent.process_with_callback(input_text, callback)

            # gear_classifier_agent의 결과를 확인하여 자동 연결 처리
            if agent_name == "Gear Classifier" and hasattr(agent, 'state') and agent.state:
                final_state = agent.state.get("final_state", "")

                # perform_design으로 끝났다면 gear_agent를 자동 호출
                if final_state == "perform_design":
                    callback("\n" + "="*50 + "\n")
                    callback("🔄 **자동 연결**: gear_classifier → gear_agent (Planning 모드)\n")
                    callback("📋 기어 설계 Planning을 시작합니다...\n")
                    callback("="*50 + "\n\n")

                    # gear_agent에 classifier 결과 전달
                    if "Gear Agent" in self.agents:
                        gear_agent = self.agents["Gear Agent"]

                        # shared_data를 gear_classifier에서 gear_agent로 복사
                        if hasattr(agent, 'shared_data'):
                            for key, value in agent.shared_data.items():
                                gear_agent.set_shared_data(key, value)

                        # gear_agent를 Planning 모드로 호출
                        gear_result = await gear_agent.process_with_callback(input_text, callback)

                        # 두 결과를 합쳐서 반환
                        return result + "\n\n" + "="*50 + "\n🎯 **Planning 결과**:\n" + gear_result

            return result

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"에이전트 처리 중 오류 발생: {str(e)}\n{error_detail}"
            callback(error_msg)
            return error_msg
               
    def get_available_agents(self) -> list:
        """사용 가능한 에이전트 목록을 반환합니다."""
        return list(self.agents.keys())
        
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """에이전트의 설정을 반환합니다."""
        if agent_name in self.agents:
            return self.agents[agent_name].config
        return None 