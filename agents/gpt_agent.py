from typing import Dict, Any, AsyncGenerator, Callable
import sys
import os
import asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from .base_agent import BaseAgent
from utils.llm import llm_call, llm_call_stream
from openai import AsyncOpenAI
import os
import streamlit as st
import time

# OpenAI 클라이언트 초기화
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class GPTAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.7)
        
    def update_config(self, new_config: Dict[str, Any]):
        """설정을 업데이트하고 내부 변수를 갱신합니다."""
        super().update_config(new_config)
        self.model = self.config.get("model", "gpt-4o-mini")
        self.temperature = self.config.get("temperature", 0.7)
    
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """콜백 방식으로 처리합니다. 청크가 도착할 때마다 콜백 함수를 호출합니다."""
        try:
            # 사용자 메시지 추가
            self.add_message("user", input_text)
            
            full_response = ""
            
            # 직접 OpenAI API 호출
            response = await client.chat.completions.create(
                model=self.model,
                messages=self.get_messages(),
                temperature=self.temperature,
                stream=True
            )
            
            # 스트림 응답 처리
            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    if chunk.choices[0].delta and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        if content:
                            full_response += content
                            # 콜백으로 청크 전달
                            callback(content)
            
            # 최종 응답을 메시지에 추가
            self.add_message("assistant", full_response)
            return full_response
        
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            callback(error_msg)
            self.add_message("assistant", error_msg)
            return error_msg
      