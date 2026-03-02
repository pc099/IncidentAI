"""
Property-Based Tests for Agent Execution Sequence

Property 19: Agent Execution Sequence
Validates: Requirements 6.1

Tests that agents are invoked in the correct sequence:
Log Analysis → Root Cause → Fix Recommendation → Communication
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.orchestrator.agent_orchestrator import StrandsOrchestrator, AgentResult


# Strategy for generating incident data
@st.composite
def incident_data_strategy(draw):
    """Generate valid incident data for testing"""
    return {
        "incident_id": f"inc-{draw(st.integers(min_value=1000, max_value=9999))}",
        "service_name": draw(st.sampled_from([
            "payment-processor",
            "user-service",
            "api-gateway",
            "database-service"
        ])),
        "timestamp": datetime.now().isoformat(),
        "error_message": draw(st.text(min_size=10, max_size=100)),
        "log_location": f"s3://logs/service/{draw(st.text(min_size=5, max_size=20))}"
    }


class TestAgentExecutionSequenceProperties:
    """
    Property 19: Agent Execution Sequence
    
    PROPERTY: WHEN an incident is triggered, agents SHALL be invoked in sequence:
    Log Analysis → Root Cause → Fix Recommendation → Communication
    
    Validates: Requirement 6.1
    """
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_agents_invoked_in_correct_sequence(self, incident_data):
        """
        Property: Agents must be invoked in the correct order
        
        Given any incident data
        When the orchestrator processes the incident
        Then agents must be invoked in sequence: log-analysis, root-cause, 
             fix-recommendation, communication
        """
        orchestrator = StrandsOrchestrator()
        
        # Track agent invocation order
        invocation_order = []
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            invocation_order.append(agent_name)
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        # Mock the agent invocation
        with patch.object(
            orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            try:
                orchestrator.handle_incident(incident_data)
            except Exception:
                pass  # Ignore errors, we're only testing sequence
        
        # Verify sequence
        expected_sequence = ["log-analysis", "root-cause", "fix-recommendation", "communication"]
        
        # Property: Invocation order must match expected sequence
        assert invocation_order == expected_sequence, (
            f"Agents invoked in wrong order. "
            f"Expected: {expected_sequence}, Got: {invocation_order}"
        )
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_all_agents_invoked_even_on_partial_failure(self, incident_data):
        """
        Property: All agents must be invoked even if earlier agents fail
        
        Given any incident data
        When an earlier agent fails
        Then subsequent agents must still be invoked
        """
        orchestrator = StrandsOrchestrator()
        
        invocation_order = []
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            invocation_order.append(agent_name)
            # Make log-analysis fail
            if agent_name == "log-analysis":
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error="Simulated failure",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            try:
                orchestrator.handle_incident(incident_data)
            except Exception:
                pass
        
        # Property: All 4 agents must be invoked despite failure
        assert len(invocation_order) == 4, (
            f"Not all agents were invoked. Got: {invocation_order}"
        )
        
        # Property: Sequence must still be correct
        expected_sequence = ["log-analysis", "root-cause", "fix-recommendation", "communication"]
        assert invocation_order == expected_sequence
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_agent_sequence_matches_config(self, incident_data):
        """
        Property: Agent invocation sequence must match AgentCore config
        
        Given any incident data
        When the orchestrator processes the incident
        Then the invocation sequence must match config.agent_sequence
        """
        orchestrator = StrandsOrchestrator()
        
        invocation_order = []
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            invocation_order.append(agent_name)
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            try:
                orchestrator.handle_incident(incident_data)
            except Exception:
                pass
        
        # Property: Invocation order must match config
        assert invocation_order == orchestrator.config.agent_sequence, (
            f"Invocation order doesn't match config. "
            f"Config: {orchestrator.config.agent_sequence}, "
            f"Actual: {invocation_order}"
        )
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_no_agent_invoked_twice(self, incident_data):
        """
        Property: Each agent must be invoked exactly once per incident
        
        Given any incident data
        When the orchestrator processes the incident
        Then each agent must be invoked exactly once (no duplicates)
        """
        orchestrator = StrandsOrchestrator()
        
        invocation_order = []
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            invocation_order.append(agent_name)
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            try:
                orchestrator.handle_incident(incident_data)
            except Exception:
                pass
        
        # Property: No duplicates in invocation order
        assert len(invocation_order) == len(set(invocation_order)), (
            f"Agents invoked multiple times: {invocation_order}"
        )
        
        # Property: Each agent invoked exactly once
        for agent in orchestrator.config.agent_sequence:
            assert invocation_order.count(agent) == 1, (
                f"Agent {agent} invoked {invocation_order.count(agent)} times"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
