#!/usr/bin/env python3
"""
Incident Simulation Script

Generates synthetic alert events for various AWS failure scenarios and triggers
the incident response system via API Gateway endpoint.

Usage:
    python scripts/simulate_incidents.py --scenario <scenario_name>
    python scripts/simulate_incidents.py --all
    python scripts/simulate_incidents.py --list
"""

import argparse
import json
import sys
import os
import time
import requests
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config


# Define failure scenarios
SCENARIOS = {
    'api_gateway_timeout': {
        'service_name': 'payment-api-gateway',
        'error_message': 'API Gateway integration timeout: Endpoint request timed out after 29 seconds',
        'log_location': 's3://{bucket}/logs/api-gateway/2025/03/01/api_gateway_timeout.log',
        'alert_source': 'CloudWatch',
        'description': 'API Gateway timeout to backend payment service'
    },
    'rds_storage_full': {
        'service_name': 'production-db-instance',
        'error_message': 'RDS storage full: could not extend file - No space left on device',
        'log_location': 's3://{bucket}/logs/rds/2025/03/01/rds_storage_full.log',
        'alert_source': 'CloudWatch',
        'description': 'PostgreSQL RDS instance out of storage space'
    },
    'lambda_deployment': {
        'service_name': 'payment-processor',
        'error_message': 'Lambda deployment failed: Unzipped size must be smaller than 262144000 bytes',
        'log_location': 's3://{bucket}/logs/lambda/2025/03/01/lambda_deployment_failure.log',
        'alert_source': 'EventBridge',
        'description': 'Lambda function deployment package too large'
    },
    'dynamodb_throttling': {
        'service_name': 'user-sessions-table',
        'error_message': 'DynamoDB throttling: ProvisionedThroughputExceededException',
        'log_location': 's3://{bucket}/logs/dynamodb/2025/03/01/dynamodb_throttling.log',
        'alert_source': 'CloudWatch',
        'description': 'DynamoDB table throttled due to insufficient write capacity'
    },
    'step_functions_failure': {
        'service_name': 'order-processing-workflow',
        'error_message': 'Step Functions execution failed: Payment processing task timed out',
        'log_location': 's3://{bucket}/logs/step-functions/2025/03/01/step_functions_failure.log',
        'alert_source': 'EventBridge',
        'description': 'Step Functions workflow failed due to Lambda timeout'
    }
}


def create_alert_payload(scenario_name: str) -> Dict[str, Any]:
    """Create alert payload for a given scenario."""
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}")
    
    scenario = SCENARIOS[scenario_name]
    
    # Format log location with actual bucket name
    log_location = scenario['log_location'].format(bucket=Config.S3_LOG_BUCKET)
    
    # Create payload
    payload = {
        'service_name': scenario['service_name'],
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error_message': scenario['error_message'],
        'log_location': log_location,
        'alert_source': scenario['alert_source']
    }
    
    return payload


def trigger_incident(scenario_name: str, api_endpoint: str, api_key: str = None) -> Dict[str, Any]:
    """Trigger an incident via API Gateway."""
    print(f"\n{'='*60}")
    print(f"Simulating Incident: {scenario_name}")
    print(f"{'='*60}")
    
    scenario = SCENARIOS[scenario_name]
    print(f"Description: {scenario['description']}")
    print(f"Service: {scenario['service_name']}")
    print(f"Alert Source: {scenario['alert_source']}")
    
    # Create payload
    payload = create_alert_payload(scenario_name)
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json'
    }
    if api_key:
        headers['x-api-key'] = api_key
    
    # Send request
    print(f"\nSending POST request to: {api_endpoint}")
    try:
        start_time = time.time()
        response = requests.post(
            api_endpoint,
            json=payload,
            headers=headers,
            timeout=30
        )
        elapsed_time = time.time() - start_time
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Time: {elapsed_time:.2f}s")
        
        if response.status_code == 202:
            response_data = response.json()
            print(f"✅ Incident triggered successfully!")
            print(f"Incident ID: {response_data.get('incident_id', 'N/A')}")
            print(f"Status: {response_data.get('status', 'N/A')}")
            print(f"Message: {response_data.get('message', 'N/A')}")
            return {
                'success': True,
                'scenario': scenario_name,
                'incident_id': response_data.get('incident_id'),
                'response_time': elapsed_time
            }
        else:
            print(f"❌ Request failed!")
            print(f"Response: {response.text}")
            return {
                'success': False,
                'scenario': scenario_name,
                'error': response.text,
                'status_code': response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {str(e)}")
        return {
            'success': False,
            'scenario': scenario_name,
            'error': str(e)
        }


def verify_processing(incident_id: str, timeout: int = 60):
    """
    Verify that incident processing completes.
    
    Note: This is a placeholder. In a real implementation, you would:
    - Poll DynamoDB for incident record
    - Check CloudWatch logs for processing completion
    - Verify email delivery via SES
    """
    print(f"\n{'='*60}")
    print(f"Verifying Incident Processing: {incident_id}")
    print(f"{'='*60}")
    print("Note: Verification requires additional implementation")
    print("Suggested checks:")
    print("  1. Query DynamoDB for incident record")
    print("  2. Check CloudWatch logs for agent execution")
    print("  3. Verify SES email delivery")
    print("  4. Confirm Knowledge Base indexing")


def list_scenarios():
    """List all available scenarios."""
    print("\nAvailable Incident Scenarios:")
    print("="*60)
    for name, scenario in SCENARIOS.items():
        print(f"\n{name}:")
        print(f"  Service: {scenario['service_name']}")
        print(f"  Description: {scenario['description']}")
        print(f"  Alert Source: {scenario['alert_source']}")


def main():
    parser = argparse.ArgumentParser(
        description='Simulate incidents for testing the incident response system'
    )
    parser.add_argument(
        '--scenario',
        type=str,
        help='Scenario name to simulate'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all scenarios'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available scenarios'
    )
    parser.add_argument(
        '--api-endpoint',
        type=str,
        help='API Gateway endpoint URL (default: from config)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        help='API key for authentication'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify incident processing after triggering'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=5,
        help='Delay between scenarios when using --all (seconds)'
    )
    
    args = parser.parse_args()
    
    # List scenarios
    if args.list:
        list_scenarios()
        return 0
    
    # Validate arguments
    if not args.scenario and not args.all:
        parser.error("Either --scenario or --all must be specified")
    
    # Get API endpoint
    api_endpoint = args.api_endpoint or os.getenv('API_GATEWAY_ENDPOINT')
    if not api_endpoint:
        print("Error: API Gateway endpoint not configured")
        print("Set API_GATEWAY_ENDPOINT environment variable or use --api-endpoint")
        return 1
    
    # Get API key
    api_key = args.api_key or os.getenv('API_GATEWAY_KEY')
    
    # Run scenarios
    results = []
    
    if args.all:
        print(f"\nRunning all {len(SCENARIOS)} scenarios...")
        for i, scenario_name in enumerate(SCENARIOS.keys(), 1):
            print(f"\n[{i}/{len(SCENARIOS)}]")
            result = trigger_incident(scenario_name, api_endpoint, api_key)
            results.append(result)
            
            if args.verify and result['success']:
                verify_processing(result['incident_id'])
            
            # Delay between scenarios
            if i < len(SCENARIOS):
                print(f"\nWaiting {args.delay} seconds before next scenario...")
                time.sleep(args.delay)
    else:
        result = trigger_incident(args.scenario, api_endpoint, api_key)
        results.append(result)
        
        if args.verify and result['success']:
            verify_processing(result['incident_id'])
    
    # Print summary
    print(f"\n{'='*60}")
    print("Simulation Summary")
    print(f"{'='*60}")
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Total scenarios: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if successful > 0:
        print("\nSuccessful incidents:")
        for result in results:
            if result['success']:
                print(f"  ✅ {result['scenario']}: {result['incident_id']}")
    
    if failed > 0:
        print("\nFailed incidents:")
        for result in results:
            if not result['success']:
                print(f"  ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
