#!/usr/bin/env python3
"""
Create realistic POC data for incident response system demo.
This script creates:
1. Sample log files with realistic errors
2. Historical incidents in Knowledge Base
3. Test scenarios for demonstration
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Disable SSL verification for corporate proxy environments
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

s3_client = boto3.client('s3', region_name='us-east-1', verify=False)
kb_client = boto3.client('bedrock-agent', region_name='us-east-1', verify=False)

# Configuration
LOG_BUCKET = os.getenv('S3_LOG_BUCKET', 'incident-response-logs-867126415696')
KB_BUCKET = os.getenv('KB_DATA_SOURCE_BUCKET', 'incident-kb-data-867126415696')
KNOWLEDGE_BASE_ID = os.getenv('KNOWLEDGE_BASE_ID', 'FVVB6AQNHD')
DATA_SOURCE_ID = os.getenv('DATA_SOURCE_ID', 'YJWQHQNQXM')

# Error Scenarios
ERROR_SCENARIOS = {
    "lambda_timeout": {
        "service_name": "payment-processor",
        "error_type": "dependency_failure",
        "description": "Lambda timeout calling external payment API"
    },
    "dynamodb_throttling": {
        "service_name": "user-service",
        "error_type": "resource_exhaustion",
        "description": "DynamoDB throttling on user table"
    },
    "api_gateway_502": {
        "service_name": "order-api",
        "error_type": "dependency_failure",
        "description": "API Gateway 502 from backend Lambda"
    },
    "lambda_memory_exhausted": {
        "service_name": "image-processor",
        "error_type": "resource_exhaustion",
        "description": "Lambda out of memory processing large images"
    },
    "rds_connection_pool": {
        "service_name": "inventory-service",
        "error_type": "configuration_error",
        "description": "RDS connection pool exhausted"
    }
}


def create_lambda_timeout_logs():
    """Create realistic Lambda timeout logs"""
    timestamp = datetime.utcnow()
    logs = []
    
    # Normal operation logs
    for i in range(5):
        t = timestamp - timedelta(minutes=20-i)
        logs.append(f"{t.isoformat()}Z INFO [payment-processor] Processing payment request {1000+i}")
        logs.append(f"{t.isoformat()}Z INFO [payment-processor] Calling Stripe API for payment validation")
    
    # Timeout errors start
    for i in range(10):
        t = timestamp - timedelta(minutes=15-i)
        logs.append(f"{t.isoformat()}Z ERROR [payment-processor] Timeout calling https://api.stripe.com/v1/charges")
        logs.append(f"{t.isoformat()}Z ERROR [payment-processor] java.net.SocketTimeoutException: Read timed out")
        logs.append(f"{t.isoformat()}Z ERROR [payment-processor] at java.net.SocketInputStream.socketRead0(Native Method)")
        logs.append(f"{t.isoformat()}Z ERROR [payment-processor] at com.stripe.net.APIResource.request(APIResource.java:142)")
        logs.append(f"{t.isoformat()}Z WARN [payment-processor] Retry attempt {i+1} failed")
    
    logs.append(f"{timestamp.isoformat()}Z FATAL [payment-processor] Lambda timeout after 30 seconds")
    logs.append(f"{timestamp.isoformat()}Z ERROR [payment-processor] Task timed out after 30.00 seconds")
    
    return "\n".join(logs)


def create_dynamodb_throttling_logs():
    """Create realistic DynamoDB throttling logs"""
    timestamp = datetime.utcnow()
    logs = []
    
    # Normal operation
    for i in range(3):
        t = timestamp - timedelta(minutes=10-i)
        logs.append(f"{t.isoformat()}Z INFO [user-service] Query user table for user_id=12345")
        logs.append(f"{t.isoformat()}Z INFO [user-service] Successfully retrieved user data")
    
    # Throttling errors
    for i in range(15):
        t = timestamp - timedelta(minutes=7-i*0.3)
        logs.append(f"{t.isoformat()}Z ERROR [user-service] ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput")
        logs.append(f"{t.isoformat()}Z ERROR [user-service] Table: users-prod, Operation: Query")
        logs.append(f"{t.isoformat()}Z WARN [user-service] Current RCU: 5, Consumed: 25")
    
    logs.append(f"{timestamp.isoformat()}Z FATAL [user-service] Service degraded - 95% of requests failing")
    
    return "\n".join(logs)


def create_api_gateway_502_logs():
    """Create realistic API Gateway 502 logs"""
    timestamp = datetime.utcnow()
    logs = []
    
    t1 = timestamp - timedelta(minutes=5)
    logs.append(f"{t1.isoformat()}Z INFO [order-api] Received POST /orders request")
    logs.append(f"{t1.isoformat()}Z INFO [order-api] Invoking Lambda function: process-order")
    
    for i in range(8):
        t = timestamp - timedelta(minutes=4-i*0.5)
        logs.append(f"{t.isoformat()}Z ERROR [order-api] Lambda invocation failed with status 502")
        logs.append(f"{t.isoformat()}Z ERROR [order-api] Error: Lambda function returned invalid response")
        logs.append(f"{t.isoformat()}Z ERROR [order-api] Response headers missing Content-Type")
        logs.append(f"{t.isoformat()}Z WARN [order-api] API Gateway returning 502 Bad Gateway to client")
    
    logs.append(f"{timestamp.isoformat()}Z FATAL [order-api] 100% error rate for /orders endpoint")
    
    return "\n".join(logs)


def create_lambda_memory_logs():
    """Create realistic Lambda memory exhaustion logs"""
    timestamp = datetime.utcnow()
    logs = []
    
    t1 = timestamp - timedelta(minutes=3)
    t2 = timestamp - timedelta(minutes=2)
    t3 = timestamp - timedelta(minutes=1)
    
    logs.append(f"{t1.isoformat()}Z INFO [image-processor] Processing image upload: large-photo.jpg (15MB)")
    logs.append(f"{t1.isoformat()}Z INFO [image-processor] Allocated memory: 512MB")
    logs.append(f"{t2.isoformat()}Z WARN [image-processor] Memory usage: 450MB (87%)")
    logs.append(f"{t2.isoformat()}Z WARN [image-processor] Creating thumbnail from 15MB source")
    logs.append(f"{t3.isoformat()}Z ERROR [image-processor] Memory usage: 510MB (99%)")
    logs.append(f"{t3.isoformat()}Z ERROR [image-processor] java.lang.OutOfMemoryError: Java heap space")
    logs.append(f"{t3.isoformat()}Z ERROR [image-processor] at java.awt.image.DataBufferByte.<init>(DataBufferByte.java:92)")
    logs.append(f"{timestamp.isoformat()}Z FATAL [image-processor] Lambda function terminated due to memory exhaustion")
    
    return "\n".join(logs)


def create_rds_connection_logs():
    """Create realistic RDS connection pool exhaustion logs"""
    timestamp = datetime.utcnow()
    logs = []
    
    t1 = timestamp - timedelta(minutes=8)
    t2 = timestamp - timedelta(minutes=6)
    t3 = timestamp - timedelta(minutes=5)
    
    logs.append(f"{t1.isoformat()}Z INFO [inventory-service] Database connection pool size: 10")
    logs.append(f"{t2.isoformat()}Z WARN [inventory-service] Active connections: 8/10")
    logs.append(f"{t3.isoformat()}Z WARN [inventory-service] Active connections: 10/10 (pool exhausted)")
    
    for i in range(12):
        t = timestamp - timedelta(minutes=4-i*0.3)
        logs.append(f"{t.isoformat()}Z ERROR [inventory-service] Cannot get connection from pool")
        logs.append(f"{t.isoformat()}Z ERROR [inventory-service] com.mysql.jdbc.exceptions.jdbc4.MySQLNonTransientConnectionException")
        logs.append(f"{t.isoformat()}Z ERROR [inventory-service] Too many connections")
    
    logs.append(f"{timestamp.isoformat()}Z FATAL [inventory-service] All database operations failing")
    
    return "\n".join(logs)


def upload_logs_to_s3():
    """Upload sample logs to S3"""
    print("Creating and uploading sample log files...")
    
    scenarios = {
        "payment-processor/2026-03-09/timeout.log": create_lambda_timeout_logs(),
        "user-service/2026-03-09/throttling.log": create_dynamodb_throttling_logs(),
        "order-api/2026-03-09/502-error.log": create_api_gateway_502_logs(),
        "image-processor/2026-03-09/memory.log": create_lambda_memory_logs(),
        "inventory-service/2026-03-09/connection.log": create_rds_connection_logs()
    }
    
    for key, content in scenarios.items():
        try:
            s3_client.put_object(
                Bucket=LOG_BUCKET,
                Key=key,
                Body=content.encode('utf-8'),
                ContentType='text/plain'
            )
            print(f"✓ Uploaded: s3://{LOG_BUCKET}/{key}")
        except Exception as e:
            print(f"✗ Failed to upload {key}: {e}")
    
    return scenarios


def create_historical_incidents():
    """Create historical incident documents for Knowledge Base"""
    incidents = [
        {
            "filename": "incident-2026-02-15-lambda-timeout.txt",
            "content": """Incident ID: inc-2026-02-15-001
Service: payment-processor
Date: 2026-02-15T14:30:00Z
Root Cause: External API timeout (Stripe payment gateway)
Category: dependency_failure
Confidence: 92%

Description:
Lambda function timing out after 30 seconds when calling Stripe API for payment validation. 
Multiple consecutive timeout errors observed over 15-minute period.

Evidence:
- 15 consecutive SocketTimeoutException errors
- All timeouts occurred calling https://api.stripe.com/v1/charges
- No internal Lambda errors or memory issues
- Stripe status page showed elevated API latency during incident window

Resolution:
1. Increased Lambda timeout from 30s to 60s
2. Implemented exponential backoff retry logic (3 retries with 2s, 4s, 8s delays)
3. Added circuit breaker pattern to fail fast after 5 consecutive failures
4. Set up CloudWatch alarm for Stripe API latency

Commands Executed:
aws lambda update-function-configuration --function-name payment-processor --timeout 60

Resolution Time: 12 minutes
Status: Resolved
"""
        },
        {
            "filename": "incident-2026-02-20-dynamodb-throttle.txt",
            "content": """Incident ID: inc-2026-02-20-002
Service: user-service
Date: 2026-02-20T09:15:00Z
Root Cause: DynamoDB provisioned throughput exceeded
Category: resource_exhaustion
Confidence: 95%

Description:
User service experiencing 95% error rate due to DynamoDB throttling. 
Table configured with 5 RCU but consuming 25 RCU during peak traffic.

Evidence:
- ProvisionedThroughputExceededException errors
- Current RCU: 5, Consumed: 25 (5x over capacity)
- Traffic spike from marketing campaign launch
- No application code changes

Resolution:
1. Enabled DynamoDB auto-scaling (min: 5 RCU, max: 100 RCU, target: 70%)
2. Switched to on-demand billing mode for immediate relief
3. Implemented application-level caching with Redis (TTL: 5 minutes)
4. Added exponential backoff in application retry logic

Commands Executed:
aws dynamodb update-table --table-name users-prod --billing-mode PAY_PER_REQUEST

Resolution Time: 8 minutes
Status: Resolved
"""
        },
        {
            "filename": "incident-2026-02-25-api-gateway-502.txt",
            "content": """Incident ID: inc-2026-02-25-003
Service: order-api
Date: 2026-02-25T16:45:00Z
Root Cause: Lambda function returning malformed response
Category: configuration_error
Confidence: 88%

Description:
API Gateway returning 502 Bad Gateway errors. Lambda function executing successfully 
but returning response without required Content-Type header.

Evidence:
- 100% error rate on /orders POST endpoint
- Lambda CloudWatch logs show successful execution
- API Gateway logs show "Lambda function returned invalid response"
- Response headers missing Content-Type

Resolution:
1. Updated Lambda function to include Content-Type header in response
2. Added response validation in Lambda function
3. Implemented API Gateway response mapping template as fallback
4. Added integration tests for API response format

Code Fix:
return {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},  # Added this
    'body': json.dumps(response_data)
}

Resolution Time: 15 minutes
Status: Resolved
"""
        },
        {
            "filename": "incident-2026-03-01-lambda-memory.txt",
            "content": """Incident ID: inc-2026-03-01-004
Service: image-processor
Date: 2026-03-01T11:20:00Z
Root Cause: Insufficient Lambda memory for large image processing
Category: resource_exhaustion
Confidence: 93%

Description:
Lambda function running out of memory when processing images larger than 10MB.
OutOfMemoryError thrown during thumbnail generation.

Evidence:
- java.lang.OutOfMemoryError: Java heap space
- Memory usage reached 99% (510MB of 512MB)
- Processing 15MB source image
- Error occurs during BufferedImage creation

Resolution:
1. Increased Lambda memory from 512MB to 2048MB
2. Implemented streaming image processing to reduce memory footprint
3. Added input validation to reject images >20MB
4. Configured S3 event filter to only process images <20MB

Commands Executed:
aws lambda update-function-configuration --function-name image-processor --memory-size 2048

Resolution Time: 10 minutes
Status: Resolved
"""
        },
        {
            "filename": "incident-2026-03-05-rds-connections.txt",
            "content": """Incident ID: inc-2026-03-05-005
Service: inventory-service
Date: 2026-03-05T13:10:00Z
Root Cause: RDS connection pool exhausted due to connection leaks
Category: configuration_error
Confidence: 90%

Description:
Database connection pool exhausted (10/10 connections active). 
Application not properly closing connections after queries.

Evidence:
- MySQLNonTransientConnectionException: Too many connections
- Connection pool size: 10 (all active)
- RDS max_connections: 100 (not reached)
- Application logs show connections opened but not closed

Resolution:
1. Fixed connection leak in application code (added try-finally blocks)
2. Increased connection pool size from 10 to 50
3. Configured connection pool timeout to 30 seconds
4. Added connection pool monitoring with CloudWatch metrics
5. Implemented connection validation before checkout

Configuration Changes:
spring.datasource.hikari.maximum-pool-size=50
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.validation-timeout=5000

Resolution Time: 20 minutes
Status: Resolved
"""
        }
    ]
    
    return incidents


def upload_incidents_to_kb():
    """Upload historical incidents to Knowledge Base S3 bucket"""
    print("\nUploading historical incidents to Knowledge Base...")
    
    incidents = create_historical_incidents()
    
    for incident in incidents:
        try:
            s3_client.put_object(
                Bucket=KB_BUCKET,
                Key=f"incidents/{incident['filename']}",
                Body=incident['content'].encode('utf-8'),
                ContentType='text/plain'
            )
            print(f"✓ Uploaded: s3://{KB_BUCKET}/incidents/{incident['filename']}")
        except Exception as e:
            print(f"✗ Failed to upload {incident['filename']}: {e}")
    
    return incidents


def trigger_kb_sync():
    """Trigger Knowledge Base ingestion job"""
    print("\nTriggering Knowledge Base ingestion...")
    
    try:
        response = kb_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        print(f"✓ Ingestion job started: {job_id}")
        print(f"  Status: {response['ingestionJob']['status']}")
        print("\nNote: Ingestion may take 2-5 minutes to complete.")
        print("Check status with: aws bedrock-agent get-ingestion-job")
        
        return job_id
    except Exception as e:
        print(f"✗ Failed to start ingestion: {e}")
        return None


def print_test_scenarios():
    """Print test scenarios for demonstration"""
    print("\n" + "="*80)
    print("POC TEST SCENARIOS")
    print("="*80)
    
    scenarios = [
        {
            "name": "Lambda Timeout (Stripe API)",
            "service": "payment-processor",
            "log_location": f"s3://{LOG_BUCKET}/payment-processor/2026-03-09/timeout.log",
            "error": "Lambda timeout calling external payment API",
            "expected_root_cause": "dependency_failure",
            "similar_incident": "inc-2026-02-15-001"
        },
        {
            "name": "DynamoDB Throttling",
            "service": "user-service",
            "log_location": f"s3://{LOG_BUCKET}/user-service/2026-03-09/throttling.log",
            "error": "ProvisionedThroughputExceededException on users table",
            "expected_root_cause": "resource_exhaustion",
            "similar_incident": "inc-2026-02-20-002"
        },
        {
            "name": "API Gateway 502",
            "service": "order-api",
            "log_location": f"s3://{LOG_BUCKET}/order-api/2026-03-09/502-error.log",
            "error": "Lambda returning invalid response format",
            "expected_root_cause": "configuration_error",
            "similar_incident": "inc-2026-02-25-003"
        },
        {
            "name": "Lambda Memory Exhaustion",
            "service": "image-processor",
            "log_location": f"s3://{LOG_BUCKET}/image-processor/2026-03-09/memory.log",
            "error": "OutOfMemoryError processing large images",
            "expected_root_cause": "resource_exhaustion",
            "similar_incident": "inc-2026-03-01-004"
        },
        {
            "name": "RDS Connection Pool Exhausted",
            "service": "inventory-service",
            "log_location": f"s3://{LOG_BUCKET}/inventory-service/2026-03-09/connection.log",
            "error": "Too many database connections",
            "expected_root_cause": "configuration_error",
            "similar_incident": "inc-2026-03-05-005"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Service: {scenario['service']}")
        print(f"   Error: {scenario['error']}")
        print(f"   Expected Root Cause: {scenario['expected_root_cause']}")
        print(f"   Similar Past Incident: {scenario['similar_incident']}")
        print(f"   Log Location: {scenario['log_location']}")
    
    print("\n" + "="*80)
    print("To test, run: python scripts/test_realistic_scenario.py <scenario_number>")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("Creating Realistic POC Data for Incident Response System")
    print("="*80 + "\n")
    
    # Upload logs
    upload_logs_to_s3()
    
    # Upload historical incidents
    upload_incidents_to_kb()
    
    # Trigger KB sync
    trigger_kb_sync()
    
    # Print test scenarios
    print_test_scenarios()
    
    print("\n✓ POC data creation complete!")
    print("\nNext steps:")
    print("1. Wait 2-5 minutes for Knowledge Base ingestion to complete")
    print("2. Run: python scripts/test_realistic_scenario.py 1")
    print("3. Check your email for the incident alert with detailed analysis")
