# Sample Historical Incidents for Knowledge Base

## Overview

This document describes the 15 sample historical incidents created for populating the Bedrock Knowledge Base. These incidents cover three main failure categories and include AWS-native scenarios as specified in the requirements.

## Incident Categories

### Configuration Errors (5 incidents)

1. **inc-2024-11-01-001**: Lambda environment variable misconfiguration
   - Missing DATABASE_URL environment variable
   - Resolution: Added environment variable via AWS CLI
   - Time to Resolution: 5 minutes

2. **inc-2024-11-05-002**: API Gateway timeout configuration too low
   - Timeout set to 3s but Lambda needs 5-8s
   - Resolution: Increased integration timeout to 15s
   - Time to Resolution: 3 minutes

3. **inc-2024-11-10-003**: IAM role missing required permissions
   - Lambda unable to write to DynamoDB
   - Resolution: Added DynamoDB write permissions to IAM role
   - Time to Resolution: 8 minutes

4. **inc-2024-11-15-004**: Step Functions state machine invalid JSON path
   - Invalid JSONPath expression in state definition
   - Resolution: Corrected JSONPath syntax
   - Time to Resolution: 12 minutes

5. **inc-2024-11-20-005**: SES email identity not verified
   - Attempted to send from unverified domain
   - Resolution: Verified domain in SES with DNS records
   - Time to Resolution: 25 minutes

### Resource Exhaustion (5 incidents)

6. **inc-2024-11-23-006**: Lambda memory exhaustion
   - Function configured with 512MB but needed 1024MB
   - Resolution: Increased memory allocation to 1536MB
   - Time to Resolution: 4 minutes

7. **inc-2024-11-25-007**: DynamoDB read capacity throttling
   - Table provisioned with 100 RCU but received 500+ requests/sec
   - Resolution: Enabled auto-scaling (100-1000 RCU)
   - Time to Resolution: 6 minutes

8. **inc-2024-11-28-008**: RDS storage full
   - Database reached 100% of 100GB allocated storage
   - Resolution: Increased storage to 200GB and enabled auto-scaling
   - Time to Resolution: 15 minutes

9. **inc-2024-12-02-009**: Lambda concurrent execution limit reached
   - Hit account-level limit of 1000 concurrent executions
   - Resolution: Requested limit increase to 3000 via AWS Support
   - Time to Resolution: 2 hours

10. **inc-2024-12-05-010**: DynamoDB write capacity throttling
    - Batch writes exceeded provisioned 100 WCU
    - Resolution: Switched to on-demand billing mode
    - Time to Resolution: 10 minutes

### Dependency Failures (5 incidents)

11. **inc-2024-12-08-011**: External payment gateway timeout
    - 15 consecutive timeout errors to external API
    - Resolution: Increased timeout to 30s, added retry logic and circuit breaker
    - Time to Resolution: 20 minutes

12. **inc-2024-12-12-012**: RDS database connection pool exhaustion
    - All 100 database connections exhausted
    - Resolution: Implemented RDS Proxy for connection pooling
    - Time to Resolution: 30 minutes

13. **inc-2024-12-15-013**: Third-party API rate limiting
    - Exceeded 100 requests/minute limit
    - Resolution: Added Redis cache and token bucket rate limiter
    - Time to Resolution: 45 minutes

14. **inc-2024-12-18-014**: SNS topic delivery failure
    - HTTP/S endpoint subscriber was down
    - Resolution: Implemented SQS dead-letter queue and retry Lambda
    - Time to Resolution: 25 minutes

15. **inc-2024-12-20-015**: S3 eventual consistency delay
    - Read-after-write failures due to timing
    - Resolution: Added retry logic with exponential backoff
    - Time to Resolution: 15 minutes

## AWS Services Covered

The sample incidents cover the following AWS services as required:

- **Lambda**: Deployment failures, memory exhaustion, concurrency limits, IAM permissions
- **DynamoDB**: Read/write throttling, capacity planning, auto-scaling
- **RDS**: Storage full, connection pool exhaustion, RDS Proxy
- **API Gateway**: Timeout configuration, integration settings
- **Step Functions**: State machine errors, JSONPath issues
- **SES**: Email identity verification
- **SNS**: Delivery failures, dead-letter queues
- **S3**: Consistency issues, retry patterns

## Document Format

Each incident document includes:

1. **Metadata**
   - Incident ID
   - Timestamp
   - Service name
   - Failure type
   - AWS service
   - Category

2. **Root Cause**
   - Clear description of the underlying issue

3. **Description**
   - Detailed explanation of the failure
   - Error patterns and stack traces
   - Resolution commands and steps
   - Time to resolution
   - Confidence score

4. **Resolution Steps**
   - Numbered list of actions taken

5. **Preventive Measures**
   - Recommendations to prevent recurrence

## Usage

### Populate Knowledge Base

Run the population script to upload all 15 incidents:

```bash
python scripts/populate_kb_samples.py
```

This will:
1. Create formatted documents for each incident
2. Upload documents to S3 (incidents/ prefix)
3. Trigger Knowledge Base ingestion job
4. Display progress and summary

### Query Examples

After ingestion completes (5-10 minutes), test queries:

```python
from src.infrastructure.setup_bedrock_kb import query_knowledge_base, get_knowledge_base_id

kb_id = get_knowledge_base_id()

# Query for Lambda deployment failures
response = query_knowledge_base(
    knowledge_base_id=kb_id,
    query_text="Lambda deployment failure timeout error"
)

# Query for DynamoDB throttling
response = query_knowledge_base(
    knowledge_base_id=kb_id,
    query_text="DynamoDB throttling capacity exceeded"
)

# Query for RDS storage issues
response = query_knowledge_base(
    knowledge_base_id=kb_id,
    query_text="RDS storage full database error"
)
```

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 3.5**: Historical incident data for RAG-powered root cause analysis
- **Requirement 3.6**: Similar past incidents with resolutions
- **Requirement 11.1**: Configuration error scenarios (5 incidents)
- **Requirement 11.2**: Resource exhaustion scenarios (5 incidents)
- **Requirement 11.3**: Dependency failure scenarios (5 incidents)

## Next Steps

1. Wait for ingestion job to complete (5-10 minutes)
2. Run `python scripts/test_kb_query.py` to verify ingestion
3. Proceed to Task 7: Implement Root Cause Agent with RAG integration

## Notes

- All incidents are fictional but based on real-world AWS failure patterns
- Confidence scores range from 85% to 100% based on evidence clarity
- Resolution times range from 3 minutes to 2 hours
- Each incident includes specific AWS CLI commands for reproduction
- Documents are optimized for semantic search with clear descriptions and keywords
