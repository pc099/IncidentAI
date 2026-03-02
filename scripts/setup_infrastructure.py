#!/usr/bin/env python3
"""
Main infrastructure setup script.

This script sets up all AWS resources required for the Incident Response System:
- S3 bucket for log storage
- DynamoDB table for incident history
- SES email identity verification
- IAM roles with least-privilege permissions
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from infrastructure.setup_s3 import (
    create_log_bucket, 
    verify_bucket_exists,
    create_kb_data_source_bucket,
    verify_kb_bucket_exists
)
from infrastructure.setup_dynamodb import create_incident_table, verify_table_exists
from infrastructure.setup_ses import verify_email_identity, check_verification_status
from infrastructure.setup_iam import (
    create_lambda_execution_role,
    create_orchestrator_role,
    get_role_arn
)
from infrastructure.setup_bedrock_kb import (
    setup_knowledge_base,
    verify_knowledge_base_exists
)
from aws_lambda_powertools import Logger

logger = Logger()


def setup_all():
    """Run all infrastructure setup steps."""
    print("=" * 60)
    print("Incident Response System - Infrastructure Setup")
    print("=" * 60)
    print()
    
    # Step 1: Create S3 bucket
    print("Step 1: Setting up S3 bucket for log storage...")
    try:
        if not verify_bucket_exists():
            create_log_bucket()
            print("✓ S3 bucket created successfully")
        else:
            print("✓ S3 bucket already exists")
    except Exception as e:
        print(f"✗ Error setting up S3 bucket: {e}")
        return False
    print()
    
    # Step 1.5: Create S3 bucket for Knowledge Base data source
    print("Step 1.5: Setting up S3 bucket for Knowledge Base data source...")
    try:
        if not verify_kb_bucket_exists():
            create_kb_data_source_bucket()
            print("✓ Knowledge Base S3 bucket created successfully")
        else:
            print("✓ Knowledge Base S3 bucket already exists")
    except Exception as e:
        print(f"✗ Error setting up Knowledge Base S3 bucket: {e}")
        return False
    print()
    
    # Step 2: Create DynamoDB table
    print("Step 2: Setting up DynamoDB table for incident history...")
    try:
        if not verify_table_exists():
            create_incident_table()
            print("✓ DynamoDB table created successfully")
        else:
            print("✓ DynamoDB table already exists")
    except Exception as e:
        print(f"✗ Error setting up DynamoDB table: {e}")
        return False
    print()
    
    # Step 3: Verify SES email identity
    print("Step 3: Setting up SES email identity...")
    try:
        verify_email_identity()
        print("✓ Verification email sent")
        print("  Please check your inbox and click the verification link")
        print("  Run 'python scripts/check_ses_status.py' to check verification status")
    except Exception as e:
        print(f"✗ Error setting up SES: {e}")
        return False
    print()
    
    # Step 4: Create IAM roles
    print("Step 4: Setting up IAM roles...")
    try:
        create_lambda_execution_role()
        print("✓ Lambda execution role created")
        
        create_orchestrator_role()
        print("✓ Orchestrator role created")
    except Exception as e:
        print(f"✗ Error setting up IAM roles: {e}")
        return False
    print()
    
    # Step 5: Set up Bedrock Knowledge Base
    print("Step 5: Setting up Bedrock Knowledge Base...")
    try:
        if not verify_knowledge_base_exists():
            kb_result = setup_knowledge_base()
            print(f"✓ Knowledge Base created: {kb_result['knowledgeBaseId']}")
            print(f"  Name: {kb_result['knowledgeBaseName']}")
            print(f"  Data source bucket: {kb_result['bucketName']}")
            print(f"  Data source ID: {kb_result['dataSourceId']}")
            print(f"  Configuration:")
            print(f"    • Embedding Model: Amazon Titan Embeddings (1536 dimensions)")
            print(f"    • Vector Search: Top 5 results, 0.6 similarity threshold")
            print(f"    • Hybrid Search: Semantic + keyword enabled")
            print(f"    • Storage: OpenSearch Serverless (auto-managed)")
        else:
            print("✓ Knowledge Base already exists")
            print(f"  Configuration:")
            print(f"    • Embedding Model: Amazon Titan Embeddings (1536 dimensions)")
            print(f"    • Vector Search: Top 5 results, 0.6 similarity threshold")
            print(f"    • Hybrid Search: Semantic + keyword enabled")
    except Exception as e:
        print(f"✗ Error setting up Knowledge Base: {e}")
        print("  Note: Ensure AWS_ACCOUNT_ID environment variable is set")
        return False
    print()
    
    print("=" * 60)
    print("Infrastructure setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify SES email identity by clicking the link in your inbox")
    print("2. Configure AWS credentials if not already done")
    print("3. Set environment variables:")
    print("   - AWS_REGION (default: us-east-1)")
    print("   - AWS_ACCOUNT_ID (your AWS account ID)")
    print("   - LOG_BUCKET_NAME (default: incident-response-logs)")
    print()
    
    return True


if __name__ == "__main__":
    success = setup_all()
    sys.exit(0 if success else 1)
