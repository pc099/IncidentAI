"""OpenSearch Serverless Collection Setup for Bedrock Knowledge Base"""
import os
import boto3
import time
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import get_aws_region, create_boto3_client

logger = Logger()


def get_collection_name() -> str:
    """Get OpenSearch Serverless collection name"""
    return os.environ.get("AOSS_COLLECTION_NAME", "incident-kb-coll")


def create_encryption_policy() -> dict:
    """
    Create encryption policy for OpenSearch Serverless collection.
    
    Returns:
        dict: Encryption policy creation response
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    policy_name = f"{collection_name}-encryption"
    
    policy = {
        "Rules": [
            {
                "ResourceType": "collection",
                "Resource": [f"collection/{collection_name}"]
            }
        ],
        "AWSOwnedKey": True
    }
    
    try:
        import json
        response = aoss_client.create_security_policy(
            name=policy_name,
            type="encryption",
            policy=json.dumps(policy)
        )
        logger.info(f"Created encryption policy: {policy_name}")
        return response
    except ClientError as e:
        if "ConflictException" in str(e) or "already exists" in str(e):
            logger.info(f"Encryption policy {policy_name} already exists")
            return {"policy": {"name": policy_name}}
        else:
            logger.error(f"Error creating encryption policy: {e}")
            raise


def create_network_policy() -> dict:
    """
    Create network policy for OpenSearch Serverless collection.
    
    Returns:
        dict: Network policy creation response
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    policy_name = f"{collection_name}-network"
    
    policy = [
        {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"]
                },
                {
                    "ResourceType": "dashboard",
                    "Resource": [f"collection/{collection_name}"]
                }
            ],
            "AllowFromPublic": True
        }
    ]
    
    try:
        import json
        response = aoss_client.create_security_policy(
            name=policy_name,
            type="network",
            policy=json.dumps(policy)
        )
        logger.info(f"Created network policy: {policy_name}")
        return response
    except ClientError as e:
        if "ConflictException" in str(e) or "already exists" in str(e):
            logger.info(f"Network policy {policy_name} already exists")
            return {"policy": {"name": policy_name}}
        else:
            logger.error(f"Error creating network policy: {e}")
            raise


def create_data_access_policy() -> dict:
    """
    Create data access policy for OpenSearch Serverless collection.
    
    Returns:
        dict: Data access policy creation response
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    policy_name = f"{collection_name}-access"
    account_id = os.environ.get("AWS_ACCOUNT_ID", "")
    
    if not account_id:
        raise ValueError("AWS_ACCOUNT_ID environment variable must be set")
    
    # Grant access to the KB role
    kb_role_arn = f"arn:aws:iam::{account_id}:role/incident-response-kb-role"
    
    policy = [
        {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"],
                    "Permission": [
                        "aoss:CreateCollectionItems",
                        "aoss:DeleteCollectionItems",
                        "aoss:UpdateCollectionItems",
                        "aoss:DescribeCollectionItems"
                    ]
                },
                {
                    "ResourceType": "index",
                    "Resource": [f"index/{collection_name}/*"],
                    "Permission": [
                        "aoss:CreateIndex",
                        "aoss:DeleteIndex",
                        "aoss:UpdateIndex",
                        "aoss:DescribeIndex",
                        "aoss:ReadDocument",
                        "aoss:WriteDocument"
                    ]
                }
            ],
            "Principal": [kb_role_arn]
        }
    ]
    
    try:
        import json
        response = aoss_client.create_access_policy(
            name=policy_name,
            type="data",
            policy=json.dumps(policy)
        )
        logger.info(f"Created data access policy: {policy_name}")
        return response
    except ClientError as e:
        if "ConflictException" in str(e) or "already exists" in str(e):
            logger.info(f"Data access policy {policy_name} already exists")
            return {"accessPolicy": {"name": policy_name}}
        else:
            logger.error(f"Error creating data access policy: {e}")
            raise


def create_collection() -> dict:
    """
    Create OpenSearch Serverless collection for Bedrock Knowledge Base.
    
    Returns:
        dict: Collection creation response with ARN
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    
    try:
        # Create policies first
        create_encryption_policy()
        create_network_policy()
        create_data_access_policy()
        
        # Wait a bit for policies to propagate
        time.sleep(5)
        
        # Create collection
        response = aoss_client.create_collection(
            name=collection_name,
            type="VECTORSEARCH",
            description="Vector store for incident response knowledge base"
        )
        
        collection_id = response["createCollectionDetail"]["id"]
        collection_arn = response["createCollectionDetail"]["arn"]
        
        logger.info(f"Created OpenSearch Serverless collection: {collection_name}")
        logger.info(f"Collection ID: {collection_id}")
        logger.info(f"Collection ARN: {collection_arn}")
        
        # Wait for collection to become active
        logger.info("Waiting for collection to become active...")
        waiter_attempts = 0
        max_attempts = 60  # 5 minutes
        
        while waiter_attempts < max_attempts:
            try:
                status_response = aoss_client.batch_get_collection(
                    ids=[collection_id]
                )
                if status_response["collectionDetails"]:
                    status = status_response["collectionDetails"][0]["status"]
                    if status == "ACTIVE":
                        logger.info("Collection is now active")
                        break
                    elif status == "FAILED":
                        raise Exception("Collection creation failed")
                    else:
                        logger.info(f"Collection status: {status}, waiting...")
                        time.sleep(5)
                        waiter_attempts += 1
            except Exception as e:
                logger.warning(f"Error checking collection status: {e}")
                time.sleep(5)
                waiter_attempts += 1
        
        if waiter_attempts >= max_attempts:
            logger.warning("Collection may not be active yet, but continuing...")
        
        return response
        
    except ClientError as e:
        if "ConflictException" in str(e) or "already exists" in str(e):
            logger.info(f"Collection {collection_name} already exists")
            # Get existing collection ARN
            try:
                collections = aoss_client.list_collections(
                    collectionFilters={"name": collection_name}
                )
                if collections["collectionSummaries"]:
                    collection_arn = collections["collectionSummaries"][0]["arn"]
                    collection_id = collections["collectionSummaries"][0]["id"]
                    return {
                        "createCollectionDetail": {
                            "id": collection_id,
                            "arn": collection_arn,
                            "name": collection_name
                        }
                    }
            except Exception as list_error:
                logger.error(f"Error listing collections: {list_error}")
            raise
        else:
            logger.error(f"Error creating collection: {e}")
            raise


def get_collection_arn() -> str:
    """
    Get the ARN of the OpenSearch Serverless collection.
    
    Returns:
        str: Collection ARN
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    
    try:
        collections = aoss_client.list_collections(
            collectionFilters={"name": collection_name}
        )
        if collections["collectionSummaries"]:
            return collections["collectionSummaries"][0]["arn"]
        else:
            raise ValueError(f"Collection {collection_name} not found")
    except ClientError as e:
        logger.error(f"Error getting collection ARN: {e}")
        raise


def verify_collection_exists() -> bool:
    """
    Verify that the OpenSearch Serverless collection exists.
    
    Returns:
        bool: True if collection exists, False otherwise
    """
    aoss_client = create_boto3_client("opensearchserverless")
    collection_name = get_collection_name()
    
    try:
        collections = aoss_client.list_collections(
            collectionFilters={"name": collection_name}
        )
        return len(collections["collectionSummaries"]) > 0
    except ClientError:
        return False
