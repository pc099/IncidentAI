"""
Unit Tests for AWS-Specific Fix Recommendations

Tests AWS-specific fix recommendations for common services:
- Lambda: deployment package size, IAM permissions, timeout, concurrency
- DynamoDB: throttling, auto-scaling, on-demand billing, exponential backoff
- RDS: storage full, auto-scaling, archival strategies
- API Gateway: timeout configuration, async processing, circuit breaker

Validates: Requirements 4.3, 4.4, 4.5
"""

import pytest
from src.agents.fix_recommendation_agent import FixRecommendationAgent


class TestLambdaDeploymentFailureFixes:
    """Test Lambda deployment failure fix recommendations."""
    
    def test_lambda_deployment_package_size_fix(self):
        """Test fix recommendations for Lambda deployment package size issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "configuration_error",
                "description": "Lambda deployment failed due to package size exceeding limit",
                "confidence_score": 85,
                "evidence": [
                    "Deployment package size exceeds 50MB limit",
                    "Code storage limit reached"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="payment-processor"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        assert len(immediate_actions) >= 2, "Should have at least 2 actions"
        
        # Check for deployment-related actions
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        assert any(keyword in action_texts for keyword in ["package", "deployment", "size"]), \
            "Should include deployment package size related actions"
    
    def test_lambda_iam_permissions_fix(self):
        """Test fix recommendations for Lambda IAM permission issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "configuration_error",
                "description": "Lambda function lacks necessary IAM permissions",
                "confidence_score": 90,
                "evidence": [
                    "Access denied error when accessing S3",
                    "IAM permission error in logs"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="data-processor"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert any(keyword in action_texts for keyword in ["iam", "permission", "role"]), \
            "Should include IAM permission related actions"
    
    def test_lambda_timeout_fix(self):
        """Test fix recommendations for Lambda timeout issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "Lambda function timed out after 3 seconds",
                "confidence_score": 88,
                "evidence": [
                    "Task timed out after 3.00 seconds",
                    "Function execution exceeded timeout"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="api-handler"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert "timeout" in action_texts, "Should include timeout related actions"
    
    def test_lambda_concurrency_fix(self):
        """Test fix recommendations for Lambda concurrency limit issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "Lambda concurrent execution limit exceeded",
                "confidence_score": 92,
                "evidence": [
                    "Rate exceeded error",
                    "Concurrent execution limit reached"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="event-processor"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert any(keyword in action_texts for keyword in ["concurrency", "concurrent", "throttling"]), \
            "Should include concurrency related actions"


class TestDynamoDBThrottlingFixes:
    """Test DynamoDB throttling fix recommendations."""
    
    def test_dynamodb_throttling_fix(self):
        """Test fix recommendations for DynamoDB throttling issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "DynamoDB table experiencing throttling due to exceeded capacity",
                "confidence_score": 95,
                "evidence": [
                    "ProvisionedThroughputExceededException",
                    "Read capacity units exceeded"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="user-data-table"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert any(keyword in action_texts for keyword in ["throttling", "capacity", "dynamodb"]), \
            "Should include DynamoDB throttling related actions"
    
    def test_dynamodb_auto_scaling_recommendation(self):
        """Test that DynamoDB fixes include auto-scaling recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "DynamoDB throttling detected",
                "confidence_score": 90,
                "evidence": ["Throttling exception in logs"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="orders-table"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        # Should mention auto-scaling or on-demand as solutions
        assert any(keyword in action_texts for keyword in ["auto-scaling", "on-demand", "scaling"]), \
            "Should include auto-scaling or on-demand billing recommendations"
    
    def test_dynamodb_exponential_backoff_recommendation(self):
        """Test that DynamoDB fixes include exponential backoff recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "DynamoDB throttling",
                "confidence_score": 85,
                "evidence": ["ProvisionedThroughputExceededException"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="sessions-table"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        # Should mention retry or backoff
        assert any(keyword in action_texts for keyword in ["retry", "backoff", "exponential"]), \
            "Should include exponential backoff recommendations"


class TestRDSStorageFullFixes:
    """Test RDS storage full fix recommendations."""
    
    def test_rds_storage_full_fix(self):
        """Test fix recommendations for RDS storage full issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "RDS database storage is full",
                "confidence_score": 98,
                "evidence": [
                    "Disk full error",
                    "Storage capacity at 100%"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="production-db"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert any(keyword in action_texts for keyword in ["storage", "disk", "space"]), \
            "Should include storage related actions"
    
    def test_rds_auto_scaling_recommendation(self):
        """Test that RDS fixes include auto-scaling recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "RDS storage full",
                "confidence_score": 95,
                "evidence": ["Storage at capacity"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="analytics-db"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        assert any(keyword in action_texts for keyword in ["auto-scaling", "scaling", "increase"]), \
            "Should include storage auto-scaling recommendations"
    
    def test_rds_archival_strategy_recommendation(self):
        """Test that RDS fixes include archival strategy recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "resource_exhaustion",
                "description": "RDS storage full",
                "confidence_score": 90,
                "evidence": ["Disk space exhausted"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="logs-db"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        # Should mention archival or cleanup
        assert any(keyword in action_texts for keyword in ["archiv", "delete", "cleanup", "data"]), \
            "Should include data archival or cleanup recommendations"


class TestAPIGatewayTimeoutFixes:
    """Test API Gateway timeout fix recommendations."""
    
    def test_api_gateway_timeout_fix(self):
        """Test fix recommendations for API Gateway timeout issues."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "dependency_failure",
                "description": "API Gateway integration timeout after 29 seconds",
                "confidence_score": 93,
                "evidence": [
                    "Endpoint request timed out",
                    "Integration timeout error"
                ]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="public-api"
        )
        
        # Assert
        immediate_actions = result["recommendations"]["immediate_actions"]
        action_texts = " ".join([a["action"] + " " + a.get("details", "") for a in immediate_actions]).lower()
        
        assert "timeout" in action_texts, "Should include timeout related actions"
    
    def test_api_gateway_async_processing_recommendation(self):
        """Test that API Gateway fixes include async processing recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "dependency_failure",
                "description": "API Gateway timeout",
                "confidence_score": 88,
                "evidence": ["Integration timeout"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="rest-api"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        # Should mention async or asynchronous processing
        assert any(keyword in action_texts for keyword in ["async", "asynchronous", "queue", "sqs"]), \
            "Should include async processing recommendations"
    
    def test_api_gateway_circuit_breaker_recommendation(self):
        """Test that API Gateway fixes include circuit breaker recommendations."""
        # Arrange
        agent = FixRecommendationAgent()
        root_cause = {
            "primary_cause": {
                "category": "dependency_failure",
                "description": "API Gateway timeout",
                "confidence_score": 85,
                "evidence": ["Timeout error"]
            }
        }
        
        # Act
        result = agent.generate_recommendations(
            root_cause=root_cause,
            service_name="gateway-api"
        )
        
        # Assert
        action_texts = " ".join([
            a["action"] + " " + a.get("details", "")
            for a in result["recommendations"]["immediate_actions"]
        ]).lower()
        
        # Should mention circuit breaker
        assert "circuit breaker" in action_texts, \
            "Should include circuit breaker recommendations"


class TestGeneralFixRecommendations:
    """Test general fix recommendation properties."""
    
    def test_all_aws_fixes_have_commands(self):
        """Test that AWS-specific fixes include executable commands."""
        # Arrange
        agent = FixRecommendationAgent()
        
        test_cases = [
            {
                "category": "configuration_error",
                "description": "Lambda deployment package size exceeded",
                "evidence": ["Package size too large"]
            },
            {
                "category": "resource_exhaustion",
                "description": "DynamoDB throttling",
                "evidence": ["ProvisionedThroughputExceededException"]
            },
            {
                "category": "resource_exhaustion",
                "description": "RDS storage full",
                "evidence": ["Disk full"]
            }
        ]
        
        for test_case in test_cases:
            root_cause = {
                "primary_cause": {
                    "category": test_case["category"],
                    "description": test_case["description"],
                    "confidence_score": 85,
                    "evidence": test_case["evidence"]
                }
            }
            
            # Act
            result = agent.generate_recommendations(
                root_cause=root_cause,
                service_name="test-service"
            )
            
            # Assert
            immediate_actions = result["recommendations"]["immediate_actions"]
            commands = [a.get("command") for a in immediate_actions if a.get("command")]
            
            # At least some actions should have commands
            assert len(commands) > 0, \
                f"AWS-specific fixes for {test_case['description']} should include executable commands"
    
    def test_fix_recommendations_include_rollback_plan(self):
        """Test that all fix recommendations include a rollback plan."""
        # Arrange
        agent = FixRecommendationAgent()
        
        categories = ["configuration_error", "resource_exhaustion", "dependency_failure"]
        
        for category in categories:
            root_cause = {
                "primary_cause": {
                    "category": category,
                    "description": f"Test {category}",
                    "confidence_score": 80,
                    "evidence": ["Test evidence"]
                }
            }
            
            # Act
            result = agent.generate_recommendations(
                root_cause=root_cause,
                service_name="test-service"
            )
            
            # Assert
            assert "rollback_plan" in result["recommendations"], \
                f"Category {category} must have a rollback plan"
            assert len(result["recommendations"]["rollback_plan"]) > 0, \
                f"Rollback plan for {category} must not be empty"
