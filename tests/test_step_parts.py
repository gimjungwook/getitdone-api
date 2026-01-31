"""
Tests for step_start and step_finish message parts.

Following TDD approach:
1. RED: Write failing tests
2. GREEN: Implement to pass
3. REFACTOR: Clean code
"""

import pytest
from datetime import datetime
from src.opencode_api.session.message import Message, MessagePart, AssistantMessage


@pytest.mark.asyncio
async def test_step_start_part_creation():
    """Test creating a step_start part with step number and max_steps."""
    # Create assistant message
    session_id = "test_session_001"
    msg = await Message.create_assistant(
        session_id=session_id,
        provider_id="anthropic",
        model="claude-sonnet-4"
    )
    
    # Create step_start part
    step_start = MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_start",
        step_number=1,
        max_steps=5
    )
    
    # Add part to message
    added_part = await Message.add_part(msg.id, session_id, step_start)
    
    # Verify
    assert added_part.type == "step_start"
    assert added_part.step_number == 1
    assert added_part.max_steps == 5
    assert added_part.id != ""


@pytest.mark.asyncio
async def test_step_finish_part_with_cost_and_tokens():
    """Test creating a step_finish part with cost, tokens, and stop_reason."""
    # Create assistant message
    session_id = "test_session_002"
    msg = await Message.create_assistant(
        session_id=session_id,
        provider_id="anthropic",
        model="claude-sonnet-4"
    )
    
    # Create step_finish part
    step_finish = MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_finish",
        step_number=1,
        max_steps=5,
        input_tokens=1000,
        output_tokens=500,
        cost=0.0045,  # Example cost
        stop_reason="end_turn"
    )
    
    # Add part to message
    added_part = await Message.add_part(msg.id, session_id, step_finish)
    
    # Verify
    assert added_part.type == "step_finish"
    assert added_part.step_number == 1
    assert added_part.max_steps == 5
    assert added_part.input_tokens == 1000
    assert added_part.output_tokens == 500
    assert added_part.cost == 0.0045
    assert added_part.stop_reason == "end_turn"


@pytest.mark.asyncio
async def test_step_parts_in_message_list():
    """Test that step parts are included when listing messages."""
    import time
    session_id = f"test_session_003_{int(time.time() * 1000)}"
    
    msg = await Message.create_assistant(
        session_id=session_id,
        provider_id="anthropic",
        model="claude-sonnet-4"
    )
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_start",
        step_number=1,
        max_steps=3
    ))
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="text",
        content="Processing step 1..."
    ))
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_finish",
        step_number=1,
        max_steps=3,
        input_tokens=500,
        output_tokens=200,
        cost=0.0021,
        stop_reason="end_turn"
    ))
    
    messages = await Message.list(session_id)
    
    assert len(messages) == 1
    assert isinstance(messages[0], AssistantMessage)
    assert len(messages[0].parts) == 3
    
    step_start = messages[0].parts[0]
    assert step_start.type == "step_start"
    assert step_start.step_number == 1
    
    text_part = messages[0].parts[1]
    assert text_part.type == "text"
    
    step_finish = messages[0].parts[2]
    assert step_finish.type == "step_finish"
    assert step_finish.cost == 0.0021


@pytest.mark.asyncio
async def test_step_parts_persistence():
    """Test that step parts are correctly persisted and retrieved."""
    session_id = "test_session_004"
    
    # Create message with step parts
    msg = await Message.create_assistant(
        session_id=session_id,
        provider_id="anthropic",
        model="claude-sonnet-4"
    )
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_start",
        step_number=2,
        max_steps=10
    ))
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="step_finish",
        step_number=2,
        max_steps=10,
        input_tokens=2000,
        output_tokens=1000,
        cost=0.009,
        stop_reason="tool_use"
    ))
    
    # Retrieve message
    retrieved = await Message.get(session_id, msg.id)
    
    # Verify persistence
    assert isinstance(retrieved, AssistantMessage)
    assert len(retrieved.parts) == 2
    
    start = retrieved.parts[0]
    assert start.type == "step_start"
    assert start.step_number == 2
    assert start.max_steps == 10
    
    finish = retrieved.parts[1]
    assert finish.type == "step_finish"
    assert finish.step_number == 2
    assert finish.input_tokens == 2000
    assert finish.output_tokens == 1000
    assert finish.cost == 0.009
    assert finish.stop_reason == "tool_use"


@pytest.mark.asyncio
async def test_existing_part_types_still_work():
    """Ensure existing part types (text, reasoning, tool_call, tool_result) still work."""
    session_id = "test_session_005"
    
    msg = await Message.create_assistant(
        session_id=session_id,
        provider_id="anthropic",
        model="claude-sonnet-4"
    )
    
    # Add existing part types
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="text",
        content="Hello world"
    ))
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="reasoning",
        content="Let me think..."
    ))
    
    await Message.add_part(msg.id, session_id, MessagePart(
        id="",
        session_id=session_id,
        message_id=msg.id,
        type="tool_call",
        tool_call_id="call_123",
        tool_name="web_search",
        tool_args={"query": "test"},
        tool_status="completed"
    ))
    
    # Retrieve and verify
    retrieved = await Message.get(session_id, msg.id)
    assert len(retrieved.parts) == 3
    assert retrieved.parts[0].type == "text"
    assert retrieved.parts[1].type == "reasoning"
    assert retrieved.parts[2].type == "tool_call"
