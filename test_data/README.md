# Test Data for AI-Powered Incident Response System

This directory contains comprehensive test data for validating the incident response system end-to-end.

## Directory Structure

```
test_data/
├── logs/                    # Sample log files for 5 AWS failure scenarios
│   ├── api_gateway_timeout.log
│   ├── rds_storage_full.log
│   ├── lambda_deployment_failure.log
│   ├── dynamodb_throttling.log
│   ├── step_functions_failure.log
│   └── README.md
│
└── knowledge_base/          # 15 historical incidents for RAG testing
    ├── configuration_errors/     (5 incidents)
    ├── resource_exhaustion/      (5 incidents)
    ├── dependency_failures/      (5 incidents)
    └── README.md
```

## Quick Start

### 1. Upload Test Logs to S3

```bash
python scripts/upload_test_logs.py
```

This uploads 5 sample log files covering:
- API Gateway timeout
- RDS storage full
- Lambda deployment failure
- DynamoDB throttling
- Step Functions execution failure

### 2. Upload Knowledge Base Test Data

```bash
python scripts/upload_kb_test_data.py
```

This uploads 15 historical incident documents (5 per category) and triggers Knowledge Base ingestion.

### 3. Simulate Incidents

```bash
# List available scenarios
python scripts/simulate_incidents.py --list

# Simulate single scenario
python scripts/simulate_incidents.py --scenario api_gateway_timeout

# Simulate all scenarios
python scripts/simulate_incidents.py --all
```

## Test Coverage

### Log Files (5 scenarios)

| Scenario | Service | Failure Type | Requirements |
|----------|---------|--------------|--------------|
| API Gateway Timeout | payment-api-gateway | Dependency failure | 11.3 |
| RDS Storage Full | production-db-instance | Resource exhaustion | 11.2 |
| Lambda Deployment | payment-processor | Configuration error | 11.1 |
| DynamoDB Throttling | user-sessions-table | Resource exhaustion | 11.2 |
| Step Functions Failure | order-processing-workflow | Dependency failure | 11.3 |

### Knowledge Base Documents (15 incidents)

| Category | Count | Confidence Range | Requirements |
|----------|-------|------------------|--------------|
| Configuration Errors | 5 | 85-98% | 3.5, 3.6 |
| Resource Exhaustion | 5 | 89-97% | 3.5, 3.6 |
| Dependency Failures | 5 | 87-99% | 3.5, 3.6 |

## End-to-End Testing Workflow

### Step 1: Setup Infrastructure
```bash
python scripts/setup_infrastructure.py
```

### Step 2: Upload Test Data
```bash
python scripts/upload_test_logs.py
python scripts/upload_kb_test_data.py
```

### Step 3: Verify Setup
```bash
python scripts/verify_setup.py
```

### Step 4: Run Simulations
```bash
# Test single scenario
python scripts/simulate_incidents.py --scenario lambda_deployment --verify

# Test all scenarios
python scripts/simulate_incidents.py --all --delay 10
```

### Step 5: Verify Results

Check that for each incident:
1. ✅ API Gateway returns 202 with incident_id
2. ✅ Orchestrator invokes all 4 agents sequentially
3. ✅ Root Cause Agent retrieves similar incidents from Knowledge Base
4. ✅ Enhanced alert delivered via SES
5. ✅ Incident stored in DynamoDB
6. ✅ Incident indexed in Knowledge Base for future RAG

## Expected Outcomes

### API Gateway Timeout Scenario

**Input**: Alert for payment-api-gateway timeout

**Expected Analysis**:
- Root Cause: Dependency failure (external gateway timeout)
- Confidence: 70-90%
- Similar Incidents: `external_api_timeout.json`
- Fix: Implement circuit breaker, increase timeout

**Expected Email**: HTML alert with:
- Root cause: External payment gateway timeout
- Immediate actions: Increase timeout, verify gateway health
- Commands: AWS CLI commands to update configuration
- Similar incidents: Past gateway timeout resolutions

### RDS Storage Full Scenario

**Input**: Alert for production-db-instance storage full

**Expected Analysis**:
- Root Cause: Resource exhaustion (storage capacity)
- Confidence: 80-95%
- Similar Incidents: `rds_storage_full.json`
- Fix: Increase storage, enable auto-scaling

**Expected Email**: HTML alert with:
- Root cause: Database storage capacity exceeded
- Immediate actions: Increase allocated storage
- Commands: `aws rds modify-db-instance`
- Preventive measures: Enable storage auto-scaling

### Lambda Deployment Scenario

**Input**: Alert for payment-processor deployment failure

**Expected Analysis**:
- Root Cause: Configuration error (package size)
- Confidence: 85-95%
- Similar Incidents: Configuration error incidents
- Fix: Remove unnecessary dependencies, use Lambda Layers

**Expected Email**: HTML alert with:
- Root cause: Deployment package exceeds size limit
- Immediate actions: Optimize package size
- Commands: Package optimization steps
- Preventive measures: Use Lambda Layers

## Validation Checklist

After running simulations, verify:

- [ ] All 5 scenarios trigger successfully (202 response)
- [ ] Each scenario generates unique incident_id
- [ ] Log Analysis Agent extracts error patterns correctly
- [ ] Root Cause Agent retrieves relevant similar incidents
- [ ] Root Cause Agent assigns appropriate confidence scores
- [ ] Fix Recommendation Agent provides actionable steps
- [ ] Communication Agent generates both technical and business summaries
- [ ] SES delivers HTML emails with proper formatting
- [ ] DynamoDB stores complete incident records
- [ ] Knowledge Base indexes new incidents for future RAG
- [ ] CloudWatch logs show agent execution traces
- [ ] CloudWatch metrics track processing time and success rate

## Troubleshooting

### Logs Not Found in S3
**Solution**: Run `python scripts/upload_test_logs.py` first

### Knowledge Base Returns No Results
**Solution**: Wait for ingestion to complete (check with `aws bedrock-agent get-ingestion-job`)

### API Gateway Returns 400
**Solution**: Verify API Gateway endpoint and authentication configured

### Email Not Received
**Solution**: Check SES email identity verified and not in sandbox mode

### Low Confidence Scores
**Solution**: Ensure Knowledge Base has sufficient historical data

## Performance Benchmarks

Expected processing times:

- API Gateway response: <1 second
- Log Analysis Agent: 2-5 seconds
- Root Cause Agent: 3-7 seconds (includes KB query)
- Fix Recommendation Agent: 2-4 seconds
- Communication Agent: 1-3 seconds
- Email Delivery: 1-2 seconds
- **Total end-to-end**: <20 seconds

## Requirements Validation

This test data validates:

- **1.1, 1.2**: Alert detection and ingestion
- **2.1-2.7**: Log retrieval and analysis
- **3.5, 3.6**: Historical pattern integration via RAG
- **11.1**: Configuration error identification (>70% confidence)
- **11.2**: Resource exhaustion identification (>70% confidence)
- **11.3**: Dependency failure identification (>70% confidence)

## Maintenance

### Adding New Test Scenarios

1. Create log file in `test_data/logs/`
2. Add scenario to `scripts/simulate_incidents.py`
3. Upload logs: `python scripts/upload_test_logs.py`
4. Test: `python scripts/simulate_incidents.py --scenario <new_scenario>`

### Adding New Historical Incidents

1. Create JSON file in appropriate `knowledge_base/` category
2. Upload: `python scripts/upload_kb_test_data.py`
3. Verify retrieval: `python scripts/test_kb_query.py --query "<search_term>"`

## Related Documentation

- [Log Files README](logs/README.md)
- [Knowledge Base README](knowledge_base/README.md)
- [Simulation Script Guide](../scripts/README_SIMULATE_INCIDENTS.md)
- [Infrastructure Setup](../docs/INFRASTRUCTURE_SETUP.md)
