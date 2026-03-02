"""
Tests for Knowledge Base sample population script.

These tests verify the structure and content of sample incidents
without requiring AWS infrastructure to be set up.
"""
import sys
import os

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Import the sample data
from populate_kb_samples import SAMPLE_INCIDENTS, create_incident_document


def test_sample_incidents_count():
    """Verify we have exactly 15 sample incidents"""
    assert len(SAMPLE_INCIDENTS) == 15, f"Expected 15 incidents, got {len(SAMPLE_INCIDENTS)}"


def test_sample_incidents_categories():
    """Verify incidents are distributed across three categories"""
    categories = {}
    for incident in SAMPLE_INCIDENTS:
        category = incident['category']
        categories[category] = categories.get(category, 0) + 1
    
    assert categories.get('configuration_error', 0) == 5, "Expected 5 configuration errors"
    assert categories.get('resource_exhaustion', 0) == 5, "Expected 5 resource exhaustion incidents"
    assert categories.get('dependency_failure', 0) == 5, "Expected 5 dependency failures"


def test_sample_incidents_aws_services():
    """Verify AWS-native scenarios are covered"""
    aws_services = set()
    for incident in SAMPLE_INCIDENTS:
        aws_services.add(incident['aws_service'])
    
    # Required AWS services from task requirements
    required_services = {'Lambda', 'DynamoDB', 'RDS', 'API Gateway', 'Step Functions'}
    
    assert required_services.issubset(aws_services), \
        f"Missing required AWS services. Expected {required_services}, got {aws_services}"


def test_sample_incident_structure():
    """Verify each incident has required fields"""
    required_fields = [
        'incident_id', 'timestamp', 'service_name', 'failure_type',
        'root_cause', 'description', 'category', 'aws_service',
        'resolution_steps', 'preventive_measures'
    ]
    
    for incident in SAMPLE_INCIDENTS:
        for field in required_fields:
            assert field in incident, \
                f"Incident {incident.get('incident_id', 'unknown')} missing field: {field}"


def test_incident_document_creation():
    """Verify incident document formatting"""
    incident = SAMPLE_INCIDENTS[0]
    doc = create_incident_document(incident)
    
    # Check document contains key sections
    assert '# Incident Report:' in doc
    assert '## Metadata' in doc
    assert '## Root Cause' in doc
    assert '## Description' in doc
    assert '## Resolution Steps' in doc
    assert '## Preventive Measures' in doc
    
    # Check metadata fields are present
    assert incident['incident_id'] in doc
    assert incident['service_name'] in doc
    assert incident['aws_service'] in doc


def test_configuration_error_incidents():
    """Verify configuration error incidents cover required scenarios"""
    config_errors = [inc for inc in SAMPLE_INCIDENTS if inc['category'] == 'configuration_error']
    
    # Check we have Lambda, API Gateway, IAM, Step Functions, SES scenarios
    services = {inc['aws_service'] for inc in config_errors}
    assert 'Lambda' in services, "Missing Lambda configuration error"
    assert 'API Gateway' in services, "Missing API Gateway configuration error"
    
    # Check for specific error types
    root_causes = [inc['root_cause'].lower() for inc in config_errors]
    assert any('environment variable' in rc for rc in root_causes), "Missing environment variable error"
    assert any('timeout' in rc for rc in root_causes), "Missing timeout configuration error"
    assert any('iam' in rc or 'permission' in rc for rc in root_causes), "Missing IAM permission error"


def test_resource_exhaustion_incidents():
    """Verify resource exhaustion incidents cover required scenarios"""
    resource_errors = [inc for inc in SAMPLE_INCIDENTS if inc['category'] == 'resource_exhaustion']
    
    # Check we have Lambda, DynamoDB, RDS scenarios
    services = {inc['aws_service'] for inc in resource_errors}
    assert 'Lambda' in services, "Missing Lambda resource exhaustion"
    assert 'DynamoDB' in services, "Missing DynamoDB resource exhaustion"
    assert 'RDS' in services, "Missing RDS resource exhaustion"
    
    # Check for specific resource types
    descriptions = [inc['description'].lower() for inc in resource_errors]
    assert any('memory' in desc for desc in descriptions), "Missing memory exhaustion"
    assert any('throttl' in desc for desc in descriptions), "Missing throttling scenario"
    assert any('storage' in desc for desc in descriptions), "Missing storage exhaustion"


def test_dependency_failure_incidents():
    """Verify dependency failure incidents cover required scenarios"""
    dep_failures = [inc for inc in SAMPLE_INCIDENTS if inc['category'] == 'dependency_failure']
    
    # Check for external dependency scenarios
    descriptions = [inc['description'].lower() for inc in dep_failures]
    assert any('timeout' in desc for desc in descriptions), "Missing timeout scenario"
    assert any('connection' in desc for desc in descriptions), "Missing connection failure"
    assert any('rate limit' in desc or 'throttl' in desc for desc in descriptions), \
        "Missing rate limiting scenario"


def test_incident_ids_unique():
    """Verify all incident IDs are unique"""
    incident_ids = [inc['incident_id'] for inc in SAMPLE_INCIDENTS]
    assert len(incident_ids) == len(set(incident_ids)), "Duplicate incident IDs found"


def test_incident_timestamps_valid():
    """Verify all timestamps are in ISO 8601 format"""
    import re
    iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'
    
    for incident in SAMPLE_INCIDENTS:
        timestamp = incident['timestamp']
        assert re.match(iso8601_pattern, timestamp), \
            f"Invalid timestamp format for {incident['incident_id']}: {timestamp}"


def test_resolution_steps_not_empty():
    """Verify all incidents have resolution steps"""
    for incident in SAMPLE_INCIDENTS:
        assert len(incident['resolution_steps']) > 0, \
            f"Incident {incident['incident_id']} has no resolution steps"


def test_preventive_measures_not_empty():
    """Verify all incidents have preventive measures"""
    for incident in SAMPLE_INCIDENTS:
        assert len(incident['preventive_measures']) > 0, \
            f"Incident {incident['incident_id']} has no preventive measures"


def test_descriptions_contain_error_patterns():
    """Verify descriptions include error patterns for analysis"""
    for incident in SAMPLE_INCIDENTS:
        description = incident['description'].lower()
        # Should contain error-related keywords
        has_error_info = any(keyword in description for keyword in [
            'error', 'exception', 'failed', 'failure', 'timeout', 'throttl'
        ])
        assert has_error_info, \
            f"Incident {incident['incident_id']} description lacks error pattern information"


if __name__ == '__main__':
    # Run tests manually
    import traceback
    
    tests = [
        test_sample_incidents_count,
        test_sample_incidents_categories,
        test_sample_incidents_aws_services,
        test_sample_incident_structure,
        test_incident_document_creation,
        test_configuration_error_incidents,
        test_resource_exhaustion_incidents,
        test_dependency_failure_incidents,
        test_incident_ids_unique,
        test_incident_timestamps_valid,
        test_resolution_steps_not_empty,
        test_preventive_measures_not_empty,
        test_descriptions_contain_error_patterns
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"✓ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
