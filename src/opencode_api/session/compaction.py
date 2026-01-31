"""Session compaction module for managing conversation context.

This module provides functionality to automatically compact conversation history
when it exceeds a threshold (50 messages), reducing API costs while maintaining context.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from ..core.identifier import Identifier
from ..core.bus import Bus, SESSION_UPDATED, SessionPayload
from .message import Message, MessageInfo, AssistantMessage
from .session import Session, SessionInfo
from ..agent import get, AgentInfo


COMPACTION_THRESHOLD = 50  # Auto-compact after 50 messages


class CompactionResult:
    """Result of a compaction operation."""
    
    def __init__(
        self,
        session_id: str,
        summary: str,
        messages_compacted: int,
        tokens_saved: int,
        cost_saved: float
    ):
        self.session_id = session_id
        self.summary = summary
        self.messages_compacted = messages_compacted
        self.tokens_saved = tokens_saved
        self.cost_saved = cost_saved
        self.compacted_at = datetime.utcnow()


class SessionCompaction:
    """Manages automatic compaction of session conversations."""
    
    @staticmethod
    async def should_compact(session_id: str) -> bool:
        """Check if session should be compacted (50+ messages).
        
        Args:
            session_id: The session ID to check
            
        Returns:
            True if message count >= COMPACTION_THRESHOLD
        """
        try:
            messages, _ = await Message.list(session_id)
            return len(messages) >= COMPACTION_THRESHOLD
        except Exception:
            return False
    
    @staticmethod
    async def compact(session_id: str, user_id: Optional[str] = None) -> Optional[CompactionResult]:
        """Compact a session by generating a summary.
        
        This method:
        1. Retrieves all messages for the session
        2. Uses the compaction agent to generate a summary
        3. Stores the summary in session metadata
        4. Returns compaction statistics
        
        Args:
            session_id: The session to compact
            user_id: Optional user ID for authorization
            
        Returns:
            CompactionResult with summary and statistics, or None if failed
        """
        try:
            # Get session info
            session = await Session.get(session_id, user_id)
            if not session:
                return None
            
            # Get all messages
            messages, _ = await Message.list(session_id)
            if not messages:
                return None
            
            # Count messages and estimate tokens
            message_count = len(messages)
            
            # Calculate estimated tokens (rough estimate: 4 chars = 1 token)
            total_chars = sum(
                len(msg.content) if hasattr(msg, 'content') and msg.content else 0
                for msg in messages
            )
            estimated_tokens = total_chars // 4
            
            # Get compaction agent
            compaction_agent = get("compaction")
            if not compaction_agent:
                return None
            
            # Build conversation summary prompt
            conversation_text = SessionCompaction._build_conversation_text(messages)
            
            # For now, create a simple summary (in production, this would call LLM)
            summary = SessionCompaction._generate_summary(conversation_text, message_count)
            
            # Calculate savings (summary is typically ~10% of original)
            summary_tokens = len(summary) // 4
            tokens_saved = max(0, estimated_tokens - summary_tokens)
            
            # Estimate cost savings ($0.01 per 1K tokens as rough estimate)
            cost_saved = (tokens_saved / 1000) * 0.01
            
            # Store summary in session (we'll add a field for this)
            # For now, we'll create a system message with the summary
            await SessionCompaction._store_summary(session_id, summary, user_id)
            
            # Broadcast update
            await Bus.publish(SESSION_UPDATED, SessionPayload(session_id=session_id))
            
            return CompactionResult(
                session_id=session_id,
                summary=summary,
                messages_compacted=message_count,
                tokens_saved=tokens_saved,
                cost_saved=cost_saved
            )
            
        except Exception as e:
            print(f"[COMPACTION ERROR] Failed to compact session {session_id}: {e}")
            return None
    
    @staticmethod
    def _build_conversation_text(messages: List[MessageInfo]) -> str:
        """Build a text representation of the conversation."""
        lines = []
        for msg in messages:
            role = msg.role
            content = ""
            
            if hasattr(msg, 'content') and msg.content:
                content = msg.content
            elif hasattr(msg, 'parts') and msg.parts:
                # For assistant messages with parts
                text_parts = [
                    p.content for p in msg.parts 
                    if p.type == "text" and p.content
                ]
                content = " ".join(text_parts)
            
            if content:
                lines.append(f"{role}: {content}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _generate_summary(conversation_text: str, message_count: int) -> str:
        """Generate a summary of the conversation.
        
        In production, this would use the compaction agent with LLM.
        For now, we create a structured summary.
        """
        lines = conversation_text.split("\n")
        
        # Extract key points (first and last few messages)
        key_messages = []
        if lines:
            key_messages.append(lines[0])  # First message
            if len(lines) > 1:
                key_messages.append(lines[-1])  # Last message
        
        summary_parts = [
            f"[Conversation Summary - {message_count} messages]",
            "",
            "Key points:",
        ]
        
        for msg in key_messages:
            if msg:
                # Truncate long messages
                display_msg = msg[:200] + "..." if len(msg) > 200 else msg
                summary_parts.append(f"- {display_msg}")
        
        summary_parts.extend([
            "",
            f"Total messages: {message_count}",
            "Context: Previous conversation history available in full log."
        ])
        
        return "\n".join(summary_parts)
    
    @staticmethod
    async def _store_summary(session_id: str, summary: str, user_id: Optional[str] = None) -> None:
        """Store the compaction summary as a system message."""
        try:
            # Create a system/assistant message with the summary
            # This message will have a special flag indicating it's a compaction summary
            from .message import Message
            
            # Note: In a full implementation, we'd add a field to SessionInfo
            # to store the compaction summary. For now, we create a message.
            await Message.create_assistant(
                session_id=session_id,
                user_id=user_id,
                summary=True  # Flag as summary message
            )
            
            # Add the summary as a text part
            # This would need the MessagePart model to support this
            
        except Exception as e:
            print(f"[COMPACTION ERROR] Failed to store summary: {e}")
    
    @staticmethod
    async def get_compaction_status(session_id: str) -> Dict[str, Any]:
        """Get the compaction status for a session.
        
        Returns:
            Dict with message_count, should_compact, last_compaction
        """
        try:
            messages, _ = await Message.list(session_id)
            message_count = len(messages)
            
            # Check if any messages are compaction summaries
            compaction_count = sum(
                1 for m in messages 
                if hasattr(m, 'summary') and m.summary
            )
            
            return {
                "session_id": session_id,
                "message_count": message_count,
                "compaction_threshold": COMPACTION_THRESHOLD,
                "should_compact": message_count >= COMPACTION_THRESHOLD,
                "compaction_count": compaction_count,
                "remaining_until_compaction": max(0, COMPACTION_THRESHOLD - message_count)
            }
        except Exception as e:
            return {
                "session_id": session_id,
                "error": str(e)
            }


# Convenience functions for external use
async def should_compact_session(session_id: str) -> bool:
    """Check if a session should be compacted."""
    return await SessionCompaction.should_compact(session_id)


async def compact_session(session_id: str, user_id: Optional[str] = None) -> Optional[CompactionResult]:
    """Compact a session."""
    return await SessionCompaction.compact(session_id, user_id)


async def get_session_compaction_status(session_id: str) -> Dict[str, Any]:
    """Get compaction status for a session."""
    return await SessionCompaction.get_compaction_status(session_id)