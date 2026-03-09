"""
Memory Manager for Enhanced Orchestrator

Manages agent memory and context across incident processing sessions.
Provides episodic memory capabilities for agent learning and context retention.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import boto3

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory storage"""
    EPISODIC = "episodic"      # Session-specific memories
    SEMANTIC = "semantic"      # General knowledge and patterns
    PROCEDURAL = "procedural"  # Learned procedures and workflows


# Alias for backward compatibility
ContextType = MemoryType


@dataclass
class MemoryEntry:
    """Individual memory entry"""
    memory_id: str
    session_id: str
    agent_name: str
    memory_type: MemoryType
    content: Dict[str, Any]
    created_at: datetime
    importance_score: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


# Alias for backward compatibility
@dataclass
class ContextEntry:
    """Individual context entry (alias for MemoryEntry)"""
    entry_id: str
    context_type: MemoryType
    agent_name: str
    timestamp: datetime
    data: Dict[str, Any]
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entry_id": self.entry_id,
            "context_type": self.context_type.value if isinstance(self.context_type, Enum) else self.context_type,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "size_bytes": self.size_bytes
        }


class MemoryManager:
    """
    Memory management system for agent orchestration
    
    Provides episodic memory that allows agents to learn from past interactions
    and maintain context across incident processing sessions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize memory manager
        
        Args:
            config: Memory configuration options
        """
        self.config = config or {}
        
        # Memory storage (in production, this would be DynamoDB)
        self.session_memories: Dict[str, List[MemoryEntry]] = {}
        self.global_memories: Dict[str, MemoryEntry] = {}
        
        # Configuration
        self.max_session_memories = self.config.get("max_session_memories", 100)
        self.memory_retention_days = self.config.get("memory_retention_days", 30)
        self.importance_threshold = self.config.get("importance_threshold", 0.7)
        
        # Memory statistics
        self.stats = {
            "total_memories": 0,
            "session_memories": 0,
            "global_memories": 0,
            "memory_retrievals": 0,
            "memory_consolidations": 0
        }
        
        logger.info("Memory manager initialized")
    
    def store_memory(
        self,
        session_id: str,
        agent_name: str,
        memory_type: MemoryType,
        content: Dict[str, Any],
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Store a memory entry
        
        Args:
            session_id: Session identifier
            agent_name: Agent that created the memory
            memory_type: Type of memory
            content: Memory content
            importance_score: Importance score (0.0-1.0)
            tags: Optional tags for categorization
            
        Returns:
            Memory ID
        """
        memory_id = f"{session_id}_{agent_name}_{int(datetime.now().timestamp())}"
        
        memory_entry = MemoryEntry(
            memory_id=memory_id,
            session_id=session_id,
            agent_name=agent_name,
            memory_type=memory_type,
            content=content,
            created_at=datetime.now(),
            importance_score=importance_score,
            tags=tags or []
        )
        
        # Store in session memories
        if session_id not in self.session_memories:
            self.session_memories[session_id] = []
        
        self.session_memories[session_id].append(memory_entry)
        
        # Update statistics
        self.stats["total_memories"] += 1
        self.stats["session_memories"] += 1
        
        # Cleanup old memories if needed
        self._cleanup_session_memories(session_id)
        
        logger.debug(f"Stored memory: {memory_id} for agent {agent_name}")
        return memory_id
    
    def retrieve_memories(
        self,
        session_id: str,
        agent_name: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Retrieve memories based on criteria
        
        Args:
            session_id: Session identifier
            agent_name: Optional agent filter
            memory_type: Optional memory type filter
            tags: Optional tag filters
            limit: Maximum number of memories to return
            
        Returns:
            List of matching memory entries
        """
        self.stats["memory_retrievals"] += 1
        
        # Get session memories
        session_memories = self.session_memories.get(session_id, [])
        
        # Apply filters
        filtered_memories = []
        for memory in session_memories:
            # Agent filter
            if agent_name and memory.agent_name != agent_name:
                continue
            
            # Memory type filter
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Tag filter
            if tags and not any(tag in memory.tags for tag in tags):
                continue
            
            filtered_memories.append(memory)
        
        # Sort by importance and recency
        filtered_memories.sort(
            key=lambda m: (m.importance_score, m.created_at),
            reverse=True
        )
        
        # Update access statistics
        for memory in filtered_memories[:limit]:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
        
        logger.debug(f"Retrieved {len(filtered_memories[:limit])} memories for session {session_id}")
        return filtered_memories[:limit]
    
    def store_agent_result(
        self,
        session_id: str,
        agent_name: str,
        result: Dict[str, Any],
        execution_time: float,
        success: bool
    ):
        """
        Store agent execution result as memory
        
        Args:
            session_id: Session identifier
            agent_name: Agent name
            result: Agent execution result
            execution_time: Execution time in seconds
            success: Whether execution was successful
        """
        # Calculate importance based on success and execution time
        importance_score = 0.8 if success else 0.3
        if execution_time > 60:  # Long-running operations are more important
            importance_score += 0.1
        
        memory_content = {
            "agent_result": result,
            "execution_time": execution_time,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        tags = [agent_name, "execution_result"]
        if success:
            tags.append("successful")
        else:
            tags.append("failed")
        
        self.store_memory(
            session_id=session_id,
            agent_name=agent_name,
            memory_type=MemoryType.EPISODIC,
            content=memory_content,
            importance_score=min(1.0, importance_score),
            tags=tags
        )
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete session context for agents
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session context dictionary
        """
        session_memories = self.session_memories.get(session_id, [])
        
        # Organize memories by agent
        agent_memories = {}
        for memory in session_memories:
            agent_name = memory.agent_name
            if agent_name not in agent_memories:
                agent_memories[agent_name] = []
            agent_memories[agent_name].append(memory)
        
        # Create context summary
        context = {
            "session_id": session_id,
            "total_memories": len(session_memories),
            "agent_memories": {},
            "important_memories": [],
            "recent_memories": []
        }
        
        # Add agent-specific memories
        for agent_name, memories in agent_memories.items():
            context["agent_memories"][agent_name] = [
                {
                    "memory_id": m.memory_id,
                    "content": m.content,
                    "importance_score": m.importance_score,
                    "created_at": m.created_at.isoformat(),
                    "tags": m.tags
                }
                for m in memories[-5:]  # Last 5 memories per agent
            ]
        
        # Add important memories (high importance score)
        important_memories = [
            m for m in session_memories 
            if m.importance_score >= self.importance_threshold
        ]
        important_memories.sort(key=lambda m: m.importance_score, reverse=True)
        
        context["important_memories"] = [
            {
                "memory_id": m.memory_id,
                "agent_name": m.agent_name,
                "content": m.content,
                "importance_score": m.importance_score
            }
            for m in important_memories[:10]
        ]
        
        # Add recent memories
        recent_memories = sorted(session_memories, key=lambda m: m.created_at, reverse=True)
        context["recent_memories"] = [
            {
                "memory_id": m.memory_id,
                "agent_name": m.agent_name,
                "content": m.content,
                "created_at": m.created_at.isoformat()
            }
            for m in recent_memories[:10]
        ]
        
        return context
    
    def consolidate_session_memories(self, session_id: str) -> Dict[str, Any]:
        """
        Consolidate session memories into global knowledge
        
        Args:
            session_id: Session identifier
            
        Returns:
            Consolidation summary
        """
        self.stats["memory_consolidations"] += 1
        
        session_memories = self.session_memories.get(session_id, [])
        if not session_memories:
            return {"consolidated_memories": 0, "patterns_identified": 0}
        
        # Identify important patterns
        important_memories = [
            m for m in session_memories 
            if m.importance_score >= self.importance_threshold
        ]
        
        # Group by agent and extract patterns
        agent_patterns = {}
        for memory in important_memories:
            agent_name = memory.agent_name
            if agent_name not in agent_patterns:
                agent_patterns[agent_name] = []
            
            # Extract key patterns from memory content
            if "error_patterns" in memory.content:
                agent_patterns[agent_name].extend(memory.content["error_patterns"])
            
            if "success_patterns" in memory.content:
                agent_patterns[agent_name].extend(memory.content["success_patterns"])
        
        # Store consolidated patterns as global memories
        consolidated_count = 0
        for agent_name, patterns in agent_patterns.items():
            if patterns:
                global_memory_id = f"global_{agent_name}_{int(datetime.now().timestamp())}"
                
                global_memory = MemoryEntry(
                    memory_id=global_memory_id,
                    session_id="global",
                    agent_name=agent_name,
                    memory_type=MemoryType.SEMANTIC,
                    content={"patterns": patterns, "source_session": session_id},
                    created_at=datetime.now(),
                    importance_score=0.9,
                    tags=["consolidated", "patterns", agent_name]
                )
                
                self.global_memories[global_memory_id] = global_memory
                consolidated_count += 1
        
        self.stats["global_memories"] += consolidated_count
        
        logger.info(f"Consolidated {consolidated_count} memories from session {session_id}")
        
        return {
            "consolidated_memories": consolidated_count,
            "patterns_identified": sum(len(patterns) for patterns in agent_patterns.values()),
            "agent_patterns": agent_patterns
        }
    
    def clear_session_memory(self, session_id: str):
        """
        Clear all memories for a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.session_memories:
            memory_count = len(self.session_memories[session_id])
            del self.session_memories[session_id]
            self.stats["session_memories"] -= memory_count
            logger.debug(f"Cleared {memory_count} memories for session {session_id}")
    
    def _cleanup_session_memories(self, session_id: str):
        """Clean up old session memories to maintain performance"""
        session_memories = self.session_memories.get(session_id, [])
        
        if len(session_memories) > self.max_session_memories:
            # Sort by importance and recency, keep the most important
            session_memories.sort(
                key=lambda m: (m.importance_score, m.created_at),
                reverse=True
            )
            
            # Keep only the most important memories
            self.session_memories[session_id] = session_memories[:self.max_session_memories]
            
            removed_count = len(session_memories) - self.max_session_memories
            self.stats["session_memories"] -= removed_count
            
            logger.debug(f"Cleaned up {removed_count} old memories for session {session_id}")
    
    def cleanup_expired_memories(self):
        """Clean up expired memories across all sessions"""
        cutoff_date = datetime.now() - timedelta(days=self.memory_retention_days)
        
        # Clean up session memories
        total_removed = 0
        for session_id, memories in list(self.session_memories.items()):
            original_count = len(memories)
            
            # Filter out expired memories
            self.session_memories[session_id] = [
                m for m in memories if m.created_at > cutoff_date
            ]
            
            removed_count = original_count - len(self.session_memories[session_id])
            total_removed += removed_count
            
            # Remove empty sessions
            if not self.session_memories[session_id]:
                del self.session_memories[session_id]
        
        # Clean up global memories
        expired_global = [
            memory_id for memory_id, memory in self.global_memories.items()
            if memory.created_at < cutoff_date
        ]
        
        for memory_id in expired_global:
            del self.global_memories[memory_id]
        
        total_removed += len(expired_global)
        self.stats["session_memories"] -= (total_removed - len(expired_global))
        self.stats["global_memories"] -= len(expired_global)
        
        if total_removed > 0:
            logger.info(f"Cleaned up {total_removed} expired memories")
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            **self.stats,
            "active_sessions": len(self.session_memories),
            "avg_memories_per_session": (
                sum(len(memories) for memories in self.session_memories.values()) /
                max(len(self.session_memories), 1)
            ),
            "memory_retention_days": self.memory_retention_days,
            "max_session_memories": self.max_session_memories
        }