#!/usr/bin/env python3
"""
Populate Bedrock Knowledge Base with sample historical incidents.

This script creates 15 sample incident documents covering:
- Configuration errors (5 incidents)
- Resource exhaustion (5 incidents)
- Dependency failures (5 incidents)

AWS-native scenarios included:
- Lambda deployment failures
- DynamoDB throttling
- RDS storage issues
- API Gateway timeouts
- Step Functions execution failures
"""
import os
import sys
import json
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.aws_config import get_aws_region, get_kb_data_source_bucket_name
from src.infrastructure.setup_bedrock_kb import get_knowledge_base_id
from aws_lambda_powertools import Logger

logger = Logger()


# Sample incident documents
SAMPLE_INCIDENTS = [
    # Configuration Errors (5 incidents)
    {
        "incident_id": "inc-2024-11-01-001",
        "timestamp": "2024-11-01T14:30:00Z",
        "service_name": "payment-processor",
        "failure_type": "configuration_error",
        "root_cause": "Lambda environment variable misconfiguration",
        "description": """
Lambda deployment failure due to missing DATABASE_URL environment variable.
The payment-processor Lambda function failed to start after deployment because
the required DATABASE_URL environment variable was not configured. This caused
all payment processing requests to fail with a 500 Internal Server Error.

Error Pattern: KeyError: 'DATABASE_URL' in function initialization
Stack Trace: File "/var/task/app.py", line 12, in <module>
             db_url = os.environ['DATABASE_URL']

Resolution: Added DATABASE_URL environment variable via AWS Console:
aws lambda update-function-configuration --function-name payment-processor \\
  --environment Variables={DATABASE_URL=postgresql://db.example.com:5432/payments}

Time to Resolution: 5 minutes
Confidence: 95%
""",
        "category": "configuration_error",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Identified missing environment variable in CloudWatch Logs",
            "Added DATABASE_URL to Lambda configuration",
            "Verified function initialization successful"
        ],
        "preventive_measures": [
            "Add environment variable validation in deployment pipeline",
            "Use AWS Systems Manager Parameter Store for configuration"
        ]
    },
    {
        "incident_id": "inc-2024-11-05-002",
        "timestamp": "2024-11-05T09:15:00Z",
        "service_name": "api-gateway-backend",
        "failure_type": "configuration_error",
        "root_cause": "API Gateway timeout configuration too low",
        "description": """
API Gateway timeout errors for backend Lambda integration. Requests to the
backend Lambda function were timing out after 3 seconds, but the Lambda
function typically takes 5-8 seconds to process complex queries.

Error Pattern: 504 Gateway Timeout from API Gateway
CloudWatch Logs: "Task timed out after 3.00 seconds"

Resolution: Increased API Gateway integration timeout to 15 seconds:
aws apigatewayv2 update-integration --api-id abc123 --integration-id xyz789 \\
  --timeout-in-millis 15000

Time to Resolution: 3 minutes
Confidence: 90%
""",
        "category": "configuration_error",
        "aws_service": "API Gateway",
        "resolution_steps": [
            "Analyzed API Gateway access logs",
            "Identified timeout configuration mismatch",
            "Increased integration timeout to 15 seconds"
        ],
        "preventive_measures": [
            "Set timeout based on Lambda function duration metrics",
            "Add CloudWatch alarm for API Gateway 5xx errors"
        ]
    },
    {
        "incident_id": "inc-2024-11-10-003",
        "timestamp": "2024-11-10T16:45:00Z",
        "service_name": "user-authentication",
        "failure_type": "configuration_error",
        "root_cause": "IAM role missing required permissions",
        "description": """
Lambda function unable to write to DynamoDB due to insufficient IAM permissions.
The user-authentication service failed to store session tokens in DynamoDB,
causing all login attempts to fail.

Error Pattern: AccessDeniedException: User is not authorized to perform: dynamodb:PutItem
Stack Trace: botocore.exceptions.ClientError: An error occurred (AccessDeniedException)

Resolution: Added DynamoDB write permissions to Lambda execution role:
aws iam put-role-policy --role-name user-auth-lambda-role \\
  --policy-name DynamoDBWriteAccess \\
  --policy-document file://dynamodb-policy.json

Time to Resolution: 8 minutes
Confidence: 98%
""",
        "category": "configuration_error",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Reviewed CloudWatch Logs for AccessDeniedException",
            "Identified missing dynamodb:PutItem permission",
            "Updated IAM role policy with required permissions"
        ],
        "preventive_measures": [
            "Use least-privilege IAM policies from the start",
            "Test IAM permissions in staging environment"
        ]
    },
    {
        "incident_id": "inc-2024-11-15-004",
        "timestamp": "2024-11-15T11:20:00Z",
        "service_name": "data-pipeline",
        "failure_type": "configuration_error",
        "root_cause": "Step Functions state machine invalid JSON path",
        "description": """
Step Functions execution failure due to invalid JSONPath expression in state
machine definition. The data-pipeline workflow failed at the Transform state
with InvalidPathException.

Error Pattern: States.Runtime error: An error occurred while executing the state
Error Details: Invalid JSONPath: $.data.records[*].id

Resolution: Fixed JSONPath expression in state machine definition:
Changed from: $.data.records[*].id
Changed to: $.data.records[0].id
Updated state machine via AWS Console and redeployed.

Time to Resolution: 12 minutes
Confidence: 92%
""",
        "category": "configuration_error",
        "aws_service": "Step Functions",
        "resolution_steps": [
            "Reviewed Step Functions execution history",
            "Identified invalid JSONPath syntax",
            "Corrected JSONPath expression and redeployed"
        ],
        "preventive_measures": [
            "Validate JSONPath expressions before deployment",
            "Add unit tests for state machine definitions"
        ]
    },
    {
        "incident_id": "inc-2024-11-20-005",
        "timestamp": "2024-11-20T13:50:00Z",
        "service_name": "notification-service",
        "failure_type": "configuration_error",
        "root_cause": "SES email identity not verified",
        "description": """
Email delivery failures due to unverified SES sender identity. The notification
service attempted to send emails from noreply@newdomain.com but the domain
was not verified in SES, causing all emails to be rejected.

Error Pattern: MessageRejected: Email address is not verified
Error Code: 400 Bad Request from SES

Resolution: Verified email domain in SES:
1. Added TXT records to DNS for domain verification
2. Waited for DNS propagation (10 minutes)
3. Confirmed verification in SES console

Time to Resolution: 25 minutes
Confidence: 100%
""",
        "category": "configuration_error",
        "aws_service": "SES",
        "resolution_steps": [
            "Identified unverified sender domain in SES error",
            "Added DNS TXT records for domain verification",
            "Confirmed verification and retested email sending"
        ],
        "preventive_measures": [
            "Verify all sender domains before production deployment",
            "Document SES verification process in runbook"
        ]
    },
    # Resource Exhaustion (5 incidents)
    {
        "incident_id": "inc-2024-11-23-006",
        "timestamp": "2024-11-23T10:30:00Z",
        "service_name": "order-processing",
        "failure_type": "resource_exhaustion",
        "root_cause": "Lambda memory exhaustion",
        "description": """
Lambda function running out of memory during large order processing. The
order-processing function was configured with 512MB memory but required
up to 1024MB for processing bulk orders, causing intermittent failures.

Error Pattern: Runtime.OutOfMemoryError: Memory limit exceeded
CloudWatch Metrics: Max memory used: 512MB (100% of allocated)

Resolution: Increased Lambda memory allocation to 1536MB:
aws lambda update-function-configuration --function-name order-processing \\
  --memory-size 1536

Time to Resolution: 4 minutes
Confidence: 95%
""",
        "category": "resource_exhaustion",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Analyzed CloudWatch memory usage metrics",
            "Identified memory limit reached during peak processing",
            "Increased memory allocation to 1536MB"
        ],
        "preventive_measures": [
            "Monitor Lambda memory usage with CloudWatch alarms",
            "Set memory allocation based on P99 usage patterns"
        ]
    },
    {
        "incident_id": "inc-2024-11-25-007",
        "timestamp": "2024-11-25T15:10:00Z",
        "service_name": "analytics-db",
        "failure_type": "resource_exhaustion",
        "root_cause": "DynamoDB read capacity throttling",
        "description": """
DynamoDB table experiencing read throttling during analytics query spike.
The analytics-db table was provisioned with 100 RCU but received 500+ read
requests per second during dashboard refresh, causing ProvisionedThroughputExceededException.

Error Pattern: ProvisionedThroughputExceededException: Rate of requests exceeds allowed throughput
CloudWatch Metrics: ConsumedReadCapacityUnits exceeded ProvisionedReadCapacityUnits

Resolution: Enabled DynamoDB auto-scaling:
aws application-autoscaling register-scalable-target \\
  --service-namespace dynamodb --resource-id table/analytics-db \\
  --scalable-dimension dynamodb:table:ReadCapacityUnits \\
  --min-capacity 100 --max-capacity 1000

Time to Resolution: 6 minutes
Confidence: 90%
""",
        "category": "resource_exhaustion",
        "aws_service": "DynamoDB",
        "resolution_steps": [
            "Reviewed DynamoDB CloudWatch metrics",
            "Identified read capacity throttling",
            "Enabled auto-scaling with 100-1000 RCU range"
        ],
        "preventive_measures": [
            "Enable auto-scaling for all production tables",
            "Consider on-demand billing for unpredictable workloads"
        ]
    },
    {
        "incident_id": "inc-2024-11-28-008",
        "timestamp": "2024-11-28T08:45:00Z",
        "service_name": "postgres-primary",
        "failure_type": "resource_exhaustion",
        "root_cause": "RDS storage full",
        "description": """
RDS PostgreSQL instance storage full, causing write failures. The postgres-primary
database reached 100% storage capacity (100GB allocated), preventing new data
writes and causing application errors.

Error Pattern: ERROR: could not extend file: No space left on device
RDS Event: Storage-full notification

Resolution: Increased RDS storage allocation:
aws rds modify-db-instance --db-instance-identifier postgres-primary \\
  --allocated-storage 200 --apply-immediately

Also enabled storage auto-scaling:
aws rds modify-db-instance --db-instance-identifier postgres-primary \\
  --max-allocated-storage 500

Time to Resolution: 15 minutes (storage expansion takes time)
Confidence: 100%
""",
        "category": "resource_exhaustion",
        "aws_service": "RDS",
        "resolution_steps": [
            "Received RDS storage-full alert",
            "Immediately increased allocated storage to 200GB",
            "Enabled storage auto-scaling with 500GB max",
            "Implemented data archival strategy for old records"
        ],
        "preventive_measures": [
            "Enable storage auto-scaling from the start",
            "Set CloudWatch alarm at 80% storage usage",
            "Implement data retention and archival policies"
        ]
    },
    {
        "incident_id": "inc-2024-12-02-009",
        "timestamp": "2024-12-02T12:20:00Z",
        "service_name": "image-processor",
        "failure_type": "resource_exhaustion",
        "root_cause": "Lambda concurrent execution limit reached",
        "description": """
Lambda concurrent execution limit reached during image processing spike.
The image-processor function hit the account-level concurrent execution limit
of 1000, causing new invocations to be throttled.

Error Pattern: TooManyRequestsException: Rate exceeded
CloudWatch Metrics: ConcurrentExecutions = 1000 (account limit)

Resolution: Requested limit increase via AWS Support:
- Increased account concurrent execution limit to 3000
- Added reserved concurrency of 500 for image-processor function

aws lambda put-function-concurrency --function-name image-processor \\
  --reserved-concurrent-executions 500

Time to Resolution: 2 hours (AWS Support response time)
Confidence: 95%
""",
        "category": "resource_exhaustion",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Identified concurrent execution limit in CloudWatch",
            "Requested limit increase via AWS Support",
            "Set reserved concurrency for critical function"
        ],
        "preventive_measures": [
            "Monitor concurrent executions with CloudWatch alarms",
            "Request limit increases proactively based on growth",
            "Implement queue-based processing for burst workloads"
        ]
    },
    {
        "incident_id": "inc-2024-12-05-010",
        "timestamp": "2024-12-05T17:30:00Z",
        "service_name": "batch-processor",
        "failure_type": "resource_exhaustion",
        "root_cause": "DynamoDB write capacity throttling",
        "description": """
DynamoDB write throttling during batch data import. The batch-processor
attempted to write 1000 items per second but the table was provisioned
with only 100 WCU, causing widespread throttling.

Error Pattern: ProvisionedThroughputExceededException on BatchWriteItem
CloudWatch Metrics: WriteThrottleEvents = 850 per minute

Resolution: Switched to on-demand billing mode:
aws dynamodb update-table --table-name batch-data \\
  --billing-mode PAY_PER_REQUEST

Also implemented exponential backoff in application code.

Time to Resolution: 10 minutes
Confidence: 92%
""",
        "category": "resource_exhaustion",
        "aws_service": "DynamoDB",
        "resolution_steps": [
            "Analyzed DynamoDB throttling metrics",
            "Switched table to on-demand billing mode",
            "Added exponential backoff retry logic in application"
        ],
        "preventive_measures": [
            "Use on-demand billing for unpredictable workloads",
            "Implement exponential backoff for all DynamoDB operations",
            "Batch writes in smaller chunks (25 items max)"
        ]
    },

    # Dependency Failures (5 incidents)
    {
        "incident_id": "inc-2024-12-08-011",
        "timestamp": "2024-12-08T09:00:00Z",
        "service_name": "payment-gateway-client",
        "failure_type": "dependency_failure",
        "root_cause": "External payment gateway timeout",
        "description": """
Payment processing failures due to external payment gateway timeouts.
The payment-gateway-client Lambda function experienced connection timeouts
when calling the external payment API, with 15 consecutive timeout errors.

Error Pattern: ConnectTimeoutError: Connection to payment-gateway.example.com timed out
Stack Trace: requests.exceptions.ConnectTimeout after 10 seconds

Resolution: Increased connection timeout and added retry logic:
- Increased timeout from 10s to 30s
- Implemented exponential backoff retry (3 attempts)
- Added circuit breaker pattern to prevent cascade failures

Time to Resolution: 20 minutes
Confidence: 85%
""",
        "category": "dependency_failure",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Identified timeout pattern in CloudWatch Logs",
            "Increased connection timeout to 30 seconds",
            "Added retry logic with exponential backoff",
            "Implemented circuit breaker pattern"
        ],
        "preventive_measures": [
            "Monitor external dependency health proactively",
            "Implement circuit breaker for all external calls",
            "Add fallback mechanisms for critical dependencies"
        ]
    },
    {
        "incident_id": "inc-2024-12-12-012",
        "timestamp": "2024-12-12T14:15:00Z",
        "service_name": "user-service",
        "failure_type": "dependency_failure",
        "root_cause": "RDS database connection pool exhaustion",
        "description": """
Application unable to connect to RDS database due to connection pool exhaustion.
The user-service Lambda functions exhausted all available database connections
(max 100), causing new requests to fail with connection timeout errors.

Error Pattern: OperationalError: FATAL: remaining connection slots are reserved
CloudWatch Logs: psycopg2.OperationalError: could not connect to server

Resolution: Implemented connection pooling with RDS Proxy:
aws rds create-db-proxy --db-proxy-name user-service-proxy \\
  --engine-family POSTGRESQL \\
  --auth {AuthScheme=SECRETS} \\
  --role-arn arn:aws:iam::123456789012:role/rds-proxy-role \\
  --vpc-subnet-ids subnet-1 subnet-2

Updated Lambda to use RDS Proxy endpoint instead of direct RDS connection.

Time to Resolution: 30 minutes
Confidence: 90%
""",
        "category": "dependency_failure",
        "aws_service": "RDS",
        "resolution_steps": [
            "Identified connection pool exhaustion in RDS metrics",
            "Created RDS Proxy for connection pooling",
            "Updated Lambda functions to use proxy endpoint",
            "Verified connection reuse and reduced connection count"
        ],
        "preventive_measures": [
            "Use RDS Proxy for Lambda database connections",
            "Implement connection pooling in application code",
            "Monitor database connection count with CloudWatch"
        ]
    },
    {
        "incident_id": "inc-2024-12-15-013",
        "timestamp": "2024-12-15T11:40:00Z",
        "service_name": "api-aggregator",
        "failure_type": "dependency_failure",
        "root_cause": "Third-party API rate limiting",
        "description": """
API aggregator service failing due to third-party API rate limits. The
api-aggregator was making 1000+ requests per minute to a third-party API
that enforces a 100 requests/minute limit, causing 429 Too Many Requests errors.

Error Pattern: HTTPError: 429 Client Error: Too Many Requests
Response Headers: X-RateLimit-Remaining: 0, Retry-After: 60

Resolution: Implemented request throttling and caching:
- Added Redis cache for API responses (5-minute TTL)
- Implemented token bucket rate limiter (90 requests/minute)
- Added request queue for burst handling

Time to Resolution: 45 minutes
Confidence: 88%
""",
        "category": "dependency_failure",
        "aws_service": "Lambda",
        "resolution_steps": [
            "Analyzed 429 error pattern in logs",
            "Implemented Redis caching layer (ElastiCache)",
            "Added rate limiting with token bucket algorithm",
            "Created request queue for overflow handling"
        ],
        "preventive_measures": [
            "Cache external API responses when possible",
            "Respect third-party rate limits proactively",
            "Monitor API usage against rate limits"
        ]
    },
    {
        "incident_id": "inc-2024-12-18-014",
        "timestamp": "2024-12-18T16:25:00Z",
        "service_name": "notification-dispatcher",
        "failure_type": "dependency_failure",
        "root_cause": "SNS topic delivery failure",
        "description": """
Notification delivery failures due to SNS topic subscription endpoint unavailable.
The notification-dispatcher published messages to SNS, but the HTTP/S endpoint
subscriber was down, causing delivery failures and message loss.

Error Pattern: SNS delivery failure notification
CloudWatch Logs: Delivery failed to endpoint https://webhook.example.com/notify

Resolution: Implemented dead-letter queue and retry mechanism:
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:123456789012:notifications \\
  --protocol sqs --notification-endpoint arn:aws:sqs:us-east-1:123456789012:dlq

Added SQS dead-letter queue for failed deliveries and retry Lambda.

Time to Resolution: 25 minutes
Confidence: 92%
""",
        "category": "dependency_failure",
        "aws_service": "SNS",
        "resolution_steps": [
            "Identified SNS delivery failures in CloudWatch",
            "Created SQS dead-letter queue for failed messages",
            "Implemented retry Lambda to process DLQ messages",
            "Added monitoring for DLQ depth"
        ],
        "preventive_measures": [
            "Always configure dead-letter queues for SNS topics",
            "Monitor endpoint health before publishing",
            "Implement retry logic with exponential backoff"
        ]
    },
    {
        "incident_id": "inc-2024-12-20-015",
        "timestamp": "2024-12-20T13:55:00Z",
        "service_name": "data-sync",
        "failure_type": "dependency_failure",
        "root_cause": "S3 eventual consistency delay",
        "description": """
Data sync failures due to S3 eventual consistency. The data-sync workflow
wrote objects to S3 and immediately attempted to read them, but the objects
were not yet available due to eventual consistency, causing read errors.

Error Pattern: NoSuchKey: The specified key does not exist
Workflow: Write to S3 → Immediate read → NoSuchKey error

Resolution: Implemented retry logic with exponential backoff:
- Added 2-second initial delay before first read attempt
- Implemented exponential backoff retry (5 attempts max)
- Switched to S3 Strong Consistency (available in all regions)

Note: S3 now provides strong read-after-write consistency by default.

Time to Resolution: 15 minutes
Confidence: 95%
""",
        "category": "dependency_failure",
        "aws_service": "S3",
        "resolution_steps": [
            "Identified timing issue in workflow logs",
            "Added retry logic with exponential backoff",
            "Verified S3 strong consistency is enabled (default)",
            "Updated workflow to handle transient read failures"
        ],
        "preventive_measures": [
            "Implement retry logic for all S3 read operations",
            "Add delays between write and read operations if needed",
            "Monitor S3 request metrics for errors"
        ]
    }
]


def create_incident_document(incident: dict) -> str:
    """
    Create a formatted incident document for Knowledge Base ingestion.
    
    Args:
        incident: Incident data dictionary
    
    Returns:
        str: Formatted document text
    """
    doc = f"""# Incident Report: {incident['incident_id']}

## Metadata
- **Incident ID**: {incident['incident_id']}
- **Timestamp**: {incident['timestamp']}
- **Service**: {incident['service_name']}
- **Failure Type**: {incident['failure_type']}
- **AWS Service**: {incident['aws_service']}
- **Category**: {incident['category']}

## Root Cause
{incident['root_cause']}

## Description
{incident['description']}

## Resolution Steps
"""
    
    for i, step in enumerate(incident['resolution_steps'], 1):
        doc += f"{i}. {step}\n"
    
    doc += "\n## Preventive Measures\n"
    for measure in incident['preventive_measures']:
        doc += f"- {measure}\n"
    
    return doc


def upload_to_s3(bucket_name: str, key: str, content: str) -> bool:
    """
    Upload incident document to S3.
    
    Args:
        bucket_name: S3 bucket name
        key: S3 object key
        content: Document content
    
    Returns:
        bool: True if successful, False otherwise
    """
    s3_client = boto3.client('s3', region_name=get_aws_region())
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='text/plain'
        )
        return True
    except ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        return False


def start_ingestion_job(knowledge_base_id: str, data_source_id: str) -> str:
    """
    Start Knowledge Base ingestion job.
    
    Args:
        knowledge_base_id: Knowledge Base ID
        data_source_id: Data source ID
    
    Returns:
        str: Ingestion job ID
    """
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=get_aws_region())
    
    try:
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id
        )
        return response['ingestionJob']['ingestionJobId']
    except ClientError as e:
        logger.error(f"Error starting ingestion job: {e}")
        raise


def get_data_source_id(knowledge_base_id: str) -> str:
    """
    Get data source ID for Knowledge Base.
    
    Args:
        knowledge_base_id: Knowledge Base ID
    
    Returns:
        str: Data source ID
    """
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=get_aws_region())
    
    try:
        response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=knowledge_base_id
        )
        
        if not response.get('dataSourceSummaries'):
            raise ValueError("No data sources found for Knowledge Base")
        
        return response['dataSourceSummaries'][0]['dataSourceId']
    except ClientError as e:
        logger.error(f"Error getting data source ID: {e}")
        raise


def main():
    """Main function to populate Knowledge Base with sample incidents"""
    
    print("=" * 80)
    print("Populating Bedrock Knowledge Base with Sample Incidents")
    print("=" * 80)
    print()
    
    # Get configuration
    bucket_name = get_kb_data_source_bucket_name()
    print(f"S3 Bucket: {bucket_name}")
    
    try:
        kb_id = get_knowledge_base_id()
        print(f"Knowledge Base ID: {kb_id}")
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Run setup_infrastructure.py first to create Knowledge Base")
        return 1
    
    try:
        data_source_id = get_data_source_id(kb_id)
        print(f"Data Source ID: {data_source_id}")
    except (ValueError, ClientError) as e:
        print(f"❌ Error: {e}")
        return 1
    
    print()
    print(f"Creating and uploading {len(SAMPLE_INCIDENTS)} sample incidents...")
    print()
    
    # Upload incidents to S3
    uploaded_count = 0
    for incident in SAMPLE_INCIDENTS:
        incident_id = incident['incident_id']
        print(f"  • {incident_id} ({incident['category']}, {incident['aws_service']})...", end=" ")
        
        # Create document
        doc_content = create_incident_document(incident)
        
        # Upload to S3 in incidents/ prefix
        s3_key = f"incidents/{incident_id}.txt"
        if upload_to_s3(bucket_name, s3_key, doc_content):
            print("✓")
            uploaded_count += 1
        else:
            print("✗")
    
    print()
    print(f"✓ Uploaded {uploaded_count}/{len(SAMPLE_INCIDENTS)} incidents to S3")
    print()
    
    # Start ingestion job
    print("Starting Knowledge Base ingestion job...")
    try:
        job_id = start_ingestion_job(kb_id, data_source_id)
        print(f"✓ Ingestion job started: {job_id}")
        print()
        print("Note: Ingestion may take 5-10 minutes to complete.")
        print("Check status in AWS Console: Bedrock → Knowledge Bases → Data Sources")
    except ClientError as e:
        print(f"❌ Error starting ingestion job: {e}")
        return 1
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total Incidents: {len(SAMPLE_INCIDENTS)}")
    print(f"  • Configuration Errors: 5")
    print(f"  • Resource Exhaustion: 5")
    print(f"  • Dependency Failures: 5")
    print()
    print("AWS Services Covered:")
    print(f"  • Lambda (deployment, memory, concurrency)")
    print(f"  • DynamoDB (throttling, capacity)")
    print(f"  • RDS (storage, connections)")
    print(f"  • API Gateway (timeouts)")
    print(f"  • Step Functions (state machine errors)")
    print(f"  • SES (email verification)")
    print(f"  • SNS (delivery failures)")
    print(f"  • S3 (consistency)")
    print()
    print("✓ Knowledge Base population complete!")
    print("Run scripts/test_kb_query.py to verify ingestion and test queries.")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
