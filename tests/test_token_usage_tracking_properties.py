"""
Property tests for token usage tracking.

Feature: incident-response-system
Property 36: Token Usage Tracking

For any Bedrock API call, the system should track and emit token usage 
metrics to CloudWatch.

Validates: Requirements 9.3
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch
from src.observability.metrics_emitter import MetricsEmitter


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    input_tokens=st.integers(min_value=1, max_value=10000),
    output_tokens=st.integers(min_value=1, max_value=10000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_bedrock_token_usage_tracked(agent_name, input_tokens, output_tokens, incident_id):
    """
    Property 36: Token Usage Tracking
    
    For any Bedrock API call, the system should track and emit token usage 
    metrics to CloudWatch.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage metrics
        emitter.emit_bedrock_token_usage(agent_name, input_tokens, output_tokens, incident_id)
        
        # Should emit 3 metrics: input tokens, output tokens, total tokens
        assert len(emitter.metric_buffer) == 3
        
        # Verify input tokens metric
        input_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockInputTokens')
        assert input_metric['Value'] == input_tokens
        assert input_metric['Unit'] == 'Count'
        
        # Verify output tokens metric
        output_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockOutputTokens')
        assert output_metric['Value'] == output_tokens
        assert output_metric['Unit'] == 'Count'
        
        # Verify total tokens metric
        total_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockTotalTokens')
        assert total_metric['Value'] == input_tokens + output_tokens
        assert total_metric['Unit'] == 'Count'


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    input_tokens=st.integers(min_value=1, max_value=10000),
    output_tokens=st.integers(min_value=1, max_value=10000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_token_metrics_include_agent_dimension(agent_name, input_tokens, output_tokens, incident_id):
    """
    Property 36: Token Usage Tracking - Agent Dimension
    
    For any Bedrock API call, token usage metrics should include the agent name
    as a dimension for tracking which agent is using tokens.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage metrics
        emitter.emit_bedrock_token_usage(agent_name, input_tokens, output_tokens, incident_id)
        
        # Verify all metrics include agent dimension
        for metric in emitter.metric_buffer:
            dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
            assert dimensions['Agent'] == agent_name
            assert dimensions['IncidentId'] == incident_id


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    input_tokens=st.integers(min_value=1, max_value=10000),
    output_tokens=st.integers(min_value=1, max_value=10000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_total_tokens_equals_sum(agent_name, input_tokens, output_tokens, incident_id):
    """
    Property 36: Token Usage Tracking - Total Calculation
    
    For any Bedrock API call, the total tokens metric should always equal
    the sum of input tokens and output tokens.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage metrics
        emitter.emit_bedrock_token_usage(agent_name, input_tokens, output_tokens, incident_id)
        
        # Get metrics
        input_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockInputTokens')
        output_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockOutputTokens')
        total_metric = next(m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockTotalTokens')
        
        # Verify total equals sum
        assert total_metric['Value'] == input_metric['Value'] + output_metric['Value']


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    token_calls=st.lists(
        st.tuples(
            st.integers(min_value=1, max_value=1000),
            st.integers(min_value=1, max_value=1000)
        ),
        min_size=2,
        max_size=5
    ),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_multiple_api_calls_tracked_separately(agent_name, token_calls, incident_id):
    """
    Property 36: Token Usage Tracking - Multiple API Calls
    
    For any sequence of Bedrock API calls, each call's token usage should be
    tracked separately with its own metrics.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage for multiple calls
        for i, (input_tokens, output_tokens) in enumerate(token_calls):
            emitter.emit_bedrock_token_usage(agent_name, input_tokens, output_tokens, f"{incident_id}-{i}")
        
        # Should have 3 metrics per call
        expected_metric_count = len(token_calls) * 3
        assert len(emitter.metric_buffer) == expected_metric_count
        
        # Verify each set of metrics has correct structure
        input_metrics = [m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockInputTokens']
        output_metrics = [m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockOutputTokens']
        total_metrics = [m for m in emitter.metric_buffer if m['MetricName'] == 'BedrockTotalTokens']
        
        assert len(input_metrics) == len(token_calls)
        assert len(output_metrics) == len(token_calls)
        assert len(total_metrics) == len(token_calls)


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    input_tokens=st.integers(min_value=1, max_value=10000),
    output_tokens=st.integers(min_value=1, max_value=10000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_token_metrics_have_same_timestamp(agent_name, input_tokens, output_tokens, incident_id):
    """
    Property 36: Token Usage Tracking - Timestamp Consistency
    
    For any Bedrock API call, all three token metrics (input, output, total)
    should have the same timestamp since they represent the same API call.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage metrics
        emitter.emit_bedrock_token_usage(agent_name, input_tokens, output_tokens, incident_id)
        
        # Get timestamps from all metrics
        timestamps = [m['Timestamp'] for m in emitter.metric_buffer]
        
        # All timestamps should be the same (or very close, within 1 second)
        # Since they're created in the same function call
        first_timestamp = timestamps[0]
        for timestamp in timestamps[1:]:
            # Timestamps should be identical or within 1 second
            time_diff = abs((timestamp - first_timestamp).total_seconds())
            assert time_diff < 1.0


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_36_zero_tokens_handled_correctly(agent_name, incident_id):
    """
    Property 36: Token Usage Tracking - Zero Tokens
    
    For any Bedrock API call with zero tokens (edge case), the system should
    still track and emit metrics correctly.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit token usage with zero tokens
        emitter.emit_bedrock_token_usage(agent_name, 0, 0, incident_id)
        
        # Should still emit 3 metrics
        assert len(emitter.metric_buffer) == 3
        
        # Verify all metrics have value 0
        for metric in emitter.metric_buffer:
            assert metric['Value'] == 0
