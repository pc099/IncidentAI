"""
Unit tests for Session Manager

Tests session lifecycle management, resource cleanup, and isolation.
"""

import pytest
import time
from datetime import datetime, timedelta
from src.orchestrator.session_manager import (
    SessionManager,
    Session,
    SessionStatus
)


class TestSession:
    """Test Session dataclass"""
    
    def test_session_creation(self):
        """Test session object creation"""
        now = datetime.now()
        session = Session(
            session_id="test-session-1",
            incident_id="inc-001",
            created_at=now,
            last_activity=now,
            status=SessionStatus.CREATED,
            timeout_seconds=300
        )
        
        assert session.session_id == "test-session-1"
        assert session.incident_id == "inc-001"
        assert session.status == SessionStatus.CREATED
        assert session.timeout_seconds == 300
    
    def test_session_is_expired(self):
        """Test session expiration check"""
        past_time = datetime.now() - timedelta(seconds=400)
        session = Session(
            session_id="test-session-1",
            incident_id="inc-001",
            created_at=past_time,
            last_activity=past_time,
            status=SessionStatus.ACTIVE,
            timeout_seconds=300
        )
        
        assert session.is_expired() is True
    
    def test_session_not_expired(self):
        """Test session not expired"""
        now = datetime.now()
        session = Session(
            session_id="test-session-1",
            incident_id="inc-001",
            created_at=now,
            last_activity=now,
            status=SessionStatus.ACTIVE,
            timeout_seconds=300
        )
        
        assert session.is_expired() is False
    
    def test_session_update_activity(self):
        """Test updating session activity timestamp"""
        past_time = datetime.now() - timedelta(seconds=100)
        session = Session(
            session_id="test-session-1",
            incident_id="inc-001",
            created_at=past_time,
            last_activity=past_time,
            status=SessionStatus.ACTIVE,
            timeout_seconds=300
        )
        
        old_activity = session.last_activity
        time.sleep(0.1)
        session.update_activity()
        
        assert session.last_activity > old_activity
    
    def test_session_to_dict(self):
        """Test session serialization to dictionary"""
        now = datetime.now()
        session = Session(
            session_id="test-session-1",
            incident_id="inc-001",
            created_at=now,
            last_activity=now,
            status=SessionStatus.ACTIVE,
            timeout_seconds=300,
            metadata={"service": "test-service"}
        )
        
        result = session.to_dict()
        
        assert result["session_id"] == "test-session-1"
        assert result["incident_id"] == "inc-001"
        assert result["status"] == "active"
        assert result["timeout_seconds"] == 300
        assert result["metadata"]["service"] == "test-service"


class TestSessionManager:
    """Test SessionManager class"""
    
    def test_session_manager_initialization(self):
        """Test session manager initialization with default config"""
        manager = SessionManager()
        
        assert manager.timeout_seconds == 300
        assert manager.max_concurrent_sessions == 10
        assert manager.cleanup_enabled is True
    
    def test_session_manager_custom_config(self):
        """Test session manager with custom configuration"""
        config = {
            "timeout_seconds": 600,
            "max_concurrent_sessions": 20,
            "session_cleanup_enabled": False
        }
        manager = SessionManager(config)
        
        assert manager.timeout_seconds == 600
        assert manager.max_concurrent_sessions == 20
        assert manager.cleanup_enabled is False
    
    def test_create_session(self):
        """Test creating a new session"""
        manager = SessionManager()
        
        session = manager.create_session(
            incident_id="inc-001",
            metadata={"service": "payment-processor"}
        )
        
        assert session is not None
        assert session.incident_id == "inc-001"
        assert session.status == SessionStatus.CREATED
        assert session.metadata["service"] == "payment-processor"
        assert session.session_id.startswith("session-")
    
    def test_create_multiple_sessions(self):
        """Test creating multiple isolated sessions"""
        manager = SessionManager()
        
        session1 = manager.create_session("inc-001")
        session2 = manager.create_session("inc-002")
        
        assert session1.session_id != session2.session_id
        assert session1.incident_id != session2.incident_id
    
    def test_max_concurrent_sessions_limit(self):
        """Test max concurrent sessions enforcement"""
        config = {"max_concurrent_sessions": 2, "session_cleanup_enabled": False}
        manager = SessionManager(config)
        
        # Create 2 sessions (at limit)
        session1 = manager.create_session("inc-001")
        session2 = manager.create_session("inc-002")
        
        # Try to create 3rd session - should fail
        with pytest.raises(RuntimeError, match="Max concurrent sessions"):
            manager.create_session("inc-003")
    
    def test_get_session(self):
        """Test retrieving session by ID"""
        manager = SessionManager()
        
        created_session = manager.create_session("inc-001")
        retrieved_session = manager.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.incident_id == "inc-001"
    
    def test_get_session_not_found(self):
        """Test retrieving non-existent session"""
        manager = SessionManager()
        
        session = manager.get_session("non-existent-session")
        
        assert session is None
    
    def test_get_session_by_incident(self):
        """Test retrieving session by incident ID"""
        manager = SessionManager()
        
        created_session = manager.create_session("inc-001")
        retrieved_session = manager.get_session_by_incident("inc-001")
        
        assert retrieved_session is not None
        assert retrieved_session.incident_id == "inc-001"
        assert retrieved_session.session_id == created_session.session_id
    
    def test_activate_session(self):
        """Test activating a session"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        success = manager.activate_session(session.session_id)
        
        assert success is True
        assert session.status == SessionStatus.ACTIVE
    
    def test_mark_executing(self):
        """Test marking session as executing"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        manager.activate_session(session.session_id)
        success = manager.mark_executing(session.session_id)
        
        assert success is True
        assert session.status == SessionStatus.EXECUTING
    
    def test_complete_session(self):
        """Test completing a session"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        final_results = {"status": "success", "data": "test"}
        success = manager.complete_session(session.session_id, final_results)
        
        assert success is True
        assert session.status == SessionStatus.COMPLETED
        assert session.agent_results["final"] == final_results
    
    def test_fail_session(self):
        """Test marking session as failed"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        success = manager.fail_session(session.session_id, "Test error")
        
        assert success is True
        assert session.status == SessionStatus.FAILED
        assert session.metadata["error"] == "Test error"
    
    def test_terminate_session(self):
        """Test terminating a session"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        session_id = session.session_id
        
        success = manager.terminate_session(session_id)
        
        assert success is True
        assert manager.get_session(session_id) is None
    
    def test_cleanup_session(self):
        """Test cleaning up completed session"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        manager.complete_session(session.session_id)
        
        success = manager.cleanup_session(session.session_id)
        
        assert success is True
        assert manager.get_session(session.session_id) is None
    
    def test_cleanup_session_not_completed(self):
        """Test cleanup fails for active session"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        manager.activate_session(session.session_id)
        
        success = manager.cleanup_session(session.session_id)
        
        assert success is False
        assert manager.get_session(session.session_id) is not None
    
    def test_store_and_retrieve_agent_result(self):
        """Test storing and retrieving agent results"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        agent_result = {"summary": "test log analysis"}
        
        store_success = manager.store_agent_result(
            session.session_id,
            "log-analysis",
            agent_result
        )
        
        assert store_success is True
        
        retrieved_result = manager.get_agent_result(
            session.session_id,
            "log-analysis"
        )
        
        assert retrieved_result == agent_result
    
    def test_update_session_activity(self):
        """Test updating session activity timestamp"""
        manager = SessionManager()
        
        session = manager.create_session("inc-001")
        old_activity = session.last_activity
        
        time.sleep(0.1)
        success = manager.update_session_activity(session.session_id)
        
        assert success is True
        assert session.last_activity > old_activity
    
    def test_get_metrics(self):
        """Test retrieving session metrics"""
        manager = SessionManager()
        
        # Create and complete some sessions
        session1 = manager.create_session("inc-001")
        session2 = manager.create_session("inc-002")
        session3 = manager.create_session("inc-003")
        
        manager.complete_session(session1.session_id)
        manager.fail_session(session2.session_id)
        
        metrics = manager.get_metrics()
        
        assert metrics["total_sessions_created"] == 3
        assert metrics["total_sessions_completed"] == 1
        assert metrics["total_sessions_failed"] == 1
        assert metrics["active_sessions"] == 1  # session3 is still active
    
    def test_list_active_sessions(self):
        """Test listing active sessions"""
        manager = SessionManager()
        
        session1 = manager.create_session("inc-001")
        session2 = manager.create_session("inc-002")
        session3 = manager.create_session("inc-003")
        
        manager.activate_session(session1.session_id)
        manager.activate_session(session2.session_id)
        manager.complete_session(session3.session_id)
        
        active_sessions = manager.list_active_sessions()
        
        assert len(active_sessions) == 2
        assert all(s.status == SessionStatus.ACTIVE for s in active_sessions)
    
    def test_session_lifecycle_complete_flow(self):
        """Test complete session lifecycle from creation to cleanup"""
        manager = SessionManager()
        
        # Create session
        session = manager.create_session(
            incident_id="inc-001",
            metadata={"service": "payment-processor"}
        )
        assert session.status == SessionStatus.CREATED
        
        # Activate session
        manager.activate_session(session.session_id)
        assert session.status == SessionStatus.ACTIVE
        
        # Mark as executing
        manager.mark_executing(session.session_id)
        assert session.status == SessionStatus.EXECUTING
        
        # Store agent results
        manager.store_agent_result(session.session_id, "log-analysis", {"data": "test"})
        manager.store_agent_result(session.session_id, "root-cause", {"cause": "timeout"})
        
        # Complete session
        manager.complete_session(session.session_id, {"final": "success"})
        assert session.status == SessionStatus.COMPLETED
        
        # Cleanup session
        manager.cleanup_session(session.session_id)
        assert manager.get_session(session.session_id) is None


class TestSessionExpiration:
    """Test session expiration and cleanup"""
    
    def test_expired_session_cleanup(self):
        """Test automatic cleanup of expired sessions"""
        config = {"timeout_seconds": 1, "session_cleanup_enabled": True}
        manager = SessionManager(config)
        
        session = manager.create_session("inc-001")
        manager.activate_session(session.session_id)
        
        # Wait for session to expire
        time.sleep(1.5)
        
        # Trigger cleanup by trying to create new session
        manager._cleanup_expired_sessions()
        
        # Session should be cleaned up
        retrieved = manager.get_session(session.session_id)
        assert retrieved is None or retrieved.status == SessionStatus.EXPIRED
    
    def test_activate_expired_session_fails(self):
        """Test activating expired session fails"""
        config = {"timeout_seconds": 1}
        manager = SessionManager(config)
        
        session = manager.create_session("inc-001")
        
        # Wait for session to expire
        time.sleep(1.5)
        
        success = manager.activate_session(session.session_id)
        
        assert success is False
        assert session.status == SessionStatus.EXPIRED
