from SmartJsonSearch import JSONPathSearcher

# JSON 파일 로드
searcher = JSONPathSearcher(json_file=r"C:\SW\GearAI\TestGD.GD1")

# "module"과 관련된 모든 키 찾기
results = searcher.search("module")

for result in results:
    print(f"경로: {result['path']}")
    print(f"값: {result['value']}")
    if 'description' in result:
        print(f"설명: {result['description']}")
    print(f"유사도: {result['score']:.1f}%")
    print("-" * 40)