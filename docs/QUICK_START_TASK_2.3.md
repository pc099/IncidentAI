# Quick Start: Task 2.3 - Populate Knowledge Base

## ✅ Status: Implementation Complete

All code is written, tested, and ready. Just needs AWS infrastructure to execute.

## 🚀 Execute in 4 Steps

### Step 1: Configure AWS Credentials
```bash
aws configure
```
Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1).

### Step 2: Set Environment Variables
```bash
# Copy example file
cp .env.example .env

# Edit .env and set:
# - AWS_ACCOUNT_ID=your-account-id
# - AWS_REGION=us-east-1
# - KB_DATA_SOURCE_BUCKET_NAME=incident-response-kb-data
```

### Step 3: Deploy Infrastructure
```bash
python scripts/setup_infrastructure.py
```
This creates the Knowledge Base and S3 bucket (takes ~2 minutes).

### Step 4: Populate Knowledge Base
```bash
python scripts/populate_kb_samples.py
```
This uploads 15 sample incidents and triggers ingestion (takes ~1 minute).

### Step 5: Verify (Optional)
```bash
# Wait 5-10 minutes for ingestion to complete, then:
python scripts/test_kb_query.py
```

## 📊 What Gets Created

- **15 Sample Incidents**
  - 5 Configuration Errors (Lambda, API Gateway, IAM, Step Functions, SES)
  - 5 Resource Exhaustion (Lambda memory, DynamoDB throttling, RDS storage)
  - 5 Dependency Failures (External APIs, RDS connections, SNS, S3)

- **AWS Services Covered**
  - Lambda, DynamoDB, RDS, API Gateway, Step Functions, SES, SNS, S3

## 🧪 Tests

All 13 tests pass:
```bash
pytest tests/test_populate_kb_samples.py -v
```

## 📚 Documentation

- **Detailed Guide**: `docs/TASK_2.3_EXECUTION_GUIDE.md`
- **Sample Incidents**: `docs/SAMPLE_INCIDENTS.md`
- **Usage Instructions**: `scripts/README_POPULATE_KB.md`
- **Implementation Summary**: `TASK_2.3_SUMMARY.md`

## ⚠️ Prerequisites

Before running, ensure:
- ✅ Python 3.11+ installed
- ✅ AWS CLI installed and configured
- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ AWS account with Bedrock access

## 🔧 Troubleshooting

**Error: Knowledge Base not found**
→ Run `python scripts/setup_infrastructure.py` first

**Error: AWS_ACCOUNT_ID not set**
→ Set in `.env` file or export as environment variable

**Error: Access Denied**
→ Verify AWS credentials have Bedrock and S3 permissions

## 📝 Requirements Satisfied

✅ Requirement 3.5: Historical incident data for RAG  
✅ Requirement 3.6: Similar past incidents with resolutions  
✅ Requirement 11.1: Configuration error scenarios  
✅ Requirement 11.2: Resource exhaustion scenarios  
✅ Requirement 11.3: Dependency failure scenarios  

## ➡️ Next Steps

After successful population:
1. Wait 5-10 minutes for ingestion
2. Verify with `python scripts/test_kb_query.py`
3. Proceed to Task 3: Implement API Gateway endpoint
4. Later: Task 7: Implement Root Cause Agent with RAG

---

**Ready to execute when AWS infrastructure is available!**
