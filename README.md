# AI-Powered Incident Response System

An intelligent incident response system using AWS Strands Agents framework and Amazon Bedrock to automatically analyze operational failures, identify root causes, and provide actionable remediation steps.

## Architecture

The system uses four specialized AI agents orchestrated via AWS Strands:
- **Log Analysis Agent**: Retrieves and analyzes logs to identify error patterns
- **Root Cause Agent**: Determines the most likely root cause with confidence scoring
- **Fix Recommendation Agent**: Generates actionable remediation steps
- **Communication Agent**: Creates summaries for different stakeholder audiences

## Prerequisites

- Python 3.11 or higher
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Virtual environment tool (venv or virtualenv)

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 3. Configure AWS Credentials

```bash
aws configure
```

### 4. Set Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `AWS_REGION`: Your AWS region (default: us-east-1)
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `LOG_BUCKET_NAME`: S3 bucket name for logs

### 5. Run Infrastructure Setup

```bash
python scripts/setup_infrastructure.py
```

This will create:
- S3 bucket for log storage with lifecycle policies
- DynamoDB table for incident history
- SES email identity (requires verification)
- IAM roles with least-privilege permissions

### 6. Verify SES Email

Check your email inbox for the SES verification link and click it. Then verify:

```bash
python scripts/check_ses_status.py
```

## Project Structure

```
.
├── src/
│   ├── agents/              # AI agent implementations
│   ├── infrastructure/      # AWS infrastructure setup
│   └── orchestrator/        # Strands orchestrator
├── tests/                   # Test suite
├── scripts/                 # Setup and utility scripts
├── requirements.txt         # Python dependencies
└── setup.py                # Package configuration
```

## AWS Resources Created

### S3 Bucket
- **Name**: `incident-response-logs` (configurable)
- **Lifecycle**: Standard-IA after 30 days, delete after 90 days
- **Encryption**: AES256 server-side encryption
- **Versioning**: Enabled

### DynamoDB Table
- **Name**: `incident-history`
- **Partition Key**: `incident_id` (String)
- **Sort Key**: `timestamp` (String)
- **GSI**: `service-timestamp-index` (service_name, timestamp)
- **Billing**: On-demand (cost optimized)
- **TTL**: 90 days
- **Encryption**: KMS

### IAM Roles
- **Lambda Execution Role**: Permissions for S3, DynamoDB, SES, Bedrock
- **Orchestrator Role**: Permissions for agent invocation

### SES
- **Email Identity**: `incidents@example.com` (requires verification)
- **Configuration Set**: `incident-response-emails`

## Cost Optimization

The system is designed to operate within AWS Free Tier limits:
- S3: Lifecycle policies reduce storage costs
- DynamoDB: On-demand billing, no provisioned capacity
- Lambda: ARM-based runtime for cost efficiency
- Bedrock: Token usage tracking and limits

## Development

### Running Tests

```bash
pytest tests/
```

### Property-Based Tests

The system uses Hypothesis for property-based testing:

```bash
pytest tests/ -k property
```

## Deployment

### Quick Start (15 minutes)

See [infrastructure/QUICK_START.md](infrastructure/QUICK_START.md) for a rapid deployment guide.

### Full Deployment

For complete deployment instructions, see [infrastructure/DEPLOYMENT_GUIDE.md](infrastructure/DEPLOYMENT_GUIDE.md).

**Linux/Mac:**
```bash
cd infrastructure
chmod +x deploy.sh
./deploy.sh dev
```

**Windows:**
```powershell
cd infrastructure
.\deploy.ps1 -Environment dev
```

The deployment script will:
1. Package Lambda functions
2. Upload to S3
3. Deploy CloudFormation stack
4. Verify SES email identity
5. Upload sample data
6. Run smoke tests

### Infrastructure as Code

All infrastructure is defined in CloudFormation templates:
- **Main Stack**: `infrastructure/cloudformation/incident-response-system.yaml`
- **Bedrock KB**: `infrastructure/cloudformation/bedrock-knowledge-base.yaml`

See [infrastructure/README.md](infrastructure/README.md) for details.

## Testing the System

After deployment, test the system:

```bash
python3 scripts/simulate_incidents.py --environment dev
```

This will:
- Create sample log files
- Trigger incidents via API Gateway
- Verify end-to-end processing
- Check email delivery

## Monitoring

Access the CloudWatch Dashboard:
- Go to AWS Console → CloudWatch → Dashboards
- Open: `IncidentResponse-dev`

Metrics tracked:
- Incident volume
- Processing time
- Confidence scores
- Agent success rates
- Token usage

## Teardown

To remove all deployed resources:

```bash
cd infrastructure
./teardown.sh dev
```

## Documentation

- [Deployment Guide](infrastructure/DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [Quick Start](infrastructure/QUICK_START.md) - 15-minute setup guide
- [Configuration Reference](infrastructure/CONFIGURATION_REFERENCE.md) - All configuration options
- [Infrastructure README](infrastructure/README.md) - IaC documentation

## Next Steps

1. ✅ Infrastructure setup complete
2. ✅ All agents implemented
3. ✅ Testing framework in place
4. ✅ Deployment automation ready
5. 🔄 Deploy to your AWS account
6. 🔄 Set up Bedrock Knowledge Base
7. 🔄 Integrate with your monitoring tools

## License

MIT
