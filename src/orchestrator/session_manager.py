"""
Session Management Module for Bedrock AgentCore

This module manages isolated sessions for incident processing, including session
lifecycle management (create, execute, terminate) and resource cleanup.

Requirements:
- 6.1: Create isolated sessions per incident
- 6.5: Clean up resources after incident resolution
"""

import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class SessionStatus(Enum):
    """Session lifecycle states"""
    CREATED = "created"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


@dataclass
class Session:
    """
    Represents an isolated session for incident processing.
    
    Each incident gets its own session to ensure isolation and proper
    resource management.
    """
    session_id: str
    incident_id: str
    created_at: datetime
    last_activity: datetime
    status: SessionStatus
    timeout_seconds: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session has exceeded timeout"""
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        return elapsed > self.timeout_seconds
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary format"""
        return {
            "session_id": self.session_id,
            "incident_id": self.incident_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.status.value,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "agent_results": self.agent_results
        }


class SessionManager:
    """
    Manages session lifecycle for incident processing.
    
    Provides:
    - Isolated session creation per incident
    - Session lifecycle management (create, execute, terminate)
    - Resource cleanup after incident resolution
    - Automatic expiration of idle sessions
    
    Requirements:
    - 6.1: WHEN an incident is triggered, create isolated session
    - 6.5: WHEN orchestration completes, clean up session resources
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize session manager.
        
        Args:
            config: Optional configuration dictionary with:
                - timeout_seconds: Session timeout (default: 300)
                - max_concurrent_sessions: Max active sessions (default: 10)
                - session_cleanup_enabled: Enable auto cleanup (default: True)
        """
        self.config = config or {}
        self.timeout_seconds = self.config.get("timeout_seconds", 300)
        self.max_concurrent_sessions = self.config.get("max_concurrent_sessions", 10)
        self.cleanup_enabled = self.config.get("session_cleanup_enabled", True)
        
        # Active sessions storage
        self._sessions: Dict[str, Session] = {}
        
        # Session metrics
        self._total_sessions_created = 0
        self._total_sessions_completed = 0
        self._total_sessions_failed = 0
    
    def create_session(
        self,
        incident_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """
        Create a new isolated session for incident processing.
        
        Args:
            incident_id: Unique identifier for the incident
            metadata: Optional metadata to attach to session
        
        Returns:
            Created Session object
        
        Raises:
            RuntimeError: If max concurrent sessions exceeded
        
        Requirements:
            - 6.1: Create isolated sessions per incident
        """
        # Check concurrent session limit
        active_sessions = self._count_active_sessions()
        if active_sessions >= self.max_concurrent_sessions:
            # Try cleanup first
            if self.cleanup_enabled:
                self._cleanup_expired_sessions()
                active_sessions = self._count_active_sessions()
            
            if active_sessions >= self.max_concurrent_sessions:
                raise RuntimeError(
                    f"Max concurrent sessions ({self.max_concurrent_sessions}) exceeded"
                )
        
        # Generate unique session ID
        session_id = f"session-{uuid.uuid4()}"
        
        # Create session
        now = datetime.now()
        session = Session(
            session_id=session_id,
            incident_id=incident_id,
            created_at=now,
            last_activity=now,
            status=SessionStatus.CREATED,
            timeout_seconds=self.timeout_seconds,
            metadata=metadata or {}
        )
        
        # Store session
        self._sessions[session_id] = session
        self._total_sessions_created += 1
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session object if found, None otherwise
        """
        return self._sessions.get(session_id)
    
    def get_session_by_incident(self, incident_id: str) -> Optional[Session]:
        """
        Retrieve session by incident ID.
        
        Args:
            incident_id: Incident identifier
        
        Returns:
            Session object if found, None otherwise
        """
        for session in self._sessions.values():
            if session.incident_id == incident_id:
                return session
        return None
    
    def activate_session(self, session_id: str) -> bool:
        """
        Activate a session for execution.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if activated successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        if session.is_expired():
            session.status = SessionStatus.EXPIRED
            return False
        
        session.status = SessionStatus.ACTIVE
        session.update_activity()
        return True
    
    def mark_executing(self, session_id: str) -> bool:
        """
        Mark session as currently executing agents.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if marked successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.EXECUTING
        session.update_activity()
        return True
    
    def complete_session(
        self,
        session_id: str,
        final_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Mark session as completed successfully.
        
        Args:
            session_id: Session identifier
            final_results: Optional final results to store
        
        Returns:
            True if completed successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.COMPLETED
        session.update_activity()
        
        if final_results:
            session.agent_results["final"] = final_results
        
        self._total_sessions_completed += 1
        return True
    
    def fail_session(
        self,
        session_id: str,
        error: Optional[str] = None
    ) -> bool:
        """
        Mark session as failed.
        
        Args:
            session_id: Session identifier
            error: Optional error message
        
        Returns:
            True if marked as failed successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.FAILED
        session.update_activity()
        
        if error:
            session.metadata["error"] = error
        
        self._total_sessions_failed += 1
        return True
    
    def terminate_session(self, session_id: str) -> bool:
        """
        Terminate and clean up a session.
        
        This removes the session from active storage and frees resources.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if terminated successfully
        
        Requirements:
            - 6.5: Clean up resources after incident resolution
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.status = SessionStatus.TERMINATED
        
        # Remove from active sessions
        del self._sessions[session_id]
        
        return True
    
    def cleanup_session(self, session_id: str) -> bool:
        """
        Clean up session resources after completion or failure.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if cleaned up successfully
        
        Requirements:
            - 6.5: Clean up resources after incident resolution
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Only cleanup completed, failed, or expired sessions
        if session.status not in [
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.EXPIRED
        ]:
            return False
        
        # Clear agent results to free memory
        session.agent_results.clear()
        
        # Remove from active sessions
        return self.terminate_session(session_id)
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if updated successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.update_activity()
        return True
    
    def store_agent_result(
        self,
        session_id: str,
        agent_name: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        Store agent execution result in session.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            result: Agent execution result
        
        Returns:
            True if stored successfully
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.agent_results[agent_name] = result
        session.update_activity()
        return True
    
    def get_agent_result(
        self,
        session_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent execution result from session.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
        
        Returns:
            Agent result if found, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.agent_results.get(agent_name)
    
    def _count_active_sessions(self) -> int:
        """Count sessions that are not completed, failed, or terminated"""
        return sum(
            1 for session in self._sessions.values()
            if session.status not in [
                SessionStatus.COMPLETED,
                SessionStatus.FAILED,
                SessionStatus.TERMINATED,
                SessionStatus.EXPIRED
            ]
        )
    
    def _cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions automatically.
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.cleanup_enabled:
            return 0
        
        expired_sessions = []
        for session_id, session in self._sessions.items():
            if session.is_expired() and session.status not in [
                SessionStatus.COMPLETED,
                SessionStatus.FAILED,
                SessionStatus.TERMINATED
            ]:
                session.status = SessionStatus.EXPIRED
                expired_sessions.append(session_id)
        
        # Clean up expired sessions
        for session_id in expired_sessions:
            self.cleanup_session(session_id)
        
        return len(expired_sessions)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get session manager metrics.
        
        Returns:
            Dictionary containing session metrics
        """
        return {
            "total_sessions_created": self._total_sessions_created,
            "total_sessions_completed": self._total_sessions_completed,
            "total_sessions_failed": self._total_sessions_failed,
            "active_sessions": self._count_active_sessions(),
            "total_sessions_in_memory": len(self._sessions)
        }
    
    def list_active_sessions(self) -> list[Session]:
        """
        List all active sessions.
        
        Returns:
            List of active Session objects
        """
        return [
            session for session in self._sessions.values()
            if session.status not in [
                SessionStatus.COMPLETED,
                SessionStatus.FAILED,
                SessionStatus.TERMINATED,
                SessionStatus.EXPIRED
            ]
        ]
