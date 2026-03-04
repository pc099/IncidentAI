# Quick Start Guide

Get the Enhanced AI-Powered Incident Response System running in under 15 minutes.

## Prerequisites

- AWS Account with Bedrock access enabled
- Python 3.11+
- AWS CLI configured
- 4GB RAM minimum

## 1. Clone and Setup (2 minutes)

```bash
git clone <repository-url>
cd enhanced-incident-response

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

## 2. Configure Environment (3 minutes)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env  # or your preferred editor
```

**Minimum required settings:**
```bash
AWS_REGION=us-east-1
SENDER_EMAIL=your-email@example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
```

## 3. Deploy Infrastructure (8 minutes)

**Linux/Mac:**
```bash
cd infrastructure
chmod +x deploy-enhanced.sh
./deploy-enhanced.sh dev
```

**Windows:**
```powershell
cd infrastructure
.\deploy-enhanced.ps1 -Environment dev -SenderEmail "your-email@example.com"
```

The deployment script will:
- ✅ Create AWS resources (Lambda, API Gateway, DynamoDB, etc.)
- ✅ Package and deploy the enhanced system
- ✅ Configure WebSocket streaming
- ✅ Set up monitoring dashboards
- ✅ Run smoke tests

## 4. Verify Deployment (1 minute)

Check your email for SES verification link and click it.

## 5. Run Demo (1 minute)

```bash
# Full demo with all incident types
python demo_enhanced_system.py

# Or test specific scenario
python demo_enhanced_system.py configuration_error
```

## Expected Demo Output

```
🚀 ENHANCED AI-POWERED INCIDENT RESPONSE SYSTEM DEMO
================================================================

✅ All enhanced components initialized successfully

🔥 CACHE WARMING DEMONSTRATION
✅ Cache warming completed - ready for parallel execution

📋 DEMO INCIDENT 1/4: CONFIGURATION_ERROR
📨 Incident Alert Received
   Service: payment-processor
   Error: Lambda deployment failed: missing DATABASE_URL...
   Severity: HIGH

🔄 Starting Enhanced Processing...

📊 PROCESSING RESULTS
⏱️  Total Time: 12.3s
⚡ Parallel Efficiency Gain: 34.2%

💰 CACHE PERFORMANCE
   Bedrock Cache Hit Rate: 75.0%
   Semantic Cache Hit Rate: 45.0%
   Cost Savings: $0.0234

🎯 CONFIDENCE ROUTING
   Action: Update environment variable
   Confidence: 88.5%
   Routing: notify_and_execute
   ✅ Automated execution approved
```

## Key URLs (from deployment output)

- **REST API**: `https://your-api-id.execute-api.us-east-1.amazonaws.com/dev`
- **WebSocket**: `wss://your-websocket-id.execute-api.us-east-1.amazonaws.com/dev`
- **Dashboard**: CloudWatch dashboard link

## Test the System

### Submit Test Incident

```bash
curl -X POST "https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/incident" \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "test-service",
    "timestamp": "2025-03-04T10:30:00Z",
    "error_message": "Service health check failed",
    "log_location": "s3://test-logs/service/"
  }'
```

### Monitor Processing

1. **CloudWatch Dashboard**: Real-time metrics
2. **WebSocket Demo**: `python demo_websocket_client.py`
3. **Slack Notifications**: Check your configured channel

## Performance Validation

After running the demo, you should see:

| Metric | Target | Typical Result |
|--------|--------|----------------|
| Processing Time | <30s | 12-25s |
| Parallel Efficiency | >30% | 32-38% |
| Cache Hit Rate | >50% | 60-75% |
| Cost Reduction | >60% | 65-80% |

## Troubleshooting

### Common Issues

**"Bedrock access denied"**
```bash
# Enable model access in AWS Console
aws bedrock list-foundation-models --region us-east-1
```

**"SES email not verified"**
- Check your email for verification link
- Or verify manually: `aws ses verify-email-identity --email-address your-email@example.com`

**"Redis connection failed"**
- ElastiCache is optional for demo
- Set `REDIS_ENDPOINT=""` in .env to disable

**"Lambda timeout"**
- Increase timeout in CloudFormation template
- Or reduce incident complexity for testing

### Get Help

- **Issues**: GitHub Issues
- **Docs**: `docs/` directory
- **Logs**: CloudWatch Logs for detailed debugging

## Next Steps

1. **Explore Features**: Try different incident types
2. **Customize Agents**: Modify agent behavior in `src/agents/`
3. **Add Integrations**: Connect your monitoring tools
4. **Scale Up**: Deploy to staging/production environments
5. **Monitor Performance**: Use CloudWatch dashboards

## Production Checklist

Before production deployment:

- [ ] Configure proper IAM roles with least privilege
- [ ] Set up multi-AZ deployment for high availability
- [ ] Configure backup and disaster recovery
- [ ] Set up proper monitoring and alerting
- [ ] Conduct security review
- [ ] Load test with expected incident volume
- [ ] Train team on system operation
- [ ] Document incident response procedures

## Competition Demo Tips

For maximum impact in competitions:

1. **Start with Architecture**: Show the system diagram
2. **Highlight Differentiators**: Parallel processing, caching, confidence routing
3. **Live Demo**: Process real incidents with streaming
4. **Show Metrics**: Performance improvements and cost savings
5. **Explain Business Value**: MTTR reduction, cost optimization, responsible AI

**Demo Script**: Use `demo_enhanced_system.py` for consistent, impressive demonstrations that showcase all key features in under 5 minutes.

You're now ready to demonstrate a competition-winning AI incident response system! 🚀