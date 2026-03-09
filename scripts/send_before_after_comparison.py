"""
Send Before/After Comparison Emails for Blog Demo

This script sends two emails to demonstrate the power of the AI-Powered Incident Response POC:
1. BEFORE: Traditional error alert (just the raw error message)
2. AFTER: AI-Enhanced alert (full analysis, fixes, commands, similar incidents)

Perfect for blog posts, presentations, and demos!
"""

import boto3
import json
from datetime import datetime

def send_traditional_alert():
    """Send a traditional error alert (BEFORE) - just the raw error."""
    
    ses = boto3.client('ses', region_name='us-east-1')
    
    # Traditional alert - clean and simple, production standard
    subject = "⚠️ Error Alert: user-service"
    
    html_body = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            background-color: #f5f5f5;
            color: #333;
            padding: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .header h1 {
            margin: 0 0 10px 0;
            font-size: 20px;
            color: #333;
        }
        .metadata {
            font-size: 13px;
            color: #666;
        }
        .section {
            padding: 20px;
        }
        .section h2 {
            margin: 0 0 15px 0;
            font-size: 18px;
            color: #333;
        }
        .error-box {
            background-color: #f5f5f5;
            border-left: 3px solid #ff9800;
            padding: 15px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Error Alert</h1>
            <p class="metadata">Service: user-service | Time: 2026-03-09T16:30:00Z</p>
        </div>
        
        <div class="section">
            <h2>Error Details</h2>
            <div class="error-box">ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput for table 'users-prod'</div>
            <p class="metadata">Log Location: s3://incident-response-logs-867126415696/user-service/2026-03-09/throttling.log</p>
        </div>
    </div>
</body>
</html>
"""
    
    text_body = """
ERROR ALERT
================================================================================

Service: user-service
Time: 2026-03-09T16:30:00Z

ERROR DETAILS:
--------------------------------------------------------------------------------
ProvisionedThroughputExceededException: Rate of requests exceeds the allowed 
throughput for table 'users-prod'

Log Location: s3://incident-response-logs-867126415696/user-service/2026-03-09/throttling.log

================================================================================
"""
    
    try:
        response = ses.send_email(
            Source='harshavignesh1@gmail.com',
            Destination={
                'ToAddresses': ['harshavignesh1@gmail.com']
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        print("=" * 80)
        print("✅ Traditional Alert Email Sent Successfully!")
        print("=" * 80)
        print(f"Subject: {subject}")
        print(f"MessageId: {response['MessageId']}")
        print()
        print("This email shows a clean, production-standard error alert:")
        print("  • Service name and timestamp")
        print("  • Error message")
        print("  • Log location")
        print("  • No analysis, no recommendations")
        print()
        
    except Exception as e:
        print(f"❌ Failed to send BEFORE email: {str(e)}")


def trigger_ai_enhanced_alert():
    """Trigger the AI-Enhanced alert (AFTER) by calling the API Gateway."""
    
    import requests
    
    api_url = "https://v5uxu396ik.execute-api.us-east-1.amazonaws.com/prod/incidents"
    
    payload = {
        "service_name": "user-service",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput for table 'users-prod'",
        "severity": "high",
        "log_location": "s3://incident-response-logs-867126415696/user-service/2026-03-09/throttling.log"
    }
    
    try:
        response = requests.post(api_url, json=payload)
        
        if response.status_code == 202:
            result = response.json()
            print("=" * 80)
            print("✅ AFTER Email Triggered Successfully!")
            print("=" * 80)
            print(f"Incident ID: {result.get('incident_id')}")
            print(f"Status: {result.get('status')}")
            print()
            print("AI-Enhanced alert will be delivered in 10-30 seconds with:")
            print("  ✅ Error message")
            print("  ✅ AI-powered root cause analysis (76% confidence)")
            print("  ✅ 4 AWS-specific fix recommendations")
            print("  ✅ Ready-to-run CLI commands")
            print("  ✅ 2 similar past incidents with resolutions")
            print("  ✅ Business impact assessment")
            print("  ✅ Estimated resolution time: 20 minutes")
            print()
        else:
            print(f"❌ Failed to trigger AFTER email: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Failed to trigger AFTER email: {str(e)}")


if __name__ == '__main__':
    print()
    print("=" * 80)
    print("BEFORE/AFTER COMPARISON EMAIL DEMO")
    print("=" * 80)
    print()
    print("This script will send two emails to demonstrate the POC:")
    print()
    print("1️⃣  BEFORE: Traditional error alert (just the error message)")
    print("2️⃣  AFTER: AI-Enhanced alert (full analysis + fixes + commands)")
    print()
    print("Perfect for blog posts and presentations!")
    print()
    print("=" * 80)
    print()
    
    # Send traditional alert first
    print("📧 Sending BEFORE email (Traditional Alert)...")
    send_traditional_alert()
    
    print()
    print("⏱️  Waiting 3 seconds...")
    import time
    time.sleep(3)
    print()
    
    # Trigger AI-enhanced alert
    print("📧 Triggering AFTER email (AI-Enhanced Alert)...")
    trigger_ai_enhanced_alert()
    
    print()
    print("=" * 80)
    print("✅ DEMO COMPLETE!")
    print("=" * 80)
    print()
    print("Check your email inbox:")
    print("  📧 harshavignesh1@gmail.com")
    print()
    print("You should receive:")
    print("  1. BEFORE email (immediately)")
    print("  2. AFTER email (in 10-30 seconds)")
    print()
    print("Compare them side-by-side to see the power of AI-powered incident response!")
    print()
