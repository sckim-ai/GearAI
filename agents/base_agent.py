from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
import asyncio

class BaseAgent(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.messages: List[Dict[str, str]] = []

    @abstractmethod
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """에이전트의 주요 처리 로직. 입력을 받아 콜백으로 스트리밍 응답을 전달한다."""
        pass
    
    def add_message(self, role: str, content: str):
        """대화 기록에 메시지를 추가합니다."""
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """현재까지의 대화 기록을 반환합니다."""
        return self.messages
    
    def clear_messages(self):
        """대화 기록을 초기화합니다."""
        self.messages = []
    
    def update_config(self, new_config: Dict[str, Any]):
        """에이전트 설정을 업데이트합니다."""
        self.config.update(new_config)
    
    async def stream_response(self, response: Any) -> str:
        """스트리밍 응답을 처리합니다."""
        full_response = ""
        async for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        full_response += content
        return full_response 