from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

# 상위 디렉토리의 services 모듈을 import하기 위해 path 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # "user" 또는 "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    agent_type: str = "Chatbot"
    config: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    show_gear_options: bool = False

@router.get("/health")
async def health_check():
    """API 상태 확인"""
    return {"status": "healthy", "service": "chat"}

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    단일 채팅 메시지 처리 (WebSocket 대신 REST API 사용 시)
    주로 테스트나 간단한 요청에 사용
    """
    try:
        from services.agent_service import AgentService

        agent_service = AgentService()

        # 설정 업데이트
        if request.config:
            agent_service.agents[request.agent_type].update_config(request.config)

        # 응답 수집
        response_parts = []

        def collect_response(chunk: str):
            response_parts.append(chunk)

        # 에이전트 처리
        await agent_service.process_with_callback(
            request.agent_type,
            request.message,
            collect_response
        )

        # 최종 응답 조합
        full_response = "".join(response_parts)

        # 기어 선택 옵션 플래그 확인
        show_gear_options = False
        if "[SHOW_GEAR_OPTIONS]" in full_response:
            show_gear_options = True
            full_response = full_response.replace("[SHOW_GEAR_OPTIONS]", "")

        return ChatResponse(
            response=full_response,
            show_gear_options=show_gear_options
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))