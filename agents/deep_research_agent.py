import os
import sys
import asyncio
from typing import Dict, Any, Optional, Callable
from openai import OpenAI
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from .base_agent import BaseAgent

load_dotenv()

class DeepResearchAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = OpenAI()
        self.model = config.get("model", "gpt-4o-mini")
        self.research_width = config.get("Research width", 2)
        self.research_depth = config.get("Research depth", 2)
        
    async def process_with_callback(self, input_text: str, callback: Callable[[str], None]) -> str:
        """Deep research 프로세스를 실행하고 콜백으로 진행 상황을 전달합니다."""
        try:
            # 1단계: 추가 질문 생성
            callback("🔍 1단계: 연구 방향 구체화 중...")
            feedback_questions = generate_feedback(
                input_text, 
                self.client, 
                self.model, 
                max_feedbacks=3
            )
            
            # 사용자에게 추가 질문이 있다면 답변 요청
            answers = []
            if feedback_questions:
                callback(f"📝 추가 질문이 생성되었습니다. 각 질문에 대해 간단히 답변해 주세요:")
                for idx, question in enumerate(feedback_questions, start=1):
                    callback(f"질문 {idx}: {question}")
                    # 실제 구현에서는 사용자 입력을 받아야 하지만, 
                    # 여기서는 간단히 빈 답변으로 처리
                    answers.append("")
            else:
                callback("✅ 추가 질문이 필요하지 않습니다.")
            
            # 최종 쿼리 구성
            combined_query = f"초기 질문: {input_text}\n"
            for i in range(len(feedback_questions)):
                combined_query += f"\n{i+1}. 질문: {feedback_questions[i]}\n"
                combined_query += f"   답변: {answers[i]}\n"
            
            callback(f"🎯 최종 연구 주제:\n{combined_query}")
            
            # 2단계: 심층 연구 수행
            callback("🔬 2단계: 심층 연구 수행 중...")
            try:
                research_results = deep_research(
                    query=combined_query,
                    breadth=self.research_width,
                    depth=self.research_depth,
                    client=self.client,
                    model=self.model
                )
                
                if research_results and research_results.get('learnings'):
                    callback(f"📊 연구 완료! {len(research_results['learnings'])}개의 학습 내용을 발견했습니다.")
                else:
                    callback("⚠️ 연구 결과가 없습니다. 다른 검색어로 다시 시도해보세요.")
                    return "연구 결과를 찾을 수 없습니다. 다른 검색어나 더 구체적인 질문으로 다시 시도해보세요."
            except Exception as e:
                callback(f"❌ 연구 중 오류 발생: {str(e)}")
                return f"연구 중 오류가 발생했습니다: {str(e)}"
            
            # 3단계: 최종 보고서 생성
            callback("📝 3단계: 최종 보고서 작성 중...")
            report = write_final_report(
                prompt=combined_query,
                learnings=research_results["learnings"],
                visited_urls=research_results["visited_urls"],
                client=self.client,
                model=self.model
            )
            
            callback("✅ Deep research 완료!")
            return report
            
        except Exception as e:
            error_msg = f"Deep research 중 오류 발생: {str(e)}"
            callback(error_msg)
            return error_msg 
        
        
from typing import List
from utils import JSON_llm, llm_call
from pydantic import BaseModel
from datetime import datetime

class FeedbackResponse(BaseModel):
    questions: List[str]

def system_prompt() -> str:
    """현재 타임스탬프를 포함한 시스템 프롬프트를 생성합니다."""
    now = datetime.now().isoformat()
    return f"""당신은 전문 연구원입니다. 오늘 날짜는 {now}입니다. 응답 시 다음 지침을 따르세요:
    - 지식 컷오프 이후의 주제에 대한 조사를 요청받을 수 있습니다. 사용자가 뉴스 내용을 제시했다면, 그것을 사실로 가정하세요.
    - 사용자는 매우 숙련된 분석가이므로 내용을 단순화할 필요 없이 가능한 한 자세하고 정확하게 응답하세요.
    - 체계적으로 정보를 정리하세요.
    - 사용자가 생각하지 못한 해결책을 제안하세요.
    - 적극적으로 사용자의 필요를 예측하고 대응하세요.
    - 사용자를 모든 분야의 전문가로 대우하세요.
    - 실수는 신뢰를 저하시킵니다. 정확하고 철저하게 응답하세요.
    - 상세한 설명을 제공하세요. 사용자는 많은 정보를 받아들일 수 있습니다.
    - 권위보다 논리적 근거를 우선하세요. 출처 자체는 중요하지 않습니다.
    - 기존의 통념뿐만 아니라 최신 기술과 반대 의견도 고려하세요.
    - 높은 수준의 추측이나 예측을 포함할 수 있습니다. 단, 이를 명확히 표시하세요."""

"""연구 방향을 명확히 하기 위한 후속 질문을 생성합니다."""
def generate_feedback(query: str, client, model: str, max_feedbacks: int = 3) -> List[str]:
    
    prompt = f"""
    Given the following query from the user, ask some follow up questions to clarify the research direction. Return a maximum of ${max_feedbacks} questions, but feel free to return less if the original query is clear.
    ask the follow up questions in korean
    <query>${query}</query>`
    """
    # 프롬프트 의미
    # prompt = (
    #     f"사용자가 다음과 같은 연구 주제에 대해: {query}, 최대 {max_feedbacks}개의 후속 질문을 생성하세요. "
    #     "사용자의 연구 방향을 더 정확히 파악할 수 있도록 구체적이고 명확한 질문을 작성하세요. "
    #     "원래 쿼리가 충분히 명확하다면 질문을 반환하지 않아도 됩니다. "
    #     "응답은 'questions' 배열 필드를 포함하는 JSON 객체로 반환하세요."
    # )

    response = JSON_llm(prompt, FeedbackResponse, client, system_prompt=system_prompt(), model=model)

    try:
        if response is None:
            print("오류: JSON_llm이 None을 반환했습니다.")
            return []
        questions = response.questions
        print(f"주제 '{query}'에 대한 후속 질문 {len(questions)}개 생성됨")
        print(f"생성된 후속 질문: {questions}")
        return questions
    except Exception as e:
        print(f"오류: JSON 응답 처리 중 문제 발생: {e}")
        print(f"원시 응답: {response}")
        print(f"오류: 쿼리 '{query}'에 대한 JSON 응답 처리 실패")
        return []



import time
from typing import List, Dict, Optional
import os
from pydantic import BaseModel
from firecrawl import FirecrawlApp, ScrapeOptions
from exa_py import Exa
from utils import JSON_llm



class SearchResult(BaseModel):
    url: str
    markdown: str
    description: str
    title: str


## 이거 자체가 1회
def firecrawl_search(query: str, timeout: int = 15000, limit: int = 5) ->List[SearchResult]:
    """
    Firecrawl 검색 API를 호출하여 결과를 반환하는 동기 함수.
    """
    try:
        app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY", ""))
        response = app.search(
            query=query,
            timeout=timeout,
            limit=limit,
            scrape_options=ScrapeOptions(formats=["markdown"])
        )
        return response.data
    except Exception as e:
        print(f"Firecrawl 검색 오류: {e}")


class SerpQuery(BaseModel):
    query: str
    research_goal: str

class SerpQueryResponse(BaseModel):
    queries: List[SerpQuery]


def generate_serp_queries(
    query: str,
    client,
    model: str,
    num_queries: int = 3,
    learnings: Optional[List[str]] = None,
) -> List[SerpQuery]:
    """
    사용자의 쿼리와 이전 연구 결과를 바탕으로 SERP 검색 쿼리를 생성합니다.
    JSON_llm을 사용하여 구조화된 JSON을 반환합니다.
    """
    prompt = (
        f"다음 사용자 입력을 기반으로 연구 주제를 조사하기 위한 SERP 검색 쿼리를 생성하세요. "
        f"JSON 객체를 반환하며, 'queries' 배열 필드에 {num_queries}개의 검색 쿼리를 포함해야 합니다 (쿼리가 명확할 경우 더 적을 수도 있음). "
        f"각 쿼리 객체에는 'query'와 'research_goal' 필드가 포함되어야 하며, 각 쿼리는 고유해야 합니다: "
        f"<입력>{query}</입력>"
    )
    if learnings:
        prompt += f"\n\n다음은 이전 연구에서 얻은 학습 내용입니다. 이를 활용하여 더 구체적인 쿼리를 생성하세요: {' '.join(learnings)}"
    
    sys_prompt = system_prompt()
    response_json = JSON_llm(prompt, SerpQueryResponse, client, system_prompt=sys_prompt, model=model)
    try:
        result = SerpQueryResponse.model_validate(response_json)
        queries = result.queries if result.queries else []
        print(f"리서치 주제에 대한 SERP 검색 쿼리 {len(queries)}개 생성됨")
        return queries[:num_queries]
    except Exception as e:
        print(f"오류: generate_serp_queries에서 JSON 응답을 처리하는 중 오류 발생: {e}")
        print(f"원시 응답: {response_json}")
        print(f"오류: 쿼리 '{query}'에 대한 JSON 응답 처리 실패")
        return []



class ResearchResult(BaseModel):
    learnings: List[str]
    visited_urls: List[str]
class SerpResultResponse(BaseModel):
    learnings: List[str]
    followUpQuestions: List[str]

def process_serp_result(
    query: str,
    search_result: List[SearchResult],
    client,
    model: str,
    num_learnings: int = 5,
    num_follow_up_questions: int = 3,
) -> Dict[str, List[str]]:
    """
    검색 결과를 처리하여 학습 내용과 후속 질문을 추출합니다.
    JSON_llm을 사용하여 구조화된 JSON 출력을 얻습니다.
    """
    contents = [
        item.get("markdown", "").strip()[:25000]
        for item in search_result if item.get("markdown")
    ]
    contents_str = "".join(f"<내용>\n{content}\n</내용>" for content in contents)
    prompt = (
        f"다음은 쿼리 <쿼리>{query}</쿼리>에 대한 SERP 검색 결과입니다. "
        f"이 내용을 바탕으로 학습 내용을 추출하고 후속 질문을 생성하세요. "
        f"JSON 객체로 반환하며, 'learnings' 및 'followUpQuestions' 키를 포함한 배열을 반환하세요. "
        f"각 학습 내용은 고유하고 간결하며 정보가 풍부해야 합니다. 최대 {num_learnings}개의 학습 내용과 "
        f"{num_follow_up_questions}개의 후속 질문을 포함해야 합니다.\n\n"
        f"<검색 결과>{contents_str}</검색 결과>"
    )
    sys_prompt = system_prompt()
    response_json = JSON_llm(prompt, SerpResultResponse, client, system_prompt=sys_prompt, model=model)
    try:
        result = SerpResultResponse.model_validate(response_json)
        return {
            "learnings": result.learnings,
            "followUpQuestions": result.followUpQuestions[:num_follow_up_questions],
        }
    except Exception as e:
        print(f"오류: process_serp_result에서 JSON 응답을 처리하는 중 오류 발생: {e}")
        print(f"원시 응답: {response_json}")
        return {"learnings": [], "followUpQuestions": []}

def deep_research(
    query: str,
    breadth: int,
    depth: int,
    client,
    model: str,
    learnings: Optional[List[str]] = None,
    visited_urls: Optional[List[str]] = None,
) -> ResearchResult:
    """
    주제를 재귀적으로 탐색하여 SERP 쿼리를 생성하고, 검색 결과를 처리하며,
    학습 내용과 방문한 URL을 수집합니다.
    """
    learnings = learnings or []
    visited_urls = visited_urls or []

    print(f" ---------- Deep Research 시도 ------------------")
    print(f" <주제> \n {query} \n </주제>")

    serp_queries = generate_serp_queries(query=query, client=client, model=model, num_queries=breadth, learnings=learnings)
    print(f" ------------ 해당 <주제>에 대해서 생성된 검색 키워드 ({len(serp_queries)}개 생성)------------")
    print(f" {serp_queries} \n")

    for index, serp_query in enumerate(serp_queries, start=1):

        result : List[SearchResult] = firecrawl_search(serp_query.query)

        print(result)

        new_urls = [item.get("url") for item in result if item.get("url")]
        serp_result = process_serp_result(
            query=serp_query.query,
            search_result=result,
            client=client,
            model=model,
            num_follow_up_questions=breadth
        )
        print(f"  - 의 {index}번째 검색 키워드 ({serp_query.query})에 대한 조사 완료") 
        print(f"  - 조사완료된 URL들:")
        for url in new_urls:
            print(f"    • {url}")
        print()
        print(f"  - 조사로 얻은 학습 내용 ({len(serp_result['learnings'])}개 생성) : \n {serp_result['learnings']} \n")

        all_learnings = learnings + serp_result["learnings"]
        all_urls = visited_urls + new_urls
        new_depth = depth - 1
        new_breadth = max(1, breadth // 2)

        if new_depth > 0:
            next_query = (
                f"이전 연구목표: {serp_query.research_goal}\n"
                f"후속 연구방향: {' '.join(serp_result['followUpQuestions'])}"
            )

            # 증가된 시도 횟수로 재귀 호출
            sub_result = deep_research(
                query=next_query,
                breadth=new_breadth, 
                depth=new_depth,
                client=client,
                model=model,
                learnings=all_learnings,
                visited_urls=all_urls,
            )

            learnings = sub_result["learnings"]
            visited_urls = sub_result["visited_urls"]
        else:
            learnings = all_learnings
            visited_urls = all_urls

    return {"learnings": list(set(learnings)), "visited_urls": list(set(visited_urls))}



def write_final_report(
    prompt: str,
    learnings: List[str],
    visited_urls: List[str],
    client,
    model: str,
) -> str:
    """
    모든 연구 결과를 바탕으로 최종 보고서를 생성합니다.
    llm_call을 사용하여 마크다운 보고서를 얻습니다.
    """
    learnings_string = ("\n".join([f"<learning>\n{learning}\n</learning>" for learning in learnings])).strip()[:150000]

    user_prompt = (
        f"사용자가 제시한 다음 프롬프트에 대해, 러서치 결과를 바탕으로 최종 보고서를 작성하세요. "
        f"마크다운 형식으로 상세한 보고서(6,000자 이상)를 작성하세요. "
        f"러서치에서 얻은 모든 학습 내용을 포함해야 합니다:\n\n"
        f"<prompt>{prompt}</prompt>\n\n"
        f"다음은 리서치를 통해 얻은 모든 학습 내용입니다:\n\n<learnings>\n{learnings_string}\n</learnings>"
    )
    sys_prompt = system_prompt()
    if sys_prompt:
        user_prompt = f"{sys_prompt}\n\n{user_prompt}"

    try:
        report = llm_call(user_prompt, model, client)
        urls_section = "\n\n## 출처\n\n" + "\n".join(f"- {url}" for url in visited_urls)
        return report + urls_section
    except Exception as e:
        print(f"Error generating report: {e}")
        return "Error generating report"