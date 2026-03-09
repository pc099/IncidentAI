#!/usr/bin/env python3
"""
Quick realtime test of the incident response system
"""
import requests
import json
from datetime import datetime, timezone

# Your deployed API details
API_ENDPOINT = "https://v5uxu396ik.execute-api.us-east-1.amazonaws.com/prod/incidents"
API_KEY = "p7klzM6d693vg385sTqF161efhNznil72G8yfshx"
LOG_BUCKET = "incident-response-logs-867126415696"

# Test scenario
payload = {
    "service_name": "payment-api-gateway",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "error_message": "API Gateway integration timeout: Endpoint request timed out after 29 seconds",
    "log_location": f"s3://{LOG_BUCKET}/logs/api-gateway/2025/03/01/api_gateway_timeout.log",
    "alert_source": "CloudWatch"
}

print("=" * 70)
print("REALTIME TEST: AI-Powered Incident Response System")
print("=" * 70)
print(f"\nAPI Endpoint: {API_ENDPOINT}")
print(f"\nTest Scenario: API Gateway Timeout")
print(f"Service: {payload['service_name']}")
print(f"\nPayload:")
print(json.dumps(payload, indent=2))

# Send request
print(f"\n{'='*70}")
print("Sending request...")
print(f"{'='*70}")

headers = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

try:
    response = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=30)
    
    print(f"\n✅ Response Status: {response.status_code}")
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 202:
        incident_id = response.json().get("incident_id")
        print(f"\n{'='*70}")
        print("🎉 SUCCESS! Incident triggered successfully!")
        print(f"{'='*70}")
        print(f"\nIncident ID: {incident_id}")
        print(f"\nWhat's happening now (in realtime):")
        print("  1. ✅ Validator Lambda validated your request")
        print("  2. 🔄 Orchestrator Lambda is processing (10-30 seconds):")
        print("     • Agent 1: Retrieving logs from S3")
        print("     • Agent 2: Querying Knowledge Base + Bedrock for root cause")
        print("     • Agent 3: Getting fix recommendations from Bedrock")
        print("     • Agent 4: Formatting email + sending via SES")
        print(f"\nMonitor in realtime:")
        print(f"  • CloudWatch Logs: aws logs tail /aws/lambda/incident-orchestrator --follow")
        print(f"  • Check email: harshavignesh1@gmail.com")
        print(f"  • Query DynamoDB: aws dynamodb get-item --table-name incident-history --key '{{\"incident_id\": {{\"S\": \"{incident_id}\"}}}}'")
    else:
        print(f"\n❌ Unexpected response code: {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
