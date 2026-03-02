# AI-Powered Incident Response System - Deployment Script (PowerShell)
# This script packages Lambda functions and deploys the CloudFormation stack

param(
    [string]$Environment = "dev",
    [string]$Region = $env:AWS_REGION
)

if (-not $Region) {
    $Region = "us-east-1"
}

$ErrorActionPreference = "Stop"

# Configuration
$StackName = "incident-response-system-$Environment"
$KBStackName = "incident-response-kb-$Environment"
$AccountId = (aws sts get-caller-identity --query Account --output text)
$DeploymentBucket = "incident-response-deployment-$AccountId"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Incident Response System Deployment" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
Write-Status "Checking prerequisites..."

if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI not found. Please install AWS CLI."
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found. Please install Python 3.11 or later."
    exit 1
}

# Verify AWS credentials
try {
    aws sts get-caller-identity | Out-Null
    Write-Status "Prerequisites check passed."
} catch {
    Write-Error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
}

# Create deployment bucket if it doesn't exist
Write-Status "Creating deployment bucket if needed..."
try {
    aws s3 ls "s3://$DeploymentBucket" 2>&1 | Out-Null
    Write-Status "Deployment bucket already exists: $DeploymentBucket"
} catch {
    aws s3 mb "s3://$DeploymentBucket" --region $Region
    Write-Status "Created deployment bucket: $DeploymentBucket"
}

# Create lambda packages directory
$LambdaPackagesDir = "lambda-packages\$Environment"
New-Item -ItemType Directory -Force -Path $LambdaPackagesDir | Out-Null

# Package API Validation Lambda
Write-Status "Packaging API Validation Lambda..."
Push-Location src
Compress-Archive -Path `
    "api\__init__.py", `
    "api\incident_validator.py", `
    "__init__.py" `
    -DestinationPath "..\$LambdaPackagesDir\api-validation.zip" -Force
Pop-Location

# Package Orchestrator Lambda with all dependencies
Write-Status "Packaging Orchestrator Lambda..."
$TempDir = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath()) -Name ([System.Guid]::NewGuid().ToString())
Copy-Item -Path "src\*" -Destination $TempDir -Recurse

# Install dependencies to temp directory
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt -t $TempDir --platform manylinux2014_aarch64 --only-binary=:all:
    if ($LASTEXITCODE -ne 0) {
        pip install -r requirements.txt -t $TempDir
    }
}

# Create zip from temp directory
Push-Location $TempDir
Get-ChildItem -Recurse | Where-Object { 
    $_.FullName -notmatch '\.pyc$|__pycache__|\.git|test' 
} | Compress-Archive -DestinationPath "$PSScriptRoot\..\$LambdaPackagesDir\orchestrator.zip" -Force
Pop-Location
Remove-Item -Path $TempDir -Recurse -Force

Write-Status "Lambda packages created successfully."

# Upload Lambda packages to S3
Write-Status "Uploading Lambda packages to S3..."
aws s3 cp "$LambdaPackagesDir\api-validation.zip" `
    "s3://$DeploymentBucket/lambda-packages/$Environment/api-validation.zip"
aws s3 cp "$LambdaPackagesDir\orchestrator.zip" `
    "s3://$DeploymentBucket/lambda-packages/$Environment/orchestrator.zip"

Write-Status "Lambda packages uploaded successfully."

# Deploy main CloudFormation stack
Write-Status "Deploying main CloudFormation stack..."
aws cloudformation deploy `
    --template-file infrastructure\cloudformation\incident-response-system.yaml `
    --stack-name $StackName `
    --parameter-overrides "file://infrastructure/cloudformation/parameters-$Environment.json" `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $Region `
    --no-fail-on-empty-changeset

if ($LASTEXITCODE -eq 0) {
    Write-Status "Main stack deployed successfully."
} else {
    Write-Error "Main stack deployment failed."
    exit 1
}

# Get stack outputs
Write-Status "Retrieving stack outputs..."
$ApiEndpoint = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" `
    --output text `
    --region $Region

$ApiKeyId = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" `
    --output text `
    --region $Region

$LogBucket = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='LogBucketName'].OutputValue" `
    --output text `
    --region $Region

$KBBucket = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseBucketName'].OutputValue" `
    --output text `
    --region $Region

$DynamoDBTable = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --query "Stacks[0].Outputs[?OutputKey=='DynamoDBTableName'].OutputValue" `
    --output text `
    --region $Region

# Get API Key value
$ApiKeyValue = aws apigateway get-api-key `
    --api-key $ApiKeyId `
    --include-value `
    --query "value" `
    --output text `
    --region $Region

# Verify SES email identity
Write-Status "Checking SES email identity..."
$ParamsContent = Get-Content "infrastructure\cloudformation\parameters-$Environment.json" | ConvertFrom-Json
$SenderEmail = ($ParamsContent | Where-Object { $_.ParameterKey -eq "SenderEmail" }).ParameterValue

$VerificationStatus = aws ses get-identity-verification-attributes `
    --identities $SenderEmail `
    --region $Region `
    --query "VerificationAttributes.`"$SenderEmail`".VerificationStatus" `
    --output text

if ($VerificationStatus -eq "Success") {
    Write-Status "SES email identity verified: $SenderEmail"
} else {
    Write-Warning "SES email identity NOT verified: $SenderEmail"
    Write-Warning "Please verify the email address by running:"
    Write-Host "  aws ses verify-email-identity --email-address $SenderEmail --region $Region"
    Write-Host "  Then check your email and click the verification link."
}

# Upload sample data to Knowledge Base bucket
Write-Status "Uploading sample data to Knowledge Base..."
if (Test-Path "test_data\knowledge_base") {
    aws s3 sync test_data\knowledge_base\ "s3://$KBBucket/incidents/" --region $Region
    Write-Status "Sample data uploaded to Knowledge Base bucket."
} else {
    Write-Warning "Sample data directory not found. Skipping Knowledge Base data upload."
}

# Run smoke tests
Write-Status "Running smoke tests..."
if (Test-Path "scripts\verify_setup.py") {
    python scripts\verify_setup.py --environment $Environment --region $Region
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Smoke tests failed. Please check the logs."
    }
} else {
    Write-Warning "Smoke test script not found. Skipping smoke tests."
}

# Save deployment info
$DeploymentInfoFile = "deployment-info-$Environment.json"
$DeploymentInfo = @{
    environment = $Environment
    region = $Region
    stack_name = $StackName
    api_endpoint = $ApiEndpoint
    api_key_id = $ApiKeyId
    api_key_value = $ApiKeyValue
    log_bucket = $LogBucket
    kb_bucket = $KBBucket
    dynamodb_table = $DynamoDBTable
    deployment_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

$DeploymentInfo | Out-File -FilePath $DeploymentInfoFile -Encoding UTF8

Write-Status "Deployment info saved to $DeploymentInfoFile"

# Print summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "API Endpoint: $ApiEndpoint"
Write-Host "API Key ID: $ApiKeyId"
Write-Host "API Key Value: $ApiKeyValue"
Write-Host "Log Bucket: $LogBucket"
Write-Host "Knowledge Base Bucket: $KBBucket"
Write-Host "DynamoDB Table: $DynamoDBTable"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Verify SES email identity if not already done"
Write-Host "2. Set up Bedrock Knowledge Base (see infrastructure/cloudformation/bedrock-knowledge-base.yaml)"
Write-Host "3. Upload sample incidents to Knowledge Base"
Write-Host "4. Test the API endpoint with a sample incident"
Write-Host ""
Write-Host "For testing, run:"
Write-Host "  python scripts\simulate_incidents.py --environment $Environment"
Write-Host ""
Write-Host "Deployment information saved to: $DeploymentInfoFile" -ForegroundColor Green
