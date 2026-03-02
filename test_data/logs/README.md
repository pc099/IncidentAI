# Test Log Files

This directory contains sample log files for testing the AI-Powered Incident Response System. Each log file represents a specific AWS failure scenario.

## Log Files

### 1. API Gateway Timeout (`api_gateway_timeout.log`)
- **Scenario**: API Gateway integration timeout to backend service
- **Failure Type**: Dependency failure
- **Key Indicators**:
  - 504 Gateway Timeout status
  - 29-second timeout threshold exceeded
  - Backend service unresponsive
  - Recent timeout pattern: 45 timeouts in 15 minutes

### 2. RDS Storage Full (`rds_storage_full.log`)
- **Scenario**: PostgreSQL RDS instance runs out of storage space
- **Failure Type**: Resource exhaustion
- **Key Indicators**:
  - Storage usage: 98.5% (98.5 GB / 100 GB)
  - Error: "No space left on device"
  - Write operations blocked
  - Auto-scaling not enabled

### 3. Lambda Deployment Failure (`lambda_deployment_failure.log`)
- **Scenario**: Lambda function deployment fails due to package size
- **Failure Type**: Configuration error
- **Key Indicators**:
  - Unzipped package size exceeds 250 MB limit
  - Package size: 52.3 MB (zipped)
  - Large dependencies: aws-sdk (45.2 MB)
  - Automatic rollback to previous version

### 4. DynamoDB Throttling (`dynamodb_throttling.log`)
- **Scenario**: DynamoDB table throttled due to insufficient write capacity
- **Failure Type**: Resource exhaustion
- **Key Indicators**:
  - ProvisionedThroughputExceededException
  - Write capacity: 5 WCU provisioned, 45 WCU consumed
  - 40 throttled requests
  - Auto-scaling not enabled

### 5. Step Functions Execution Failure (`step_functions_failure.log`)
- **Scenario**: Step Functions workflow fails due to Lambda function error
- **Failure Type**: Dependency failure
- **Key Indicators**:
  - States.TaskFailed error
  - Payment gateway connection timeout
  - 2 retry attempts exhausted
  - Execution duration: 12.8 seconds

## Usage

### Upload to S3
Use the upload script to push these logs to your S3 bucket:

```bash
python scripts/upload_test_logs.py
```

### S3 URIs
After upload, logs will be available at:
- `s3://<bucket>/logs/api-gateway/2025/03/01/api_gateway_timeout.log`
- `s3://<bucket>/logs/rds/2025/03/01/rds_storage_full.log`
- `s3://<bucket>/logs/lambda/2025/03/01/lambda_deployment_failure.log`
- `s3://<bucket>/logs/dynamodb/2025/03/01/dynamodb_throttling.log`
- `s3://<bucket>/logs/step-functions/2025/03/01/step_functions_failure.log`

### Testing with Incident Simulator
These logs are referenced by the incident simulation script:

```bash
python scripts/simulate_incidents.py --scenario api_gateway_timeout
python scripts/simulate_incidents.py --scenario rds_storage_full
python scripts/simulate_incidents.py --scenario lambda_deployment
python scripts/simulate_incidents.py --scenario dynamodb_throttling
python scripts/simulate_incidents.py --scenario step_functions_failure
```

## Log Format

All logs follow a consistent format:
```
YYYY-MM-DDTHH:MM:SS.sssZ LEVEL [Service] Message
```

- **Timestamp**: ISO 8601 format with milliseconds
- **Level**: INFO, WARN, ERROR
- **Service**: AWS service name (APIGateway, RDS, Lambda, DynamoDB, StepFunctions)
- **Message**: Detailed log message with context

## Requirements Validation

These logs support testing requirements:
- **11.1**: Configuration error scenarios (Lambda deployment)
- **11.2**: Resource exhaustion scenarios (RDS storage, DynamoDB throttling)
- **11.3**: Dependency failure scenarios (API Gateway timeout, Step Functions)
