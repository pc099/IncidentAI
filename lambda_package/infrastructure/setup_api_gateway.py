"""
API Gateway setup for incident response system.

This module creates and configures the API Gateway REST API with:
- /incidents endpoint for POST requests
- API key authentication
- Rate limiting (100 requests/minute)
- CloudWatch logging
"""

import boto3
import json
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


class APIGatewaySetup:
    """Manages API Gateway REST API setup for incident ingestion."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize API Gateway setup.
        
        Args:
            region: AWS region for API Gateway
        """
        self.region = region
        self.client = boto3.client("apigateway", region_name=region)
        self.api_id: Optional[str] = None
        self.resource_id: Optional[str] = None
        self.stage_name = "prod"
        
    def create_rest_api(self, api_name: str = "incident-response-api") -> str:
        """
        Create REST API Gateway.
        
        Args:
            api_name: Name for the API Gateway
            
        Returns:
            API Gateway ID
        """
        try:
            response = self.client.create_rest_api(
                name=api_name,
                description="API Gateway for AI-Powered Incident Response System",
                endpointConfiguration={"types": ["REGIONAL"]}
            )
            self.api_id = response["id"]
            print(f"Created API Gateway: {self.api_id}")
            return self.api_id
        except ClientError as e:
            print(f"Error creating API Gateway: {e}")
            raise
    
    def get_root_resource_id(self) -> str:
        """
        Get the root resource ID for the API.
        
        Returns:
            Root resource ID
        """
        if not self.api_id:
            raise ValueError("API ID not set. Create API first.")
        
        try:
            response = self.client.get_resources(restApiId=self.api_id)
            for item in response["items"]:
                if item["path"] == "/":
                    return item["id"]
            raise ValueError("Root resource not found")
        except ClientError as e:
            print(f"Error getting root resource: {e}")
            raise
    
    def create_incidents_resource(self) -> str:
        """
        Create /incidents resource.
        
        Returns:
            Resource ID for /incidents
        """
        if not self.api_id:
            raise ValueError("API ID not set. Create API first.")
        
        try:
            root_id = self.get_root_resource_id()
            response = self.client.create_resource(
                restApiId=self.api_id,
                parentId=root_id,
                pathPart="incidents"
            )
            self.resource_id = response["id"]
            print(f"Created /incidents resource: {self.resource_id}")
            return self.resource_id
        except ClientError as e:
            print(f"Error creating /incidents resource: {e}")
            raise
    
    def create_post_method(self, lambda_arn: str) -> None:
        """
        Create POST method for /incidents endpoint.
        
        Args:
            lambda_arn: ARN of the Lambda function to integrate
        """
        if not self.api_id or not self.resource_id:
            raise ValueError("API ID and resource ID must be set")
        
        try:
            # Create method with API key requirement
            self.client.put_method(
                restApiId=self.api_id,
                resourceId=self.resource_id,
                httpMethod="POST",
                authorizationType="NONE",
                apiKeyRequired=True,
                requestParameters={
                    "method.request.header.Content-Type": True
                }
            )
            print("Created POST method with API key requirement")
            
            # Create Lambda integration
            uri = f"arn:aws:apigateway:{self.region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
            self.client.put_integration(
                restApiId=self.api_id,
                resourceId=self.resource_id,
                httpMethod="POST",
                type="AWS_PROXY",
                integrationHttpMethod="POST",
                uri=uri
            )
            print("Created Lambda integration")
            
        except ClientError as e:
            print(f"Error creating POST method: {e}")
            raise
    
    def create_usage_plan(self, api_key_id: str, plan_name: str = "incident-response-plan") -> str:
        """
        Create usage plan with rate limiting.
        
        Args:
            api_key_id: API key ID to associate with the plan
            plan_name: Name for the usage plan
            
        Returns:
            Usage plan ID
        """
        if not self.api_id:
            raise ValueError("API ID not set")
        
        try:
            # Create usage plan with rate limiting (100 requests/minute)
            response = self.client.create_usage_plan(
                name=plan_name,
                description="Usage plan for incident response API with rate limiting",
                throttle={
                    "rateLimit": 100.0,  # 100 requests per second
                    "burstLimit": 200    # Burst capacity
                },
                quota={
                    "limit": 144000,     # 100 req/min * 60 min * 24 hours
                    "period": "DAY"
                }
            )
            usage_plan_id = response["id"]
            print(f"Created usage plan: {usage_plan_id}")
            
            # Associate API stage with usage plan
            self.client.create_usage_plan_key(
                usagePlanId=usage_plan_id,
                keyId=api_key_id,
                keyType="API_KEY"
            )
            print(f"Associated API key with usage plan")
            
            return usage_plan_id
        except ClientError as e:
            print(f"Error creating usage plan: {e}")
            raise
    
    def create_api_key(self, key_name: str = "incident-response-key") -> Dict[str, str]:
        """
        Create API key for authentication.
        
        Args:
            key_name: Name for the API key
            
        Returns:
            Dictionary with key ID and value
        """
        try:
            response = self.client.create_api_key(
                name=key_name,
                description="API key for incident response system",
                enabled=True
            )
            print(f"Created API key: {response['id']}")
            return {
                "id": response["id"],
                "value": response["value"]
            }
        except ClientError as e:
            print(f"Error creating API key: {e}")
            raise
    
    def enable_cloudwatch_logging(self) -> None:
        """Enable CloudWatch logging for the API Gateway."""
        if not self.api_id:
            raise ValueError("API ID not set")
        
        try:
            # Update stage settings for CloudWatch logging
            self.client.update_stage(
                restApiId=self.api_id,
                stageName=self.stage_name,
                patchOperations=[
                    {
                        "op": "replace",
                        "path": "/accessLogSettings/destinationArn",
                        "value": f"arn:aws:logs:{self.region}:*:log-group:/aws/apigateway/incident-response"
                    },
                    {
                        "op": "replace",
                        "path": "/accessLogSettings/format",
                        "value": json.dumps({
                            "requestId": "$context.requestId",
                            "ip": "$context.identity.sourceIp",
                            "requestTime": "$context.requestTime",
                            "httpMethod": "$context.httpMethod",
                            "resourcePath": "$context.resourcePath",
                            "status": "$context.status",
                            "protocol": "$context.protocol",
                            "responseLength": "$context.responseLength"
                        })
                    },
                    {
                        "op": "replace",
                        "path": "/*/*/logging/loglevel",
                        "value": "INFO"
                    },
                    {
                        "op": "replace",
                        "path": "/*/*/logging/dataTrace",
                        "value": "true"
                    }
                ]
            )
            print("Enabled CloudWatch logging")
        except ClientError as e:
            print(f"Error enabling CloudWatch logging: {e}")
            raise
    
    def deploy_api(self, stage_name: str = "prod") -> str:
        """
        Deploy API to a stage.
        
        Args:
            stage_name: Name of the deployment stage
            
        Returns:
            Deployment ID
        """
        if not self.api_id:
            raise ValueError("API ID not set")
        
        self.stage_name = stage_name
        
        try:
            response = self.client.create_deployment(
                restApiId=self.api_id,
                stageName=stage_name,
                description="Production deployment of incident response API"
            )
            deployment_id = response["id"]
            print(f"Deployed API to stage '{stage_name}': {deployment_id}")
            
            # Get invoke URL
            invoke_url = f"https://{self.api_id}.execute-api.{self.region}.amazonaws.com/{stage_name}"
            print(f"API Endpoint: {invoke_url}/incidents")
            
            return deployment_id
        except ClientError as e:
            print(f"Error deploying API: {e}")
            raise
    
    def setup_complete_api(self, lambda_arn: str) -> Dict[str, Any]:
        """
        Complete API Gateway setup with all configurations.
        
        Args:
            lambda_arn: ARN of the Lambda function for incident validation
            
        Returns:
            Dictionary with API details (api_id, endpoint, api_key)
        """
        # Create API
        api_id = self.create_rest_api()
        
        # Create /incidents resource
        self.create_incidents_resource()
        
        # Create POST method with Lambda integration
        self.create_post_method(lambda_arn)
        
        # Deploy API
        self.deploy_api()
        
        # Create API key
        api_key = self.create_api_key()
        
        # Create usage plan with rate limiting
        usage_plan_id = self.create_usage_plan(api_key["id"])
        
        # Associate usage plan with stage
        self.client.update_usage_plan(
            usagePlanId=usage_plan_id,
            patchOperations=[
                {
                    "op": "add",
                    "path": "/apiStages",
                    "value": f"{api_id}:{self.stage_name}"
                }
            ]
        )
        
        # Enable CloudWatch logging
        try:
            self.enable_cloudwatch_logging()
        except Exception as e:
            print(f"Warning: Could not enable CloudWatch logging: {e}")
        
        endpoint = f"https://{api_id}.execute-api.{self.region}.amazonaws.com/{self.stage_name}/incidents"
        
        return {
            "api_id": api_id,
            "endpoint": endpoint,
            "api_key_id": api_key["id"],
            "api_key_value": api_key["value"],
            "usage_plan_id": usage_plan_id,
            "stage": self.stage_name
        }


def main():
    """Main function for testing API Gateway setup."""
    import os
    
    # Get Lambda ARN from environment or use placeholder
    lambda_arn = os.environ.get(
        "INCIDENT_VALIDATOR_LAMBDA_ARN",
        "arn:aws:lambda:us-east-1:123456789012:function:incident-validator"
    )
    
    setup = APIGatewaySetup()
    result = setup.setup_complete_api(lambda_arn)
    
    print("\n=== API Gateway Setup Complete ===")
    print(f"API ID: {result['api_id']}")
    print(f"Endpoint: {result['endpoint']}")
    print(f"API Key: {result['api_key_value']}")
    print(f"Usage Plan ID: {result['usage_plan_id']}")
    print("\nTest with:")
    print(f"curl -X POST {result['endpoint']} \\")
    print(f"  -H 'x-api-key: {result['api_key_value']}' \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{{\"service_name\":\"test\",\"timestamp\":\"2025-01-15T10:30:00Z\",\"error_message\":\"test\",\"log_location\":\"s3://test/log.txt\"}}'")


if __name__ == "__main__":
    main()
