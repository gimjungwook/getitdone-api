from typing import Dict, Any, List, Optional, AsyncGenerator
import json
import os

from .provider import BaseProvider, ModelInfo, Message, StreamChunk, ToolCall


DEFAULT_MODELS = {
    # Z.ai GLM-4.7 Flash (무료)
    "zai/glm-4.7-flash": ModelInfo(
        id="zai/glm-4.7-flash",
        name="GLM-4.7 Flash",
        provider_id="zai",
        context_limit=128000,
        output_limit=8192,
        supports_tools=True,
        supports_streaming=True,
        cost_input=0.0,
        cost_output=0.0,
    ),
}


class LiteLLMProvider(BaseProvider):
    
    def __init__(self):
        self._litellm = None
        self._models = dict(DEFAULT_MODELS)
    
    @property
    def id(self) -> str:
        return "zai"
    
    @property
    def name(self) -> str:
        return "Z.ai"
    
    @property
    def models(self) -> Dict[str, ModelInfo]:
        return self._models
    
    def add_model(self, model: ModelInfo) -> None:
        self._models[model.id] = model
    
    def _get_litellm(self):
        if self._litellm is None:
            try:
                import litellm
                litellm.drop_params = True
                self._litellm = litellm
            except ImportError:
                raise ImportError("litellm package is required. Install with: pip install litellm")
        return self._litellm
    
    async def stream(
        self,
        model_id: str,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        litellm = self._get_litellm()
        
        litellm_messages = []
        
        if system:
            litellm_messages.append({"role": "system", "content": system})
        
        for msg in messages:
            content = msg.content
            if isinstance(content, str):
                litellm_messages.append({"role": msg.role, "content": content})
            else:
                litellm_messages.append({
                    "role": msg.role,
                    "content": [{"type": c.type, "text": c.text} for c in content if c.text]
                })
        
        # Z.ai 모델 처리: OpenAI-compatible API 사용
        actual_model = model_id
        if model_id.startswith("zai/"):
            # zai/glm-4.7-flash -> openai/glm-4.7-flash with custom api_base
            actual_model = "openai/" + model_id[4:]

        kwargs: Dict[str, Any] = {
            "model": actual_model,
            "messages": litellm_messages,
            "stream": True,
        }

        # Z.ai 전용 설정
        if model_id.startswith("zai/"):
            kwargs["api_base"] = os.environ.get("ZAI_API_BASE", "https://api.z.ai/api/paas/v4")
            kwargs["api_key"] = os.environ.get("ZAI_API_KEY")

        if temperature is not None:
            kwargs["temperature"] = temperature

        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = 8192
        
        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", t.get("input_schema", {}))
                    }
                }
                for t in tools
            ]
        
        current_tool_calls: Dict[int, Dict[str, Any]] = {}
        
        try:
            response = await litellm.acompletion(**kwargs)
            
            async for chunk in response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    delta = getattr(choice, 'delta', None)
                    
                    if delta:
                        if hasattr(delta, 'content') and delta.content:
                            yield StreamChunk(type="text", text=delta.content)
                        
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tc in delta.tool_calls:
                                idx = tc.index if hasattr(tc, 'index') else 0
                                
                                if idx not in current_tool_calls:
                                    current_tool_calls[idx] = {
                                        "id": tc.id if hasattr(tc, 'id') and tc.id else f"call_{idx}",
                                        "name": "",
                                        "arguments_json": ""
                                    }
                                
                                if hasattr(tc, 'function'):
                                    if hasattr(tc.function, 'name') and tc.function.name:
                                        current_tool_calls[idx]["name"] = tc.function.name
                                    if hasattr(tc.function, 'arguments') and tc.function.arguments:
                                        current_tool_calls[idx]["arguments_json"] += tc.function.arguments
                    
                    finish_reason = getattr(choice, 'finish_reason', None)
                    if finish_reason:
                        for idx, tc_data in current_tool_calls.items():
                            if tc_data["name"]:
                                try:
                                    args = json.loads(tc_data["arguments_json"]) if tc_data["arguments_json"] else {}
                                except json.JSONDecodeError:
                                    args = {}
                                
                                yield StreamChunk(
                                    type="tool_call",
                                    tool_call=ToolCall(
                                        id=tc_data["id"],
                                        name=tc_data["name"],
                                        arguments=args
                                    )
                                )
                        
                        usage = None
                        if hasattr(chunk, 'usage') and chunk.usage:
                            usage = {
                                "input_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
                                "output_tokens": getattr(chunk.usage, 'completion_tokens', 0),
                            }
                        
                        stop_reason = self._map_stop_reason(finish_reason)
                        yield StreamChunk(type="done", usage=usage, stop_reason=stop_reason)
            
        except Exception as e:
            yield StreamChunk(type="error", error=str(e))
    
    async def complete(
        self,
        model_id: str,
        prompt: str,
        max_tokens: int = 100,
    ) -> str:
        """단일 완료 요청 (스트리밍 없음)"""
        litellm = self._get_litellm()

        actual_model = model_id
        kwargs: Dict[str, Any] = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        # Z.ai 모델 처리
        if model_id.startswith("zai/"):
            actual_model = "openai/" + model_id[4:]
            kwargs["model"] = actual_model
            kwargs["api_base"] = os.environ.get("ZAI_API_BASE", "https://api.z.ai/api/paas/v4")
            kwargs["api_key"] = os.environ.get("ZAI_API_KEY")

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content or ""

    def _map_stop_reason(self, finish_reason: Optional[str]) -> str:
        if not finish_reason:
            return "end_turn"

        mapping = {
            "stop": "end_turn",
            "end_turn": "end_turn",
            "tool_calls": "tool_calls",
            "function_call": "tool_calls",
            "length": "max_tokens",
            "max_tokens": "max_tokens",
            "content_filter": "content_filter",
        }
        return mapping.get(finish_reason, "end_turn")
