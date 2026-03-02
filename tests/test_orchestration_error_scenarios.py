"""
Unit Tests for Orchestration Error Scenarios

Tests various error scenarios in the orchestration flow:
- All agents succeed
- First agent fails
- Middle agent fails
- Last agent fails
- Multiple agents fail

Validates: Requirements 6.3, 6.4
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.orchestrator.agent_orchestrator import (
    StrandsOrchestrator,
    AgentResult,
    OrchestrationResult
)


class TestOrchestrationErrorScenarios:
    """Unit tests for various orchestration error scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.orchestrator = StrandsOrchestrator()
        self.incident_data = {
            "incident_id": "inc-test-001",
            "service_name": "payment-processor",
            "timestamp": datetime.now().isoformat(),
            "error_message": "Service health check failed",
            "log_location": "s3://logs/payment-processor/2025-01-15.log"
        }
    
    def test_all_agents_succeed(self):
        """
        Test: All agents succeed
        
        Given incident data
        When all agents execute successfully
        Then orchestration result should indicate success
        And all agent outputs should be present
        And partial_results should be False
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={
                    "agent": agent_name,
                    "result": f"success from {agent_name}",
                    "data": {"key": "value"}
                },
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Assertions
            assert result.success is True, "Orchestration should succeed"
            assert result.partial_results is False, "Should not have partial results"
            assert len(result.agent_results) == 4, "Should have 4 agent results"
            
            # All agents should be successful
            for agent_name, agent_result in result.agent_results.items():
                assert agent_result.success is True, f"Agent {agent_name} should succeed"
                assert agent_result.output is not None, f"Agent {agent_name} should have output"
                assert agent_result.error is None, f"Agent {agent_name} should have no error"
            
            # Enhanced alert should be complete
            assert result.enhanced_alert is not None
            assert "agent_outputs" in result.enhanced_alert
            assert result.enhanced_alert["processing_metadata"]["successful_agents"] == 4
            assert result.enhanced_alert["processing_metadata"]["failed_agents"] == 0
    
    def test_first_agent_fails(self):
        """
        Test: First agent (log-analysis) fails
        
        Given incident data
        When log-analysis agent fails after retries
        Then orchestration should continue with remaining agents
        And partial_results should be True
        And failed agent should be marked as failed
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            if agent_name == "log-analysis":
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error="Log retrieval failed",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={
                    "agent": agent_name,
                    "result": f"success from {agent_name}"
                },
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Assertions
            assert result.success is False, "Orchestration should not fully succeed"
            assert result.partial_results is True, "Should have partial results"
            
            # Log analysis should be failed
            log_result = result.agent_results["log-analysis"]
            assert log_result.success is False
            assert log_result.error is not None
            assert log_result.retry_count == 2, "Should have retried 2 times"
            
            # Other agents should succeed
            for agent_name in ["root-cause", "fix-recommendation", "communication"]:
                agent_result = result.agent_results[agent_name]
                assert agent_result.success is True, f"Agent {agent_name} should succeed"
            
            # Metadata should reflect partial success
            metadata = result.enhanced_alert["processing_metadata"]
            assert metadata["successful_agents"] == 3
            assert metadata["failed_agents"] == 1
    
    def test_middle_agent_fails(self):
        """
        Test: Middle agent (root-cause) fails
        
        Given incident data
        When root-cause agent fails after retries
        Then orchestration should continue with remaining agents
        And partial_results should be True
        And subsequent agents should receive empty input from failed agent
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            if agent_name == "root-cause":
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error="Root cause analysis failed",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={
                    "agent": agent_name,
                    "result": f"success from {agent_name}"
                },
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Assertions
            assert result.partial_results is True
            
            # Root cause should be failed
            root_cause_result = result.agent_results["root-cause"]
            assert root_cause_result.success is False
            assert root_cause_result.error is not None
            
            # Log analysis should succeed
            log_result = result.agent_results["log-analysis"]
            assert log_result.success is True
            
            # Fix recommendation and communication should still execute
            fix_result = result.agent_results["fix-recommendation"]
            assert fix_result.success is True
            
            comm_result = result.agent_results["communication"]
            assert comm_result.success is True
            
            # Metadata
            metadata = result.enhanced_alert["processing_metadata"]
            assert metadata["successful_agents"] == 3
            assert metadata["failed_agents"] == 1
    
    def test_last_agent_fails(self):
        """
        Test: Last agent (communication) fails
        
        Given incident data
        When communication agent fails after retries
        Then orchestration should complete with partial results
        And all previous agent outputs should be preserved
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            if agent_name == "communication":
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error="Communication generation failed",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={
                    "agent": agent_name,
                    "result": f"success from {agent_name}"
                },
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Assertions
            assert result.partial_results is True
            
            # Communication should be failed
            comm_result = result.agent_results["communication"]
            assert comm_result.success is False
            assert comm_result.error is not None
            
            # All previous agents should succeed
            for agent_name in ["log-analysis", "root-cause", "fix-recommendation"]:
                agent_result = result.agent_results[agent_name]
                assert agent_result.success is True, f"Agent {agent_name} should succeed"
                assert agent_result.output is not None
            
            # Metadata
            metadata = result.enhanced_alert["processing_metadata"]
            assert metadata["successful_agents"] == 3
            assert metadata["failed_agents"] == 1
    
    def test_multiple_agents_fail(self):
        """
        Test: Multiple agents fail
        
        Given incident data
        When multiple agents fail (log-analysis and fix-recommendation)
        Then orchestration should continue and preserve successful results
        And partial_results should be True
        And failed_agents count should be 2
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            if agent_name in ["log-analysis", "fix-recommendation"]:
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error=f"{agent_name} failed",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={
                    "agent": agent_name,
                    "result": f"success from {agent_name}"
                },
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Assertions
            assert result.success is False
            assert result.partial_results is True
            
            # Failed agents
            log_result = result.agent_results["log-analysis"]
            assert log_result.success is False
            
            fix_result = result.agent_results["fix-recommendation"]
            assert fix_result.success is False
            
            # Successful agents
            root_cause_result = result.agent_results["root-cause"]
            assert root_cause_result.success is True
            
            comm_result = result.agent_results["communication"]
            assert comm_result.success is True
            
            # Metadata
            metadata = result.enhanced_alert["processing_metadata"]
            assert metadata["successful_agents"] == 2
            assert metadata["failed_agents"] == 2
    
    def test_session_cleanup_on_success(self):
        """
        Test: Session cleanup occurs on successful orchestration
        
        Given incident data
        When orchestration completes successfully
        Then session should be cleaned up
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"agent": agent_name, "result": "success"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Session should be cleaned up (not in active sessions)
            session = self.orchestrator.session_manager.get_session_by_incident(
                self.incident_data["incident_id"]
            )
            assert session is None, "Session should be cleaned up"
    
    def test_session_cleanup_on_failure(self):
        """
        Test: Session cleanup occurs even on orchestration failure
        
        Given incident data
        When orchestration fails
        Then session should still be cleaned up
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=False,
                output=None,
                error="All agents fail",
                execution_time_seconds=0.5,
                retry_count=2
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            result = self.orchestrator.handle_incident(self.incident_data)
            
            # Session should be cleaned up
            session = self.orchestrator.session_manager.get_session_by_incident(
                self.incident_data["incident_id"]
            )
            assert session is None, "Session should be cleaned up even on failure"
    
    def test_metrics_emitted_on_completion(self):
        """
        Test: CloudWatch metrics are emitted on orchestration completion
        
        Given incident data
        When orchestration completes
        Then metrics should be emitted to CloudWatch
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"agent": agent_name, "result": "success"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            with patch('src.orchestrator.agent_orchestrator.cloudwatch') as mock_cw:
                result = self.orchestrator.handle_incident(self.incident_data)
                
                # Metrics should be emitted
                assert mock_cw.put_metric_data.called, "Metrics should be emitted"
                
                # Check metric data
                call_args = mock_cw.put_metric_data.call_args
                assert call_args[1]['Namespace'] == 'IncidentResponse/Orchestration'
                assert len(call_args[1]['MetricData']) > 0
    
    def test_error_logged_on_agent_failure(self):
        """
        Test: Errors are logged when agents fail
        
        Given incident data
        When an agent fails
        Then error should be logged with context
        """
        def mock_invoke_agent(session_id, agent_name, input_data):
            if agent_name == "log-analysis":
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error="Test error",
                    execution_time_seconds=0.5,
                    retry_count=2
                )
            return AgentResult(
                agent_name=agent_name,
                success=True,
                output={"agent": agent_name, "result": "success"},
                error=None,
                execution_time_seconds=0.5,
                retry_count=0
            )
        
        with patch.object(
            self.orchestrator,
            '_invoke_agent_with_retry',
            side_effect=mock_invoke_agent
        ):
            with patch('src.orchestrator.agent_orchestrator.logger') as mock_logger:
                result = self.orchestrator.handle_incident(self.incident_data)
                
                # Error should be logged
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any('failed' in call.lower() for call in error_calls), (
                    "Error should be logged for agent failure"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
