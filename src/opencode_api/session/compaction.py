"""Session compaction module — prune old tool outputs and LLM-based summarization.

Ported from OpenCode TS compaction.ts:
- prune(): Remove old tool outputs beyond PRUNE_PROTECT threshold
- compact(): LLM-based conversation summarization (summary=True message)
- is_overflow(): Check if session exceeds model context limit
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from ..core.identifier import Identifier
from ..core.bus import Bus, SESSION_UPDATED, SessionPayload
from .message import Message, MessageInfo, MessagePart, UserMessage, AssistantMessage
from .session import Session, SessionInfo
from ..agent import get as get_agent, AgentInfo, get_system_prompt
from ..provider import get_provider, get_model
from ..provider.provider import Message as ProviderMessage, StreamChunk
from ..util.token import estimate, count_messages, is_overflow as token_is_overflow


# --- Constants (from OpenCode TS) ---
COMPACTION_THRESHOLD = 50  # Auto-compact after 50 messages
PRUNE_MINIMUM = 20_000     # Minimum pruned tokens to justify DB writes
PRUNE_PROTECT = 40_000     # Protect this many tokens of recent tool outputs
PRUNE_PROTECTED_TOOLS = ["skill"]  # Never prune these tools
PRUNED_MARKER = "[pruned]"  # Marker for pruned tool outputs

# Default compaction prompt (from OpenCode TS)
DEFAULT_COMPACTION_PROMPT = (
    "Provide a detailed prompt for continuing our conversation above. "
    "Focus on information that would be helpful for continuing the conversation, "
    "including what we did, what we're doing, which files we're working on, "
    "and what we're going to do next considering new session will not have "
    "access to our conversation."
)


class PruneResult:
    """Result of a prune operation."""

    def __init__(self, pruned_count: int, tokens_saved: int):
        self.pruned_count = pruned_count
        self.tokens_saved = tokens_saved


class CompactionResult:
    """Result of a compaction operation."""

    def __init__(
        self,
        session_id: str,
        summary: str,
        messages_compacted: int,
        tokens_saved: int,
        cost_saved: float,
    ):
        self.session_id = session_id
        self.summary = summary
        self.messages_compacted = messages_compacted
        self.tokens_saved = tokens_saved
        self.cost_saved = cost_saved
        self.compacted_at = datetime.utcnow()


# ============================================================
# Core Functions
# ============================================================


async def prune(session_id: str, user_id: Optional[str] = None) -> Optional[PruneResult]:
    """Prune old tool outputs to save context tokens.

    Goes backwards through messages. Protects the latest 2 turns and
    PRUNE_PROTECT tokens of recent tool outputs. Everything beyond that
    threshold gets its tool_output replaced with PRUNED_MARKER.

    Algorithm (from OpenCode TS compaction.ts lines 49-90):
    1. Iterate messages backwards
    2. Count user messages as turns — skip if turns < 2
    3. Stop at summary messages
    4. Accumulate tool_result token estimates
    5. Once total > PRUNE_PROTECT, mark excess parts for pruning
    6. If pruned total > PRUNE_MINIMUM, persist changes
    """
    try:
        messages, _ = await Message.list(session_id, user_id=user_id)
        if not messages:
            return None

        total = 0
        pruned = 0
        to_prune: List[Dict[str, str]] = []  # [{message_id, part_id, estimate}]
        turns = 0

        # Iterate messages backwards (newest first)
        for msg_index in range(len(messages) - 1, -1, -1):
            msg = messages[msg_index]

            # Count user messages as turns
            if isinstance(msg, UserMessage):
                turns += 1

            # Protect latest 2 turns
            if turns < 2:
                continue

            # Stop at summary messages
            if isinstance(msg, AssistantMessage) and msg.summary:
                break

            # Process assistant message parts backwards
            if isinstance(msg, AssistantMessage):
                for part_index in range(len(msg.parts) - 1, -1, -1):
                    part = msg.parts[part_index]

                    # Only process completed tool_result parts
                    if part.type != "tool_result":
                        continue

                    # Skip protected tools
                    if part.tool_name and part.tool_name in PRUNE_PROTECTED_TOOLS:
                        continue

                    # Skip already pruned
                    if part.tool_output and part.tool_output.startswith(PRUNED_MARKER):
                        break  # Already pruned = compaction boundary, stop

                    # Estimate tokens
                    est = estimate(part.tool_output or "")
                    total += est

                    # Beyond protection threshold -> mark for pruning
                    if total > PRUNE_PROTECT:
                        pruned += est
                        to_prune.append({
                            "message_id": msg.id,
                            "part_id": part.id,
                            "session_id": session_id,
                        })

        # Only persist if we have enough tokens to justify it
        if pruned > PRUNE_MINIMUM:
            for item in to_prune:
                await Message.update_part(
                    session_id=item["session_id"],
                    message_id=item["message_id"],
                    part_id=item["part_id"],
                    updates={"tool_output": PRUNED_MARKER},
                    user_id=user_id,
                )
            return PruneResult(pruned_count=len(to_prune), tokens_saved=pruned)

        return None

    except Exception as e:
        print(f"[COMPACTION] prune error: {e}")
        return None


async def compact(
    session_id: str, user_id: Optional[str] = None
) -> Optional[CompactionResult]:
    """Compact a session by generating an LLM summary.

    1. Load all messages
    2. Get compaction agent and determine model
    3. Create summary assistant message
    4. Call LLM with conversation history + compaction prompt
    5. Store summary text and publish event
    """
    try:
        session = await Session.get(session_id, user_id)
        if not session:
            return None

        messages, _ = await Message.list(session_id, user_id=user_id)
        if not messages:
            return None

        message_count = len(messages)

        # Get compaction agent
        compaction_agent = get_agent("compaction")
        if not compaction_agent:
            return None

        # Determine provider and model
        provider_id = session.provider_id or "litellm"
        model_id = session.model_id or "gemini/gemini-2.0-flash"

        # If compaction agent has its own model, use that
        if compaction_agent.model:
            provider_id = compaction_agent.model.provider_id
            model_id = compaction_agent.model.model_id

        provider = get_provider(provider_id)
        if not provider:
            return None

        # Estimate tokens before compaction
        token_info = count_messages(messages)
        estimated_tokens_before = token_info.total

        # Create summary assistant message
        summary_msg = await Message.create_assistant(
            session_id=session_id,
            provider_id=provider_id,
            model=model_id,
            user_id=user_id,
            summary=True,
        )

        # Build provider messages from history
        provider_messages = _build_provider_messages(messages)

        # Append compaction prompt as final user message
        provider_messages.append(
            ProviderMessage(role="user", content=DEFAULT_COMPACTION_PROMPT)
        )

        # Get system prompt for compaction agent
        system_prompt = get_system_prompt(compaction_agent)

        # Stream LLM response and collect all text
        summary_text = ""
        try:
            async for chunk in provider.stream(
                model_id=model_id,
                messages=provider_messages,
                tools=None,
                system=system_prompt or None,
                temperature=compaction_agent.temperature,
                max_tokens=compaction_agent.max_tokens,
            ):
                if chunk.type == "text" and chunk.text:
                    summary_text += chunk.text
                elif chunk.type == "error":
                    print(f"[COMPACTION] LLM error: {chunk.error}")
                    break
        except Exception as e:
            print(f"[COMPACTION] LLM stream error: {e}")
            # Fallback to simple summary if LLM fails
            summary_text = _fallback_summary(messages, message_count)

        if not summary_text:
            summary_text = _fallback_summary(messages, message_count)

        # Store summary as text part
        await Message.add_part(
            summary_msg.id,
            session_id,
            MessagePart(
                id="",
                session_id=session_id,
                message_id=summary_msg.id,
                type="text",
                content=summary_text,
            ),
            user_id,
        )

        # Estimate tokens saved
        summary_tokens = estimate(summary_text)
        tokens_saved = max(0, estimated_tokens_before - summary_tokens)
        cost_saved = (tokens_saved / 1_000_000) * 0.01  # rough estimate

        # Publish event
        await Bus.publish(
            SESSION_UPDATED, SessionPayload(id=session_id)
        )

        return CompactionResult(
            session_id=session_id,
            summary=summary_text,
            messages_compacted=message_count,
            tokens_saved=tokens_saved,
            cost_saved=cost_saved,
        )

    except Exception as e:
        print(f"[COMPACTION] compact error: {e}")
        return None


async def is_overflow(
    session_id: str,
    model_id: str,
    provider_id: str,
    user_id: Optional[str] = None,
) -> bool:
    """Check if session messages exceed model context limit."""
    try:
        messages, _ = await Message.list(session_id, user_id=user_id)
        return token_is_overflow(messages, model_id, provider_id)
    except Exception:
        return False


# ============================================================
# Backward-compatible convenience functions
# ============================================================


async def should_compact_session(session_id: str, user_id: Optional[str] = None) -> bool:
    """Check if session should be compacted (50+ messages)."""
    try:
        messages, _ = await Message.list(session_id, user_id=user_id)
        return len(messages) >= COMPACTION_THRESHOLD
    except Exception:
        return False


async def compact_session(
    session_id: str, user_id: Optional[str] = None
) -> Optional[CompactionResult]:
    """Compact a session (convenience wrapper)."""
    return await compact(session_id, user_id)


async def get_session_compaction_status(
    session_id: str, user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Get compaction status for a session."""
    try:
        messages, _ = await Message.list(session_id, user_id=user_id)
        message_count = len(messages)

        compaction_count = sum(
            1
            for m in messages
            if isinstance(m, AssistantMessage) and m.summary
        )

        return {
            "session_id": session_id,
            "message_count": message_count,
            "compaction_threshold": COMPACTION_THRESHOLD,
            "should_compact": message_count >= COMPACTION_THRESHOLD,
            "compaction_count": compaction_count,
            "remaining_until_compaction": max(
                0, COMPACTION_THRESHOLD - message_count
            ),
        }
    except Exception as e:
        return {"session_id": session_id, "error": str(e)}


# ============================================================
# Internal helpers
# ============================================================


def _build_provider_messages(
    messages: List,
) -> List[ProviderMessage]:
    """Build provider message list from session history.

    Same pattern as SessionPrompt._build_messages but simplified
    for compaction (no tool schema needed).
    """
    result = []

    for msg in messages:
        if isinstance(msg, UserMessage):
            if msg.content:
                result.append(ProviderMessage(role="user", content=msg.content))

        elif isinstance(msg, AssistantMessage):
            text_parts = []
            tool_results = []

            for part in msg.parts:
                if part.type == "text" and part.content:
                    text_parts.append(part.content)
                elif part.type == "tool_result" and part.tool_output:
                    # Include pruned marker as-is (model sees "[pruned]")
                    tool_results.append(part.tool_output)

            if text_parts:
                result.append(
                    ProviderMessage(role="assistant", content="".join(text_parts))
                )

            if tool_results:
                result.append(
                    ProviderMessage(
                        role="user",
                        content="\n\n".join(
                            f"Tool result:\n{r}" for r in tool_results
                        ),
                    )
                )

    return result


def _fallback_summary(messages: List, message_count: int) -> str:
    """Generate a simple fallback summary when LLM is unavailable."""
    lines = []
    for msg in messages:
        if isinstance(msg, UserMessage) and msg.content:
            lines.append(f"user: {msg.content[:200]}")
        elif isinstance(msg, AssistantMessage):
            for part in msg.parts:
                if part.type == "text" and part.content:
                    lines.append(f"assistant: {part.content[:200]}")
                    break

    key_messages = []
    if lines:
        key_messages.append(lines[0])
        if len(lines) > 1:
            key_messages.append(lines[-1])

    summary_parts = [
        f"[Conversation Summary - {message_count} messages]",
        "",
        "Key points:",
    ]
    for msg_line in key_messages:
        summary_parts.append(f"- {msg_line}")

    summary_parts.extend(
        [
            "",
            f"Total messages: {message_count}",
            "Context: Previous conversation history available in full log.",
        ]
    )
    return "\n".join(summary_parts)
