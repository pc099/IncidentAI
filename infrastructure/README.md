# Infrastructure as Code

This directory contains Infrastructure as Code (IaC) templates and deployment scripts for the AI-Powered Incident Response System.

## Contents

### CloudFormation Templates

- **`cloudformation/incident-response-system.yaml`** - Main CloudFormation template
  - Defines all AWS resources (S3, DynamoDB, Lambda, API Gateway, IAM, CloudWatch)
  - Configurable via parameters
  - Outputs deployment information

- **`cloudformation/bedrock-knowledge-base.yaml`** - Bedrock Knowledge Base configuration
  - Stores configuration in SSM Parameter Store
  - Provides setup instructions
  - Note: Bedrock KB requires manual setup via console/CLI

- **`cloudformation/parameters-dev.json`** - Development environment parameters
- **`cloudformation/parameters-prod.json`** - Production environment parameters

### Deployment Scripts

- **`deploy.sh`** - Bash deployment script (Linux/Mac)
  - Packages Lambda functions
  - Uploads to S3
  - Deploys CloudFormation stack
  - Verifies SES email
  - Runs smoke tests

- **`deploy.ps1`** - PowerShell deployment script (Windows)
  - Same functionality as deploy.sh
  - Windows-compatible commands

- **`teardown.sh`** - Cleanup script
  - Empties S3 buckets
  - Deletes CloudFormation stack
  - Removes local deployment files

### Documentation

- **`DEPLOYMENT_GUIDE.md`** - Complete deployment guide
  - Prerequisites
  - Step-by-step instructions
  - Post-deployment configuration
  - Troubleshooting

- **`QUICK_START.md`** - 15-minute quick start
  - Minimal steps to get running
  - Essential configuration only

- **`CONFIGURATION_REFERENCE.md`** - Complete configuration reference
  - All parameters explained
  - Environment variables
  - IAM permissions
  - Cost optimization settings

## Quick Start

### 1. Prerequisites

- AWS CLI configured
- Python 3.11+
- Bedrock model access enabled

### 2. Configure Parameters

Edit `cloudformation/parameters-dev.json`:
```json
{
  "ParameterKey": "SenderEmail",
  "ParameterValue": "your-email@example.com"
}
```

### 3. Deploy

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh dev
```

**Windows:**
```powershell
.\deploy.ps1 -Environment dev
```

### 4. Verify

Check your email for SES verification link, then:
```bash
python3 ../scripts/simulate_incidents.py --environment dev
```

## Architecture

```
┌─────────────────┐
│   CloudWatch    │
│   EventBridge   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Gateway    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Lambda Functions│
│  - Validation   │
│  - Orchestrator │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌──────┐ ┌────────┐ ┌────┐ ┌────────┐
│  S3  │ │DynamoDB│ │SES │ │Bedrock │
└──────┘ └────────┘ └────┘ └────────┘
```

## Resources Created

### Compute
- 2 Lambda functions (API validation, orchestrator)

### Storage
- 2 S3 buckets (logs, Knowledge Base data)
- 1 DynamoDB table (incident history)

### Networking
- 1 API Gateway REST API
- 1 API Key

### Monitoring
- 1 CloudWatch Dashboard
- 3 CloudWatch Alarms

### Security
- 2 IAM Roles (Lambda execution, Bedrock KB)
- Least-privilege policies

### AI/ML
- Bedrock model access (Claude, Titan Embeddings)
- Bedrock Knowledge Base (manual setup required)

## Cost Estimate

### Free Tier (First 12 Months)
- Lambda: 1M requests/month free
- DynamoDB: 25 GB storage + 25 WCU/RCU free
- S3: 5 GB storage + 20K GET requests free
- Bedrock: Model-specific free tier (first 3 months)
- CloudWatch: 10 custom metrics free

**Estimated Cost:** $0-5/month (within Free Tier)

### After Free Tier
- Lambda: ~$1-5/month
- DynamoDB: ~$2-10/month
- S3: ~$1-3/month
- Bedrock: ~$5-20/month (depends on usage)
- CloudWatch: ~$1-2/month

**Estimated Cost:** $10-40/month (typical usage)

## Deployment Environments

### Development (dev)
- Lower rate limits (100 req/min)
- Shorter log retention (7 days)
- Smaller Lambda memory allocations
- Cost-optimized settings

### Staging (staging)
- Medium rate limits (200 req/min)
- Standard log retention (14 days)
- Production-like configuration
- Testing environment

### Production (prod)
- Higher rate limits (500+ req/min)
- Extended log retention (30 days)
- Optimized Lambda memory
- High availability settings

## Security

### Encryption
- All data encrypted at rest (S3, DynamoDB)
- All data encrypted in transit (HTTPS/TLS)

### Access Control
- IAM roles with least-privilege permissions
- API Gateway authentication (API key + IAM)
- S3 buckets block public access

### Compliance
- PII redaction in logs
- 90-day data retention (GDPR-friendly)
- Audit logging via CloudWatch

## Monitoring

### CloudWatch Dashboard
- Incident volume
- Processing time
- Confidence scores
- Agent success rates
- Token usage

### CloudWatch Alarms
- High latency (>60s)
- High error rate (>20%)
- Token usage warning (>80% Free Tier)

### CloudWatch Logs
- All Lambda invocations
- Structured JSON logging
- 7-day retention (configurable)

## Maintenance

### Update Stack
```bash
aws cloudformation update-stack \
    --stack-name incident-response-system-dev \
    --template-body file://cloudformation/incident-response-system.yaml \
    --parameters file://cloudformation/parameters-dev.json \
    --capabilities CAPABILITY_NAMED_IAM
```

### Update Lambda Code
```bash
# Repackage and upload
./deploy.sh dev
```

### View Logs
```bash
aws logs tail /aws/lambda/incident-orchestrator-dev --follow
```

### Check Stack Status
```bash
aws cloudformation describe-stacks \
    --stack-name incident-response-system-dev \
    --query "Stacks[0].StackStatus"
```

## Troubleshooting

### Deployment Failed
1. Check CloudFormation events:
   ```bash
   aws cloudformation describe-stack-events \
       --stack-name incident-response-system-dev \
       --max-items 10
   ```
2. Verify IAM permissions
3. Check resource limits (e.g., Lambda concurrent executions)

### Lambda Timeout
1. Check CloudWatch Logs
2. Verify Bedrock model access
3. Increase timeout in template (max 900s)

### Email Not Sending
1. Verify SES email identity
2. Check SES sandbox status
3. Review CloudWatch Logs for SES errors

### High Costs
1. Check CloudWatch metrics for token usage
2. Review S3 lifecycle policies
3. Verify DynamoDB is using on-demand billing
4. Check for unexpected Lambda invocations

## Best Practices

### Development
- Use `dev` environment for testing
- Enable debug logging (`LOG_LEVEL=DEBUG`)
- Test with sample data before production

### Staging
- Mirror production configuration
- Test with production-like data
- Validate performance and costs

### Production
- Use separate AWS account (recommended)
- Enable CloudWatch alarms
- Set up automated backups
- Monitor costs regularly
- Review security settings

### CI/CD
- Automate deployments with GitHub Actions, GitLab CI, or AWS CodePipeline
- Run tests before deployment
- Use separate environments for dev/staging/prod
- Tag releases for rollback capability

## Support

### Documentation
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment guide
- [QUICK_START.md](QUICK_START.md) - 15-minute quick start
- [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) - Configuration reference

### AWS Resources
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)

### Troubleshooting
- Check CloudWatch Logs for errors
- Review CloudFormation events
- Verify IAM permissions
- Check AWS service quotas

## Contributing

When modifying infrastructure:

1. Update CloudFormation templates
2. Test in `dev` environment
3. Update documentation
4. Validate templates:
   ```bash
   aws cloudformation validate-template \
       --template-body file://cloudformation/incident-response-system.yaml
   ```
5. Deploy to `staging` for testing
6. Deploy to `prod` after validation

## License

See main project LICENSE file.
