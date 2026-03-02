#!/usr/bin/env python3
"""
Integration test script for Bedrock Claude root cause analysis.

This script demonstrates the complete workflow:
1. Query Knowledge Base for similar incidents
2. Invoke Bedrock Claude with log summary and historical context
3. Parse structured JSON response with root cause analysis

Usage:
    python scripts/test_bedrock_root_cause_integration.py

Requirements: 3.1, 3.7
"""

import json
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agents.root_cause_classifier import BedrockRootCauseAnalyzer
from src.agents.kb_query import query_similar_incidents

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_bedrock_integration_with_kb():
    """
    Test complete Bedrock integration with Knowledge Base query.
    
    This demonstrates the full workflow:
    1. Query KB for similar incidents
    2. Invoke Claude with historical context
    3. Parse and display results
    """
    logger.info("=" * 80)
    logger.info("Testing Bedrock Claude Root Cause Analysis Integration")
    logger.info("=" * 80)
    
    # Test scenario: Payment gateway timeout
    service_name = "payment-processor"
    error_message = "Connection timeout to payment-gateway.example.com after 10 seconds"
    
    log_summary = {
        "error_patterns": [
            {
                "pattern": "TimeoutException",
                "occurrences": 15,
                "first_seen": "2025-01-15T10:28:45Z",
                "last_seen": "2025-01-15T10:30:12Z"
            },
            {
                "pattern": "ConnectionRefused",
                "occurrences": 3,
                "first_seen": "2025-01-15T10:29:00Z",
                "last_seen": "2025-01-15T10:29:30Z"
            }
        ],
        "stack_traces": [
            {
                "exception": "java.net.SocketTimeoutException",
                "location": "PaymentClient.java:142",
                "message": "Read timed out"
            }
        ],
        "relevant_excerpts": [
            "2025-01-15T10:30:00Z ERROR Failed to connect to payment-gateway.example.com:443",
            "2025-01-15T10:29:45Z WARN Connection pool exhausted, waiting for available connection",
            "2025-01-15T10:29:30Z ERROR Payment gateway health check failed"
        ],
        "log_volume": "2.3 MB",
        "time_range": "10:15:00 - 10:35:00"
    }
    
    logger.info("\n" + "=" * 80)
    logger.info("Step 1: Query Knowledge Base for similar incidents")
    logger.info("=" * 80)
    
    try:
        # Query Knowledge Base for similar incidents
        similar_incidents = query_similar_incidents(
            service_name=service_name,
            error_message=error_message,
            log_summary=log_summary
        )
        
        logger.info(f"\nFound {len(similar_incidents)} similar incidents:")
        for idx, incident in enumerate(similar_incidents, 1):
            logger.info(f"\n  {idx}. Incident: {incident.get('incident_id', 'unknown')}")
            logger.info(f"     Similarity: {incident.get('similarity_score', 0):.0%}")
            logger.info(f"     Root Cause: {incident.get('root_cause', 'N/A')}")
            logger.info(f"     Resolution: {incident.get('resolution', 'N/A')}")
    
    except Exception as e:
        logger.warning(f"Knowledge Base query failed: {str(e)}")
        logger.info("Continuing without historical context...")
        similar_incidents = []
    
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: Invoke Bedrock Claude for root cause analysis")
    logger.info("=" * 80)
    
    try:
        # Initialize Bedrock analyzer
        analyzer = BedrockRootCauseAnalyzer()
        
        # Perform analysis with Bedrock Claude
        result = analyzer.analyze_with_bedrock(
            service_name=service_name,
            error_message=error_message,
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Parse and display results")
        logger.info("=" * 80)
        
        # Display primary cause
        primary = result["primary_cause"]
        logger.info("\n🎯 PRIMARY ROOT CAUSE:")
        logger.info(f"   Category: {primary['category']}")
        logger.info(f"   Description: {primary['description']}")
        logger.info(f"   Confidence: {primary['confidence_score']}%")
        logger.info(f"   Evidence:")
        for evidence in primary.get("evidence", []):
            logger.info(f"     - {evidence}")
        
        # Display alternative causes
        if result.get("alternative_causes"):
            logger.info("\n🔄 ALTERNATIVE CAUSES:")
            for idx, alt in enumerate(result["alternative_causes"], 1):
                logger.info(f"\n   {idx}. {alt['category']} ({alt['confidence_score']}%)")
                logger.info(f"      {alt['description']}")
        
        # Display similar incidents used
        if result.get("similar_incidents"):
            logger.info("\n📚 SIMILAR INCIDENTS REFERENCED:")
            for idx, incident in enumerate(result["similar_incidents"], 1):
                logger.info(f"\n   {idx}. {incident['incident_id']} (similarity: {incident['similarity_score']:.0%})")
                logger.info(f"      Root Cause: {incident['root_cause']}")
                logger.info(f"      Resolution: {incident['resolution']}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Bedrock integration test completed successfully!")
        logger.info("=" * 80)
        
        # Display full JSON result
        logger.info("\n📄 Full JSON Result:")
        logger.info(json.dumps(result, indent=2))
        
        return result
    
    except Exception as e:
        logger.error(f"\n❌ Bedrock integration test failed: {str(e)}")
        logger.exception("Full error details:")
        return None


def test_bedrock_integration_without_kb():
    """
    Test Bedrock integration without Knowledge Base (no historical context).
    
    This demonstrates analysis when no similar incidents are available.
    """
    logger.info("\n\n" + "=" * 80)
    logger.info("Testing Bedrock Analysis WITHOUT Knowledge Base Context")
    logger.info("=" * 80)
    
    # Test scenario: Lambda deployment failure
    service_name = "order-processing-lambda"
    error_message = "Lambda deployment failed: deployment package size exceeds 250MB limit"
    
    log_summary = {
        "error_patterns": [
            {
                "pattern": "DeploymentPackageTooLarge",
                "occurrences": 1
            }
        ],
        "stack_traces": [],
        "relevant_excerpts": [
            "ERROR: Uncompressed deployment package size (275MB) exceeds the limit (250MB)",
            "ERROR: Lambda function update failed"
        ]
    }
    
    try:
        # Initialize Bedrock analyzer
        analyzer = BedrockRootCauseAnalyzer()
        
        # Perform analysis without similar incidents
        result = analyzer.analyze_with_bedrock(
            service_name=service_name,
            error_message=error_message,
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Display results
        primary = result["primary_cause"]
        logger.info("\n🎯 PRIMARY ROOT CAUSE:")
        logger.info(f"   Category: {primary['category']}")
        logger.info(f"   Description: {primary['description']}")
        logger.info(f"   Confidence: {primary['confidence_score']}%")
        
        logger.info("\n✅ Analysis without KB context completed successfully!")
        
        return result
    
    except Exception as e:
        logger.error(f"\n❌ Analysis failed: {str(e)}")
        logger.exception("Full error details:")
        return None


def test_bedrock_fallback():
    """
    Test fallback to rule-based classification when Bedrock fails.
    
    This demonstrates the system's resilience when Bedrock is unavailable.
    """
    logger.info("\n\n" + "=" * 80)
    logger.info("Testing Fallback to Rule-Based Classification")
    logger.info("=" * 80)
    
    # Test scenario: DynamoDB throttling
    service_name = "user-service"
    error_message = "ProvisionedThroughputExceededException: Rate of requests exceeds the allowed throughput"
    
    log_summary = {
        "error_patterns": [
            {
                "pattern": "ThrottlingException",
                "occurrences": 50
            },
            {
                "pattern": "ProvisionedThroughputExceeded",
                "occurrences": 50
            }
        ],
        "stack_traces": [],
        "relevant_excerpts": [
            "ERROR: DynamoDB request throttled",
            "WARN: Retry attempt 3 of 3 failed"
        ]
    }
    
    try:
        # Initialize analyzer with invalid model ID to force fallback
        analyzer = BedrockRootCauseAnalyzer(bedrock_model_id="invalid-model-id")
        
        # This should fall back to rule-based classification
        result = analyzer.analyze_with_bedrock(
            service_name=service_name,
            error_message=error_message,
            log_summary=log_summary,
            similar_incidents=None
        )
        
        # Display results
        primary = result["primary_cause"]
        logger.info("\n🎯 PRIMARY ROOT CAUSE (from fallback):")
        logger.info(f"   Category: {primary['category']}")
        logger.info(f"   Description: {primary['description']}")
        logger.info(f"   Confidence: {primary['confidence_score']}%")
        
        logger.info("\n✅ Fallback mechanism worked successfully!")
        
        return result
    
    except Exception as e:
        logger.error(f"\n❌ Fallback test failed: {str(e)}")
        logger.exception("Full error details:")
        return None


def main():
    """Run all integration tests."""
    logger.info("Starting Bedrock Claude Root Cause Analysis Integration Tests")
    logger.info("=" * 80)
    
    # Test 1: Full integration with Knowledge Base
    result1 = test_bedrock_integration_with_kb()
    
    # Test 2: Integration without Knowledge Base
    result2 = test_bedrock_integration_without_kb()
    
    # Test 3: Fallback mechanism
    # Note: Commented out to avoid unnecessary API errors in normal testing
    # Uncomment to test fallback behavior
    # result3 = test_bedrock_fallback()
    
    logger.info("\n\n" + "=" * 80)
    logger.info("All Integration Tests Completed")
    logger.info("=" * 80)
    
    if result1 and result2:
        logger.info("\n✅ All tests passed successfully!")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Check logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
