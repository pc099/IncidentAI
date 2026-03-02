# Populating Knowledge Base with Sample Incidents

## Overview

The `populate_kb_samples.py` script creates and uploads 15 sample historical incidents to the Bedrock Knowledge Base for RAG-powered root cause analysis.

## Prerequisites

Before running this script, ensure the following are completed:

### 1. Environment Setup

Create a `.env` file from `.env.example` and set:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id-here
KB_DATA_SOURCE_BUCKET_NAME=incident-response-kb-data
```

### 2. AWS Infrastructure

Run the infrastructure setup script:

```bash
python scripts/setup_infrastructure.py
```

This creates:
- S3 bucket for Knowledge Base data source
- Bedrock Knowledge Base with Amazon Titan Embeddings
- S3 data source configuration
- IAM roles with required permissions

### 3. Verify Setup

Check that the Knowledge Base exists:

```bash
python scripts/test_kb_query.py
```

## Running the Script

Once prerequisites are met:

```bash
python scripts/populate_kb_samples.py
```

## What the Script Does

1. **Creates 15 Sample Incidents** covering:
   - Configuration errors (5 incidents)
   - Resource exhaustion (5 incidents)
   - Dependency failures (5 incidents)

2. **AWS Services Covered**:
   - Lambda (deployment, memory, concurrency)
   - DynamoDB (throttling, capacity)
   - RDS (storage, connections)
   - API Gateway (timeouts)
   - Step Functions (state machine errors)
   - SES (email verification)
   - SNS (delivery failures)
   - S3 (consistency)

3. **Uploads to S3**:
   - Each incident is formatted as a text document
   - Uploaded to `s3://incident-response-kb-data/incidents/`
   - Files named: `inc-YYYY-MM-DD-NNN.txt`

4. **Triggers Ingestion**:
   - Starts Knowledge Base ingestion job
   - Ingestion takes 5-10 minutes to complete
   - Documents are embedded and indexed for semantic search

## Expected Output

```
================================================================================
Populating Bedrock Knowledge Base with Sample Incidents
================================================================================

S3 Bucket: incident-response-kb-data
Knowledge Base ID: ABCDEFGHIJ
Data Source ID: KLMNOPQRST

Creating and uploading 15 sample incidents...

  • inc-2024-11-01-001 (configuration_error, Lambda)... ✓
  • inc-2024-11-05-002 (configuration_error, API Gateway)... ✓
  • inc-2024-11-10-003 (configuration_error, Lambda)... ✓
  • inc-2024-11-15-004 (configuration_error, Step Functions)... ✓
  • inc-2024-11-20-005 (configuration_error, SES)... ✓
  • inc-2024-11-23-006 (resource_exhaustion, Lambda)... ✓
  • inc-2024-11-25-007 (resource_exhaustion, DynamoDB)... ✓
  • inc-2024-11-28-008 (resource_exhaustion, RDS)... ✓
  • inc-2024-12-02-009 (resource_exhaustion, Lambda)... ✓
  • inc-2024-12-05-010 (resource_exhaustion, DynamoDB)... ✓
  • inc-2024-12-08-011 (dependency_failure, Lambda)... ✓
  • inc-2024-12-12-012 (dependency_failure, RDS)... ✓
  • inc-2024-12-15-013 (dependency_failure, Lambda)... ✓
  • inc-2024-12-18-014 (dependency_failure, SNS)... ✓
  • inc-2024-12-20-015 (dependency_failure, S3)... ✓

✓ Uploaded 15/15 incidents to S3

Starting Knowledge Base ingestion job...
✓ Ingestion job started: 12345678-abcd-efgh-ijkl-123456789012

Note: Ingestion may take 5-10 minutes to complete.
Check status in AWS Console: Bedrock → Knowledge Bases → Data Sources

================================================================================
Summary
================================================================================
Total Incidents: 15
  • Configuration Errors: 5
  • Resource Exhaustion: 5
  • Dependency Failures: 5

AWS Services Covered:
  • Lambda (deployment, memory, concurrency)
  • DynamoDB (throttling, capacity)
  • RDS (storage, connections)
  • API Gateway (timeouts)
  • Step Functions (state machine errors)
  • SES (email verification)
  • SNS (delivery failures)
  • S3 (consistency)

✓ Knowledge Base population complete!
Run scripts/test_kb_query.py to verify ingestion and test queries.
================================================================================
```

## Verification

After ingestion completes (wait 5-10 minutes), verify the data:

```bash
python scripts/test_kb_query.py
```

This will:
- Query the Knowledge Base for sample incidents
- Display similarity scores
- Verify hybrid search is working
- Show retrieved incident details

## Sample Incidents

See `docs/SAMPLE_INCIDENTS.md` for detailed descriptions of all 15 incidents.

## Troubleshooting

### Error: Knowledge Base not found

**Solution**: Run `python scripts/setup_infrastructure.py` first to create the Knowledge Base.

### Error: AWS_ACCOUNT_ID not set

**Solution**: Set the environment variable:
```bash
export AWS_ACCOUNT_ID=123456789012  # Unix/Mac
set AWS_ACCOUNT_ID=123456789012     # Windows CMD
$env:AWS_ACCOUNT_ID="123456789012"  # Windows PowerShell
```

Or add it to your `.env` file.

### Error: S3 bucket does not exist

**Solution**: The infrastructure setup script should create the bucket. Verify:
```bash
aws s3 ls | grep incident-response-kb-data
```

If missing, run `python scripts/setup_infrastructure.py` again.

### Ingestion job fails

**Solution**: Check IAM permissions. The Knowledge Base role needs:
- `s3:GetObject` on the data source bucket
- `s3:ListBucket` on the data source bucket
- `bedrock:InvokeModel` for Titan Embeddings

## Requirements Satisfied

This implementation satisfies:

- **Task 2.3**: Populate Knowledge Base with sample historical incidents
- **Requirement 3.5**: Historical incident data for RAG
- **Requirement 3.6**: Similar past incidents with resolutions
- **Requirement 11.1**: Configuration error scenarios
- **Requirement 11.2**: Resource exhaustion scenarios
- **Requirement 11.3**: Dependency failure scenarios

## Next Steps

After successful population:

1. Wait for ingestion to complete (5-10 minutes)
2. Run `python scripts/test_kb_query.py` to verify
3. Proceed to Task 7: Implement Root Cause Agent with RAG integration
