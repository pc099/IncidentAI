#!/usr/bin/env python3
"""
Add Bedrock permissions to the orchestrator Lambda role
"""

import boto3
import json

def add_bedrock_permissions():
    """Add Bedrock permissions to orchestrator role"""
    iam = boto3.client('iam')
    
    role_name = 'incident-response-orchestrator-role'
    
    # Create inline policy for Bedrock access
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": [
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0",
                    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
                    "arn:aws:bedrock:*::foundation-model/*"
                ]
            }
        ]
    }
    
    try:
        print(f"Adding Bedrock permissions to role: {role_name}")
        
        # Put inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName='BedrockInvokeModelPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✓ Successfully added Bedrock permissions")
        
        # List all policies to verify
        print("\nCurrent policies attached to role:")
        
        # Managed policies
        response = iam.list_attached_role_policies(RoleName=role_name)
        for policy in response['AttachedPolicies']:
            print(f"  - {policy['PolicyName']} (managed)")
        
        # Inline policies
        response = iam.list_role_policies(RoleName=role_name)
        for policy_name in response['PolicyNames']:
            print(f"  - {policy_name} (inline)")
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding Bedrock permissions: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = add_bedrock_permissions()
    exit(0 if success else 1)
