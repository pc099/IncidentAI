# Incident Simulation Script

This script generates synthetic alert events for various AWS failure scenarios and triggers the incident response system via API Gateway.

## Prerequisites

1. **Infrastructure Setup**: Ensure all infrastructure is deployed:
   - S3 bucket for logs
   - API Gateway endpoint
   - Lambda functions
   - DynamoDB table
   - Bedrock Knowledge Base

2. **Test Logs Uploaded**: Run the upload script first:
   ```bash
   python scripts/upload_test_logs.py
   ```

3. **API Gateway Configuration**: Set environment variables:
   ```bash
   export API_GATEWAY_ENDPOINT="https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/incidents"
   export API_GATEWAY_KEY="your-api-key"  # Optional if using IAM auth
   ```

## Usage

### List Available Scenarios
```bash
python scripts/simulate_incidents.py --list
```

Output:
```
Available Incident Scenarios:
============================================================

api_gateway_timeout:
  Service: payment-api-gateway
  Description: API Gateway timeout to backend payment service
  Alert Source: CloudWatch

rds_storage_full:
  Service: production-db-instance
  Description: PostgreSQL RDS instance out of storage space
  Alert Source: CloudWatch

lambda_deployment:
  Service: payment-processor
  Description: Lambda function deployment package too large
  Alert Source: EventBridge

dynamodb_throttling:
  Service: user-sessions-table
  Description: DynamoDB table throttled due to insufficient write capacity
  Alert Source: CloudWatch

step_functions_failure:
  Service: order-processing-workflow
  Description: Step Functions workflow failed due to Lambda timeout
  Alert Source: EventBridge
```

### Simulate Single Scenario
```bash
python scripts/simulate_incidents.py --scenario api_gateway_timeout
```

### Simulate All Scenarios
```bash
python scripts/simulate_incidents.py --all
```

### Simulate with Verification
```bash
python scripts/simulate_incidents.py --scenario rds_storage_full --verify
```

### Custom API Endpoint
```bash
python scripts/simulate_incidents.py \
  --scenario lambda_deployment \
  --api-endpoint "https://custom-api.example.com/incidents" \
  --api-key "your-api-key"
```

### Adjust Delay Between Scenarios
```bash
python scripts/simulate_incidents.py --all --delay 10
```

## Scenarios

### 1. API Gateway Timeout
- **Scenario**: `api_gateway_timeout`
- **Service**: payment-api-gateway
- **Failure Type**: Dependency failure
- **Expected Root Cause**: External payment gateway timeout
- **Expected Confidence**: 70-90%

### 2. RDS Storage Full
- **Scenario**: `rds_storage_full`
- **Service**: production-db-instance
- **Failure Type**: Resource exhaustion
- **Expected Root Cause**: Database storage capacity exceeded
- **Expected Confidence**: 80-95%

### 3. Lambda Deployment Failure
- **Scenario**: `lambda_deployment`
- **Service**: payment-processor
- **Failure Type**: Configuration error
- **Expected Root Cause**: Deployment package size exceeds limit
- **Expected Confidence**: 85-95%

### 4. DynamoDB Throttling
- **Scenario**: `dynamodb_throttling`
- **Service**: user-sessions-table
- **Failure Type**: Resource exhaustion
- **Expected Root Cause**: Insufficient provisioned write capacity
- **Expected Confidence**: 80-95%

### 5. Step Functions Failure
- **Scenario**: `step_functions_failure`
- **Service**: order-processing-workflow
- **Failure Type**: Dependency failure
- **Expected Root Cause**: Lambda function timeout in workflow
- **Expected Confidence**: 75-90%

## Output

### Successful Request
```
============================================================
Simulating Incident: api_gateway_timeout
============================================================
Description: API Gateway timeout to backend payment service
Service: payment-api-gateway
Alert Source: CloudWatch

Payload:
{
  "service_name": "payment-api-gateway",
  "timestamp": "2025-03-01T15:30:00.123456Z",
  "error_message": "API Gateway integration timeout: Endpoint request timed out after 29 seconds",
  "log_location": "s3://incident-logs-bucket/logs/api-gateway/2025/03/01/api_gateway_timeout.log",
  "alert_source": "CloudWatch"
}

Sending POST request to: https://api-id.execute-api.us-east-1.amazonaws.com/prod/incidents

Response Status: 202
Response Time: 0.45s
✅ Incident triggered successfully!
Incident ID: inc-2025-03-01-abc123
Status: processing
Message: Incident analysis initiated
```

### Failed Request
```
Response Status: 400
Response Time: 0.23s
❌ Request failed!
Response: {"error": "Invalid payload", "details": "Missing required field: service_name"}
```

## Verification

After triggering incidents, verify processing by checking:

1. **DynamoDB Table**: Query `incident-history` table for incident records
   ```bash
   aws dynamodb get-item \
     --table-name incident-history \
     --key '{"incident_id": {"S": "inc-2025-03-01-abc123"}}'
   ```

2. **CloudWatch Logs**: Check agent execution logs
   ```bash
   aws logs tail /aws/lambda/incident-orchestrator --follow
   ```

3. **SES Email**: Check email inbox for enhanced alert

4. **Bedrock Knowledge Base**: Verify incident indexed for future RAG
   ```bash
   aws bedrock-agent-runtime retrieve \
     --knowledge-base-id <kb-id> \
     --retrieval-query text="API Gateway timeout"
   ```

## Troubleshooting

### Error: API Gateway endpoint not configured
**Solution**: Set the `API_GATEWAY_ENDPOINT` environment variable or use `--api-endpoint` flag.

### Error: 403 Forbidden
**Solution**: Provide valid API key using `--api-key` flag or `API_GATEWAY_KEY` environment variable.

### Error: 400 Bad Request - Invalid payload
**Solution**: Ensure test logs are uploaded to S3 first using `upload_test_logs.py`.

### Error: Connection timeout
**Solution**: Check that API Gateway and Lambda functions are deployed and accessible.

## Requirements Validation

This script validates:
- **Requirement 1.1**: System receives alerts within 5 seconds
- **Requirement 1.2**: System processes EventBridge and CloudWatch events
- **Requirement 1.6**: Orchestrator invoked within 2 seconds of alert receipt

## Integration with Testing

Use this script in integration tests:

```python
import subprocess
import json

def test_end_to_end_incident_processing():
    # Trigger incident
    result = subprocess.run(
        ['python', 'scripts/simulate_incidents.py', 
         '--scenario', 'api_gateway_timeout'],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    # Additional assertions...
```
