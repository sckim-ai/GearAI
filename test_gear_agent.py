"""
Gear Agent 테스트 스크립트
langgraph + MCP tool 기반 재편성된 gear_agent.py를 테스트
"""
import asyncio
import sys
import os
# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.gear_agent import GearAgent

async def test_gear_agent():
    """Gear Agent 기본 테스트"""
    print("Gear Agent 테스트 시작...")
    
    # 1. Agent 초기화
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "gear_design_path": r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows",
        "template_json_path": "TestGD.GD1"
    }
    
    agent = GearAgent(config)
    
    def callback(message):
        print(f"[콜백] {message}")
    
    # 2. 기어 관련 질문 테스트 (직접 응답)
    print("\n--- 테스트 1: 기어 관련 일반 질문 ---")
    simple_question = "기어란 무엇인가요?"
    
    try:
        result = await agent.process_with_callback(simple_question, callback)
        print(f"[결과] {result[:500]}...")
        print(f"[전체길이] {len(result)}자")
    except Exception as e:
        print(f"[오류] {e}")
    
    # 3. 기어 계산 요청 테스트 (MCP tool 사용)
    print("\n--- 테스트 2: 기어 설계 계산 요청 ---")
    design_request = "모듈 3, 잇수 20인 스퍼 기어의 강도를 계산해주세요"
    
    try:
        result = await agent.process_with_callback(design_request, callback)
        print(f"[결과] {result[:500]}...")
        print(f"[전체길이] {len(result)}자")
    except Exception as e:
        print(f"[오류] {e}")
    
    # 4. 비기어 관련 질문 테스트
    print("\n--- 테스트 3: 비기어 관련 질문 ---")
    non_gear_question = "파이썬 프로그래밍에 대해 알려주세요"
    
    try:
        result = await agent.process_with_callback(non_gear_question, callback)
        print(f"[결과] {result}")
    except Exception as e:
        print(f"[오류] {e}")
    
    print("\nGear Agent 테스트 완료!")

async def test_workflow_structure():
    """워크플로우 구조 테스트"""
    print("\n워크플로우 구조 분석...")
    
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.0
    }
    
    agent = GearAgent(config)
    
    # 워크플로우 그래프 정보 출력
    try:
        graph = agent.workflow.get_graph()
        print(f"[그래프] 노드 개수: {len(graph.nodes)}")
        print(f"[그래프] 노드 목록: {list(graph.nodes.keys())}")
        print(f"[그래프] 엣지 개수: {len(graph.edges)}")
        
        # 각 노드별 연결 정보
        for node in graph.nodes:
            print(f"  - {node}: {graph.nodes[node]}")
            
    except Exception as e:
        print(f"[오류] 그래프 분석 오류: {e}")

if __name__ == "__main__":
    print("Gear Agent 테스트 스크립트 실행")
    
    # 기본 테스트
    asyncio.run(test_gear_agent())
    
    # 워크플로우 구조 테스트
    asyncio.run(test_workflow_structure())