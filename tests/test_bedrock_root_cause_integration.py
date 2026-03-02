#!/usr/bin/env python3
"""
Unit tests for Bedrock Claude integration in Root Cause Agent.

Tests cover:
- Bedrock prompt template creation with similar incidents
- Claude model invocation with log summary and historical context
- Structured JSON response parsing
- Fallback to rule-based classification on errors

Requirements: 3.1, 3.7
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.agents.root_cause_classifier import BedrockRootCauseAnalyzer


class TestBedrockPromptCreation:
    """Test Bedrock prompt template creation"""
    
    def test_create_prompt_basic(self):
        """Test basic prompt creation without similar incidents"""
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [
                {"pattern": "TimeoutException", "occurrences": 15}
            ],
            "stack_traces": [
                {"exception": "java.net.SocketTimeoutException", "message": "Read timed out"}
            ],
            "relevant_excerpts": [
                "ERROR: Connection timeout to payment-gateway.example.com"
            ]
        }
        
        prompt = analyzer.create_prompt(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify prompt contains key elements
        assert "payment-processor" in prompt
        assert "Connection timeout" in prompt
        assert "TimeoutException" in prompt
        assert "15 occurrences" in prompt
        assert "java.net.SocketTimeoutException" in prompt
        assert "configuration_error" in prompt
        assert "resource_exhaustion" in prompt
        assert "dependency_failure" in prompt
    
    def test_create_prompt_with_similar_incidents(self):
        """Test prompt creation with similar incidents from Knowledge Base"""
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        similar_incidents = [
            {
                "incident_id": "inc-2024-11-23-001",
                "similarity_score": 0.78,
                "resolution": "Increased timeout threshold to 30s",
                "root_cause": "Payment gateway timeout"
            },
            {
                "incident_id": "inc-2024-10-15-002",
                "similarity_score": 0.65,
                "resolution": {"action": "Added circuit breaker pattern"},
                "root_cause": {"category": "dependency_failure", "description": "External API timeout"}
            }
        ]
        
        prompt = analyzer.create_prompt(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        
        # Verify similar incidents are included
        assert "Similar Past Incidents" in prompt
        assert "inc-2024-11-23-001" in prompt
        assert "78%" in prompt
        assert "Increased timeout threshold to 30s" in prompt
        assert "inc-2024-10-15-002" in prompt
        assert "65%" in prompt
        assert "Added circuit breaker pattern" in prompt
        assert "semantic search" in prompt
    
    def test_create_prompt_empty_log_summary(self):
        """Test prompt creation with empty log summary"""
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        prompt = analyzer.create_prompt(
            service_name="test-service",
            error_message="Unknown error",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify prompt handles empty data gracefully
        assert "test-service" in prompt
        assert "Unknown error" in prompt
        assert "None detected" in prompt or "None found" in prompt or "None available" in prompt
    
    def test_create_prompt_limits_similar_incidents(self):
        """Test that prompt limits similar incidents to top 5"""
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {"error_patterns": [], "stack_traces": [], "relevant_excerpts": []}
        
        # Create 10 similar incidents
        similar_incidents = [
            {
                "incident_id": f"inc-{i}",
                "similarity_score": 0.9 - (i * 0.05),
                "resolution": f"Resolution {i}",
                "root_cause": f"Cause {i}"
            }
            for i in range(10)
        ]
        
        prompt = analyzer.create_prompt(
            service_name="test-service",
            error_message="Error",
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        
        # Verify only top 5 are included
        assert "inc-0" in prompt
        assert "inc-4" in prompt
        assert "inc-5" not in prompt
        assert "inc-9" not in prompt


class TestBedrockClaudeInvocation:
    """Test Claude model invocation"""
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_invoke_claude_success(self, mock_boto_client):
        """Test successful Claude invocation with valid JSON response"""
        # Mock Bedrock Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        
        claude_response = {
            "content": [
                {
                    "text": json.dumps({
                        "primary_cause": {
                            "category": "dependency_failure",
                            "description": "External payment gateway timeout",
                            "confidence_score": 85,
                            "evidence": [
                                "15 consecutive connection timeouts",
                                "No similar issues in past 30 days"
                            ]
                        },
                        "alternative_causes": [
                            {
                                "category": "resource_exhaustion",
                                "description": "Network bandwidth saturation",
                                "confidence_score": 35,
                                "evidence": ["High request volume"]
                            }
                        ]
                    })
                }
            ]
        }
        
        mock_response['body'].read.return_value = json.dumps(claude_response).encode('utf-8')
        mock_client.invoke_model.return_value = mock_response
        
        # Test invocation
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        result = analyzer.invoke_claude(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify result structure
        assert "primary_cause" in result
        assert result["primary_cause"]["category"] == "dependency_failure"
        assert result["primary_cause"]["confidence_score"] == 85
        assert len(result["primary_cause"]["evidence"]) == 2
        assert "alternative_causes" in result
        assert len(result["alternative_causes"]) == 1
        
        # Verify Bedrock was called correctly
        mock_client.invoke_model.assert_called_once()
        call_args = mock_client.invoke_model.call_args
        assert call_args[1]["modelId"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"
        assert call_args[1]["contentType"] == "application/json"
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_invoke_claude_invalid_json_fallback(self, mock_boto_client):
        """Test fallback to rule-based classification when Claude returns invalid JSON"""
        # Mock Bedrock Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock response with invalid JSON
        mock_response = {
            'body': Mock()
        }
        
        claude_response = {
            "content": [
                {
                    "text": "This is not valid JSON, just plain text analysis"
                }
            ]
        }
        
        mock_response['body'].read.return_value = json.dumps(claude_response).encode('utf-8')
        mock_client.invoke_model.return_value = mock_response
        
        # Test invocation
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        result = analyzer.invoke_claude(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify fallback classification was used
        assert "primary_cause" in result
        assert result["primary_cause"]["category"] in ["configuration_error", "resource_exhaustion", "dependency_failure"]
        assert 0 <= result["primary_cause"]["confidence_score"] <= 100
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_invoke_claude_with_similar_incidents(self, mock_boto_client):
        """Test Claude invocation with similar incidents in prompt"""
        # Mock Bedrock Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        
        claude_response = {
            "content": [
                {
                    "text": json.dumps({
                        "primary_cause": {
                            "category": "dependency_failure",
                            "description": "Payment gateway timeout (similar to past incident inc-001)",
                            "confidence_score": 90,
                            "evidence": ["Historical pattern match", "15 timeouts"]
                        },
                        "alternative_causes": []
                    })
                }
            ]
        }
        
        mock_response['body'].read.return_value = json.dumps(claude_response).encode('utf-8')
        mock_client.invoke_model.return_value = mock_response
        
        # Test invocation
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        similar_incidents = [
            {
                "incident_id": "inc-001",
                "similarity_score": 0.85,
                "resolution": "Increased timeout to 30s",
                "root_cause": "Gateway timeout"
            }
        ]
        
        result = analyzer.invoke_claude(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        
        # Verify result
        assert result["primary_cause"]["confidence_score"] == 90
        
        # Verify prompt included similar incidents
        call_args = mock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]["body"])
        prompt = request_body["messages"][0]["content"]
        assert "Similar Past Incidents" in prompt
        assert "inc-001" in prompt


class TestResponseValidation:
    """Test response validation and normalization"""
    
    def test_validate_valid_response(self):
        """Test validation of valid response"""
        analyzer = BedrockRootCauseAnalyzer()
        
        response = {
            "primary_cause": {
                "category": "dependency_failure",
                "description": "External API timeout",
                "confidence_score": 85,
                "evidence": ["Timeout pattern", "Network logs"]
            },
            "alternative_causes": [
                {
                    "category": "resource_exhaustion",
                    "description": "High CPU usage",
                    "confidence_score": 40,
                    "evidence": ["CPU metrics"]
                }
            ]
        }
        
        validated = analyzer._validate_and_normalize_response(response)
        
        assert validated["primary_cause"]["category"] == "dependency_failure"
        assert validated["primary_cause"]["confidence_score"] == 85
        assert len(validated["alternative_causes"]) == 1
    
    def test_validate_confidence_score_bounds(self):
        """Test that confidence scores are bounded to [0, 100]"""
        analyzer = BedrockRootCauseAnalyzer()
        
        response = {
            "primary_cause": {
                "category": "dependency_failure",
                "description": "Test",
                "confidence_score": 150,  # Invalid: > 100
                "evidence": []
            },
            "alternative_causes": [
                {
                    "category": "resource_exhaustion",
                    "description": "Test",
                    "confidence_score": -10,  # Invalid: < 0
                    "evidence": []
                }
            ]
        }
        
        validated = analyzer._validate_and_normalize_response(response)
        
        # Verify bounds are enforced
        assert validated["primary_cause"]["confidence_score"] == 100
        assert validated["alternative_causes"][0]["confidence_score"] == 0
    
    def test_validate_invalid_category(self):
        """Test handling of invalid category"""
        analyzer = BedrockRootCauseAnalyzer()
        
        response = {
            "primary_cause": {
                "category": "invalid_category",  # Invalid
                "description": "Test",
                "confidence_score": 85,
                "evidence": []
            },
            "alternative_causes": []
        }
        
        validated = analyzer._validate_and_normalize_response(response)
        
        # Should default to dependency_failure
        assert validated["primary_cause"]["category"] == "dependency_failure"
    
    def test_validate_missing_fields(self):
        """Test handling of missing fields"""
        analyzer = BedrockRootCauseAnalyzer()
        
        response = {
            "primary_cause": {
                "category": "dependency_failure"
                # Missing: description, confidence_score, evidence
            },
            # Missing: alternative_causes
        }
        
        validated = analyzer._validate_and_normalize_response(response)
        
        # Verify defaults are added
        assert "description" in validated["primary_cause"]
        assert validated["primary_cause"]["confidence_score"] == 50  # Default
        assert validated["primary_cause"]["evidence"] == []
        assert validated["alternative_causes"] == []


class TestBedrockAnalysisEndToEnd:
    """Test complete Bedrock analysis workflow"""
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_analyze_with_bedrock_success(self, mock_boto_client):
        """Test complete analysis workflow with successful Bedrock response"""
        # Mock Bedrock Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        
        claude_response = {
            "content": [
                {
                    "text": json.dumps({
                        "primary_cause": {
                            "category": "dependency_failure",
                            "description": "External payment gateway timeout",
                            "confidence_score": 85,
                            "evidence": ["15 consecutive timeouts", "Gateway health check failed"]
                        },
                        "alternative_causes": [
                            {
                                "category": "resource_exhaustion",
                                "description": "Network bandwidth saturation",
                                "confidence_score": 35,
                                "evidence": ["High request volume"]
                            }
                        ]
                    })
                }
            ]
        }
        
        mock_response['body'].read.return_value = json.dumps(claude_response).encode('utf-8')
        mock_client.invoke_model.return_value = mock_response
        
        # Test complete analysis
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": ["ERROR: Connection timeout"]
        }
        
        similar_incidents = [
            {
                "incident_id": "inc-2024-11-23-001",
                "similarity_score": 0.78,
                "resolution": "Increased timeout to 30s",
                "root_cause": "Gateway timeout"
            }
        ]
        
        result = analyzer.analyze_with_bedrock(
            service_name="payment-processor",
            error_message="Connection timeout to payment-gateway.example.com",
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        
        # Verify complete result structure
        assert "primary_cause" in result
        assert result["primary_cause"]["category"] == "dependency_failure"
        assert result["primary_cause"]["confidence_score"] == 85
        assert "alternative_causes" in result
        assert "similar_incidents" in result
        assert len(result["similar_incidents"]) == 1
        assert result["similar_incidents"][0]["incident_id"] == "inc-2024-11-23-001"
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_analyze_with_bedrock_fallback_on_error(self, mock_boto_client):
        """Test fallback to rule-based classification when Bedrock fails"""
        # Mock Bedrock Runtime client that raises an exception
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("Bedrock API timeout")
        
        # Test analysis with error
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        result = analyzer.analyze_with_bedrock(
            service_name="payment-processor",
            error_message="Connection timeout",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify fallback classification was used
        assert "primary_cause" in result
        assert result["primary_cause"]["category"] in ["configuration_error", "resource_exhaustion", "dependency_failure"]
        assert 0 <= result["primary_cause"]["confidence_score"] <= 100
        assert "alternative_causes" in result
    
    @patch('src.agents.root_cause_classifier.boto3.client')
    def test_analyze_with_bedrock_no_similar_incidents(self, mock_boto_client):
        """Test analysis without similar incidents"""
        # Mock Bedrock Runtime client
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Mock successful response
        mock_response = {
            'body': Mock()
        }
        
        claude_response = {
            "content": [
                {
                    "text": json.dumps({
                        "primary_cause": {
                            "category": "configuration_error",
                            "description": "Missing environment variable",
                            "confidence_score": 75,
                            "evidence": ["DATABASE_URL not set"]
                        },
                        "alternative_causes": []
                    })
                }
            ]
        }
        
        mock_response['body'].read.return_value = json.dumps(claude_response).encode('utf-8')
        mock_client.invoke_model.return_value = mock_response
        
        # Test analysis
        analyzer = BedrockRootCauseAnalyzer()
        
        log_summary = {
            "error_patterns": [{"pattern": "EnvironmentVariableError"}],
            "stack_traces": [],
            "relevant_excerpts": []
        }
        
        result = analyzer.analyze_with_bedrock(
            service_name="test-service",
            error_message="Missing DATABASE_URL",
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Verify result
        assert result["primary_cause"]["category"] == "configuration_error"
        assert result["similar_incidents"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
