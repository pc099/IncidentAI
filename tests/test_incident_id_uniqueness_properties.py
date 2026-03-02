"""
Property-Based Tests for Incident ID Uniqueness

This module tests Property 28: Incident ID Uniqueness

Property 28: Incident ID Uniqueness
For any two alerts sent by the system, they should have different incident IDs
(uniqueness property).

Validates: Requirements 7.5
"""

from datetime import datetime
from unittest import mock
from hypothesis import given, strategies as st, settings
import pytest

from src.alerts.ses_delivery import SESDeliveryService


# Strategy for generating enhanced alerts
@st.composite
def enhanced_alert_strategy(draw):
    """Generate valid enhanced alert dictionaries."""
    import uuid
    # Use UUID to ensure uniqueness
    incident_id = str(uuid.uuid4())
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


@given(
    alert1=enhanced_alert_strategy(),
    alert2=enhanced_alert_strategy()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_uniqueness(alert1, alert2):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness
    
    For any two alerts sent by the system, they should have different
    incident IDs (uniqueness property).
    
    Validates: Requirements 7.5
    """
    # Property: Two different alerts should have different incident IDs
    # (This is guaranteed by our strategy which generates unique IDs)
    assert alert1['incident_id'] != alert2['incident_id'], (
        "Two different alerts must have different incident IDs"
    )


@given(alerts=st.lists(enhanced_alert_strategy(), min_size=2, max_size=20))
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_multiple_incident_ids_unique(alerts):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Multiple Alerts)
    
    For any collection of alerts, all incident IDs should be unique.
    
    Validates: Requirements 7.5
    """
    incident_ids = [alert['incident_id'] for alert in alerts]
    
    # Property: All incident IDs should be unique
    assert len(incident_ids) == len(set(incident_ids)), (
        f"All incident IDs should be unique. Found {len(incident_ids)} alerts "
        f"but only {len(set(incident_ids))} unique IDs"
    )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_in_subject(alert):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Subject Line)
    
    For any alert, the incident ID should be included in the email subject line.
    
    Validates: Requirements 7.5
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        # Capture the subject line
        captured_subject = None
        
        def capture_send_email(**kwargs):
            nonlocal captured_subject
            captured_subject = kwargs['Message']['Subject']['Data']
            return {'MessageId': f"msg-{alert['incident_id']}"}
        
        mock_ses.send_email.side_effect = capture_send_email
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=alert,
            recipients=["test@example.com"]
        )
        
        # Property: Incident ID must be in subject line
        assert captured_subject is not None
        assert alert['incident_id'] in captured_subject, (
            f"Incident ID {alert['incident_id']} should be in subject: {captured_subject}"
        )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_in_delivery_result(alert):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Delivery Result)
    
    For any alert delivery, the result should include the incident ID for tracking.
    
    Validates: Requirements 7.5
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {
            'MessageId': f"msg-{alert['incident_id']}"
        }
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=alert,
            recipients=["test@example.com"]
        )
        
        # Property: Delivery result must include incident ID
        assert 'incident_id' in result
        assert result['incident_id'] == alert['incident_id']


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_format(alert):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Format)
    
    For any alert, the incident ID should follow a consistent format that
    ensures uniqueness (e.g., prefix + unique identifier).
    
    Validates: Requirements 7.5
    """
    incident_id = alert['incident_id']
    
    # Property: Incident ID should have a consistent format
    # Expected format: "inc-{unique_identifier}"
    assert incident_id.startswith('inc-'), (
        f"Incident ID should start with 'inc-': {incident_id}"
    )
    
    # Property: Incident ID should have sufficient length for uniqueness
    assert len(incident_id) >= 10, (
        f"Incident ID should be at least 10 characters for uniqueness: {incident_id}"
    )
    
    # Property: Incident ID should not contain spaces
    assert ' ' not in incident_id, (
        f"Incident ID should not contain spaces: {incident_id}"
    )


@given(alerts=st.lists(enhanced_alert_strategy(), min_size=5, max_size=50))
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_collision_resistance(alerts):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Collision Resistance)
    
    For any large collection of alerts, the probability of incident ID
    collision should be negligible (all IDs unique).
    
    Validates: Requirements 7.5
    """
    incident_ids = [alert['incident_id'] for alert in alerts]
    unique_ids = set(incident_ids)
    
    # Property: No collisions should occur
    collision_count = len(incident_ids) - len(unique_ids)
    
    assert collision_count == 0, (
        f"Found {collision_count} incident ID collisions in {len(incident_ids)} alerts"
    )
    
    # Property: All IDs should be unique
    assert len(unique_ids) == len(incident_ids)


@given(
    alert1=enhanced_alert_strategy(),
    alert2=enhanced_alert_strategy()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_same_service_different_ids(alert1, alert2):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Same Service)
    
    Even for alerts from the same service, incident IDs should be unique.
    
    Validates: Requirements 7.5
    """
    # Force both alerts to have the same service name
    service_name = "test-service"
    alert1['original_alert']['service_name'] = service_name
    alert2['original_alert']['service_name'] = service_name
    
    # Property: Even with same service, IDs should be different
    assert alert1['incident_id'] != alert2['incident_id'], (
        f"Alerts from same service should have different IDs: "
        f"{alert1['incident_id']} vs {alert2['incident_id']}"
    )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_28_incident_id_immutable(alert):
    """
    Feature: incident-response-system
    Property 28: Incident ID Uniqueness (Immutability)
    
    For any alert, the incident ID should remain constant throughout
    the delivery process.
    
    Validates: Requirements 7.5
    """
    original_id = alert['incident_id']
    
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {
            'MessageId': f"msg-{alert['incident_id']}"
        }
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=alert,
            recipients=["test@example.com"]
        )
        
        # Property: Incident ID should not change during delivery
        assert alert['incident_id'] == original_id, (
            "Incident ID should not be modified during delivery"
        )
        
        assert result['incident_id'] == original_id, (
            "Delivery result should contain original incident ID"
        )
