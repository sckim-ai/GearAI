from openai import AsyncOpenAI, OpenAI
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator
from pydantic import BaseModel

import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
sync_client = OpenAI(api_key=OPENAI_API_KEY)

async def llm_call_async(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    stream: bool = False
) -> AsyncGenerator[Any, None]:
    """비동기 LLM 호출"""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=prompt,
            temperature=temperature,
            stream=stream
        )
        
        if stream:
            async for chunk in response:
                yield chunk
        else:
            yield response
    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생: {str(e)}")

def llm_call(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> str:
    """동기 LLM 호출"""
    try:
        response = sync_client.chat.completions.create(
            model=model,
            messages=prompt,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생: {str(e)}")

def llm_call(
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> str:
    """동기 LLM 호출"""
    try:
        response = sync_client.chat.completions.create(
            model=model,
            messages=prompt,
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생: {str(e)}")

def llm_call_stream(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Generator[str, None, None]:
    """동기적으로 스트리밍 응답을 처리하는 LLM 호출"""
    try:
        response = sync_client.chat.completions.create(
            model=model,
            messages=prompt,
            temperature=temperature,
            stream=True
        )
        
        for chunk in response:
            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생: {str(e)}") 
    
def JSON_llm(user_prompt: str, schema: BaseModel, client, system_prompt: Optional[str] = None, model: Optional[str] = None):
    """
    JSON 모드에서 언어 모델 호출을 실행하고 구조화된 JSON 객체를 반환합니다.
    모델이 제공되지 않으면 기본 JSON 처리 가능한 모델이 사용됩니다.
    """
    if model is None:
        model = "gpt-4o-mini"
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=schema,
        )
        
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error in JSON_llm: {e}")
        return None
    

def remove_code_block_llm(llm_response: str) -> str:
    """
    LLM 응답에서 코드블럭(```json ... ```)을 제거하여 순수 JSON 문자열만 반환합니다.
    Args:
        llm_response (str): LLM의 원본 응답 문자열
    Returns:
        str: 코드블럭이 제거된 JSON 문자열
    """
    import re
    cleaned = llm_response.strip()
    # 정규표현식으로 코드블럭 제거
    cleaned = re.sub(r"^```[a-zA-Z]*\n|```$", "", cleaned, flags=re.MULTILINE)
    return cleaned
