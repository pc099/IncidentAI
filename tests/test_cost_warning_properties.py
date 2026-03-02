"""
Property tests for cost warning threshold.

Feature: incident-response-system
Property 37: Cost Warning Threshold

For any AWS service usage that reaches 80% of Free Tier limits, the system 
should emit a cost warning metric.

Validates: Requirements 9.4
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch
from src.observability.warning_tracker import WarningTracker
from src.observability.metrics_emitter import MetricsEmitter


@given(
    input_tokens=st.integers(min_value=20001, max_value=25000),
    output_tokens=st.integers(min_value=1, max_value=5000),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_cost_warning_emitted_at_80_percent(input_tokens, output_tokens, incident_id):
    """
    Property 37: Cost Warning Threshold
    
    For any AWS service usage that reaches 80% of Free Tier limits, the system 
    should emit a cost warning metric.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Track Bedrock usage that exceeds 80% threshold
        tracker.track_bedrock_usage(input_tokens, output_tokens, incident_id)
        
        # Should emit cost warning (input tokens >= 80% of 25000 = 20000)
        cost_warnings = [m for m in emitter.metric_buffer if m['MetricName'] == 'CostWarning']
        assert len(cost_warnings) > 0
        
        # Verify warning structure
        warning = cost_warnings[0]
        assert warning['Value'] == 1
        assert warning['Unit'] == 'Count'
        
        # Verify dimensions
        dimensions = {d['Name']: d['Value'] for d in warning['Dimensions']}
        assert dimensions['Service'] == 'Bedrock'
        assert float(dimensions['UsagePercentage']) >= 80


@given(
    input_tokens=st.integers(min_value=1, max_value=19999),
    output_tokens=st.integers(min_value=1, max_value=19999),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_no_warning_below_80_percent(input_tokens, output_tokens, incident_id):
    """
    Property 37: Cost Warning Threshold - No Warning Below Threshold
    
    For any AWS service usage below 80% of Free Tier limits, the system 
    should NOT emit a cost warning metric.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Track Bedrock usage below 80% threshold
        tracker.track_bedrock_usage(input_tokens, output_tokens, incident_id)
        
        # Should NOT emit cost warning
        cost_warnings = [m for m in emitter.metric_buffer if m['MetricName'] == 'CostWarning']
        assert len(cost_warnings) == 0


@given(
    service_name=st.sampled_from(['Bedrock', 'Lambda', 'DynamoDB', 'S3']),
    usage_percentage=st.floats(min_value=80.0, max_value=100.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_warning_includes_service_name(service_name, usage_percentage, incident_id):
    """
    Property 37: Cost Warning Threshold - Service Name Included
    
    For any cost warning, the metric should include the AWS service name
    that triggered the warning.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit cost warning directly
        emitter.emit_cost_warning(service_name, usage_percentage, incident_id)
        
        # Verify warning includes service name
        assert len(emitter.metric_buffer) == 1
        warning = emitter.metric_buffer[0]
        
        dimensions = {d['Name']: d['Value'] for d in warning['Dimensions']}
        assert dimensions['Service'] == service_name
        assert dimensions['UsagePercentage'] == str(int(usage_percentage))


@given(
    usage_percentage=st.floats(min_value=80.0, max_value=100.0)
)
@pytest.mark.property_test
def test_property_37_warning_without_incident_id(usage_percentage):
    """
    Property 37: Cost Warning Threshold - Optional Incident ID
    
    Cost warnings can be emitted without an incident ID (for system-wide tracking).
    The warning should still be valid without the incident dimension.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit cost warning without incident_id
        emitter.emit_cost_warning('Bedrock', usage_percentage, incident_id=None)
        
        # Verify warning was emitted
        assert len(emitter.metric_buffer) == 1
        warning = emitter.metric_buffer[0]
        
        # Verify dimensions don't include IncidentId
        dimensions = {d['Name']: d['Value'] for d in warning['Dimensions']}
        assert 'IncidentId' not in dimensions
        assert dimensions['Service'] == 'Bedrock'


@given(
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_multiple_services_tracked_independently(incident_id):
    """
    Property 37: Cost Warning Threshold - Multiple Services
    
    For any incident that uses multiple AWS services, each service's usage
    should be tracked independently and emit separate warnings.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Track usage for multiple services at 80%+ threshold
        tracker.track_bedrock_usage(20001, 1000, incident_id)  # 80%+ of input tokens
        tracker.track_lambda_invocation(320001, incident_id)  # 80%+ of compute seconds
        tracker.track_dynamodb_usage(read_units=21, write_units=0, incident_id=incident_id)  # 80%+ of read units
        tracker.track_s3_usage(get_requests=16001, put_requests=0, incident_id=incident_id)  # 80%+ of GET requests
        
        # Should emit warnings for each service
        cost_warnings = [m for m in emitter.metric_buffer if m['MetricName'] == 'CostWarning']
        assert len(cost_warnings) >= 4
        
        # Verify each service has a warning
        services_warned = {d['Value'] for warning in cost_warnings 
                          for d in warning['Dimensions'] if d['Name'] == 'Service'}
        assert 'Bedrock' in services_warned
        assert 'Lambda' in services_warned
        assert 'DynamoDB' in services_warned
        assert 'S3' in services_warned


@given(
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_usage_summary_tracks_percentages(incident_id):
    """
    Property 37: Cost Warning Threshold - Usage Summary
    
    The warning tracker should maintain a usage summary that shows current
    usage percentages for all services.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Track some usage
        tracker.track_bedrock_usage(5000, 3000, incident_id)
        tracker.track_lambda_invocation(100000, incident_id)
        
        # Get usage summary
        summary = tracker.get_usage_summary()
        
        # Verify summary structure
        assert 'Bedrock' in summary
        assert 'Lambda' in summary
        assert 'DynamoDB' in summary
        assert 'S3' in summary
        
        # Verify Bedrock usage is tracked
        assert summary['Bedrock']['input_tokens']['current'] == 5000
        assert summary['Bedrock']['output_tokens']['current'] == 3000
        assert 'percentage' in summary['Bedrock']['input_tokens']
        
        # Verify Lambda usage is tracked
        assert summary['Lambda']['compute_seconds']['current'] == 100000
        assert 'percentage' in summary['Lambda']['compute_seconds']


@given(
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_37_threshold_boundary_exactly_80_percent(incident_id):
    """
    Property 37: Cost Warning Threshold - Boundary Test
    
    Test the exact boundary at 80%. Usage of exactly 80% should emit a warning.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Track exactly 80% of Bedrock input tokens (20000 out of 25000)
        tracker.track_bedrock_usage(20000, 1000, incident_id)
        
        # Should emit warning at exactly 80%
        cost_warnings = [m for m in emitter.metric_buffer if m['MetricName'] == 'CostWarning']
        assert len(cost_warnings) > 0
        
        # Verify warning is for Bedrock
        warning = cost_warnings[0]
        dimensions = {d['Name']: d['Value'] for d in warning['Dimensions']}
        assert dimensions['Service'] == 'Bedrock'
        assert float(dimensions['UsagePercentage']) == 80
