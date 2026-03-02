"""DynamoDB Table Setup for Incident History"""
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import (
    get_aws_region,
    get_incident_table_name,
    INCIDENT_TABLE_GSI_NAME
)

logger = Logger()


def create_incident_table() -> dict:
    """
    Create DynamoDB table for incident history.
    
    Table structure:
    - Partition key: incident_id (String)
    - Sort key: timestamp (String)
    - GSI: service-timestamp-index
      - Partition key: service_name (String)
      - Sort key: timestamp (String)
    - Billing mode: On-demand (cost optimization)
    - TTL: 90 days
    
    Returns:
        dict: Table creation response
    """
    dynamodb_client = boto3.client("dynamodb", region_name=get_aws_region())
    table_name = get_incident_table_name()
    
    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "incident_id", "KeyType": "HASH"},  # Partition key
                {"AttributeName": "timestamp", "KeyType": "RANGE"}    # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "incident_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
                {"AttributeName": "service_name", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": INCIDENT_TABLE_GSI_NAME,
                    "KeySchema": [
                        {"AttributeName": "service_name", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST",  # On-demand billing for cost optimization
            SSESpecification={
                "Enabled": True,
                "SSEType": "KMS"
            },
            Tags=[
                {"Key": "Project", "Value": "IncidentResponse"},
                {"Key": "Environment", "Value": "Production"}
            ]
        )
        
        logger.info(f"Created DynamoDB table: {table_name}")
        
        # Wait for table to be active
        waiter = dynamodb_client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        
        # Enable TTL (90 days)
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                "Enabled": True,
                "AttributeName": "ttl"
            }
        )
        logger.info(f"Enabled TTL for table: {table_name}")
        
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info(f"Table {table_name} already exists")
            return {"TableDescription": {"TableName": table_name}}
        else:
            logger.error(f"Error creating table: {e}")
            raise


def verify_table_exists() -> bool:
    """
    Verify that the incident table exists.
    
    Returns:
        bool: True if table exists, False otherwise
    """
    dynamodb_client = boto3.client("dynamodb", region_name=get_aws_region())
    table_name = get_incident_table_name()
    
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError:
        return False
