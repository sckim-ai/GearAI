from typing import List, Dict
from .llm import llm_call

def remove_code_block_from_llm_response(llm_response: str) -> str:
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

def prompt_chain_workflow(messages: List[Dict[str, str]]) -> List[str]:
    """프롬프트 체이닝 워크플로우를 실행합니다."""
    response_chain = []
    user_input = messages[-1]["content"]
    
    # 프롬프트 체인 정의
    prompt_chain = [
        """사용자의 요청사항을 수행하기 위한 3가지 방법을 추천하세요. 
        - 먼저 사용자가 입력한 요청사항을 요약해줘
        - 사용자가 입력한 요청사항을 반영해서 왜 적합한 방법인지 설명해주세요
        - 각 방법의 특징, 장단점 등을 설명하세요.
        """,
        
        """주어진 추천 방법 중 3가지 중 하나를 선택하세요. 선택한 방법을 알려주세요. 
        그리고 선택한 이유를 설명해주세요.
        - 해당 방법을 수행하기 위한 주요 활동 5가지를 나열하세요.
        """
    ]
    
    # 각 프롬프트에 대해 LLM 호출
    for prompt in prompt_chain:
        final_prompt = f"Prompt: {prompt}\nUser:\n{user_input}"
        input_prompt = [{"role": "user", "content": final_prompt}]
        
        # 동기로 응답 처리
        response = llm_call(input_prompt)
        response_chain.append(response)
        user_input = response
        
    return response_chain 