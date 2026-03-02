"""
Property tests for token usage limits.

Feature: incident-response-system
Property 46: Token Usage Limits

For any incident processing, the total Bedrock token usage should stay within 
AWS Free Tier allowances (tracked cumulatively).

Validates: Requirements 13.1
"""

import pytest
from hypothesis import given, strategies as st, assume
from unittest.mock import Mock, patch
from src.observability.token_usage_limiter import TokenUsageLimiter, TokenLimitExceeded
from src.observability.metrics_emitter import MetricsEmitter


@given(
    input_tokens=st.integers(min_value=1, max_value=1000),
    output_tokens=st.integers(min_value=1, max_value=1000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_46_token_usage_tracked_cumulatively(input_tokens, output_tokens, incident_id):
    """
    Property 46: Token Usage Limits - Cumulative Tracking
    
    For any incident processing, token usage should be tracked cumulatively
    and stay within Free Tier allowances.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track usage
        limiter.track_usage(input_tokens, output_tokens, incident_id)
        
        # Verify cumulative tracking
        assert limiter.usage['input_tokens'] == input_tokens
        assert limiter.usage['output_tokens'] == output_tokens
        assert limiter.usage['total_tokens'] == input_tokens + output_tokens
        
        # Track more usage
        limiter.track_usage(input_tokens, output_tokens, incident_id)
        
        # Verify cumulative addition
        assert limiter.usage['input_tokens'] == input_tokens * 2
        assert limiter.usage['output_tokens'] == output_tokens * 2
        assert limiter.usage['total_tokens'] == (input_tokens + output_tokens) * 2


@given(
    input_tokens=st.integers(min_value=20001, max_value=23500),
    output_tokens=st.integers(min_value=1, max_value=1000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_46_warning_emitted_at_80_percent(input_tokens, output_tokens, incident_id):
    """
    Property 46: Token Usage Limits - Warning at 80%
    
    When token usage reaches 80% of Free Tier limit, a warning should be emitted.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track usage that exceeds 80% threshold but stays below 95%
        limiter.track_usage(input_tokens, output_tokens, incident_id)
        
        # Verify warning was emitted
        cost_warnings = [m for m in emitter.metric_buffer if m['MetricName'] == 'CostWarning']
        assert len(cost_warnings) > 0


@given(
    input_tokens=st.integers(min_value=23751, max_value=25000),
    output_tokens=st.integers(min_value=1, max_value=1000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_46_hard_limit_blocks_requests(input_tokens, output_tokens, incident_id):
    """
    Property 46: Token Usage Limits - Hard Limit at 95%
    
    When token usage reaches 95% of Free Tier limit, further requests should be blocked.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track usage that exceeds 95% threshold
        with pytest.raises(TokenLimitExceeded):
            limiter.track_usage(input_tokens, output_tokens, incident_id)


@given(
    input_tokens=st.integers(min_value=1, max_value=1000),
    output_tokens=st.integers(min_value=1, max_value=1000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_46_usage_summary_accurate(input_tokens, output_tokens, incident_id):
    """
    Property 46: Token Usage Limits - Usage Summary Accuracy
    
    The usage summary should accurately reflect current usage and remaining capacity.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track usage
        limiter.track_usage(input_tokens, output_tokens, incident_id)
        
        # Get usage summary
        summary = limiter.get_usage_summary()
        
        # Verify accuracy
        assert summary['input_tokens']['current'] == input_tokens
        assert summary['output_tokens']['current'] == output_tokens
        assert summary['total_tokens']['current'] == input_tokens + output_tokens
        
        # Verify remaining capacity
        assert summary['input_tokens']['remaining'] == limiter.FREE_TIER_LIMITS['input_tokens'] - input_tokens
        assert summary['output_tokens']['remaining'] == limiter.FREE_TIER_LIMITS['output_tokens'] - output_tokens


@given(
    input_tokens=st.integers(min_value=1, max_value=1000),
    output_tokens=st.integers(min_value=1, max_value=1000)
)
@pytest.mark.property_test
def test_property_46_can_make_request_check(input_tokens, output_tokens):
    """
    Property 46: Token Usage Limits - Request Feasibility Check
    
    The system should accurately determine if a request can be made without exceeding limits.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Check if request can be made (should be true for small requests)
        can_make = limiter.can_make_request(input_tokens, output_tokens)
        assert can_make is True
        
        # Fill up to near limit
        limiter.track_usage(23000, 1000, "test-incident")
        
        # Check if large request can be made (should be false)
        can_make = limiter.can_make_request(5000, 5000)
        assert can_make is False


@given(
    requests=st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=500),
            st.integers(min_value=1, max_value=500)
        ),
        min_size=2,
        max_size=10
    )
)
@pytest.mark.property_test
def test_property_46_cumulative_tracking_multiple_requests(requests):
    """
    Property 46: Token Usage Limits - Multiple Request Tracking
    
    For any sequence of requests, token usage should be tracked cumulatively
    across all requests.
    """
    # Ensure total usage doesn't exceed limits
    total_input = sum(r[0] for r in requests)
    total_output = sum(r[1] for r in requests)
    assume(total_input < 20000)  # Stay below warning threshold
    assume(total_output < 20000)
    
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track multiple requests
        for i, (input_tokens, output_tokens) in enumerate(requests):
            limiter.track_usage(input_tokens, output_tokens, f"incident-{i}")
        
        # Verify cumulative totals
        assert limiter.usage['input_tokens'] == total_input
        assert limiter.usage['output_tokens'] == total_output
        assert limiter.usage['total_tokens'] == total_input + total_output


@given(
    input_tokens=st.integers(min_value=1, max_value=1000),
    output_tokens=st.integers(min_value=1, max_value=1000)
)
@pytest.mark.property_test
def test_property_46_reset_usage_clears_tracking(input_tokens, output_tokens):
    """
    Property 46: Token Usage Limits - Usage Reset
    
    Resetting usage should clear all tracked usage (for new billing period).
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track usage
        limiter.track_usage(input_tokens, output_tokens, "test-incident")
        
        # Verify usage is tracked
        assert limiter.usage['input_tokens'] > 0
        assert limiter.usage['output_tokens'] > 0
        
        # Reset usage
        limiter.reset_usage()
        
        # Verify usage is cleared
        assert limiter.usage['input_tokens'] == 0
        assert limiter.usage['output_tokens'] == 0
        assert limiter.usage['total_tokens'] == 0


@given(
    avg_input=st.integers(min_value=10, max_value=500),
    avg_output=st.integers(min_value=10, max_value=500)
)
@pytest.mark.property_test
def test_property_46_estimate_requests_remaining(avg_input, avg_output):
    """
    Property 46: Token Usage Limits - Remaining Request Estimation
    
    The system should accurately estimate how many more requests can be made
    with average token usage.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Get initial estimate
        initial_estimate = limiter.estimate_requests_remaining(avg_input, avg_output)
        
        # Should be positive
        assert initial_estimate > 0
        
        # Track some usage
        limiter.track_usage(5000, 5000, "test-incident")
        
        # Get new estimate
        new_estimate = limiter.estimate_requests_remaining(avg_input, avg_output)
        
        # Should be less than initial estimate
        assert new_estimate < initial_estimate


@given(
    input_tokens=st.integers(min_value=1, max_value=1000),
    output_tokens=st.integers(min_value=1, max_value=1000)
)
@pytest.mark.property_test
def test_property_46_status_reflects_usage_level(input_tokens, output_tokens):
    """
    Property 46: Token Usage Limits - Status Indication
    
    The status should accurately reflect the usage level (ok, warning, critical).
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        limiter = TokenUsageLimiter(emitter)
        
        # Track small usage
        limiter.track_usage(input_tokens, output_tokens, "test-incident")
        
        # Get summary
        summary = limiter.get_usage_summary()
        
        # Status should be 'ok' for small usage
        assert summary['input_tokens']['status'] == 'ok'
        assert summary['output_tokens']['status'] == 'ok'
        assert summary['total_tokens']['status'] == 'ok'
