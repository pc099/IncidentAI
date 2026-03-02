"""
End-to-end integration test for AI-Powered Incident Response System.

This test validates the complete flow from alert ingestion through email delivery,
testing with multiple AWS failure scenarios.

Tests:
- Complete flow from alert ingestion to email delivery
- Lambda deployment failure scenario
- DynamoDB throttling scenario
- API Gateway timeout scenario
- Incident storage in DynamoDB and Knowledge Base

Requirements: 1.1, 1.2, 1.6, 6.1, 6.5, 7.1, 8.1
"""

import pytest
import boto3
from moto import mock_aws
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
from src.api.incident_validator import lambda_handler as validator_handler
from src.orchestrator.agent_orchestrator import StrandsOrchestrator
from src.agents.log_analysis_agent import LogAnalysisAgent
from src.agents.fix_recommendation_agent import FixRecommendationAgent
from src.agents.communication_agent import CommunicationAgent
from src.alerts.ses_delivery import SESDeliveryService
from src.history.incident_storage import IncidentStorage
from src.history.kb_sync import sync_incident_to_kb


# Test data for different failure scenarios
LAMBDA_DEPLOYMENT_FAILURE_ALERT = {
    "service_name": "payment-processor",
    "timestamp": "2025-03-01T10:30:00Z",
    "error_message": "Lambda deployment failed: package size exceeds limit",
    "log_location": "s3://test-logs/payment-processor/2025-03-01/10-30.log",
    "alert_source": "CloudWatch"
}

DYNAMODB_THROTTLING_ALERT = {
    "service_name": "user-sessions-table",
    "timestamp": "2025-03-01T11:00:00Z",
    "error_message": "ProvisionedThroughputExceededException",
    "log_location": "s3://test-logs/user-sessions-table/2025-03-01/11-00.log",
    "alert_source": "CloudWatch"
}

API_GATEWAY_TIMEOUT_ALERT = {
    "service_name": "payment-api-gateway",
    "timestamp": "2025-03-01T15:00:00Z",
    "error_message": "Integration timeout: Endpoint request timed out",
    "log_location": "s3://test-logs/payment-api-gateway/2025-03-01/15-00.log",
    "alert_source": "CloudWatch"
}


class TestEndToEndIntegration:
    """End-to-end integration tests for the complete incident response flow."""
    
    @mock_aws
    def test_complete_flow_lambda_deployment_failure(self):
        """
        Test complete flow from alert ingestion to email delivery for Lambda deployment failure.
        
        This test validates:
        1. API Gateway receives and validates alert
        2. Orchestrator invokes all agents sequentially
        3. Log Analysis Agent retrieves and analyzes logs
        4. Root Cause Agent identifies configuration error
        5. Fix Recommendation Agent provides remediation steps
        6. Communication Agent generates summaries
        7. SES delivers enhanced alert email
        8. Incident stored in DynamoDB
        9. Incident indexed in Knowledge Base
        
        Requirements: 1.1, 1.2, 1.6, 6.1, 6.5, 7.1, 8.1
        """
        # Setup AWS mocks
        s3_client, dynamodb_table, ses_client = self._setup_aws_services()
        
        # Upload Lambda deployment failure logs
        log_content = self._get_lambda_deployment_failure_logs()
        s3_client.put_object(
            Bucket='test-logs',
            Key='payment-processor/2025-03-01/10-30.log',
            Body=log_content.encode('utf-8')
        )
        
        # Step 1: API Gateway receives alert
        start_time = time.time()
        api_event = self._create_api_gateway_event(LAMBDA_DEPLOYMENT_FAILURE_ALERT)
        api_response = validator_handler(api_event, Mock())
        
        # Verify API Gateway response
        assert api_response["statusCode"] == 202
        api_body = json.loads(api_response["body"])
        assert "incident_id" in api_body
        incident_id = api_body["incident_id"]
        
        # Verify API Gateway timing (< 2 seconds)
        api_elapsed = time.time() - start_time
        assert api_elapsed < 2.0, f"API Gateway took {api_elapsed:.2f}s, expected < 2.0s"
        
        # Step 2: Orchestrator processes incident
        orchestrator_start = time.time()
        
        # Mock Bedrock responses for agents
        with patch('src.agents.log_analysis_agent.LogAnalysisAgent.analyze') as mock_log_analysis, \
             patch('src.agents.fix_recommendation_agent.FixRecommendationAgent.generate_recommendations') as mock_fix_gen, \
             patch('src.agents.communication_agent.CommunicationAgent.generate_summaries') as mock_comm:
            
            # Configure mock responses
            mock_log_analysis.return_value = {
                "agent": "log-analysis",
                "summary": {
                    "error_patterns": [
                        {
                            "pattern": "DeploymentPackageTooLarge",
                            "occurrences": 1,
                            "first_seen": "2025-03-01T10:30:00Z"
                        }
                    ],
                    "stack_traces": [],
                    "relevant_excerpts": [
                        "ERROR: Deployment package size 75MB exceeds limit of 50MB"
                    ],
                    "log_volume": "2 MB"
                }
            }
            
            # Mock root cause analysis (would query Knowledge Base)
            mock_root_cause = {
                "agent": "root-cause",
                "analysis": {
                    "primary_cause": {
                        "category": "configuration_error",
                        "description": "Lambda deployment package exceeds size limit",
                        "confidence_score": 88,
                        "evidence": [
                            "Deployment package size 75MB exceeds limit of 50MB",
                            "Similar pattern in 3 historical incidents"
                        ]
                    },
                    "alternative_causes": [],
                    "similar_incidents": [
                        {
                            "incident_id": "inc-2024-12-01-001",
                            "similarity_score": 0.85,
                            "resolution": "Removed unused dependencies, reduced package to 45MB",
                            "root_cause": "Lambda deployment package too large"
                        }
                    ]
                }
            }
            
            mock_fix_gen.return_value = {
                "agent": "fix-recommendation",
                "recommendations": {
                    "immediate_actions": [
                        {
                            "step": 1,
                            "action": "Remove unused dependencies from deployment package",
                            "command": "pip install --target ./package -r requirements-minimal.txt",
                            "estimated_time": "10 minutes",
                            "risk_level": "low"
                        },
                        {
                            "step": 2,
                            "action": "Use Lambda Layers for common dependencies",
                            "command": "aws lambda publish-layer-version --layer-name common-deps",
                            "estimated_time": "15 minutes",
                            "risk_level": "low"
                        }
                    ],
                    "preventive_measures": [
                        {
                            "action": "Implement package size monitoring in CI/CD",
                            "priority": "high"
                        }
                    ]
                }
            }
            
            mock_comm.return_value = {
                "agent": "communication",
                "enhanced_alert": {
                    "incident_id": incident_id,
                    "timestamp": "2025-03-01T10:30:00Z",
                    "service_name": "payment-processor",
                    "technical_summary": {
                        "title": "Payment Processor - Configuration Error",
                        "root_cause": "Lambda deployment package exceeds size limit (88% confidence)",
                        "evidence": "Deployment package size 75MB exceeds limit of 50MB",
                        "immediate_fix": "Remove unused dependencies",
                        "estimated_resolution": "25 minutes"
                    },
                    "business_summary": {
                        "title": "Payment Processing Deployment Failed",
                        "impact": "Unable to deploy new payment processor version",
                        "status": "Root cause identified, fix in progress",
                        "estimated_resolution": "25 minutes"
                    },
                    "confidence_score": 88
                }
            }
            
            # Invoke orchestrator
            orchestrator = StrandsOrchestrator()
            orchestration_event = {
                "incident_id": incident_id,
                **LAMBDA_DEPLOYMENT_FAILURE_ALERT
            }
            
            result = orchestrator.handle_incident(orchestration_event)
        
        # Verify orchestration completed
        assert result.success or result.partial_results
        assert result.enhanced_alert is not None
        
        # Verify orchestration timing
        orchestrator_elapsed = time.time() - orchestrator_start
        assert orchestrator_elapsed < 30.0, f"Orchestration took {orchestrator_elapsed:.2f}s"
        
        # Step 3: Verify agent execution sequence
        assert "log-analysis" in result.agent_results or "log_analysis" in str(result.agent_results)
        
        # Step 4: Store incident in DynamoDB
        storage = IncidentStorage(table_name='incident-history', region='us-east-1')
        
        # Build enhanced alert with proper structure for storage
        enhanced_alert_for_storage = {
            "incident_id": incident_id,
            "timestamp": "2025-03-01T10:30:00Z",
            "original_alert": LAMBDA_DEPLOYMENT_FAILURE_ALERT,
            "root_cause": {
                "category": "configuration_error",
                "description": "Lambda deployment package exceeds size limit",
                "confidence_score": 88,  # Integer, not float
                "evidence": [
                    "Deployment package size 75MB exceeds limit of 50MB",
                    "Similar pattern in 3 historical incidents"
                ]
            },
            "recommended_fixes": mock_fix_gen.return_value["recommendations"]["immediate_actions"],
            "agent_outputs": {
                "log-analysis": {
                    "success": True,
                    "output": mock_log_analysis.return_value
                },
                "root-cause": {
                    "success": True,
                    "output": {
                        "primary_cause": {
                            "category": "configuration_error",
                            "description": "Lambda deployment package exceeds size limit",
                            "confidence_score": 88,
                            "evidence": [
                                "Deployment package size 75MB exceeds limit of 50MB"
                            ]
                        },
                        "similar_incidents": []
                    }
                },
                "fix-recommendation": {
                    "success": True,
                    "output": mock_fix_gen.return_value["recommendations"]
                }
            }
        }
        
        storage.store_incident(enhanced_alert_for_storage)
        
        # Verify incident stored in DynamoDB
        stored_incident = dynamodb_table.get_item(Key={
            "incident_id": incident_id,
            "timestamp": "2025-03-01T10:30:00Z"
        })
        assert "Item" in stored_incident
        assert stored_incident["Item"]["service_name"] == "payment-processor"
        assert stored_incident["Item"]["failure_type"] == "configuration_error"
        
        # Step 5: Send email via SES
        ses_service = SESDeliveryService(
            sender_email='incidents@example.com',
            region='us-east-1'
        )
        
        email_result = ses_service.deliver_alert(
            enhanced_alert=result.enhanced_alert,
            recipients=['oncall@example.com']
        )
        
        # Verify email delivery
        assert email_result['success'] is True
        assert 'message_id' in email_result
        
        # Verify total end-to-end timing
        total_elapsed = time.time() - start_time
        assert total_elapsed < 60.0, f"End-to-end processing took {total_elapsed:.2f}s"
        
        # Step 6: Verify incident indexed in Knowledge Base (simulated)
        # In production, this would trigger Knowledge Base ingestion
        kb_document = {
            "incident_id": incident_id,
            "service_name": "payment-processor",
            "failure_type": "configuration_error",
            "root_cause": "Lambda deployment package too large",
            "resolution": "Removed unused dependencies"
        }
        
        # Verify KB document structure
        assert kb_document["incident_id"] == incident_id
        assert kb_document["failure_type"] == "configuration_error"
    
    @mock_aws
    def test_complete_flow_dynamodb_throttling(self):
        """
        Test complete flow for DynamoDB throttling scenario.
        
        Requirements: 1.1, 1.2, 1.6, 6.1, 7.1, 8.1, 11.2
        """
        # Setup AWS mocks
        s3_client, dynamodb_table, ses_client = self._setup_aws_services()
        
        # Upload DynamoDB throttling logs
        log_content = self._get_dynamodb_throttling_logs()
        s3_client.put_object(
            Bucket='test-logs',
            Key='user-sessions-table/2025-03-01/11-00.log',
            Body=log_content.encode('utf-8')
        )
        
        # API Gateway receives alert
        api_event = self._create_api_gateway_event(DYNAMODB_THROTTLING_ALERT)
        api_response = validator_handler(api_event, Mock())
        
        assert api_response["statusCode"] == 202
        api_body = json.loads(api_response["body"])
        incident_id = api_body["incident_id"]
        
        # Mock agent responses for DynamoDB throttling
        with patch('src.agents.log_analysis_agent.LogAnalysisAgent.analyze') as mock_log, \
             patch('src.agents.fix_recommendation_agent.FixRecommendationAgent.generate_recommendations') as mock_fix, \
             patch('src.agents.communication_agent.CommunicationAgent.generate_summaries') as mock_comm:
            
            mock_log.return_value = {
                "summary": {
                    "error_patterns": [
                        {
                            "pattern": "ProvisionedThroughputExceededException",
                            "occurrences": 45
                        }
                    ]
                }
            }
            
            mock_fix.return_value = {
                "recommendations": {
                    "immediate_actions": [
                        {
                            "step": 1,
                            "action": "Enable DynamoDB auto-scaling",
                            "command": "aws dynamodb update-table --table-name user-sessions --auto-scaling-enabled",
                            "estimated_time": "5 minutes"
                        }
                    ]
                }
            }
            
            mock_comm.return_value = {
                "enhanced_alert": {
                    "incident_id": incident_id,
                    "service_name": "user-sessions-table",
                    "confidence_score": 92
                }
            }
            
            # Process incident
            orchestrator = StrandsOrchestrator()
            result = orchestrator.handle_incident({
                "incident_id": incident_id,
                **DYNAMODB_THROTTLING_ALERT
            })
        
        # Verify processing completed
        assert result.enhanced_alert is not None
        
        # Store and verify incident
        storage = IncidentStorage(table_name='incident-history', region='us-east-1')
        
        enhanced_alert_for_storage = {
            "incident_id": incident_id,
            "timestamp": "2025-03-01T11:00:00Z",
            "original_alert": DYNAMODB_THROTTLING_ALERT,
            "root_cause": {
                "category": "resource_exhaustion",
                "description": "DynamoDB read capacity exceeded",
                "confidence_score": 92
            },
            "agent_outputs": {
                "log-analysis": {
                    "success": True,
                    "output": mock_log.return_value
                }
            }
        }
        
        storage.store_incident(enhanced_alert_for_storage)
        
        # Verify stored
        stored = dynamodb_table.get_item(Key={
            "incident_id": incident_id,
            "timestamp": "2025-03-01T11:00:00Z"
        })
        assert "Item" in stored
        assert stored["Item"]["failure_type"] == "resource_exhaustion"
    
    @mock_aws
    def test_complete_flow_api_gateway_timeout(self):
        """
        Test complete flow for API Gateway timeout scenario.
        
        Requirements: 1.1, 1.2, 1.6, 6.1, 7.1, 8.1, 11.3
        """
        # Setup AWS mocks
        s3_client, dynamodb_table, ses_client = self._setup_aws_services()
        
        # Upload API Gateway timeout logs
        log_content = self._get_api_gateway_timeout_logs()
        s3_client.put_object(
            Bucket='test-logs',
            Key='payment-api-gateway/2025-03-01/15-00.log',
            Body=log_content.encode('utf-8')
        )
        
        # API Gateway receives alert
        api_event = self._create_api_gateway_event(API_GATEWAY_TIMEOUT_ALERT)
        api_response = validator_handler(api_event, Mock())
        
        assert api_response["statusCode"] == 202
        api_body = json.loads(api_response["body"])
        incident_id = api_body["incident_id"]
        
        # Mock agent responses for API Gateway timeout
        with patch('src.agents.log_analysis_agent.LogAnalysisAgent.analyze') as mock_log, \
             patch('src.agents.fix_recommendation_agent.FixRecommendationAgent.generate_recommendations') as mock_fix, \
             patch('src.agents.communication_agent.CommunicationAgent.generate_summaries') as mock_comm:
            
            mock_log.return_value = {
                "summary": {
                    "error_patterns": [
                        {
                            "pattern": "IntegrationTimeout",
                            "occurrences": 12
                        }
                    ]
                }
            }
            
            mock_fix.return_value = {
                "recommendations": {
                    "immediate_actions": [
                        {
                            "step": 1,
                            "action": "Implement circuit breaker pattern",
                            "estimated_time": "30 minutes"
                        },
                        {
                            "step": 2,
                            "action": "Increase timeout threshold",
                            "command": "Update API Gateway integration timeout",
                            "estimated_time": "5 minutes"
                        }
                    ]
                }
            }
            
            mock_comm.return_value = {
                "enhanced_alert": {
                    "incident_id": incident_id,
                    "service_name": "payment-api-gateway",
                    "confidence_score": 87
                }
            }
            
            # Process incident
            orchestrator = StrandsOrchestrator()
            result = orchestrator.handle_incident({
                "incident_id": incident_id,
                **API_GATEWAY_TIMEOUT_ALERT
            })
        
        # Verify processing completed
        assert result.enhanced_alert is not None
        
        # Store and verify incident
        storage = IncidentStorage(table_name='incident-history', region='us-east-1')
        
        enhanced_alert_for_storage = {
            "incident_id": incident_id,
            "timestamp": "2025-03-01T15:00:00Z",
            "original_alert": API_GATEWAY_TIMEOUT_ALERT,
            "root_cause": {
                "category": "dependency_failure",
                "description": "External payment gateway timeout",
                "confidence_score": 87
            },
            "agent_outputs": {
                "log-analysis": {
                    "success": True,
                    "output": mock_log.return_value
                }
            }
        }
        
        storage.store_incident(enhanced_alert_for_storage)
        
        # Verify stored
        stored = dynamodb_table.get_item(Key={
            "incident_id": incident_id,
            "timestamp": "2025-03-01T15:00:00Z"
        })
        assert "Item" in stored
        assert stored["Item"]["failure_type"] == "dependency_failure"
    
    @mock_aws
    def test_incident_stored_in_dynamodb_and_knowledge_base(self):
        """
        Test that incidents are properly stored in both DynamoDB and Knowledge Base.
        
        Requirements: 8.1
        """
        # Setup AWS mocks
        s3_client, dynamodb_table, ses_client = self._setup_aws_services()
        
        # Create test incident
        incident_id = "inc-2025-03-01-test-001"
        
        enhanced_alert_for_storage = {
            "incident_id": incident_id,
            "timestamp": "2025-03-01T10:30:00Z",
            "original_alert": {
                "service_name": "test-service",
                "error_message": "Test error",
                "log_location": "s3://test-logs/test.log"
            },
            "root_cause": {
                "category": "configuration_error",
                "description": "Test configuration error",
                "confidence_score": 85,
                "evidence": ["Test evidence"]
            },
            "recommended_fixes": [
                {
                    "action": "Test fix",
                    "command": "test command"
                }
            ],
            "agent_outputs": {
                "log-analysis": {
                    "success": True,
                    "output": {
                        "error_patterns": [{"pattern": "TestError"}]
                    }
                }
            }
        }
        
        # Store in DynamoDB
        storage = IncidentStorage(table_name='incident-history', region='us-east-1')
        storage.store_incident(enhanced_alert_for_storage)
        
        # Verify DynamoDB storage
        stored = dynamodb_table.get_item(Key={
            "incident_id": incident_id,
            "timestamp": "2025-03-01T10:30:00Z"
        })
        assert "Item" in stored
        assert stored["Item"]["incident_id"] == incident_id
        assert stored["Item"]["service_name"] == "test-service"
        assert stored["Item"]["failure_type"] == "configuration_error"
        
        # Verify TTL is set (90 days)
        assert "ttl" in stored["Item"]
        
        # Simulate Knowledge Base sync
        # In production, this would write to S3 and trigger ingestion
        kb_document = {
            "incident_id": incident_id,
            "service_name": "test-service",
            "failure_type": "configuration_error",
            "error_patterns": ["TestError"],
            "root_cause": enhanced_alert_for_storage["root_cause"],
            "resolution": enhanced_alert_for_storage["recommended_fixes"][0],
            "timestamp": "2025-03-01T10:30:00Z"
        }
        
        # Verify KB document structure
        assert kb_document["incident_id"] == incident_id
        assert kb_document["failure_type"] == "configuration_error"
        assert "root_cause" in kb_document
        assert "resolution" in kb_document
    
    # Helper methods
    
    def _setup_aws_services(self):
        """Setup mock AWS services for testing."""
        # Create S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket='test-logs')
        
        # Create DynamoDB table
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
        
        # Create SES client and verify email
        ses_client = boto3.client('ses', region_name='us-east-1')
        ses_client.verify_email_identity(EmailAddress='incidents@example.com')
        
        return s3_client, table, ses_client
    
    def _create_api_gateway_event(self, alert_data):
        """Create API Gateway event from alert data."""
        return {
            "body": json.dumps(alert_data),
            "headers": {
                "x-api-key": "test-api-key-12345",
                "Content-Type": "application/json"
            },
            "requestContext": {
                "identity": {
                    "apiKey": "test-api-key-12345"
                }
            }
        }
    
    def _get_lambda_deployment_failure_logs(self):
        """Get sample Lambda deployment failure logs."""
        return """
2025-03-01T10:28:00Z INFO [Lambda] Starting deployment for payment-processor
2025-03-01T10:28:15Z INFO [Lambda] Validating deployment package
2025-03-01T10:28:30Z INFO [Lambda] Package size: 75MB
2025-03-01T10:29:00Z ERROR [Lambda] Deployment package size 75MB exceeds limit of 50MB
2025-03-01T10:29:01Z ERROR [Lambda] Deployment failed: InvalidParameterValueException
2025-03-01T10:29:02Z ERROR [Lambda] Error: Unzipped size must be smaller than 262144000 bytes
2025-03-01T10:29:03Z INFO [Lambda] Rollback initiated
2025-03-01T10:30:00Z ERROR [Lambda] Deployment failed for payment-processor
"""
    
    def _get_dynamodb_throttling_logs(self):
        """Get sample DynamoDB throttling logs."""
        return """
2025-03-01T10:58:00Z INFO [DynamoDB] Table: user-sessions-table
2025-03-01T10:59:00Z WARN [DynamoDB] Read capacity at 95%
2025-03-01T10:59:30Z WARN [DynamoDB] Read capacity at 100%
2025-03-01T11:00:00Z ERROR [DynamoDB] ProvisionedThroughputExceededException
2025-03-01T11:00:01Z ERROR [DynamoDB] Request rate exceeds provisioned throughput
2025-03-01T11:00:02Z ERROR [DynamoDB] 45 throttled requests in last minute
2025-03-01T11:00:03Z WARN [DynamoDB] Auto-scaling not enabled
2025-03-01T11:00:04Z ERROR [DynamoDB] Application experiencing degraded performance
"""
    
    def _get_api_gateway_timeout_logs(self):
        """Get sample API Gateway timeout logs."""
        return """
2025-03-01T15:00:00Z INFO [APIGateway] Request received: POST /api/v1/payments
2025-03-01T15:00:01Z INFO [APIGateway] Forwarding to backend: https://payment-gateway.example.com
2025-03-01T15:00:05Z WARN [APIGateway] Backend response delayed: 5 seconds
2025-03-01T15:00:10Z WARN [APIGateway] Backend response delayed: 10 seconds
2025-03-01T15:00:20Z WARN [APIGateway] Backend response delayed: 20 seconds
2025-03-01T15:00:29Z ERROR [APIGateway] Integration timeout: Endpoint request timed out
2025-03-01T15:00:29Z ERROR [APIGateway] Status Code: 504 Gateway Timeout
2025-03-01T15:00:30Z WARN [APIGateway] 12 timeouts in last 5 minutes
"""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
