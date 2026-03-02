"""
Integration tests for AgentCore runtime layer

Tests the integration of configuration, session management, and memory management.
"""

import pytest
from src.orchestrator import (
    AgentCoreConfig,
    SessionManager,
    MemoryManager,
    get_default_config
)


class TestAgentCoreIntegration:
    """Test integration of AgentCore components"""
    
    def test_complete_incident_processing_flow(self):
        """Test complete flow from session creation to cleanup"""
        # 1. Initialize with configuration
        config = get_default_config()
        config.validate()
        
        session_manager = SessionManager(config.session.to_dict())
        memory_manager = MemoryManager(config.memory.to_dict())
        
        # 2. Create session for incident
        incident_id = "inc-2025-01-15-001"
        session = session_manager.create_session(
            incident_id=incident_id,
            metadata={"service": "payment-processor"}
        )
        
        assert session is not None
        assert session.incident_id == incident_id
        
        # 3. Activate session
        session_manager.activate_session(session.session_id)
        assert session.status.value == "active"
        
        # 4. Mark as executing
        session_manager.mark_executing(session.session_id)
        
        # 5. Simulate agent execution with memory storage
        agent_sequence = config.agent_sequence
        
        # Agent 1: Log Analysis
        log_input = {
            "log_location": "s3://bucket/logs",
            "timestamp": "2025-01-15T10:30:00Z",
            "service_name": "payment-processor"
        }
        
        memory_manager.store_agent_input(
            session.session_id,
            "log-analysis",
            log_input
        )
        
        log_output = {
            "summary": "Connection timeout detected",
            "error_patterns": ["ConnectionTimeout"],
            "occurrences": 15
        }
        
        memory_manager.store_agent_output(
            session.session_id,
            "log-analysis",
            log_output
        )
        
        session_manager.store_agent_result(
            session.session_id,
            "log-analysis",
            log_output
        )
        
        # Agent 2: Root Cause - gets previous context
        previous_outputs = memory_manager.get_previous_agent_outputs(
            session.session_id,
            "root-cause",
            agent_sequence
        )
        
        assert "log-analysis" in previous_outputs
        assert previous_outputs["log-analysis"]["summary"] == "Connection timeout detected"
        
        root_cause_output = {
            "primary_cause": "dependency_failure",
            "confidence": 85,
            "evidence": ["15 consecutive timeouts"]
        }
        
        memory_manager.store_agent_output(
            session.session_id,
            "root-cause",
            root_cause_output
        )
        
        session_manager.store_agent_result(
            session.session_id,
            "root-cause",
            root_cause_output
        )
        
        # Agent 3: Fix Recommendation - gets all previous context
        previous_outputs = memory_manager.get_previous_agent_outputs(
            session.session_id,
            "fix-recommendation",
            agent_sequence
        )
        
        assert len(previous_outputs) == 2
        assert "log-analysis" in previous_outputs
        assert "root-cause" in previous_outputs
        
        fix_output = {
            "immediate_actions": [
                {"step": 1, "action": "Increase timeout to 30s"}
            ]
        }
        
        memory_manager.store_agent_output(
            session.session_id,
            "fix-recommendation",
            fix_output
        )
        
        # Agent 4: Communication
        previous_outputs = memory_manager.get_previous_agent_outputs(
            session.session_id,
            "communication",
            agent_sequence
        )
        
        assert len(previous_outputs) == 3
        
        communication_output = {
            "technical_summary": "Timeout issue detected",
            "business_summary": "Payment processing temporarily unavailable"
        }
        
        memory_manager.store_agent_output(
            session.session_id,
            "communication",
            communication_output
        )
        
        # 6. Complete session
        final_results = {
            "incident_id": incident_id,
            "status": "resolved",
            "all_agents_completed": True
        }
        
        session_manager.complete_session(session.session_id, final_results)
        
        # 7. Verify session state
        assert session.status.value == "completed"
        
        # 8. Verify memory contains all agent outputs
        full_context = memory_manager.get_full_context(session.session_id)
        assert len(full_context["agent_outputs"]) == 4
        
        # 9. Cleanup
        memory_manager.clear_session_memory(session.session_id)
        session_manager.cleanup_session(session.session_id)
        
        # 10. Verify cleanup
        assert session_manager.get_session(session.session_id) is None
        assert memory_manager.get_memory_size(session.session_id) == 0
    
    def test_session_and_memory_metrics(self):
        """Test metrics collection from session and memory managers"""
        config = get_default_config()
        
        session_manager = SessionManager(config.session.to_dict())
        memory_manager = MemoryManager(config.memory.to_dict())
        
        # Create multiple sessions
        session1 = session_manager.create_session("inc-001")
        session2 = session_manager.create_session("inc-002")
        
        # Store data in memory
        memory_manager.store_agent_output(
            session1.session_id,
            "log-analysis",
            {"output": "test1"}
        )
        
        memory_manager.store_agent_output(
            session2.session_id,
            "log-analysis",
            {"output": "test2"}
        )
        
        # Complete one session
        session_manager.complete_session(session1.session_id)
        
        # Get metrics
        session_metrics = session_manager.get_metrics()
        memory_metrics = memory_manager.get_metrics()
        
        assert session_metrics["total_sessions_created"] == 2
        assert session_metrics["total_sessions_completed"] == 1
        assert session_metrics["active_sessions"] == 1
        
        assert memory_metrics["total_entries_stored"] == 2
        assert memory_metrics["active_sessions"] == 2
        assert memory_metrics["total_memory_kb"] > 0
    
    def test_configuration_validation(self):
        """Test configuration validation enforces requirements"""
        config = AgentCoreConfig()
        
        # Valid configuration should pass
        assert config.validate() is True
        
        # Invalid timeout should fail
        config.session.timeout_seconds = -1
        with pytest.raises(ValueError, match="Session timeout must be positive"):
            config.validate()
        
        # Reset and test another validation
        config = AgentCoreConfig()
        config.session.timeout_seconds = 10
        config.max_processing_time_seconds = 60
        
        with pytest.raises(ValueError, match="Session timeout must be >= max processing time"):
            config.validate()
    
    def test_agent_sequence_enforcement(self):
        """Test that agent sequence is enforced by configuration"""
        config = get_default_config()
        
        # Default sequence should be correct
        expected_sequence = [
            "log-analysis",
            "root-cause",
            "fix-recommendation",
            "communication"
        ]
        
        assert config.agent_sequence == expected_sequence
        
        # Invalid sequence should fail validation
        config.agent_sequence = ["log-analysis", "root-cause"]  # Missing agents
        
        with pytest.raises(ValueError, match="Agent sequence must contain exactly"):
            config.validate()
    
    def test_memory_compression_with_session(self):
        """Test memory compression during active session"""
        config = get_default_config()
        config.memory.max_context_size_kb = 0.001  # Very small to trigger compression
        
        session_manager = SessionManager(config.session.to_dict())
        memory_manager = MemoryManager(config.memory.to_dict())
        
        session = session_manager.create_session("inc-001")
        
        # Store essential output
        memory_manager.store_agent_output(
            session.session_id,
            "log-analysis",
            {"output": "important data"}
        )
        
        # Store intermediate result (will be compressed)
        memory_manager.store_intermediate_result(
            session.session_id,
            "log-analysis",
            {"intermediate": "less important"}
        )
        
        # Verify compression occurred
        full_context = memory_manager.get_full_context(session.session_id)
        
        # Agent outputs should be preserved
        assert len(full_context["agent_outputs"]) == 1
        # Intermediate results should be removed
        assert len(full_context["intermediate_results"]) == 0
        
        # Session should still be active
        assert session.status.value == "created"


class TestAgentCoreErrorHandling:
    """Test error handling in AgentCore integration"""
    
    def test_session_not_found_in_memory(self):
        """Test memory manager handles non-existent session gracefully"""
        memory_manager = MemoryManager()
        
        output = memory_manager.get_agent_output(
            "non-existent-session",
            "log-analysis"
        )
        
        assert output is None
    
    def test_max_concurrent_sessions_with_cleanup(self):
        """Test that cleanup allows new sessions when at limit"""
        config = {
            "timeout_seconds": 300,
            "max_concurrent_sessions": 2,
            "session_cleanup_enabled": True
        }
        
        session_manager = SessionManager(config)
        
        # Create 2 sessions (at limit)
        session1 = session_manager.create_session("inc-001")
        session2 = session_manager.create_session("inc-002")
        
        # Complete first session
        session_manager.complete_session(session1.session_id)
        
        # Cleanup completed session
        session_manager.cleanup_session(session1.session_id)
        
        # Should now be able to create another session
        session3 = session_manager.create_session("inc-003")
        
        assert session3 is not None
