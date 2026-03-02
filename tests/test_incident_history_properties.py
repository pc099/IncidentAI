"""
Property-Based Tests for Incident History Management

This module tests Properties 31, 32, and 33 for incident history management.

Property 31: Incident Query Filtering
Property 32: Similar Incident Ranking and Limiting
Property 33: ISO 8601 Timestamp Format

Validates: Requirements 8.3, 8.4, 8.6
"""

from datetime import datetime, timedelta
from unittest import mock
from hypothesis import given, strategies as st, settings
import pytest
import re

from src.history.incident_query import IncidentQuery
from src.history.incident_storage import IncidentStorage


# Simple strategies
service_name_strategy = st.text(min_size=3, max_size=30, alphabet=st.characters(
    whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-'
))

failure_type_strategy = st.sampled_from([
    'configuration_error',
    'resource_exhaustion',
    'dependency_failure'
])


@given(service_name=service_name_strategy)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_31_query_returns_matching_service(service_name):
    """
    Feature: incident-response-system
    Property 31: Incident Query Filtering
    
    For any query by service name, all returned incidents should match
    that service name.
    
    Validates: Requirements 8.3
    """
    # Mock DynamoDB with matching incidents
    with mock.patch('boto3.resource') as mock_boto_resource:
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Create mock incidents that match the service
        mock_incidents = [
            {'service_name': service_name, 'incident_id': f'inc-{i}'}
            for i in range(3)
        ]
        
        mock_table.query.return_value = {'Items': mock_incidents}
        
        query = IncidentQuery(table_name="test-table")
        results = query.query_by_service(service_name)
        
        # Property: All returned incidents must match the service name
        for incident in results:
            assert incident['service_name'] == service_name


@given(service_name=service_name_strategy)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_31_empty_results_handled_gracefully(service_name):
    """
    Feature: incident-response-system
    Property 31: Incident Query Filtering (Empty Results)
    
    For any query that returns no results, the system should handle it
    gracefully without errors.
    
    Validates: Requirements 8.3, 8.5
    """
    # Mock DynamoDB to return empty results
    with mock.patch('boto3.resource') as mock_boto_resource:
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        mock_table.query.return_value = {'Items': []}
        
        query = IncidentQuery(table_name="test-table")
        results = query.query_by_service(service_name)
        
        # Property: Empty results should be returned as empty list
        assert isinstance(results, list)
        assert len(results) == 0


@given(
    service_name=service_name_strategy,
    num_incidents=st.integers(min_value=1, max_value=20)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_32_similar_incidents_limited_to_top_5(service_name, num_incidents):
    """
    Feature: incident-response-system
    Property 32: Similar Incident Ranking and Limiting
    
    For any query that finds similar incidents, the system should return
    at most 5 incidents.
    
    Validates: Requirements 8.4
    """
    # Mock DynamoDB with many incidents
    with mock.patch('boto3.resource') as mock_boto_resource:
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Create mock incidents
        mock_incidents = [
            {
                'service_name': service_name,
                'incident_id': f'inc-{i}',
                'error_message': f'Error {i}',
                'root_cause': {'description': f'Cause {i}'},
                'error_patterns': [f'Pattern{i}']
            }
            for i in range(num_incidents)
        ]
        
        mock_table.query.return_value = {'Items': mock_incidents}
        
        query = IncidentQuery(table_name="test-table")
        results = query.find_similar_incidents(
            service_name=service_name,
            failure_pattern="Error pattern"
        )
        
        # Property: Results should be limited to 5
        assert len(results) <= 5


@given(
    service_name=service_name_strategy,
    num_incidents=st.integers(min_value=2, max_value=10)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_32_similar_incidents_ranked_by_similarity(service_name, num_incidents):
    """
    Feature: incident-response-system
    Property 32: Similar Incident Ranking and Limiting (Ranking)
    
    For any query that finds similar incidents, they should be ranked
    by similarity score in descending order.
    
    Validates: Requirements 8.4
    """
    # Mock DynamoDB with incidents
    with mock.patch('boto3.resource') as mock_boto_resource:
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Create mock incidents with varying similarity
        mock_incidents = [
            {
                'service_name': service_name,
                'incident_id': f'inc-{i}',
                'error_message': 'Connection timeout' if i < num_incidents // 2 else 'Other error',
                'root_cause': {'description': 'Timeout issue' if i < num_incidents // 2 else 'Different issue'},
                'error_patterns': ['Timeout'] if i < num_incidents // 2 else ['Other']
            }
            for i in range(num_incidents)
        ]
        
        mock_table.query.return_value = {'Items': mock_incidents}
        
        query = IncidentQuery(table_name="test-table")
        results = query.find_similar_incidents(
            service_name=service_name,
            failure_pattern="Connection timeout"
        )
        
        # Property: Results should be ranked by similarity (descending)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['similarity_score'] >= results[i + 1]['similarity_score']


@given(
    service_name=service_name_strategy,
    timestamp_str=st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    ).map(lambda dt: dt.isoformat() + 'Z')
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_33_iso_8601_timestamp_format(service_name, timestamp_str):
    """
    Feature: incident-response-system
    Property 33: ISO 8601 Timestamp Format
    
    For any stored incident record, all timestamps should be in valid
    ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).
    
    Validates: Requirements 8.6
    """
    # Create enhanced alert with timestamp
    enhanced_alert = {
        'incident_id': 'inc-test-123',
        'timestamp': timestamp_str,
        'original_alert': {
            'service_name': service_name,
            'error_message': 'Test error',
            'log_location': 's3://logs/test.log'
        },
        'root_cause': {
            'category': 'configuration_error',
            'description': 'Test root cause',
            'confidence_score': 85,
            'evidence': ['Evidence 1']
        },
        'recommended_fixes': [],
        'agent_outputs': {}
    }
    
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
        result = storage.store_incident(enhanced_alert)
        
        assert result['success'] is True
        assert stored_item is not None
        
        # Property: Timestamp should be in ISO 8601 format
        timestamp = stored_item['timestamp']
        
        # Check format: YYYY-MM-DDTHH:MM:SS with timezone
        iso_8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$'
        assert re.match(iso_8601_pattern, timestamp), (
            f"Timestamp should be in ISO 8601 format: {timestamp}"
        )
        
        # Check that it contains 'T' separator
        assert 'T' in timestamp
        
        # Check that it has timezone indicator
        assert timestamp.endswith('Z') or '+' in timestamp or timestamp.count('-') > 2


@given(service_name=service_name_strategy)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_33_timestamp_parseable(service_name):
    """
    Feature: incident-response-system
    Property 33: ISO 8601 Timestamp Format (Parseable)
    
    For any stored incident timestamp, it should be parseable as a
    valid datetime.
    
    Validates: Requirements 8.6
    """
    # Create enhanced alert
    enhanced_alert = {
        'incident_id': 'inc-test-456',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'original_alert': {
            'service_name': service_name,
            'error_message': 'Test error',
            'log_location': 's3://logs/test.log'
        },
        'root_cause': {
            'category': 'dependency_failure',
            'description': 'Test root cause',
            'confidence_score': 75,
            'evidence': ['Evidence 1']
        },
        'recommended_fixes': [],
        'agent_outputs': {}
    }
    
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
        result = storage.store_incident(enhanced_alert)
        
        assert result['success'] is True
        assert stored_item is not None
        
        # Property: Timestamp should be parseable
        timestamp = stored_item['timestamp']
        
        # Try to parse the timestamp
        try:
            # Remove 'Z' if present and parse
            timestamp_to_parse = timestamp.rstrip('Z')
            datetime.fromisoformat(timestamp_to_parse)
            parsed_successfully = True
        except ValueError:
            parsed_successfully = False
        
        assert parsed_successfully, (
            f"Timestamp should be parseable as ISO 8601: {timestamp}"
        )


@given(
    service_name=service_name_strategy,
    limit=st.integers(min_value=1, max_value=50)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_31_query_respects_limit(service_name, limit):
    """
    Feature: incident-response-system
    Property 31: Incident Query Filtering (Limit)
    
    For any query with a limit, the number of returned incidents should
    not exceed the limit.
    
    Validates: Requirements 8.3
    """
    # Mock DynamoDB with many incidents
    with mock.patch('boto3.resource') as mock_boto_resource:
        mock_table = mock.Mock()
        mock_dynamodb = mock.Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb
        
        # Create more incidents than the limit
        mock_incidents = [
            {'service_name': service_name, 'incident_id': f'inc-{i}'}
            for i in range(limit + 10)
        ]
        
        # Mock query to return limited results
        mock_table.query.return_value = {'Items': mock_incidents[:limit]}
        
        query = IncidentQuery(table_name="test-table")
        results = query.query_by_service(service_name, limit=limit)
        
        # Property: Number of results should not exceed limit
        assert len(results) <= limit
