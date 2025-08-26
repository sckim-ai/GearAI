from typing import Dict, Any, AsyncGenerator, Callable
import sys
import os
import asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from .base_agent import BaseAgent
import streamlit as st
import time
from langsmith import traceable
from dotenv import load_dotenv

load_dotenv()


# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult

# 스트리밍 콜백 핸들러
class StreamingCallbackHandler(AsyncCallbackHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """새로운 토큰이 생성될 때마다 콜백 함수 호출"""
        self.callback(token)

class GPTAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "gpt-4o-mini")
        self.temperature = config.get("temperature", 0.7)
        self.provider = config.get("provider", "openai")
        self.llm = self._initialize_llm()
        
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
                    streaming=True
                )
            elif self.provider == "google":
                return ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    google_api_key=os.getenv("GEMINI_API_KEY"),
                    streaming=True
                )
            else:
                # 기본값은 OpenAI
                return ChatOpenAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    api_key=os.getenv("OPENAI_API_KEY"),
                    streaming=False
                )
        except Exception as e:
            print(f"LLM 초기화 오류: {e}")
            # 오류 시 기본 OpenAI 모델로 fallback
            return ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=os.getenv("OPENAI_API_KEY"),
                streaming=False
            )
        
    def update_config(self, new_config: Dict[str, Any]):
        """설정을 업데이트하고 내부 변수를 갱신합니다."""
        super().update_config(new_config)
        old_provider = self.provider
        old_model = self.model_name
        
        self.model_name = self.config.get("model", "gpt-4o-mini")
        self.temperature = self.config.get("temperature", 0.7)
        self.provider = self.config.get("provider", "openai")
        
        # 모델이나 프로바이더가 변경된 경우 LLM 재초기화
        if old_provider != self.provider or old_model != self.model_name:
            self.llm = self._initialize_llm()
    
    def _convert_messages_to_langchain(self):
        """BaseAgent의 메시지를 LangChain 메시지 형식으로 변환"""
        langchain_messages = []
        for msg in self.get_messages():
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        return langchain_messages
    
    @traceable
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """콜백 방식으로 처리합니다. 청크가 도착할 때마다 콜백 함수를 호출합니다."""
        try:
            # 사용자 메시지 추가
            self.add_message("user", input_text)
            
            # LangChain 메시지 형식으로 변환
            messages = self._convert_messages_to_langchain()
            
            full_response = ""
            
            # 프로바이더에 따른 응답 처리
            if self.provider == "openai":
                # OpenAI는 스트리밍 비활성화로 인해 일반 응답 사용
                response = await self.llm.ainvoke(messages)
                full_response = response.content if hasattr(response, 'content') else str(response)
                callback(full_response)
            else:
                # 다른 프로바이더는 스트리밍 유지
                async for chunk in self.llm.astream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        full_response += chunk.content
                        # 콜백 함수를 직접 호출
                        callback(chunk.content)
            
            # 최종 응답을 메시지에 추가
            self.add_message("assistant", full_response)
            return full_response
        
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            callback(error_msg)
            self.add_message("assistant", error_msg)
            return error_msg
      