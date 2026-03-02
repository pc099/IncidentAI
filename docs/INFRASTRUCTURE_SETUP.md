# Infrastructure Setup Guide

This guide explains how to set up the AWS infrastructure for the Incident Response System.

## Overview

The infrastructure setup creates the following AWS resources:

1. **S3 Bucket** - Log storage with lifecycle policies
2. **S3 Bucket** - Knowledge Base data source storage
3. **DynamoDB Table** - Incident history with GSI
4. **SES Email Identity** - Email delivery for alerts
5. **IAM Roles** - Least-privilege permissions for Lambda functions
6. **Bedrock Knowledge Base** - RAG-powered historical incident search

## Prerequisites

- AWS Account with administrative access
- AWS CLI installed and configured
- Python 3.11 or higher
- Virtual environment activated

## Setup Steps

### 1. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012  # Your AWS account ID
LOG_BUCKET_NAME=incident-response-logs
KB_DATA_SOURCE_BUCKET_NAME=incident-response-kb-data
KB_NAME=incident-response-kb
```

### 2. Run Infrastructure Setup

```bash
python scripts/setup_infrastructure.py
```

This script will:
- Create S3 bucket with encryption and lifecycle policies
- Create S3 bucket for Knowledge Base data source
- Create DynamoDB table with GSI and TTL
- Send SES verification email
- Create IAM roles with least-privilege permissions
- Create Bedrock Knowledge Base with Amazon Titan Embeddings
- Configure S3 data source for Knowledge Base

### 3. Verify SES Email

Check your email inbox for the SES verification link and click it.

Verify the status:

```bash
python scripts/check_ses_status.py
```

You should see:
```
incidents@example.com: Success
```

## Resource Details

### S3 Bucket

**Name**: `incident-response-logs` (configurable via `LOG_BUCKET_NAME`)

**Features**:
- Versioning enabled
- Server-side encryption (AES256)
- Lifecycle policy:
  - Transition to Standard-IA after 30 days
  - Delete after 90 days

**Purpose**: Store service logs for analysis by the Log Analysis Agent.

### S3 Bucket (Knowledge Base Data Source)

**Name**: `incident-response-kb-data` (configurable via `KB_DATA_SOURCE_BUCKET_NAME`)

**Features**:
- Versioning enabled
- Server-side encryption (AES256)
- Bucket policy for Bedrock access
- Organized with `incidents/` prefix for documents

**Purpose**: Store historical incident documents for Bedrock Knowledge Base ingestion and RAG queries.

### Bedrock Knowledge Base

**Name**: `incident-response-kb` (configurable via `KB_NAME`)

**Configuration**:
- Embedding Model: Amazon Titan Embeddings (1536 dimensions)
- Vector Search: Top 5 results, 0.6 similarity threshold
- Hybrid Search: Semantic + keyword enabled
- Storage: OpenSearch Serverless (auto-managed)
- Chunking: Fixed size (300 tokens, 20% overlap)

**Features**:
- Automatic embedding generation
- Semantic search for similar incidents
- S3 data source with sync capabilities
- IAM role for secure access

**Purpose**: Enable RAG-powered root cause analysis by finding similar historical incidents.

### DynamoDB Table

**Name**: `incident-history`

**Schema**:
- Partition Key: `incident_id` (String)
- Sort Key: `timestamp` (String)
- GSI: `service-timestamp-index`
  - Partition Key: `service_name` (String)
  - Sort Key: `timestamp` (String)

**Features**:
- On-demand billing (cost optimized)
- KMS encryption
- TTL enabled (90 days)

**Purpose**: Store historical incident data for pattern matching and learning.

### SES Email Identity

**Email**: `incidents@example.com` (configurable via `SES_SENDER_EMAIL`)

**Features**:
- DKIM signing (optional)
- Configuration set for tracking
- Bounce and complaint handling

**Purpose**: Send enhanced alert emails to on-call engineers and stakeholders.

### IAM Roles

#### Lambda Execution Role

**Name**: `incident-response-lambda-role`

**Permissions**:
- CloudWatch Logs (write)
- S3 (read from log bucket)
- DynamoDB (read/write to incident table)
- SES (send emails from incidents@*)
- Bedrock (invoke Claude models)
- Bedrock Agent Runtime (invoke agents, retrieve from Knowledge Base)
- CloudWatch Metrics (write to IncidentResponse namespace)

#### Orchestrator Role

**Name**: `incident-response-orchestrator-role`

**Permissions**:
- CloudWatch Logs (write)
- Bedrock Agent (invoke agents)
- Lambda (invoke agent functions)

#### Knowledge Base Role

**Name**: `incident-response-kb-role`

**Permissions**:
- S3 (read from Knowledge Base data source bucket)
- Bedrock (invoke Titan Embeddings model)

**Purpose**: Allow Bedrock Knowledge Base to access S3 documents and generate embeddings.

## Verification

Run the verification script to check all resources:

```bash
python scripts/verify_setup.py
```

## Cost Optimization

The infrastructure is designed to stay within AWS Free Tier limits:

- **S3**: Lifecycle policies reduce storage costs
- **DynamoDB**: On-demand billing, no provisioned capacity
- **SES**: Free Tier includes 62,000 emails/month
- **Lambda**: ARM-based runtime for 20% cost savings
- **Bedrock**: Token usage tracking and limits

## Troubleshooting

### S3 Bucket Already Exists

If the bucket name is taken, change `LOG_BUCKET_NAME` in `.env` to a unique name.

### SES Verification Email Not Received

1. Check spam folder
2. Verify the email address in `.env` is correct
3. Try domain verification instead: `verify_domain_identity()`

### IAM Permission Errors

Ensure your AWS credentials have permissions to:
- Create IAM roles and policies
- Create S3 buckets
- Create DynamoDB tables
- Verify SES identities

### Region-Specific Issues

Some AWS services have regional availability. Ensure:
- Bedrock is available in your region (us-east-1, us-west-2 recommended)
- Bedrock Knowledge Base is available in your region
- SES is out of sandbox mode for production use

### Knowledge Base Creation Errors

If Knowledge Base creation fails:
1. Ensure AWS_ACCOUNT_ID is set correctly
2. Wait 10-15 seconds for IAM role propagation
3. Verify Bedrock service is enabled in your account
4. Check that OpenSearch Serverless is available in your region

## Next Steps

After infrastructure setup:

1. ~~Configure Bedrock Knowledge Base (Task 2)~~ ✓ Complete
2. Populate Knowledge Base with sample incidents (Task 2.3)
3. Implement API Gateway endpoint (Task 3)
4. Deploy Lambda functions
5. Test end-to-end flow

## Cleanup

To remove all infrastructure:

```bash
# Delete S3 buckets (must be empty first)
aws s3 rm s3://incident-response-logs --recursive
aws s3 rb s3://incident-response-logs

aws s3 rm s3://incident-response-kb-data --recursive
aws s3 rb s3://incident-response-kb-data

# Delete DynamoDB table
aws dynamodb delete-table --table-name incident-history

# Delete Knowledge Base (get ID first)
KB_ID=$(aws bedrock-agent list-knowledge-bases --query "knowledgeBaseSummaries[?name=='incident-response-kb'].knowledgeBaseId" --output text)
aws bedrock-agent delete-knowledge-base --knowledge-base-id $KB_ID

# Delete IAM roles
aws iam delete-role --role-name incident-response-lambda-role
aws iam delete-role --role-name incident-response-orchestrator-role
aws iam delete-role --role-name incident-response-kb-role

# Remove SES identity
aws ses delete-identity --identity incidents@example.com
```

## Security Best Practices

1. **Least Privilege**: IAM roles have minimal required permissions
2. **Encryption**: All data encrypted at rest and in transit
3. **Access Control**: API Gateway uses authentication
4. **Audit Logging**: CloudWatch logs all operations
5. **PII Redaction**: Sensitive data removed before analysis

## Support

For issues or questions:
- Check CloudWatch Logs for error details
- Review IAM policy permissions
- Verify AWS service quotas
- Consult AWS documentation for service-specific issues
