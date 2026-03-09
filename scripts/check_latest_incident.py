#!/usr/bin/env python3
"""
Check the latest incident in DynamoDB to see if Bedrock analysis worked
"""

import boto3
import json
from datetime import datetime, timedelta

dynamodb = boto3.client('dynamodb')

# Scan for recent incidents
response = dynamodb.scan(
    TableName='incident-history',
    Limit=5
)

print("Recent Incidents:")
print("=" * 80)

for item in sorted(response['Items'], key=lambda x: x['timestamp']['S'], reverse=True)[:3]:
    incident_id = item.get('incident_id', {}).get('S', 'Unknown')
    timestamp = item.get('timestamp', {}).get('S', 'Unknown')
    service = item.get('service_name', {}).get('S', 'Unknown')
    confidence = item.get('confidence_score', {}).get('N', '0')
    
    print(f"\nIncident: {incident_id}")
    print(f"Service: {service}")
    print(f"Time: {timestamp}")
    print(f"Confidence Score: {confidence}%")
    
    # Check if we have enhanced_alert data
    enhanced_alert = item.get('enhanced_alert', {}).get('M', {})
    if enhanced_alert:
        root_cause = enhanced_alert.get('root_cause', {}).get('M', {})
        if root_cause:
            primary_cause = root_cause.get('primary_cause', {}).get('M', {})
            if primary_cause:
                description = primary_cause.get('description', {}).get('S', 'No description')
                category = primary_cause.get('category', {}).get('S', 'Unknown')
                print(f"Category: {category}")
                print(f"Description: {description[:100]}...")
    
    print("-" * 80)
