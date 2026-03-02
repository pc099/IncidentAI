"""
Property tests for latency warning threshold.

Feature: incident-response-system
Property 35: Latency Warning Threshold

For any incident processing that takes longer than 60 seconds, the system 
should emit a latency warning metric.

Validates: Requirements 9.2
"""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import Mock, patch
from src.observability.warning_tracker import WarningTracker
from src.observability.metrics_emitter import MetricsEmitter


@given(
    processing_time_seconds=st.floats(min_value=60.1, max_value=300.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_35_latency_warning_emitted_above_threshold(processing_time_seconds, incident_id):
    """
    Property 35: Latency Warning Threshold
    
    For any incident processing that takes longer than 60 seconds, the system 
    should emit a latency warning metric.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Check latency - should emit warning
        warning_emitted = tracker.check_latency(processing_time_seconds, incident_id)
        
        # Verify warning was emitted
        assert warning_emitted is True
        
        # Verify metric was added to buffer
        assert len(emitter.metric_buffer) == 1
        metric = emitter.metric_buffer[0]
        
        # Verify metric structure
        assert metric['MetricName'] == 'LatencyWarning'
        assert metric['Value'] == 1
        assert metric['Unit'] == 'Count'
        
        # Verify dimensions include incident_id
        dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
        assert dimensions['IncidentId'] == incident_id


@given(
    processing_time_seconds=st.floats(min_value=0.1, max_value=60.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_35_no_warning_below_threshold(processing_time_seconds, incident_id):
    """
    Property 35: Latency Warning Threshold - No Warning Below Threshold
    
    For any incident processing that takes 60 seconds or less, the system 
    should NOT emit a latency warning metric.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Check latency - should NOT emit warning
        warning_emitted = tracker.check_latency(processing_time_seconds, incident_id)
        
        # Verify no warning was emitted
        assert warning_emitted is False
        
        # Verify no metrics in buffer
        assert len(emitter.metric_buffer) == 0


@given(
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_35_threshold_boundary_exactly_60_seconds(incident_id):
    """
    Property 35: Latency Warning Threshold - Boundary Test
    
    Test the exact boundary at 60 seconds. Processing time of exactly 60 seconds
    should NOT emit a warning (only > 60 seconds should).
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Check latency at exactly 60 seconds
        warning_emitted = tracker.check_latency(60.0, incident_id)
        
        # Verify no warning at boundary
        assert warning_emitted is False
        assert len(emitter.metric_buffer) == 0
        
        # Check latency at 60.1 seconds (just above threshold)
        warning_emitted = tracker.check_latency(60.1, incident_id)
        
        # Verify warning is emitted just above threshold
        assert warning_emitted is True
        assert len(emitter.metric_buffer) == 1


@given(
    processing_time_seconds=st.floats(min_value=60.1, max_value=300.0),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_35_warning_includes_processing_time(processing_time_seconds, incident_id):
    """
    Property 35: Latency Warning Threshold - Processing Time Included
    
    For any latency warning, the metric should include the actual processing time
    in the dimensions for tracking purposes.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Check latency - should emit warning
        tracker.check_latency(processing_time_seconds, incident_id)
        
        # Verify metric includes processing time
        metric = emitter.metric_buffer[0]
        dimensions = {d['Name']: d['Value'] for d in metric['Dimensions']}
        
        # Processing time should be included as a dimension
        assert 'ProcessingTime' in dimensions
        # Should be the integer value of processing time
        assert dimensions['ProcessingTime'] == str(int(processing_time_seconds))


@given(
    processing_times=st.lists(
        st.floats(min_value=60.1, max_value=300.0),
        min_size=2,
        max_size=5
    ),
    incident_id=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pd')))
)
@pytest.mark.property_test
def test_property_35_multiple_warnings_tracked_independently(processing_times, incident_id):
    """
    Property 35: Latency Warning Threshold - Multiple Warnings
    
    For any sequence of incidents with processing times exceeding 60 seconds,
    each should emit its own latency warning metric.
    """
    with patch('boto3.client') as mock_boto_client:
        mock_cloudwatch = Mock()
        mock_boto_client.return_value = mock_cloudwatch
        
        emitter = MetricsEmitter()
        tracker = WarningTracker(emitter)
        
        # Check multiple latencies
        warnings_emitted = 0
        for i, processing_time in enumerate(processing_times):
            if tracker.check_latency(processing_time, f"{incident_id}-{i}"):
                warnings_emitted += 1
        
        # Verify all warnings were emitted
        assert warnings_emitted == len(processing_times)
        assert len(emitter.metric_buffer) == len(processing_times)
        
        # Verify each metric has correct structure
        for metric in emitter.metric_buffer:
            assert metric['MetricName'] == 'LatencyWarning'
            assert metric['Value'] == 1
