"""
Property-Based Tests for Incident Storage Completeness

This module tests Property 30: Incident Storage Completeness

Property 30: Incident Storage Completeness
For any stored incident record, it should include service_name, failure_type,
root_cause, fix_applied, and resolution_time.

Validates: Requirements 8.2
"""

from datetime import datetime, timedelta
from unittest import mock
from hypothesis import given, strategies as st, settings
import pytest

from src.history.incident_storage import IncidentStorage


# Strategy for generating enhanced alerts
@st.composite
def enhanced_alert_strategy(draw):
    """Generate valid enhanced alert dictionaries."""
    import uuid
    
    service_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-'
    )))
    
    failure_type = draw(st.sampled_from([
        'configuration_error',
        'resource_exhaustion',
        'dependency_failure'
    ]))
    
    return {
        'incident_id': f"inc-{uuid.uuid4()}",
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'original_alert': {
            'service_name': service_name,
            'error_message': draw(st.text(min_size=10, max_size=100)),
            'log_location': f"s3://logs/{service_name}/2025-01-15.log"
        },
        'root_cause': {
            'category': failure_type,
            'description': draw(st.text(min_size=20, max_size=200)),
            'confidence_score': draw(st.integers(min_value=0, max_value=100)),
            'evidence': draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        },
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
        'agent_outputs': {
            'log-analysis': {
                'success': True,
                'output': {
                    'error_patterns': [
                        {'pattern': draw(st.text(min_size=5, max_size=30))}
                        for _ in range(draw(st.integers(min_value=1, max_value=5)))
                    ]
                }
            },
            'root-cause': {
                'success': True,
                'output': {
                    'similar_incidents': []
                }
            },
            'fix-recommendation': {
                'success': True,
                'output': {
                    'immediate_actions': draw(st.lists(
                        st.fixed_dictionaries({
                            'action': st.text(min_size=10, max_size=100),
                            'command': st.text(min_size=10, max_size=200)
                        }),
                        min_size=1,
                        max_size=3
                    ))
                }
            }
        }
    }


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_incident_storage_completeness(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness
    
    For any stored incident record, it should include service_name, failure_type,
    root_cause, fix_applied, and resolution_time.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Capture the stored item
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        # Store incident
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        # Verify storage succeeded
        assert result['success'] is True
        assert stored_item is not None
        
        # Property: Stored record must include service_name
        assert 'service_name' in stored_item, (
            "Stored incident must include service_name"
        )
        assert stored_item['service_name'] == alert['original_alert']['service_name']
        
        # Property: Stored record must include failure_type
        assert 'failure_type' in stored_item, (
            "Stored incident must include failure_type"
        )
        assert stored_item['failure_type'] in [
            'configuration_error',
            'resource_exhaustion',
            'dependency_failure',
            'unknown'
        ]
        
        # Property: Stored record must include root_cause
        assert 'root_cause' in stored_item, (
            "Stored incident must include root_cause"
        )
        assert isinstance(stored_item['root_cause'], dict)
        assert 'category' in stored_item['root_cause']
        assert 'description' in stored_item['root_cause']
        assert 'confidence_score' in stored_item['root_cause']
        
        # Property: Stored record must include fix_applied
        assert 'fix_applied' in stored_item, (
            "Stored incident must include fix_applied"
        )
        
        # Property: Stored record must include resolution_time_seconds
        assert 'resolution_time_seconds' in stored_item, (
            "Stored incident must include resolution_time_seconds"
        )
        assert isinstance(stored_item['resolution_time_seconds'], (int, float))


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_required_fields_non_empty(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (Non-Empty Fields)
    
    For any stored incident, required fields should not be empty or null.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        assert result['success'] is True
        assert stored_item is not None
        
        # Property: service_name should not be empty
        assert stored_item['service_name'], (
            "service_name should not be empty"
        )
        
        # Property: failure_type should not be empty
        assert stored_item['failure_type'], (
            "failure_type should not be empty"
        )
        
        # Property: root_cause should not be empty dict
        assert stored_item['root_cause'], (
            "root_cause should not be empty"
        )
        
        # Property: resolution_time_seconds should be a valid number
        assert stored_item['resolution_time_seconds'] >= 0, (
            "resolution_time_seconds should be non-negative"
        )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_incident_id_preserved(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (ID Preservation)
    
    For any stored incident, the incident_id should be preserved exactly.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        # Property: incident_id should be preserved
        assert stored_item['incident_id'] == alert['incident_id']
        assert result['incident_id'] == alert['incident_id']


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_timestamp_preserved(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (Timestamp)
    
    For any stored incident, the timestamp should be preserved.
    
    Validates: Requirements 8.2, 8.6
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        # Property: timestamp should be present
        assert 'timestamp' in stored_item
        
        # Property: timestamp should be in ISO 8601 format
        timestamp = stored_item['timestamp']
        assert 'T' in timestamp, "Timestamp should contain 'T' separator"
        assert timestamp.endswith('Z') or '+' in timestamp, (
            "Timestamp should have timezone indicator"
        )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_ttl_configured(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (TTL)
    
    For any stored incident, TTL should be configured for automatic deletion.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table", ttl_days=90)
        result = storage.store_incident(alert)
        
        # Property: TTL field should be present
        assert 'ttl' in stored_item, (
            "Stored incident must include TTL field"
        )
        
        # Property: TTL should be a valid Unix timestamp
        assert isinstance(stored_item['ttl'], int)
        assert stored_item['ttl'] > 0
        
        # Property: TTL should be approximately 90 days in the future
        import time
        current_time = int(time.time())
        ttl_value = stored_item['ttl']
        days_90_seconds = 90 * 24 * 60 * 60
        
        # Allow some tolerance (within 1 day)
        assert abs((ttl_value - current_time) - days_90_seconds) < 86400, (
            f"TTL should be approximately 90 days from now. "
            f"Expected ~{days_90_seconds}s, got {ttl_value - current_time}s"
        )


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_error_patterns_stored(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (Error Patterns)
    
    For any stored incident with error patterns, they should be preserved.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        # Property: error_patterns field should be present
        assert 'error_patterns' in stored_item
        
        # Property: error_patterns should be a list
        assert isinstance(stored_item['error_patterns'], list)


@given(alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_30_complete_alert_stored(alert):
    """
    Feature: incident-response-system
    Property 30: Incident Storage Completeness (Complete Alert)
    
    For any stored incident, the complete enhanced_alert should be stored
    for reference.
    
    Validates: Requirements 8.2
    """
    # Mock DynamoDB
    with mock.patch('boto3.resource') as mock_boto_resource, \
         mock.patch('boto3.client') as mock_boto_client:
        
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        stored_item = None
        
        def capture_put_item(**kwargs):
            nonlocal stored_item
            stored_item = kwargs['Item']
            return {}
        
        mock_table.put_item.side_effect = capture_put_item
        
        storage = IncidentStorage(table_name="test-table")
        result = storage.store_incident(alert)
        
        # Property: enhanced_alert should be stored
        assert 'enhanced_alert' in stored_item
        
        # Property: stored enhanced_alert should match input
        assert stored_item['enhanced_alert'] == alert
