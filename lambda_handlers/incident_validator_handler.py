"""
Lambda Handler: Incident Validator
Validates incoming alert payloads and triggers orchestrator
"""
import json
import os
import sys
import boto3
from datetime import datetime
import uuid

# Add src to path for imports
sys.path.insert(0, '/opt/python')  # Lambda layer path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.incident_validator import validate_payload, extract_incident_context


def lambda_handler(event, context):
    """
    Lambda handler for incident validation.
    
    Triggered by: API Gateway POST /incidents
    
    Args:
        event: API Gateway event with body containing alert payload
        context: Lambda context
        
    Returns:
        dict: API Gateway response with status code and body
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Validate payload
        is_valid, error_message = validate_payload(body)
        
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid payload',
                    'message': error_message
                })
            }
        
        # Generate incident ID
        incident_id = f"inc-{datetime.utcnow().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}"
        
        # Extract incident context
        incident_context = extract_incident_context(body)
        
        # Prepare payload for orchestrator
        orchestrator_payload = {
            'incident_id': incident_id,
            'service_name': body['service_name'],
            'timestamp': body['timestamp'],
            'error_message': body['error_message'],
            'log_location': body['log_location'],
            'alert_source': body.get('alert_source', 'Manual'),
            'received_at': datetime.utcnow().isoformat()
        }
        
        # Invoke orchestrator Lambda asynchronously
        lambda_client = boto3.client('lambda')
        orchestrator_function = os.environ.get('ORCHESTRATOR_FUNCTION_NAME', 'incident-orchestrator')
        
        lambda_client.invoke(
            FunctionName=orchestrator_function,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps(orchestrator_payload)
        )
        
        # Return 202 Accepted
        return {
            'statusCode': 202,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Incident accepted for processing',
                'incident_id': incident_id,
                'status': 'processing'
            })
        }
        
    except Exception as e:
        print(f"Error in incident validator: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
