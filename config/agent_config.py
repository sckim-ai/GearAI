AGENT_CONFIGS = {
    "gpt": {
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000
    },
    "chain": {
        "chain_length": 3,
        "memory_size": 5
    }
}

SYSTEM_MESSAGE = [
    {
        "role": "system",
        "content": (
            "아래의 대화는 이전부터 진행되었으며, 현재까지 기록된 실제 대화 내역입니다. "
            "따라서 사용자가 과거의 메시지나 맥락을 언급하면, 지금까지 받은 메시지가 이전 메시지가 저장된 기록임을 인지하고 자연스럽게 응답해야 합니다."
        ),
    },
    {
        "role": "assistant",
        "content": "무엇을 도와드릴까요?"
    }
] 