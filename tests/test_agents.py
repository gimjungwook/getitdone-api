"""
Tests for agent module - verify plan agent removal.
"""

import pytest
from src.opencode_api.agent import agent


class TestAgentList:
    """Test agent listing and availability."""
    
    def test_plan_agent_not_in_default_agents(self):
        """Plan agent should not be in DEFAULT_AGENTS."""
        assert "plan" not in agent.DEFAULT_AGENTS, "Plan agent should be removed from DEFAULT_AGENTS"
    
    def test_plan_agent_not_retrievable(self):
        """GET /agent/plan should return None."""
        result = agent.get("plan")
        assert result is None, "Plan agent should not be retrievable via get()"
    
    def test_plan_agent_not_in_list(self):
        """Plan agent should not appear in list_agents()."""
        agents = agent.list_agents()
        agent_ids = [a.id for a in agents]
        assert "plan" not in agent_ids, "Plan agent should not appear in list_agents()"
    
    def test_required_agents_exist(self):
        """Verify required agents still exist."""
        required_agents = {"build", "general", "explore"}
        agents = agent.list_agents()
        agent_ids = {a.id for a in agents}
        
        for required in required_agents:
            assert required in agent_ids, f"Required agent '{required}' is missing"
    
    def test_build_agent_is_default(self):
        """Build agent should be the default agent."""
        default = agent.default_agent()
        assert default.id == "build", "Default agent should be 'build'"
    
    def test_agent_count_reduced(self):
        """Agent count should be 3 (build, general, explore) after plan removal."""
        agents = agent.list_agents()
        assert len(agents) == 3, f"Expected 3 agents, got {len(agents)}"
