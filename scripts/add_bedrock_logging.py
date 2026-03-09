#!/usr/bin/env python3
"""
Add detailed Bedrock error logging to agents
"""

import boto3
import json

def test_bedrock_access():
    """Test if we can access Bedrock"""
    print("Testing Bedrock access...")
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Try to invoke Claude 3 Haiku
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": "Say hello"}]
        }
        
        print(f"Invoking model: {model_id}")
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        print(f"✓ Bedrock access successful!")
        print(f"Response: {response_body}")
        return True
        
    except Exception as e:
        print(f"✗ Bedrock access failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_bedrock_access()
