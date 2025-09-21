from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os

# 상위 디렉토리의 services 모듈을 import하기 위해 path 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()

class AgentInfo(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    config: Optional[dict] = None

class AgentConfigResponse(BaseModel):
    agent_type: str
    config: dict

@router.get("/available")
async def get_available_agents() -> List[str]:
    """사용 가능한 에이전트 목록 조회"""
    try:
        from services.agent_service import AgentService
        agent_service = AgentService()
        return agent_service.get_available_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config/{agent_type}")
async def get_agent_config(agent_type: str) -> AgentConfigResponse:
    """특정 에이전트의 설정 조회"""
    try:
        from services.agent_service import AgentService
        agent_service = AgentService()

        config = agent_service.get_agent_config(agent_type)
        if config is None:
            raise HTTPException(status_code=404, detail=f"Agent {agent_type} not found")

        return AgentConfigResponse(agent_type=agent_type, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_agents_info() -> List[AgentInfo]:
    """모든 에이전트 정보 조회"""
    try:
        from services.agent_service import AgentService
        agent_service = AgentService()

        agents = agent_service.get_available_agents()
        agents_info = []

        for agent_name in agents:
            config = agent_service.get_agent_config(agent_name)
            agents_info.append(AgentInfo(
                name=agent_name,
                type=agent_name.lower().replace(" ", "_"),
                description=f"{agent_name} 에이전트",
                config=config
            ))

        return agents_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/{agent_type}")
async def get_agent_workflow(agent_type: str):
    """에이전트 워크플로우 정보 조회"""
    try:
        from services.agent_service import AgentService
        agent_service = AgentService()

        if agent_type not in agent_service.agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_type} not found")

        agent = agent_service.agents[agent_type]

        # 워크플로우 시각화 가능 여부 확인
        has_workflow = hasattr(agent, 'get_graph_image') or hasattr(agent, 'get_mermaid_graph')

        workflow_info = {
            "agent_type": agent_type,
            "has_workflow": has_workflow,
            "supports_langgraph": agent_type in ["Gear Classifier", "Gear Design", "Gear Agent"]
        }

        # Mermaid 그래프가 있는 경우 추가
        if hasattr(agent, 'get_mermaid_graph'):
            try:
                mermaid_graph = agent.get_mermaid_graph()
                workflow_info["mermaid_graph"] = mermaid_graph
            except:
                pass

        return workflow_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))