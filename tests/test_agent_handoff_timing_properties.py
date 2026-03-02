"""
Property-Based Tests for Agent Output Handoff Timing

Property 20: Agent Output Handoff Timing
Validates: Requirements 6.2

Tests that agent outputs are passed to the next agent within 1 second.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
from datetime import datetime
import time

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
            "api-gateway"
        ])),
        "timestamp": datetime.now().isoformat(),
        "error_message": draw(st.text(min_size=10, max_size=100)),
        "log_location": f"s3://logs/service/test"
    }


class TestAgentHandoffTimingProperties:
    """
    Property 20: Agent Output Handoff Timing
    
    PROPERTY: WHEN an agent completes, its output SHALL be passed to the next
    agent within 1 second
    
    Validates: Requirement 6.2
    """
    
    @given(
        incident_data=incident_data_strategy(),
        execution_time=st.floats(min_value=0.1, max_value=0.9)
    )
    @settings(max_examples=100, deadline=None)
    def test_handoff_within_one_second(self, incident_data, execution_time):
        """
        Property: Agent output must be handed off within 1 second
        
        Given any incident data and agent execution time < 1 second
        When an agent completes
        Then the output must be available to the next agent within 1 second
        """
        orchestrator = StrandsOrchestrator()
        
        handoff_times = []
        agent_completion_times = {}
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            # Simulate agent execution
            time.sleep(execution_time)
            agent_completion_times[agent_name] = time.time()
            
            # Check if this agent received input from previous agent
            if agent_name != "log-analysis":
                # Get previous agent in sequence
                agent_index = orchestrator.config.agent_sequence.index(agent_name)
                prev_agent = orchestrator.config.agent_sequence[agent_index - 1]
                
                if prev_agent in agent_completion_times:
                    handoff_time = time.time() - agent_completion_times[prev_agent]
                    handoff_times.append(handoff_time)
            
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=execution_time,
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
        
        # Property: All handoffs must be within 1 second
        for handoff_time in handoff_times:
            assert handoff_time <= 1.0, (
                f"Handoff time exceeded 1 second: {handoff_time:.3f}s"
            )
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_handoff_timeout_logged_when_exceeded(self, incident_data):
        """
        Property: When handoff exceeds 1 second, a warning must be logged
        
        Given any incident data
        When an agent takes > 1 second to complete
        Then a warning must be logged about timeout
        """
        orchestrator = StrandsOrchestrator()
        
        # Mock agent that takes > 1 second
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=1.5,  # Exceeds timeout
                retry_count=0
            )
        
        with patch.object(
            orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            with patch('src.orchestrator.agent_orchestrator.logger') as mock_logger:
                try:
                    orchestrator.handle_incident(incident_data)
                except Exception:
                    pass
                
                # Property: Warning must be logged for timeout
                warning_calls = [
                    call for call in mock_logger.warning.call_args_list
                    if 'handoff exceeded timeout' in str(call).lower()
                ]
                
                assert len(warning_calls) > 0, (
                    "No warning logged for handoff timeout"
                )
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_memory_manager_stores_output_immediately(self, incident_data):
        """
        Property: Agent output must be stored in memory manager immediately
        
        Given any incident data
        When an agent completes
        Then its output must be stored in memory manager before next agent starts
        """
        orchestrator = StrandsOrchestrator()
        
        storage_order = []
        invocation_order = []
        
        original_store = orchestrator.memory_manager.store_agent_output
        
        def mock_store_output(session_id, agent_name, output_data):
            storage_order.append(agent_name)
            return original_store(session_id, agent_name, output_data)
        
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
            orchestrator.memory_manager,
            'store_agent_output',
            side_effect=mock_store_output
        ):
            with patch.object(
                orchestrator,
                '_invoke_agent_with_retry',
                side_effect=mock_invoke_agent
            ):
                try:
                    orchestrator.handle_incident(incident_data)
                except Exception:
                    pass
        
        # Property: Each agent's output must be stored before next agent invoked
        for i in range(len(storage_order) - 1):
            stored_agent = storage_order[i]
            next_invoked_agent = invocation_order[i + 1]
            
            # Find index of stored agent in invocation order
            stored_index = invocation_order.index(stored_agent)
            next_index = invocation_order.index(next_invoked_agent)
            
            assert stored_index < next_index, (
                f"Agent {stored_agent} output not stored before {next_invoked_agent} invoked"
            )
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_session_activity_updated_on_handoff(self, incident_data):
        """
        Property: Session activity must be updated on each agent handoff
        
        Given any incident data
        When an agent completes and hands off to next agent
        Then session activity timestamp must be updated
        """
        orchestrator = StrandsOrchestrator()
        
        activity_updates = []
        
        original_update = orchestrator.session_manager.update_session_activity
        
        def mock_update_activity(session_id):
            activity_updates.append(time.time())
            return original_update(session_id)
        
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"result": f"output from {agent_name}"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            orchestrator.session_manager,
            'update_session_activity',
            side_effect=mock_update_activity
        ):
            with patch.object(
                orchestrator,
                '_invoke_agent_with_retry',
                side_effect=mock_invoke_agent
            ):
                try:
                    orchestrator.handle_incident(incident_data)
                except Exception:
                    pass
        
        # Property: Session activity must be updated at least once per agent
        num_agents = len(orchestrator.config.agent_sequence)
        assert len(activity_updates) >= num_agents, (
            f"Session activity not updated enough times. "
            f"Expected >= {num_agents}, got {len(activity_updates)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
