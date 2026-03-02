# Configuration Reference

Complete reference for all configuration options in the AI-Powered Incident Response System.

## CloudFormation Parameters

### Environment
- **Type:** String
- **Default:** `dev`
- **Allowed Values:** `dev`, `staging`, `prod`
- **Description:** Environment name used for resource naming and tagging
- **Example:** `prod`

### SenderEmail
- **Type:** String
- **Default:** `incidents@example.com`
- **Description:** Email address for sending incident alerts (must be verified in SES)
- **Requirements:** 
  - Valid email format
  - Must be verified in SES before use
  - Can be a domain (e.g., `@example.com`) if domain is verified
- **Example:** `incidents@mycompany.com`

### OnCallEngineersEmail
- **Type:** String
- **Required:** Yes
- **Description:** Comma-separated list of on-call engineer email addresses
- **Format:** `email1@example.com,email2@example.com`
- **Requirements:**
  - At least one email address
  - All addresses must be verified in SES (if in sandbox mode)
- **Example:** `oncall@mycompany.com,engineer1@mycompany.com,engineer2@mycompany.com`

### StakeholdersEmail
- **Type:** String
- **Default:** Empty string
- **Description:** Comma-separated list of stakeholder email addresses (optional)
- **Format:** `email1@example.com,email2@example.com`
- **Example:** `cto@mycompany.com,product@mycompany.com`

### BedrockModelId
- **Type:** String
- **Default:** `anthropic.claude-3-sonnet-20240229-v1:0`
- **Description:** Bedrock model ID for Claude
- **Available Models:**
  - `anthropic.claude-3-sonnet-20240229-v1:0` (Recommended - balanced performance/cost)
  - `anthropic.claude-3-haiku-20240307-v1:0` (Faster, lower cost)
  - `anthropic.claude-3-opus-20240229-v1:0` (Highest quality, higher cost)
- **Requirements:** Model access must be enabled in Bedrock console
- **Example:** `anthropic.claude-3-sonnet-20240229-v1:0`

### ApiRateLimit
- **Type:** Number
- **Default:** `100`
- **Description:** API Gateway rate limit in requests per minute
- **Range:** 1-10000
- **Recommendations:**
  - Dev: 100 requests/minute
  - Staging: 200 requests/minute
  - Prod: 500-1000 requests/minute
- **Example:** `500`

## Lambda Environment Variables

### Core Configuration

#### ENVIRONMENT
- **Type:** String
- **Description:** Deployment environment
- **Values:** `dev`, `staging`, `prod`
- **Set By:** CloudFormation parameter
- **Example:** `dev`

#### LOG_BUCKET
- **Type:** String
- **Description:** S3 bucket name for log storage
- **Format:** `incident-logs-{account-id}-{environment}`
- **Set By:** CloudFormation (from S3 bucket resource)
- **Example:** `incident-logs-123456789012-dev`

#### KB_DATA_BUCKET
- **Type:** String
- **Description:** S3 bucket name for Knowledge Base data
- **Format:** `incident-kb-data-{account-id}-{environment}`
- **Set By:** CloudFormation (from S3 bucket resource)
- **Example:** `incident-kb-data-123456789012-dev`

#### DYNAMODB_TABLE
- **Type:** String
- **Description:** DynamoDB table name for incident history
- **Format:** `incident-history-{environment}`
- **Set By:** CloudFormation (from DynamoDB table resource)
- **Example:** `incident-history-dev`

#### KNOWLEDGE_BASE_ID
- **Type:** String
- **Description:** Bedrock Knowledge Base ID
- **Format:** 10-character alphanumeric ID
- **Set By:** Manual (after Knowledge Base creation)
- **Example:** `ABCDEFGHIJ`
- **Note:** Must be set manually after creating Knowledge Base

#### BEDROCK_MODEL_ID
- **Type:** String
- **Description:** Bedrock Claude model ID
- **Set By:** CloudFormation parameter
- **Example:** `anthropic.claude-3-sonnet-20240229-v1:0`

### Email Configuration

#### SENDER_EMAIL
- **Type:** String
- **Description:** SES sender email address
- **Set By:** CloudFormation parameter
- **Requirements:** Must be verified in SES
- **Example:** `incidents@mycompany.com`

#### ONCALL_EMAILS
- **Type:** String (comma-separated)
- **Description:** On-call engineer email addresses
- **Set By:** CloudFormation parameter
- **Example:** `oncall@mycompany.com,engineer@mycompany.com`

#### STAKEHOLDER_EMAILS
- **Type:** String (comma-separated)
- **Description:** Stakeholder email addresses (optional)
- **Set By:** CloudFormation parameter
- **Example:** `cto@mycompany.com,product@mycompany.com`

### Optional Configuration

#### LOG_LEVEL
- **Type:** String
- **Default:** `INFO`
- **Values:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description:** Logging verbosity level
- **Set By:** Manual (via Lambda console or CLI)
- **Example:** `DEBUG`

#### TOKEN_USAGE_LIMIT
- **Type:** Number
- **Default:** `100000` (Free Tier limit)
- **Description:** Maximum Bedrock tokens per month
- **Set By:** Manual (via Lambda console or CLI)
- **Example:** `200000`

#### PROCESSING_TIMEOUT
- **Type:** Number
- **Default:** `300` (5 minutes)
- **Description:** Maximum processing time in seconds
- **Range:** 60-900
- **Set By:** Manual (via Lambda console or CLI)
- **Example:** `600`

## S3 Bucket Configuration

### Log Storage Bucket

**Bucket Name:** `incident-logs-{account-id}-{environment}`

**Lifecycle Policies:**
- Transition to Standard-IA after 30 days
- Delete after 90 days

**Encryption:** AES256 (SSE-S3)

**Versioning:** Enabled

**Public Access:** Blocked

**Path Structure:**
```
s3://incident-logs-{account-id}-{environment}/
  └── {service-name}/
      └── {year}/
          └── {month}/
              └── {day}/
                  └── {hour}-{minute}.log
```

**Example:**
```
s3://incident-logs-123456789012-dev/
  └── payment-processor/
      └── 2025/
          └── 03/
              └── 01/
                  └── 10-30.log
```

### Knowledge Base Data Bucket

**Bucket Name:** `incident-kb-data-{account-id}-{environment}`

**Lifecycle Policies:** None (data retained indefinitely)

**Encryption:** AES256 (SSE-S3)

**Versioning:** Enabled

**Public Access:** Blocked

**Path Structure:**
```
s3://incident-kb-data-{account-id}-{environment}/
  └── incidents/
      └── {incident-id}.json
```

**Example:**
```
s3://incident-kb-data-123456789012-dev/
  └── incidents/
      ├── inc-2025-03-01-001.json
      ├── inc-2025-03-01-002.json
      └── inc-2025-03-02-001.json
```

## DynamoDB Table Configuration

**Table Name:** `incident-history-{environment}`

**Billing Mode:** On-Demand (PAY_PER_REQUEST)

**Primary Key:**
- Partition Key: `incident_id` (String)
- Sort Key: `timestamp` (String)

**Global Secondary Index:**
- Index Name: `service-timestamp-index`
- Partition Key: `service_name` (String)
- Sort Key: `timestamp` (String)
- Projection: ALL

**Time To Live (TTL):**
- Attribute: `ttl`
- Enabled: Yes
- Retention: 90 days

**Encryption:** AWS managed key (SSE)

**Point-in-Time Recovery:** Enabled

**Example Item:**
```json
{
  "incident_id": "inc-2025-03-01-001",
  "timestamp": "2025-03-01T10:30:00Z",
  "service_name": "payment-processor",
  "failure_type": "dependency_failure",
  "root_cause": {
    "category": "dependency_failure",
    "description": "External payment gateway timeout",
    "confidence_score": 85
  },
  "ttl": 1735689000
}
```

## API Gateway Configuration

**API Name:** `incident-response-api-{environment}`

**Endpoint Type:** Regional

**Authentication:** AWS_IAM + API Key

**Rate Limiting:**
- Rate Limit: Configurable (default 100 req/min)
- Burst Limit: Same as rate limit

**Endpoints:**

### POST /incidents
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** API Key (x-api-key header) or AWS_IAM
- **Request Body:**
  ```json
  {
    "service_name": "string (required)",
    "timestamp": "ISO8601 string (required)",
    "error_message": "string (required)",
    "log_location": "S3 URI (required)",
    "alert_source": "string (optional)"
  }
  ```
- **Response (202 Accepted):**
  ```json
  {
    "incident_id": "string",
    "status": "processing",
    "message": "Incident analysis initiated"
  }
  ```
- **Response (400 Bad Request):**
  ```json
  {
    "error": "string",
    "details": "string"
  }
  ```

## Bedrock Knowledge Base Configuration

**Knowledge Base Name:** `incident-history-kb-{environment}`

**Embedding Model:** Amazon Titan Embeddings G1 - Text
- Model ID: `amazon.titan-embed-text-v1`
- Dimensions: 1536

**Vector Store:** OpenSearch Serverless
- Collection Name: `incident-kb-{environment}`
- Index Name: `incident-history-index`
- Vector Field: `embedding`
- Text Field: `text`
- Metadata Field: `metadata`

**Data Source:**
- Type: S3
- Bucket: `incident-kb-data-{account-id}-{environment}`
- Prefix: `incidents/`

**Chunking Configuration:**
- Strategy: Fixed-size
- Max Tokens: 512
- Overlap Percentage: 20%

**Query Configuration:**
- Number of Results: 5
- Similarity Threshold: 0.6 (60%)
- Search Type: Hybrid (semantic + keyword)

## CloudWatch Configuration

### Dashboard

**Dashboard Name:** `IncidentResponse-{environment}`

**Widgets:**
1. Incident Volume (Sum, 5-minute periods)
2. Average Processing Time (Average, 5-minute periods)
3. Average Confidence Score (Average, 5-minute periods)
4. Agent Success Rates (Average by agent, 5-minute periods)
5. Bedrock Token Usage (Sum, 1-hour periods)
6. Recent Errors (Log query, last 20 errors)

### Alarms

#### High Latency Alarm
- **Metric:** ProcessingTime
- **Threshold:** 60 seconds
- **Evaluation Periods:** 1
- **Period:** 5 minutes
- **Statistic:** Average
- **Action:** None (monitoring only)

#### High Error Rate Alarm
- **Metric:** AgentFailureRate
- **Threshold:** 20% (0.2)
- **Evaluation Periods:** 2
- **Period:** 5 minutes
- **Statistic:** Average
- **Action:** None (monitoring only)

#### Token Usage Warning Alarm
- **Metric:** TokenUsagePercentage
- **Threshold:** 80%
- **Evaluation Periods:** 1
- **Period:** 1 hour
- **Statistic:** Maximum
- **Action:** None (monitoring only)

### Custom Metrics

**Namespace:** `IncidentResponse`

**Metrics:**
- `IncidentVolume` - Count of incidents processed
- `ProcessingTime` - Time to process incident (seconds)
- `ConfidenceScore` - Root cause confidence score (0-100)
- `AgentSuccess` - Agent success rate (0-1) by agent name
- `AgentFailureRate` - Agent failure rate (0-1)
- `TokenUsage` - Bedrock tokens consumed
- `TokenUsagePercentage` - Percentage of Free Tier limit used

**Dimensions:**
- `Environment` - Deployment environment
- `Agent` - Agent name (log-analysis, root-cause, fix-recommendation, communication)
- `ServiceName` - Service that failed

## IAM Roles and Permissions

### Lambda Execution Role

**Role Name:** `IncidentResponseLambdaRole-{environment}`

**Managed Policies:**
- `AWSLambdaBasicExecutionRole`

**Inline Policies:**

**S3 Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::incident-logs-*",
    "arn:aws:s3:::incident-logs-*/*",
    "arn:aws:s3:::incident-kb-data-*",
    "arn:aws:s3:::incident-kb-data-*/*"
  ]
}
```

**DynamoDB Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:UpdateItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:*:*:table/incident-history-*",
    "arn:aws:dynamodb:*:*:table/incident-history-*/index/*"
  ]
}
```

**SES Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "ses:SendEmail",
    "ses:SendRawEmail"
  ],
  "Resource": "*"
}
```

**Bedrock Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "bedrock:Retrieve",
    "bedrock:RetrieveAndGenerate"
  ],
  "Resource": "*"
}
```

**CloudWatch Permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "cloudwatch:PutMetricData",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "*"
}
```

### Bedrock Knowledge Base Role

**Role Name:** `BedrockKnowledgeBaseRole-{environment}`

**Inline Policies:**

**S3 Access:**
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::incident-kb-data-*",
    "arn:aws:s3:::incident-kb-data-*/*"
  ]
}
```

## Cost Optimization Settings

### Lambda Configuration
- **Architecture:** ARM64 (Graviton2) - 20% cost savings
- **Memory:** 256 MB (API validation), 1024 MB (orchestrator)
- **Timeout:** 30s (API validation), 300s (orchestrator)

### DynamoDB Configuration
- **Billing Mode:** On-Demand - pay only for what you use
- **No provisioned capacity** - avoid idle costs

### S3 Configuration
- **Lifecycle Policies:**
  - Standard → Standard-IA after 30 days (50% storage cost reduction)
  - Delete after 90 days (zero storage cost)
- **Intelligent-Tiering:** Not used (overhead not worth it for this use case)

### Bedrock Configuration
- **Token Tracking:** Monitor usage to stay within Free Tier
- **Free Tier Limits:**
  - First 3 months: Varies by model
  - Claude Sonnet: ~100K tokens/month free
- **Warning Threshold:** 80% of Free Tier limit

### CloudWatch Configuration
- **Metric Batching:** Batch multiple metrics into single API call
- **Log Retention:** 7 days (configurable)
- **Dashboard:** Single dashboard (no additional cost)

## Security Best Practices

### Encryption
- **At Rest:** All S3 buckets and DynamoDB tables encrypted
- **In Transit:** All API calls use HTTPS/TLS

### Access Control
- **Least Privilege:** IAM roles have minimum required permissions
- **API Authentication:** API Gateway requires API key or IAM auth
- **PII Redaction:** Sensitive data redacted before analysis

### Network Security
- **VPC:** Not required (all services are serverless)
- **Security Groups:** Not applicable
- **Public Access:** All S3 buckets block public access

### Monitoring
- **CloudWatch Logs:** All Lambda invocations logged
- **CloudWatch Metrics:** Performance and error metrics tracked
- **Alarms:** Alerts for high latency and error rates

## Updating Configuration

### Update CloudFormation Parameters

```bash
aws cloudformation update-stack \
    --stack-name incident-response-system-dev \
    --use-previous-template \
    --parameters file://infrastructure/cloudformation/parameters-dev.json \
    --capabilities CAPABILITY_NAMED_IAM
```

### Update Lambda Environment Variables

```bash
aws lambda update-function-configuration \
    --function-name incident-orchestrator-dev \
    --environment "Variables={
        ENVIRONMENT=dev,
        LOG_LEVEL=DEBUG,
        ...
    }"
```

### Update API Rate Limit

```bash
aws apigateway update-usage-plan \
    --usage-plan-id <usage-plan-id> \
    --patch-operations \
        op=replace,path=/throttle/rateLimit,value=200 \
        op=replace,path=/throttle/burstLimit,value=200
```

## Validation

### Validate Configuration

```bash
# Validate CloudFormation template
aws cloudformation validate-template \
    --template-body file://infrastructure/cloudformation/incident-response-system.yaml

# Test API endpoint
curl -X POST "${API_ENDPOINT}" \
    -H "x-api-key: ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d @test-payload.json

# Check Lambda configuration
aws lambda get-function-configuration \
    --function-name incident-orchestrator-dev

# Verify SES identity
aws ses get-identity-verification-attributes \
    --identities incidents@example.com
```

## Troubleshooting Configuration Issues

### Issue: Invalid Parameter Value

**Solution:** Check parameter constraints in CloudFormation template

### Issue: Resource Already Exists

**Solution:** Use unique names or delete existing resources

### Issue: Insufficient Permissions

**Solution:** Verify IAM user/role has required permissions

### Issue: Bedrock Model Not Available

**Solution:** Request model access in Bedrock console

### Issue: SES Email Not Verified

**Solution:** Verify email identity and click verification link

For more troubleshooting, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting).
