#!/usr/bin/env python3
"""
Test realistic incident scenarios for POC demonstration.
"""

import requests
import json
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_ENDPOINT = os.getenv('API_GATEWAY_ENDPOINT', 'https://v5uxu396ik.execute-api.us-east-1.amazonaws.com/prod/incidents')
API_KEY = os.getenv('API_KEY', 'p7klzM6d693vg385sTqF161efhNznil72G8yfshx')
LOG_BUCKET = os.getenv('S3_LOG_BUCKET', 'incident-response-logs-867126415696')

# Test Scenarios
SCENARIOS = {
    1: {
        "name": "Lambda Timeout (Stripe API)",
        "service_name": "payment-processor",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "Lambda function timeout after 30 seconds calling Stripe API",
        "log_location": f"s3://{LOG_BUCKET}/payment-processor/2026-03-09/timeout.log",
        "alert_source": "CloudWatch"
    },
    2: {
        "name": "DynamoDB Throttling",
        "service_name": "user-service",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "ProvisionedThroughputExceededException on users-prod table",
        "log_location": f"s3://{LOG_BUCKET}/user-service/2026-03-09/throttling.log",
        "alert_source": "CloudWatch"
    },
    3: {
        "name": "API Gateway 502",
        "service_name": "order-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "API Gateway returning 502 Bad Gateway - Lambda invalid response",
        "log_location": f"s3://{LOG_BUCKET}/order-api/2026-03-09/502-error.log",
        "alert_source": "CloudWatch"
    },
    4: {
        "name": "Lambda Memory Exhaustion",
        "service_name": "image-processor",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "OutOfMemoryError: Java heap space during image processing",
        "log_location": f"s3://{LOG_BUCKET}/image-processor/2026-03-09/memory.log",
        "alert_source": "CloudWatch"
    },
    5: {
        "name": "RDS Connection Pool Exhausted",
        "service_name": "inventory-service",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_message": "MySQLNonTransientConnectionException: Too many connections",
        "log_location": f"s3://{LOG_BUCKET}/inventory-service/2026-03-09/connection.log",
        "alert_source": "CloudWatch"
    }
}


def trigger_incident(scenario_num):
    """Trigger an incident scenario"""
    if scenario_num not in SCENARIOS:
        print(f"Error: Invalid scenario number. Choose 1-{len(SCENARIOS)}")
        return False
    
    scenario = SCENARIOS[scenario_num]
    
    print(f"\n{'='*80}")
    print(f"Testing Scenario {scenario_num}: {scenario['name']}")
    print(f"{'='*80}\n")
    
    print(f"Service: {scenario['service_name']}")
    print(f"Error: {scenario['error_message']}")
    print(f"Log Location: {scenario['log_location']}")
    print(f"\nSending incident to API Gateway...")
    
    # Prepare request
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
    }
    
    payload = {
        "service_name": scenario['service_name'],
        "timestamp": scenario['timestamp'],
        "error_message": scenario['error_message'],
        "log_location": scenario['log_location'],
        "alert_source": scenario['alert_source']
    }
    
    try:
        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        print(f"\nAPI Response:")
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 202:
            result = response.json()
            print(f"  Incident ID: {result.get('incident_id')}")
            print(f"  Status: {result.get('status')}")
            print(f"  Message: {result.get('message')}")
            
            print(f"\n{'='*80}")
            print("✓ Incident triggered successfully!")
            print(f"{'='*80}\n")
            
            print("What happens next:")
            print("1. Orchestrator Lambda invokes 4 AI agents sequentially")
            print("2. Log Analysis Agent retrieves and analyzes logs from S3")
            print("3. Root Cause Agent queries Knowledge Base for similar incidents")
            print("4. Fix Recommendation Agent generates remediation steps")
            print("5. Communication Agent creates technical and business summaries")
            print("6. Enhanced alert email sent via SES")
            
            print(f"\n⏱️  Expected email delivery: 10-30 seconds")
            print(f"📧 Check your email: {os.getenv('RECIPIENT_EMAIL', 'harshavignesh1@gmail.com')}")
            
            print(f"\nThe email will include:")
            print("  • Root cause analysis with confidence score")
            print("  • Evidence from log analysis")
            print("  • Similar past incidents from Knowledge Base")
            print("  • Specific fix recommendations with commands")
            print("  • Estimated resolution time")
            print("  • Business impact summary")
            
            return True
        else:
            print(f"  Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n✗ Error triggering incident: {e}")
        return False


def print_usage():
    """Print usage instructions"""
    print("\nUsage: python scripts/test_realistic_scenario.py <scenario_number>")
    print("\nAvailable Scenarios:")
    for num, scenario in SCENARIOS.items():
        print(f"  {num}. {scenario['name']}")
        print(f"     Service: {scenario['service_name']}")
        print(f"     Error: {scenario['error_message'][:60]}...")
    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)
    
    try:
        scenario_num = int(sys.argv[1])
        success = trigger_incident(scenario_num)
        sys.exit(0 if success else 1)
    except ValueError:
        print("Error: Scenario number must be an integer")
        print_usage()
        sys.exit(1)
