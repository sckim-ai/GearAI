import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm import llm_call


default_json_path = os.path.join(os.path.dirname(__file__), "data", "schema", "Default.json")

with open(default_json_path, "r", encoding="utf-8") as f:
    gear_data = json.load(f)

# 2. LLM 프롬프트 구성
system_prompt = (
    "너는 기어 설계 데이터의 JSON을 수정하는 AI야.\n"
    "아래의 사용자 요청에 따라 전달받은 JSON 데이터의 값을 적절히 변경해야 해.\n"
    "전달받은 JSON 데이터의 메타데이터는 Key 값 앞에 $가 붙어있으니 참고해.\n"
    "반환 시 변경해야할 정확한 JSON KEY 값과 Value만 반환해.\n"    
    "반환하는 데이터 형태는 반드시 JSON의 표준 중첩구조를 따라야 해."
)
prompt = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"사용자 요청: 모듈 3으로 바꿔줘. 잇수도 기어비 2:1에 맞게 바꿔줘\n현재 데이터: {json.dumps(gear_data, ensure_ascii=False)}"}
]
# prompt = [
#     {"role": "system", "content": system_prompt},
#     {"role": "user", "content": f"사용자 요청: 모듈 3으로 바꿔줘"}
# ]

response = llm_call(prompt=prompt, model="gpt-4o")

print(response)
