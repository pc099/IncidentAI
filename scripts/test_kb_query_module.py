#!/usr/bin/env python3
"""
Test script for KB query module functionality.

This script demonstrates the KB query module with example scenarios:
- Lambda deployment failure
- DynamoDB throttling
- API Gateway timeout

Usage:
    python scripts/test_kb_query_module.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agents.kb_query import (
    convert_incident_to_query,
    query_similar_incidents,
    parse_incident_metadata
)


def test_query_conversion():
    """Test converting incidents to query text"""
    print("=" * 80)
    print("Test 1: Query Text Conversion")
    print("=" * 80)
    
    # Test 1: Basic conversion
    query1 = convert_incident_to_query(
        service_name="payment-processor",
        error_message="Service health check failed"
    )
    print("\n1. Basic query (no log summary):")
    print(query1)
    
    # Test 2: With error patterns
    log_summary = {
        "error_patterns": [
            {"pattern": "ConnectionTimeout", "occurrences": 15},
            {"pattern": "SocketTimeoutException", "occurrences": 10}
        ]
    }
    query2 = convert_incident_to_query(
        service_name="payment-processor",
        error_message="Connection timeout to payment gateway",
        log_summary=log_summary
    )
    print("\n2. Query with error patterns:")
    print(query2)
    
    # Test 3: Lambda deployment failure
    log_summary_lambda = {
        "error_patterns": [
            {"pattern": "DeploymentPackageTooLarge"}
        ]
    }
    query3 = convert_incident_to_query(
        service_name="lambda-function",
        error_message="Lambda deployment failed: package size exceeds limit",
        log_summary=log_summary_lambda
    )
    print("\n3. Lambda deployment failure query:")
    print(query3)
    
    print("\n✓ Query conversion tests completed\n")


def test_metadata_parsing():
    """Test parsing incident metadata"""
    print("=" * 80)
    print("Test 2: Metadata Parsing")
    print("=" * 80)
    
    # Test 1: Basic metadata
    result1 = {
        "metadata": {
            "incident_id": "inc-2024-11-23-001",
            "root_cause": "Payment gateway timeout",
            "service_name": "payment-processor"
        },
        "content": {
            "text": "Increased timeout threshold to 30s"
        }
    }
    incident1 = parse_incident_metadata(result1)
    print("\n1. Basic metadata:")
    print(f"   Incident ID: {incident1['incident_id']}")
    print(f"   Root Cause: {incident1['root_cause']}")
    print(f"   Resolution: {incident1['resolution']}")
    print(f"   Service: {incident1.get('service_name', 'N/A')}")
    
    # Test 2: Dict root cause
    result2 = {
        "metadata": {
            "incident_id": "inc-2024-12-01-002",
            "root_cause": {
                "category": "dependency_failure",
                "description": "External API timeout"
            }
        },
        "content": {
            "text": "Implemented circuit breaker pattern"
        }
    }
    incident2 = parse_incident_metadata(result2)
    print("\n2. Dict root cause:")
    print(f"   Incident ID: {incident2['incident_id']}")
    print(f"   Root Cause: {incident2['root_cause']}")
    print(f"   Resolution: {incident2['resolution']}")
    
    # Test 3: Resolution in metadata
    result3 = {
        "metadata": {
            "incident_id": "inc-2024-12-15-003",
            "root_cause": "DynamoDB throttling",
            "resolution": {
                "action": "Enabled auto-scaling for read/write capacity",
                "success": True
            }
        },
        "content": {
            "text": ""
        }
    }
    incident3 = parse_incident_metadata(result3)
    print("\n3. Resolution in metadata:")
    print(f"   Incident ID: {incident3['incident_id']}")
    print(f"   Root Cause: {incident3['root_cause']}")
    print(f"   Resolution: {incident3['resolution']}")
    
    print("\n✓ Metadata parsing tests completed\n")


def test_example_scenarios():
    """Test example scenarios (without actual AWS calls)"""
    print("=" * 80)
    print("Test 3: Example Scenarios")
    print("=" * 80)
    
    print("\nScenario 1: Lambda Deployment Failure")
    print("-" * 40)
    query = convert_incident_to_query(
        service_name="lambda-function",
        error_message="Lambda deployment failed: package size exceeds limit",
        log_summary={
            "error_patterns": [
                {"pattern": "DeploymentPackageTooLarge"}
            ]
        }
    )
    print("Query text:")
    print(query)
    print("\nExpected similar incidents:")
    print("- Previous Lambda deployment failures")
    print("- Package size optimization solutions")
    
    print("\n\nScenario 2: DynamoDB Throttling")
    print("-" * 40)
    query = convert_incident_to_query(
        service_name="dynamodb-table",
        error_message="ProvisionedThroughputExceededException",
        log_summary={
            "error_patterns": [
                {"pattern": "ThrottlingException"}
            ]
        }
    )
    print("Query text:")
    print(query)
    print("\nExpected similar incidents:")
    print("- Previous DynamoDB throttling issues")
    print("- Auto-scaling configurations")
    print("- On-demand billing mode switches")
    
    print("\n\nScenario 3: API Gateway Timeout")
    print("-" * 40)
    query = convert_incident_to_query(
        service_name="api-gateway",
        error_message="API Gateway timeout after 29s",
        log_summary={
            "error_patterns": [
                {"pattern": "TimeoutException"},
                {"pattern": "GatewayTimeout"}
            ]
        }
    )
    print("Query text:")
    print(query)
    print("\nExpected similar incidents:")
    print("- Previous API Gateway timeout issues")
    print("- Async processing implementations")
    print("- Circuit breaker patterns")
    
    print("\n✓ Example scenarios completed\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("KB Query Module Test Suite")
    print("=" * 80 + "\n")
    
    try:
        test_query_conversion()
        test_metadata_parsing()
        test_example_scenarios()
        
        print("=" * 80)
        print("All tests completed successfully!")
        print("=" * 80)
        print("\nNote: To test actual Knowledge Base queries, use:")
        print("  python scripts/test_kb_query.py")
        print("\nThis requires:")
        print("  - AWS credentials configured")
        print("  - Knowledge Base ID from infrastructure setup")
        print("  - Sample incidents populated in the Knowledge Base")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
