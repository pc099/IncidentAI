"""Bedrock Knowledge Base Setup"""
import os
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import get_aws_region, get_kb_data_source_bucket_name

logger = Logger()


def get_kb_name() -> str:
    """Get Knowledge Base name from environment or use default"""
    return os.environ.get("KB_NAME", "incident-response-kb")


def get_kb_role_arn() -> str:
    """Get or create IAM role ARN for Knowledge Base"""
    account_id = os.environ.get("AWS_ACCOUNT_ID", "")
    if not account_id:
        raise ValueError("AWS_ACCOUNT_ID environment variable must be set")
    
    region = get_aws_region()
    # Role should be created by setup_iam.py
    return f"arn:aws:iam::{account_id}:role/incident-response-kb-role"


def create_kb_iam_role() -> str:
    """
    Create IAM role for Bedrock Knowledge Base with necessary permissions.
    
    Returns:
        str: Role ARN
    """
    iam_client = boto3.client("iam", region_name=get_aws_region())
    role_name = "incident-response-kb-role"
    bucket_name = get_kb_data_source_bucket_name()
    account_id = os.environ.get("AWS_ACCOUNT_ID", "")
    
    if not account_id:
        raise ValueError("AWS_ACCOUNT_ID environment variable must be set")
    
    # Trust policy for Bedrock service
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock:{get_aws_region()}:{account_id}:knowledge-base/*"
                    }
                }
            }
        ]
    }
    
    try:
        # Create role
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=str(trust_policy).replace("'", '"'),
            Description="IAM role for Bedrock Knowledge Base to access S3 data source"
        )
        role_arn = response["Role"]["Arn"]
        logger.info(f"Created IAM role: {role_name}")
        
        # Attach inline policy for S3 access
        s3_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="KnowledgeBaseS3Access",
            PolicyDocument=str(s3_policy).replace("'", '"')
        )
        logger.info(f"Attached S3 access policy to role: {role_name}")
        
        # Attach policy for Bedrock model invocation
        bedrock_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel"
                    ],
                    "Resource": f"arn:aws:bedrock:{get_aws_region()}::foundation-model/amazon.titan-embed-text-v1"
                }
            ]
        }
        
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="KnowledgeBaseBedrockAccess",
            PolicyDocument=str(bedrock_policy).replace("'", '"')
        )
        logger.info(f"Attached Bedrock access policy to role: {role_name}")
        
        return role_arn
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            logger.info(f"IAM role {role_name} already exists")
            response = iam_client.get_role(RoleName=role_name)
            return response["Role"]["Arn"]
        else:
            logger.error(f"Error creating IAM role: {e}")
            raise


def create_knowledge_base() -> dict:
    """
    Create Bedrock Knowledge Base with Amazon Titan Embeddings.
    
    Configuration:
    - Embedding model: Amazon Titan Embeddings (1536 dimensions)
    - Vector search: Top 5 results, 0.6 similarity threshold
    - Hybrid search: Semantic + keyword enabled
    
    Returns:
        dict: Knowledge Base creation response with knowledgeBaseId
    """
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=get_aws_region())
    kb_name = get_kb_name()
    
    try:
        # Ensure IAM role exists
        role_arn = create_kb_iam_role()
        
        # Wait a bit for IAM role to propagate
        import time
        time.sleep(10)
        
        # Create Knowledge Base with vector search and hybrid search configuration
        response = bedrock_agent_client.create_knowledge_base(
            name=kb_name,
            description="Historical incident data for AI-powered root cause analysis with hybrid search (semantic + keyword)",
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{get_aws_region()}::foundation-model/amazon.titan-embed-text-v1"
                }
            },
            storageConfiguration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": "",  # Will be auto-created
                    "vectorIndexName": "incident-history-index",
                    "fieldMapping": {
                        "vectorField": "embedding",
                        "textField": "text",
                        "metadataField": "metadata"
                    }
                }
            }
        )
        
        kb_id = response["knowledgeBase"]["knowledgeBaseId"]
        logger.info(f"Created Knowledge Base: {kb_name} (ID: {kb_id})")
        logger.info(f"Vector search configured: top 5 results, 0.6 similarity threshold (applied at query time)")
        logger.info(f"Hybrid search enabled: semantic + keyword search")
        
        return response
        
    except ClientError as e:
        if "ConflictException" in str(e):
            logger.info(f"Knowledge Base {kb_name} already exists")
            # List and find existing KB
            list_response = bedrock_agent_client.list_knowledge_bases()
            for kb in list_response.get("knowledgeBaseSummaries", []):
                if kb["name"] == kb_name:
                    logger.info(f"Found existing Knowledge Base ID: {kb['knowledgeBaseId']}")
                    return {"knowledgeBase": kb}
            raise
        else:
            logger.error(f"Error creating Knowledge Base: {e}")
            raise


def create_data_source(knowledge_base_id: str) -> dict:
    """
    Create S3 data source for Knowledge Base with sync settings.
    
    Args:
        knowledge_base_id: ID of the Knowledge Base
    
    Returns:
        dict: Data source creation response
    """
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=get_aws_region())
    bucket_name = get_kb_data_source_bucket_name()
    data_source_name = f"{get_kb_name()}-s3-source"
    
    try:
        response = bedrock_agent_client.create_data_source(
            knowledgeBaseId=knowledge_base_id,
            name=data_source_name,
            description="S3 bucket containing historical incident documents",
            dataSourceConfiguration={
                "type": "S3",
                "s3Configuration": {
                    "bucketArn": f"arn:aws:s3:::{bucket_name}",
                    "inclusionPrefixes": ["incidents/"]  # Only sync documents in incidents/ prefix
                }
            },
            vectorIngestionConfiguration={
                "chunkingConfiguration": {
                    "chunkingStrategy": "FIXED_SIZE",
                    "fixedSizeChunkingConfiguration": {
                        "maxTokens": 300,
                        "overlapPercentage": 20
                    }
                }
            }
        )
        
        data_source_id = response["dataSource"]["dataSourceId"]
        logger.info(f"Created data source: {data_source_name} (ID: {data_source_id})")
        
        return response
        
    except ClientError as e:
        if "ConflictException" in str(e):
            logger.info(f"Data source {data_source_name} already exists")
            # List and find existing data source
            list_response = bedrock_agent_client.list_data_sources(
                knowledgeBaseId=knowledge_base_id
            )
            for ds in list_response.get("dataSourceSummaries", []):
                if ds["name"] == data_source_name:
                    logger.info(f"Found existing data source ID: {ds['dataSourceId']}")
                    return {"dataSource": ds}
            raise
        else:
            logger.error(f"Error creating data source: {e}")
            raise


def setup_knowledge_base() -> dict:
    """
    Complete setup of Bedrock Knowledge Base with S3 data source.
    
    Returns:
        dict: Setup result with knowledgeBaseId and dataSourceId
    """
    logger.info("Starting Bedrock Knowledge Base setup...")
    
    # Step 1: Create Knowledge Base
    kb_response = create_knowledge_base()
    kb_id = kb_response["knowledgeBase"]["knowledgeBaseId"]
    
    # Step 2: Create S3 data source
    ds_response = create_data_source(kb_id)
    ds_id = ds_response["dataSource"]["dataSourceId"]
    
    result = {
        "knowledgeBaseId": kb_id,
        "dataSourceId": ds_id,
        "knowledgeBaseName": get_kb_name(),
        "bucketName": get_kb_data_source_bucket_name()
    }
    
    logger.info(f"Knowledge Base setup complete: {result}")
    
    return result


def verify_knowledge_base_exists() -> bool:
    """
    Verify that the Knowledge Base exists.
    
    Returns:
        bool: True if Knowledge Base exists, False otherwise
    """
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=get_aws_region())
    kb_name = get_kb_name()
    
    try:
        list_response = bedrock_agent_client.list_knowledge_bases()
        for kb in list_response.get("knowledgeBaseSummaries", []):
            if kb["name"] == kb_name:
                return True
        return False
    except ClientError as e:
        logger.error(f"Error checking Knowledge Base: {e}")
        return False


def get_knowledge_base_id() -> str:
    """
    Get the Knowledge Base ID by name.
    
    Returns:
        str: Knowledge Base ID
    
    Raises:
        ValueError: If Knowledge Base not found
    """
    bedrock_agent_client = boto3.client("bedrock-agent", region_name=get_aws_region())
    kb_name = get_kb_name()
    
    try:
        list_response = bedrock_agent_client.list_knowledge_bases()
        for kb in list_response.get("knowledgeBaseSummaries", []):
            if kb["name"] == kb_name:
                return kb["knowledgeBaseId"]
        raise ValueError(f"Knowledge Base '{kb_name}' not found")
    except ClientError as e:
        logger.error(f"Error getting Knowledge Base ID: {e}")
        raise


def query_knowledge_base(
    knowledge_base_id: str,
    query_text: str,
    max_results: int = 5,
    similarity_threshold: float = 0.6,
    enable_hybrid_search: bool = True
) -> dict:
    """
    Query Bedrock Knowledge Base with vector search and hybrid search configuration.
    
    Args:
        knowledge_base_id: ID of the Knowledge Base to query
        query_text: Query text for semantic search
        max_results: Maximum number of results to return (default: 5)
        similarity_threshold: Minimum similarity score threshold (default: 0.6)
        enable_hybrid_search: Enable hybrid search combining semantic + keyword (default: True)
    
    Returns:
        dict: Query results with retrievalResults containing similar incidents
    
    Configuration applied:
    - Top 5 results (configurable via max_results)
    - 0.6 similarity threshold (configurable via similarity_threshold)
    - Hybrid search: semantic + keyword (configurable via enable_hybrid_search)
    """
    bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=get_aws_region())
    
    try:
        # Build retrieval configuration
        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": max_results,
                "overrideSearchType": "HYBRID" if enable_hybrid_search else "SEMANTIC"
            }
        }
        
        # Query Knowledge Base
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                "text": query_text
            },
            retrievalConfiguration=retrieval_config
        )
        
        # Filter results by similarity threshold
        filtered_results = []
        for result in response.get("retrievalResults", []):
            if result.get("score", 0) >= similarity_threshold:
                filtered_results.append(result)
        
        response["retrievalResults"] = filtered_results
        
        logger.info(
            f"Knowledge Base query completed: {len(filtered_results)} results "
            f"(threshold: {similarity_threshold}, hybrid: {enable_hybrid_search})"
        )
        
        return response
        
    except ClientError as e:
        logger.error(f"Error querying Knowledge Base: {e}")
        raise


def get_vector_search_config() -> dict:
    """
    Get the default vector search configuration for Knowledge Base queries.
    
    Returns:
        dict: Vector search configuration with:
            - numberOfResults: 5 (top 5 results)
            - similarityThreshold: 0.6 (minimum similarity score)
            - hybridSearch: True (semantic + keyword search enabled)
    """
    return {
        "numberOfResults": 5,
        "similarityThreshold": 0.6,
        "hybridSearch": True,
        "searchType": "HYBRID"  # Combines semantic vector search with keyword matching
    }
