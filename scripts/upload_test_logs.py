#!/usr/bin/env python3
"""
Upload test log files to S3 bucket for testing the incident response system.

This script uploads sample log files for various AWS failure scenarios to the
configured S3 log bucket.
"""

import os
import sys
import boto3
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config


def upload_test_logs():
    """Upload all test log files to S3."""
    s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
    
    # Define log files and their S3 keys
    log_files = {
        'test_data/logs/api_gateway_timeout.log': 'logs/api-gateway/2025/03/01/api_gateway_timeout.log',
        'test_data/logs/rds_storage_full.log': 'logs/rds/2025/03/01/rds_storage_full.log',
        'test_data/logs/lambda_deployment_failure.log': 'logs/lambda/2025/03/01/lambda_deployment_failure.log',
        'test_data/logs/dynamodb_throttling.log': 'logs/dynamodb/2025/03/01/dynamodb_throttling.log',
        'test_data/logs/step_functions_failure.log': 'logs/step-functions/2025/03/01/step_functions_failure.log',
    }
    
    print(f"Uploading test logs to S3 bucket: {Config.S3_LOG_BUCKET}")
    print("-" * 60)
    
    uploaded_count = 0
    failed_count = 0
    
    for local_path, s3_key in log_files.items():
        try:
            # Check if file exists
            if not Path(local_path).exists():
                print(f"❌ File not found: {local_path}")
                failed_count += 1
                continue
            
            # Upload to S3
            s3_client.upload_file(
                local_path,
                Config.S3_LOG_BUCKET,
                s3_key,
                ExtraArgs={
                    'ContentType': 'text/plain',
                    'Metadata': {
                        'uploaded_at': datetime.utcnow().isoformat(),
                        'purpose': 'test_data'
                    }
                }
            )
            
            s3_uri = f"s3://{Config.S3_LOG_BUCKET}/{s3_key}"
            print(f"✅ Uploaded: {local_path}")
            print(f"   S3 URI: {s3_uri}")
            uploaded_count += 1
            
        except Exception as e:
            print(f"❌ Failed to upload {local_path}: {str(e)}")
            failed_count += 1
    
    print("-" * 60)
    print(f"Upload complete: {uploaded_count} succeeded, {failed_count} failed")
    
    if uploaded_count > 0:
        print("\nS3 URIs for testing:")
        for local_path, s3_key in log_files.items():
            if Path(local_path).exists():
                print(f"  s3://{Config.S3_LOG_BUCKET}/{s3_key}")
    
    return uploaded_count, failed_count


if __name__ == "__main__":
    try:
        uploaded, failed = upload_test_logs()
        sys.exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
