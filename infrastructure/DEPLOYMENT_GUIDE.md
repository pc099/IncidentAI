# Deployment Guide: AI-Powered Incident Response System

This guide provides step-by-step instructions for deploying the AI-Powered Incident Response System to AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Setup](#pre-deployment-setup)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Testing the Deployment](#testing-the-deployment)
6. [Troubleshooting](#troubleshooting)
7. [Teardown](#teardown)

## Prerequisites

### Required Software

- **AWS CLI** (version 2.x or later)
  - Installation: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
  - Verify: `aws --version`

- **Python 3.11 or later**
  - Installation: https://www.python.org/downloads/
  - Verify: `python3 --version` or `python --version`

- **pip** (Python package manager)
  - Usually included with Python
  - Verify: `pip3 --version` or `pip --version`

- **zip utility** (Linux/Mac) or built-in compression (Windows)
  - Linux: `sudo apt-get install zip` or `sudo yum install zip`
  - Mac: Pre-installed
  - Windows: Built-in

### AWS Account Requirements

1. **AWS Account** with appropriate permissions:
   - CloudFormation: Full access
   - Lambda: Full access
   - API Gateway: Full access
   - S3: Full access
   - DynamoDB: Full access
   - SES: Full access
   - Bedrock: Model access and Knowledge Base access
   - IAM: Role creation and policy management
   - CloudWatch: Logs, Metrics, and Dashboard access

2. **AWS Bedrock Access**:
   - Request access to Claude models in your AWS region
   - Go to AWS Console → Bedrock → Model access
   - Request access to: `anthropic.claude-3-sonnet-20240229-v1:0`
   - Request access to: `amazon.titan-embed-text-v1` (for embeddings)
   - Access approval typically takes a few minutes

3. **AWS Free Tier Eligibility** (optional but recommended for cost savings):
   - New AWS accounts get 12 months of Free Tier benefits
   - Check your Free Tier status: https://console.aws.amazon.com/billing/home#/freetier

### AWS Credentials Configuration

Configure AWS credentials using one of these methods:

**Method 1: AWS CLI Configuration**
```bash
aws configure
```
Provide:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (e.g., `json`)

**Method 2: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

**Method 3: IAM Role (for EC2/ECS deployments)**
- Attach an IAM role with required permissions to your compute instance

Verify credentials:
```bash
aws sts get-caller-identity
```

## Pre-Deployment Setup

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd incident-response-system
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Deployment Parameters

Edit the parameter file for your environment:

**For Development:**
```bash
nano infrastructure/cloudformation/parameters-dev.json
```

**For Production:**
```bash
nano infrastructure/cloudformation/parameters-prod.json
```

Update the following values:

```json
[
  {
    "ParameterKey": "SenderEmail",
    "ParameterValue": "incidents@yourdomain.com"
  },
  {
    "ParameterKey": "OnCallEngineersEmail",
    "ParameterValue": "oncall@yourdomain.com,engineer2@yourdomain.com"
  },
  {
    "ParameterKey": "StakeholdersEmail",
    "ParameterValue": "stakeholders@yourdomain.com"
  }
]
```

**Important:** Use real email addresses that you have access to for SES verification.

### 4. Verify SES Sandbox Status (Optional)

If your AWS account is in SES sandbox mode:
- You can only send emails to verified addresses
- You can verify up to 200 email addresses
- To send to any address, request production access: https://console.aws.amazon.com/ses/home#/account

## Deployment Steps

### Option 1: Automated Deployment (Recommended)

**Linux/Mac:**
```bash
cd infrastructure
chmod +x deploy.sh
./deploy.sh dev
```

**Windows (PowerShell):**
```powershell
cd infrastructure
.\deploy.ps1 -Environment dev
```

The script will:
1. Check prerequisites
2. Create deployment S3 bucket
3. Package Lambda functions
4. Upload packages to S3
5. Deploy CloudFormation stack
6. Verify SES email identity
7. Upload sample data
8. Run smoke tests
9. Display deployment information

### Option 2: Manual Deployment

#### Step 1: Create Deployment Bucket

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
DEPLOYMENT_BUCKET="incident-response-deployment-${ACCOUNT_ID}"
aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region us-east-1
```

#### Step 2: Package Lambda Functions

```bash
# Package API Validation Lambda
cd src
zip -r ../lambda-packages/dev/api-validation.zip \
    api/__init__.py \
    api/incident_validator.py \
    __init__.py
cd ..

# Package Orchestrator Lambda
mkdir -p temp-lambda
cp -r src/* temp-lambda/
pip install -r requirements.txt -t temp-lambda/
cd temp-lambda
zip -r ../lambda-packages/dev/orchestrator.zip . -x "*.pyc" "*__pycache__*"
cd ..
rm -rf temp-lambda
```

#### Step 3: Upload Lambda Packages

```bash
aws s3 cp lambda-packages/dev/api-validation.zip \
    "s3://${DEPLOYMENT_BUCKET}/lambda-packages/dev/api-validation.zip"

aws s3 cp lambda-packages/dev/orchestrator.zip \
    "s3://${DEPLOYMENT_BUCKET}/lambda-packages/dev/orchestrator.zip"
```

#### Step 4: Deploy CloudFormation Stack

```bash
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/incident-response-system.yaml \
    --stack-name incident-response-system-dev \
    --parameter-overrides file://infrastructure/cloudformation/parameters-dev.json \
    --capabilities CAPABILITY_NAMED_IAM \
    --region us-east-1
```

#### Step 5: Get Stack Outputs

```bash
aws cloudformation describe-stacks \
    --stack-name incident-response-system-dev \
    --query "Stacks[0].Outputs" \
    --output table
```

## Post-Deployment Configuration

### 1. Verify SES Email Identity

The sender email must be verified before the system can send alerts.

**Verify Email:**
```bash
aws ses verify-email-identity \
    --email-address incidents@yourdomain.com \
    --region us-east-1
```

**Check Verification Status:**
```bash
aws ses get-identity-verification-attributes \
    --identities incidents@yourdomain.com \
    --region us-east-1
```

**Important:** Check your email inbox and click the verification link sent by AWS.

### 2. Set Up Bedrock Knowledge Base

The Knowledge Base requires manual setup as it's not fully supported by CloudFormation.

#### Step 2.1: Create OpenSearch Serverless Collection

```bash
aws opensearchserverless create-collection \
    --name incident-kb-dev \
    --type VECTORSEARCH \
    --region us-east-1
```

Wait for collection to become active:
```bash
aws opensearchserverless batch-get-collection \
    --names incident-kb-dev \
    --region us-east-1
```

#### Step 2.2: Create Knowledge Base via Console

1. Go to AWS Console → Bedrock → Knowledge Bases
2. Click "Create knowledge base"
3. Configure:
   - **Name:** `incident-history-kb-dev`
   - **Description:** Historical incident data for RAG
   - **IAM Role:** Select the role created by CloudFormation (`BedrockKnowledgeBaseRole-dev`)
4. Configure vector store:
   - **Vector database:** OpenSearch Serverless
   - **Collection:** Select `incident-kb-dev`
   - **Vector index name:** `incident-history-index`
   - **Vector field:** `embedding`
   - **Text field:** `text`
   - **Metadata field:** `metadata`
5. Configure embeddings:
   - **Model:** Amazon Titan Embeddings G1 - Text
6. Create knowledge base

#### Step 2.3: Add S3 Data Source

1. In the Knowledge Base, click "Add data source"
2. Configure:
   - **Name:** `incident-s3-datasource-dev`
   - **Data source type:** S3
   - **S3 URI:** Get from CloudFormation outputs (KnowledgeBaseBucketName)
   - **Inclusion prefix:** `incidents/`
3. Configure chunking:
   - **Strategy:** Fixed-size chunking
   - **Max tokens:** 512
   - **Overlap percentage:** 20%
4. Create data source

#### Step 2.4: Sync Data Source

```bash
# Get Knowledge Base ID from console
KB_ID="your-kb-id"
DS_ID="your-datasource-id"

# Start ingestion job
aws bedrock-agent start-ingestion-job \
    --knowledge-base-id $KB_ID \
    --data-source-id $DS_ID \
    --region us-east-1
```

#### Step 2.5: Update Lambda Environment Variables

```bash
# Get Lambda function name from CloudFormation outputs
FUNCTION_NAME="incident-orchestrator-dev"

# Update environment variables
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --environment "Variables={
        KNOWLEDGE_BASE_ID=$KB_ID,
        ENVIRONMENT=dev,
        LOG_BUCKET=<log-bucket-name>,
        KB_DATA_BUCKET=<kb-bucket-name>,
        DYNAMODB_TABLE=incident-history-dev,
        BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,
        SENDER_EMAIL=incidents@yourdomain.com,
        ONCALL_EMAILS=oncall@yourdomain.com,
        STAKEHOLDER_EMAILS=stakeholders@yourdomain.com
    }" \
    --region us-east-1
```

### 3. Upload Sample Incident Data

```bash
# Upload sample incidents to Knowledge Base bucket
aws s3 sync test_data/knowledge_base/ \
    "s3://<kb-bucket-name>/incidents/" \
    --region us-east-1

# Trigger ingestion job
aws bedrock-agent start-ingestion-job \
    --knowledge-base-id $KB_ID \
    --data-source-id $DS_ID \
    --region us-east-1
```

## Testing the Deployment

### 1. Run Verification Script

```bash
python3 scripts/verify_setup.py --environment dev --region us-east-1
```

This script checks:
- S3 buckets are accessible
- DynamoDB table exists
- Lambda functions are deployed
- API Gateway endpoint is reachable
- SES email identity is verified

### 2. Test API Endpoint

Get API endpoint and key from deployment info:
```bash
cat deployment-info-dev.json
```

Test with curl:
```bash
API_ENDPOINT="<your-api-endpoint>"
API_KEY="<your-api-key>"

curl -X POST "${API_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -H "x-api-key: ${API_KEY}" \
    -d '{
        "service_name": "test-service",
        "timestamp": "2025-03-01T10:00:00Z",
        "error_message": "Service health check failed",
        "log_location": "s3://test-logs/service/2025-03-01/10-00.log",
        "alert_source": "Manual"
    }'
```

Expected response:
```json
{
    "incident_id": "inc-2025-03-01-001",
    "status": "processing",
    "message": "Incident analysis initiated"
}
```

### 3. Simulate Incidents

Run the incident simulation script:
```bash
python3 scripts/simulate_incidents.py --environment dev
```

This will:
- Create sample log files in S3
- Trigger incidents via API Gateway
- Verify end-to-end processing
- Check email delivery

### 4. Monitor CloudWatch Dashboard

1. Go to AWS Console → CloudWatch → Dashboards
2. Open dashboard: `IncidentResponse-dev`
3. Verify metrics are being recorded:
   - Incident volume
   - Processing time
   - Confidence scores
   - Agent success rates
   - Token usage

### 5. Check Email Delivery

- Check the on-call engineer email inbox
- Verify HTML-formatted incident alert was received
- Verify alert contains:
  - Root cause analysis
  - Confidence score
  - Immediate action steps
  - Commands to execute
  - Business impact summary

## Configuration Options

### Environment Variables

The Lambda functions use these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `dev`, `staging`, `prod` |
| `LOG_BUCKET` | S3 bucket for logs | `incident-logs-123456789-dev` |
| `KB_DATA_BUCKET` | S3 bucket for KB data | `incident-kb-data-123456789-dev` |
| `DYNAMODB_TABLE` | DynamoDB table name | `incident-history-dev` |
| `KNOWLEDGE_BASE_ID` | Bedrock KB ID | `ABCDEFGHIJ` |
| `BEDROCK_MODEL_ID` | Claude model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `SENDER_EMAIL` | SES sender email | `incidents@example.com` |
| `ONCALL_EMAILS` | On-call engineer emails | `oncall@example.com` |
| `STAKEHOLDER_EMAILS` | Stakeholder emails | `stakeholders@example.com` |

### CloudFormation Parameters

Customize deployment by editing parameter files:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `Environment` | Environment name | `dev` |
| `SenderEmail` | SES sender email | `incidents@example.com` |
| `OnCallEngineersEmail` | On-call emails (comma-separated) | Required |
| `StakeholdersEmail` | Stakeholder emails (comma-separated) | Optional |
| `BedrockModelId` | Claude model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `ApiRateLimit` | API rate limit (req/min) | `100` |

### Cost Optimization Settings

The deployment is configured for AWS Free Tier:

- **Lambda:** ARM64 (Graviton) architecture for cost efficiency
- **DynamoDB:** On-demand billing (no provisioned capacity)
- **S3:** Lifecycle policies (Standard-IA after 30 days, delete after 90 days)
- **Bedrock:** Token usage tracking with warnings at 80% of Free Tier

To monitor costs:
```bash
aws ce get-cost-and-usage \
    --time-period Start=2025-03-01,End=2025-03-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --filter file://cost-filter.json
```

## Troubleshooting

### Common Issues

#### 1. CloudFormation Stack Creation Failed

**Error:** `CREATE_FAILED` status

**Solutions:**
- Check CloudFormation events for specific error:
  ```bash
  aws cloudformation describe-stack-events \
      --stack-name incident-response-system-dev \
      --max-items 10
  ```
- Common causes:
  - Insufficient IAM permissions
  - Resource limits exceeded
  - Invalid parameter values
  - S3 bucket name already exists

#### 2. Lambda Function Timeout

**Error:** Task timed out after 300 seconds

**Solutions:**
- Check CloudWatch Logs for the Lambda function
- Verify Bedrock model access is enabled
- Check network connectivity to AWS services
- Increase Lambda timeout in CloudFormation template

#### 3. SES Email Not Sending

**Error:** Email not received

**Solutions:**
- Verify email identity:
  ```bash
  aws ses get-identity-verification-attributes \
      --identities incidents@yourdomain.com
  ```
- Check SES sandbox status (can only send to verified addresses)
- Check CloudWatch Logs for SES errors
- Verify IAM permissions for SES

#### 4. Bedrock Access Denied

**Error:** `AccessDeniedException` when invoking Bedrock

**Solutions:**
- Request model access in Bedrock console
- Wait for access approval (usually a few minutes)
- Verify IAM role has `bedrock:InvokeModel` permission
- Check model ID is correct for your region

#### 5. Knowledge Base Query Fails

**Error:** Knowledge Base returns no results

**Solutions:**
- Verify Knowledge Base ingestion job completed:
  ```bash
  aws bedrock-agent list-ingestion-jobs \
      --knowledge-base-id $KB_ID \
      --data-source-id $DS_ID
  ```
- Check S3 bucket has data in `incidents/` prefix
- Verify OpenSearch Serverless collection is active
- Re-run ingestion job

### Debug Mode

Enable detailed logging:

```bash
# Update Lambda function
aws lambda update-function-configuration \
    --function-name incident-orchestrator-dev \
    --environment "Variables={...,LOG_LEVEL=DEBUG}"
```

View logs:
```bash
aws logs tail /aws/lambda/incident-orchestrator-dev --follow
```

### Support Resources

- **AWS Documentation:** https://docs.aws.amazon.com/
- **Bedrock Documentation:** https://docs.aws.amazon.com/bedrock/
- **CloudFormation Documentation:** https://docs.aws.amazon.com/cloudformation/
- **AWS Support:** https://console.aws.amazon.com/support/

## Teardown

To remove all deployed resources:

**Linux/Mac:**
```bash
cd infrastructure
chmod +x teardown.sh
./teardown.sh dev
```

**Manual Teardown:**
```bash
# Empty S3 buckets
aws s3 rm s3://incident-logs-<account-id>-dev --recursive
aws s3 rm s3://incident-kb-data-<account-id>-dev --recursive

# Delete CloudFormation stack
aws cloudformation delete-stack \
    --stack-name incident-response-system-dev

# Wait for deletion
aws cloudformation wait stack-delete-complete \
    --stack-name incident-response-system-dev

# Delete Knowledge Base (manual via console)
# Delete OpenSearch Serverless collection (manual via console)
```

**Important:** Bedrock Knowledge Base and OpenSearch Serverless collection must be deleted manually via AWS Console.

## Next Steps

After successful deployment:

1. **Integrate with Monitoring Tools:**
   - Configure CloudWatch alarms to send notifications
   - Integrate with PagerDuty, Slack, or other alerting systems

2. **Add More Incident Data:**
   - Upload historical incidents to Knowledge Base
   - Improve root cause accuracy with more training data

3. **Customize Fix Recommendations:**
   - Add service-specific fix templates
   - Customize remediation steps for your infrastructure

4. **Set Up CI/CD:**
   - Automate deployments with GitHub Actions, GitLab CI, or AWS CodePipeline
   - Implement automated testing before deployment

5. **Monitor Costs:**
   - Set up AWS Budgets to track spending
   - Review CloudWatch metrics for token usage
   - Optimize Lambda memory allocation based on usage

6. **Request Production Access:**
   - Request SES production access to send to any email
   - Request higher Bedrock quotas if needed
   - Review and adjust API rate limits

## Conclusion

You now have a fully deployed AI-Powered Incident Response System! The system will automatically analyze operational failures, identify root causes, and provide actionable remediation steps.

For questions or issues, refer to the troubleshooting section or consult AWS documentation.
