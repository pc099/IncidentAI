#!/usr/bin/env python3
"""
Test log analysis agent locally to debug Bedrock issues
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.log_analysis_agent import LogAnalysisAgent

def test_log_analysis():
    """Test the log analysis agent"""
    print("Testing Log Analysis Agent...")
    print("=" * 80)
    
    agent = LogAnalysisAgent()
    print(f"Model ID: {agent.model_id}")
    
    # Test with the actual log location
    result = agent.analyze(
        service_name="payment-processor",
        timestamp="2026-03-09T08:12:15.953370Z",
        log_location="s3://incident-response-logs-867126415696/payment-processor/2026-03-09/timeout.log"
    )
    
    print("\nResult:")
    print(f"Confidence Score: {result.get('confidence_score', 0)}%")
    print(f"Error Patterns: {len(result.get('error_patterns', []))}")
    print(f"Stack Traces: {len(result.get('stack_traces', []))}")
    
    if 'error' in result:
        print(f"\nERROR: {result['error']}")
    
    if 'bedrock_analysis' in result:
        print(f"\nBedrock Analysis: {result['bedrock_analysis']}")
    
    return result

if __name__ == "__main__":
    result = test_log_analysis()
