"""
Property-Based Tests for Partial Results Preservation

Property 22: Partial Results Preservation
Validates: Requirements 6.4

Tests that results from successful agents are preserved even when other agents fail.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
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
            "api-gateway"
        ])),
        "timestamp": datetime.now().isoformat(),
        "error_message": draw(st.text(min_size=10, max_size=100)),
        "log_location": f"s3://logs/service/test"
    }


class TestPartialResultsProperties:
    """
    Property 22: Partial Results Preservation
    
    PROPERTY: WHEN an agent fails after retries, results from successful agents
    SHALL be preserved in the enhanced alert
    
    Validates: Requirement 6.4
    """
    
    @given(
        incident_data=incident_data_strategy(),
        failing_agent=st.sampled_from(["log-analysis", "root-cause", "fix-recommendation", "communication"])
    )
    @settings(max_examples=100, deadline=None)
    def test_successful_agent_results_preserved_on_failure(self, incident_data, failing_agent):
        """
        Property: Successful agent results must be preserved when another agent fails
        
        Given any incident data and a failing agent
        When one agent fails but others succeed
        Then all successful agent results must be in the enhanced alert
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            if agent_name == failing_agent:
                raise Exception(f"Simulated failure for {agent_name}")
            return {"result": f"success from {agent_name}", "agent": agent_name}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            with patch('time.sleep'):  # Skip retry delays
                try:
                    result = orchestrator.handle_incident(incident_data)
                    
                    # Property: Enhanced alert must exist
                    assert result.enhanced_alert is not None, (
                        "Enhanced alert is None despite partial success"
                    )
                    
                    # Property: Successful agents must have their outputs preserved
                    for agent_name in orchestrator.config.agent_sequence:
                        if agent_name != failing_agent:
                            agent_result = result.agent_results.get(agent_name)
                            assert agent_result is not None, (
                                f"Result for successful agent {agent_name} not found"
                            )
                            assert agent_result.success is True, (
                                f"Agent {agent_name} marked as failed but should succeed"
                            )
                            assert agent_result.output is not None, (
                                f"Output for successful agent {agent_name} is None"
                            )
                    
                    # Property: Failed agent must be marked as failed
                    failed_result = result.agent_results.get(failing_agent)
                    assert failed_result is not None, (
                        f"Result for failed agent {failing_agent} not found"
                    )
                    assert failed_result.success is False, (
                        f"Agent {failing_agent} marked as success but should fail"
                    )
                    
                except Exception as e:
                    pytest.fail(f"Orchestrator raised exception: {str(e)}")
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_partial_results_flag_set_on_failure(self, incident_data):
        """
        Property: partial_results flag must be True when any agent fails
        
        Given any incident data
        When at least one agent fails
        Then result.partial_results must be True
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            # Fail the first agent
            if agent_name == "log-analysis":
                raise Exception("Simulated failure")
            return {"result": f"success from {agent_name}"}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            with patch('time.sleep'):
                try:
                    result = orchestrator.handle_incident(incident_data)
                    
                    # Property: partial_results must be True
                    assert result.partial_results is True, (
                        "partial_results should be True when agent fails"
                    )
                    
                except Exception as e:
                    pytest.fail(f"Orchestrator raised exception: {str(e)}")
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_partial_results_flag_false_on_all_success(self, incident_data):
        """
        Property: partial_results flag must be False when all agents succeed
        
        Given any incident data
        When all agents succeed
        Then result.partial_results must be False
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            return {"result": f"success from {agent_name}"}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            try:
                result = orchestrator.handle_incident(incident_data)
                
                # Property: partial_results must be False
                assert result.partial_results is False, (
                    "partial_results should be False when all agents succeed"
                )
                
            except Exception as e:
                pytest.fail(f"Orchestrator raised exception: {str(e)}")
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_enhanced_alert_contains_partial_results_metadata(self, incident_data):
        """
        Property: Enhanced alert must contain metadata about partial results
        
        Given any incident data
        When agents produce partial results
        Then enhanced alert must include processing_metadata with partial_results flag
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            if agent_name == "log-analysis":
                raise Exception("Simulated failure")
            return {"result": f"success from {agent_name}"}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            with patch('time.sleep'):
                try:
                    result = orchestrator.handle_incident(incident_data)
                    
                    # Property: Enhanced alert must have processing_metadata
                    assert "processing_metadata" in result.enhanced_alert, (
                        "Enhanced alert missing processing_metadata"
                    )
                    
                    metadata = result.enhanced_alert["processing_metadata"]
                    
                    # Property: Metadata must include partial_results flag
                    assert "partial_results" in metadata, (
                        "processing_metadata missing partial_results flag"
                    )
                    
                    assert metadata["partial_results"] is True, (
                        "partial_results flag should be True in metadata"
                    )
                    
                    # Property: Metadata must include success/failure counts
                    assert "successful_agents" in metadata, (
                        "processing_metadata missing successful_agents count"
                    )
                    assert "failed_agents" in metadata, (
                        "processing_metadata missing failed_agents count"
                    )
                    
                    assert metadata["successful_agents"] == 3, (
                        f"Expected 3 successful agents, got {metadata['successful_agents']}"
                    )
                    assert metadata["failed_agents"] == 1, (
                        f"Expected 1 failed agent, got {metadata['failed_agents']}"
                    )
                    
                except Exception as e:
                    pytest.fail(f"Orchestrator raised exception: {str(e)}")
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_agent_outputs_preserved_in_enhanced_alert(self, incident_data):
        """
        Property: All agent outputs must be preserved in enhanced alert
        
        Given any incident data
        When agents execute (with some failures)
        Then enhanced alert must contain all agent outputs (success and failure)
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            if agent_name == "root-cause":
                raise Exception("Simulated failure")
            return {"result": f"success from {agent_name}", "data": f"output_{agent_name}"}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            with patch('time.sleep'):
                try:
                    result = orchestrator.handle_incident(incident_data)
                    
                    # Property: Enhanced alert must have agent_outputs section
                    assert "agent_outputs" in result.enhanced_alert, (
                        "Enhanced alert missing agent_outputs section"
                    )
                    
                    agent_outputs = result.enhanced_alert["agent_outputs"]
                    
                    # Property: All agents must be represented in outputs
                    for agent_name in orchestrator.config.agent_sequence:
                        assert agent_name in agent_outputs, (
                            f"Agent {agent_name} missing from agent_outputs"
                        )
                        
                        agent_output = agent_outputs[agent_name]
                        
                        # Property: Each output must have success flag
                        assert "success" in agent_output, (
                            f"Agent {agent_name} output missing success flag"
                        )
                        
                        # Property: Successful agents must have output data
                        if agent_name != "root-cause":
                            assert agent_output["success"] is True, (
                                f"Agent {agent_name} should be successful"
                            )
                            assert agent_output["output"] is not None, (
                                f"Successful agent {agent_name} has None output"
                            )
                        else:
                            assert agent_output["success"] is False, (
                                f"Agent {agent_name} should be failed"
                            )
                            assert agent_output["error"] is not None, (
                                f"Failed agent {agent_name} has None error"
                            )
                    
                except Exception as e:
                    pytest.fail(f"Orchestrator raised exception: {str(e)}")
    
    @given(incident_data=incident_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_partial_results_logged_with_warning(self, incident_data):
        """
        Property: Partial results must be logged with warning
        
        Given any incident data
        When an agent fails and partial results are preserved
        Then a warning must be logged about partial results
        """
        orchestrator = StrandsOrchestrator()
        
        def mock_invoke_strands_agent(agent_name, input_data, previous_outputs):
            if agent_name == "fix-recommendation":
                raise Exception("Simulated failure")
            return {"result": f"success from {agent_name}"}
        
        with patch.object(
            orchestrator,
            '_invoke_strands_agent',
            side_effect=mock_invoke_strands_agent
        ):
            with patch('time.sleep'):
                with patch('src.orchestrator.agent_orchestrator.logger') as mock_logger:
                    try:
                        orchestrator.handle_incident(incident_data)
                    except Exception:
                        pass
                    
                    # Property: Warning must be logged about partial results
                    warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                    partial_result_warnings = [
                        call for call in warning_calls 
                        if 'partial' in call.lower() or 'failed' in call.lower()
                    ]
                    
                    assert len(partial_result_warnings) > 0, (
                        "No warning logged about partial results"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
