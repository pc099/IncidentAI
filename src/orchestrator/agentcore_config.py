"""
AgentCore Configuration Module

This module provides configuration for the Bedrock AgentCore runtime layer that manages
agent execution. It defines session management, security policies, and observability settings.

Requirements:
- 6.1: Agent orchestration and collaboration
- 10.3: Encrypted channels via Amazon Bedrock AgentCore
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class SecurityPolicyLevel(Enum):
    """Security policy levels for agent execution"""
    LEAST_PRIVILEGE = "least_privilege"
    STANDARD = "standard"
    ELEVATED = "elevated"


class MemoryRetentionStrategy(Enum):
    """Memory retention strategies for agent context"""
    PER_INCIDENT = "per_incident"
    PER_SESSION = "per_session"
    PERSISTENT = "persistent"


class LogLevel(Enum):
    """Logging levels for observability"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


@dataclass
class ObservabilityConfig:
    """Configuration for observability features"""
    logging: str = "detailed"
    metrics: bool = True
    tracing: bool = True
    log_level: LogLevel = LogLevel.DETAILED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "logging": self.logging,
            "metrics": self.metrics,
            "tracing": self.tracing,
            "log_level": self.log_level.value
        }


@dataclass
class SecurityConfig:
    """Configuration for security policies"""
    policy_level: SecurityPolicyLevel = SecurityPolicyLevel.LEAST_PRIVILEGE
    encrypted_channels: bool = True
    iam_role_arn: Optional[str] = None
    allowed_actions: list = field(default_factory=lambda: [
        "bedrock:InvokeModel",
        "bedrock:Retrieve",
        "s3:GetObject",
        "dynamodb:Query",
        "dynamodb:PutItem",
        "logs:PutLogEvents",
        "cloudwatch:PutMetricData"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "policy_level": self.policy_level.value,
            "encrypted_channels": self.encrypted_channels,
            "iam_role_arn": self.iam_role_arn,
            "allowed_actions": self.allowed_actions
        }


@dataclass
class SessionConfig:
    """Configuration for session management"""
    timeout_seconds: int = 300  # 5 minutes
    max_concurrent_sessions: int = 10
    session_cleanup_enabled: bool = True
    idle_timeout_seconds: int = 180  # 3 minutes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "session_cleanup_enabled": self.session_cleanup_enabled,
            "idle_timeout_seconds": self.idle_timeout_seconds
        }


@dataclass
class MemoryConfig:
    """Configuration for memory management"""
    retention_strategy: MemoryRetentionStrategy = MemoryRetentionStrategy.PER_INCIDENT
    max_context_size_kb: int = 100
    enable_context_compression: bool = True
    persist_intermediate_results: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "retention_strategy": self.retention_strategy.value,
            "max_context_size_kb": self.max_context_size_kb,
            "enable_context_compression": self.enable_context_compression,
            "persist_intermediate_results": self.persist_intermediate_results
        }


@dataclass
class AgentCoreConfig:
    """
    Complete AgentCore configuration for the Bedrock runtime layer.
    
    This configuration manages:
    - Session lifecycle and timeouts
    - Memory retention per incident
    - Security policies with least privilege
    - Observability (logging, metrics, tracing)
    
    Requirements:
    - 6.1: WHEN an incident is triggered, THE Orchestrator SHALL invoke agents in sequence
    - 10.3: WHEN transmitting data between agents, THE System SHALL use encrypted channels
    """
    
    session: SessionConfig = field(default_factory=SessionConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    
    # Agent execution configuration
    agent_sequence: list = field(default_factory=lambda: [
        "log-analysis",
        "root-cause",
        "fix-recommendation",
        "communication"
    ])
    
    # Retry configuration
    max_retries: int = 2
    retry_backoff_base_seconds: int = 1  # Exponential backoff: 1s, 2s, 4s
    
    # Performance configuration
    agent_handoff_timeout_seconds: int = 1
    max_processing_time_seconds: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format for AgentCore runtime.
        
        Returns:
            Dictionary containing all configuration settings
        """
        return {
            "session": self.session.to_dict(),
            "memory": self.memory.to_dict(),
            "security": self.security.to_dict(),
            "observability": self.observability.to_dict(),
            "agent_sequence": self.agent_sequence,
            "max_retries": self.max_retries,
            "retry_backoff_base_seconds": self.retry_backoff_base_seconds,
            "agent_handoff_timeout_seconds": self.agent_handoff_timeout_seconds,
            "max_processing_time_seconds": self.max_processing_time_seconds
        }
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        if self.session.timeout_seconds <= 0:
            raise ValueError("Session timeout must be positive")
        
        if self.session.timeout_seconds < self.max_processing_time_seconds:
            raise ValueError(
                "Session timeout must be >= max processing time"
            )
        
        if self.memory.max_context_size_kb <= 0:
            raise ValueError("Max context size must be positive")
        
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        
        if self.agent_handoff_timeout_seconds <= 0:
            raise ValueError("Agent handoff timeout must be positive")
        
        if len(self.agent_sequence) == 0:
            raise ValueError("Agent sequence cannot be empty")
        
        # Validate agent sequence matches expected agents
        expected_agents = {
            "log-analysis",
            "root-cause",
            "fix-recommendation",
            "communication"
        }
        if set(self.agent_sequence) != expected_agents:
            raise ValueError(
                f"Agent sequence must contain exactly: {expected_agents}"
            )
        
        return True


# Default configuration instance
DEFAULT_AGENTCORE_CONFIG = AgentCoreConfig()


def get_default_config() -> AgentCoreConfig:
    """
    Get the default AgentCore configuration.
    
    Returns:
        Default AgentCoreConfig instance with:
        - Session timeout: 300 seconds (5 minutes)
        - Memory retention: per incident
        - Security policy: least privilege
        - Observability: detailed logging, metrics, and tracing enabled
    """
    return AgentCoreConfig()


def create_custom_config(
    session_timeout: Optional[int] = None,
    memory_retention: Optional[MemoryRetentionStrategy] = None,
    security_policy: Optional[SecurityPolicyLevel] = None,
    log_level: Optional[LogLevel] = None,
    iam_role_arn: Optional[str] = None
) -> AgentCoreConfig:
    """
    Create a custom AgentCore configuration.
    
    Args:
        session_timeout: Session timeout in seconds (default: 300)
        memory_retention: Memory retention strategy (default: PER_INCIDENT)
        security_policy: Security policy level (default: LEAST_PRIVILEGE)
        log_level: Logging level (default: DETAILED)
        iam_role_arn: IAM role ARN for agent execution (optional)
    
    Returns:
        Customized AgentCoreConfig instance
    """
    config = AgentCoreConfig()
    
    if session_timeout is not None:
        config.session.timeout_seconds = session_timeout
    
    if memory_retention is not None:
        config.memory.retention_strategy = memory_retention
    
    if security_policy is not None:
        config.security.policy_level = security_policy
    
    if log_level is not None:
        config.observability.log_level = log_level
    
    if iam_role_arn is not None:
        config.security.iam_role_arn = iam_role_arn
    
    config.validate()
    return config
