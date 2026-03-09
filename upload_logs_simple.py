#!/usr/bin/env python3
"""Upload test logs to S3"""
import boto3
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BUCKET = "incident-response-logs-867126415696"
REGION = "us-east-1"

s3 = boto3.client('s3', region_name=REGION, verify=False)

log_files = {
    'test_data/logs/api_gateway_timeout.log': 'logs/api-gateway/2025/03/01/api_gateway_timeout.log',
    'test_data/logs/rds_storage_full.log': 'logs/rds/2025/03/01/rds_storage_full.log',
    'test_data/logs/lambda_deployment_failure.log': 'logs/lambda/2025/03/01/lambda_deployment_failure.log',
    'test_data/logs/dynamodb_throttling.log': 'logs/dynamodb/2025/03/01/dynamodb_throttling.log',
    'test_data/logs/step_functions_failure.log': 'logs/step-functions/2025/03/01/step_functions_failure.log',
}

print(f"Uploading test logs to: {BUCKET}")
print("=" * 70)

for local_path, s3_key in log_files.items():
    try:
        s3.upload_file(local_path, BUCKET, s3_key)
        print(f"✅ {local_path} → s3://{BUCKET}/{s3_key}")
    except Exception as e:
        print(f"❌ {local_path}: {e}")

print("\n✅ Upload complete!")
