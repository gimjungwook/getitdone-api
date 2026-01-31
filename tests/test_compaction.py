"""Tests for session compaction functionality."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.opencode_api.session.compaction import (
    SessionCompaction,
    CompactionResult,
    should_compact_session,
    compact_session,
    get_session_compaction_status,
    COMPACTION_THRESHOLD
)
from src.opencode_api.session.session import Session, SessionCreate
from src.opencode_api.session.message import Message, UserMessage, AssistantMessage, MessagePart


@pytest.fixture
async def test_session():
    """Create a test session (in-memory, no Supabase)."""
    session = await Session.create(
        SessionCreate(title="Compaction Test")
        # No user_id - uses in-memory storage
    )
    return session


@pytest.mark.asyncio
async def test_should_compact_empty_session(test_session):
    """Test that empty session should not be compacted."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        result = await SessionCompaction.should_compact(test_session.id)
        assert result is False


@pytest.mark.asyncio
async def test_should_compact_threshold_not_reached(test_session):
    """Test session with less than 50 messages should not be compacted."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow()
            )
            for i in range(49)
        ]
        mock_list.return_value = mock_messages
        result = await SessionCompaction.should_compact(test_session.id)
        assert result is False


@pytest.mark.asyncio
async def test_should_compact_threshold_reached(test_session):
    """Test session with 50+ messages should be compacted."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow()
            )
            for i in range(50)
        ]
        mock_list.return_value = (mock_messages, 50)
        result = await SessionCompaction.should_compact(test_session.id)
        assert result is True


@pytest.mark.asyncio
async def test_compact_empty_session(test_session):
    """Test compacting empty session returns None."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([], 0)
        with patch('src.opencode_api.session.compaction.Session.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_session
            result = await SessionCompaction.compact(test_session.id)
            assert result is None


@pytest.mark.asyncio
async def test_compact_session_with_messages(test_session):
    """Test compacting session with messages."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        with patch('src.opencode_api.session.compaction.Session.get', new_callable=AsyncMock) as mock_get:
            with patch('src.opencode_api.session.compaction.SessionCompaction._store_summary', new_callable=AsyncMock):
                with patch('src.opencode_api.session.compaction.SessionPayload') as mock_payload:
                    with patch('src.opencode_api.session.compaction.Bus.publish', new_callable=AsyncMock):
                        with patch('src.opencode_api.session.compaction.get') as mock_agent_get:
                            mock_messages = [
                                UserMessage(
                                    id=f"msg_{i}",
                                    session_id=test_session.id,
                                    content=f"Test message content {i}",
                                    created_at=datetime.utcnow()
                                )
                                for i in range(10)
                            ]
                            mock_list.return_value = (mock_messages, 10)
                            mock_get.return_value = test_session
                            mock_payload.return_value = MagicMock()
                            mock_agent_get.return_value = MagicMock()
                            
                            result = await SessionCompaction.compact(test_session.id)
                            
                            assert result is not None
                            assert isinstance(result, CompactionResult)
                            assert result.session_id == test_session.id
                            assert result.messages_compacted == 10
                            assert result.summary is not None
                            assert len(result.summary) > 0


@pytest.mark.asyncio
async def test_compaction_result_structure(test_session):
    """Test CompactionResult has all required fields."""
    result = CompactionResult(
        session_id=test_session.id,
        summary="Test summary",
        messages_compacted=50,
        tokens_saved=1000,
        cost_saved=0.01
    )
    
    assert result.session_id == test_session.id
    assert result.summary == "Test summary"
    assert result.messages_compacted == 50
    assert result.tokens_saved == 1000
    assert result.cost_saved == 0.01
    assert result.compacted_at is not None


@pytest.mark.asyncio
async def test_get_compaction_status_empty(test_session):
    """Test compaction status for empty session."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = ([], 0)
        status = await SessionCompaction.get_compaction_status(test_session.id)
        
        assert status["session_id"] == test_session.id
        assert status["message_count"] == 0
        assert status["compaction_threshold"] == COMPACTION_THRESHOLD
        assert status["should_compact"] is False
        assert status["remaining_until_compaction"] == COMPACTION_THRESHOLD


@pytest.mark.asyncio
async def test_get_compaction_status_with_messages(test_session):
    """Test compaction status with messages."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow()
            )
            for i in range(30)
        ]
        mock_list.return_value = (mock_messages, 30)
        status = await SessionCompaction.get_compaction_status(test_session.id)
        
        assert status["message_count"] == 30
        assert status["should_compact"] is False
        assert status["remaining_until_compaction"] == 20


@pytest.mark.asyncio
async def test_convenience_functions(test_session):
    """Test convenience wrapper functions."""
    with patch('src.opencode_api.session.compaction.Message.list', new_callable=AsyncMock) as mock_list:
        with patch('src.opencode_api.session.compaction.Session.get', new_callable=AsyncMock) as mock_get:
            with patch('src.opencode_api.session.compaction.SessionCompaction._store_summary', new_callable=AsyncMock):
                with patch('src.opencode_api.session.compaction.SessionPayload') as mock_payload:
                    with patch('src.opencode_api.session.compaction.Bus.publish', new_callable=AsyncMock):
                        with patch('src.opencode_api.session.compaction.get') as mock_agent_get:
                            mock_messages = [
                                UserMessage(
                                    id=f"msg_{i}",
                                    session_id=test_session.id,
                                    content=f"Message {i}",
                                    created_at=datetime.utcnow()
                                )
                                for i in range(5)
                            ]
                            mock_list.return_value = (mock_messages, 5)
                            mock_get.return_value = test_session
                            mock_payload.return_value = MagicMock()
                            mock_agent_get.return_value = MagicMock()
                            
                            should_compact = await should_compact_session(test_session.id)
                            assert should_compact is False
                            
                            result = await compact_session(test_session.id)
                            assert result is not None
                            
                            status = await get_session_compaction_status(test_session.id)
                            assert status["message_count"] == 5


@pytest.mark.asyncio
async def test_build_conversation_text():
    """Test building conversation text from messages."""
    messages = [
        UserMessage(
            id="msg_1",
            session_id="test_session",
            content="Hello",
            created_at=datetime.utcnow()
        ),
        AssistantMessage(
            id="msg_2",
            session_id="test_session",
            created_at=datetime.utcnow(),
            parts=[MessagePart(
                id="part_1",
                session_id="test_session",
                message_id="msg_2",
                type="text",
                content="Hi there"
            )]
        ),
        UserMessage(
            id="msg_3",
            session_id="test_session",
            content="How are you?",
            created_at=datetime.utcnow()
        )
    ]
    
    text = SessionCompaction._build_conversation_text(messages)
    
    assert "user: Hello" in text
    assert "assistant: Hi there" in text
    assert "user: How are you?" in text


@pytest.mark.asyncio
async def test_generate_summary():
    """Test summary generation."""
    conversation = "user: Hello\nassistant: Hi\nuser: Question"
    summary = SessionCompaction._generate_summary(conversation, 3)
    
    assert "[Conversation Summary" in summary
    assert "3 messages" in summary
    assert "Key points:" in summary
    assert len(summary) > 0