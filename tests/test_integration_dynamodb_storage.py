"""
Integration test for DynamoDB storage and retrieval.

Tests:
- Incident storage with all fields
- Query by service_name and failure pattern
- TTL configuration

Requirements: 8.1, 8.2, 8.3, 8.6
"""

import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timezone, timedelta

# Import modules to test
from src.history.incident_storage import IncidentStorage
from src.history.incident_query import IncidentQuery


class TestDynamoDBStorageAndRetrieval:
    """Integration tests for DynamoDB incident storage and retrieval."""
    
    @mock_aws
    def test_incident_storage_with_all_fields(self):
        """
        Test storing incident with all required fields.
        
        Requirements: 8.1, 8.2
        """
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='incident-history',
            KeySchema=[
                {'AttributeName': 'incident_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'incident_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'service_name', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'service-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'service_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Create incident storage instance
        storage = IncidentStorage(table_name='incident-history')
        
        # Create incident data
        incident_data = {
            'incident_id': 'inc-2025-01-15-001',
            'timestamp': '2025-01-15T10:30:00Z',
            'service_name': 'payment-processor',
            'failure_type': 'dependency_failure',
            'root_cause': {
                'category': 'dependency_failure',
                'description': 'Payment gateway timeout',
                'confidence_score': 85
            },
            'error_patterns': ['ConnectionTimeout', 'SocketTimeoutException'],
            'fix_applied': {
                'action': 'Increased timeout to 30s',
                'timestamp': '2025-01-15T10:35:00Z',
                'applied_by': 'auto'
            },
            'resolution_time_seconds': 300,
            'log_location': 's3://logs/payment-processor/2025-01-15/10-30.log'
        }
        
        # Store incident
        storage.store_incident(incident_data)
        
        # Retrieve and verify
        response = table.get_item(
            Key={
                'incident_id': 'inc-2025-01-15-001',
                'timestamp': '2025-01-15T10:30:00Z'
            }
        )
        
        assert 'Item' in response
        item = response['Item']
        
        # Verify all required fields are present
        assert item['incident_id'] == 'inc-2025-01-15-001'
        assert item['timestamp'] == '2025-01-15T10:30:00Z'
        assert item['service_name'] == 'payment-processor'
        assert item['failure_type'] == 'dependency_failure'
        assert 'root_cause' in item
        assert 'error_patterns' in item
        assert 'fix_applied' in item
        assert item['resolution_time_seconds'] == 300
    
    @mock_aws
    def test_query_by_service_name(self):
        """
        Test querying incidents by service name.
        
        Requirements: 8.3
        """
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='incident-history',
            KeySchema=[
                {'AttributeName': 'incident_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'incident_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'service_name', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'service-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'service_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        
        # Create storage and query instances
        storage = IncidentStorage(table_name='incident-history')
        query = IncidentQuery(table_name='incident-history')
        
        # Store multiple incidents
        incidents = [
            {
                'incident_id': 'inc-2025-01-15-001',
                'timestamp': '2025-01-15T10:30:00Z',
                'service_name': 'payment-processor',
                'failure_type': 'dependency_failure',
                'root_cause': {'category': 'dependency_failure'},
                'error_patterns': ['ConnectionTimeout'],
                'fix_applied': {'action': 'Increased timeout'},
                'resolution_time_seconds': 300
            },
            {
                'incident_id': 'inc-2025-01-14-002',
                'timestamp': '2025-01-14T15:20:00Z',
                'service_name': 'payment-processor',
                'failure_type': 'dependency_failure',
                'root_cause': {'category': 'dependency_failure'},
                'error_patterns': ['ConnectionTimeout'],
                'fix_applied': {'action': 'Added retry logic'},
                'resolution_time_seconds': 600
            },
            {
                'incident_id': 'inc-2025-01-13-003',
                'timestamp': '2025-01-13T09:15:00Z',
                'service_name': 'order-service',
                'failure_type': 'resource_exhaustion',
                'root_cause': {'category': 'resource_exhaustion'},
                'error_patterns': ['OutOfMemoryError'],
                'fix_applied': {'action': 'Increased memory'},
                'resolution_time_seconds': 900
            }
        ]
        
        for incident in incidents:
            storage.store_incident(incident)
        
        # Query by service name
        results = query.query_by_service('payment-processor')
        
        # Verify results
        assert len(results) == 2
        for result in results:
            assert result['service_name'] == 'payment-processor'
    
    @mock_aws
    def test_ttl_configuration(self):
        """
        Test that TTL is configured correctly (90 days).
        
        Requirements: 8.6
        """
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='incident-history',
            KeySchema=[
                {'AttributeName': 'incident_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'incident_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create storage instance
        storage = IncidentStorage(table_name='incident-history')
        
        # Create incident
        now = datetime.now(timezone.utc)
        incident = {
            'incident_id': 'inc-2025-01-15-001',
            'timestamp': now.isoformat(),
            'service_name': 'test-service',
            'failure_type': 'test',
            'root_cause': {'category': 'test'},
            'error_patterns': ['test'],
            'fix_applied': {'action': 'test'},
            'resolution_time_seconds': 100
        }
        
        # Store incident
        storage.store_incident(incident)
        
        # Retrieve and verify TTL
        response = table.get_item(
            Key={
                'incident_id': 'inc-2025-01-15-001',
                'timestamp': now.isoformat()
            }
        )
        
        assert 'Item' in response
        item = response['Item']
        
        # Verify TTL field exists
        assert 'ttl' in item
        
        # Verify TTL is approximately 90 days from now
        stored_ttl = item['ttl']
        expected_ttl = int((now + timedelta(days=90)).timestamp())
        assert abs(stored_ttl - expected_ttl) < 86400  # Within 1 day
    
    @mock_aws
    def test_iso_8601_timestamp_format(self):
        """
        Test that timestamps are stored in ISO 8601 format.
        
        Requirements: 8.6
        """
        # Create mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='incident-history',
            KeySchema=[
                {'AttributeName': 'incident_id', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'incident_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create storage instance
        storage = IncidentStorage(table_name='incident-history')
        
        # Create incident with ISO 8601 timestamp
        incident = {
            'incident_id': 'inc-2025-01-15-001',
            'timestamp': '2025-01-15T10:30:00Z',
            'service_name': 'test-service',
            'failure_type': 'test',
            'root_cause': {'category': 'test'},
            'error_patterns': ['test'],
            'fix_applied': {'action': 'test', 'timestamp': '2025-01-15T10:35:00Z'},
            'resolution_time_seconds': 300
        }
        
        # Store incident
        storage.store_incident(incident)
        
        # Retrieve and verify
        response = table.get_item(
            Key={
                'incident_id': 'inc-2025-01-15-001',
                'timestamp': '2025-01-15T10:30:00Z'
            }
        )
        
        assert 'Item' in response
        item = response['Item']
        
        # Verify timestamp format
        timestamp = item['timestamp']
        assert 'T' in timestamp
        
        # Verify it can be parsed as ISO 8601
        parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
