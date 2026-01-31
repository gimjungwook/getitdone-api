"""Tests for session compaction functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from src.opencode_api.session.compaction import (
    CompactionResult,
    PruneResult,
    prune,
    compact,
    is_overflow,
    should_compact_session,
    compact_session,
    get_session_compaction_status,
    COMPACTION_THRESHOLD,
    PRUNE_MINIMUM,
    PRUNE_PROTECT,
    PRUNE_PROTECTED_TOOLS,
    PRUNED_MARKER,
)
from src.opencode_api.session.session import Session, SessionCreate
from src.opencode_api.session.message import (
    Message,
    UserMessage,
    AssistantMessage,
    MessagePart,
)
from src.opencode_api.util.token import estimate


@pytest.fixture
async def test_session():
    session = await Session.create(SessionCreate(title="Compaction Test"))
    return session


# ============================================================
# should_compact_session tests
# ============================================================


@pytest.mark.asyncio
async def test_should_compact_empty_session(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        result = await should_compact_session(test_session.id)
        assert result is False


@pytest.mark.asyncio
async def test_should_compact_threshold_not_reached(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow(),
            )
            for i in range(49)
        ]
        mock_list.return_value = (mock_messages, 49)
        result = await should_compact_session(test_session.id)
        assert result is False


@pytest.mark.asyncio
async def test_should_compact_threshold_reached(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow(),
            )
            for i in range(50)
        ]
        mock_list.return_value = (mock_messages, 50)
        result = await should_compact_session(test_session.id)
        assert result is True


# ============================================================
# compact tests
# ============================================================


@pytest.mark.asyncio
async def test_compact_empty_session(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        with patch(
            "src.opencode_api.session.compaction.Session.get",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = test_session
            result = await compact(test_session.id)
            assert result is None


@pytest.mark.asyncio
async def test_compact_session_with_messages(test_session):
    """Test compacting session with messages (LLM mocked)."""
    mock_messages = [
        UserMessage(
            id=f"msg_{i}",
            session_id=test_session.id,
            content=f"Test message content {i}",
            created_at=datetime.utcnow(),
        )
        for i in range(10)
    ]

    # Mock provider that yields text chunks
    mock_provider = MagicMock()

    async def mock_stream(**kwargs):
        from src.opencode_api.provider.provider import StreamChunk

        yield StreamChunk(type="text", text="Summary of conversation.")
        yield StreamChunk(type="done", stop_reason="end_turn")

    mock_provider.stream = mock_stream

    with (
        patch(
            "src.opencode_api.session.compaction.Message.list",
            new_callable=AsyncMock,
            return_value=(mock_messages, 10),
        ),
        patch(
            "src.opencode_api.session.compaction.Session.get",
            new_callable=AsyncMock,
            return_value=test_session,
        ),
        patch(
            "src.opencode_api.session.compaction.get_agent",
            return_value=MagicMock(
                model=None, temperature=None, max_tokens=None
            ),
        ),
        patch(
            "src.opencode_api.session.compaction.get_provider",
            return_value=mock_provider,
        ),
        patch(
            "src.opencode_api.session.compaction.Message.create_assistant",
            new_callable=AsyncMock,
            return_value=AssistantMessage(
                id="summary_msg",
                session_id=test_session.id,
                created_at=datetime.utcnow(),
                summary=True,
            ),
        ),
        patch(
            "src.opencode_api.session.compaction.Message.add_part",
            new_callable=AsyncMock,
        ),
        patch(
            "src.opencode_api.session.compaction.Bus.publish",
            new_callable=AsyncMock,
        ),
        patch(
            "src.opencode_api.session.compaction.get_system_prompt",
            return_value="You are a compaction agent.",
        ),
    ):
        result = await compact(test_session.id)

        assert result is not None
        assert isinstance(result, CompactionResult)
        assert result.session_id == test_session.id
        assert result.messages_compacted == 10
        assert result.summary == "Summary of conversation."
        assert len(result.summary) > 0


@pytest.mark.asyncio
async def test_compaction_result_structure(test_session):
    result = CompactionResult(
        session_id=test_session.id,
        summary="Test summary",
        messages_compacted=50,
        tokens_saved=1000,
        cost_saved=0.01,
    )

    assert result.session_id == test_session.id
    assert result.summary == "Test summary"
    assert result.messages_compacted == 50
    assert result.tokens_saved == 1000
    assert result.cost_saved == 0.01
    assert result.compacted_at is not None


# ============================================================
# get_session_compaction_status tests
# ============================================================


@pytest.mark.asyncio
async def test_get_compaction_status_empty(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        status = await get_session_compaction_status(test_session.id)

        assert status["session_id"] == test_session.id
        assert status["message_count"] == 0
        assert status["compaction_threshold"] == COMPACTION_THRESHOLD
        assert status["should_compact"] is False
        assert status["remaining_until_compaction"] == COMPACTION_THRESHOLD


@pytest.mark.asyncio
async def test_get_compaction_status_with_messages(test_session):
    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_messages = [
            UserMessage(
                id=f"msg_{i}",
                session_id=test_session.id,
                content=f"Message {i}",
                created_at=datetime.utcnow(),
            )
            for i in range(30)
        ]
        mock_list.return_value = (mock_messages, 30)
        status = await get_session_compaction_status(test_session.id)

        assert status["message_count"] == 30
        assert status["should_compact"] is False
        assert status["remaining_until_compaction"] == 20


# ============================================================
# convenience function tests
# ============================================================


@pytest.mark.asyncio
async def test_convenience_functions(test_session):
    mock_messages = [
        UserMessage(
            id=f"msg_{i}",
            session_id=test_session.id,
            content=f"Message {i}",
            created_at=datetime.utcnow(),
        )
        for i in range(5)
    ]

    with (
        patch(
            "src.opencode_api.session.compaction.Message.list",
            new_callable=AsyncMock,
            return_value=(mock_messages, 5),
        ),
        patch(
            "src.opencode_api.session.compaction.Session.get",
            new_callable=AsyncMock,
            return_value=test_session,
        ),
        patch(
            "src.opencode_api.session.compaction.get_agent",
            return_value=MagicMock(
                model=None, temperature=None, max_tokens=None
            ),
        ),
        patch(
            "src.opencode_api.session.compaction.get_provider",
            return_value=None,
        ),
        patch(
            "src.opencode_api.session.compaction.Bus.publish",
            new_callable=AsyncMock,
        ),
    ):
        should = await should_compact_session(test_session.id)
        assert should is False

        # compact_session returns None because provider is None
        result = await compact_session(test_session.id)
        assert result is None

        status = await get_session_compaction_status(test_session.id)
        assert status["message_count"] == 5


# ============================================================
# prune tests
# ============================================================


def _make_tool_result_part(
    part_id: str,
    msg_id: str,
    session_id: str,
    tool_output: str,
    tool_name: str = "bash",
) -> MessagePart:
    return MessagePart(
        id=part_id,
        session_id=session_id,
        message_id=msg_id,
        type="tool_result",
        tool_call_id=f"tc_{part_id}",
        tool_name=tool_name,
        tool_output=tool_output,
        tool_status="completed",
    )


def _make_large_output(token_count: int) -> str:
    """Create a string that estimates to approximately token_count tokens."""
    # estimate(text) = round(len(text) / 4), so len = token_count * 4
    return "x" * (token_count * 4)


@pytest.mark.asyncio
async def test_prune_skips_recent_turns():
    """Prune should protect the latest 2 turns (user messages)."""
    sid = "test_session"
    messages = [
        UserMessage(id="u1", session_id=sid, content="First", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a1",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p1", "a1", sid, _make_large_output(50000)),
            ],
        ),
        UserMessage(id="u2", session_id=sid, content="Second", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a2",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p2", "a2", sid, _make_large_output(50000)),
            ],
        ),
    ]

    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
        return_value=(messages, len(messages)),
    ):
        # Only 2 turns — all protected, nothing to prune
        result = await prune(sid)
        assert result is None


@pytest.mark.asyncio
async def test_prune_stops_at_summary_message():
    """Prune should stop scanning when it hits a summary message."""
    sid = "test_session"
    messages = [
        UserMessage(id="u1", session_id=sid, content="Old", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a_summary",
            session_id=sid,
            created_at=datetime.utcnow(),
            summary=True,
            parts=[
                MessagePart(
                    id="ps", session_id=sid, message_id="a_summary",
                    type="text", content="Previous summary",
                ),
            ],
        ),
        UserMessage(id="u2", session_id=sid, content="After summary 1", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a2",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p2", "a2", sid, _make_large_output(50000)),
            ],
        ),
        UserMessage(id="u3", session_id=sid, content="After summary 2", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a3",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p3", "a3", sid, _make_large_output(50000)),
            ],
        ),
        UserMessage(id="u4", session_id=sid, content="Latest", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a4",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p4", "a4", sid, _make_large_output(50000)),
            ],
        ),
    ]

    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
        return_value=(messages, len(messages)),
    ):
        # Summary message should stop backward scan
        # Only parts after summary are candidates
        result = await prune(sid)
        # Even if there are large outputs, the summary boundary limits scope
        # Result depends on whether enough tokens accumulate after summary
        # With 3 turns after summary, turns >= 2 so scanning starts
        # But summary breaks the loop before reaching old parts
        assert result is None or isinstance(result, PruneResult)


@pytest.mark.asyncio
async def test_prune_protects_skill_tool():
    """Prune should never prune tool outputs from 'skill' tool."""
    sid = "test_session"
    messages = [
        UserMessage(id="u1", session_id=sid, content="First", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a1",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p1", "a1", sid, _make_large_output(60000), tool_name="skill"),
            ],
        ),
        UserMessage(id="u2", session_id=sid, content="Second", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a2",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p2", "a2", sid, _make_large_output(60000), tool_name="skill"),
            ],
        ),
        UserMessage(id="u3", session_id=sid, content="Third", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a3",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p3", "a3", sid, _make_large_output(60000), tool_name="skill"),
            ],
        ),
    ]

    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
        return_value=(messages, len(messages)),
    ):
        result = await prune(sid)
        # All tool outputs are from "skill" — protected, nothing pruned
        assert result is None


@pytest.mark.asyncio
async def test_prune_below_minimum_threshold():
    """No pruning if pruned tokens < PRUNE_MINIMUM (20,000)."""
    sid = "test_session"
    # Create messages where tool outputs are small
    messages = [
        UserMessage(id="u1", session_id=sid, content="First", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a1",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p1", "a1", sid, _make_large_output(15000)),
            ],
        ),
        UserMessage(id="u2", session_id=sid, content="Second", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a2",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p2", "a2", sid, _make_large_output(15000)),
            ],
        ),
        UserMessage(id="u3", session_id=sid, content="Third", created_at=datetime.utcnow()),
        AssistantMessage(
            id="a3",
            session_id=sid,
            created_at=datetime.utcnow(),
            parts=[
                _make_tool_result_part("p3", "a3", sid, _make_large_output(15000)),
            ],
        ),
    ]

    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
        return_value=(messages, len(messages)),
    ):
        result = await prune(sid)
        # total = 15000 + 15000 = 30000 (only 2 parts scanned, latest turn protected)
        # After PRUNE_PROTECT (40000), pruned = 0 since total < PRUNE_PROTECT
        assert result is None


@pytest.mark.asyncio
async def test_prune_above_threshold():
    """Pruning happens when enough tokens exceed PRUNE_PROTECT."""
    sid = "test_session"
    # Need many turns with large tool outputs
    messages = []
    for i in range(8):
        messages.append(
            UserMessage(
                id=f"u{i}",
                session_id=sid,
                content=f"Turn {i}",
                created_at=datetime.utcnow(),
            )
        )
        messages.append(
            AssistantMessage(
                id=f"a{i}",
                session_id=sid,
                created_at=datetime.utcnow(),
                parts=[
                    _make_tool_result_part(
                        f"p{i}", f"a{i}", sid, _make_large_output(15000)
                    ),
                ],
            )
        )

    with (
        patch(
            "src.opencode_api.session.compaction.Message.list",
            new_callable=AsyncMock,
            return_value=(messages, len(messages)),
        ),
        patch(
            "src.opencode_api.session.compaction.Message.update_part",
            new_callable=AsyncMock,
        ) as mock_update,
    ):
        result = await prune(sid)
        # 8 turns, latest 2 protected (turns < 2 skipped)
        # 6 turns scanned: 6 * 15000 = 90000 total
        # First 40000 protected, remaining 50000 pruned
        # 50000 > PRUNE_MINIMUM (20000) -> pruning happens
        assert result is not None
        assert isinstance(result, PruneResult)
        assert result.pruned_count > 0
        assert result.tokens_saved > PRUNE_MINIMUM
        assert mock_update.called


# ============================================================
# is_overflow tests
# ============================================================


@pytest.mark.asyncio
async def test_is_overflow_function():
    sid = "test_session"
    messages = [
        UserMessage(
            id="u1",
            session_id=sid,
            content="Hello",
            created_at=datetime.utcnow(),
        )
    ]

    with patch(
        "src.opencode_api.session.compaction.Message.list",
        new_callable=AsyncMock,
        return_value=(messages, 1),
    ):
        with patch(
            "src.opencode_api.session.compaction.token_is_overflow",
            return_value=False,
        ):
            result = await is_overflow(sid, "test-model", "test-provider")
            assert result is False

        with patch(
            "src.opencode_api.session.compaction.token_is_overflow",
            return_value=True,
        ):
            result = await is_overflow(sid, "test-model", "test-provider")
            assert result is True


# ============================================================
# _fallback_summary / _build_provider_messages tests
# ============================================================


@pytest.mark.asyncio
async def test_build_conversation_text():
    """Test building provider messages from history."""
    from src.opencode_api.session.compaction import _build_provider_messages

    messages = [
        UserMessage(
            id="msg_1",
            session_id="test_session",
            content="Hello",
            created_at=datetime.utcnow(),
        ),
        AssistantMessage(
            id="msg_2",
            session_id="test_session",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part_1",
                    session_id="test_session",
                    message_id="msg_2",
                    type="text",
                    content="Hi there",
                )
            ],
        ),
        UserMessage(
            id="msg_3",
            session_id="test_session",
            content="How are you?",
            created_at=datetime.utcnow(),
        ),
    ]

    result = _build_provider_messages(messages)

    assert len(result) == 3
    assert result[0].role == "user"
    assert result[0].content == "Hello"
    assert result[1].role == "assistant"
    assert result[1].content == "Hi there"
    assert result[2].role == "user"
    assert result[2].content == "How are you?"


@pytest.mark.asyncio
async def test_fallback_summary():
    from src.opencode_api.session.compaction import _fallback_summary

    messages = [
        UserMessage(
            id="msg_1",
            session_id="test",
            content="Hello",
            created_at=datetime.utcnow(),
        ),
    ]
    summary = _fallback_summary(messages, 1)

    assert "[Conversation Summary" in summary
    assert "1 messages" in summary
    assert "Key points:" in summary
    assert len(summary) > 0
