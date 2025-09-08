"""
ChatAgent 비스트리밍 기능 테스트
"""
import asyncio
import sys
import os

# 프로젝트 루트를 패스에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agents.chat_agent import ChatAgent

async def test_streaming():
    """스트리밍 응답 테스트"""
    print("=== 스트리밍 응답 테스트 ===")
    
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "provider": "openai"
    }
    
    agent = ChatAgent(config)
    
    def callback(chunk):
        print(chunk, end="", flush=True)
    
    print("질문: 파이썬에 대해 간단히 설명해줘")
    print("답변: ", end="")
    
    response = await agent.process_with_callback("파이썬에 대해 간단히 설명해줘", callback)
    print("\n")
    print(f"전체 응답 길이: {len(response)}")
    print("=" * 50)

async def test_non_streaming():
    """비스트리밍 응답 테스트"""
    print("\n=== 비스트리밍 응답 테스트 ===")
    
    config = {
        "model": "gpt-4o-mini", 
        "temperature": 0.7,
        "provider": "openai"
    }
    
    agent = ChatAgent(config)
    
    print("질문: 자바스크립트와 파이썬의 차이점은?")
    print("처리 중...")
    
    # 비동기 방식
    response = await agent.process("자바스크립트와 파이썬의 차이점은?")
    print(f"답변: {response}")
    print(f"전체 응답 길이: {len(response)}")
    print("=" * 50)

def test_sync_response():
    """완전 동기식 응답 테스트"""
    print("\n=== 동기식 응답 테스트 ===")
    
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.7, 
        "provider": "openai"
    }
    
    agent = ChatAgent(config)
    
    print("질문: 머신러닝이란 무엇인가요?")
    print("처리 중...")
    
    # 완전 동기식 방식 
    response = agent.get_response("머신러닝이란 무엇인가요?")
    print(f"답변: {response}")
    print(f"전체 응답 길이: {len(response)}")
    print("=" * 50)

async def main():
    """메인 테스트 함수"""
    await test_streaming()
    await test_non_streaming()
    test_sync_response()

if __name__ == "__main__":
    asyncio.run(main())