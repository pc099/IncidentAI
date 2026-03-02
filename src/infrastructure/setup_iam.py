"""IAM Role Setup with Least-Privilege Permissions"""
import json
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import (
    get_aws_region,
    get_log_bucket_name,
    get_incident_table_name,
    LAMBDA_EXECUTION_ROLE_NAME,
    ORCHESTRATOR_ROLE_NAME,
    AGENT_ROLE_NAME,
    AWS_ACCOUNT_ID
)

logger = Logger()


def create_lambda_execution_role() -> dict:
    """
    Create IAM role for Lambda function execution with least-privilege permissions.
    
    Permissions:
    - CloudWatch Logs (write)
    - S3 (read logs)
    - DynamoDB (read/write incident history)
    - SES (send emails)
    - Bedrock (invoke models)
    
    Returns:
        dict: Role creation response
    """
    iam_client = boto3.client("iam", region_name=get_aws_region())
    
    # Trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        response = iam_client.create_role(
            RoleName=LAMBDA_EXECUTION_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for Incident Response Lambda functions",
            Tags=[
                {"Key": "Project", "Value": "IncidentResponse"},
                {"Key": "Environment", "Value": "Production"}
            ]
        )
        
        logger.info(f"Created IAM role: {LAMBDA_EXECUTION_ROLE_NAME}")
        
        # Attach AWS managed policy for basic Lambda execution
        iam_client.attach_role_policy(
            RoleName=LAMBDA_EXECUTION_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        # Create and attach custom policy for S3, DynamoDB, SES, Bedrock
        custom_policy = create_lambda_custom_policy()
        iam_client.put_role_policy(
            RoleName=LAMBDA_EXECUTION_ROLE_NAME,
            PolicyName="IncidentResponsePermissions",
            PolicyDocument=json.dumps(custom_policy)
        )
        
        logger.info(f"Attached policies to role: {LAMBDA_EXECUTION_ROLE_NAME}")
        
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            logger.info(f"Role {LAMBDA_EXECUTION_ROLE_NAME} already exists")
            return {"Role": {"RoleName": LAMBDA_EXECUTION_ROLE_NAME}}
        else:
            logger.error(f"Error creating role: {e}")
            raise


def create_lambda_custom_policy() -> dict:
    """
    Create custom IAM policy with least-privilege permissions.
    
    Returns:
        dict: IAM policy document
    """
    bucket_name = get_log_bucket_name()
    table_name = get_incident_table_name()
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3LogReadAccess",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            },
            {
                "Sid": "DynamoDBIncidentAccess",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:UpdateItem"
                ],
                "Resource": [
                    f"arn:aws:dynamodb:{get_aws_region()}:{AWS_ACCOUNT_ID}:table/{table_name}",
                    f"arn:aws:dynamodb:{get_aws_region()}:{AWS_ACCOUNT_ID}:table/{table_name}/index/*"
                ]
            },
            {
                "Sid": "SESEmailSendAccess",
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail"
                ],
                "Resource": "*",
                "Condition": {
                    "StringLike": {
                        "ses:FromAddress": "incidents@*"
                    }
                }
            },
            {
                "Sid": "BedrockModelAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{get_aws_region()}::foundation-model/anthropic.claude-*"
                ]
            },
            {
                "Sid": "BedrockAgentRuntimeAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agent-runtime:InvokeAgent",
                    "bedrock-agent-runtime:Retrieve"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchMetricsAccess",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "cloudwatch:namespace": "IncidentResponse"
                    }
                }
            }
        ]
    }
    
    return policy


def create_orchestrator_role() -> dict:
    """
    Create IAM role for Strands Orchestrator with agent invocation permissions.
    
    Returns:
        dict: Role creation response
    """
    iam_client = boto3.client("iam", region_name=get_aws_region())
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        response = iam_client.create_role(
            RoleName=ORCHESTRATOR_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Orchestrator role for Strands Agents framework",
            Tags=[
                {"Key": "Project", "Value": "IncidentResponse"},
                {"Key": "Component", "Value": "Orchestrator"}
            ]
        )
        
        logger.info(f"Created IAM role: {ORCHESTRATOR_ROLE_NAME}")
        
        # Attach basic execution policy
        iam_client.attach_role_policy(
            RoleName=ORCHESTRATOR_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        # Create orchestrator-specific policy
        orchestrator_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "BedrockAgentAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agent:InvokeAgent",
                        "bedrock-agent-runtime:InvokeAgent"
                    ],
                    "Resource": "*"
                },
                {
                    "Sid": "LambdaInvokeAgents",
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        f"arn:aws:lambda:{get_aws_region()}:{AWS_ACCOUNT_ID}:function:incident-*-agent"
                    ]
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=ORCHESTRATOR_ROLE_NAME,
            PolicyName="OrchestratorPermissions",
            PolicyDocument=json.dumps(orchestrator_policy)
        )
        
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            logger.info(f"Role {ORCHESTRATOR_ROLE_NAME} already exists")
            return {"Role": {"RoleName": ORCHESTRATOR_ROLE_NAME}}
        else:
            logger.error(f"Error creating role: {e}")
            raise


def get_role_arn(role_name: str) -> str:
    """
    Get ARN for an IAM role.
    
    Args:
        role_name: Name of the IAM role
        
    Returns:
        str: Role ARN
    """
    iam_client = boto3.client("iam", region_name=get_aws_region())
    
    try:
        response = iam_client.get_role(RoleName=role_name)
        return response["Role"]["Arn"]
    except ClientError as e:
        logger.error(f"Error getting role ARN: {e}")
        raise
