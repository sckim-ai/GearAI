"""
Gear Agent 그래프 시각화 테스트
"""
import sys
import os
# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.gear_agent import GearAgent

def test_graph_visualization():
    """그래프 시각화 테스트"""
    print("Gear Agent 그래프 시각화 테스트 시작...")
    
    config = {
        "model": "gpt-4o-mini",
        "temperature": 0.0
    }
    
    agent = GearAgent(config)
    
    try:
        # 그래프 이미지 생성
        graph_image = agent.get_graph_image()
        
        if graph_image:
            print(f"[성공] 그래프 이미지 생성 완료")
            print(f"[정보] 이미지 크기: {graph_image.size}")
            print(f"[정보] 이미지 모드: {graph_image.mode}")
            
            # 그래프 구조 정보도 출력
            graph = agent.workflow.get_graph()
            print(f"[정보] 노드 개수: {len(graph.nodes)}")
            print(f"[정보] 노드 목록: {list(graph.nodes.keys())}")
            print(f"[정보] 엣지 개수: {len(graph.edges)}")
            
            return True
        else:
            print("[실패] 그래프 이미지 생성 실패")
            return False
            
    except Exception as e:
        print(f"[오류] 그래프 시각화 테스트 중 오류: {e}")
        return False

if __name__ == "__main__":
    success = test_graph_visualization()
    if success:
        print("\n✅ 그래프 시각화 구현 성공!")
    else:
        print("\n❌ 그래프 시각화 구현 실패!")