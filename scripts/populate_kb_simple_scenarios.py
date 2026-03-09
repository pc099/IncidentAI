"""
Populate Knowledge Base with Simple Historical Incidents

Creates 3 simple historical incidents that demonstrate RAG/KB value:
1. DynamoDB Throttling - resolved with auto-scaling
2. RDS Connection Timeout - resolved by waiting 5 mins then restart
3. Lambda Memory Exhaustion - resolved by increasing memory
"""

import boto3
import json
from datetime import datetime, timedelta

# Historical incidents to add to Knowledge Base
HISTORICAL_INCIDENTS = [
    {
        "incident_id": "inc-2026-02-15-abc123",
        "service_name": "user-service",
        "timestamp": "2026-02-15T14:30:00Z",
        "error_message": "ProvisionedThroughputExceededException on users-prod table",
        "category": "resource_exhaustion",
        "root_cause": {
            "description": "DynamoDB table exceeded provisioned read capacity during traffic spike",
            "category": "resource_exhaustion",
            "confidence_score": 95,
            "evidence": [
                "ConsumedReadCapacityUnits exceeded ProvisionedReadCapacityUnits",
                "ThrottledRequests metric spiked to 1200/min",
                "Traffic increased 300% during marketing campaign"
            ]
        },
        "resolution": {
            "actions_taken": [
                "Enabled DynamoDB auto-scaling for read capacity",
                "Set min capacity to 5, max capacity to 100",
                "Configured target utilization at 70%"
            ],
            "commands_executed": [
                "aws application-autoscaling register-scalable-target --service-namespace dynamodb --resource-id table/users-prod --scalable-dimension dynamodb:table:ReadCapacityUnits --min-capacity 5 --max-capacity 100",
                "aws application-autoscaling put-scaling-policy --service-namespace dynamodb --resource-id table/users-prod --scalable-dimension dynamodb:table:ReadCapacityUnits --policy-name UserTableReadScaling --policy-type TargetTrackingScaling --target-tracking-scaling-policy-configuration 'PredefinedMetricSpecification={PredefinedMetricType=DynamoDBReadCapacityUtilization},TargetValue=70.0'"
            ],
            "time_to_resolve": "8 minutes",
            "status": "resolved",
            "outcome": "Auto-scaling prevented future throttling incidents. No recurrence in 3 weeks."
        },
        "lessons_learned": [
            "Always enable auto-scaling for production DynamoDB tables",
            "Monitor capacity utilization during marketing campaigns",
            "Set target utilization at 70% to allow headroom for spikes"
        ]
    },
    {
        "incident_id": "inc-2026-02-20-xyz456",
        "service_name": "order-service",
        "timestamp": "2026-02-20T09:15:00Z",
        "error_message": "SQLTransientConnectionException: Connection timeout after 30s",
        "category": "dependency_failure",
        "root_cause": {
            "description": "RDS connection pool exhausted due to long-running queries",
            "category": "dependency_failure",
            "confidence_score": 90,
            "evidence": [
                "All 50 connections in pool were in use",
                "Average query time increased from 200ms to 8s",
                "Database CPU utilization at 95%"
            ]
        },
        "resolution": {
            "actions_taken": [
                "Waited 5 minutes for existing connections to timeout",
                "Restarted order-service to clear connection pool",
                "Killed long-running queries on database"
            ],
            "commands_executed": [
                "# Wait 5 minutes before restarting (critical!)",
                "aws ecs update-service --cluster prod-cluster --service order-service --force-new-deployment",
                "# On RDS: SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';"
            ],
            "time_to_resolve": "7 minutes",
            "status": "resolved",
            "outcome": "Service recovered. Added query timeout configuration to prevent future occurrences."
        },
        "lessons_learned": [
            "CRITICAL: Wait 5 minutes before restarting to allow connections to timeout",
            "Restarting immediately won't help if connections are still held",
            "Configure query timeouts at application level (30s max)",
            "Monitor database connection pool utilization"
        ]
    },
    {
        "incident_id": "inc-2026-02-10-mem789",
        "service_name": "image-processor",
        "timestamp": "2026-02-10T16:45:00Z",
        "error_message": "OutOfMemoryError: Java heap space during image processing",
        "category": "resource_exhaustion",
        "root_cause": {
            "description": "Lambda function ran out of memory processing large images",
            "category": "resource_exhaustion",
            "confidence_score": 98,
            "evidence": [
                "Lambda memory usage reached 512MB limit",
                "Processing 8K resolution images (15MB each)",
                "Java heap space exhausted during image resize operation"
            ]
        },
        "resolution": {
            "actions_taken": [
                "Increased Lambda memory from 512MB to 2048MB",
                "This also increased CPU allocation proportionally",
                "Verified processing works with new memory limit"
            ],
            "commands_executed": [
                "aws lambda update-function-configuration --function-name image-processor --memory-size 2048"
            ],
            "time_to_resolve": "3 minutes",
            "status": "resolved",
            "outcome": "Lambda now handles 8K images without issues. Processing time reduced from timeout to 12s."
        },
        "lessons_learned": [
            "Lambda memory also affects CPU allocation",
            "2048MB provides 4x the original capacity",
            "Cost increases 4x but prevents failures",
            "Consider adding image size validation before processing"
        ],
        "cost_impact": {
            "before": "$0.0000002 per invocation (512MB)",
            "after": "$0.0000008 per invocation (2048MB)",
            "justification": "4x cost increase acceptable to prevent failures and improve user experience"
        }
    }
]


def store_incident_in_dynamodb(incident: dict, table_name: str = "incident-history"):
    """Store historical incident in DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Add metadata
    incident['created_at'] = incident['timestamp']
    incident['ttl'] = int((datetime.now() + timedelta(days=365)).timestamp())
    
    # Store in DynamoDB
    table.put_item(Item=incident)
    print(f"✓ Stored {incident['incident_id']} in DynamoDB")


def create_kb_document(incident: dict) -> str:
    """Create a formatted document for Knowledge Base"""
    doc = f"""# Incident Report: {incident['incident_id']}

## Incident Details
- **Service**: {incident['service_name']}
- **Date**: {incident['timestamp']}
- **Error**: {incident['error_message']}
- **Category**: {incident['category']}
- **Status**: {incident['resolution']['status'].upper()}

## Root Cause Analysis
**Description**: {incident['root_cause']['description']}

**Confidence**: {incident['root_cause']['confidence_score']}%

**Evidence**:
"""
    
    for evidence in incident['root_cause']['evidence']:
        doc += f"- {evidence}\n"
    
    doc += f"""
## Resolution

**Time to Resolve**: {incident['resolution']['time_to_resolve']}

**Actions Taken**:
"""
    
    for action in incident['resolution']['actions_taken']:
        doc += f"- {action}\n"
    
    doc += "\n**Commands Executed**:\n```bash\n"
    for cmd in incident['resolution']['commands_executed']:
        doc += f"{cmd}\n"
    doc += "```\n"
    
    doc += f"\n**Outcome**: {incident['resolution']['outcome']}\n"
    
    doc += "\n## Lessons Learned\n"
    for lesson in incident['lessons_learned']:
        doc += f"- {lesson}\n"
    
    if 'cost_impact' in incident:
        doc += f"""
## Cost Impact
- **Before**: {incident['cost_impact']['before']}
- **After**: {incident['cost_impact']['after']}
- **Justification**: {incident['cost_impact']['justification']}
"""
    
    return doc


def upload_to_s3_for_kb(incident: dict, bucket_name: str = "incident-response-logs-867126415696"):
    """Upload incident document to S3 for Knowledge Base ingestion"""
    s3 = boto3.client('s3')
    
    # Create document
    doc_content = create_kb_document(incident)
    
    # Upload to S3 in kb-documents folder
    key = f"kb-documents/{incident['incident_id']}.md"
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=doc_content.encode('utf-8'),
        ContentType='text/markdown'
    )
    
    print(f"✓ Uploaded {incident['incident_id']}.md to S3 for KB ingestion")
    return f"s3://{bucket_name}/{key}"


def main():
    """Populate Knowledge Base with historical incidents"""
    print("=" * 60)
    print("Populating Knowledge Base with Simple Historical Incidents")
    print("=" * 60)
    
    for incident in HISTORICAL_INCIDENTS:
        print(f"\nProcessing {incident['incident_id']}...")
        
        # Store in DynamoDB
        try:
            store_incident_in_dynamodb(incident)
        except Exception as e:
            print(f"  ⚠ DynamoDB storage failed: {e}")
        
        # Upload to S3 for KB
        try:
            s3_location = upload_to_s3_for_kb(incident)
            print(f"  📄 Document: {s3_location}")
        except Exception as e:
            print(f"  ⚠ S3 upload failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Knowledge Base Population Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. If you have a Bedrock Knowledge Base configured:")
    print("   - Sync the S3 bucket to ingest these documents")
    print("   - Test KB queries to find similar incidents")
    print("\n2. Test the scenarios:")
    print("   python scripts/test_realistic_scenario.py 2  # DynamoDB throttling")
    print("\n3. Check email for 'Similar Past Incidents' section")


if __name__ == "__main__":
    main()
