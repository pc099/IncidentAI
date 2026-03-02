"""
Property tests for metrics emission.

Feature: incident-response-system
Property 34: Metrics Emission

For any agent execution, the system should emit CloudWatch metrics for 
execution time, success rate, and error count.

Validates: Requirements 9.1
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch, call
from src.observability.metrics_emitter import MetricsEmitter


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    execution_time_ms=st.floats(min_value=1.0, max_value=60000.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_34_agent_execution_emits_metrics(agent_name, execution_time_ms, incident_id):
    """
    Property 34: Metrics Emission
    
    For any agent execution, the system should emit CloudWatch metrics for 
    execution time, success rate, and error count.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit execution time metric
        emitter.emit_agent_execution_time(agent_name, execution_time_ms, incident_id)
        
        # Verify metric was added to buffer
        assert len(emitter.metric_buffer) == 1
        metric = emitter.metric_buffer[0]
        
        # Verify metric structure
        assert metric['MetricName'] == 'AgentExecutionTime'
        assert metric['Value'] == execution_time_ms
        assert metric['Unit'] == 'Milliseconds'
        assert 'Timestamp' in metric
        
        # Verify dimensions
        dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
        assert dimensions['Agent'] == agent_name
        assert dimensions['IncidentId'] == incident_id


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_34_agent_success_emits_metrics(agent_name, incident_id):
    """
    Property 34: Metrics Emission - Success Rate
    
    For any successful agent execution, the system should emit success metrics.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit success metric
        emitter.emit_agent_success(agent_name, incident_id)
        
        # Verify metric was added to buffer
        assert len(emitter.metric_buffer) == 1
        metric = emitter.metric_buffer[0]
        
        # Verify metric structure
        assert metric['MetricName'] == 'AgentSuccess'
        assert metric['Value'] == 1
        assert metric['Unit'] == 'Count'
        
        # Verify dimensions
        dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
        assert dimensions['Agent'] == agent_name
        assert dimensions['IncidentId'] == incident_id


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    error_type=st.sampled_from(['BEDROCK_TIMEOUT', 'S3_ERROR', 'DYNAMODB_ERROR', 'VALIDATION_ERROR']),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_34_agent_error_emits_metrics(agent_name, error_type, incident_id):
    """
    Property 34: Metrics Emission - Error Count
    
    For any agent error, the system should emit error count metrics.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        
        # Emit error metric
        emitter.emit_agent_error(agent_name, error_type, incident_id)
        
        # Verify metric was added to buffer
        assert len(emitter.metric_buffer) == 1
        metric = emitter.metric_buffer[0]
        
        # Verify metric structure
        assert metric['MetricName'] == 'AgentError'
        assert metric['Value'] == 1
        assert metric['Unit'] == 'Count'
        
        # Verify dimensions
        dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
        assert dimensions['Agent'] == agent_name
        assert dimensions['ErrorType'] == error_type
        assert dimensions['IncidentId'] == incident_id


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    execution_time_ms=st.floats(min_value=1.0, max_value=60000.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_34_metrics_batching(agent_name, execution_time_ms, incident_id):
    """
    Property 34: Metrics Emission - Batching
    
    For any agent execution, metrics should be batched to reduce API calls.
    When buffer reaches size limit, metrics should be flushed.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        emitter.buffer_size = 5  # Set small buffer for testing
        
        # Add metrics up to buffer size
        for i in range(5):
            emitter.emit_agent_execution_time(agent_name, execution_time_ms, f"{incident_id}-{i}")
        
        # Verify flush was called when buffer reached size
        assert mock_cloudwatch.put_metric_data.called
        
        # Verify buffer was cleared after flush
        assert len(emitter.metric_buffer) == 0


@given(
    agent_name=st.sampled_from(['log-analysis', 'root-cause', 'fix-recommendation', 'communication']),
    execution_time_ms=st.floats(min_value=1.0, max_value=60000.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_34_context_manager_flushes_metrics(agent_name, execution_time_ms, incident_id):
    """
    Property 34: Metrics Emission - Context Manager
    
    When using MetricsEmitter as a context manager, all buffered metrics 
    should be flushed on exit.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        with MetricsEmitter() as emitter:
            emitter.emit_agent_execution_time(agent_name, execution_time_ms, incident_id)
            # Metrics should be in buffer
            assert len(emitter.metric_buffer) > 0
        
        # After context exit, flush should have been called
        assert mock_cloudwatch.put_metric_data.called
