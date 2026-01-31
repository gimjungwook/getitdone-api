"""토큰 계산 유틸리티

OpenCode TS의 토큰 추정 로직을 Python으로 포팅:
- CHARS_PER_TOKEN = 4 (간단한 휴리스틱)
- estimate(text) = len(text) / 4
- 메시지 토큰 카운팅
- 모델 컨텍스트 오버플로우 체크
"""

from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel

from ..provider.provider import get_model, ModelInfo
from ..session.message import UserMessage, AssistantMessage, MessagePart


CHARS_PER_TOKEN = 4


class TokenInfo(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total: int = 0


MODEL_LIMITS: Dict[str, int] = {
    "zai/glm-4.7-flash": 128000,
}


def estimate(text: str) -> int:
    """텍스트의 토큰 수를 간단한 휴리스틱으로 추정
    
    OpenCode TS 패턴: Math.round(text.length / 4)
    """
    if not text:
        return 0
    return max(0, round(len(text) / CHARS_PER_TOKEN))


def count_messages(messages: List[Union[UserMessage, AssistantMessage]]) -> TokenInfo:
    """메시지 리스트의 총 토큰 수 계산
    
    UserMessage: content 토큰 카운트 (input)
    AssistantMessage: parts의 모든 content 토큰 카운트 (output)
    """
    input_tokens = 0
    output_tokens = 0
    
    for msg in messages:
        if isinstance(msg, UserMessage):
            input_tokens += estimate(msg.content)
        elif isinstance(msg, AssistantMessage):
            for part in msg.parts:
                if part.type == "text" and part.content:
                    output_tokens += estimate(part.content)
                elif part.type == "reasoning" and part.content:
                    output_tokens += estimate(part.content)
                elif part.type == "tool_call":
                    if part.tool_name:
                        output_tokens += estimate(part.tool_name)
                    if part.tool_args:
                        import json
                        output_tokens += estimate(json.dumps(part.tool_args))
                elif part.type == "tool_result" and part.tool_output:
                    input_tokens += estimate(part.tool_output)
    
    total = input_tokens + output_tokens
    
    return TokenInfo(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total=total
    )


def is_overflow(
    messages: List[Union[UserMessage, AssistantMessage]],
    model_id: str,
    provider_id: str
) -> bool:
    """메시지가 모델의 컨텍스트 한계를 초과하는지 체크
    
    OpenCode TS 로직:
    - usable = context_limit - min(output_limit, 16384)
    - overflow = total_tokens > usable
    """
    model = get_model(provider_id, model_id)
    if not model:
        return False
    
    if model.context_limit == 0:
        return False
    
    token_info = count_messages(messages)
    
    output_reserve = min(model.output_limit, 16384)
    usable_limit = model.context_limit - output_reserve
    
    return token_info.total > usable_limit
