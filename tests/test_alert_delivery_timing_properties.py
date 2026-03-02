"""
Property-Based Tests for Alert Delivery Timing

This module tests Property 24: Alert Delivery Timing

Property 24: Alert Delivery Timing
For any ready Enhanced_Alert, it should be delivered via SES within 10 seconds.

Validates: Requirements 7.1
"""

import time
from datetime import datetime
from unittest import mock
from hypothesis import given, strategies as st, settings
import pytest

from src.alerts.ses_delivery import SESDeliveryService


# Strategy for generating enhanced alerts
@st.composite
def enhanced_alert_strategy(draw):
    """Generate valid enhanced alert dictionaries."""
    incident_id = draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    service_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    
    return {
        'incident_id': f"inc-{incident_id}",
        'timestamp': datetime.now().isoformat(),
        'original_alert': {
            'service_name': service_name,
            'error_message': draw(st.text(min_size=10, max_size=100))
        },
        'root_cause': {
            'category': draw(st.sampled_from(['configuration_error', 'resource_exhaustion', 'dependency_failure'])),
            'description': draw(st.text(min_size=20, max_size=200)),
            'evidence': draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        },
        'confidence_score': draw(st.integers(min_value=0, max_value=100)),
        'recommended_fixes': draw(st.lists(
            st.fixed_dictionaries({
                'step': st.integers(min_value=1, max_value=5),
                'action': st.text(min_size=10, max_size=100),
                'command': st.text(min_size=10, max_size=200),
                'estimated_time': st.text(min_size=5, max_size=20),
                'risk_level': st.sampled_from(['none', 'low', 'medium', 'high'])
            }),
            min_size=2,
            max_size=5
        )),
        'business_summary': {
            'impact': draw(st.text(min_size=20, max_size=200)),
            'estimated_resolution': draw(st.text(min_size=5, max_size=20))
        }
    }


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_24_alert_delivery_timing(enhanced_alert):
    """
    Feature: incident-response-system
    Property 24: Alert Delivery Timing
    
    For any ready Enhanced_Alert, it should be delivered via SES within 10 seconds.
    
    Validates: Requirements 7.1
    """
    # Mock SES client to avoid actual email sending
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        # Mock successful SES response
        mock_ses.send_email.return_value = {
            'MessageId': f"msg-{enhanced_alert['incident_id']}"
        }
        
        # Create delivery service
        service = SESDeliveryService(
            sender_email="test@example.com",
            region="us-east-1"
        )
        
        # Measure delivery time
        start_time = time.time()
        
        result = service.deliver_alert(
            enhanced_alert=enhanced_alert,
            recipients=["test@example.com"]
        )
        
        delivery_time = time.time() - start_time
        
        # Property: Delivery should complete within 10 seconds
        assert delivery_time < 10.0, (
            f"Alert delivery took {delivery_time:.2f}s, exceeding 10 second limit"
        )
        
        # Verify delivery was successful
        assert result['success'] is True
        assert 'message_id' in result
        assert result['incident_id'] == enhanced_alert['incident_id']
        
        # Verify delivery_time_seconds is tracked
        assert 'delivery_time_seconds' in result
        assert result['delivery_time_seconds'] < 10.0


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_24_delivery_timing_tracked(enhanced_alert):
    """
    Feature: incident-response-system
    Property 24: Alert Delivery Timing (Tracking)
    
    For any alert delivery, the system should track and return the delivery time.
    
    Validates: Requirements 7.1
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {
            'MessageId': f"msg-{enhanced_alert['incident_id']}"
        }
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=enhanced_alert,
            recipients=["test@example.com"]
        )
        
        # Property: Delivery time must be tracked
        assert 'delivery_time_seconds' in result
        assert isinstance(result['delivery_time_seconds'], (int, float))
        assert result['delivery_time_seconds'] >= 0
        
        # Property: Delivery time should be reasonable (< 10 seconds)
        assert result['delivery_time_seconds'] < 10.0


@given(
    enhanced_alert=enhanced_alert_strategy(),
    delay_seconds=st.floats(min_value=0.1, max_value=2.0)
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_24_delivery_timing_with_delays(enhanced_alert, delay_seconds):
    """
    Feature: incident-response-system
    Property 24: Alert Delivery Timing (With Simulated Delays)
    
    Even with network delays, delivery should complete within 10 seconds.
    
    Validates: Requirements 7.1
    """
    # Mock SES client with simulated delay
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        def delayed_send(*args, **kwargs):
            time.sleep(delay_seconds)
            return {'MessageId': f"msg-{enhanced_alert['incident_id']}"}
        
        mock_ses.send_email.side_effect = delayed_send
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        start_time = time.time()
        result = service.deliver_alert(
            enhanced_alert=enhanced_alert,
            recipients=["test@example.com"]
        )
        total_time = time.time() - start_time
        
        # Property: Even with delays, should complete within 10 seconds
        assert total_time < 10.0
        assert result['success'] is True
        assert result['delivery_time_seconds'] < 10.0
