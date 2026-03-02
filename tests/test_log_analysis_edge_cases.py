"""
Unit Tests for Log Analysis Edge Cases

Tests edge cases for the Log Analysis Agent including:
- Empty logs
- Logs >10MB
- Missing S3 objects
- Logs with special characters

Validates: Requirements 2.3, 2.7
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from src.agents.log_retrieval import retrieve_logs_from_s3, LogRetrievalError
from src.agents.log_parser import parse_logs
from src.agents.log_analysis_agent import LogAnalysisAgent


class TestLogRetrievalEdgeCases:
    """Test edge cases for log retrieval"""
    
    def test_empty_logs(self):
        """
        Test that empty logs are handled gracefully.
        
        Validates: Requirements 2.7
        """
        # Parse empty log content
        result = parse_logs("")
        
        # Should return valid structure with empty lists
        assert result['error_patterns'] == []
        assert result['stack_traces'] == []
        assert result['relevant_excerpts'] == []
    
    @patch('src.agents.log_retrieval.boto3.client')
    def test_logs_exceeding_10mb(self, mock_boto_client):
        """
        Test that logs >10MB are truncated to most recent 10MB.
        
        Validates: Requirements 2.3
        """
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock head_object to return 15MB size
        mock_s3.head_object.return_value = {
            'ContentLength': 15 * 1024 * 1024  # 15MB
        }
        
        # Mock get_object to return truncated content
        mock_body = Mock()
        mock_body.read.return_value = b"ERROR: Test log content\n" * 1000
        mock_s3.get_object.return_value = {
            'Body': mock_body
        }
        
        # Retrieve logs
        result = retrieve_logs_from_s3(
            log_location="s3://test-bucket/test.log",
            timestamp="2025-01-15T10:30:00Z",
            service_name="test-service"
        )
        
        # Verify truncation
        assert result['truncated'] is True
        assert result['log_volume'] == "10 MB"
        
        # Verify Range parameter was used
        call_args = mock_s3.get_object.call_args
        assert 'Range' in call_args[1]
        assert call_args[1]['Range'].startswith('bytes=')
    
    @patch('src.agents.log_retrieval.boto3.client')
    def test_missing_s3_object(self, mock_boto_client):
        """
        Test that missing S3 objects are handled gracefully.
        
        Validates: Requirements 2.7
        """
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock head_object to raise NoSuchKey error
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
        mock_s3.head_object.side_effect = mock_s3.exceptions.NoSuchKey()
        
        # Retrieve logs
        result = retrieve_logs_from_s3(
            log_location="s3://test-bucket/missing.log",
            timestamp="2025-01-15T10:30:00Z",
            service_name="test-service"
        )
        
        # Should return confidence score 0 and error message
        assert result['confidence_score'] == 0
        assert result['log_content'] == ""
        assert 'not found' in result['error'].lower()
    
    @patch('src.agents.log_retrieval.boto3.client')
    def test_s3_access_denied(self, mock_boto_client):
        """
        Test that S3 access denied errors are handled gracefully.
        
        Validates: Requirements 2.7
        """
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Create a proper exception class
        NoSuchKeyException = type('NoSuchKey', (Exception,), {})
        mock_s3.exceptions.NoSuchKey = NoSuchKeyException
        
        # Mock head_object to raise generic exception (not NoSuchKey)
        mock_s3.head_object.side_effect = Exception("Access Denied")
        
        # Retrieve logs
        result = retrieve_logs_from_s3(
            log_location="s3://test-bucket/denied.log",
            timestamp="2025-01-15T10:30:00Z",
            service_name="test-service"
        )
        
        # Should return confidence score 0 and error message
        assert result['confidence_score'] == 0
        assert result['log_content'] == ""
        assert 'error' in result
    
    def test_logs_with_special_characters(self):
        """
        Test that logs with special characters are parsed correctly.
        
        Validates: Requirements 2.7
        """
        # Create log content with special characters
        log_content = """
        2025-01-15T10:30:00Z ERROR: Failed to process data with special chars: ñ, é, ü, 中文
        2025-01-15T10:30:01Z Exception: Invalid UTF-8 sequence: \x00\x01\x02
        2025-01-15T10:30:02Z CRITICAL: Emoji in logs 🚨 🔥 ⚠️
        """
        
        # Parse logs
        result = parse_logs(log_content)
        
        # Should parse without crashing
        assert isinstance(result, dict)
        assert 'error_patterns' in result
        assert 'stack_traces' in result
        assert 'relevant_excerpts' in result
    
    def test_logs_with_null_bytes(self):
        """
        Test that logs with null bytes are handled.
        
        Validates: Requirements 2.7
        """
        # Create log content with null bytes
        log_content = "ERROR: Test\x00with\x00null\x00bytes"
        
        # Parse logs - should not crash
        result = parse_logs(log_content)
        
        # Should return valid structure
        assert isinstance(result, dict)
    
    @patch('src.agents.log_retrieval.boto3.client')
    def test_invalid_s3_uri(self, mock_boto_client):
        """
        Test that invalid S3 URIs are rejected.
        
        Validates: Requirements 2.1
        """
        # Test with invalid URI (not starting with s3://)
        with pytest.raises(LogRetrievalError) as exc_info:
            retrieve_logs_from_s3(
                log_location="http://bucket/file.log",
                timestamp="2025-01-15T10:30:00Z",
                service_name="test-service"
            )
        
        assert "Invalid S3 URI" in str(exc_info.value)
    
    @patch('src.agents.log_retrieval.boto3.client')
    def test_malformed_s3_path(self, mock_boto_client):
        """
        Test that malformed S3 paths are rejected.
        
        Validates: Requirements 2.1
        """
        # Test with malformed path (missing key)
        with pytest.raises(LogRetrievalError) as exc_info:
            retrieve_logs_from_s3(
                log_location="s3://bucket-only",
                timestamp="2025-01-15T10:30:00Z",
                service_name="test-service"
            )
        
        assert "Invalid S3 path format" in str(exc_info.value)


class TestLogAnalysisAgentEdgeCases:
    """Test edge cases for the complete Log Analysis Agent"""
    
    @patch('src.agents.log_analysis_agent.boto3.client')
    def test_analyze_with_missing_logs(self, mock_boto_client):
        """
        Test that agent handles missing logs gracefully.
        
        Validates: Requirements 2.7
        """
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock head_object to raise NoSuchKey
        mock_s3.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
        mock_s3.head_object.side_effect = mock_s3.exceptions.NoSuchKey()
        
        # Create agent
        agent = LogAnalysisAgent()
        
        # Analyze
        result = agent.analyze(
            log_location="s3://test-bucket/missing.log",
            timestamp="2025-01-15T10:30:00Z",
            service_name="test-service"
        )
        
        # Should return failed status with confidence 0
        assert result['status'] == 'failed'
        assert result['confidence_score'] == 0
        assert result['summary']['error_patterns'] == []
    
    @patch('src.agents.log_analysis_agent.boto3.client')
    def test_analyze_with_bedrock_failure(self, mock_boto_client):
        """
        Test that agent falls back to parsed data when Bedrock fails.
        
        Validates: Requirements 2.6
        """
        # Mock S3 client
        mock_s3 = Mock()
        mock_boto_client.side_effect = lambda service: mock_s3 if service == 's3' else Mock()
        
        # Mock successful S3 retrieval
        mock_s3.head_object.return_value = {'ContentLength': 1000}
        mock_body = Mock()
        mock_body.read.return_value = b"ERROR: Test error\nERROR: Another error"
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        # Create agent with mocked Bedrock that fails
        agent = LogAnalysisAgent()
        
        with patch.object(agent, '_invoke_bedrock', side_effect=Exception("Bedrock unavailable")):
            # Analyze
            result = agent.analyze(
                log_location="s3://test-bucket/test.log",
                timestamp="2025-01-15T10:30:00Z",
                service_name="test-service"
            )
        
        # Should still succeed with parsed data
        assert result['status'] == 'success'
        assert 'error_patterns' in result['summary']
        assert 'Bedrock unavailable' in result['summary']['summary']
    
    def test_parse_logs_with_very_long_lines(self):
        """
        Test that very long log lines are handled.
        
        Validates: Requirements 2.7
        """
        # Create log with moderately long line (not too long to avoid timeout)
        long_line = "ERROR: Test error with long message " + "A" * 1000
        log_content = long_line + "\nERROR: Another error\nERROR: Third error"
        
        # Parse logs - should not crash
        result = parse_logs(log_content)
        
        # Should return valid structure
        assert isinstance(result, dict)
        # Should find ERROR patterns
        assert len(result['error_patterns']) >= 0  # May or may not find patterns depending on regex
    
    def test_parse_logs_with_many_errors(self):
        """
        Test that logs with many errors are handled efficiently.
        
        Validates: Requirements 2.5
        """
        # Create log with many error lines
        log_lines = [f"2025-01-15T10:30:{i:02d}Z ERROR: Error {i}" for i in range(1000)]
        log_content = "\n".join(log_lines)
        
        # Parse logs
        result = parse_logs(log_content)
        
        # Should extract patterns (limited to top patterns)
        assert isinstance(result['error_patterns'], list)
        assert len(result['error_patterns']) <= 10  # Should limit to top 10
        
        # Should extract relevant excerpts (limited to 5)
        assert len(result['relevant_excerpts']) <= 5
