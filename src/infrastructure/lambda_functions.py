"""
Lambda Functions for Enhanced Incident Response System

Production-ready Lambda functions for:
- API Gateway integration
- Microsoft Teams notifications
- Incident processing orchestration
- Human approval workflows
"""

import json
import logging
import os
import asyncio
import uuid
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients lazily to avoid import-time credential requirements
stepfunctions = None
apigateway_management = None  # Initialized per request

def get_stepfunctions_client():
    """Get Step Functions client with lazy initialization"""
    global stepfunctions
    if stepfunctions is None:
        stepfunctions = boto3.client('stepfunctions')
    return stepfunctions


def handle_direct_invocation(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Handle direct Lambda invocation (for testing)
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        # Extract incident data from event
        incident_data = event.get('body', {})
        if isinstance(incident_data, str):
            incident_data = json.loads(incident_data)
        
        # Generate incident ID
        incident_id = f"direct-{uuid.uuid4().hex[:12]}"
        
        # For direct invocation, we'll simulate the response
        # In a real implementation, this would process the incident
        response_body = {
            "incident_id": incident_id,
            "status": "processing",
            "message": "Incident processing started via direct invocation"
        }
        
        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Direct invocation error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler that routes requests based on event source
    
    Handles:
    - API Gateway REST requests (incident submission)
    - Microsoft Teams webhook events (approval responses)
    - Step Functions tasks (orchestration)
    - SNS notifications (approval workflows)
    """
    try:
        # Determine event source and route accordingly
        if 'requestContext' in event:
            # REST API event
            return handle_api_event(event, context)
        elif 'source' in event and event['source'] == 'aws.stepfunctions':
            # Step Functions task
            return handle_stepfunctions_task(event, context)
        elif 'Records' in event:
            # SNS/SQS event
            return handle_sns_event(event, context)
        else:
            # Direct invocation (testing)
            return handle_direct_invocation(event, context)
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


def handle_api_event(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle REST API Gateway events"""
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'POST' and path == '/incident':
            return handle_incident_submission(event, context)
        elif http_method == 'GET' and path.startswith('/incident/'):
            return handle_incident_status(event, context)
        elif http_method == 'POST' and path.startswith('/approval/'):
            return handle_approval_response(event, context)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        logger.error(f"API event handling error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_incident_submission(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle incident submission via REST API"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        required_fields = ['service_name', 'timestamp', 'error_message', 'log_location']
        missing_fields = [field for field in required_fields if field not in body]
        
        if missing_fields:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields',
                    'missing_fields': missing_fields
                })
            }
        
        # Generate incident ID
        import uuid
        incident_id = f"incident-{uuid.uuid4().hex[:8]}"
        body['incident_id'] = incident_id
        
        # Start Step Functions execution
        state_machine_arn = os.environ['INCIDENT_PROCESSING_STATE_MACHINE_ARN']
        
        stepfunctions_client = get_stepfunctions_client()
        execution_response = stepfunctions_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=f"incident-{incident_id}",
            input=json.dumps(body)
        )
        
        logger.info(f"Started incident processing: {incident_id}")
        
        return {
            'statusCode': 202,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'incident_id': incident_id,
                'status': 'processing',
                'execution_arn': execution_response['executionArn']
            })
        }
        
    except Exception as e:
        logger.error(f"Incident submission error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_stepfunctions_task(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle Step Functions task execution"""
    try:
        task_name = event.get('task_name')
        
        if task_name == 'enhanced_orchestration':
            return handle_enhanced_orchestration(event, context)
        elif task_name == 'human_approval':
            return handle_human_approval_task(event, context)
        elif task_name == 'send_notification':
            return handle_notification_task(event, context)
        else:
            raise ValueError(f"Unknown task: {task_name}")
            
    except Exception as e:
        logger.error(f"Step Functions task error: {str(e)}")
        raise


def handle_enhanced_orchestration(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle enhanced incident orchestration"""
    try:
        # Import enhanced system (lazy loading)
        import sys
        import os
        sys.path.append('/opt/python')  # Lambda layer path
        
        from enhanced_system import get_enhanced_system
        
        # Get incident data
        incident_data = event.get('incident_data', {})
        
        # Process with enhanced system
        enhanced_system = get_enhanced_system()
        
        # Run async processing in Lambda
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                enhanced_system.process_incident(
                    incident_data=incident_data
                )
            )
            
            return {
                'statusCode': 200,
                'result': result
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Enhanced orchestration error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }


# Approval workflow handlers
def handle_human_approval_task(event: Dict[str, Any], context) -> Dict[str, Any]:
    """Handle human approval task"""
    try:
        approval_request = event.get('approval_request', {})
        task_token = event.get('task_token')
        
        # Store approval request in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        approvals_table = dynamodb.Table(os.environ['APPROVAL_REQUESTS_TABLE'])
        
        approval_id = f"approval-{uuid.uuid4().hex[:8]}"
        
        approvals_table.put_item(
            Item={
                'approval_id': approval_id,
                'task_token': task_token,
                'approval_request': approval_request,
                'status': 'pending',
                'created_at': int(time.time()),
                'expires_at': int(time.time()) + 1800,  # 30 minutes
                'ttl': int(time.time()) + 3600  # 1 hour TTL
            }
        )
        
        # Send Teams approval notification
        send_teams_approval_notification(approval_id, approval_request)
        
        return {
            'statusCode': 200,
            'approval_id': approval_id,
            'status': 'pending'
        }
        
    except Exception as e:
        logger.error(f"Human approval task error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }


def send_teams_approval_notification(approval_id: str, approval_request: Dict[str, Any]):
    """Send approval notification to Microsoft Teams"""
    try:
        import urllib3
        
        webhook_url = os.environ.get('TEAMS_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("Teams webhook URL not configured")
            return
        
        # Teams Adaptive Card format
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.3",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "🚨 Human Approval Required",
                                "weight": "Bolder",
                                "size": "Medium",
                                "color": "Attention"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Incident:",
                                        "value": approval_request.get('incident_id')
                                    },
                                    {
                                        "title": "Action:",
                                        "value": approval_request.get('action_type')
                                    },
                                    {
                                        "title": "Confidence:",
                                        "value": f"{approval_request.get('confidence_score', 0):.1f}%"
                                    }
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": f"**Reasoning:** {approval_request.get('reasoning', 'No reasoning provided')}",
                                "wrap": True
                            }
                        ],
                        "actions": [
                            {
                                "type": "Action.Http",
                                "title": "✅ Approve",
                                "style": "positive",
                                "url": f"{os.environ.get('API_GATEWAY_URL', '')}/approval/{approval_id}/approve",
                                "method": "POST"
                            },
                            {
                                "type": "Action.Http", 
                                "title": "❌ Reject",
                                "style": "destructive",
                                "url": f"{os.environ.get('API_GATEWAY_URL', '')}/approval/{approval_id}/reject",
                                "method": "POST"
                            }
                        ]
                    }
                }
            ]
        }
        
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(card),
            headers={'Content-Type': 'application/json'}
        )
        
        logger.info(f"Teams notification sent for approval {approval_id}")
        
    except Exception as e:
        logger.error(f"Teams notification error: {str(e)}")


# Import required modules at module level for Lambda
import time
import uuid