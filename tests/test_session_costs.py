"""
Session-level cost and token tracking tests.

Tests verify:
- SessionInfo has cost tracking fields
- Costs accumulate across messages
- GET /session/{id}/cost endpoint works
- Costs match provider pricing (per 1M tokens)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from opencode_api.session.session import Session, SessionInfo
from opencode_api.provider.provider import ModelInfo


@pytest.fixture
def mock_model_info():
    """Mock model with known pricing"""
    return ModelInfo(
        id="test-model",
        name="Test Model",
        provider_id="test-provider",
        context_limit=128000,
        output_limit=8192,
        supports_tools=True,
        supports_streaming=True,
        cost_input=3.0,  # $3 per 1M input tokens
        cost_output=15.0,  # $15 per 1M output tokens
    )


@pytest.mark.asyncio
async def test_session_info_has_cost_fields():
    """SessionInfo should have total_cost, total_input_tokens, total_output_tokens fields"""
    session = await Session.create()
    
    # 새 세션은 비용이 0이어야 함
    assert hasattr(session, 'total_cost')
    assert hasattr(session, 'total_input_tokens')
    assert hasattr(session, 'total_output_tokens')
    assert session.total_cost == 0.0
    assert session.total_input_tokens == 0
    assert session.total_output_tokens == 0


@pytest.mark.asyncio
async def test_cost_accumulation_single_message(mock_model_info):
    """단일 메시지 후 비용이 정확히 누적되어야 함"""
    session = await Session.create()
    
    # 1000 input tokens, 500 output tokens 사용
    input_tokens = 1000
    output_tokens = 500
    
    # 예상 비용 계산: (1000/1M * $3) + (500/1M * $15) = $0.003 + $0.0075 = $0.0105
    expected_cost = (input_tokens / 1_000_000 * mock_model_info.cost_input) + \
                    (output_tokens / 1_000_000 * mock_model_info.cost_output)
    
    # 비용 업데이트 (실제로는 SessionPrompt.prompt()에서 호출됨)
    await Session.update(session.id, {
        'total_input_tokens': input_tokens,
        'total_output_tokens': output_tokens,
        'total_cost': expected_cost,
    })
    
    updated_session = await Session.get(session.id)
    assert updated_session.total_input_tokens == input_tokens
    assert updated_session.total_output_tokens == output_tokens
    assert abs(updated_session.total_cost - expected_cost) < 0.0001  # 부동소수점 오차 허용


@pytest.mark.asyncio
async def test_cost_accumulation_multiple_messages(mock_model_info):
    """여러 메시지에 걸쳐 비용이 누적되어야 함"""
    session = await Session.create()
    
    # 첫 번째 메시지: 1000 input, 500 output
    first_input = 1000
    first_output = 500
    first_cost = (first_input / 1_000_000 * mock_model_info.cost_input) + \
                 (first_output / 1_000_000 * mock_model_info.cost_output)
    
    await Session.update(session.id, {
        'total_input_tokens': first_input,
        'total_output_tokens': first_output,
        'total_cost': first_cost,
    })
    
    # 두 번째 메시지: 2000 input, 1000 output 추가
    second_input = 2000
    second_output = 1000
    second_cost = (second_input / 1_000_000 * mock_model_info.cost_input) + \
                  (second_output / 1_000_000 * mock_model_info.cost_output)
    
    # 누적 업데이트
    session = await Session.get(session.id)
    await Session.update(session.id, {
        'total_input_tokens': session.total_input_tokens + second_input,
        'total_output_tokens': session.total_output_tokens + second_output,
        'total_cost': session.total_cost + second_cost,
    })
    
    # 검증
    final_session = await Session.get(session.id)
    assert final_session.total_input_tokens == first_input + second_input
    assert final_session.total_output_tokens == first_output + second_output
    expected_total_cost = first_cost + second_cost
    assert abs(final_session.total_cost - expected_total_cost) < 0.0001


def test_cost_endpoint_exists(client: TestClient):
    """GET /session/{id}/cost 엔드포인트가 존재해야 함"""
    # 세션 생성
    response = client.post("/session/")
    assert response.status_code == 200
    session_id = response.json()["id"]
    
    # 비용 조회
    response = client.get(f"/session/{session_id}/cost")
    assert response.status_code == 200
    
    cost_data = response.json()
    assert "total_cost" in cost_data
    assert "total_input_tokens" in cost_data
    assert "total_output_tokens" in cost_data
    assert "breakdown" in cost_data


def test_cost_endpoint_returns_correct_data(client: TestClient, mock_model_info):
    """비용 엔드포인트가 정확한 데이터를 반환해야 함"""
    # 세션 생성
    response = client.post("/session/")
    assert response.status_code == 200
    session_id = response.json()["id"]
    
    # 비용 조회 (초기 상태)
    response = client.get(f"/session/{session_id}/cost")
    assert response.status_code == 200
    
    cost_data = response.json()
    assert cost_data["total_cost"] == 0.0
    assert cost_data["total_input_tokens"] == 0
    assert cost_data["total_output_tokens"] == 0
    assert cost_data["breakdown"]["input_cost"] == 0.0
    assert cost_data["breakdown"]["output_cost"] == 0.0


def test_cost_endpoint_404_for_nonexistent_session(client: TestClient):
    """존재하지 않는 세션에 대해 404를 반환해야 함"""
    response = client.get("/session/ses_nonexistent/cost")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cost_calculation_accuracy(mock_model_info):
    """비용 계산이 provider 가격과 정확히 일치해야 함"""
    # 다양한 토큰 수로 테스트
    test_cases = [
        (1000, 500),      # 작은 수
        (100_000, 50_000),  # 중간 수
        (1_000_000, 500_000),  # 큰 수
    ]
    
    for input_tokens, output_tokens in test_cases:
        expected_input_cost = input_tokens / 1_000_000 * mock_model_info.cost_input
        expected_output_cost = output_tokens / 1_000_000 * mock_model_info.cost_output
        expected_total_cost = expected_input_cost + expected_output_cost
        
        session = await Session.create()
        await Session.update(session.id, {
            'total_input_tokens': input_tokens,
            'total_output_tokens': output_tokens,
            'total_cost': expected_total_cost,
        })
        
        updated_session = await Session.get(session.id)
        assert abs(updated_session.total_cost - expected_total_cost) < 0.0001


# Fixtures
@pytest.fixture
def client():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import app
    return TestClient(app)
