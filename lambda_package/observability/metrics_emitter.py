"""CloudWatch metrics emission module for incident response system."""

import boto3
from datetime import datetime
from typing import List, Dict, Any, Optional
import time


class MetricsEmitter:
    """Emits CloudWatch metrics for agent execution and system performance."""
    
    def __init__(self, namespace: str = "IncidentResponse"):
        """
        Initialize the metrics emitter.
        
        Args:
            namespace: CloudWatch namespace for metrics
        """
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
        self.metric_buffer: List[Dict[str, Any]] = []
        self.buffer_size = 20  # CloudWatch allows max 20 metrics per PutMetricData call
        
    def emit_agent_execution_time(self, agent_name: str, execution_time_ms: float, incident_id: str):
        """
        Emit agent execution time metric.
        
        Args:
            agent_name: Name of the agent
            execution_time_ms: Execution time in milliseconds
            incident_id: Incident ID for tracking
        """
        self._add_metric({
            'MetricName': 'AgentExecutionTime',
            'Value': execution_time_ms,
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
    def emit_agent_success(self, agent_name: str, incident_id: str):
        """
        Emit agent success metric.
        
        Args:
            agent_name: Name of the agent
            incident_id: Incident ID for tracking
        """
        self._add_metric({
            'MetricName': 'AgentSuccess',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
    def emit_agent_error(self, agent_name: str, error_type: str, incident_id: str):
        """
        Emit agent error metric.
        
        Args:
            agent_name: Name of the agent
            error_type: Type of error encountered
            incident_id: Incident ID for tracking
        """
        self._add_metric({
            'MetricName': 'AgentError',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'ErrorType', 'Value': error_type},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
    def emit_bedrock_token_usage(self, agent_name: str, input_tokens: int, output_tokens: int, incident_id: str):
        """
        Emit Bedrock token usage metrics.
        
        Args:
            agent_name: Name of the agent making the Bedrock call
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            incident_id: Incident ID for tracking
        """
        timestamp = datetime.utcnow()
        
        self._add_metric({
            'MetricName': 'BedrockInputTokens',
            'Value': input_tokens,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
        self._add_metric({
            'MetricName': 'BedrockOutputTokens',
            'Value': output_tokens,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
        # Total tokens
        self._add_metric({
            'MetricName': 'BedrockTotalTokens',
            'Value': input_tokens + output_tokens,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'Agent', 'Value': agent_name},
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
    def emit_latency_warning(self, processing_time_seconds: float, incident_id: str):
        """
        Emit latency warning when processing exceeds 60 seconds.
        
        Args:
            processing_time_seconds: Total processing time in seconds
            incident_id: Incident ID for tracking
        """
        self._add_metric({
            'MetricName': 'LatencyWarning',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': 'IncidentId', 'Value': incident_id},
                {'Name': 'ProcessingTime', 'Value': str(int(processing_time_seconds))}
            ]
        })
        
    def emit_cost_warning(self, service_name: str, usage_percentage: float, incident_id: Optional[str] = None):
        """
        Emit cost warning when Free Tier usage reaches 80%.
        
        Args:
            service_name: AWS service name (e.g., 'Bedrock', 'Lambda', 'DynamoDB')
            usage_percentage: Percentage of Free Tier usage
            incident_id: Optional incident ID for tracking
        """
        dimensions = [
            {'Name': 'Service', 'Value': service_name},
            {'Name': 'UsagePercentage', 'Value': str(int(usage_percentage))}
        ]
        
        if incident_id:
            dimensions.append({'Name': 'IncidentId', 'Value': incident_id})
            
        self._add_metric({
            'MetricName': 'CostWarning',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow(),
            'Dimensions': dimensions
        })
        
    def emit_incident_processed(self, incident_id: str, total_time_seconds: float, confidence_score: int):
        """
        Emit metric for completed incident processing.
        
        Args:
            incident_id: Incident ID
            total_time_seconds: Total processing time in seconds
            confidence_score: Confidence score of the analysis
        """
        timestamp = datetime.utcnow()
        
        self._add_metric({
            'MetricName': 'IncidentProcessed',
            'Value': 1,
            'Unit': 'Count',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
        self._add_metric({
            'MetricName': 'ProcessingTime',
            'Value': total_time_seconds,
            'Unit': 'Seconds',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
        self._add_metric({
            'MetricName': 'ConfidenceScore',
            'Value': confidence_score,
            'Unit': 'None',
            'Timestamp': timestamp,
            'Dimensions': [
                {'Name': 'IncidentId', 'Value': incident_id}
            ]
        })
        
    def _add_metric(self, metric_data: Dict[str, Any]):
        """
        Add metric to buffer and flush if buffer is full.
        
        Args:
            metric_data: Metric data dictionary
        """
        self.metric_buffer.append(metric_data)
        
        # Flush if buffer reaches size limit
        if len(self.metric_buffer) >= self.buffer_size:
            self.flush()
            
    def flush(self):
        """Flush all buffered metrics to CloudWatch."""
        if not self.metric_buffer:
            return
            
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=self.metric_buffer
            )
            self.metric_buffer = []
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Error flushing metrics to CloudWatch: {e}")
            self.metric_buffer = []
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - flush remaining metrics."""
        self.flush()
