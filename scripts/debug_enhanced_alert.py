"""
Debug script to see what the enhanced_alert structure looks like
"""

import json
import sys
sys.path.insert(0, 'src')

from agents.log_analysis_agent import LogAnalysisAgent
from agents.fix_recommendation_agent import FixRecommendationAgent
from agents.communication_agent import CommunicationAgent

# Simulate what the orchestrator does
service_name = "user-service"
timestamp = "2026-03-09T10:43:59.719467Z"
log_location = "s3://incident-response-logs-867126415696/user-service/2026-03-09/throttling.log"
error_message = "ProvisionedThroughputExceededException on users-prod table"
incident_id = "test-incident-123"

print("=" * 80)
print("Step 1: Log Analysis")
print("=" * 80)

log_agent = LogAnalysisAgent()
log_analysis = log_agent.analyze(
    service_name=service_name,
    timestamp=timestamp,
    log_location=log_location
)

print(f"\nLog Analysis Result:")
print(f"  Confidence Score: {log_analysis.get('confidence_score')}")
print(f"  Error Patterns: {len(log_analysis.get('error_patterns', []))}")
print(f"  Bedrock Analysis Keys: {list(log_analysis.get('bedrock_analysis', {}).keys())}")

print("\n" + "=" * 80)
print("Step 2: Root Cause Analysis")
print("=" * 80)

# Extract data from log analysis
bedrock_analysis = log_analysis.get('bedrock_analysis', {})
key_findings = bedrock_analysis.get('key_findings', [])
description = ' '.join(key_findings[:2]) if key_findings else error_message

error_patterns = log_analysis.get('error_patterns', [])
evidence = [p.get('message', '') for p in error_patterns[:3]] if error_patterns else [error_message]

# Determine category
error_lower = error_message.lower()
if 'throttl' in error_lower or 'capacity' in error_lower:
    category = 'resource_exhaustion'
else:
    category = 'dependency_failure'

confidence_score = log_analysis.get('confidence_score', 75)

root_cause = {
    'analysis': {
        'primary_cause': {
            'description': description,
            'category': category,
            'confidence_score': confidence_score,
            'evidence': evidence
        },
        'similar_incidents': []
    }
}

print(f"\nRoot Cause Structure:")
print(json.dumps(root_cause, indent=2))

print("\n" + "=" * 80)
print("Step 3: Fix Recommendations")
print("=" * 80)

fix_agent = FixRecommendationAgent()
fix_recommendations = fix_agent.generate_recommendations(
    root_cause=root_cause,
    service_name=service_name,
    log_summary=log_analysis
)

print(f"\nFix Recommendations Keys: {list(fix_recommendations.keys())}")
if 'recommendations' in fix_recommendations:
    print(f"  Immediate Actions: {len(fix_recommendations['recommendations'].get('immediate_actions', []))}")

print("\n" + "=" * 80)
print("Step 4: Communication Agent")
print("=" * 80)

comm_agent = CommunicationAgent()
summaries = comm_agent.generate_summaries(
    root_cause=root_cause,
    fixes=fix_recommendations,
    original_alert={
        'incident_id': incident_id,
        'service_name': service_name,
        'timestamp': timestamp,
        'error_message': error_message
    }
)

print(f"\nSummaries Structure:")
print(f"  Keys: {list(summaries.keys())}")
if 'enhanced_alert' in summaries:
    enhanced_alert = summaries['enhanced_alert']
    print(f"  Enhanced Alert Keys: {list(enhanced_alert.keys())}")
    print(f"  Confidence Score: {enhanced_alert.get('confidence_score')}")
    print(f"  Root Cause Keys: {list(enhanced_alert.get('root_cause', {}).keys())}")

print("\n" + "=" * 80)
print("Step 5: Email Formatter Structure")
print("=" * 80)

# What the email formatter expects
enhanced_alert = summaries.get('enhanced_alert', {})
root_cause_data = enhanced_alert.get('root_cause', {})
primary_cause = root_cause_data.get('analysis', {}).get('primary_cause', {}) if isinstance(root_cause_data, dict) else {}

fixes_data = enhanced_alert.get('fixes', {})
recommendations = fixes_data.get('recommendations', {}) if isinstance(fixes_data, dict) else {}
immediate_actions = recommendations.get('immediate_actions', [])

email_enhanced_alert = {
    'incident_id': enhanced_alert.get('incident_id', incident_id),
    'timestamp': enhanced_alert.get('timestamp', timestamp),
    'service_name': enhanced_alert.get('service_name', service_name),
    'confidence_score': primary_cause.get('confidence_score', 0),
    'root_cause': {
        'category': primary_cause.get('category', 'Unknown'),
        'description': primary_cause.get('description', 'No description available'),
        'evidence': primary_cause.get('evidence', [])
    },
    'recommended_fixes': immediate_actions,
    'business_summary': enhanced_alert.get('business_summary', {}),
    'original_alert': enhanced_alert.get('original_alert', {})
}

print(f"\nEmail Enhanced Alert:")
print(json.dumps(email_enhanced_alert, indent=2, default=str))
