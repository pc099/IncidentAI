#!/usr/bin/env python3
"""
Lambda Deployment Script
Packages and deploys all Lambda functions for the incident response system
"""
import os
import sys
import json
import zipfile
import shutil
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from infrastructure.aws_config import (
    get_aws_region,
    LAMBDA_EXECUTION_ROLE_NAME,
    ORCHESTRATOR_ROLE_NAME,
    create_boto3_client
)
from infrastructure.setup_iam import get_role_arn


def create_deployment_package(function_name, handler_file, output_dir="dist"):
    """
    Create Lambda deployment package (ZIP file).
    
    Args:
        function_name: Name of the Lambda function
        handler_file: Path to the handler file
        output_dir: Output directory for ZIP files
        
    Returns:
        str: Path to created ZIP file
    """
    print(f"\n📦 Creating deployment package for {function_name}...")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create temp directory for packaging
    temp_dir = os.path.join(output_dir, f"temp_{function_name}")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        # Copy handler file
        handler_dest = os.path.join(temp_dir, os.path.basename(handler_file))
        shutil.copy2(handler_file, handler_dest)
        print(f"  ✓ Copied handler: {os.path.basename(handler_file)}")
        
        # Copy entire src directory
        src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
        dest_src_dir = os.path.join(temp_dir, "src")
        shutil.copytree(src_dir, dest_src_dir, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print(f"  ✓ Copied src directory")
        
        # Install dependencies
        requirements_file = os.path.join(os.path.dirname(__file__), "..", "lambda_requirements.txt")
        if os.path.exists(requirements_file):
            print(f"  ⏳ Installing dependencies...")
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "-r", requirements_file,
                "-t", temp_dir,
                "--quiet"
            ], check=True)
            print(f"  ✓ Installed dependencies")
        
        # Create ZIP file
        zip_path = os.path.join(output_dir, f"{function_name}.zip")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                # Skip __pycache__ directories
                dirs[:] = [d for d in dirs if d != '__pycache__']
                
                for file in files:
                    if file.endswith('.pyc'):
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Get ZIP size
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"  ✓ Created ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
        
        return zip_path
        
    finally:
        # Cleanup temp directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def deploy_lambda_function(
    function_name,
    zip_path,
    handler,
    role_arn,
    memory_mb=512,
    timeout_seconds=30,
    environment_vars=None
):
    """
    Deploy Lambda function to AWS.
    
    Args:
        function_name: Name of the Lambda function
        zip_path: Path to deployment ZIP file
        handler: Handler function (e.g., "handler.lambda_handler")
        role_arn: IAM role ARN
        memory_mb: Memory allocation in MB
        timeout_seconds: Timeout in seconds
        environment_vars: Environment variables dict
        
    Returns:
        dict: Lambda function details
    """
    print(f"\n🚀 Deploying Lambda function: {function_name}...")
    
    lambda_client = create_boto3_client('lambda')
    
    # Read ZIP file
    with open(zip_path, 'rb') as f:
        zip_content = f.read()
    
    # Prepare environment variables
    env_vars = environment_vars or {}
    env_vars.update({
        'LOG_BUCKET_NAME': os.environ.get('LOG_BUCKET_NAME', 'incident-response-logs-867126415696'),
        'KB_DATA_SOURCE_BUCKET_NAME': os.environ.get('KB_DATA_SOURCE_BUCKET_NAME', 'incident-response-kb-data'),
        'INCIDENT_TABLE_NAME': 'incident-history',
        'SES_SENDER_EMAIL': os.environ.get('SES_SENDER_EMAIL', 'harshavignesh1@gmail.com')
    })
    
    try:
        # Try to create function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler=handler,
            Code={'ZipFile': zip_content},
            Timeout=timeout_seconds,
            MemorySize=memory_mb,
            Environment={'Variables': env_vars},
            Tags={
                'Project': 'IncidentResponse',
                'ManagedBy': 'DeploymentScript'
            }
        )
        print(f"  ✓ Created function: {function_name}")
        return response
        
    except lambda_client.exceptions.ResourceConflictException:
        # Function exists, update it
        print(f"  ℹ Function exists, updating...")
        
        # Update function code
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        print(f"  ✓ Updated function code")
        
        # Update function configuration
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Role=role_arn,
            Handler=handler,
            Timeout=timeout_seconds,
            MemorySize=memory_mb,
            Environment={'Variables': env_vars}
        )
        print(f"  ✓ Updated function configuration")
        
        return response


def deploy_all_lambdas():
    """Deploy all Lambda functions."""
    print("=" * 60)
    print("Lambda Deployment - Incident Response System")
    print("=" * 60)
    
    # Get IAM role ARNs
    print("\n📋 Getting IAM role ARNs...")
    try:
        lambda_role_arn = get_role_arn(LAMBDA_EXECUTION_ROLE_NAME)
        orchestrator_role_arn = get_role_arn(ORCHESTRATOR_ROLE_NAME)
        print(f"  ✓ Lambda role: {lambda_role_arn}")
        print(f"  ✓ Orchestrator role: {orchestrator_role_arn}")
    except Exception as e:
        print(f"  ✗ Error getting IAM roles: {e}")
        print("  Please ensure IAM roles are created first")
        return False
    
    # Lambda configurations
    lambdas = [
        {
            'name': 'incident-validator',
            'handler_file': 'lambda_handlers/incident_validator_handler.py',
            'handler': 'incident_validator_handler.lambda_handler',
            'role_arn': lambda_role_arn,
            'memory': 256,
            'timeout': 10,
            'env_vars': {}
        },
        {
            'name': 'incident-orchestrator',
            'handler_file': 'lambda_handlers/orchestrator_handler.py',
            'handler': 'orchestrator_handler.lambda_handler',
            'role_arn': orchestrator_role_arn,
            'memory': 512,
            'timeout': 300,  # 5 minutes for full orchestration
            'env_vars': {
                'LOG_ANALYSIS_FUNCTION': 'log-analysis-agent',
                'ROOT_CAUSE_FUNCTION': 'root-cause-agent',
                'FIX_REC_FUNCTION': 'fix-recommendation-agent',
                'COMMUNICATION_FUNCTION': 'communication-agent'
            }
        }
    ]
    
    deployed_functions = []
    
    # Deploy each Lambda
    for lambda_config in lambdas:
        try:
            # Create deployment package
            zip_path = create_deployment_package(
                lambda_config['name'],
                lambda_config['handler_file']
            )
            
            # Deploy to AWS
            result = deploy_lambda_function(
                function_name=lambda_config['name'],
                zip_path=zip_path,
                handler=lambda_config['handler'],
                role_arn=lambda_config['role_arn'],
                memory_mb=lambda_config['memory'],
                timeout_seconds=lambda_config['timeout'],
                environment_vars=lambda_config['env_vars']
            )
            
            deployed_functions.append({
                'name': lambda_config['name'],
                'arn': result['FunctionArn'],
                'status': 'deployed'
            })
            
        except Exception as e:
            print(f"  ✗ Error deploying {lambda_config['name']}: {e}")
            import traceback
            traceback.print_exc()
            deployed_functions.append({
                'name': lambda_config['name'],
                'status': 'failed',
                'error': str(e)
            })
    
    # Update orchestrator with validator function name
    if any(f['name'] == 'incident-validator' for f in deployed_functions):
        try:
            lambda_client = create_boto3_client('lambda')
            lambda_client.update_function_configuration(
                FunctionName='incident-validator',
                Environment={
                    'Variables': {
                        'ORCHESTRATOR_FUNCTION_NAME': 'incident-orchestrator',
                        'LOG_BUCKET_NAME': os.environ.get('LOG_BUCKET_NAME', 'incident-response-logs-867126415696')
                    }
                }
            )
            print("\n  ✓ Updated validator with orchestrator function name")
        except Exception as e:
            print(f"\n  ⚠ Warning: Could not update validator config: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("Deployment Summary")
    print("=" * 60)
    
    for func in deployed_functions:
        status_icon = "✓" if func['status'] == 'deployed' else "✗"
        print(f"{status_icon} {func['name']}: {func['status']}")
        if func['status'] == 'deployed':
            print(f"  ARN: {func['arn']}")
        elif 'error' in func:
            print(f"  Error: {func['error']}")
    
    # Save deployment info
    deployment_info = {
        'timestamp': str(Path(__file__).stat().st_mtime),
        'region': get_aws_region(),
        'functions': deployed_functions
    }
    
    with open('deployment_info.json', 'w') as f:
        json.dump(deployment_info, f, indent=2)
    print(f"\n💾 Deployment info saved to: deployment_info.json")
    
    success_count = sum(1 for f in deployed_functions if f['status'] == 'deployed')
    total_count = len(deployed_functions)
    
    print(f"\n📊 Deployed {success_count}/{total_count} Lambda functions")
    
    if success_count == total_count:
        print("\n✅ All Lambda functions deployed successfully!")
        print("\nNext steps:")
        print("1. Verify SES email (check Gmail for verification link)")
        print("2. Deploy API Gateway: python scripts/deploy_api_gateway.py")
        print("3. Test end-to-end: python scripts/test_end_to_end.py")
        return True
    else:
        print("\n⚠️  Some Lambda functions failed to deploy")
        print("Please check the errors above and retry")
        return False


if __name__ == "__main__":
    import sys
    success = deploy_all_lambdas()
    sys.exit(0 if success else 1)
