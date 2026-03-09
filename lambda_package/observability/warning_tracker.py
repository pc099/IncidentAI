"""Warning tracker for latency and cost thresholds."""

from typing import Optional
from .metrics_emitter import MetricsEmitter


class WarningTracker:
    """Tracks system metrics and emits warnings when thresholds are exceeded."""
    
    # Thresholds
    LATENCY_THRESHOLD_SECONDS = 60
    COST_WARNING_PERCENTAGE = 80
    
    # Free Tier limits (monthly)
    FREE_TIER_LIMITS = {
        'Bedrock': {
            'input_tokens': 25000,  # Example limit
            'output_tokens': 25000
        },
        'Lambda': {
            'invocations': 1000000,
            'compute_seconds': 400000
        },
        'DynamoDB': {
            'read_units': 25,
            'write_units': 25
        },
        'S3': {
            'get_requests': 20000,
            'put_requests': 2000
        }
    }
    
    def __init__(self, metrics_emitter: MetricsEmitter):
        """
        Initialize the warning tracker.
        
        Args:
            metrics_emitter: MetricsEmitter instance for emitting warnings
        """
        self.metrics_emitter = metrics_emitter
        self.usage_tracking = {
            'Bedrock': {'input_tokens': 0, 'output_tokens': 0},
            'Lambda': {'invocations': 0, 'compute_seconds': 0},
            'DynamoDB': {'read_units': 0, 'write_units': 0},
            'S3': {'get_requests': 0, 'put_requests': 0}
        }
        
    def check_latency(self, processing_time_seconds: float, incident_id: str) -> bool:
        """
        Check if processing time exceeds latency threshold and emit warning if needed.
        
        Args:
            processing_time_seconds: Total processing time in seconds
            incident_id: Incident ID for tracking
            
        Returns:
            True if warning was emitted, False otherwise
        """
        if processing_time_seconds > self.LATENCY_THRESHOLD_SECONDS:
            self.metrics_emitter.emit_latency_warning(processing_time_seconds, incident_id)
            return True
        return False
        
    def track_bedrock_usage(self, input_tokens: int, output_tokens: int, incident_id: Optional[str] = None):
        """
        Track Bedrock token usage and emit cost warning if threshold reached.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            incident_id: Optional incident ID for tracking
        """
        self.usage_tracking['Bedrock']['input_tokens'] += input_tokens
        self.usage_tracking['Bedrock']['output_tokens'] += output_tokens
        
        # Check input tokens usage
        input_usage_pct = (self.usage_tracking['Bedrock']['input_tokens'] / 
                          self.FREE_TIER_LIMITS['Bedrock']['input_tokens']) * 100
        
        if input_usage_pct >= self.COST_WARNING_PERCENTAGE:
            self.metrics_emitter.emit_cost_warning('Bedrock', input_usage_pct, incident_id)
            
        # Check output tokens usage
        output_usage_pct = (self.usage_tracking['Bedrock']['output_tokens'] / 
                           self.FREE_TIER_LIMITS['Bedrock']['output_tokens']) * 100
        
        if output_usage_pct >= self.COST_WARNING_PERCENTAGE:
            self.metrics_emitter.emit_cost_warning('Bedrock', output_usage_pct, incident_id)
            
    def track_lambda_invocation(self, compute_seconds: float, incident_id: Optional[str] = None):
        """
        Track Lambda invocation and compute time.
        
        Args:
            compute_seconds: Compute time in seconds
            incident_id: Optional incident ID for tracking
        """
        self.usage_tracking['Lambda']['invocations'] += 1
        self.usage_tracking['Lambda']['compute_seconds'] += compute_seconds
        
        # Check invocations
        invocation_usage_pct = (self.usage_tracking['Lambda']['invocations'] / 
                               self.FREE_TIER_LIMITS['Lambda']['invocations']) * 100
        
        if invocation_usage_pct >= self.COST_WARNING_PERCENTAGE:
            self.metrics_emitter.emit_cost_warning('Lambda', invocation_usage_pct, incident_id)
            
        # Check compute seconds
        compute_usage_pct = (self.usage_tracking['Lambda']['compute_seconds'] / 
                            self.FREE_TIER_LIMITS['Lambda']['compute_seconds']) * 100
        
        if compute_usage_pct >= self.COST_WARNING_PERCENTAGE:
            self.metrics_emitter.emit_cost_warning('Lambda', compute_usage_pct, incident_id)
            
    def track_dynamodb_usage(self, read_units: int = 0, write_units: int = 0, incident_id: Optional[str] = None):
        """
        Track DynamoDB read/write capacity usage.
        
        Args:
            read_units: Number of read capacity units used
            write_units: Number of write capacity units used
            incident_id: Optional incident ID for tracking
        """
        self.usage_tracking['DynamoDB']['read_units'] += read_units
        self.usage_tracking['DynamoDB']['write_units'] += write_units
        
        # Check read units
        if read_units > 0:
            read_usage_pct = (self.usage_tracking['DynamoDB']['read_units'] / 
                             self.FREE_TIER_LIMITS['DynamoDB']['read_units']) * 100
            
            if read_usage_pct >= self.COST_WARNING_PERCENTAGE:
                self.metrics_emitter.emit_cost_warning('DynamoDB', read_usage_pct, incident_id)
                
        # Check write units
        if write_units > 0:
            write_usage_pct = (self.usage_tracking['DynamoDB']['write_units'] / 
                              self.FREE_TIER_LIMITS['DynamoDB']['write_units']) * 100
            
            if write_usage_pct >= self.COST_WARNING_PERCENTAGE:
                self.metrics_emitter.emit_cost_warning('DynamoDB', write_usage_pct, incident_id)
                
    def track_s3_usage(self, get_requests: int = 0, put_requests: int = 0, incident_id: Optional[str] = None):
        """
        Track S3 request usage.
        
        Args:
            get_requests: Number of GET requests
            put_requests: Number of PUT requests
            incident_id: Optional incident ID for tracking
        """
        self.usage_tracking['S3']['get_requests'] += get_requests
        self.usage_tracking['S3']['put_requests'] += put_requests
        
        # Check GET requests
        if get_requests > 0:
            get_usage_pct = (self.usage_tracking['S3']['get_requests'] / 
                            self.FREE_TIER_LIMITS['S3']['get_requests']) * 100
            
            if get_usage_pct >= self.COST_WARNING_PERCENTAGE:
                self.metrics_emitter.emit_cost_warning('S3', get_usage_pct, incident_id)
                
        # Check PUT requests
        if put_requests > 0:
            put_usage_pct = (self.usage_tracking['S3']['put_requests'] / 
                            self.FREE_TIER_LIMITS['S3']['put_requests']) * 100
            
            if put_usage_pct >= self.COST_WARNING_PERCENTAGE:
                self.metrics_emitter.emit_cost_warning('S3', put_usage_pct, incident_id)
                
    def get_usage_summary(self) -> dict:
        """
        Get current usage summary with percentages.
        
        Returns:
            Dictionary with usage statistics
        """
        summary = {}
        
        for service, usage in self.usage_tracking.items():
            summary[service] = {}
            for metric, value in usage.items():
                limit = self.FREE_TIER_LIMITS[service][metric]
                percentage = (value / limit) * 100
                summary[service][metric] = {
                    'current': value,
                    'limit': limit,
                    'percentage': round(percentage, 2)
                }
                
        return summary
        
    def reset_usage(self):
        """Reset usage tracking (typically called at start of new billing period)."""
        self.usage_tracking = {
            'Bedrock': {'input_tokens': 0, 'output_tokens': 0},
            'Lambda': {'invocations': 0, 'compute_seconds': 0},
            'DynamoDB': {'read_units': 0, 'write_units': 0},
            'S3': {'get_requests': 0, 'put_requests': 0}
        }
