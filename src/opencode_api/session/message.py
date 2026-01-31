from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.storage import Storage, NotFoundError
from ..core.bus import Bus, MESSAGE_UPDATED, MESSAGE_REMOVED, PART_UPDATED, MessagePayload, PartPayload
from ..core.identifier import Identifier
from ..core.supabase import get_client, is_enabled as supabase_enabled


class MessagePart(BaseModel):
    """메시지 파트 모델

    type 종류:
    - "text": 일반 텍스트 응답
    - "reasoning": Claude의 thinking/extended thinking
    - "tool_call": 도구 호출 (tool_name, tool_args, tool_status)
    - "tool_result": 도구 실행 결과 (tool_output)
    - "step_start": 단계 시작 (step_number, max_steps)
    - "step_finish": 단계 완료 (step_number, max_steps, tokens, cost, stop_reason)
    """
    id: str
    session_id: str
    message_id: str
    type: str  # "text", "reasoning", "tool_call", "tool_result", "step_start", "step_finish"
    content: Optional[str] = None  # text, reasoning용
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    tool_status: Optional[str] = None  # "pending", "running", "completed", "error"
    step_number: Optional[int] = None
    max_steps: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    stop_reason: Optional[str] = None


class MessageInfo(BaseModel):
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    created_at: datetime
    model: Optional[str] = None
    provider_id: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    parent_id: Optional[str] = None   # 소속 user 메시지 ID
    finish: Optional[str] = None      # 종료 이유 ("tool_calls", "stop" 등)


class UserMessage(MessageInfo):
    role: Literal["user"] = "user"
    content: str


class AssistantMessage(MessageInfo):
    role: Literal["assistant"] = "assistant"
    parts: List[MessagePart] = Field(default_factory=list)
    summary: bool = False


class Message:
    
    @staticmethod
    async def create_user(session_id: str, content: str, user_id: Optional[str] = None) -> UserMessage:
        message_id = Identifier.generate("message")
        now = datetime.utcnow()
        
        msg = UserMessage(
            id=message_id,
            session_id=session_id,
            content=content,
            created_at=now,
        )
        
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_messages").insert({
                "id": message_id,
                "session_id": session_id,
                "role": "user",
                "content": content,
            }).execute()
        else:
            await Storage.write(["message", session_id, message_id], msg.model_dump())
        
        await Bus.publish(MESSAGE_UPDATED, MessagePayload(session_id=session_id, message_id=message_id))
        return msg
    
    @staticmethod
    async def create_assistant(
        session_id: str,
        provider_id: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        summary: bool = False,
        parent_id: Optional[str] = None
    ) -> AssistantMessage:
        message_id = Identifier.generate("message")
        now = datetime.utcnow()

        msg = AssistantMessage(
            id=message_id,
            session_id=session_id,
            created_at=now,
            provider_id=provider_id,
            model=model,
            parts=[],
            summary=summary,
            parent_id=parent_id,
        )

        if supabase_enabled() and user_id:
            client = get_client()
            insert_data = {
                "id": message_id,
                "session_id": session_id,
                "role": "assistant",
                "provider_id": provider_id,
                "model_id": model,
            }
            if parent_id:
                insert_data["parent_id"] = parent_id
            client.table("opencode_messages").insert(insert_data).execute()
        else:
            await Storage.write(["message", session_id, message_id], msg.model_dump())
        
        await Bus.publish(MESSAGE_UPDATED, MessagePayload(session_id=session_id, message_id=message_id))
        return msg
    
    @staticmethod
    async def get(session_id: str, message_id: str, user_id: Optional[str] = None) -> Union[UserMessage, AssistantMessage]:
        if supabase_enabled() and user_id:
            client = get_client()
            result = client.table("opencode_messages").select("*, opencode_message_parts(*)").eq("id", message_id).eq("session_id", session_id).single().execute()
            if not result.data:
                raise NotFoundError(["message", session_id, message_id])
            
            data = result.data
            if data.get("role") == "user":
                return UserMessage(
                    id=data["id"],
                    session_id=data["session_id"],
                    role="user",
                    content=data.get("content", ""),
                    created_at=data["created_at"],
                )
            
            parts = [
                MessagePart(
                    id=p["id"],
                    session_id=session_id,
                    message_id=message_id,
                    type=p["type"],
                    content=p.get("content"),
                    tool_call_id=p.get("tool_call_id"),
                    tool_name=p.get("tool_name"),
                    tool_args=p.get("tool_args"),
                    tool_output=p.get("tool_output"),
                    tool_status=p.get("tool_status"),
                    step_number=p.get("step_number"),
                    max_steps=p.get("max_steps"),
                    input_tokens=p.get("input_tokens"),
                    output_tokens=p.get("output_tokens"),
                    cost=p.get("cost"),
                    stop_reason=p.get("stop_reason"),
                )
                for p in data.get("opencode_message_parts", [])
            ]
            return AssistantMessage(
                id=data["id"],
                session_id=data["session_id"],
                role="assistant",
                created_at=data["created_at"],
                provider_id=data.get("provider_id"),
                model=data.get("model_id"),
                usage={"input_tokens": data.get("input_tokens", 0), "output_tokens": data.get("output_tokens", 0)} if data.get("input_tokens") else None,
                error=data.get("error"),
                parts=parts,
            )
        
        data = await Storage.read(["message", session_id, message_id])
        if not data:
            raise NotFoundError(["message", session_id, message_id])
        
        if data.get("role") == "user":
            return UserMessage(**data)
        return AssistantMessage(**data)
    
    @staticmethod
    async def add_part(message_id: str, session_id: str, part: MessagePart, user_id: Optional[str] = None) -> MessagePart:
        part.id = Identifier.generate("part")
        part.message_id = message_id
        part.session_id = session_id
        
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_message_parts").insert({
                "id": part.id,
                "message_id": message_id,
                "type": part.type,
                "content": part.content,
                "tool_call_id": part.tool_call_id,
                "tool_name": part.tool_name,
                "tool_args": part.tool_args,
                "tool_output": part.tool_output,
                "tool_status": part.tool_status,
                "step_number": part.step_number,
                "max_steps": part.max_steps,
                "input_tokens": part.input_tokens,
                "output_tokens": part.output_tokens,
                "cost": part.cost,
                "stop_reason": part.stop_reason,
            }).execute()
        else:
            msg_data = await Storage.read(["message", session_id, message_id])
            if not msg_data:
                raise NotFoundError(["message", session_id, message_id])
            
            if "parts" not in msg_data:
                msg_data["parts"] = []
            msg_data["parts"].append(part.model_dump())
            await Storage.write(["message", session_id, message_id], msg_data)
        
        await Bus.publish(PART_UPDATED, PartPayload(
            session_id=session_id,
            message_id=message_id,
            part_id=part.id
        ))
        return part
    
    @staticmethod
    async def update_part(session_id: str, message_id: str, part_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> MessagePart:
        if supabase_enabled() and user_id:
            client = get_client()
            result = client.table("opencode_message_parts").update(updates).eq("id", part_id).execute()
            if result.data:
                p = result.data[0]
                await Bus.publish(PART_UPDATED, PartPayload(
                    session_id=session_id,
                    message_id=message_id,
                    part_id=part_id
                ))
                return MessagePart(
                    id=p["id"],
                    session_id=session_id,
                    message_id=message_id,
                    type=p["type"],
                    content=p.get("content"),
                    tool_call_id=p.get("tool_call_id"),
                    tool_name=p.get("tool_name"),
                    tool_args=p.get("tool_args"),
                    tool_output=p.get("tool_output"),
                    tool_status=p.get("tool_status"),
                    step_number=p.get("step_number"),
                    max_steps=p.get("max_steps"),
                    input_tokens=p.get("input_tokens"),
                    output_tokens=p.get("output_tokens"),
                    cost=p.get("cost"),
                    stop_reason=p.get("stop_reason"),
                )
            raise NotFoundError(["part", message_id, part_id])
        
        msg_data = await Storage.read(["message", session_id, message_id])
        if not msg_data:
            raise NotFoundError(["message", session_id, message_id])
        
        for i, p in enumerate(msg_data.get("parts", [])):
            if p.get("id") == part_id:
                msg_data["parts"][i].update(updates)
                await Storage.write(["message", session_id, message_id], msg_data)
                await Bus.publish(PART_UPDATED, PartPayload(
                    session_id=session_id,
                    message_id=message_id,
                    part_id=part_id
                ))
                return MessagePart(**msg_data["parts"][i])
        
        raise NotFoundError(["part", message_id, part_id])
    
    @staticmethod
    async def list(session_id: str, limit: Optional[int] = None, user_id: Optional[str] = None) -> List[Union[UserMessage, AssistantMessage]]:
        if supabase_enabled() and user_id:
            client = get_client()
            query = client.table("opencode_messages").select("*, opencode_message_parts(*)").eq("session_id", session_id).order("created_at")
            if limit:
                query = query.limit(limit)
            result = query.execute()
            
            messages = []
            for data in result.data:
                if data.get("role") == "user":
                    messages.append(UserMessage(
                        id=data["id"],
                        session_id=data["session_id"],
                        role="user",
                        content=data.get("content", ""),
                        created_at=data["created_at"],
                    ))
                else:
                    parts = [
                        MessagePart(
                            id=p["id"],
                            session_id=session_id,
                            message_id=data["id"],
                            type=p["type"],
                            content=p.get("content"),
                            tool_call_id=p.get("tool_call_id"),
                            tool_name=p.get("tool_name"),
                            tool_args=p.get("tool_args"),
                            tool_output=p.get("tool_output"),
                            tool_status=p.get("tool_status"),
                            step_number=p.get("step_number"),
                            max_steps=p.get("max_steps"),
                            input_tokens=p.get("input_tokens"),
                            output_tokens=p.get("output_tokens"),
                            cost=p.get("cost"),
                            stop_reason=p.get("stop_reason"),
                        )
                        for p in data.get("opencode_message_parts", [])
                    ]
                    messages.append(AssistantMessage(
                        id=data["id"],
                        session_id=data["session_id"],
                        role="assistant",
                        created_at=data["created_at"],
                        provider_id=data.get("provider_id"),
                        model=data.get("model_id"),
                        usage={"input_tokens": data.get("input_tokens", 0), "output_tokens": data.get("output_tokens", 0)} if data.get("input_tokens") else None,
                        error=data.get("error"),
                        parts=parts,
                        parent_id=data.get("parent_id"),
                        finish=data.get("finish"),
                    ))
            return messages
        
        message_keys = await Storage.list(["message", session_id])
        messages = []
        
        for key in message_keys:
            if limit and len(messages) >= limit:
                break
            data = await Storage.read(key)
            if data:
                if data.get("role") == "user":
                    messages.append(UserMessage(**data))
                else:
                    messages.append(AssistantMessage(**data))
        
        messages.sort(key=lambda m: m.created_at)
        return messages
    
    @staticmethod
    async def delete(session_id: str, message_id: str, user_id: Optional[str] = None) -> bool:
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_messages").delete().eq("id", message_id).execute()
        else:
            await Storage.remove(["message", session_id, message_id])
        
        await Bus.publish(MESSAGE_REMOVED, MessagePayload(session_id=session_id, message_id=message_id))
        return True
    
    @staticmethod
    async def set_usage(session_id: str, message_id: str, usage: Dict[str, int], user_id: Optional[str] = None) -> None:
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_messages").update({
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }).eq("id", message_id).execute()
        else:
            msg_data = await Storage.read(["message", session_id, message_id])
            if msg_data:
                msg_data["usage"] = usage
                await Storage.write(["message", session_id, message_id], msg_data)
    
    @staticmethod
    async def set_error(session_id: str, message_id: str, error: str, user_id: Optional[str] = None) -> None:
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_messages").update({"error": error}).eq("id", message_id).execute()
        else:
            msg_data = await Storage.read(["message", session_id, message_id])
            if msg_data:
                msg_data["error"] = error
                await Storage.write(["message", session_id, message_id], msg_data)

    @staticmethod
    async def set_finish(session_id: str, message_id: str, finish: str, user_id: Optional[str] = None) -> None:
        if supabase_enabled() and user_id:
            client = get_client()
            client.table("opencode_messages").update({"finish": finish}).eq("id", message_id).execute()
        else:
            msg_data = await Storage.read(["message", session_id, message_id])
            if msg_data:
                msg_data["finish"] = finish
                await Storage.write(["message", session_id, message_id], msg_data)
