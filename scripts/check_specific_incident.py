#!/usr/bin/env python3
"""
Check a specific incident in DynamoDB
"""

import boto3
import json
import sys

dynamodb = boto3.client('dynamodb')

incident_id = sys.argv[1] if len(sys.argv) > 1 else "inc-2026-03-09-9691c32b"

print(f"Checking incident: {incident_id}")
print("=" * 80)

try:
    response = dynamodb.get_item(
        TableName='incident-history',
        Key={'incident_id': {'S': incident_id}}
    )
    
    if 'Item' not in response:
        print("Incident not found!")
        exit(1)
    
    item = response['Item']
    
    print(f"Service: {item.get('service_name', {}).get('S', 'Unknown')}")
    print(f"Timestamp: {item.get('timestamp', {}).get('S', 'Unknown')}")
    print(f"Confidence Score: {item.get('confidence_score', {}).get('N', '0')}%")
    
    # Check enhanced_alert
    enhanced_alert = item.get('enhanced_alert', {}).get('M', {})
    if enhanced_alert:
        print("\nEnhanced Alert Found:")
        
        # Root cause
        root_cause = enhanced_alert.get('root_cause', {}).get('M', {})
        if root_cause:
            primary = root_cause.get('primary_cause', {}).get('M', {})
            if primary:
                print(f"\nRoot Cause:")
                print(f"  Category: {primary.get('category', {}).get('S', 'Unknown')}")
                print(f"  Description: {primary.get('description', {}).get('S', 'No description')}")
                print(f"  Confidence: {primary.get('confidence_score', {}).get('N', '0')}%")
        
        # Technical summary
        tech_summary = enhanced_alert.get('technical_summary', {}).get('M', {})
        if tech_summary:
            print(f"\nTechnical Summary:")
            print(f"  Title: {tech_summary.get('title', {}).get('S', 'N/A')}")
            print(f"  Root Cause: {tech_summary.get('root_cause', {}).get('S', 'N/A')[:100]}...")
    else:
        print("\nNo enhanced_alert data found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
