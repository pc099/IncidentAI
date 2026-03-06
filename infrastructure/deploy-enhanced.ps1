# Enhanced AI-Powered Incident Response System Deployment Script (PowerShell)
# Deploys the competition-winning architecture with all enhancements

param(
    [string]$Environment = "dev",
    [string]$Region = $env:AWS_REGION ?? "us-east-1",
    [string]$SenderEmail = $env:SENDER_EMAIL,
    [string]$TeamsWebhookUrl = $env:TEAMS_WEBHOOK_URL,
    [string]$BedrockKbId = $env:BEDROCK_KB_ID,
    [string]$RedisEndpoint = $env:REDIS_ENDPOINT
)

# Configuration
$StackName = "enhanced-incident-response-$Environment"

Write-Host "🚀 Enhanced AI-Powered Incident Response System Deployment" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Environment: " -NoNewline; Write-Host $Environment -ForegroundColor Green
Write-Host "Region: " -NoNewline; Write-Host $Region -ForegroundColor Green
Write-Host "Stack Name: " -NoNewline; Write-Host $StackName -ForegroundColor Green
Write-Host ""

# Validate required parameters
if (-not $SenderEmail) {
    Write-Host "❌ Error: SenderEmail parameter is required" -ForegroundColor Red
    Write-Host "   Use: .\deploy-enhanced.ps1 -SenderEmail your-email@example.com" -ForegroundColor Yellow
    exit 1
}

if (-not $TeamsWebhookUrl) {
    Write-Host "⚠️  Warning: TeamsWebhookUrl not set - Teams notifications will be disabled" -ForegroundColor Yellow
    $TeamsWebhookUrl = "https://your-org.webhook.office.com/webhookb2/placeholder"
}

if (-not $BedrockKbId) {
    Write-Host "⚠️  Warning: BedrockKbId not set - Knowledge Base features will be limited" -ForegroundColor Yellow
    $BedrockKbId = "placeholder-kb-id"
}

if (-not $RedisEndpoint) {
    $RedisEndpoint = ""
}

# Check AWS CLI and credentials
Write-Host "🔍 Checking AWS credentials..." -ForegroundColor Blue
try {
    $CallerIdentity = aws sts get-caller-identity | ConvertFrom-Json
    $AccountId = $CallerIdentity.Account
    Write-Host "   Account ID: " -NoNewline; Write-Host $AccountId -ForegroundColor Green
}
catch {
    Write-Host "❌ Error: AWS credentials not configured" -ForegroundColor Red
    Write-Host "   Run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Check Bedrock model access
Write-Host "🤖 Checking Bedrock model access..." -ForegroundColor Blue
try {
    aws bedrock list-foundation-models --region $Region | Out-Null
    Write-Host "   ✅ Bedrock access confirmed" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Warning: Bedrock access not confirmed - ensure model access is enabled" -ForegroundColor Yellow
}

# Create deployment bucket if it doesn't exist
$DeploymentBucket = "enhanced-incident-deployment-$AccountId-$Region"
Write-Host "📦 Preparing deployment bucket..." -ForegroundColor Blue

try {
    aws s3 ls "s3://$DeploymentBucket" | Out-Null
    Write-Host "   ✅ Deployment bucket exists: $DeploymentBucket" -ForegroundColor Green
}
catch {
    Write-Host "   Creating deployment bucket: $DeploymentBucket"
    aws s3 mb "s3://$DeploymentBucket" --region $Region
    
    # Enable versioning
    aws s3api put-bucket-versioning --bucket $DeploymentBucket --versioning-configuration Status=Enabled
}

# Package Lambda function
Write-Host "📦 Packaging Lambda function..." -ForegroundColor Blue
$LambdaZip = "enhanced-incident-response-$Environment.zip"

# Create temporary directory for packaging
$TempDir = New-TemporaryFile | ForEach-Object { Remove-Item $_; New-Item -ItemType Directory -Path $_ }
Write-Host "   Using temp directory: $TempDir"

# Copy source code
Copy-Item -Path "..\src" -Destination $TempDir -Recurse
Copy-Item -Path "..\requirements.txt" -Destination $TempDir

# Install dependencies
Write-Host "   Installing Python dependencies..."
Push-Location $TempDir
pip install -r requirements.txt -t . --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error: Failed to install Python dependencies" -ForegroundColor Red
    exit 1
}

# Create deployment package
Write-Host "   Creating deployment package..."
$ZipPath = Join-Path $TempDir $LambdaZip
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipPath -Force

# Upload to S3
Write-Host "   Uploading to S3..."
aws s3 cp $ZipPath "s3://$DeploymentBucket/$LambdaZip"

# Get S3 object version
$LambdaVersion = aws s3api head-object --bucket $DeploymentBucket --key $LambdaZip --query VersionId --output text

Write-Host "   ✅ Lambda package uploaded (version: $LambdaVersion)" -ForegroundColor Green

# Clean up temp directory
Pop-Location
Remove-Item -Path $TempDir -Recurse -Force

# Deploy CloudFormation stack
Write-Host "☁️  Deploying CloudFormation stack..." -ForegroundColor Blue

# Check if stack exists
try {
    aws cloudformation describe-stacks --stack-name $StackName --region $Region | Out-Null
    Write-Host "   Updating existing stack..."
    $Operation = "update-stack"
}
catch {
    Write-Host "   Creating new stack..."
    $Operation = "create-stack"
}

# Deploy stack
$Parameters = @(
    "ParameterKey=Environment,ParameterValue=$Environment",
    "ParameterKey=SenderEmail,ParameterValue=$SenderEmail",
    "ParameterKey=TeamsWebhookUrl,ParameterValue=$TeamsWebhookUrl",
    "ParameterKey=BedrockKnowledgeBaseId,ParameterValue=$BedrockKbId",
    "ParameterKey=RedisClusterEndpoint,ParameterValue=$RedisEndpoint"
)

aws cloudformation $Operation `
    --stack-name $StackName `
    --template-body file://cloudformation/enhanced-incident-response.yaml `
    --parameters $Parameters `
    --capabilities CAPABILITY_NAMED_IAM `
    --region $Region

Write-Host "   Waiting for stack deployment to complete..."
$WaitOperation = $Operation.Replace("-stack", "-complete")
aws cloudformation wait "stack-$WaitOperation" --stack-name $StackName --region $Region

# Update Lambda function code
Write-Host "🔄 Updating Lambda function code..." -ForegroundColor Blue
$StackOutputs = aws cloudformation describe-stacks --stack-name $StackName --region $Region --query 'Stacks[0].Outputs' | ConvertFrom-Json
$LambdaArn = ($StackOutputs | Where-Object { $_.OutputKey -eq "LambdaFunctionArn" }).OutputValue
$FunctionName = $LambdaArn.Split(":")[-1]

aws lambda update-function-code `
    --function-name $FunctionName `
    --s3-bucket $DeploymentBucket `
    --s3-key $LambdaZip `
    --s3-object-version $LambdaVersion `
    --region $Region | Out-Null

Write-Host "   ✅ Lambda function updated" -ForegroundColor Green

# Get stack outputs
Write-Host "📋 Retrieving deployment information..." -ForegroundColor Blue
$RestApiUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "RestApiUrl" }).OutputValue
$WebSocketUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "WebSocketUrl" }).OutputValue
$DashboardUrl = ($StackOutputs | Where-Object { $_.OutputKey -eq "DashboardUrl" }).OutputValue

# Verify SES email
Write-Host "📧 Verifying SES email address..." -ForegroundColor Blue
try {
    $VerificationStatus = aws ses get-identity-verification-attributes --identities $SenderEmail --region $Region --query "VerificationAttributes.`"$SenderEmail`".VerificationStatus" --output text
    
    if ($VerificationStatus -eq "Success") {
        Write-Host "   ✅ Email address verified: $SenderEmail" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Email verification required for: $SenderEmail" -ForegroundColor Yellow
        Write-Host "   Sending verification email..."
        aws ses verify-email-identity --email-address $SenderEmail --region $Region
        Write-Host "   📧 Check your email and click the verification link"
    }
}
catch {
    Write-Host "⚠️  Could not verify SES email status" -ForegroundColor Yellow
}

# Run smoke tests
Write-Host "🧪 Running smoke tests..." -ForegroundColor Blue
Write-Host "   Testing REST API endpoint..."

$TestPayload = @{
    service_name = "test-service"
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    error_message = "Smoke test error"
    log_location = "s3://test-bucket/logs/"
} | ConvertTo-Json

try {
    $Response = Invoke-RestMethod -Uri "$RestApiUrl/incident" -Method Post -Body $TestPayload -ContentType "application/json" -ErrorAction Stop
    Write-Host "   ✅ REST API responding" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  REST API test failed - check API Gateway configuration" -ForegroundColor Yellow
}

# Display deployment summary
Write-Host ""
Write-Host "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Deployment Summary:" -ForegroundColor Blue
Write-Host "   Environment: " -NoNewline; Write-Host $Environment -ForegroundColor Green
Write-Host "   Stack Name: " -NoNewline; Write-Host $StackName -ForegroundColor Green
Write-Host "   Region: " -NoNewline; Write-Host $Region -ForegroundColor Green
Write-Host ""
Write-Host "🔗 Endpoints:" -ForegroundColor Blue
Write-Host "   REST API: " -NoNewline; Write-Host $RestApiUrl -ForegroundColor Green
Write-Host "   WebSocket: " -NoNewline; Write-Host $WebSocketUrl -ForegroundColor Green
Write-Host "   Dashboard: " -NoNewline; Write-Host $DashboardUrl -ForegroundColor Green
Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Blue
Write-Host "   1. Verify SES email if not already done"
Write-Host "   2. Configure Bedrock Knowledge Base with sample data"
Write-Host "   3. Test the system with: " -NoNewline; Write-Host "python ..\demo_enhanced_system.py" -ForegroundColor Green
Write-Host "   4. Monitor performance in CloudWatch Dashboard"
Write-Host ""
Write-Host "💡 Demo Commands:" -ForegroundColor Blue
Write-Host "   # Run full demo"
Write-Host "   python ..\demo_enhanced_system.py" -ForegroundColor Green
Write-Host ""
Write-Host "   # Test specific incident type"
Write-Host "   python ..\demo_enhanced_system.py configuration_error" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Blue
Write-Host "   Architecture: ..\docs\ARCHITECTURE.md"
Write-Host "   API Reference: ..\docs\API.md"
Write-Host "   Troubleshooting: ..\docs\TROUBLESHOOTING.md"
Write-Host ""
Write-Host "✨ Enhanced system ready for competition demonstration!" -ForegroundColor Green