"""Token usage limiter for Bedrock API calls to stay within Free Tier."""

from typing import Optional
from .metrics_emitter import MetricsEmitter


class TokenUsageLimiter:
    """Enforces token usage limits to stay within AWS Free Tier allowances."""
    
    # AWS Bedrock Free Tier limits (monthly)
    # Note: These are example values - actual Free Tier limits may vary
    FREE_TIER_LIMITS = {
        'input_tokens': 25000,
        'output_tokens': 25000,
        'total_tokens': 50000
    }
    
    # Warning threshold (80% of Free Tier)
    WARNING_THRESHOLD = 0.80
    
    # Hard limit threshold (95% of Free Tier)
    HARD_LIMIT_THRESHOLD = 0.95
    
    def __init__(self, metrics_emitter: Optional[MetricsEmitter] = None):
        """
        Initialize the token usage limiter.
        
        Args:
            metrics_emitter: Optional MetricsEmitter for emitting warnings
        """
        self.metrics_emitter = metrics_emitter
        self.usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }
        
    def track_usage(self, input_tokens: int, output_tokens: int, incident_id: Optional[str] = None):
        """
        Track token usage and check against limits.
        
        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            incident_id: Optional incident ID for tracking
            
        Raises:
            TokenLimitExceeded: If usage exceeds hard limit
        """
        self.usage['input_tokens'] += input_tokens
        self.usage['output_tokens'] += output_tokens
        self.usage['total_tokens'] += (input_tokens + output_tokens)
        
        # Check limits
        self._check_limits(incident_id)
        
    def _check_limits(self, incident_id: Optional[str] = None):
        """
        Check if usage is approaching or exceeding limits.
        
        Args:
            incident_id: Optional incident ID for tracking
            
        Raises:
            TokenLimitExceeded: If usage exceeds hard limit
        """
        for token_type, usage in self.usage.items():
            limit = self.FREE_TIER_LIMITS[token_type]
            usage_percentage = (usage / limit) * 100
            
            # Check hard limit
            if usage_percentage >= (self.HARD_LIMIT_THRESHOLD * 100):
                raise TokenLimitExceeded(
                    f"{token_type} usage ({usage}) has reached {usage_percentage:.1f}% "
                    f"of Free Tier limit ({limit}). Further API calls are blocked."
                )
            
            # Check warning threshold
            if usage_percentage >= (self.WARNING_THRESHOLD * 100):
                if self.metrics_emitter:
                    self.metrics_emitter.emit_cost_warning(
                        'Bedrock',
                        usage_percentage,
                        incident_id
                    )
                    
    def can_make_request(self, estimated_input_tokens: int, estimated_output_tokens: int) -> bool:
        """
        Check if a request can be made without exceeding limits.
        
        Args:
            estimated_input_tokens: Estimated input tokens for the request
            estimated_output_tokens: Estimated output tokens for the request
            
        Returns:
            bool: True if request can be made, False otherwise
        """
        estimated_total = estimated_input_tokens + estimated_output_tokens
        
        # Check if estimated usage would exceed hard limit
        for token_type in ['input_tokens', 'output_tokens', 'total_tokens']:
            if token_type == 'input_tokens':
                estimated_usage = self.usage[token_type] + estimated_input_tokens
            elif token_type == 'output_tokens':
                estimated_usage = self.usage[token_type] + estimated_output_tokens
            else:
                estimated_usage = self.usage[token_type] + estimated_total
                
            limit = self.FREE_TIER_LIMITS[token_type]
            usage_percentage = (estimated_usage / limit) * 100
            
            if usage_percentage >= (self.HARD_LIMIT_THRESHOLD * 100):
                return False
                
        return True
        
    def get_usage_summary(self) -> dict:
        """
        Get current usage summary with percentages.
        
        Returns:
            dict: Usage summary
        """
        summary = {}
        
        for token_type, usage in self.usage.items():
            limit = self.FREE_TIER_LIMITS[token_type]
            percentage = (usage / limit) * 100
            remaining = limit - usage
            
            summary[token_type] = {
                'current': usage,
                'limit': limit,
                'percentage': round(percentage, 2),
                'remaining': remaining,
                'status': self._get_status(percentage)
            }
            
        return summary
        
    def _get_status(self, percentage: float) -> str:
        """
        Get status based on usage percentage.
        
        Args:
            percentage: Usage percentage
            
        Returns:
            str: Status (ok, warning, critical)
        """
        if percentage >= (self.HARD_LIMIT_THRESHOLD * 100):
            return 'critical'
        elif percentage >= (self.WARNING_THRESHOLD * 100):
            return 'warning'
        else:
            return 'ok'
            
    def reset_usage(self):
        """Reset usage tracking (typically called at start of new billing period)."""
        self.usage = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0
        }
        
    def get_remaining_capacity(self) -> dict:
        """
        Get remaining capacity before hitting limits.
        
        Returns:
            dict: Remaining capacity for each token type
        """
        return {
            token_type: self.FREE_TIER_LIMITS[token_type] - self.usage[token_type]
            for token_type in self.usage.keys()
        }
        
    def estimate_requests_remaining(self, avg_input_tokens: int, avg_output_tokens: int) -> int:
        """
        Estimate how many more requests can be made with average token usage.
        
        Args:
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request
            
        Returns:
            int: Estimated number of requests remaining
        """
        remaining = self.get_remaining_capacity()
        
        # Calculate based on most restrictive limit
        input_requests = remaining['input_tokens'] // avg_input_tokens if avg_input_tokens > 0 else float('inf')
        output_requests = remaining['output_tokens'] // avg_output_tokens if avg_output_tokens > 0 else float('inf')
        total_requests = remaining['total_tokens'] // (avg_input_tokens + avg_output_tokens) if (avg_input_tokens + avg_output_tokens) > 0 else float('inf')
        
        return int(min(input_requests, output_requests, total_requests))


class TokenLimitExceeded(Exception):
    """Exception raised when token usage exceeds limits."""
    pass
