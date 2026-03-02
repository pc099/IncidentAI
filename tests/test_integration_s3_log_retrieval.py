"""
Integration test for S3 log retrieval.

Tests:
- Successful log retrieval
- Missing log handling
- Large log truncation (>10MB)

Requirements: 2.1, 2.2, 2.3, 2.7
"""

import pytest
import boto3
from moto import mock_aws
from datetime import datetime, timedelta
import json

# Import module to test
from src.agents.log_retrieval import retrieve_logs_from_s3, calculate_time_window


class TestS3LogRetrieval:
    """Integration tests for S3 log retrieval."""
    
    @mock_aws
    def test_successful_log_retrieval(self):
        """
        Test successful retrieval of logs from S3.
        
        Requirements: 2.1, 2.2
        """
        # Create mock S3 bucket and upload test logs
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-logs-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create test log content
        log_content = """
2025-01-15T10:28:00Z INFO Starting payment processor
2025-01-15T10:29:00Z ERROR Connection timeout to payment-gateway.example.com
2025-01-15T10:29:30Z ERROR Connection timeout to payment-gateway.example.com
2025-01-15T10:30:00Z ERROR Service health check failed
2025-01-15T10:30:30Z ERROR Connection timeout to payment-gateway.example.com
2025-01-15T10:31:00Z INFO Attempting reconnection
"""
        
        # Upload log to S3
        log_key = 'payment-processor/2025/01/15/10-30.log'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=log_key,
            Body=log_content.encode('utf-8')
        )
        
        # Test log retrieval
        log_location = f's3://{bucket_name}/{log_key}'
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'payment-processor'
        
        result = retrieve_logs_from_s3(log_location, timestamp, service_name)
        
        # Verify successful retrieval
        assert 'log_content' in result
        assert 'ERROR' in result['log_content']
        assert 'Connection timeout' in result['log_content']
        
        # Verify log volume is calculated
        assert 'log_volume' in result
        assert result['log_volume'].endswith('KB') or result['log_volume'].endswith('MB')
        
        # Verify time range is included
        assert 'time_range' in result
        
        # Verify log content contains expected errors
        assert 'Service health check failed' in result['log_content']
        
        # Verify no truncation for small logs
        assert result.get('truncated') is False
    
    @mock_aws
    def test_missing_log_handling(self):
        """
        Test handling of missing logs in S3.
        
        Requirements: 2.7
        """
        # Create mock S3 bucket (but don't upload any logs)
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-logs-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Test log retrieval for non-existent log
        log_location = f's3://{bucket_name}/nonexistent/log.txt'
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'test-service'
        
        result = retrieve_logs_from_s3(log_location, timestamp, service_name)
        
        # Verify graceful handling of missing logs
        assert result['confidence_score'] == 0
        assert 'error' in result
        assert 'not found' in result['error'].lower() or 'not available' in result['error'].lower()
        
        # Verify time range is still calculated
        assert 'time_range' in result
    
    @mock_aws
    def test_large_log_truncation(self):
        """
        Test that logs >10MB are truncated to most recent 10MB.
        
        Requirements: 2.3
        """
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-logs-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create large log content (>10MB)
        # Each line is ~100 bytes, so 150,000 lines = ~15MB
        log_lines = []
        for i in range(150000):
            log_lines.append(
                f'2025-01-15T10:{i%60:02d}:{i%60:02d}Z INFO Processing request {i} - some additional data here\n'
            )
        
        # Add error at the end (most recent)
        log_lines.append('2025-01-15T10:30:00Z ERROR Service health check failed\n')
        log_lines.append('2025-01-15T10:30:01Z ERROR Connection timeout\n')
        
        large_log_content = ''.join(log_lines)
        
        # Upload large log to S3
        log_key = 'test-service/2025/01/15/10-30.log'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=log_key,
            Body=large_log_content.encode('utf-8')
        )
        
        # Test log retrieval
        log_location = f's3://{bucket_name}/{log_key}'
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'test-service'
        
        result = retrieve_logs_from_s3(log_location, timestamp, service_name)
        
        # Verify log was retrieved
        assert 'log_content' in result
        
        # Verify log was truncated to 10MB
        log_size_bytes = len(result['log_content'].encode('utf-8'))
        max_size_bytes = 10 * 1024 * 1024  # 10MB
        assert log_size_bytes <= max_size_bytes, f"Log size {log_size_bytes} exceeds 10MB limit"
        
        # Verify truncation flag is set
        assert result.get('truncated') is True
        
        # Verify most recent logs are included (error at the end)
        assert 'Service health check failed' in result['log_content']
        assert 'Connection timeout' in result['log_content']
    
    def test_time_window_calculation(self):
        """
        Test that time window is calculated correctly (15 min before, 5 min after).
        
        Requirements: 2.2
        """
        # Test timestamp
        timestamp = '2025-01-15T10:30:00Z'
        
        # Calculate time window
        start_time, end_time = calculate_time_window(timestamp)
        
        # Parse timestamps
        failure_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Verify start time is 15 minutes before
        expected_start = failure_time - timedelta(minutes=15)
        assert start_time == expected_start
        
        # Verify end time is 5 minutes after
        expected_end = failure_time + timedelta(minutes=5)
        assert end_time == expected_end
        
        # Verify total window is 20 minutes
        window_duration = end_time - start_time
        assert window_duration == timedelta(minutes=20)
    
    @mock_aws
    def test_log_retrieval_with_special_characters(self):
        """
        Test log retrieval with special characters and unicode.
        
        Requirements: 2.1
        """
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-logs-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Create log content with special characters
        log_content = """
2025-01-15T10:30:00Z ERROR Failed to process: {"error": "Invalid JSON", "details": "Unexpected character '\\u0000'"}
2025-01-15T10:30:01Z ERROR Stack trace: at com.example.Service.process(Service.java:142)
2025-01-15T10:30:02Z ERROR Message contains unicode: 日本語 テスト
2025-01-15T10:30:03Z ERROR Special chars: <>&"'
"""
        
        # Upload log to S3
        log_key = 'test-service/2025/01/15/10-30.log'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=log_key,
            Body=log_content.encode('utf-8')
        )
        
        # Test log retrieval
        log_location = f's3://{bucket_name}/{log_key}'
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'test-service'
        
        result = retrieve_logs_from_s3(log_location, timestamp, service_name)
        
        # Verify successful retrieval
        assert 'log_content' in result
        
        # Verify special characters are preserved
        assert 'Invalid JSON' in result['log_content']
        assert 'Service.java:142' in result['log_content']
        assert '日本語' in result['log_content']
        assert '<>&' in result['log_content']
    
    @mock_aws
    def test_log_retrieval_with_empty_file(self):
        """
        Test log retrieval when log file is empty.
        
        Requirements: 2.7
        """
        # Create mock S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-logs-bucket'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Upload empty log to S3
        log_key = 'test-service/2025/01/15/10-30.log'
        s3_client.put_object(
            Bucket=bucket_name,
            Key=log_key,
            Body=b''
        )
        
        # Test log retrieval
        log_location = f's3://{bucket_name}/{log_key}'
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'test-service'
        
        result = retrieve_logs_from_s3(log_location, timestamp, service_name)
        
        # Verify handling of empty log
        # System should still return success but with empty content
        assert 'log_content' in result
        assert result['log_content'] == '' or len(result['log_content']) == 0
        
        # Log volume should be 0
        assert '0' in result['log_volume']
    
    @mock_aws
    def test_log_retrieval_with_invalid_s3_uri(self):
        """
        Test log retrieval with invalid S3 URI format.
        
        Requirements: 2.7
        """
        # Test with invalid S3 URI
        invalid_uris = [
            'http://example.com/logs/test.log',
            's3://bucket-without-key',
            'not-a-uri',
            ''
        ]
        
        timestamp = '2025-01-15T10:30:00Z'
        service_name = 'test-service'
        
        for invalid_uri in invalid_uris:
            try:
                result = retrieve_logs_from_s3(invalid_uri, timestamp, service_name)
                
                # If no exception, verify graceful error handling
                assert result['confidence_score'] == 0
                assert 'error' in result
            except Exception as e:
                # Exception is also acceptable for invalid URIs
                assert 'Invalid S3 URI' in str(e) or 'Failed to retrieve logs' in str(e)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
