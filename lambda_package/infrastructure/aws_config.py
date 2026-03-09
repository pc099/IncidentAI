"""AWS Configuration Module"""
import os
from typing import Optional

# AWS Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")

# S3 Configuration
LOG_BUCKET_NAME = os.environ.get("LOG_BUCKET_NAME", "incident-response-logs")
KB_DATA_SOURCE_BUCKET_NAME = os.environ.get("KB_DATA_SOURCE_BUCKET_NAME", "incident-response-kb-data")

# DynamoDB Configuration
INCIDENT_TABLE_NAME = "incident-history"
INCIDENT_TABLE_GSI_NAME = "service-timestamp-index"

# SES Configuration
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "harshavignesh1@gmail.com")
SES_VERIFIED_DOMAIN = os.environ.get("SES_VERIFIED_DOMAIN", "gmail.com")

# IAM Role Names
LAMBDA_EXECUTION_ROLE_NAME = "incident-response-lambda-role"
ORCHESTRATOR_ROLE_NAME = "incident-response-orchestrator-role"
AGENT_ROLE_NAME = "incident-response-agent-role"


def get_aws_region() -> str:
    """Get configured AWS region"""
    return AWS_REGION


def get_log_bucket_name() -> str:
    """Get S3 log bucket name"""
    return LOG_BUCKET_NAME


def get_kb_data_source_bucket_name() -> str:
    """Get S3 Knowledge Base data source bucket name"""
    return KB_DATA_SOURCE_BUCKET_NAME


def get_incident_table_name() -> str:
    """Get DynamoDB incident table name"""
    return INCIDENT_TABLE_NAME


def get_boto3_config():
    """
    Get boto3 Config object with SSL verification settings.
    
    Returns Config with verify=False if SSL_VERIFY environment variable is set to 'false'
    """
    import boto3
    from botocore.config import Config
    
    # Check if SSL verification should be disabled
    ssl_verify = os.environ.get("SSL_VERIFY", "true").lower() != "false"
    
    if not ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    return Config(
        region_name=AWS_REGION,
        signature_version='v4',
        retries={'max_attempts': 3, 'mode': 'standard'}
    ), ssl_verify


def create_boto3_client(service_name: str, **kwargs):
    """
    Create a boto3 client with proper configuration.
    
    Args:
        service_name: AWS service name (e.g., 's3', 'dynamodb')
        **kwargs: Additional arguments to pass to boto3.client()
    
    Returns:
        boto3 client
    """
    import boto3
    
    config, ssl_verify = get_boto3_config()
    
    return boto3.client(
        service_name,
        region_name=AWS_REGION,
        config=config,
        verify=ssl_verify,
        **kwargs
    )
