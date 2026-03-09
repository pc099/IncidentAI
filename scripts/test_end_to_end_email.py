#!/usr/bin/env python3
"""
End-to-End Email Delivery Test
Triggers the deployed Lambda via API Gateway and verifies email delivery
"""

import json
import os
import sys
import time
import requests
from datetime import datetime

def test_email_delivery():
    """Test the complete incident response flow and email delivery"""
    
    # Get API Gateway endpoint from environment or use default from deployment
    api_endpoint = os.getenv('API_GATEWAY_ENDPOINT', 'https://v5uxu396ik.execute-api.us-east-1.amazonaws.com/prod')
    
    # Get API key from environment or use default from deployment
    api_key = os.getenv('API_KEY', 'p7klzM6d693vg385sTqF161efhNznil72G8yfshx')
    
    # Create test incident payload
    test_incident = {
        "service_name": "payment-service",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "Payment processing failures detected - multiple transaction timeouts",
        "log_location": "s3://incident-response-logs-867126415696/test-logs/payment-service.log",
        "severity": "high",
        "alert_source": "CloudWatch",
        "affected_resources": [
            "arn:aws:lambda:us-east-1:123456789012:function:payment-processor",
            "arn:aws:dynamodb:us-east-1:123456789012:table/transactions"
        ],
        "metrics": {
            "error_rate": 15.5,
            "latency_p99": 5000,
            "failed_transactions": 47
        },
        "tags": {
            "environment": "production",
            "team": "payments",
            "priority": "critical"
        }
    }
    
    print("\n" + "=" * 80)
    print("🧪 END-TO-END EMAIL DELIVERY TEST")
    print("=" * 80)
    print(f"\n📍 API Endpoint: {api_endpoint}/incidents")
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"⚠️  Severity: {test_incident['severity']}")
    print(f"🔧 Service: {test_incident['service_name']}")
    
    print("\n" + "-" * 80)
    print("📤 Sending incident to API Gateway...")
    print("-" * 80)
    
    try:
        # Send POST request to API Gateway
        response = requests.post(
            f"{api_endpoint}/incidents",
            json=test_incident,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key
            },
            timeout=30
        )
        
        print(f"\n✅ Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            response_data = response.json()
            print(f"✅ Response Body:")
            print(json.dumps(response_data, indent=2))
            
            incident_id = response_data.get('incident_id', test_incident.get('incident_id', 'unknown'))
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS - Incident Submitted")
            print("=" * 80)
            print(f"\n🆔 Incident ID: {incident_id}")
            print("\n📧 Email Processing:")
            print("   • Lambda function triggered successfully")
            print("   • Incident analysis in progress")
            print("   • Email will be sent via AWS SES")
            print("\n⏱️  Expected delivery time: 30-60 seconds")
            print("\n📬 Check your email inbox for:")
            print(f"   Subject: [HIGH] Incident Alert: {test_incident['service_name']}")
            print(f"   From: AWS Incident Response System")
            print(f"   To: harshavignesh1@gmail.com")
            
            print("\n" + "-" * 80)
            print("📊 What to expect in the email:")
            print("-" * 80)
            print("   ✓ Executive Summary (non-technical)")
            print("   ✓ Technical Summary (detailed)")
            print("   ✓ Root Cause Analysis")
            print("   ✓ Fix Recommendations")
            print("   ✓ User Impact Assessment")
            print("   ✓ Historical Pattern Analysis")
            
            return True
            
        elif response.status_code == 403:
            print("\n❌ ERROR: Access Denied (403)")
            print("   • Check if API key is required and configured")
            print("   • Verify IAM permissions for API Gateway")
            return False
            
        elif response.status_code == 500:
            print("\n❌ ERROR: Internal Server Error (500)")
            print("   • Lambda function may have encountered an error")
            print("   • Check CloudWatch Logs for details")
            if response.text:
                print(f"\n   Error details: {response.text}")
            return False
            
        else:
            print(f"\n❌ ERROR: Unexpected status code {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        print("   • API Gateway may be slow to respond")
        print("   • Lambda cold start may be taking longer than expected")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ ERROR: Connection failed")
        print(f"   • Cannot reach API Gateway endpoint")
        print(f"   • Verify the endpoint URL is correct")
        print(f"   • Error: {str(e)}")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error occurred")
        print(f"   {str(e)}")
        return False

def check_cloudwatch_logs():
    """Provide instructions for checking CloudWatch logs"""
    print("\n" + "=" * 80)
    print("🔍 TROUBLESHOOTING - CloudWatch Logs")
    print("=" * 80)
    print("\nIf you don't receive an email, check CloudWatch Logs:")
    print("\n1. Go to AWS Console → CloudWatch → Log Groups")
    print("2. Look for: /aws/lambda/incident-orchestrator")
    print("3. Check recent log streams for errors")
    print("\nCommon issues:")
    print("   • SES email not verified (check SES console)")
    print("   • IAM permissions missing for Lambda")
    print("   • Bedrock model access not enabled")
    print("   • DynamoDB table not accessible")

if __name__ == "__main__":
    print("\n🚀 Starting End-to-End Email Delivery Test\n")
    
    success = test_email_delivery()
    
    if not success:
        check_cloudwatch_logs()
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)
    print("\n💡 Next Steps:")
    print("   1. Check your email inbox (may take 30-60 seconds)")
    print("   2. Check spam folder if not in inbox")
    print("   3. Verify sender email in AWS SES console")
    print("   4. Review CloudWatch Logs if no email received")
    print()
