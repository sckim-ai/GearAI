from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import asyncio
import json
import sys
import os
from typing import Dict, List

# 상위 디렉토리의 services와 agents 모듈을 import하기 위해 path 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agent_service import AgentService
from api.chat import router as chat_router
from api.agents import router as agents_router
from api.config import router as config_router

app = FastAPI(title="Gear AI Backend", version="1.0.0")

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 에이전트 서비스
agent_service = AgentService()

# 활성 웹소켓 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_sessions: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if client_id not in self.client_sessions:
            self.client_sessions[client_id] = {
                "messages": [],
                "agent_settings": {},
                "current_agent": "Chatbot"
            }

    def disconnect(self, websocket: WebSocket, client_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # 세션 데이터는 유지 (재연결 시 복원)

    async def send_message(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message, ensure_ascii=False))

manager = ConnectionManager()

# API 라우터 등록
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
app.include_router(config_router, prefix="/api/config", tags=["config"])

@app.get("/")
async def read_root():
    return {"message": "Gear AI Backend API", "version": "1.0.0"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_type = message_data.get("type")

            if message_type == "chat_message":
                await handle_chat_message(websocket, client_id, message_data)
            elif message_type == "agent_change":
                await handle_agent_change(websocket, client_id, message_data)
            elif message_type == "config_update":
                await handle_config_update(websocket, client_id, message_data)
            elif message_type == "get_session":
                await handle_get_session(websocket, client_id)
            elif message_type == "clear_messages":
                await handle_clear_messages(websocket, client_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.send_message(websocket, {
            "type": "error",
            "message": str(e)
        })

async def handle_chat_message(websocket: WebSocket, client_id: str, message_data: dict):
    """채팅 메시지 처리"""
    user_message = message_data.get("message", "")
    agent_type = message_data.get("agent_type", "Chatbot")

    # 세션에 사용자 메시지 추가
    session = manager.client_sessions[client_id]
    session["messages"].append({"role": "user", "content": user_message})
    session["current_agent"] = agent_type

    # 사용자 메시지 확인 응답
    await manager.send_message(websocket, {
        "type": "user_message_received",
        "message": user_message
    })

    try:
        # 응답 스트리밍을 위한 콜백 함수
        async def stream_callback(chunk: str):
            await manager.send_message(websocket, {
                "type": "assistant_chunk",
                "chunk": chunk
            })

        # 에이전트 응답 처리
        response_parts = []

        def collect_response(chunk: str):
            response_parts.append(chunk)
            # WebSocket에서는 동기 콜백이므로 asyncio.create_task 사용
            asyncio.create_task(stream_callback(chunk))

        # 에이전트 처리
        await agent_service.process_with_callback(
            agent_type,
            user_message,
            collect_response
        )

        # 최종 응답 조합
        full_response = "".join(response_parts)

        # 기어 선택 옵션 플래그 확인
        show_gear_options = False
        if "[SHOW_GEAR_OPTIONS]" in full_response:
            show_gear_options = True
            full_response = full_response.replace("[SHOW_GEAR_OPTIONS]", "")

        # 세션에 어시스턴트 응답 추가
        session["messages"].append({"role": "assistant", "content": full_response})

        # 응답 완료 알림
        await manager.send_message(websocket, {
            "type": "assistant_response_complete",
            "response": full_response,
            "show_gear_options": show_gear_options
        })

    except Exception as e:
        error_message = f"오류가 발생했습니다: {str(e)}"
        session["messages"].append({"role": "assistant", "content": error_message})

        await manager.send_message(websocket, {
            "type": "error",
            "message": error_message
        })

async def handle_agent_change(websocket: WebSocket, client_id: str, message_data: dict):
    """에이전트 변경 처리"""
    new_agent = message_data.get("agent_type")
    session = manager.client_sessions[client_id]

    if session["current_agent"] != new_agent:
        # 에이전트 변경 시 메시지 초기화
        session["messages"] = []
        session["current_agent"] = new_agent

        # 이전 에이전트의 메시지 히스토리 초기화
        if session["current_agent"] in agent_service.agents:
            agent_service.agents[session["current_agent"]].clear_messages()

    await manager.send_message(websocket, {
        "type": "agent_changed",
        "agent_type": new_agent,
        "messages": session["messages"]
    })

async def handle_config_update(websocket: WebSocket, client_id: str, message_data: dict):
    """설정 업데이트 처리"""
    agent_type = message_data.get("agent_type")
    config = message_data.get("config")

    session = manager.client_sessions[client_id]

    if agent_type not in session["agent_settings"]:
        session["agent_settings"][agent_type] = {}

    session["agent_settings"][agent_type].update(config)

    # 에이전트 설정 업데이트
    if agent_type in agent_service.agents:
        agent_service.agents[agent_type].update_config(session["agent_settings"][agent_type])

    await manager.send_message(websocket, {
        "type": "config_updated",
        "agent_type": agent_type,
        "config": session["agent_settings"][agent_type]
    })

async def handle_get_session(websocket: WebSocket, client_id: str):
    """세션 데이터 조회"""
    session = manager.client_sessions[client_id]

    await manager.send_message(websocket, {
        "type": "session_data",
        "messages": session["messages"],
        "agent_settings": session["agent_settings"],
        "current_agent": session["current_agent"]
    })

async def handle_clear_messages(websocket: WebSocket, client_id: str):
    """메시지 초기화"""
    session = manager.client_sessions[client_id]
    session["messages"] = []

    # 현재 에이전트의 메시지 히스토리도 초기화
    current_agent = session["current_agent"]
    if current_agent in agent_service.agents:
        agent_service.agents[current_agent].clear_messages()

    await manager.send_message(websocket, {
        "type": "messages_cleared"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)