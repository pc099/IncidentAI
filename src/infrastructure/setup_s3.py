"""S3 Bucket Setup for Log Storage"""
import os
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import get_aws_region, get_log_bucket_name, get_kb_data_source_bucket_name

logger = Logger()


def create_log_bucket() -> dict:
    """
    Create S3 bucket for log storage with lifecycle policies.
    
    Lifecycle policies:
    - Transition to Standard-IA after 30 days
    - Delete after 90 days
    
    Returns:
        dict: Bucket creation response
    """
    s3_client = boto3.client("s3", region_name=get_aws_region())
    bucket_name = get_log_bucket_name()
    region = get_aws_region()
    
    try:
        # Create bucket
        if region == "us-east-1":
            response = s3_client.create_bucket(Bucket=bucket_name)
        else:
            response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        
        logger.info(f"Created S3 bucket: {bucket_name}")
        
        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"}
        )
        logger.info(f"Enabled versioning for bucket: {bucket_name}")
        
        # Configure lifecycle policy
        lifecycle_policy = {
            "Rules": [
                {
                    "Id": "TransitionToStandardIA",
                    "Status": "Enabled",
                    "Prefix": "",
                    "Transitions": [
                        {
                            "Days": 30,
                            "StorageClass": "STANDARD_IA"
                        }
                    ],
                    "Expiration": {
                        "Days": 90
                    }
                }
            ]
        }
        
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_policy
        )
        logger.info(f"Configured lifecycle policy for bucket: {bucket_name}")
        
        # Enable server-side encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        )
        logger.info(f"Enabled encryption for bucket: {bucket_name}")
        
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            logger.info(f"Bucket {bucket_name} already exists")
            return {"Location": f"/{bucket_name}"}
        else:
            logger.error(f"Error creating bucket: {e}")
            raise


def verify_bucket_exists() -> bool:
    """
    Verify that the log bucket exists.
    
    Returns:
        bool: True if bucket exists, False otherwise
    """
    s3_client = boto3.client("s3", region_name=get_aws_region())
    bucket_name = get_log_bucket_name()
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False


def create_kb_data_source_bucket() -> dict:
    """
    Create S3 bucket for Bedrock Knowledge Base data source.
    
    Features:
    - Versioning enabled for data integrity
    - Bucket policy configured for Bedrock access
    - Server-side encryption enabled
    
    Returns:
        dict: Bucket creation response
    """
    s3_client = boto3.client("s3", region_name=get_aws_region())
    bucket_name = get_kb_data_source_bucket_name()
    region = get_aws_region()
    
    try:
        # Create bucket
        if region == "us-east-1":
            response = s3_client.create_bucket(Bucket=bucket_name)
        else:
            response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region}
            )
        
        logger.info(f"Created S3 bucket for Knowledge Base: {bucket_name}")
        
        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"}
        )
        logger.info(f"Enabled versioning for Knowledge Base bucket: {bucket_name}")
        
        # Enable server-side encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        )
        logger.info(f"Enabled encryption for Knowledge Base bucket: {bucket_name}")
        
        # Configure bucket policy for Bedrock access
        # Note: AWS Account ID is required for the policy
        account_id = os.environ.get("AWS_ACCOUNT_ID", "")
        if account_id:
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowBedrockKnowledgeBaseAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": account_id
                            }
                        }
                    }
                ]
            }
            
            import json
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            logger.info(f"Configured bucket policy for Bedrock access: {bucket_name}")
        else:
            logger.warning("AWS_ACCOUNT_ID not set - skipping bucket policy configuration")
            logger.warning("Set AWS_ACCOUNT_ID environment variable and run again to configure Bedrock access")
        
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
            logger.info(f"Knowledge Base bucket {bucket_name} already exists")
            return {"Location": f"/{bucket_name}"}
        else:
            logger.error(f"Error creating Knowledge Base bucket: {e}")
            raise


def verify_kb_bucket_exists() -> bool:
    """
    Verify that the Knowledge Base data source bucket exists.
    
    Returns:
        bool: True if bucket exists, False otherwise
    """
    s3_client = boto3.client("s3", region_name=get_aws_region())
    bucket_name = get_kb_data_source_bucket_name()
    
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False
