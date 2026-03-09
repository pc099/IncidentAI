"""
Add Historical Incidents to DynamoDB

Populates the incident-history table with realistic past incidents
so that future tests will show "Similar Past Incidents" in emails.
"""

import boto3
from decimal import Decimal
from datetime import datetime, timedelta

def add_historical_incidents():
    """Add 3 historical incidents to DynamoDB for demo purposes."""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('incident-history')
    
    # Calculate past dates
    now = datetime.utcnow()
    two_weeks_ago = now - timedelta(days=14)
    one_week_ago = now - timedelta(days=7)
    three_days_ago = now - timedelta(days=3)
    
    incidents = [
        {
            'incident_id': 'inc-2025-12-22-hist001',
            'timestamp': two_weeks_ago.isoformat() + 'Z',
            'service_name': 'user-service',
            'root_cause': {
                'category': 'resource_exhaustion',
                'description': 'DynamoDB users-prod table experiencing ProvisionedThroughputExceededException due to sudden traffic spike',
                'confidence_score': Decimal('82.5')
            },
            'fixes': {
                'immediate_actions': [
                    {
                        'action': 'Enabled DynamoDB auto-scaling',
                        'estimated_time': '5 minutes'
                    }
                ]
            },
            'resolution_summary': 'Enabled auto-scaling on users-prod table, capacity adjusted automatically',
            'resolution_time_minutes': 8,
            'resolved_at': (two_weeks_ago + timedelta(minutes=8)).isoformat() + 'Z'
        },
        {
            'incident_id': 'inc-2025-12-28-hist002',
            'timestamp': one_week_ago.isoformat() + 'Z',
            'service_name': 'user-service',
            'root_cause': {
                'category': 'resource_exhaustion',
                'description': 'High read capacity consumption on users-prod DynamoDB table during peak hours',
                'confidence_score': Decimal('78.0')
            },
            'fixes': {
                'immediate_actions': [
                    {
                        'action': 'Switched to on-demand billing mode',
                        'estimated_time': '3 minutes'
                    }
                ]
            },
            'resolution_summary': 'Migrated users-prod table to on-demand billing to handle unpredictable traffic',
            'resolution_time_minutes': 5,
            'resolved_at': (one_week_ago + timedelta(minutes=5)).isoformat() + 'Z'
        },
        {
            'incident_id': 'inc-2026-01-03-hist003',
            'timestamp': three_days_ago.isoformat() + 'Z',
            'service_name': 'payment-service',
            'root_cause': {
                'category': 'resource_exhaustion',
                'description': 'DynamoDB throttling on transactions table due to insufficient write capacity',
                'confidence_score': Decimal('85.0')
            },
            'fixes': {
                'immediate_actions': [
                    {
                        'action': 'Increased write capacity units',
                        'estimated_time': '2 minutes'
                    },
                    {
                        'action': 'Added exponential backoff in application',
                        'estimated_time': '10 minutes'
                    }
                ]
            },
            'resolution_summary': 'Increased WCU from 10 to 50, added retry logic with exponential backoff',
            'resolution_time_minutes': 12,
            'resolved_at': (three_days_ago + timedelta(minutes=12)).isoformat() + 'Z'
        }
    ]
    
    print("Adding historical incidents to DynamoDB...")
    print("=" * 80)
    
    for incident in incidents:
        try:
            table.put_item(Item=incident)
            print(f"✓ Added: {incident['incident_id']}")
            print(f"  Service: {incident['service_name']}")
            print(f"  Category: {incident['root_cause']['category']}")
            print(f"  Date: {incident['timestamp'][:10]}")
            print(f"  Resolution: {incident['resolution_summary']}")
            print()
        except Exception as e:
            print(f"✗ Failed to add {incident['incident_id']}: {str(e)}")
            print()
    
    print("=" * 80)
    print("✅ Historical incidents added successfully!")
    print()
    print("Next steps:")
    print("1. Run: python scripts/test_realistic_scenario.py 2")
    print("2. Check your email - it should now show 'Similar Past Incidents'")
    print()
    print("Expected similar incidents in email:")
    print("  • inc-2025-12-22-hist001 (14 days ago) - Enabled auto-scaling")
    print("  • inc-2025-12-28-hist002 (7 days ago) - Switched to on-demand billing")

if __name__ == '__main__':
    add_historical_incidents()
