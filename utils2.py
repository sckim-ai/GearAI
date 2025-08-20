from openai import AsyncOpenAI, OpenAI
from typing import List
import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
)
sync_client = OpenAI(
    api_key=OPENAI_API_KEY,
)

def llm_call(promt: list[str], model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    # messages = [promt]
    # messages.append({"role": "user", "content": promt})
    chat_completion = sync_client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=promt,
    )
    return chat_completion.choices[0].message.content

async def llm_call_async(promt: list[str], model: str = "gpt-4o-mini", temperature: float = 0.7) -> str:
    chat_completion = await client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=promt,
    )
    return chat_completion.choices[0].message.content

# 1. Prompt chaining
def prompt_chain_workflow(initial_input: list[str]) -> List[str]:
    response_chain = []
    response = initial_input[-1]["content"]

    # 프롬프트 체인: LLM이 단계적으로 여행을 계획하도록 유도
    prompt_chain = [
        ## 사용자 요청사항에 따라 3가지 방법을 제시하고 그 이유를 설명
    """사용자의 요청사항을 수행하기 위한 3가지 방법을 추천하세요. 
    - 먼저 사용자가 입력한 요청사항을 요약해줘
    - 사용자가 입력한 요청사항을 반영해서 왜 적합한 방법인지 설명해주세요
    - 각 방법의 특징, 장단점 등을 설명하세요.
    """,

        ## 추천 방법 중 1가지를 선택하고 방법을 수행하기 위한 활동 5가지 나열
    """주어진 추천 방법 중 3가지 중 하나를 선택하세요. 선택한 방법을 알려주세요. 그리고 선택한 이유를 설명해주세요.
    - 해당 방법을 수행하기 위한 주요 활동 5가지를 나열하세요. 
    """,
    ]

    for i, prompt in enumerate(prompt_chain, 1):
        final_prompt = f"Prompt: {prompt}\nUser:\n{response}"
        input_promt = [{"role": "user", "content": final_prompt}]
        response = llm_call(input_promt)
        response_chain.append(response)

    return response_chain


# 2. Routing
def run_router_workflow(initial_input : list[str]):
    response_chain = []
    user_prompt = initial_input[-1]["content"]
    router_prompt = f"""
    사용자의 프롬프트/질문: {user_prompt}

    각 모델은 서로 다른 기능을 가지고 있습니다. 사용자의 질문에 가장 적합한 모델을 선택하세요:
    - gpt-4o-mini: 간단한 답변에 적합한 모델 (기본값)
    - gpt-4o: 고민이 필요한 답변에 적합한 모델 

    모델명만 단답형으로 응답하세요
    """

    input_promt = [{"role": "user", "content": router_prompt}]
    selected_model = llm_call(input_promt)
    response_chain.append("Selected model: " + selected_model)

    response = llm_call([initial_input[-1]], model = selected_model)
    response_chain.append(response)

    return response_chain

# 3. Parallelization
async def run_Parallelization(initial_input : list[str]):
    user_prompt = initial_input[-1]["content"]

    parallel_prompt_details = [
        {"user_prompt": user_prompt, "model": "gpt-4o"},
        {"user_prompt": user_prompt, "model": "gpt-4o-mini"},
    ]

    tasks = [llm_call_async(
        promt=[{"role": "user", "content": prompt['user_prompt']}], 
        model=prompt['model']) for prompt in parallel_prompt_details]
    
    responses = []
    
    for task in asyncio.as_completed(tasks):
        result = await task
        responses.append(result)
    
    aggregator_prompt = ("다음은 여러 개의 AI 모델이 사용자 질문에 대해 생성한 응답입니다.\n"
                         "당신의 역할은 이 응답들을 모두 종합하여 최종 답변을 제공하는 것입니다.\n"
                         "일부 응답이 부정확하거나 편향될 수 있으므로, 신뢰성과 정확성을 갖춘 응답을 생성하는 것이 중요합니다.\n\n"
                         "# 사용자 질문:\n"
                         f"{user_prompt}\n\n"
                         "# 모델 응답들:")

    for i in range(len(parallel_prompt_details)):
        responses[i] = f"{i + 1}번 응답: {responses[i]}"
        aggregator_prompt += f"\n{responses[i]}"
    
    sum_promt = [{"role": "user", "content": aggregator_prompt}]
    final_response = await llm_call_async(sum_promt, model="gpt-4o")
    responses.append(f"최종 답변: {final_response}")

    return responses

# 4. Orchestrator
async def run_llm_parallel(prompt_list : list[str]):
    tasks = [llm_call_async(promt=[{"role": "user", "content": prompt}]) for prompt in prompt_list]
    responses = []

    for task in asyncio.as_completed(tasks):
        result = await task
        responses.append(result)
    
    return responses

def get_orchestrator_prompt(user_query):
    return f"""
다음 사용자 질문을 분석하고, 이를 관련된 하위 질문으로 분해하십시오:

다음 형식으로 응답을 제공하십시오:

{{
    "analysis": "사용자 질문에 대한 이해를 상세히 설명하고, 작성한 하위 질문들의 근거를 설명하십시오.",
    "subtasks": [
        {{
            "description": "이 하위 질문의 초점과 의도를 설명하십시오.",
            "sub_question": "질문 1"
        }},
        {{
            "description": "이 하위 질문의 초점과 의도를 설명하십시오.",
            "sub_question": "질문 2"
        }}
        // 필요에 따라 추가 하위 질문 포함
    ]
}}
질문의 수준에 따라 최대 5개의 하위 질문을 생성하세요.

# 사용자 질문: {user_query}
"""

def get_worker_prompt(user_query, sub_question, description):
    return f"""
    다음 사용자 질문에서 파생된 하위 질문을 다루는 작업을 맡았습니다:
    \n원래 질문:  {user_query}
    \n하위 질문: {sub_question}

    지침: {description}

    하위 질문을 철저히 다루는 포괄적이고 상세한 응답을 해주세요
    """

async def orchestrate_task(initial_input : list[str]):
    user_query = initial_input[-1]["content"]    
    # 1단계 : 사용자 질문 기반으로 여러 질문 도출
    orchestrator_prompt = get_orchestrator_prompt(user_query)
    input_promt = [{"role": "user", "content": orchestrator_prompt}]
    orchestrator_response = llm_call(input_promt, model="gpt-4o")
     
    response_json = json.loads(orchestrator_response.replace('```json', '').replace('```', ''))   
    analysis = response_json.get("analysis", "")
    sub_tasks = response_json.get("subtasks", [])

    # 2단계 : 각 하위질문에 대한 LLM 호출
    worker_prompts = [get_worker_prompt(user_query, task["sub_question"], task["description"]) for task in sub_tasks]     
    worker_responses = await run_llm_parallel(worker_prompts)
        
    # 3단계 : 하위질문 응답 종합 및 LLM 호출
    aggregator_prompt = f"""아래는 사용자의 원래 질문에 대해서 하위 질문을 나누고 응답한 결과입니다.
    아래 질문 및 응답내용을 포함한 최종 응답을 제공해주세요.
    ## 요청사항
    - 하위질문 응답내용이 최대한 포괄적이고 상세하게 포함되어야 합니다
    사용자의 원래 질문:
    {user_query}

    하위 질문 및 응답:
    """
    
    for i in range(len(sub_tasks)):
        aggregator_prompt += f"\n{i+1}. 하위 질문: {sub_tasks[i]['sub_question']}\n"
        aggregator_prompt += f"\n   응답: {worker_responses[i]}\n"
        
    final_response = llm_call(promt=[{"role": "user", "content": aggregator_prompt}], model="gpt-4o")
    
    return final_response

# 5. Evaluator optimizer
def loop_workflow(initial_input, evaluator_prompt, max_retries=5) -> str:
    """평가자가 생성된 요약을 통과할 때까지 최대 max_retries번 반복."""
    user_query = initial_input[-1]["content"]    

    retries = 0
    while retries < max_retries:
        print(f"\n========== 📝 요약 프롬프트 (시도 {retries + 1}/{max_retries}) ==========\n")
        print(user_query)
        
        summary = llm_call(user_query, model="gpt-4o-mini")
        print(f"\n========== 📝 요약 결과 (시도 {retries + 1}/{max_retries}) ==========\n")
        print(summary)
        
        final_evaluator_prompt = evaluator_prompt + summary
        evaluation_result = llm_call(final_evaluator_prompt, model="gpt-4o").strip()

        print(f"\n========== 🔍 평가 프롬프트 (시도 {retries + 1}/{max_retries}) ==========\n")
        print(final_evaluator_prompt)

        print(f"\n========== 🔍 평가 결과 (시도 {retries + 1}/{max_retries}) ==========\n")
        print(evaluation_result)

        if "평가결과 = PASS" in evaluation_result:
            print("\n✅ 통과! 최종 요약이 승인되었습니다.\n")
            return summary
        
        retries += 1
        print(f"\n🔄 재시도 필요... ({retries}/{max_retries})\n")

        # If max retries reached, return last attempt
        if retries >= max_retries:
            print("❌ 최대 재시도 횟수 도달. 마지막 요약을 반환합니다.")
            return summary  # Returning the last attempted summary, even if it's not perfect.

        # Updating the user_query for the next attempt with full history
        user_query += f"{retries}차 요약 결과:\n\n{summary}\n"
        user_query += f"{retries}차 요약 피드백:\n\n{evaluation_result}\n\n"


if __name__ == "__main__":
    test = llm_call([{"role": "user", "content": "안녕"}])
    print(test)