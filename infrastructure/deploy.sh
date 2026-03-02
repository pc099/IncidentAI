#!/bin/bash

# AI-Powered Incident Response System - Deployment Script
# This script packages Lambda functions and deploys the CloudFormation stack

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="incident-response-system-${ENVIRONMENT}"
KB_STACK_NAME="incident-response-kb-${ENVIRONMENT}"
DEPLOYMENT_BUCKET="incident-response-deployment-$(aws sts get-caller-identity --query Account --output text)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Incident Response System Deployment${NC}"
echo -e "${GREEN}Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}Region: ${AWS_REGION}${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install AWS CLI."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.11 or later."
    exit 1
fi

if ! command -v zip &> /dev/null; then
    print_error "zip command not found. Please install zip utility."
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi

print_status "Prerequisites check passed."

# Create deployment bucket if it doesn't exist
print_status "Creating deployment bucket if needed..."
if ! aws s3 ls "s3://${DEPLOYMENT_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    print_status "Deployment bucket already exists: ${DEPLOYMENT_BUCKET}"
else
    aws s3 mb "s3://${DEPLOYMENT_BUCKET}" --region "${AWS_REGION}"
    print_status "Created deployment bucket: ${DEPLOYMENT_BUCKET}"
fi

# Create lambda packages directory
LAMBDA_PACKAGES_DIR="lambda-packages/${ENVIRONMENT}"
mkdir -p "${LAMBDA_PACKAGES_DIR}"

# Package API Validation Lambda
print_status "Packaging API Validation Lambda..."
cd src
zip -r "../${LAMBDA_PACKAGES_DIR}/api-validation.zip" \
    api/__init__.py \
    api/incident_validator.py \
    __init__.py \
    -x "*.pyc" "*__pycache__*" "*.git*"
cd ..

# Package Orchestrator Lambda with all dependencies
print_status "Packaging Orchestrator Lambda..."
TEMP_DIR=$(mktemp -d)
cp -r src/* "${TEMP_DIR}/"

# Install dependencies to temp directory
if [ -f requirements.txt ]; then
    pip install -r requirements.txt -t "${TEMP_DIR}" --platform manylinux2014_aarch64 --only-binary=:all: || \
    pip install -r requirements.txt -t "${TEMP_DIR}"
fi

# Create zip from temp directory
cd "${TEMP_DIR}"
zip -r "${OLDPWD}/${LAMBDA_PACKAGES_DIR}/orchestrator.zip" . \
    -x "*.pyc" "*__pycache__*" "*.git*" "*test*"
cd "${OLDPWD}"
rm -rf "${TEMP_DIR}"

print_status "Lambda packages created successfully."

# Upload Lambda packages to S3
print_status "Uploading Lambda packages to S3..."
aws s3 cp "${LAMBDA_PACKAGES_DIR}/api-validation.zip" \
    "s3://${DEPLOYMENT_BUCKET}/lambda-packages/${ENVIRONMENT}/api-validation.zip"
aws s3 cp "${LAMBDA_PACKAGES_DIR}/orchestrator.zip" \
    "s3://${DEPLOYMENT_BUCKET}/lambda-packages/${ENVIRONMENT}/orchestrator.zip"

print_status "Lambda packages uploaded successfully."

# Deploy main CloudFormation stack
print_status "Deploying main CloudFormation stack..."
aws cloudformation deploy \
    --template-file infrastructure/cloudformation/incident-response-system.yaml \
    --stack-name "${STACK_NAME}" \
    --parameter-overrides file://infrastructure/cloudformation/parameters-${ENVIRONMENT}.json \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "${AWS_REGION}" \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    print_status "Main stack deployed successfully."
else
    print_error "Main stack deployment failed."
    exit 1
fi

# Get stack outputs
print_status "Retrieving stack outputs..."
API_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

API_KEY_ID=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

LOG_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='LogBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

KB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

DYNAMODB_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='DynamoDBTableName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}")

# Get API Key value
API_KEY_VALUE=$(aws apigateway get-api-key \
    --api-key "${API_KEY_ID}" \
    --include-value \
    --query "value" \
    --output text \
    --region "${AWS_REGION}")

# Verify SES email identity
print_status "Checking SES email identity..."
SENDER_EMAIL=$(grep -A 1 '"ParameterKey": "SenderEmail"' infrastructure/cloudformation/parameters-${ENVIRONMENT}.json | grep ParameterValue | cut -d'"' -f4)

if aws ses get-identity-verification-attributes \
    --identities "${SENDER_EMAIL}" \
    --region "${AWS_REGION}" \
    --query "VerificationAttributes.\"${SENDER_EMAIL}\".VerificationStatus" \
    --output text | grep -q "Success"; then
    print_status "SES email identity verified: ${SENDER_EMAIL}"
else
    print_warning "SES email identity NOT verified: ${SENDER_EMAIL}"
    print_warning "Please verify the email address by running:"
    echo "  aws ses verify-email-identity --email-address ${SENDER_EMAIL} --region ${AWS_REGION}"
    echo "  Then check your email and click the verification link."
fi

# Upload sample data to Knowledge Base bucket
print_status "Uploading sample data to Knowledge Base..."
if [ -d "test_data/knowledge_base" ]; then
    aws s3 sync test_data/knowledge_base/ "s3://${KB_BUCKET}/incidents/" --region "${AWS_REGION}"
    print_status "Sample data uploaded to Knowledge Base bucket."
else
    print_warning "Sample data directory not found. Skipping Knowledge Base data upload."
fi

# Run smoke tests
print_status "Running smoke tests..."
if [ -f "scripts/verify_setup.py" ]; then
    python3 scripts/verify_setup.py --environment "${ENVIRONMENT}" --region "${AWS_REGION}" || \
        print_warning "Smoke tests failed. Please check the logs."
else
    print_warning "Smoke test script not found. Skipping smoke tests."
fi

# Save deployment info
DEPLOYMENT_INFO_FILE="deployment-info-${ENVIRONMENT}.json"
cat > "${DEPLOYMENT_INFO_FILE}" <<EOF
{
  "environment": "${ENVIRONMENT}",
  "region": "${AWS_REGION}",
  "stack_name": "${STACK_NAME}",
  "api_endpoint": "${API_ENDPOINT}",
  "api_key_id": "${API_KEY_ID}",
  "api_key_value": "${API_KEY_VALUE}",
  "log_bucket": "${LOG_BUCKET}",
  "kb_bucket": "${KB_BUCKET}",
  "dynamodb_table": "${DYNAMODB_TABLE}",
  "deployment_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

print_status "Deployment info saved to ${DEPLOYMENT_INFO_FILE}"

# Print summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API Endpoint: ${API_ENDPOINT}"
echo "API Key ID: ${API_KEY_ID}"
echo "API Key Value: ${API_KEY_VALUE}"
echo "Log Bucket: ${LOG_BUCKET}"
echo "Knowledge Base Bucket: ${KB_BUCKET}"
echo "DynamoDB Table: ${DYNAMODB_TABLE}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Verify SES email identity if not already done"
echo "2. Set up Bedrock Knowledge Base (see infrastructure/cloudformation/bedrock-knowledge-base.yaml)"
echo "3. Upload sample incidents to Knowledge Base"
echo "4. Test the API endpoint with a sample incident"
echo ""
echo "For testing, run:"
echo "  python3 scripts/simulate_incidents.py --environment ${ENVIRONMENT}"
echo ""
echo -e "${GREEN}Deployment information saved to: ${DEPLOYMENT_INFO_FILE}${NC}"
