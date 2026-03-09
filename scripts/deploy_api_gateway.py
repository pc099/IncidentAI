#!/usr/bin/env python3
"""
API Gateway Deployment Script
Creates API Gateway REST API and connects to Lambda validator
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from infrastructure.setup_api_gateway import APIGatewaySetup
from infrastructure.aws_config import get_aws_region, create_boto3_client


def get_lambda_arn(function_name):
    """Get Lambda function ARN."""
    lambda_client = create_boto3_client('lambda')
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        return response['Configuration']['FunctionArn']
    except Exception as e:
        print(f"Error getting Lambda ARN for {function_name}: {e}")
        return None


def add_lambda_permission(function_name, api_id, region):
    """Add permission for API Gateway to invoke Lambda."""
    lambda_client = create_boto3_client('lambda')
    
    statement_id = f"apigateway-{api_id}"
    source_arn = f"arn:aws:execute-api:{region}:*:{api_id}/*/*"
    
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        print(f"  ✓ Added API Gateway invoke permission to {function_name}")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"  ℹ Permission already exists for {function_name}")
    except Exception as e:
        print(f"  ⚠ Error adding permission: {e}")


def deploy_api_gateway():
    """Deploy API Gateway."""
    print("=" * 60)
    print("API Gateway Deployment - Incident Response System")
    print("=" * 60)
    
    # Get Lambda ARN
    print("\n📋 Getting Lambda function ARN...")
    lambda_arn = get_lambda_arn('incident-validator')
    
    if not lambda_arn:
        print("  ✗ Lambda function 'incident-validator' not found")
        print("  Please deploy Lambda functions first: python scripts/deploy_lambdas.py")
        return False
    
    print(f"  ✓ Lambda ARN: {lambda_arn}")
    
    # Create API Gateway
    print("\n🚀 Creating API Gateway...")
    setup = APIGatewaySetup(region=get_aws_region())
    
    try:
        result = setup.setup_complete_api(lambda_arn)
        
        # Add Lambda permission
        add_lambda_permission('incident-validator', result['api_id'], get_aws_region())
        
        # Print results
        print("\n" + "=" * 60)
        print("API Gateway Deployment Complete!")
        print("=" * 60)
        print(f"\n📍 API Endpoint: {result['endpoint']}")
        print(f"🔑 API Key: {result['api_key_value']}")
        print(f"📊 API ID: {result['api_id']}")
        print(f"🎯 Stage: {result['stage']}")
        print(f"📈 Usage Plan: {result['usage_plan_id']}")
        
        # Save API info
        api_info = {
            'endpoint': result['endpoint'],
            'api_key': result['api_key_value'],
            'api_id': result['api_id'],
            'stage': result['stage'],
            'usage_plan_id': result['usage_plan_id'],
            'region': get_aws_region()
        }
        
        with open('api_gateway_info.json', 'w') as f:
            json.dump(api_info, f, indent=2)
        print(f"\n💾 API info saved to: api_gateway_info.json")
        
        # Print test command
        print("\n" + "=" * 60)
        print("Test Your API")
        print("=" * 60)
        print("\nTest with curl:")
        print(f"""
curl -X POST {result['endpoint']} \\
  -H 'x-api-key: {result['api_key_value']}' \\
  -H 'Content-Type: application/json' \\
  -d '{{
    "service_name": "test-service",
    "timestamp": "2026-03-09T10:00:00Z",
    "error_message": "Test error",
    "log_location": "s3://incident-response-logs-867126415696/test.log"
  }}'
""")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error deploying API Gateway: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = deploy_api_gateway()
    sys.exit(0 if success else 1)
