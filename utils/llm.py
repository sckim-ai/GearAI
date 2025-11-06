from openai import AsyncOpenAI, OpenAI
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator
from pydantic import BaseModel

import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

# API 키 로드
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# OpenAI 클라이언트
openai_async_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
openai_sync_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Anthropic 클라이언트 (lazy import)
anthropic_async_client = None
anthropic_sync_client = None

# Google 클라이언트 (lazy import)
google_client = None

def _get_anthropic_clients():
    """Anthropic 클라이언트 초기화 (필요시)"""
    global anthropic_async_client, anthropic_sync_client

    if anthropic_async_client is None and ANTHROPIC_API_KEY:
        try:
            from anthropic import AsyncAnthropic, Anthropic
            anthropic_async_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            anthropic_sync_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        except ImportError:
            raise ImportError("Anthropic 패키지가 설치되지 않았습니다. 'pip install anthropic' 실행 필요")

    return anthropic_async_client, anthropic_sync_client

def _get_google_client():
    """Google Generative AI 클라이언트 초기화 (필요시)"""
    global google_client

    if google_client is None and GOOGLE_API_KEY:
        try:
            from google import genai
            genai.configure(api_key=GOOGLE_API_KEY)
            google_client = genai
        except ImportError:
            raise ImportError("Google Generative AI 패키지가 설치되지 않았습니다. 'pip install google-generativeai' 실행 필요")

    return google_client

def _detect_provider(model: str) -> str:
    """모델명으로 프로바이더 자동 감지"""
    model_lower = model.lower()

    if model_lower.startswith("gpt-") or model_lower.startswith("o1"):
        return "openai"
    elif model_lower.startswith("claude"):
        return "anthropic"
    elif model_lower.startswith("gemini"):
        return "google"
    else:
        # 기본값은 OpenAI
        return "openai"

def _convert_messages_to_anthropic(messages: List[Dict[str, str]]) -> tuple[Optional[str], List[Dict[str, str]]]:
    """OpenAI 형식 메시지를 Anthropic 형식으로 변환"""
    system_prompt = None
    claude_messages = []

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            # Anthropic은 system을 별도 파라미터로 받음
            system_prompt = content
        elif role in ["user", "assistant"]:
            claude_messages.append({"role": role, "content": content})

    return system_prompt, claude_messages

def _convert_messages_to_google(messages: List[Dict[str, str]]) -> str:
    """OpenAI 형식 메시지를 Google Gemini 형식으로 변환"""
    # Google은 단순 텍스트 프롬프트 또는 Chat 형식 사용
    # 여기서는 간단히 모든 메시지를 합쳐서 전달
    combined_prompt = ""

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            combined_prompt += f"System: {content}\n\n"
        elif role == "user":
            combined_prompt += f"User: {content}\n\n"
        elif role == "assistant":
            combined_prompt += f"Assistant: {content}\n\n"

    return combined_prompt.strip()

async def llm_call_async(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    stream: bool = False
) -> AsyncGenerator[Any, None]:
    """비동기 LLM 호출 (OpenAI, Anthropic, Google 지원)"""
    provider = _detect_provider(model)

    try:
        if provider == "openai":
            if not openai_async_client:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

            response = await openai_async_client.chat.completions.create(
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

        elif provider == "anthropic":
            async_client, _ = _get_anthropic_clients()
            if not async_client:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

            system_prompt, claude_messages = _convert_messages_to_anthropic(prompt)

            response = await async_client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=claude_messages,
                stream=stream
            )

            if stream:
                async for chunk in response:
                    yield chunk
            else:
                yield response

        elif provider == "google":
            google = _get_google_client()
            if not google:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")

            gemini_prompt = _convert_messages_to_google(prompt)
            gemini_model = google.GenerativeModel(model)

            if stream:
                response = gemini_model.generate_content(
                    gemini_prompt,
                    generation_config={"temperature": temperature},
                    stream=True
                )
                for chunk in response:
                    yield chunk
            else:
                response = gemini_model.generate_content(
                    gemini_prompt,
                    generation_config={"temperature": temperature}
                )
                yield response

    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생 ({provider}): {str(e)}")

def llm_call(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.1
) -> str:
    """동기 LLM 호출 (OpenAI, Anthropic, Google 지원)"""
    provider = _detect_provider(model)

    try:
        if provider == "openai":
            if not openai_sync_client:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

            response = openai_sync_client.chat.completions.create(
                model=model,
                messages=prompt,
                temperature=temperature
            )
            return response.choices[0].message.content

        elif provider == "anthropic":
            _, sync_client = _get_anthropic_clients()
            if not sync_client:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

            system_prompt, claude_messages = _convert_messages_to_anthropic(prompt)

            response = sync_client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=claude_messages
            )

            # Anthropic 응답에서 텍스트 추출
            return response.content[0].text

        elif provider == "google":
            google = _get_google_client()
            if not google:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")

            gemini_prompt = _convert_messages_to_google(prompt)
            gemini_model = google.GenerativeModel(model)

            response = gemini_model.generate_content(
                gemini_prompt,
                generation_config={"temperature": temperature}
            )

            return response.text

    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생 ({provider}): {str(e)}")

def llm_call_stream(
    prompt: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Generator[str, None, None]:
    """동기적으로 스트리밍 응답을 처리하는 LLM 호출 (OpenAI, Anthropic, Google 지원)"""
    provider = _detect_provider(model)

    try:
        if provider == "openai":
            if not openai_sync_client:
                raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

            response = openai_sync_client.chat.completions.create(
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

        elif provider == "anthropic":
            _, sync_client = _get_anthropic_clients()
            if not sync_client:
                raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

            system_prompt, claude_messages = _convert_messages_to_anthropic(prompt)

            with sync_client.messages.stream(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=claude_messages
            ) as stream:
                for text in stream.text_stream:
                    yield text

        elif provider == "google":
            google = _get_google_client()
            if not google:
                raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다")

            gemini_prompt = _convert_messages_to_google(prompt)
            gemini_model = google.GenerativeModel(model)

            response = gemini_model.generate_content(
                gemini_prompt,
                generation_config={"temperature": temperature},
                stream=True
            )

            for chunk in response:
                if hasattr(chunk, 'text'):
                    yield chunk.text

    except Exception as e:
        raise Exception(f"LLM 호출 중 오류 발생 ({provider}): {str(e)}")

def JSON_llm(
    user_prompt: str,
    schema: BaseModel,
    client=None,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None
):
    """
    JSON 모드에서 언어 모델 호출을 실행하고 구조화된 JSON 객체를 반환합니다.

    Note: 현재는 OpenAI의 structured output만 지원합니다.
    Anthropic과 Google은 향후 추가 예정입니다.
    """
    if model is None:
        model = "gpt-4o-mini"

    provider = _detect_provider(model)

    if provider != "openai":
        raise NotImplementedError(f"{provider} 프로바이더는 아직 JSON 스키마 출력을 지원하지 않습니다. OpenAI 모델을 사용하세요.")

    try:
        # client가 제공되지 않으면 기본 클라이언트 사용
        if client is None:
            client = openai_sync_client

        if not client:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다")

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


# 사용 예시 및 도움말
def get_supported_models() -> Dict[str, List[str]]:
    """지원하는 모델 목록 반환"""
    return {
        "openai": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "o1-preview",
            "o1-mini"
        ],
        "anthropic": [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        "google": [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
    }
