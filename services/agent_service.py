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
from agents.gpt_agent import GPTAgent

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
        
        # GPT 에이전트 설정
        gpt_config = {
            "model": "gpt-4o-mini",
            "temperature": 0.7
        }
        self.register_agent("Gear Agent", GPTAgent(gpt_config)) 
        
    def register_agent(self, name: str, agent: BaseAgent):
        """새로운 에이전트를 등록합니다."""
        self.agents[name] = agent
        
    async def process_with_callback(self, agent_name: str, input_text: str, callback: Callable[[str], None]) -> str:
        """
        지정된 에이전트로 입력을 처리하고 콜백으로 결과를 반환합니다.
        - 에이전트의 실제 처리 로직은 BaseAgent의 process_with_callback에 위임
        - AgentService는 에이전트 선택 및 호출만 담당
        """
        if agent_name not in self.agents:
            error_msg = f"알 수 없는 에이전트 타입: {agent_name}"
            callback(error_msg)
            return error_msg
            
        try:
            agent = self.agents[agent_name]
            return await agent.process_with_callback(input_text, callback)
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