"""
Memory Management Module for Agent Context

This module manages memory and context for agent execution, including storing
intermediate results for agent handoffs and maintaining conversation context
across agent invocations.

Requirements:
- 6.2: Store intermediate results for agent handoffs
- 6.2: Maintain conversation context across agent invocations
"""

import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ContextType(Enum):
    """Types of context stored in memory"""
    AGENT_INPUT = "agent_input"
    AGENT_OUTPUT = "agent_output"
    INTERMEDIATE_RESULT = "intermediate_result"
    CONVERSATION = "conversation"
    METADATA = "metadata"


@dataclass
class ContextEntry:
    """
    Represents a single context entry in memory.
    
    Each entry captures a piece of information from the agent execution flow.
    """
    entry_id: str
    context_type: ContextType
    agent_name: str
    timestamp: datetime
    data: Dict[str, Any]
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context entry to dictionary format"""
        return {
            "entry_id": self.entry_id,
            "context_type": self.context_type.value,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "size_bytes": self.size_bytes
        }


class MemoryManager:
    """
    Manages memory and context for agent execution.
    
    Provides:
    - Storage of intermediate results for agent handoffs
    - Conversation context maintenance across agent invocations
    - Context compression when size limits are exceeded
    - Context retrieval for agent execution
    
    Requirements:
    - 6.2: WHEN an agent completes, store output for next agent
    - 6.2: WHEN an agent is invoked, provide context from previous agents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize memory manager.
        
        Args:
            config: Optional configuration dictionary with:
                - max_context_size_kb: Max context size in KB (default: 100)
                - enable_context_compression: Enable compression (default: True)
                - persist_intermediate_results: Persist results (default: True)
        """
        self.config = config or {}
        self.max_context_size_kb = self.config.get("max_context_size_kb", 100)
        self.enable_compression = self.config.get("enable_context_compression", True)
        self.persist_results = self.config.get("persist_intermediate_results", True)
        
        # Memory storage per session
        self._session_memory: Dict[str, List[ContextEntry]] = {}
        
        # Context index for fast retrieval
        self._context_index: Dict[str, Dict[str, List[str]]] = {}
        
        # Memory metrics
        self._total_entries_stored = 0
        self._total_bytes_stored = 0
        self._compression_count = 0
    
    def store_agent_input(
        self,
        session_id: str,
        agent_name: str,
        input_data: Dict[str, Any]
    ) -> str:
        """
        Store agent input data.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            input_data: Input data for the agent
        
        Returns:
            Entry ID of stored context
        
        Requirements:
            - 6.2: Store intermediate results for agent handoffs
        """
        return self._store_context(
            session_id=session_id,
            agent_name=agent_name,
            context_type=ContextType.AGENT_INPUT,
            data=input_data
        )
    
    def store_agent_output(
        self,
        session_id: str,
        agent_name: str,
        output_data: Dict[str, Any]
    ) -> str:
        """
        Store agent output data for handoff to next agent.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            output_data: Output data from the agent
        
        Returns:
            Entry ID of stored context
        
        Requirements:
            - 6.2: Store intermediate results for agent handoffs
        """
        return self._store_context(
            session_id=session_id,
            agent_name=agent_name,
            context_type=ContextType.AGENT_OUTPUT,
            data=output_data
        )
    
    def store_intermediate_result(
        self,
        session_id: str,
        agent_name: str,
        result_data: Dict[str, Any]
    ) -> str:
        """
        Store intermediate processing result.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            result_data: Intermediate result data
        
        Returns:
            Entry ID of stored context
        
        Requirements:
            - 6.2: Store intermediate results for agent handoffs
        """
        if not self.persist_results:
            return ""
        
        return self._store_context(
            session_id=session_id,
            agent_name=agent_name,
            context_type=ContextType.INTERMEDIATE_RESULT,
            data=result_data
        )
    
    def store_conversation_context(
        self,
        session_id: str,
        agent_name: str,
        conversation_data: Dict[str, Any]
    ) -> str:
        """
        Store conversation context for multi-turn interactions.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            conversation_data: Conversation context data
        
        Returns:
            Entry ID of stored context
        
        Requirements:
            - 6.2: Maintain conversation context across agent invocations
        """
        return self._store_context(
            session_id=session_id,
            agent_name=agent_name,
            context_type=ContextType.CONVERSATION,
            data=conversation_data
        )
    
    def get_agent_output(
        self,
        session_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve agent output data.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
        
        Returns:
            Agent output data if found, None otherwise
        
        Requirements:
            - 6.2: Provide context from previous agents
        """
        entries = self._get_context_by_type(
            session_id=session_id,
            agent_name=agent_name,
            context_type=ContextType.AGENT_OUTPUT
        )
        
        if not entries:
            return None
        
        # Return most recent output
        return entries[-1].data
    
    def get_previous_agent_outputs(
        self,
        session_id: str,
        current_agent: str,
        agent_sequence: List[str]
    ) -> Dict[str, Any]:
        """
        Get outputs from all previous agents in the sequence.
        
        Args:
            session_id: Session identifier
            current_agent: Name of current agent
            agent_sequence: Ordered list of agent names
        
        Returns:
            Dictionary mapping agent names to their outputs
        
        Requirements:
            - 6.2: Provide context from previous agents for handoffs
        """
        previous_outputs = {}
        
        try:
            current_index = agent_sequence.index(current_agent)
        except ValueError:
            return previous_outputs
        
        # Get outputs from all previous agents
        for i in range(current_index):
            agent_name = agent_sequence[i]
            output = self.get_agent_output(session_id, agent_name)
            if output:
                previous_outputs[agent_name] = output
        
        return previous_outputs
    
    def get_conversation_context(
        self,
        session_id: str,
        agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation context.
        
        Args:
            session_id: Session identifier
            agent_name: Optional agent name to filter by
        
        Returns:
            List of conversation context entries
        
        Requirements:
            - 6.2: Maintain conversation context across agent invocations
        """
        if agent_name:
            entries = self._get_context_by_type(
                session_id=session_id,
                agent_name=agent_name,
                context_type=ContextType.CONVERSATION
            )
        else:
            entries = self._get_all_context_by_type(
                session_id=session_id,
                context_type=ContextType.CONVERSATION
            )
        
        return [entry.data for entry in entries]
    
    def get_full_context(
        self,
        session_id: str,
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get complete context for a session or agent.
        
        Args:
            session_id: Session identifier
            agent_name: Optional agent name to filter by
        
        Returns:
            Dictionary containing all context data organized by type
        """
        if session_id not in self._session_memory:
            return {}
        
        entries = self._session_memory[session_id]
        
        if agent_name:
            entries = [e for e in entries if e.agent_name == agent_name]
        
        # Organize by context type
        context = {
            "agent_inputs": [],
            "agent_outputs": [],
            "intermediate_results": [],
            "conversations": [],
            "metadata": []
        }
        
        for entry in entries:
            if entry.context_type == ContextType.AGENT_INPUT:
                context["agent_inputs"].append(entry.to_dict())
            elif entry.context_type == ContextType.AGENT_OUTPUT:
                context["agent_outputs"].append(entry.to_dict())
            elif entry.context_type == ContextType.INTERMEDIATE_RESULT:
                context["intermediate_results"].append(entry.to_dict())
            elif entry.context_type == ContextType.CONVERSATION:
                context["conversations"].append(entry.to_dict())
            elif entry.context_type == ContextType.METADATA:
                context["metadata"].append(entry.to_dict())
        
        return context
    
    def clear_session_memory(self, session_id: str) -> bool:
        """
        Clear all memory for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if cleared successfully
        """
        if session_id not in self._session_memory:
            return False
        
        # Clear memory
        del self._session_memory[session_id]
        
        # Clear index
        if session_id in self._context_index:
            del self._context_index[session_id]
        
        return True
    
    def get_memory_size(self, session_id: str) -> int:
        """
        Get total memory size for a session in bytes.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Total size in bytes
        """
        if session_id not in self._session_memory:
            return 0
        
        return sum(
            entry.size_bytes
            for entry in self._session_memory[session_id]
        )
    
    def compress_context(self, session_id: str) -> bool:
        """
        Compress context when size exceeds limits.
        
        This removes intermediate results and keeps only essential data.
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if compression performed
        """
        if not self.enable_compression:
            return False
        
        if session_id not in self._session_memory:
            return False
        
        current_size_kb = self.get_memory_size(session_id) / 1024
        
        if current_size_kb <= self.max_context_size_kb:
            return False
        
        # Remove intermediate results (least important)
        entries = self._session_memory[session_id]
        compressed_entries = [
            entry for entry in entries
            if entry.context_type != ContextType.INTERMEDIATE_RESULT
        ]
        
        self._session_memory[session_id] = compressed_entries
        self._compression_count += 1
        
        # Rebuild index
        self._rebuild_index(session_id)
        
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get memory manager metrics.
        
        Returns:
            Dictionary containing memory metrics
        """
        total_sessions = len(self._session_memory)
        total_size_kb = sum(
            self.get_memory_size(sid) / 1024
            for sid in self._session_memory.keys()
        )
        
        return {
            "total_entries_stored": self._total_entries_stored,
            "total_bytes_stored": self._total_bytes_stored,
            "compression_count": self._compression_count,
            "active_sessions": total_sessions,
            "total_memory_kb": round(total_size_kb, 2),
            "average_memory_per_session_kb": (
                round(total_size_kb / total_sessions, 2)
                if total_sessions > 0 else 0
            )
        }
    
    def _store_context(
        self,
        session_id: str,
        agent_name: str,
        context_type: ContextType,
        data: Dict[str, Any]
    ) -> str:
        """Internal method to store context entry"""
        # Generate entry ID
        entry_id = f"{session_id}-{agent_name}-{context_type.value}-{len(self._session_memory.get(session_id, []))}"
        
        # Calculate size
        data_json = json.dumps(data)
        size_bytes = len(data_json.encode('utf-8'))
        
        # Create entry
        entry = ContextEntry(
            entry_id=entry_id,
            context_type=context_type,
            agent_name=agent_name,
            timestamp=datetime.now(),
            data=data,
            size_bytes=size_bytes
        )
        
        # Initialize session memory if needed
        if session_id not in self._session_memory:
            self._session_memory[session_id] = []
            self._context_index[session_id] = {}
        
        # Store entry
        self._session_memory[session_id].append(entry)
        
        # Update index
        self._update_index(session_id, agent_name, context_type, entry_id)
        
        # Update metrics
        self._total_entries_stored += 1
        self._total_bytes_stored += size_bytes
        
        # Check if compression needed
        if self.enable_compression:
            self.compress_context(session_id)
        
        return entry_id
    
    def _get_context_by_type(
        self,
        session_id: str,
        agent_name: str,
        context_type: ContextType
    ) -> List[ContextEntry]:
        """Internal method to retrieve context entries by type"""
        if session_id not in self._session_memory:
            return []
        
        return [
            entry for entry in self._session_memory[session_id]
            if entry.agent_name == agent_name and entry.context_type == context_type
        ]
    
    def _get_all_context_by_type(
        self,
        session_id: str,
        context_type: ContextType
    ) -> List[ContextEntry]:
        """Internal method to retrieve all context entries of a type"""
        if session_id not in self._session_memory:
            return []
        
        return [
            entry for entry in self._session_memory[session_id]
            if entry.context_type == context_type
        ]
    
    def _update_index(
        self,
        session_id: str,
        agent_name: str,
        context_type: ContextType,
        entry_id: str
    ):
        """Update context index for fast retrieval"""
        index_key = f"{agent_name}:{context_type.value}"
        
        if index_key not in self._context_index[session_id]:
            self._context_index[session_id][index_key] = []
        
        self._context_index[session_id][index_key].append(entry_id)
    
    def _rebuild_index(self, session_id: str):
        """Rebuild index after compression"""
        if session_id not in self._session_memory:
            return
        
        # Clear existing index
        self._context_index[session_id] = {}
        
        # Rebuild from entries
        for entry in self._session_memory[session_id]:
            self._update_index(
                session_id,
                entry.agent_name,
                entry.context_type,
                entry.entry_id
            )
