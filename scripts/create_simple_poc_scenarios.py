#!/usr/bin/env python3
"""
Create simple POC scenarios with Knowledge Base historical incidents
"""

import boto3
import json
from datetime import datetime, timedelta

s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')

LOG_BUCKET = 'incident-response-logs-867126415696'

# Scenario 1: DynamoDB Throttling
def create_dynamodb_throttling_scenario():
    """Create DynamoDB throttling scenario with logs and historical incident"""
    
    print("Creating Scenario 1: DynamoDB Throttling")
    print("=" * 80)
    
    # Create realistic log file
    log_content = """2026-03-09T10:00:00.000Z ERROR [user-service] DynamoDB operation failed
2026-03-09T10:00:00.100Z ERROR [user-service] ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput
2026-03-09T10:00:00.200Z ERROR [user-service] Table: users-prod, Operation: PutItem
2026-03-09T10:00:01.000Z ERROR [user-service] DynamoDB operation failed
2026-03-09T10:00:01.100Z ERROR [user-service] ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput
2026-03-09T10:00:02.000Z ERROR [user-service] DynamoDB operation failed
2026-03-09T10:00:02.100Z ERROR [user-service] ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput
2026-03-09T10:00:03.000Z WARN [user-service] Retry attempt 1 failed
2026-03-09T10:00:04.000Z ERROR [user-service] DynamoDB operation failed
2026-03-09T10:00:04.100Z ERROR [user-service] ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput
2026-03-09T10:00:05.000Z WARN [user-service] Retry attempt 2 failed
2026-03-09T10:00:06.000Z ERROR [user-service] Max retries exceeded, operation aborted
"""
    
    # Upload log to S3
    s3.put_object(
        Bucket=LOG_BUCKET,
        Key='user-service/2026-03-09/throttling.log',
        Body=log_content.encode('utf-8')
    )
    print("✓ Uploaded log file to S3")
    
    # Create historical incident for Knowledge Base
    historical_incident = {
        "incident_id": "inc-2026-02-15-abc123",
        "timestamp": "2026-02-15T14:30:00Z",
        "service_name": "user-service",
        "error_type": "DynamoDB Throttling",
        "root_cause": "ProvisionedThroughputExceededException on users-prod table during peak traffic",
        "resolution": "Enabled DynamoDB auto-scaling with min 5 RCU/WCU and max 100 RCU/WCU. Issue resolved immediately.",
        "resolution_time_minutes": 8,
        "commands_executed": [
            "aws application-autoscaling register-scalable-target --service-namespace dynamodb --resource-id table/users-prod --scalable-dimension dynamodb:table:ReadCapacityUnits --min-capacity 5 --max-capacity 100",
            "aws application-autoscaling put-scaling-policy --service-namespace dynamodb --resource-id table/users-prod --scalable-dimension dynamodb:table:ReadCapacityUnits --policy-name UserTableReadScaling --policy-type TargetTrackingScaling --target-tracking-scaling-policy-configuration file://scaling-policy.json"
        ],
        "preventive_actions": "Set up CloudWatch alarms for consumed capacity > 80%",
        "similar_incidents": ["inc-2026-01-20-xyz789", "inc-2025-12-10-def456"]
    }
    
    kb_document = f"""# Incident Report: DynamoDB Throttling - User Service

**Incident ID:** {historical_incident['incident_id']}
**Date:** {historical_incident['timestamp']}
**Service:** {historical_incident['service_name']}
**Severity:** High

## Problem
{historical_incident['root_cause']}

## Root Cause
The users-prod DynamoDB table was configured with fixed provisioned capacity (5 RCU/5 WCU). During peak traffic hours, the application exceeded this capacity, causing ProvisionedThroughputExceededException errors.

## Resolution
{historical_incident['resolution']}

### Commands Executed
```bash
{chr(10).join(historical_incident['commands_executed'])}
```

## Resolution Time
{historical_incident['resolution_time_minutes']} minutes

## Preventive Measures
- {historical_incident['preventive_actions']}
- Consider switching to on-demand billing mode for unpredictable workloads
- Implement exponential backoff in application code

## Similar Incidents
{', '.join(historical_incident['similar_incidents'])}
"""
    
    # Save to local file (for manual KB upload if needed)
    with open('kb_incident_dynamodb_throttling.md', 'w') as f:
        f.write(kb_document)
    
    print("✓ Created Knowledge Base document: kb_incident_dynamodb_throttling.md")
    print(f"\nTest this scenario with:")
    print(f'  Service: user-service')
    print(f'  Error: ProvisionedThroughputExceededException on users-prod table')
    print(f'  Log: s3://{LOG_BUCKET}/user-service/2026-03-09/throttling.log')
    print()


# Scenario 2: RDS Connection Timeout
def create_rds_connection_scenario():
    """Create RDS connection timeout scenario"""
    
    print("Creating Scenario 2: RDS Connection Timeout")
    print("=" * 80)
    
    log_content = """2026-03-09T10:05:00.000Z ERROR [order-service] Database connection failed
2026-03-09T10:05:00.100Z ERROR [order-service] java.sql.SQLTransientConnectionException: Connection is not available, request timed out after 30000ms
2026-03-09T10:05:00.200Z ERROR [order-service] HikariPool-1 - Connection is not available
2026-03-09T10:05:01.000Z ERROR [order-service] Database connection failed
2026-03-09T10:05:01.100Z ERROR [order-service] java.sql.SQLTransientConnectionException: Connection is not available, request timed out after 30000ms
2026-03-09T10:05:02.000Z WARN [order-service] All connection pool connections are in use
2026-03-09T10:05:03.000Z ERROR [order-service] Database connection failed
2026-03-09T10:05:03.100Z ERROR [order-service] java.sql.SQLTransientConnectionException: Connection is not available, request timed out after 30000ms
2026-03-09T10:05:04.000Z ERROR [order-service] Unable to process order, database unavailable
"""
    
    s3.put_object(
        Bucket=LOG_BUCKET,
        Key='order-service/2026-03-09/connection-timeout.log',
        Body=log_content.encode('utf-8')
    )
    print("✓ Uploaded log file to S3")
    
    historical_incident = {
        "incident_id": "inc-2026-02-20-xyz456",
        "timestamp": "2026-02-20T09:15:00Z",
        "service_name": "order-service",
        "error_type": "RDS Connection Timeout",
        "root_cause": "RDS connection pool exhausted due to long-running queries blocking connections",
        "resolution": "Restarted the application after 5 minutes. Long-running queries were killed. Connection pool recovered.",
        "resolution_time_minutes": 7,
        "immediate_action": "Wait 5 minutes for existing connections to timeout, then restart the service",
        "commands_executed": [
            "# Wait 5 minutes for connections to timeout",
            "aws ecs update-service --cluster prod-cluster --service order-service --force-new-deployment"
        ],
        "preventive_actions": "Increased connection pool size from 10 to 20. Added query timeout of 30 seconds."
    }
    
    kb_document = f"""# Incident Report: RDS Connection Timeout - Order Service

**Incident ID:** {historical_incident['incident_id']}
**Date:** {historical_incident['timestamp']}
**Service:** {historical_incident['service_name']}
**Severity:** Critical

## Problem
{historical_incident['root_cause']}

## Root Cause
The application's connection pool (HikariCP) was configured with only 10 connections. Several long-running queries (>2 minutes) held connections, preventing new requests from acquiring connections. This caused a cascading failure.

## Resolution
{historical_incident['resolution']}

### Immediate Action
**{historical_incident['immediate_action']}**

This is a temporary fix that works because:
1. Existing connections will timeout after 5 minutes
2. Restarting clears the connection pool
3. New connections can be established fresh

### Commands Executed
```bash
{chr(10).join(historical_incident['commands_executed'])}
```

## Resolution Time
{historical_incident['resolution_time_minutes']} minutes

## Preventive Measures
- {historical_incident['preventive_actions']}
- Set up CloudWatch alarms for database connection count
- Implement connection pool monitoring
- Add circuit breaker for database operations

## Important Note
**If you see this error, wait 5 minutes before restarting.** Restarting immediately may not help if connections are still held.
"""
    
    with open('kb_incident_rds_connection.md', 'w') as f:
        f.write(kb_document)
    
    print("✓ Created Knowledge Base document: kb_incident_rds_connection.md")
    print(f"\nTest this scenario with:")
    print(f'  Service: order-service')
    print(f'  Error: SQLTransientConnectionException - Connection timeout')
    print(f'  Log: s3://{LOG_BUCKET}/order-service/2026-03-09/connection-timeout.log')
    print()


# Scenario 3: Lambda Memory Error
def create_lambda_memory_scenario():
    """Create Lambda memory error scenario"""
    
    print("Creating Scenario 3: Lambda Memory Exhaustion")
    print("=" * 80)
    
    log_content = """2026-03-09T10:10:00.000Z INFO [image-processor] Processing image: large-photo-15MB.jpg
2026-03-09T10:10:01.000Z INFO [image-processor] Loading image into memory
2026-03-09T10:10:02.000Z INFO [image-processor] Applying filters and transformations
2026-03-09T10:10:03.000Z ERROR [image-processor] java.lang.OutOfMemoryError: Java heap space
2026-03-09T10:10:03.100Z ERROR [image-processor] at java.awt.image.DataBufferByte.<init>(DataBufferByte.java:92)
2026-03-09T10:10:03.200Z ERROR [image-processor] at java.awt.image.ComponentSampleModel.createDataBuffer(ComponentSampleModel.java:415)
2026-03-09T10:10:03.300Z ERROR [image-processor] Failed to process image
2026-03-09T10:10:03.400Z ERROR [image-processor] Lambda function failed with OutOfMemoryError
"""
    
    s3.put_object(
        Bucket=LOG_BUCKET,
        Key='image-processor/2026-03-09/memory-error.log',
        Body=log_content.encode('utf-8')
    )
    print("✓ Uploaded log file to S3")
    
    historical_incident = {
        "incident_id": "inc-2026-02-10-mem789",
        "timestamp": "2026-02-10T16:45:00Z",
        "service_name": "image-processor",
        "error_type": "Lambda OutOfMemoryError",
        "root_cause": "Lambda function configured with 512MB memory trying to process 15MB+ images",
        "resolution": "Increased Lambda memory from 512MB to 2048MB. Issue resolved immediately.",
        "resolution_time_minutes": 3,
        "commands_executed": [
            "aws lambda update-function-configuration --function-name image-processor --memory-size 2048"
        ],
        "preventive_actions": "Added input validation to reject images > 10MB. Set up CloudWatch alarm for memory usage > 80%."
    }
    
    kb_document = f"""# Incident Report: Lambda Memory Exhaustion - Image Processor

**Incident ID:** {historical_incident['incident_id']}
**Date:** {historical_incident['timestamp']}
**Service:** {historical_incident['service_name']}
**Severity:** High

## Problem
{historical_incident['root_cause']}

## Root Cause
The image-processor Lambda function was configured with only 512MB of memory. When processing large images (15MB+), the Java heap space was exhausted during image transformation operations.

## Resolution
{historical_incident['resolution']}

### Commands Executed
```bash
{chr(10).join(historical_incident['commands_executed'])}
```

## Resolution Time
{historical_incident['resolution_time_minutes']} minutes

## Why This Works
- Increasing Lambda memory also increases CPU allocation
- More memory allows larger images to be processed in-memory
- 2048MB provides 4x the original capacity

## Preventive Measures
- {historical_incident['preventive_actions']}
- Consider using streaming processing for very large images
- Implement image size limits at API Gateway level

## Cost Impact
Increasing memory from 512MB to 2048MB increases cost by 4x, but prevents failures. Monitor usage and optimize if needed.
"""
    
    with open('kb_incident_lambda_memory.md', 'w') as f:
        f.write(kb_document)
    
    print("✓ Created Knowledge Base document: kb_incident_lambda_memory.md")
    print(f"\nTest this scenario with:")
    print(f'  Service: image-processor')
    print(f'  Error: OutOfMemoryError: Java heap space')
    print(f'  Log: s3://{LOG_BUCKET}/image-processor/2026-03-09/memory-error.log')
    print()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CREATING SIMPLE POC SCENARIOS WITH KNOWLEDGE BASE")
    print("="*80 + "\n")
    
    create_dynamodb_throttling_scenario()
    create_rds_connection_scenario()
    create_lambda_memory_scenario()
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print("\n3 scenarios created with logs and Knowledge Base documents:")
    print("\n1. DynamoDB Throttling (user-service)")
    print("   - KB shows: Enable auto-scaling resolved it in 8 minutes")
    print("   - Suggested fix: Enable auto-scaling")
    print("\n2. RDS Connection Timeout (order-service)")
    print("   - KB shows: Restarting after 5 minutes resolved it")
    print("   - Suggested fix: Wait 5 minutes, then restart service")
    print("\n3. Lambda Memory Error (image-processor)")
    print("   - KB shows: Increasing memory to 2048MB resolved it in 3 minutes")
    print("   - Suggested fix: Increase Lambda memory")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Upload KB documents to Knowledge Base (if you have one configured)")
    print("2. Test scenarios using the test script")
    print("3. Verify emails show similar past incidents and suggested fixes")
    print()
