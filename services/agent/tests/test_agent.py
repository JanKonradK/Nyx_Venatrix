import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent_logic import DeepApplyAgent

@pytest.fixture
def mock_kb():
    """Mock knowledge base."""
    kb = Mock()
    kb.search_relevant_info = Mock(return_value=["Mock bio info", "Mock experience"])
    return kb

@pytest.fixture
def agent(mock_kb):
    """Create agent instance with mocked dependencies."""
    with patch.dict(os.environ, {'GROK_API_KEY': 'test_key', 'MODEL_NAME': 'grok-beta'}):
        return DeepApplyAgent(kb=mock_kb)

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test that agent initializes correctly."""
    assert agent.llm is not None
    assert agent.kb is not None

@pytest.mark.asyncio
async def test_agent_returns_cost_data(agent):
    """Test that agent returns cost tracking data."""
    with patch('src.agent_logic.Agent') as MockAgent:
        mock_agent_instance = AsyncMock()
        mock_history = Mock()
        mock_history.final_result = Mock(return_value="Application submitted successfully")
        mock_agent_instance.run = AsyncMock(return_value=mock_history)
        MockAgent.return_value = mock_agent_instance

        result = await agent.run("https://example.com/job")

        assert 'cost_usd' in result
        assert 'tokens_input' in result
        assert 'tokens_output' in result
        assert isinstance(result['cost_usd'], (int, float))

@pytest.mark.asyncio
async def test_agent_error_handling(agent):
    """Test that agent handles errors gracefully."""
    with patch('src.agent_logic.Agent') as MockAgent:
        MockAgent.return_value.run = AsyncMock(side_effect=Exception("Test error"))

        result = await agent.run("https://example.com/job")

        assert 'error' in result
        assert result['cost_usd'] == 0
        assert result['tokens_input'] == 0
        assert result['tokens_output'] == 0

@pytest.mark.asyncio
async def test_cost_calculation_consistency(agent):
    """Test that cost calculations are consistent."""
    with patch('src.agent_logic.Agent') as MockAgent:
        mock_agent_instance = AsyncMock()
        mock_history = Mock()
        mock_history.final_result = Mock(return_value="Success")
        mock_agent_instance.run = AsyncMock(return_value=mock_history)
        MockAgent.return_value = mock_agent_instance

        results = []
        for _ in range(5):
            result = await agent.run("https://example.com/job")
            results.append(result)

        # All should return cost data
        for result in results:
            assert 'cost_usd' in result
            assert result['cost_usd'] >= 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
