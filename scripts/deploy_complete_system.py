#!/usr/bin/env python3
"""
Complete System Deployment Script
Deploys Lambda functions and API Gateway in correct order
"""
import os
import sys
import subprocess


def run_script(script_name, description):
    """Run a deployment script."""
    print("\n" + "=" * 70)
    print(f"STEP: {description}")
    print("=" * 70)
    
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False
        )
        print(f"\n✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED")
        print(f"Error: {e}")
        return False


def main():
    """Main deployment function."""
    print("=" * 70)
    print("COMPLETE SYSTEM DEPLOYMENT")
    print("AI-Powered Incident Response System")
    print("=" * 70)
    
    # Check environment variables
    print("\n📋 Checking environment variables...")
    required_vars = ['AWS_ACCOUNT_ID', 'LOG_BUCKET_NAME']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"  ✓ {var}: {value}")
        else:
            print(f"  ✗ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set them:")
        print("  export AWS_ACCOUNT_ID=867126415696")
        print("  export LOG_BUCKET_NAME=incident-response-logs-867126415696")
        print("  export SSL_VERIFY=false  # If needed")
        return False
    
    # Deployment steps
    steps = [
        ("deploy_lambdas.py", "Deploy Lambda Functions"),
        ("deploy_api_gateway.py", "Deploy API Gateway")
    ]
    
    for script, description in steps:
        success = run_script(script, description)
        if not success:
            print(f"\n❌ Deployment failed at: {description}")
            print("Please fix the errors and run again")
            return False
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 DEPLOYMENT COMPLETE!")
    print("=" * 70)
    
    print("\n✅ Deployed Components:")
    print("  • Lambda: incident-validator")
    print("  • Lambda: incident-orchestrator")
    print("  • API Gateway: incident-response-api")
    print("  • S3 Buckets: logs + KB data")
    print("  • DynamoDB: incident-history")
    print("  • IAM Roles: 3 roles")
    print("  • SES: harshavignesh1@gmail.com")
    
    print("\n📋 Next Steps:")
    print("  1. ✅ Verify SES email (check Gmail)")
    print("  2. ⏳ Test API endpoint (see api_gateway_info.json)")
    print("  3. ⏳ Monitor CloudWatch logs")
    print("  4. ⏳ Populate Knowledge Base with sample incidents")
    
    print("\n📄 Generated Files:")
    print("  • deployment_info.json - Lambda deployment details")
    print("  • api_gateway_info.json - API Gateway details")
    
    print("\n🔗 Quick Links:")
    print(f"  • Lambda Console: https://console.aws.amazon.com/lambda/home?region=us-east-1")
    print(f"  • API Gateway Console: https://console.aws.amazon.com/apigateway/home?region=us-east-1")
    print(f"  • DynamoDB Console: https://console.aws.amazon.com/dynamodb/home?region=us-east-1")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
