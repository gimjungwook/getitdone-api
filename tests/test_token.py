import pytest
from datetime import datetime

from src.opencode_api.util.token import estimate, count_messages, is_overflow, TokenInfo
from src.opencode_api.session.message import UserMessage, AssistantMessage, MessagePart
from src.opencode_api.provider.provider import ModelInfo, register_provider
from src.opencode_api.provider.litellm import LiteLLMProvider


@pytest.fixture
def setup_provider():
    provider = LiteLLMProvider()
    register_provider(provider)
    yield
    

def test_estimate_simple():
    assert estimate("hello world") == 3
    assert estimate("") == 0
    assert estimate("a" * 4) == 1
    assert estimate("a" * 8) == 2
    assert estimate("a" * 10) == 2
    assert estimate("a" * 12) == 3


def test_estimate_korean():
    text = "안녕하세요"
    result = estimate(text)
    assert result > 0


def test_count_messages_user_only():
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content="hello world",
            created_at=datetime.utcnow()
        )
    ]
    
    info = count_messages(messages)
    assert info.input_tokens == 3
    assert info.output_tokens == 0
    assert info.total == 3


def test_count_messages_assistant_text():
    messages = [
        AssistantMessage(
            id="msg1",
            session_id="sess1",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part1",
                    session_id="sess1",
                    message_id="msg1",
                    type="text",
                    content="hello world"
                )
            ]
        )
    ]
    
    info = count_messages(messages)
    assert info.input_tokens == 0
    assert info.output_tokens == 3
    assert info.total == 3


def test_count_messages_mixed():
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content="what is 2+2?",
            created_at=datetime.utcnow()
        ),
        AssistantMessage(
            id="msg2",
            session_id="sess1",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part1",
                    session_id="sess1",
                    message_id="msg2",
                    type="text",
                    content="The answer is 4"
                )
            ]
        )
    ]
    
    info = count_messages(messages)
    assert info.input_tokens == 3
    assert info.output_tokens == 4
    assert info.total == 7


def test_count_messages_with_reasoning():
    messages = [
        AssistantMessage(
            id="msg1",
            session_id="sess1",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part1",
                    session_id="sess1",
                    message_id="msg1",
                    type="reasoning",
                    content="Let me think about this..."
                ),
                MessagePart(
                    id="part2",
                    session_id="sess1",
                    message_id="msg1",
                    type="text",
                    content="The answer is 42"
                )
            ]
        )
    ]
    
    info = count_messages(messages)
    assert info.output_tokens > 0


def test_count_messages_with_tool_call():
    messages = [
        AssistantMessage(
            id="msg1",
            session_id="sess1",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part1",
                    session_id="sess1",
                    message_id="msg1",
                    type="tool_call",
                    tool_call_id="call1",
                    tool_name="web_search",
                    tool_args={"query": "python"}
                )
            ]
        )
    ]
    
    info = count_messages(messages)
    assert info.output_tokens > 0


def test_count_messages_with_tool_result():
    messages = [
        AssistantMessage(
            id="msg1",
            session_id="sess1",
            created_at=datetime.utcnow(),
            parts=[
                MessagePart(
                    id="part1",
                    session_id="sess1",
                    message_id="msg1",
                    type="tool_result",
                    tool_output="Search results: Python is a programming language"
                )
            ]
        )
    ]
    
    info = count_messages(messages)
    assert info.input_tokens > 0


def test_is_overflow_no_overflow(setup_provider):
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content="hello",
            created_at=datetime.utcnow()
        )
    ]
    
    result = is_overflow(messages, "zai/glm-4.7-flash", "zai")
    assert result is False


def test_is_overflow_with_overflow(setup_provider):
    long_content = "a" * 500000
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content=long_content,
            created_at=datetime.utcnow()
        )
    ]
    
    result = is_overflow(messages, "zai/glm-4.7-flash", "zai")
    assert result is True


def test_is_overflow_unknown_model():
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content="hello",
            created_at=datetime.utcnow()
        )
    ]
    
    result = is_overflow(messages, "unknown-model", "unknown-provider")
    assert result is False


def test_is_overflow_zero_context_limit(setup_provider):
    from src.opencode_api.provider.provider import get_provider
    
    provider = get_provider("zai")
    if provider:
        provider.add_model(ModelInfo(
            id="zai/test-unlimited",
            name="Test Unlimited",
            provider_id="zai",
            context_limit=0,
            output_limit=8192
        ))
    
    messages = [
        UserMessage(
            id="msg1",
            session_id="sess1",
            content="a" * 1000000,
            created_at=datetime.utcnow()
        )
    ]
    
    result = is_overflow(messages, "zai/test-unlimited", "zai")
    assert result is False
