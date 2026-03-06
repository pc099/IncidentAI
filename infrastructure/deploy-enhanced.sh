#!/bin/bash

# Enhanced AI-Powered Incident Response System Deployment Script
# Deploys the competition-winning architecture with all enhancements

set -e

# Configuration
ENVIRONMENT=${1:-dev}
STACK_NAME="enhanced-incident-response-${ENVIRONMENT}"
REGION=${AWS_REGION:-us-east-1}
SENDER_EMAIL=${SENDER_EMAIL:-""}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-""}
BEDROCK_KB_ID=${BEDROCK_KB_ID:-""}
REDIS_ENDPOINT=${REDIS_ENDPOINT:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Enhanced AI-Powered Incident Response System Deployment${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "Region: ${GREEN}${REGION}${NC}"
echo -e "Stack Name: ${GREEN}${STACK_NAME}${NC}"
echo ""

# Validate required parameters
if [ -z "$SENDER_EMAIL" ]; then
    echo -e "${RED}❌ Error: SENDER_EMAIL environment variable is required${NC}"
    echo "   Set it with: export SENDER_EMAIL=your-email@example.com"
    exit 1
fi

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo -e "${YELLOW}⚠️  Warning: SLACK_WEBHOOK_URL not set - Teams notifications will be disabled${NC}"
    SLACK_WEBHOOK_URL="https://your-org.webhook.office.com/webhookb2/placeholder"
fi

if [ -z "$BEDROCK_KB_ID" ]; then
    echo -e "${YELLOW}⚠️  Warning: BEDROCK_KB_ID not set - Knowledge Base features will be limited${NC}"
    BEDROCK_KB_ID="placeholder-kb-id"
fi

# Check AWS CLI and credentials
echo -e "${BLUE}🔍 Checking AWS credentials...${NC}"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: AWS credentials not configured${NC}"
    echo "   Run: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "   Account ID: ${GREEN}${ACCOUNT_ID}${NC}"

# Check Bedrock model access
echo -e "${BLUE}🤖 Checking Bedrock model access...${NC}"
if aws bedrock list-foundation-models --region ${REGION} > /dev/null 2>&1; then
    echo -e "   ✅ Bedrock access confirmed"
else
    echo -e "${YELLOW}⚠️  Warning: Bedrock access not confirmed - ensure model access is enabled${NC}"
fi

# Create deployment bucket if it doesn't exist
DEPLOYMENT_BUCKET="enhanced-incident-deployment-${ACCOUNT_ID}-${REGION}"
echo -e "${BLUE}📦 Preparing deployment bucket...${NC}"

if ! aws s3 ls "s3://${DEPLOYMENT_BUCKET}" > /dev/null 2>&1; then
    echo -e "   Creating deployment bucket: ${DEPLOYMENT_BUCKET}"
    aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region ${REGION}
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket ${DEPLOYMENT_BUCKET} \
        --versioning-configuration Status=Enabled
else
    echo -e "   ✅ Deployment bucket exists: ${DEPLOYMENT_BUCKET}"
fi

# Package Lambda function
echo -e "${BLUE}📦 Packaging Lambda function...${NC}"
LAMBDA_ZIP="enhanced-incident-response-${ENVIRONMENT}.zip"

# Create temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo -e "   Using temp directory: ${TEMP_DIR}"

# Copy source code
cp -r ../src ${TEMP_DIR}/
cp ../requirements.txt ${TEMP_DIR}/

# Install dependencies
echo -e "   Installing Python dependencies..."
cd ${TEMP_DIR}
pip install -r requirements.txt -t . --quiet

# Create deployment package
echo -e "   Creating deployment package..."
zip -r ${LAMBDA_ZIP} . -x "*.pyc" "__pycache__/*" "*.git*" > /dev/null

# Upload to S3
echo -e "   Uploading to S3..."
aws s3 cp ${LAMBDA_ZIP} "s3://${DEPLOYMENT_BUCKET}/${LAMBDA_ZIP}"

# Get S3 object version
LAMBDA_VERSION=$(aws s3api head-object \
    --bucket ${DEPLOYMENT_BUCKET} \
    --key ${LAMBDA_ZIP} \
    --query VersionId --output text)

echo -e "   ✅ Lambda package uploaded (version: ${LAMBDA_VERSION})"

# Clean up temp directory
cd - > /dev/null
rm -rf ${TEMP_DIR}

# Deploy CloudFormation stack
echo -e "${BLUE}☁️  Deploying CloudFormation stack...${NC}"

# Check if stack exists
if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} > /dev/null 2>&1; then
    echo -e "   Updating existing stack..."
    OPERATION="update-stack"
else
    echo -e "   Creating new stack..."
    OPERATION="create-stack"
fi

# Deploy stack
aws cloudformation ${OPERATION} \
    --stack-name ${STACK_NAME} \
    --template-body file://cloudformation/enhanced-incident-response.yaml \
    --parameters \
        ParameterKey=Environment,ParameterValue=${ENVIRONMENT} \
        ParameterKey=SenderEmail,ParameterValue=${SENDER_EMAIL} \
        ParameterKey=TeamsWebhookUrl,ParameterValue=${SLACK_WEBHOOK_URL} \
        ParameterKey=BedrockKnowledgeBaseId,ParameterValue=${BEDROCK_KB_ID} \
        ParameterKey=RedisClusterEndpoint,ParameterValue=${REDIS_ENDPOINT} \
    --capabilities CAPABILITY_NAMED_IAM \
    --region ${REGION}

echo -e "   Waiting for stack deployment to complete..."
aws cloudformation wait stack-${OPERATION%-stack}-complete \
    --stack-name ${STACK_NAME} \
    --region ${REGION}

# Update Lambda function code
echo -e "${BLUE}🔄 Updating Lambda function code...${NC}"
FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
    --output text | cut -d':' -f7)

aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --s3-bucket ${DEPLOYMENT_BUCKET} \
    --s3-key ${LAMBDA_ZIP} \
    --s3-object-version ${LAMBDA_VERSION} \
    --region ${REGION} > /dev/null

echo -e "   ✅ Lambda function updated"

# Get stack outputs
echo -e "${BLUE}📋 Retrieving deployment information...${NC}"
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --query 'Stacks[0].Outputs')

REST_API_URL=$(echo ${OUTPUTS} | jq -r '.[] | select(.OutputKey=="RestApiUrl") | .OutputValue')
WEBSOCKET_URL=$(echo ${OUTPUTS} | jq -r '.[] | select(.OutputKey=="WebSocketUrl") | .OutputValue')
DASHBOARD_URL=$(echo ${OUTPUTS} | jq -r '.[] | select(.OutputKey=="DashboardUrl") | .OutputValue')

# Verify SES email
echo -e "${BLUE}📧 Verifying SES email address...${NC}"
if aws ses get-identity-verification-attributes \
    --identities ${SENDER_EMAIL} \
    --region ${REGION} \
    --query "VerificationAttributes.\"${SENDER_EMAIL}\".VerificationStatus" \
    --output text | grep -q "Success"; then
    echo -e "   ✅ Email address verified: ${SENDER_EMAIL}"
else
    echo -e "${YELLOW}⚠️  Email verification required for: ${SENDER_EMAIL}${NC}"
    echo -e "   Sending verification email..."
    aws ses verify-email-identity --email-address ${SENDER_EMAIL} --region ${REGION}
    echo -e "   📧 Check your email and click the verification link"
fi

# Run smoke tests
echo -e "${BLUE}🧪 Running smoke tests...${NC}"
echo -e "   Testing REST API endpoint..."

# Test API Gateway
TEST_PAYLOAD='{
    "service_name": "test-service",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "error_message": "Smoke test error",
    "log_location": "s3://test-bucket/logs/"
}'

# Get AWS credentials for API call
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
AWS_SESSION_TOKEN=$(aws configure get aws_session_token)

# Make authenticated API call (simplified - in production use proper AWS SigV4)
if curl -s -X POST "${REST_API_URL}/incident" \
    -H "Content-Type: application/json" \
    -d "${TEST_PAYLOAD}" > /dev/null; then
    echo -e "   ✅ REST API responding"
else
    echo -e "${YELLOW}⚠️  REST API test failed - check API Gateway configuration${NC}"
fi

# Display deployment summary
echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}====================================${NC}"
echo ""
echo -e "${BLUE}📊 Deployment Summary:${NC}"
echo -e "   Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "   Stack Name: ${GREEN}${STACK_NAME}${NC}"
echo -e "   Region: ${GREEN}${REGION}${NC}"
echo ""
echo -e "${BLUE}🔗 Endpoints:${NC}"
echo -e "   REST API: ${GREEN}${REST_API_URL}${NC}"
echo -e "   WebSocket: ${GREEN}${WEBSOCKET_URL}${NC}"
echo -e "   Dashboard: ${GREEN}${DASHBOARD_URL}${NC}"
echo ""
echo -e "${BLUE}🎯 Next Steps:${NC}"
echo -e "   1. Verify SES email if not already done"
echo -e "   2. Configure Bedrock Knowledge Base with sample data"
echo -e "   3. Test the system with: ${GREEN}python ../demo_enhanced_system.py${NC}"
echo -e "   4. Monitor performance in CloudWatch Dashboard"
echo ""
echo -e "${BLUE}💡 Demo Commands:${NC}"
echo -e "   # Run full demo"
echo -e "   ${GREEN}python ../demo_enhanced_system.py${NC}"
echo ""
echo -e "   # Test specific incident type"
echo -e "   ${GREEN}python ../demo_enhanced_system.py configuration_error${NC}"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo -e "   Architecture: ../docs/ARCHITECTURE.md"
echo -e "   API Reference: ../docs/API.md"
echo -e "   Troubleshooting: ../docs/TROUBLESHOOTING.md"
echo ""
echo -e "${GREEN}✨ Enhanced system ready for competition demonstration!${NC}"