"""
Unit Tests for Email Delivery

This module tests specific email delivery scenarios including:
- Successful delivery
- Delivery retry on failure
- HTML rendering
- Plain text fallback

Validates: Requirements 7.1, 7.6
"""

import time
from datetime import datetime
from unittest import mock
import pytest
from botocore.exceptions import ClientError

from src.alerts.ses_delivery import SESDeliveryService, send_incident_alert
from src.alerts.email_formatter import format_html_email, format_text_email


# Sample enhanced alert for testing
SAMPLE_ALERT = {
    'incident_id': 'inc-test-001',
    'timestamp': '2025-01-15T10:30:00Z',
    'original_alert': {
        'service_name': 'payment-processor',
        'error_message': 'DynamoDB throttling detected',
        'timestamp': '2025-01-15T10:30:00Z',
        'log_location': 's3://logs/payment-processor/2025-01-15.log'
    },
    'root_cause': {
        'category': 'resource_exhaustion',
        'description': 'DynamoDB read capacity exceeded',
        'evidence': [
            'ProvisionedThroughputExceededException in logs',
            'Read capacity at 100% for 5 minutes',
            'Request rate increased 300% in last hour'
        ]
    },
    'confidence_score': 85,
    'recommended_fixes': [
        {
            'step': 1,
            'action': 'Enable DynamoDB auto-scaling',
            'command': 'aws dynamodb update-table --table-name payments --auto-scaling-enabled',
            'estimated_time': '5 minutes',
            'risk_level': 'low'
        },
        {
            'step': 2,
            'action': 'Implement exponential backoff in application',
            'command': 'Update application code with AWS SDK retry logic',
            'estimated_time': '30 minutes',
            'risk_level': 'medium'
        }
    ],
    'business_summary': {
        'impact': 'Payment transactions are failing due to database throttling',
        'estimated_resolution': '35 minutes'
    }
}


def test_successful_email_delivery():
    """
    Test successful email delivery via SES.
    
    Validates: Requirements 7.1
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        # Mock successful SES response
        mock_ses.send_email.return_value = {
            'MessageId': 'msg-12345',
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"]
        )
        
        # Verify successful delivery
        assert result['success'] is True
        assert result['message_id'] == 'msg-12345'
        assert result['incident_id'] == 'inc-test-001'
        assert result['attempt'] == 1
        assert result['delivery_time_seconds'] < 5.0
        
        # Verify SES was called correctly
        mock_ses.send_email.assert_called_once()
        call_args = mock_ses.send_email.call_args[1]
        
        assert call_args['Source'] == "test@example.com"
        assert call_args['Destination']['ToAddresses'] == ["oncall@example.com"]
        assert 'inc-test-001' in call_args['Message']['Subject']['Data']


def test_email_delivery_retry_on_failure():
    """
    Test email delivery retry logic with exponential backoff.
    
    Validates: Requirements 7.6
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        # Mock SES to fail twice, then succeed
        mock_ses.send_email.side_effect = [
            ClientError(
                {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
                'SendEmail'
            ),
            ClientError(
                {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
                'SendEmail'
            ),
            {'MessageId': 'msg-12345'}
        ]
        
        service = SESDeliveryService(
            sender_email="test@example.com",
            max_retries=3,
            retry_backoff_base=0.1  # Faster for testing
        )
        
        start_time = time.time()
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"]
        )
        elapsed = time.time() - start_time
        
        # Verify successful delivery after retries
        assert result['success'] is True
        assert result['message_id'] == 'msg-12345'
        assert result['attempt'] == 3
        
        # Verify exponential backoff was applied
        # Expected delays: 0.1s, 0.2s = 0.3s minimum
        assert elapsed >= 0.3
        
        # Verify SES was called 3 times
        assert mock_ses.send_email.call_count == 3


def test_email_delivery_failure_after_retries():
    """
    Test email delivery failure after all retries exhausted.
    
    Validates: Requirements 7.6
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        # Mock SES to always fail
        mock_ses.send_email.side_effect = ClientError(
            {'Error': {'Code': 'MessageRejected', 'Message': 'Email address not verified'}},
            'SendEmail'
        )
        
        service = SESDeliveryService(
            sender_email="test@example.com",
            max_retries=2,
            retry_backoff_base=0.1
        )
        
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"]
        )
        
        # Verify delivery failed
        assert result['success'] is False
        assert 'error' in result
        assert 'MessageRejected' in result['error']
        assert result['attempts'] == 3  # Initial + 2 retries
        
        # Verify SES was called 3 times
        assert mock_ses.send_email.call_count == 3


def test_html_email_rendering():
    """
    Test HTML email rendering with proper formatting.
    
    Validates: Requirements 7.2, 7.3
    """
    html_content = format_html_email(SAMPLE_ALERT)
    
    # Verify HTML structure
    assert '<!DOCTYPE html>' in html_content
    assert '<html>' in html_content
    assert '</html>' in html_content
    
    # Verify incident information
    assert 'inc-test-001' in html_content
    assert 'payment-processor' in html_content
    
    # Verify root cause section
    assert 'Root Cause' in html_content
    assert 'resource_exhaustion' in html_content
    assert 'DynamoDB read capacity exceeded' in html_content
    
    # Verify confidence score
    assert '85' in html_content
    assert 'confidence' in html_content.lower()
    
    # Verify evidence items
    for evidence in SAMPLE_ALERT['root_cause']['evidence']:
        assert evidence in html_content
    
    # Verify fix recommendations
    assert 'Enable DynamoDB auto-scaling' in html_content
    assert 'Implement exponential backoff' in html_content
    
    # Verify commands
    assert 'aws dynamodb update-table' in html_content
    
    # Verify business summary
    assert 'Payment transactions are failing' in html_content
    assert '35 minutes' in html_content
    
    # Verify CSS styling
    assert '<style>' in html_content
    assert 'font-family' in html_content


def test_plain_text_email_fallback():
    """
    Test plain text email fallback rendering.
    
    Validates: Requirements 7.2, 7.3
    """
    text_content = format_text_email(SAMPLE_ALERT)
    
    # Verify text structure (no HTML tags)
    assert '<html>' not in text_content
    assert '<div>' not in text_content
    
    # Verify incident information
    assert 'inc-test-001' in text_content
    assert 'payment-processor' in text_content
    
    # Verify root cause section
    assert 'ROOT CAUSE' in text_content or 'Root Cause' in text_content
    assert 'resource_exhaustion' in text_content
    assert 'DynamoDB read capacity exceeded' in text_content
    
    # Verify confidence score
    assert '85' in text_content
    
    # Verify evidence items
    for evidence in SAMPLE_ALERT['root_cause']['evidence']:
        assert evidence in text_content
    
    # Verify fix recommendations
    assert 'Enable DynamoDB auto-scaling' in text_content
    assert 'Implement exponential backoff' in text_content
    
    # Verify commands
    assert 'aws dynamodb update-table' in text_content
    
    # Verify business summary
    assert 'Payment transactions are failing' in text_content
    
    # Verify section separators
    assert '---' in text_content or '===' in text_content


def test_email_with_multiple_recipients():
    """
    Test email delivery to multiple recipients and CC addresses.
    
    Validates: Requirements 7.1
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {'MessageId': 'msg-12345'}
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        recipients = ["oncall1@example.com", "oncall2@example.com"]
        cc_recipients = ["manager@example.com", "director@example.com"]
        
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=recipients,
            cc_recipients=cc_recipients
        )
        
        # Verify successful delivery
        assert result['success'] is True
        assert result['recipients'] == recipients
        assert result['cc_recipients'] == cc_recipients
        
        # Verify SES was called with correct recipients
        call_args = mock_ses.send_email.call_args[1]
        assert call_args['Destination']['ToAddresses'] == recipients
        assert call_args['Destination']['CcAddresses'] == cc_recipients


def test_email_subject_line_generation():
    """
    Test email subject line generation with incident ID and service name.
    
    Validates: Requirements 7.5
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {'MessageId': 'msg-12345'}
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"]
        )
        
        # Verify subject line
        call_args = mock_ses.send_email.call_args[1]
        subject = call_args['Message']['Subject']['Data']
        
        assert 'inc-test-001' in subject
        assert 'payment-processor' in subject
        assert '🚨' in subject  # Alert emoji


def test_low_confidence_alert_rendering():
    """
    Test email rendering for low confidence alerts (< 50%).
    
    Validates: Requirements 7.4
    """
    low_confidence_alert = SAMPLE_ALERT.copy()
    low_confidence_alert['confidence_score'] = 35
    
    html_content = format_html_email(low_confidence_alert)
    text_content = format_text_email(low_confidence_alert)
    
    # Verify low confidence warning in HTML
    assert 'warning' in html_content.lower()
    assert 'low confidence' in html_content.lower() or '50' in html_content
    
    # Verify low confidence warning in text
    assert 'WARNING' in text_content or 'warning' in text_content.lower()
    assert 'low confidence' in text_content.lower() or '50' in text_content


def test_convenience_function():
    """
    Test the convenience function for quick email delivery.
    
    Validates: Requirements 7.1
    """
    # Mock SES client
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        mock_ses.send_email.return_value = {'MessageId': 'msg-12345'}
        
        result = send_incident_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"],
            sender_email="test@example.com"
        )
        
        # Verify successful delivery
        assert result['success'] is True
        assert result['message_id'] == 'msg-12345'


def test_email_delivery_timing_warning():
    """
    Test that delivery timing warnings are logged when exceeding 5 seconds.
    
    Validates: Requirements 7.1
    """
    # Mock SES client with delay
    with mock.patch('boto3.client') as mock_boto_client:
        mock_ses = mock.Mock()
        mock_boto_client.return_value = mock_ses
        
        def delayed_send(*args, **kwargs):
            time.sleep(6)  # Exceed 5 second target
            return {'MessageId': 'msg-12345'}
        
        mock_ses.send_email.side_effect = delayed_send
        
        service = SESDeliveryService(sender_email="test@example.com")
        
        result = service.deliver_alert(
            enhanced_alert=SAMPLE_ALERT,
            recipients=["oncall@example.com"]
        )
        
        # Verify delivery succeeded but took too long
        assert result['success'] is True
        assert result['delivery_time_seconds'] > 5.0


def test_email_with_similar_incidents():
    """
    Test email rendering with similar past incidents.
    
    Validates: Requirements 7.2, 7.3
    """
    alert_with_similar = SAMPLE_ALERT.copy()
    alert_with_similar['agent_outputs'] = {
        'root-cause': {
            'success': True,
            'output': {
                'similar_incidents': [
                    {
                        'incident_id': 'inc-2024-12-01-001',
                        'similarity_score': 0.85,
                        'resolution': 'Enabled DynamoDB auto-scaling'
                    },
                    {
                        'incident_id': 'inc-2024-11-15-003',
                        'similarity_score': 0.72,
                        'resolution': 'Increased read capacity units'
                    }
                ]
            }
        }
    }
    
    html_content = format_html_email(alert_with_similar)
    text_content = format_text_email(alert_with_similar)
    
    # Verify similar incidents in HTML
    assert 'Similar' in html_content or 'similar' in html_content.lower()
    assert 'inc-2024-12-01-001' in html_content
    assert 'inc-2024-11-15-003' in html_content
    assert '85%' in html_content or '0.85' in html_content
    
    # Verify similar incidents in text
    assert 'inc-2024-12-01-001' in text_content
    assert 'inc-2024-11-15-003' in text_content
