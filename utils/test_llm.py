"""
LLM 유틸리티 함수 테스트 코드

사용법:
    python utils/test_llm.py
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.llm import (
    llm_call,
    llm_call_stream,
    llm_call_async,
    _detect_provider,
    get_supported_models
)
import asyncio


def test_detect_provider():
    """프로바이더 자동 감지 테스트"""
    print("\n=== 프로바이더 자동 감지 테스트 ===")

    test_cases = [
        ("gpt-5", "openai"),
        ("gpt-5-mini", "openai"),
        ("gpt-5-nano", "openai"),
        ("claude-sonnet-4-5-20250929", "anthropic"),
        ("claude-haiku-4-5-20251001", "anthropic"),
        ("gemini-2.5-flash", "google"),
    ]

    for model, expected_provider in test_cases:
        detected = _detect_provider(model)
        status = "✅" if detected == expected_provider else "❌"
        print(f"{status} {model:30s} → {detected:10s} (예상: {expected_provider})")


def test_supported_models():
    """지원 모델 목록 확인 테스트"""
    print("\n=== 지원 모델 목록 ===")

    models = get_supported_models()

    for provider, model_list in models.items():
        print(f"\n{provider.upper()}:")
        for model in model_list:
            print(f"  - {model}")


def test_llm_call_openai():
    """OpenAI 동기 호출 테스트"""
    print("\n=== OpenAI 동기 호출 테스트 ===")

    try:
        response = llm_call(
            prompt=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from OpenAI!' and nothing else."}
            ],
            model="gpt-4o-mini",
            temperature=0.1
        )
        print(f"✅ 응답: {response}")
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_llm_call_anthropic():
    """Anthropic 동기 호출 테스트"""
    print("\n=== Anthropic 동기 호출 테스트 ===")

    try:
        response = llm_call(
            prompt=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from Claude!' and nothing else."}
            ],
            model="claude-haiku-4-5-20251001",
            temperature=0.1
        )
        print(f"✅ 응답: {response}")
        return True
    except ValueError as e:
        print(f"⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_llm_call_google():
    """Google 동기 호출 테스트"""
    print("\n=== Google 동기 호출 테스트 ===")

    try:
        response = llm_call(
            prompt=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from Gemini!' and nothing else."}
            ],
            model="gemini-2.5-flash",
            temperature=0.1
        )
        print(f"✅ 응답: {response}")
        return True
    except ValueError as e:
        print(f"⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_llm_call_stream_openai():
    """OpenAI 스트리밍 호출 테스트"""
    print("\n=== OpenAI 스트리밍 호출 테스트 ===")

    try:
        print("응답: ", end="")
        for chunk in llm_call_stream(
            prompt=[
                {"role": "user", "content": "Count from 1 to 5 slowly."}
            ],
            model="gpt-4o-mini",
            temperature=0.7
        ):
            print(chunk, end="", flush=True)
        print("\n✅ 스트리밍 완료")
        return True
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


def test_llm_call_stream_anthropic():
    """Anthropic 스트리밍 호출 테스트"""
    print("\n=== Anthropic 스트리밍 호출 테스트 ===")

    try:
        print("응답: ", end="")
        for chunk in llm_call_stream(
            prompt=[
                {"role": "user", "content": "Count from 1 to 3."}
            ],
            model="claude-haiku-4-5-20251001",
            temperature=0.7
        ):
            print(chunk, end="", flush=True)
        print("\n✅ 스트리밍 완료")
        return True
    except ValueError as e:
        print(f"\n⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"\n⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


def test_llm_call_stream_google():
    """Google 스트리밍 호출 테스트"""
    print("\n=== Google 스트리밍 호출 테스트 ===")

    try:
        print("응답: ", end="")
        for chunk in llm_call_stream(
            prompt=[
                {"role": "user", "content": "Say hello."}
            ],
            model="gemini-2.5-flash",
            temperature=0.7
        ):
            print(chunk, end="", flush=True)
        print("\n✅ 스트리밍 완료")
        return True
    except ValueError as e:
        print(f"\n⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"\n⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False


async def test_llm_call_async_openai():
    """OpenAI 비동기 호출 테스트"""
    print("\n=== OpenAI 비동기 호출 테스트 ===")

    try:
        async for response in llm_call_async(
            prompt=[
                {"role": "user", "content": "Say 'Async OpenAI works!' and nothing else."}
            ],
            model="gpt-4o-mini",
            temperature=0.1,
            stream=False
        ):
            # 응답 객체에서 텍스트 추출
            if hasattr(response, 'choices'):
                text = response.choices[0].message.content
                print(f"✅ 응답: {text}")
        return True
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


async def test_llm_call_async_anthropic():
    """Anthropic 비동기 호출 테스트"""
    print("\n=== Anthropic 비동기 호출 테스트 ===")

    try:
        async for response in llm_call_async(
            prompt=[
                {"role": "user", "content": "Say 'Async Claude works!' and nothing else."}
            ],
            model="claude-haiku-4-5-20251001",
            temperature=0.1,
            stream=False
        ):
            # 응답 객체에서 텍스트 추출
            if hasattr(response, 'content'):
                text = response.content[0].text
                print(f"✅ 응답: {text}")
        return True
    except ValueError as e:
        print(f"⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


async def test_llm_call_async_google():
    """Google 비동기 호출 테스트"""
    print("\n=== Google 비동기 호출 테스트 ===")

    try:
        async for response in llm_call_async(
            prompt=[
                {"role": "user", "content": "Say 'Async Gemini works!' and nothing else."}
            ],
            model="gemini-2.5-flash",
            temperature=0.1,
            stream=False
        ):
            # 응답 객체에서 텍스트 추출
            if hasattr(response, 'text'):
                text = response.text
                print(f"✅ 응답: {text}")
        return True
    except ValueError as e:
        print(f"⚠️  API 키 없음: {e}")
        return None
    except ImportError as e:
        print(f"⚠️  패키지 미설치: {e}")
        return None
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


async def run_async_tests():
    """비동기 테스트 실행"""
    await test_llm_call_async_openai()
    await test_llm_call_async_anthropic()
    await test_llm_call_async_google()


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("LLM 유틸리티 통합 테스트 시작")
    print("=" * 60)

    # 기본 테스트
    test_detect_provider()
    test_supported_models()

    # 동기 호출 테스트
    print("\n" + "=" * 60)
    print("동기 호출 테스트")
    print("=" * 60)
    test_llm_call_openai()
    test_llm_call_anthropic()
    test_llm_call_google()

    # 스트리밍 테스트
    print("\n" + "=" * 60)
    print("스트리밍 호출 테스트")
    print("=" * 60)
    test_llm_call_stream_openai()
    test_llm_call_stream_anthropic()
    test_llm_call_stream_google()

    # 비동기 테스트
    print("\n" + "=" * 60)
    print("비동기 호출 테스트")
    print("=" * 60)
    asyncio.run(run_async_tests())

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


def run_quick_test():
    """빠른 테스트 (OpenAI만)"""
    print("=" * 60)
    print("빠른 테스트 (OpenAI만)")
    print("=" * 60)

    test_detect_provider()
    test_llm_call_openai()
    test_llm_call_stream_openai()

    async def quick_async():
        await test_llm_call_async_openai()

    asyncio.run(quick_async())

    print("\n빠른 테스트 완료")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM 유틸리티 테스트")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="빠른 테스트 (OpenAI만)"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google", "all"],
        default="all",
        help="테스트할 프로바이더 선택"
    )

    args = parser.parse_args()

    if args.quick:
        run_quick_test()
    elif args.provider == "all":
        run_all_tests()
    elif args.provider == "openai":
        test_detect_provider()
        test_llm_call_openai()
        test_llm_call_stream_openai()
        asyncio.run(test_llm_call_async_openai())
    elif args.provider == "anthropic":
        test_detect_provider()
        test_llm_call_anthropic()
        test_llm_call_stream_anthropic()
        asyncio.run(test_llm_call_async_anthropic())
    elif args.provider == "google":
        test_detect_provider()
        test_llm_call_google()
        test_llm_call_stream_google()
        asyncio.run(test_llm_call_async_google())
