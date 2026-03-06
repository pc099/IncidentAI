# AWS Deployment Requirements

Complete guide for deploying the Enhanced AI-Powered Incident Response System on AWS.

## 📋 Table of Contents

1. [AWS Services Required](#aws-services-required)
2. [Environment Variables](#environment-variables)
3. [IAM Permissions](#iam-permissions)
4. [CloudFormation Parameters](#cloudformation-parameters)
5. [Pre-Deployment Setup](#pre-deployment-setup)
6. [Deployment Steps](#deployment-steps)
7. [Post-Deployment Configuration](#post-deployment-configuration)
8. [Cost Estimation](#cost-estimation)

## 🏗️ AWS Services Required

### Core Compute Services
- **AWS Lambda** - Serverless function execution
- **Amazon API Gateway** - REST API endpoints
- **AWS Step Functions** - Orchestration workflows

### AI/ML Services
- **Amazon Bedrock** - LLM inference (Claude 3 Sonnet)
- **Amazon Bedrock Knowledge Base** - RAG capabilities
- **Amazon OpenSearch Serverless** - Vector search for knowledge base

### Storage Services
- **Amazon S3** - Log storage and knowledge base documents
- **Amazon DynamoDB** - Incident tracking and caching
- **Amazon ElastiCache (Redis)** - Semantic caching

### Messaging & Notifications
- **Amazon SES** - Email notifications (fallback)
- **Amazon SNS** - Event notifications
- **Amazon EventBridge** - Event routing

### Security & Monitoring
- **AWS IAM** - Identity and access management
- **Amazon CloudWatch** - Logging and monitoring
- **AWS Secrets Manager** - Secure credential storage

### Networking (Optional)
- **Amazon VPC** - Network isolation
- **AWS PrivateLink** - Secure service connections

## 🔑 Environment Variables

### Required Environment Variables

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_KB_ID=your-knowledge-base-id
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1

# DynamoDB Tables
INCIDENT_TABLE_NAME=enhanced-incident-response-incidents
APPROVAL_REQUESTS_TABLE=enhanced-incident-response-approvals
CACHE_TABLE_NAME=enhanced-incident-response-cache
PLAN_CACHE_TABLE_NAME=enhanced-incident-response-plans

# S3 Buckets
LOG_STORAGE_BUCKET=enhanced-incident-logs-bucket
KB_DOCUMENTS_BUCKET=enhanced-incident-kb-documents
DEPLOYMENT_BUCKET=enhanced-incident-deployment-artifacts

# ElastiCache Configuration
REDIS_HOST=your-elasticache-cluster.cache.amazonaws.com
REDIS_PORT=6379
REDIS_SSL=true

# API Gateway
API_GATEWAY_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
INCIDENT_PROCESSING_STATE_MACHINE_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:enhanced-incident-processing

# Microsoft Teams Integration
TEAMS_WEBHOOK_URL=https://your-org.webhook.office.com/webhookb2/...
TEAMS_APPROVAL_CHANNEL=incident-approvals

# Email Configuration (Fallback)
SES_FROM_EMAIL=incidents@your-domain.com
SES_REPLY_TO_EMAIL=noreply@your-domain.com

# OpenSearch Configuration
OPENSEARCH_ENDPOINT=https://your-collection.us-east-1.aoss.amazonaws.com
OPENSEARCH_INDEX_NAME=incident-knowledge-base

# Security
SECRETS_MANAGER_SECRET_NAME=enhanced-incident-response/config
KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012

# Performance Tuning
LAMBDA_MEMORY_SIZE=1024
LAMBDA_TIMEOUT=300
BEDROCK_MAX_TOKENS=4096
CACHE_TTL_SECONDS=3600
```

### Optional Environment Variables

```bash
# Development/Testing
DEBUG_MODE=false
LOG_LEVEL=INFO
ENABLE_XRAY_TRACING=true

# Cost Optimization
BEDROCK_CACHE_ENABLED=true
SEMANTIC_CACHE_ENABLED=true
PLAN_CACHE_ENABLED=true

# Performance Monitoring
CLOUDWATCH_NAMESPACE=EnhancedIncidentResponse
METRICS_ENABLED=true
DETAILED_MONITORING=true

# Network Configuration (if using VPC)
VPC_ID=vpc-12345678
SUBNET_IDS=subnet-12345678,subnet-87654321
SECURITY_GROUP_ID=sg-12345678
```

## 🔐 IAM Permissions

### Lambda Execution Role Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve",
        "bedrock:RetrieveAndGenerate"
      ],
      "Resource": "arn:aws:bedrock:*:*:knowledge-base/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/enhanced-incident-response-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::enhanced-incident-*",
        "arn:aws:s3:::enhanced-incident-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:StartExecution",
        "states:SendTaskSuccess",
        "states:SendTaskFailure"
      ],
      "Resource": "arn:aws:states:*:*:stateMachine:enhanced-incident-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:*:*:enhanced-incident-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:enhanced-incident-response/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": "arn:aws:aoss:*:*:collection/*"
    }
  ]
}
```

### Bedrock Knowledge Base Service Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": "arn:aws:aoss:*:*:collection/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::enhanced-incident-kb-documents",
        "arn:aws:s3:::enhanced-incident-kb-documents/*"
      ]
    }
  ]
}
```

## ⚙️ CloudFormation Parameters

### Required Parameters

```yaml
Parameters:
  # Environment Configuration
  Environment:
    Type: String
    Default: prod
    AllowedValues: [dev, staging, prod]
    Description: Deployment environment

  # Bedrock Configuration
  BedrockModelId:
    Type: String
    Default: anthropic.claude-3-sonnet-20240229-v1:0
    Description: Bedrock model ID for LLM inference

  BedrockEmbeddingModelId:
    Type: String
    Default: amazon.titan-embed-text-v1
    Description: Bedrock embedding model for knowledge base

  # Teams Integration
  TeamsWebhookUrl:
    Type: String
    NoEcho: true
    Description: Microsoft Teams webhook URL for notifications

  # Email Configuration
  SESFromEmail:
    Type: String
    Description: Email address for SES notifications
    AllowedPattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

  # Performance Configuration
  LambdaMemorySize:
    Type: Number
    Default: 1024
    MinValue: 128
    MaxValue: 10240
    Description: Lambda function memory size in MB

  LambdaTimeout:
    Type: Number
    Default: 300
    MinValue: 30
    MaxValue: 900
    Description: Lambda function timeout in seconds

  # Cache Configuration
  RedisNodeType:
    Type: String
    Default: cache.t3.micro
    AllowedValues: 
      - cache.t3.micro
      - cache.t3.small
      - cache.t3.medium
    Description: ElastiCache Redis node type

  # Monitoring
  EnableDetailedMonitoring:
    Type: String
    Default: true
    AllowedValues: [true, false]
    Description: Enable detailed CloudWatch monitoring

  # Security
  KMSKeyId:
    Type: String
    Description: KMS key ID for encryption (optional)
    Default: ""
```

### Optional Parameters

```yaml
  # Network Configuration
  VpcId:
    Type: String
    Default: ""
    Description: VPC ID for Lambda functions (optional)

  SubnetIds:
    Type: CommaDelimitedList
    Default: ""
    Description: Subnet IDs for Lambda functions (optional)

  # Cost Optimization
  EnableBedrock Caching:
    Type: String
    Default: true
    AllowedValues: [true, false]
    Description: Enable Bedrock prompt caching

  # Development Settings
  DebugMode:
    Type: String
    Default: false
    AllowedValues: [true, false]
    Description: Enable debug logging
```

## 🚀 Pre-Deployment Setup

### 1. AWS CLI Configuration

```bash
# Configure AWS CLI
aws configure set region us-east-1
aws configure set output json

# Verify access
aws sts get-caller-identity
```

### 2. Enable Required AWS Services

```bash
# Enable Bedrock model access
aws bedrock put-model-invocation-logging-configuration \
  --logging-config cloudWatchConfig='{logGroupName="/aws/bedrock/modelinvocations",roleArn="arn:aws:iam::ACCOUNT:role/service-role/AmazonBedrockExecutionRoleForKnowledgeBase"}'

# Enable Bedrock Claude 3 Sonnet
aws bedrock get-foundation-model --model-identifier anthropic.claude-3-sonnet-20240229-v1:0
```

### 3. Create S3 Buckets

```bash
# Create deployment bucket
aws s3 mb s3://enhanced-incident-deployment-artifacts-$(date +%s)

# Create log storage bucket
aws s3 mb s3://enhanced-incident-logs-bucket-$(date +%s)

# Create knowledge base documents bucket
aws s3 mb s3://enhanced-incident-kb-documents-$(date +%s)
```

### 4. Microsoft Teams Setup

1. **Create Teams Webhook:**
   - Go to your Teams channel
   - Click "..." → "Connectors" → "Incoming Webhook"
   - Configure webhook and copy URL

2. **Test Webhook:**
   ```bash
   curl -X POST "YOUR_TEAMS_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"text": "Test message from Enhanced Incident Response System"}'
   ```

## 📦 Deployment Steps

### 1. Deploy Infrastructure

```bash
# Clone repository
git clone <repository-url>
cd enhanced-incident-response

# Make deployment script executable
chmod +x infrastructure/deploy-enhanced.sh

# Deploy with parameters
./infrastructure/deploy-enhanced.sh \
  --environment prod \
  --teams-webhook-url "YOUR_TEAMS_WEBHOOK_URL" \
  --ses-from-email "incidents@your-domain.com" \
  --enable-monitoring true
```

### 2. Alternative: Manual CloudFormation Deployment

```bash
# Package and deploy
aws cloudformation package \
  --template-file infrastructure/cloudformation/enhanced-incident-response.yaml \
  --s3-bucket your-deployment-bucket \
  --output-template-file packaged-template.yaml

aws cloudformation deploy \
  --template-file packaged-template.yaml \
  --stack-name enhanced-incident-response-prod \
  --parameter-overrides \
    Environment=prod \
    TeamsWebhookUrl="YOUR_TEAMS_WEBHOOK_URL" \
    SESFromEmail="incidents@your-domain.com" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
```

### 3. Deploy Lambda Code

```bash
# Package Lambda functions
cd src
zip -r ../lambda-deployment.zip . -x "*.pyc" "__pycache__/*" "tests/*"

# Update Lambda functions
aws lambda update-function-code \
  --function-name enhanced-incident-response-main \
  --zip-file fileb://../lambda-deployment.zip
```

## 🔧 Post-Deployment Configuration

### 1. Configure Bedrock Knowledge Base

```bash
# Create knowledge base
aws bedrock-agent create-knowledge-base \
  --name "enhanced-incident-knowledge-base" \
  --role-arn "arn:aws:iam::ACCOUNT:role/AmazonBedrockExecutionRoleForKnowledgeBase" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "arn:aws:aoss:us-east-1:ACCOUNT:collection/enhanced-incident-kb",
      "vectorIndexName": "incident-knowledge-base",
      "fieldMapping": {
        "vectorField": "vector",
        "textField": "text",
        "metadataField": "metadata"
      }
    }
  }'

# Create data source
aws bedrock-agent create-data-source \
  --knowledge-base-id "YOUR_KB_ID" \
  --name "incident-documents" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::enhanced-incident-kb-documents"
    }
  }'
```

### 2. Upload Sample Knowledge Base Documents

```bash
# Upload sample documents
aws s3 cp test_data/knowledge_base/ s3://enhanced-incident-kb-documents/ --recursive

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id "YOUR_KB_ID" \
  --data-source-id "YOUR_DATA_SOURCE_ID"
```

### 3. Configure SES (if using email notifications)

```bash
# Verify email address
aws ses verify-email-identity --email-address incidents@your-domain.com

# Create configuration set
aws ses create-configuration-set --configuration-set Name=enhanced-incident-response
```

### 4. Test Deployment

```bash
# Test API endpoint
curl -X POST "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/incident" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "test-service",
    "timestamp": "2024-03-04T10:30:00Z",
    "error_message": "Test incident for deployment validation",
    "log_location": "s3://enhanced-incident-logs-bucket/test/",
    "severity": "medium"
  }'
```

## 💰 Cost Estimation

### Monthly Cost Breakdown (Production)

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| **Lambda** | 10,000 invocations, 1GB memory | $20 |
| **Bedrock Claude 3 Sonnet** | 1M input tokens, 100K output tokens | $45 |
| **Bedrock Knowledge Base** | 10K queries | $15 |
| **DynamoDB** | 1M read/write requests | $25 |
| **ElastiCache Redis** | t3.micro instance | $15 |
| **S3** | 100GB storage, 10K requests | $25 |
| **API Gateway** | 100K requests | $35 |
| **Step Functions** | 1K executions | $25 |
| **CloudWatch** | Logs and metrics | $10 |
| **OpenSearch Serverless** | 1 OCU | $700 |
| **SES** | 1K emails | $1 |

**Total Estimated Monthly Cost: ~$916**

### Cost Optimization Tips

1. **Enable Caching:**
   - Bedrock prompt caching: 90% cost reduction on repeated prompts
   - Semantic caching: Reduces Bedrock calls by 60-80%

2. **Right-size Resources:**
   - Use smaller Lambda memory for non-ML tasks
   - Scale ElastiCache based on actual usage

3. **Use Reserved Capacity:**
   - OpenSearch Serverless reserved capacity for predictable workloads

4. **Monitor Usage:**
   - Set up CloudWatch billing alarms
   - Use AWS Cost Explorer for optimization

## 🔍 Validation Checklist

### Pre-Deployment
- [ ] AWS CLI configured with appropriate permissions
- [ ] All required services enabled in target region
- [ ] Teams webhook URL obtained and tested
- [ ] SES email addresses verified
- [ ] S3 buckets created with appropriate policies

### Post-Deployment
- [ ] CloudFormation stack deployed successfully
- [ ] Lambda functions deployed and configured
- [ ] Bedrock Knowledge Base created and populated
- [ ] API Gateway endpoints responding
- [ ] Teams notifications working
- [ ] DynamoDB tables created with correct schemas
- [ ] ElastiCache cluster accessible
- [ ] CloudWatch logs and metrics flowing

### Testing
- [ ] End-to-end incident processing test
- [ ] Teams notification test
- [ ] Confidence routing test
- [ ] Cache performance validation
- [ ] Error handling verification

## 📞 Support and Troubleshooting

### Common Issues

1. **Bedrock Access Denied:**
   - Ensure model access is enabled in Bedrock console
   - Verify IAM permissions for Bedrock service

2. **Teams Webhook Failures:**
   - Validate webhook URL format
   - Check Teams channel permissions

3. **Lambda Timeout:**
   - Increase timeout for complex processing
   - Optimize code for better performance

4. **DynamoDB Throttling:**
   - Increase read/write capacity
   - Implement exponential backoff

### Monitoring and Alerts

Set up CloudWatch alarms for:
- Lambda function errors and duration
- DynamoDB throttling events
- Bedrock API errors
- API Gateway 4xx/5xx errors
- ElastiCache connection failures

### Log Locations

- **Lambda Logs:** `/aws/lambda/enhanced-incident-response-*`
- **API Gateway Logs:** `/aws/apigateway/enhanced-incident-response`
- **Step Functions Logs:** `/aws/stepfunctions/enhanced-incident-processing`

---

For additional support, refer to the [DEPLOYMENT_VALIDATION.md](DEPLOYMENT_VALIDATION.md) and [EVENT_FLOW_GUIDE.md](EVENT_FLOW_GUIDE.md) documentation.