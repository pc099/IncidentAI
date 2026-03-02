# Quick Start Guide

Get the AI-Powered Incident Response System up and running in 15 minutes.

## Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured
- Python 3.11+
- Email address for SES verification

## 5-Step Deployment

### 1. Configure Email Addresses

Edit `infrastructure/cloudformation/parameters-dev.json`:

```json
{
  "ParameterKey": "SenderEmail",
  "ParameterValue": "your-email@example.com"
},
{
  "ParameterKey": "OnCallEngineersEmail",
  "ParameterValue": "your-email@example.com"
}
```

### 2. Enable Bedrock Models

```bash
# Go to AWS Console → Bedrock → Model access
# Request access to:
# - anthropic.claude-3-sonnet-20240229-v1:0
# - amazon.titan-embed-text-v1
```

### 3. Run Deployment Script

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

### 4. Verify Email

Check your email inbox and click the SES verification link.

### 5. Test the System

```bash
python3 scripts/simulate_incidents.py --environment dev
```

Check your email for the incident alert!

## What's Next?

- Set up Bedrock Knowledge Base (see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#2-set-up-bedrock-knowledge-base))
- Upload historical incident data
- Integrate with your monitoring tools
- Customize fix recommendations

## Troubleshooting

**Deployment failed?**
- Check AWS credentials: `aws sts get-caller-identity`
- Verify Bedrock access is enabled
- Check CloudFormation events for errors

**Email not received?**
- Verify email identity in SES console
- Check CloudWatch Logs for errors
- Ensure SES is not in sandbox mode (or use verified addresses)

**Need help?**
See the full [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

## Clean Up

To remove all resources:

```bash
cd infrastructure
./teardown.sh dev
```

## Cost Estimate

With AWS Free Tier:
- **First 12 months:** ~$0-5/month (within Free Tier limits)
- **After Free Tier:** ~$10-30/month (depending on usage)

Main costs:
- Bedrock API calls (Claude invocations)
- DynamoDB on-demand requests
- S3 storage and requests
- Lambda invocations

Monitor costs in AWS Cost Explorer.
