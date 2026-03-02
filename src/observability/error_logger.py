"""Detailed error logging module for CloudWatch Logs."""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import traceback


class ErrorLogger:
    """Logs detailed error information to CloudWatch Logs with structured JSON."""
    
    def __init__(self, logger_name: str = "IncidentResponse"):
        """
        Initialize the error logger.
        
        Args:
            logger_name: Name of the logger
        """
        self.logger = logging.getLogger(logger_name)
        
        # Configure structured JSON logging
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JsonFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
    def log_agent_failure(
        self,
        agent_name: str,
        error_message: str,
        incident_id: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ):
        """
        Log agent failure with detailed context.
        
        Args:
            agent_name: Name of the failed agent
            error_message: Error message
            incident_id: Incident ID for tracking
            context: Additional context information
            exception: Optional exception object
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'ERROR',
            'event_type': 'agent_failure',
            'agent_name': agent_name,
            'error_message': error_message,
            'incident_id': incident_id,
            'context': context or {}
        }
        
        if exception:
            log_entry['exception_type'] = type(exception).__name__
            log_entry['exception_details'] = str(exception)
            log_entry['stack_trace'] = traceback.format_exc()
            
        self.logger.error(json.dumps(log_entry))
        
    def log_orchestration_error(
        self,
        error_message: str,
        incident_id: str,
        failed_agents: list,
        successful_agents: list,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log orchestration-level errors.
        
        Args:
            error_message: Error message
            incident_id: Incident ID for tracking
            failed_agents: List of agents that failed
            successful_agents: List of agents that succeeded
            context: Additional context information
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'ERROR',
            'event_type': 'orchestration_error',
            'error_message': error_message,
            'incident_id': incident_id,
            'failed_agents': failed_agents,
            'successful_agents': successful_agents,
            'context': context or {}
        }
        
        self.logger.error(json.dumps(log_entry))
        
    def log_bedrock_error(
        self,
        agent_name: str,
        error_message: str,
        incident_id: str,
        model_id: Optional[str] = None,
        request_details: Optional[Dict[str, Any]] = None
    ):
        """
        Log Bedrock API errors.
        
        Args:
            agent_name: Name of the agent making the Bedrock call
            error_message: Error message
            incident_id: Incident ID for tracking
            model_id: Bedrock model ID
            request_details: Details of the request
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'ERROR',
            'event_type': 'bedrock_error',
            'agent_name': agent_name,
            'error_message': error_message,
            'incident_id': incident_id,
            'model_id': model_id,
            'request_details': request_details or {}
        }
        
        self.logger.error(json.dumps(log_entry))
        
    def log_aws_service_error(
        self,
        service_name: str,
        operation: str,
        error_message: str,
        incident_id: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log AWS service errors (S3, DynamoDB, SES, etc.).
        
        Args:
            service_name: AWS service name
            operation: Operation that failed
            error_message: Error message
            incident_id: Incident ID for tracking
            error_code: AWS error code
            context: Additional context information
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'ERROR',
            'event_type': 'aws_service_error',
            'service_name': service_name,
            'operation': operation,
            'error_message': error_message,
            'incident_id': incident_id,
            'error_code': error_code,
            'context': context or {}
        }
        
        self.logger.error(json.dumps(log_entry))
        
    def log_info(self, message: str, incident_id: str, context: Optional[Dict[str, Any]] = None):
        """
        Log informational message.
        
        Args:
            message: Log message
            incident_id: Incident ID for tracking
            context: Additional context information
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO',
            'event_type': 'info',
            'message': message,
            'incident_id': incident_id,
            'context': context or {}
        }
        
        self.logger.info(json.dumps(log_entry))
        
    def log_warning(self, message: str, incident_id: str, context: Optional[Dict[str, Any]] = None):
        """
        Log warning message.
        
        Args:
            message: Warning message
            incident_id: Incident ID for tracking
            context: Additional context information
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'WARNING',
            'event_type': 'warning',
            'message': message,
            'incident_id': incident_id,
            'context': context or {}
        }
        
        self.logger.warning(json.dumps(log_entry))
        
    def log_agent_retry(
        self,
        agent_name: str,
        attempt: int,
        max_attempts: int,
        incident_id: str,
        error_message: str
    ):
        """
        Log agent retry attempts.
        
        Args:
            agent_name: Name of the agent being retried
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            incident_id: Incident ID for tracking
            error_message: Error that triggered the retry
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'WARNING',
            'event_type': 'agent_retry',
            'agent_name': agent_name,
            'attempt': attempt,
            'max_attempts': max_attempts,
            'incident_id': incident_id,
            'error_message': error_message
        }
        
        self.logger.warning(json.dumps(log_entry))
        
    def log_partial_results(
        self,
        incident_id: str,
        successful_agents: list,
        failed_agents: list,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log when processing completes with partial results.
        
        Args:
            incident_id: Incident ID for tracking
            successful_agents: List of agents that succeeded
            failed_agents: List of agents that failed
            context: Additional context information
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'WARNING',
            'event_type': 'partial_results',
            'incident_id': incident_id,
            'successful_agents': successful_agents,
            'failed_agents': failed_agents,
            'context': context or {}
        }
        
        self.logger.warning(json.dumps(log_entry))


class JsonFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        # If the message is already JSON, return it as-is
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            # Otherwise, wrap it in a JSON structure
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'message': record.getMessage(),
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_entry['exception'] = self.formatException(record.exc_info)
                
            return json.dumps(log_entry)
