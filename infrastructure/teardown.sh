#!/bin/bash

# AI-Powered Incident Response System - Teardown Script
# This script removes all deployed resources

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
STACK_NAME="incident-response-system-${ENVIRONMENT}"
DEPLOYMENT_BUCKET="incident-response-deployment-$(aws sts get-caller-identity --query Account --output text)"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Incident Response System Teardown${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"
echo -e "${YELLOW}Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}========================================${NC}"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Confirm deletion
echo -e "${RED}WARNING: This will delete all resources for environment: ${ENVIRONMENT}${NC}"
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_status "Teardown cancelled."
    exit 0
fi

# Get stack outputs before deletion
print_status "Retrieving stack outputs..."
LOG_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='LogBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

KB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseBucketName'].OutputValue" \
    --output text \
    --region "${AWS_REGION}" 2>/dev/null || echo "")

# Empty S3 buckets before deletion
if [ -n "$LOG_BUCKET" ]; then
    print_status "Emptying log bucket: ${LOG_BUCKET}"
    aws s3 rm "s3://${LOG_BUCKET}" --recursive --region "${AWS_REGION}" || \
        print_warning "Failed to empty log bucket"
fi

if [ -n "$KB_BUCKET" ]; then
    print_status "Emptying Knowledge Base bucket: ${KB_BUCKET}"
    aws s3 rm "s3://${KB_BUCKET}" --recursive --region "${AWS_REGION}" || \
        print_warning "Failed to empty KB bucket"
fi

# Delete CloudFormation stack
print_status "Deleting CloudFormation stack: ${STACK_NAME}"
aws cloudformation delete-stack \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}"

print_status "Waiting for stack deletion to complete..."
aws cloudformation wait stack-delete-complete \
    --stack-name "${STACK_NAME}" \
    --region "${AWS_REGION}" || \
    print_warning "Stack deletion may have failed. Check AWS Console."

# Clean up deployment bucket
print_status "Cleaning up deployment bucket..."
aws s3 rm "s3://${DEPLOYMENT_BUCKET}/lambda-packages/${ENVIRONMENT}/" --recursive --region "${AWS_REGION}" || \
    print_warning "Failed to clean deployment bucket"

# Clean up local files
print_status "Cleaning up local deployment files..."
rm -f "deployment-info-${ENVIRONMENT}.json"
rm -rf "lambda-packages/${ENVIRONMENT}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Teardown Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
print_status "All resources for environment '${ENVIRONMENT}' have been removed."
print_warning "Note: Bedrock Knowledge Base must be deleted manually if created."
