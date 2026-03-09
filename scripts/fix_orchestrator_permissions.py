#!/usr/bin/env python3
"""
Fix IAM permissions for the orchestrator Lambda role
"""

import boto3
import json

def fix_orchestrator_permissions():
    """Add missing permissions to the orchestrator role"""
    
    iam = boto3.client('iam')
    role_name = 'incident-response-orchestrator-role'
    
    print(f"🔧 Fixing permissions for role: {role_name}")
    
    # Define the policy document with all required permissions
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3LogAccess",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject"
                ],
                "Resource": [
                    "arn:aws:s3:::incident-response-logs-*",
                    "arn:aws:s3:::incident-response-logs-*/*"
                ]
            },
            {
                "Sid": "DynamoDBAccess",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": "arn:aws:dynamodb:us-east-1:*:table/incident-history"
            },
            {
                "Sid": "BedrockAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": "arn:aws:bedrock:us-east-1::foundation-model/*"
            },
            {
                "Sid": "SESAccess",
                "Effect": "Allow",
                "Action": [
                    "ses:SendEmail",
                    "ses:SendRawEmail",
                    "ses:GetIdentityVerificationAttributes"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "arn:aws:logs:*:*:*"
            }
        ]
    }
    
    policy_name = 'incident-orchestrator-permissions'
    
    try:
        # Try to create the policy
        print(f"  📝 Creating inline policy: {policy_name}")
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print(f"  ✅ Policy created successfully")
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False
    
    print("\n✅ Permissions fixed successfully!")
    print("\nGranted permissions:")
    print("  • S3: ListBucket, GetObject, PutObject")
    print("  • DynamoDB: PutItem, GetItem, UpdateItem, Query, Scan")
    print("  • Bedrock: InvokeModel")
    print("  • SES: SendEmail, SendRawEmail")
    print("  • CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents")
    
    return True

if __name__ == "__main__":
    success = fix_orchestrator_permissions()
    exit(0 if success else 1)
