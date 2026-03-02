"""
Unit tests for Memory Manager

Tests memory management, context storage, and agent handoffs.
"""

import pytest
from src.orchestrator.memory_manager import (
    MemoryManager,
    ContextEntry,
    ContextType
)
from datetime import datetime


class TestContextEntry:
    """Test ContextEntry dataclass"""
    
    def test_context_entry_creation(self):
        """Test context entry object creation"""
        now = datetime.now()
        entry = ContextEntry(
            entry_id="test-entry-1",
            context_type=ContextType.AGENT_OUTPUT,
            agent_name="log-analysis",
            timestamp=now,
            data={"summary": "test"},
            size_bytes=100
        )
        
        assert entry.entry_id == "test-entry-1"
        assert entry.context_type == ContextType.AGENT_OUTPUT
        assert entry.agent_name == "log-analysis"
        assert entry.size_bytes == 100
    
    def test_context_entry_to_dict(self):
        """Test context entry serialization"""
        now = datetime.now()
        entry = ContextEntry(
            entry_id="test-entry-1",
            context_type=ContextType.AGENT_OUTPUT,
            agent_name="log-analysis",
            timestamp=now,
            data={"summary": "test"},
            size_bytes=100
        )
        
        result = entry.to_dict()
        
        assert result["entry_id"] == "test-entry-1"
        assert result["context_type"] == "agent_output"
        assert result["agent_name"] == "log-analysis"
        assert result["data"]["summary"] == "test"


class TestMemoryManager:
    """Test MemoryManager class"""
    
    def test_memory_manager_initialization(self):
        """Test memory manager initialization with default config"""
        manager = MemoryManager()
        
        assert manager.max_context_size_kb == 100
        assert manager.enable_compression is True
        assert manager.persist_results is True
    
    def test_memory_manager_custom_config(self):
        """Test memory manager with custom configuration"""
        config = {
            "max_context_size_kb": 200,
            "enable_context_compression": False,
            "persist_intermediate_results": False
        }
        manager = MemoryManager(config)
        
        assert manager.max_context_size_kb == 200
        assert manager.enable_compression is False
        assert manager.persist_results is False
    
    def test_store_agent_input(self):
        """Test storing agent input data"""
        manager = MemoryManager()
        
        input_data = {
            "log_location": "s3://bucket/logs",
            "timestamp": "2025-01-15T10:30:00Z",
            "service_name": "payment-processor"
        }
        
        entry_id = manager.store_agent_input(
            session_id="session-1",
            agent_name="log-analysis",
            input_data=input_data
        )
        
        assert entry_id is not None
        assert entry_id.startswith("session-1-log-analysis-agent_input")
    
    def test_store_agent_output(self):
        """Test storing agent output data"""
        manager = MemoryManager()
        
        output_data = {
            "summary": "Connection timeout detected",
            "error_patterns": ["ConnectionTimeout"],
            "occurrences": 15
        }
        
        entry_id = manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data=output_data
        )
        
        assert entry_id is not None
        assert entry_id.startswith("session-1-log-analysis-agent_output")
    
    def test_store_intermediate_result(self):
        """Test storing intermediate result"""
        manager = MemoryManager()
        
        result_data = {
            "processing_step": "pattern_extraction",
            "patterns_found": 5
        }
        
        entry_id = manager.store_intermediate_result(
            session_id="session-1",
            agent_name="log-analysis",
            result_data=result_data
        )
        
        assert entry_id is not None
    
    def test_store_intermediate_result_disabled(self):
        """Test intermediate results not stored when disabled"""
        config = {"persist_intermediate_results": False}
        manager = MemoryManager(config)
        
        result_data = {"step": "test"}
        
        entry_id = manager.store_intermediate_result(
            session_id="session-1",
            agent_name="log-analysis",
            result_data=result_data
        )
        
        assert entry_id == ""
    
    def test_store_conversation_context(self):
        """Test storing conversation context"""
        manager = MemoryManager()
        
        conversation_data = {
            "turn": 1,
            "message": "Analyzing logs...",
            "response": "Found 15 errors"
        }
        
        entry_id = manager.store_conversation_context(
            session_id="session-1",
            agent_name="log-analysis",
            conversation_data=conversation_data
        )
        
        assert entry_id is not None
    
    def test_get_agent_output(self):
        """Test retrieving agent output"""
        manager = MemoryManager()
        
        output_data = {
            "summary": "Connection timeout",
            "confidence": 85
        }
        
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data=output_data
        )
        
        retrieved = manager.get_agent_output(
            session_id="session-1",
            agent_name="log-analysis"
        )
        
        assert retrieved is not None
        assert retrieved["summary"] == "Connection timeout"
        assert retrieved["confidence"] == 85
    
    def test_get_agent_output_not_found(self):
        """Test retrieving non-existent agent output"""
        manager = MemoryManager()
        
        retrieved = manager.get_agent_output(
            session_id="session-1",
            agent_name="log-analysis"
        )
        
        assert retrieved is None
    
    def test_get_previous_agent_outputs(self):
        """Test retrieving outputs from previous agents"""
        manager = MemoryManager()
        
        agent_sequence = ["log-analysis", "root-cause", "fix-recommendation"]
        
        # Store outputs from first two agents
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"summary": "log analysis result"}
        )
        
        manager.store_agent_output(
            session_id="session-1",
            agent_name="root-cause",
            output_data={"cause": "timeout"}
        )
        
        # Get previous outputs for third agent
        previous_outputs = manager.get_previous_agent_outputs(
            session_id="session-1",
            current_agent="fix-recommendation",
            agent_sequence=agent_sequence
        )
        
        assert len(previous_outputs) == 2
        assert "log-analysis" in previous_outputs
        assert "root-cause" in previous_outputs
        assert previous_outputs["log-analysis"]["summary"] == "log analysis result"
        assert previous_outputs["root-cause"]["cause"] == "timeout"
    
    def test_get_previous_agent_outputs_first_agent(self):
        """Test getting previous outputs for first agent (should be empty)"""
        manager = MemoryManager()
        
        agent_sequence = ["log-analysis", "root-cause", "fix-recommendation"]
        
        previous_outputs = manager.get_previous_agent_outputs(
            session_id="session-1",
            current_agent="log-analysis",
            agent_sequence=agent_sequence
        )
        
        assert len(previous_outputs) == 0
    
    def test_get_conversation_context(self):
        """Test retrieving conversation context"""
        manager = MemoryManager()
        
        # Store multiple conversation entries
        manager.store_conversation_context(
            session_id="session-1",
            agent_name="log-analysis",
            conversation_data={"turn": 1, "message": "First message"}
        )
        
        manager.store_conversation_context(
            session_id="session-1",
            agent_name="log-analysis",
            conversation_data={"turn": 2, "message": "Second message"}
        )
        
        context = manager.get_conversation_context(
            session_id="session-1",
            agent_name="log-analysis"
        )
        
        assert len(context) == 2
        assert context[0]["turn"] == 1
        assert context[1]["turn"] == 2
    
    def test_get_full_context(self):
        """Test retrieving full context for a session"""
        manager = MemoryManager()
        
        # Store various types of context
        manager.store_agent_input(
            session_id="session-1",
            agent_name="log-analysis",
            input_data={"input": "test"}
        )
        
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"output": "test"}
        )
        
        manager.store_intermediate_result(
            session_id="session-1",
            agent_name="log-analysis",
            result_data={"intermediate": "test"}
        )
        
        full_context = manager.get_full_context(session_id="session-1")
        
        assert len(full_context["agent_inputs"]) == 1
        assert len(full_context["agent_outputs"]) == 1
        assert len(full_context["intermediate_results"]) == 1
    
    def test_get_full_context_filtered_by_agent(self):
        """Test retrieving full context filtered by agent name"""
        manager = MemoryManager()
        
        # Store context for multiple agents
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"output": "log result"}
        )
        
        manager.store_agent_output(
            session_id="session-1",
            agent_name="root-cause",
            output_data={"output": "cause result"}
        )
        
        # Get context for specific agent
        context = manager.get_full_context(
            session_id="session-1",
            agent_name="log-analysis"
        )
        
        assert len(context["agent_outputs"]) == 1
        assert context["agent_outputs"][0]["agent_name"] == "log-analysis"
    
    def test_clear_session_memory(self):
        """Test clearing session memory"""
        manager = MemoryManager()
        
        # Store some data
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"output": "test"}
        )
        
        # Clear memory
        success = manager.clear_session_memory("session-1")
        
        assert success is True
        
        # Verify memory is cleared
        retrieved = manager.get_agent_output(
            session_id="session-1",
            agent_name="log-analysis"
        )
        
        assert retrieved is None
    
    def test_clear_session_memory_not_found(self):
        """Test clearing non-existent session memory"""
        manager = MemoryManager()
        
        success = manager.clear_session_memory("non-existent")
        
        assert success is False
    
    def test_get_memory_size(self):
        """Test getting memory size for a session"""
        manager = MemoryManager()
        
        # Store some data
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"summary": "test data"}
        )
        
        size = manager.get_memory_size("session-1")
        
        assert size > 0
    
    def test_get_memory_size_empty_session(self):
        """Test getting memory size for non-existent session"""
        manager = MemoryManager()
        
        size = manager.get_memory_size("non-existent")
        
        assert size == 0
    
    def test_compress_context(self):
        """Test context compression when size exceeds limit"""
        config = {"max_context_size_kb": 0.001}  # Very small limit to trigger compression
        manager = MemoryManager(config)
        
        # Store agent output (essential)
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"output": "important data"}
        )
        
        # Store intermediate result (can be compressed)
        manager.store_intermediate_result(
            session_id="session-1",
            agent_name="log-analysis",
            result_data={"intermediate": "less important data"}
        )
        
        # Compression should have been triggered automatically
        full_context = manager.get_full_context("session-1")
        
        # Intermediate results should be removed
        assert len(full_context["intermediate_results"]) == 0
        # Agent outputs should be preserved
        assert len(full_context["agent_outputs"]) == 1
    
    def test_compress_context_disabled(self):
        """Test compression doesn't occur when disabled"""
        config = {
            "max_context_size_kb": 0.001,
            "enable_context_compression": False
        }
        manager = MemoryManager(config)
        
        manager.store_intermediate_result(
            session_id="session-1",
            agent_name="log-analysis",
            result_data={"intermediate": "data"}
        )
        
        full_context = manager.get_full_context("session-1")
        
        # Intermediate results should still be there
        assert len(full_context["intermediate_results"]) == 1
    
    def test_get_metrics(self):
        """Test retrieving memory metrics"""
        manager = MemoryManager()
        
        # Store some data
        manager.store_agent_output(
            session_id="session-1",
            agent_name="log-analysis",
            output_data={"output": "test"}
        )
        
        manager.store_agent_output(
            session_id="session-2",
            agent_name="root-cause",
            output_data={"cause": "timeout"}
        )
        
        metrics = manager.get_metrics()
        
        assert metrics["total_entries_stored"] == 2
        assert metrics["active_sessions"] == 2
        assert metrics["total_memory_kb"] > 0
    
    def test_agent_handoff_workflow(self):
        """Test complete agent handoff workflow"""
        manager = MemoryManager()
        
        agent_sequence = ["log-analysis", "root-cause", "fix-recommendation"]
        session_id = "session-1"
        
        # Agent 1: Log Analysis
        manager.store_agent_output(
            session_id=session_id,
            agent_name="log-analysis",
            output_data={
                "summary": "Connection timeout detected",
                "error_patterns": ["ConnectionTimeout"],
                "occurrences": 15
            }
        )
        
        # Agent 2: Root Cause - gets previous output
        log_analysis_output = manager.get_agent_output(
            session_id=session_id,
            agent_name="log-analysis"
        )
        
        assert log_analysis_output is not None
        assert log_analysis_output["summary"] == "Connection timeout detected"
        
        # Store root cause output
        manager.store_agent_output(
            session_id=session_id,
            agent_name="root-cause",
            output_data={
                "primary_cause": "dependency_failure",
                "confidence": 85
            }
        )
        
        # Agent 3: Fix Recommendation - gets all previous outputs
        previous_outputs = manager.get_previous_agent_outputs(
            session_id=session_id,
            current_agent="fix-recommendation",
            agent_sequence=agent_sequence
        )
        
        assert len(previous_outputs) == 2
        assert "log-analysis" in previous_outputs
        assert "root-cause" in previous_outputs
        assert previous_outputs["root-cause"]["confidence"] == 85


class TestMemoryManagerIntegration:
    """Integration tests for memory manager with multiple agents"""
    
    def test_multi_agent_context_flow(self):
        """Test context flow through multiple agents"""
        manager = MemoryManager()
        session_id = "session-1"
        
        # Simulate complete agent flow
        agents = [
            ("log-analysis", {"summary": "Error found"}),
            ("root-cause", {"cause": "timeout"}),
            ("fix-recommendation", {"fix": "increase timeout"}),
            ("communication", {"alert": "sent"})
        ]
        
        for agent_name, output_data in agents:
            manager.store_agent_output(
                session_id=session_id,
                agent_name=agent_name,
                output_data=output_data
            )
        
        # Verify all outputs stored
        full_context = manager.get_full_context(session_id)
        assert len(full_context["agent_outputs"]) == 4
        
        # Verify each agent can retrieve previous outputs
        for i, (agent_name, _) in enumerate(agents):
            if i > 0:
                output = manager.get_agent_output(session_id, agents[i-1][0])
                assert output is not None
