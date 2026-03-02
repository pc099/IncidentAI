#!/usr/bin/env python3
"""
Unit tests for Bedrock Knowledge Base query module.

Tests cover:
- Converting incidents to query text
- Querying Knowledge Base for similar incidents
- Parsing incident metadata
- Error handling

Requirements: 3.5, 3.6
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.agents.kb_query import (
    convert_incident_to_query,
    query_similar_incidents,
    parse_incident_metadata
)


class TestConvertIncidentToQuery:
    """Test incident to query text conversion"""
    
    def test_basic_query_conversion(self):
        """Test basic incident conversion without log summary"""
        query = convert_incident_to_query(
            service_name="payment-processor",
            error_message="Service health check failed"
        )
        
        assert "Service: payment-processor" in query
        assert "Error: Service health check failed" in query
    
    def test_query_with_error_patterns(self):
        """Test query conversion with error patterns from log summary"""
        log_summary = {
            "error_patterns": [
                {"pattern": "ConnectionTimeout", "occurrences": 15},
                {"pattern": "SocketTimeoutException", "occurrences": 10}
            ]
        }
        
        query = convert_incident_to_query(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary
        )
        
        assert "Service: payment-processor" in query
        assert "Error: Connection timeout" in query
        assert "Patterns: ConnectionTimeout, SocketTimeoutException" in query
    
    def test_query_with_string_patterns(self):
        """Test query conversion with string patterns"""
        log_summary = {
            "error_patterns": ["ConnectionTimeout", "SocketTimeout"]
        }
        
        query = convert_incident_to_query(
            service_name="api-gateway",
            error_message="Timeout",
            log_summary=log_summary
        )
        
        assert "Patterns: ConnectionTimeout, SocketTimeout" in query
    
    def test_query_with_empty_patterns(self):
        """Test query conversion with empty patterns list"""
        log_summary = {
            "error_patterns": []
        }
        
        query = convert_incident_to_query(
            service_name="lambda-function",
            error_message="Deployment failed",
            log_summary=log_summary
        )
        
        assert "Service: lambda-function" in query
        assert "Error: Deployment failed" in query
        assert "Patterns:" not in query
    
    def test_query_with_no_log_summary(self):
        """Test query conversion with None log summary"""
        query = convert_incident_to_query(
            service_name="dynamodb-table",
            error_message="Throttling exception",
            log_summary=None
        )
        
        assert "Service: dynamodb-table" in query
        assert "Error: Throttling exception" in query
        assert "Patterns:" not in query


class TestQuerySimilarIncidents:
    """Test Knowledge Base query functionality"""
    
    @patch("src.agents.kb_query.boto3.client")
    def test_successful_query(self, mock_boto_client):
        """Test successful Knowledge Base query with results"""
        # Mock Bedrock Agent Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock retrieve response
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "score": 0.85,
                    "metadata": {
                        "incident_id": "inc-2024-11-23-001",
                        "root_cause": "Payment gateway timeout",
                        "service_name": "payment-processor"
                    },
                    "content": {
                        "text": "Increased timeout threshold to 30s"
                    }
                },
                {
                    "score": 0.72,
                    "metadata": {
                        "incident_id": "inc-2024-12-01-002",
                        "root_cause": "Network connectivity issue"
                    },
                    "content": {
                        "text": "Restarted network interface"
                    }
                }
            ]
        }
        
        # Query similar incidents
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="payment-processor",
            error_message="Connection timeout"
        )
        
        # Verify results
        assert len(results) == 2
        
        # Check first result
        assert results[0]["incident_id"] == "inc-2024-11-23-001"
        assert results[0]["similarity_score"] == 0.85
        assert results[0]["root_cause"] == "Payment gateway timeout"
        assert results[0]["resolution"] == "Increased timeout threshold to 30s"
        
        # Check second result
        assert results[1]["incident_id"] == "inc-2024-12-01-002"
        assert results[1]["similarity_score"] == 0.72
        
        # Verify retrieve was called correctly
        mock_client.retrieve.assert_called_once()
        call_args = mock_client.retrieve.call_args
        assert call_args[1]["knowledgeBaseId"] == "kb-test-123"
        assert "retrievalQuery" in call_args[1]
        assert "retrievalConfiguration" in call_args[1]
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_with_similarity_threshold(self, mock_boto_client):
        """Test that results below similarity threshold are filtered"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock retrieve response with varying scores
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "score": 0.85,
                    "metadata": {"incident_id": "inc-001"},
                    "content": {"text": "Fix 1"}
                },
                {
                    "score": 0.55,  # Below default threshold of 0.6
                    "metadata": {"incident_id": "inc-002"},
                    "content": {"text": "Fix 2"}
                },
                {
                    "score": 0.70,
                    "metadata": {"incident_id": "inc-003"},
                    "content": {"text": "Fix 3"}
                }
            ]
        }
        
        # Query with default threshold (0.6)
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error"
        )
        
        # Should only return 2 results (scores 0.85 and 0.70)
        assert len(results) == 2
        assert results[0]["incident_id"] == "inc-001"
        assert results[1]["incident_id"] == "inc-003"
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_with_custom_threshold(self, mock_boto_client):
        """Test query with custom similarity threshold"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "score": 0.85,
                    "metadata": {"incident_id": "inc-001"},
                    "content": {"text": "Fix 1"}
                },
                {
                    "score": 0.75,
                    "metadata": {"incident_id": "inc-002"},
                    "content": {"text": "Fix 2"}
                }
            ]
        }
        
        # Query with higher threshold
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error",
            similarity_threshold=0.8
        )
        
        # Should only return 1 result (score 0.85)
        assert len(results) == 1
        assert results[0]["incident_id"] == "inc-001"
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_with_max_results(self, mock_boto_client):
        """Test query with custom max_results parameter"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": []
        }
        
        # Query with custom max_results
        query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error",
            max_results=10
        )
        
        # Verify max_results was passed to retrieve
        call_args = mock_client.retrieve.call_args
        vector_config = call_args[1]["retrievalConfiguration"]["vectorSearchConfiguration"]
        assert vector_config["numberOfResults"] == 10
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_with_log_summary(self, mock_boto_client):
        """Test query includes error patterns from log summary"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": []
        }
        
        log_summary = {
            "error_patterns": [
                {"pattern": "ConnectionTimeout"}
            ]
        }
        
        # Query with log summary
        query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error",
            log_summary=log_summary
        )
        
        # Verify query text includes patterns
        call_args = mock_client.retrieve.call_args
        query_text = call_args[1]["retrievalQuery"]["text"]
        assert "ConnectionTimeout" in query_text
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_empty_results(self, mock_boto_client):
        """Test query with no matching results"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": []
        }
        
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error"
        )
        
        assert results == []
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_client_error(self, mock_boto_client):
        """Test error handling when Knowledge Base query fails"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Simulate ClientError
        mock_client.retrieve.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "KB not found"}},
            "Retrieve"
        )
        
        # Should return empty list on error
        results = query_similar_incidents(
            knowledge_base_id="kb-invalid",
            service_name="test-service",
            error_message="Test error"
        )
        
        assert results == []
    
    @patch("src.agents.kb_query.boto3.client")
    def test_query_unexpected_error(self, mock_boto_client):
        """Test error handling for unexpected exceptions"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Simulate unexpected error
        mock_client.retrieve.side_effect = Exception("Unexpected error")
        
        # Should return empty list on error
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error"
        )
        
        assert results == []
    
    @patch("src.agents.kb_query.boto3.client")
    def test_hybrid_search_configuration(self, mock_boto_client):
        """Test that hybrid search is configured correctly"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": []
        }
        
        query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="test-service",
            error_message="Test error"
        )
        
        # Verify hybrid search is enabled
        call_args = mock_client.retrieve.call_args
        vector_config = call_args[1]["retrievalConfiguration"]["vectorSearchConfiguration"]
        assert vector_config["overrideSearchType"] == "HYBRID"


class TestParseIncidentMetadata:
    """Test incident metadata parsing"""
    
    def test_parse_basic_metadata(self):
        """Test parsing basic incident metadata"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-2024-11-23-001",
                "root_cause": "Payment gateway timeout"
            },
            "content": {
                "text": "Increased timeout threshold to 30s"
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["incident_id"] == "inc-2024-11-23-001"
        assert incident["root_cause"] == "Payment gateway timeout"
        assert incident["resolution"] == "Increased timeout threshold to 30s"
    
    def test_parse_dict_root_cause(self):
        """Test parsing root cause when it's a dict"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-001",
                "root_cause": {
                    "category": "dependency_failure",
                    "description": "External API timeout"
                }
            },
            "content": {
                "text": "Increased timeout"
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["root_cause"] == "External API timeout"
    
    def test_parse_dict_root_cause_category_only(self):
        """Test parsing root cause dict with only category"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-001",
                "root_cause": {
                    "category": "resource_exhaustion"
                }
            },
            "content": {
                "text": "Scaled up resources"
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["root_cause"] == "resource_exhaustion"
    
    def test_parse_resolution_from_metadata(self):
        """Test parsing resolution from metadata when content is empty"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-001",
                "root_cause": "timeout",
                "resolution": {
                    "action": "Increased timeout to 30s",
                    "success": True
                }
            },
            "content": {
                "text": ""
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["resolution"] == "Increased timeout to 30s"
    
    def test_parse_additional_metadata_fields(self):
        """Test parsing additional metadata fields"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-001",
                "root_cause": "timeout",
                "service_name": "payment-processor",
                "failure_type": "dependency_failure",
                "timestamp": "2024-11-23T10:30:00Z"
            },
            "content": {
                "text": "Fixed timeout"
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["service_name"] == "payment-processor"
        assert incident["failure_type"] == "dependency_failure"
        assert incident["timestamp"] == "2024-11-23T10:30:00Z"
    
    def test_parse_missing_metadata(self):
        """Test parsing with missing metadata fields"""
        retrieval_result = {
            "metadata": {},
            "content": {}
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["incident_id"] == "unknown"
        assert incident["root_cause"] == ""
        assert incident["resolution"] == ""
    
    def test_parse_missing_content(self):
        """Test parsing with missing content"""
        retrieval_result = {
            "metadata": {
                "incident_id": "inc-001",
                "root_cause": "timeout"
            }
        }
        
        incident = parse_incident_metadata(retrieval_result)
        
        assert incident["incident_id"] == "inc-001"
        assert incident["resolution"] == ""


class TestIntegrationScenarios:
    """Test realistic integration scenarios"""
    
    @patch("src.agents.kb_query.boto3.client")
    def test_lambda_deployment_failure_query(self, mock_boto_client):
        """Test querying for Lambda deployment failure"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "score": 0.88,
                    "metadata": {
                        "incident_id": "inc-lambda-001",
                        "root_cause": "Deployment package too large",
                        "service_name": "lambda-function",
                        "failure_type": "configuration_error"
                    },
                    "content": {
                        "text": "Reduced package size by removing unused dependencies"
                    }
                }
            ]
        }
        
        log_summary = {
            "error_patterns": [
                {"pattern": "DeploymentPackageTooLarge"}
            ]
        }
        
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="lambda-function",
            error_message="Lambda deployment failed: package size exceeds limit",
            log_summary=log_summary
        )
        
        assert len(results) == 1
        assert results[0]["incident_id"] == "inc-lambda-001"
        assert results[0]["failure_type"] == "configuration_error"
    
    @patch("src.agents.kb_query.boto3.client")
    def test_dynamodb_throttling_query(self, mock_boto_client):
        """Test querying for DynamoDB throttling"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "score": 0.92,
                    "metadata": {
                        "incident_id": "inc-ddb-001",
                        "root_cause": "DynamoDB throttling",
                        "failure_type": "resource_exhaustion"
                    },
                    "content": {
                        "text": "Enabled auto-scaling for read/write capacity"
                    }
                }
            ]
        }
        
        results = query_similar_incidents(
            knowledge_base_id="kb-test-123",
            service_name="dynamodb-table",
            error_message="ProvisionedThroughputExceededException"
        )
        
        assert len(results) == 1
        assert results[0]["failure_type"] == "resource_exhaustion"
