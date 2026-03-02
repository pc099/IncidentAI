# Knowledge Base Test Data

This directory contains 15 sample incident documents for testing the Bedrock Knowledge Base RAG functionality. The incidents are organized into three failure categories, with 5 incidents per category.

## Structure

```
knowledge_base/
├── configuration_errors/       (5 incidents)
├── resource_exhaustion/        (5 incidents)
└── dependency_failures/        (5 incidents)
```

## Categories

### Configuration Errors (5 incidents)

1. **lambda_env_variable_missing.json**
   - Missing environment variable in Lambda
   - Confidence: 95%
   - Resolution: Add environment variable to Lambda config

2. **iam_permission_denied.json**
   - Lambda IAM role missing S3 PutObject permission
   - Confidence: 98%
   - Resolution: Add S3 write permission to IAM role

3. **lambda_timeout_config.json**
   - Lambda timeout too low for database operations
   - Confidence: 92%
   - Resolution: Increase timeout from 3s to 10s

4. **api_gateway_integration_timeout.json**
   - API Gateway timeout insufficient for backend processing
   - Confidence: 88%
   - Resolution: Implement async processing pattern

5. **dynamodb_gsi_missing.json**
   - Query using non-indexed attribute causing table scans
   - Confidence: 85%
   - Resolution: Create Global Secondary Index

### Resource Exhaustion (5 incidents)

1. **rds_storage_full.json**
   - RDS storage capacity exhausted
   - Confidence: 97%
   - Resolution: Increase storage and enable auto-scaling

2. **ecs_cpu_throttling.json**
   - ECS task CPU limit insufficient
   - Confidence: 89%
   - Resolution: Increase CPU allocation and enable auto-scaling

3. **dynamodb_throttling_writes.json**
   - DynamoDB write capacity insufficient for traffic spike
   - Confidence: 94%
   - Resolution: Enable auto-scaling

4. **lambda_memory_exceeded.json**
   - Lambda memory limit exceeded during processing
   - Confidence: 96%
   - Resolution: Increase memory from 512 MB to 1024 MB

5. **lambda_concurrent_executions.json**
   - Account-level Lambda concurrency limit reached
   - Confidence: 91%
   - Resolution: Set reserved concurrency and request limit increase

### Dependency Failures (5 incidents)

1. **redis_connection_refused.json**
   - ElastiCache Redis unreachable due to security group issue
   - Confidence: 90%
   - Resolution: Fix security group ingress rules

2. **external_api_timeout.json**
   - External payment gateway experiencing high latency
   - Confidence: 87%
   - Resolution: Implement circuit breaker pattern

3. **rds_connection_pool_exhausted.json**
   - Database connection pool exhausted due to leaks
   - Confidence: 93%
   - Resolution: Fix connection leaks and increase pool size

4. **s3_bucket_access_denied.json**
   - S3 bucket policy blocking Lambda access
   - Confidence: 96%
   - Resolution: Update bucket policy

5. **sqs_queue_not_found.json**
   - SQS queue accidentally deleted
   - Confidence: 99%
   - Resolution: Recreate queue and update configuration

## Document Format

Each incident document contains:

```json
{
  "incident_id": "unique-incident-id",
  "timestamp": "ISO 8601 timestamp",
  "service_name": "affected-service",
  "failure_category": "configuration_error | resource_exhaustion | dependency_failure",
  "root_cause": "detailed root cause description",
  "confidence_score": 0-100,
  "error_message": "actual error message",
  "evidence": ["list", "of", "evidence"],
  "resolution": "how it was resolved",
  "fix_commands": ["aws", "cli", "commands"],
  "time_to_resolution": "human-readable time",
  "preventive_measures": ["future", "prevention", "steps"],
  "similar_incidents": ["related-incident-ids"],
  "tags": ["searchable", "tags"]
}
```

## Usage

### Upload to Knowledge Base

```bash
python scripts/upload_kb_test_data.py
```

This script will:
1. Upload all 15 incident documents to S3 data source bucket
2. Trigger Bedrock Knowledge Base ingestion job
3. Wait for ingestion to complete
4. Display statistics

### Query Knowledge Base

After upload, test RAG queries:

```bash
# Query for Lambda issues
python scripts/test_kb_query.py --query "Lambda timeout error"

# Query for DynamoDB issues
python scripts/test_kb_query.py --query "DynamoDB throttling"

# Query for storage issues
python scripts/test_kb_query.py --query "storage full"
```

### Expected RAG Behavior

When the Root Cause Agent queries the Knowledge Base:

1. **Configuration Error Query**: Should retrieve incidents from `configuration_errors/`
   - Example: "Lambda deployment failed" → retrieves `lambda_timeout_config.json`, `iam_permission_denied.json`

2. **Resource Exhaustion Query**: Should retrieve incidents from `resource_exhaustion/`
   - Example: "DynamoDB throttling" → retrieves `dynamodb_throttling_writes.json`

3. **Dependency Failure Query**: Should retrieve incidents from `dependency_failures/`
   - Example: "Connection timeout" → retrieves `external_api_timeout.json`, `redis_connection_refused.json`

## Requirements Validation

This test data validates:

- **Requirement 3.5**: Knowledge Base stores historical incidents
- **Requirement 3.6**: Similar incidents retrieved via semantic search
- **Requirement 8.1**: Incident records stored with all required fields
- **Requirement 8.3**: Query by service name and failure pattern
- **Requirement 8.4**: Top 5 similar incidents ranked by similarity

## Confidence Score Distribution

- **High Confidence (90-100%)**: 8 incidents
- **Medium Confidence (80-89%)**: 6 incidents
- **Low Confidence (<80%)**: 1 incident

This distribution ensures the system can handle varying confidence levels.

## Testing Scenarios

### Test 1: Exact Match
Query: "Lambda function timeout"
Expected: Retrieve `lambda_timeout_config.json` with high similarity score

### Test 2: Semantic Match
Query: "Database storage issues"
Expected: Retrieve `rds_storage_full.json` even though exact words differ

### Test 3: Category Match
Query: "Configuration problems"
Expected: Retrieve multiple incidents from `configuration_errors/`

### Test 4: Service-Specific Match
Query: "DynamoDB performance issues"
Expected: Retrieve `dynamodb_throttling_writes.json` and `dynamodb_gsi_missing.json`

### Test 5: Cross-Category Match
Query: "Connection failures"
Expected: Retrieve incidents from both `dependency_failures/` and `configuration_errors/`

## Maintenance

To add new test incidents:

1. Create JSON file in appropriate category directory
2. Follow the document format above
3. Run upload script to sync with Knowledge Base
4. Verify retrieval with test queries
