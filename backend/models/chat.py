from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: Optional[str] = None

class ChatSession(BaseModel):
    session_id: str
    messages: List[ChatMessage] = []
    current_agent: str = "Chatbot"
    agent_settings: dict = {}

class WebSocketMessage(BaseModel):
    type: str
    data: dict

class ChatStreamChunk(BaseModel):
    chunk: str
    is_complete: bool = False

class GearOption(BaseModel):
    key: str
    title: str
    description: str

class GearOptionsResponse(BaseModel):
    show_options: bool
    options: List[GearOption] = []