#!/usr/bin/env python3
"""
Property-Based Tests for Confidence Score Bounds

Feature: incident-response-system
Property 8: Confidence Score Bounds

For any root cause identification, the confidence score should be a number
between 0 and 100 (inclusive).

Validates: Requirements 3.3
"""

import pytest
from hypothesis import given, strategies as st, assume
from src.agents.root_cause_classifier import (
    FailureCategory,
    classify_failure,
    calculate_confidence_score,
    BedrockRootCauseAnalyzer,
)


# Strategy for generating error messages
@st.composite
def error_message_strategy(draw):
    """Generate realistic error messages for different failure categories."""
    category = draw(st.sampled_from([
        'configuration',
        'resource',
        'dependency'
    ]))
    
    if category == 'configuration':
        templates = [
            "Configuration error: missing {param}",
            "Invalid {param} value: {value}",
            "Environment variable {param} not set",
            "Permission denied: IAM role missing {permission}",
            "Deployment failed: {reason}",
            "Authentication failed: {reason}",
            "Access denied to {resource}",
        ]
        param = draw(st.sampled_from(['DATABASE_URL', 'API_KEY', 'CONFIG_FILE', 'REGION', 'BUCKET_NAME']))
        value = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L', 'N'))))
        permission = draw(st.sampled_from(['s3:GetObject', 'dynamodb:PutItem', 'lambda:InvokeFunction']))
        resource = draw(st.sampled_from(['S3 bucket', 'DynamoDB table', 'Lambda function']))
        reason = draw(st.sampled_from(['invalid syntax', 'malformed JSON', 'missing parameter']))
        
        template = draw(st.sampled_from(templates))
        return template.format(param=param, value=value, permission=permission, resource=resource, reason=reason)
    
    elif category == 'resource':
        templates = [
            "Out of memory: {limit}MB limit exceeded",
            "CPU throttling detected: {percent}% usage",
            "Disk space exhausted: {size}GB used",
            "DynamoDB throttling: ProvisionedThroughputExceededException",
            "Lambda concurrent execution limit reached: {count} executions",
            "Rate limit exceeded: {requests} requests per minute",
            "Storage quota exceeded: {size}GB limit",
        ]
        limit = draw(st.integers(min_value=128, max_value=10240))
        percent = draw(st.integers(min_value=80, max_value=100))
        size = draw(st.integers(min_value=10, max_value=1000))
        count = draw(st.integers(min_value=100, max_value=10000))
        requests = draw(st.integers(min_value=100, max_value=10000))
        
        template = draw(st.sampled_from(templates))
        return template.format(limit=limit, percent=percent, size=size, count=count, requests=requests)
    
    else:  # dependency
        templates = [
            "Connection timeout to {endpoint}",
            "Failed to connect to {service}: connection refused",
            "External API timeout: {endpoint} after {seconds}s",
            "Database connection failed: {reason}",
            "Service unavailable: {service}",
            "Network error: {endpoint} unreachable",
            "Gateway timeout: {service} not responding",
        ]
        endpoint = draw(st.sampled_from([
            'payment-gateway.example.com',
            'api.external-service.com',
            'database.internal.local',
            'cache.redis.local'
        ]))
        service = draw(st.sampled_from(['payment gateway', 'external API', 'database', 'cache service']))
        seconds = draw(st.integers(min_value=5, max_value=60))
        reason = draw(st.sampled_from(['connection refused', 'timeout', 'network unreachable']))
        
        template = draw(st.sampled_from(templates))
        return template.format(endpoint=endpoint, service=service, seconds=seconds, reason=reason)


# Strategy for generating log summaries
@st.composite
def log_summary_strategy(draw):
    """Generate log summary with error patterns."""
    pattern_count = draw(st.integers(min_value=0, max_value=5))
    
    if pattern_count == 0:
        return None
    
    patterns = []
    for _ in range(pattern_count):
        pattern_name = draw(st.sampled_from([
            'ConnectionTimeout',
            'OutOfMemoryError',
            'ConfigurationError',
            'PermissionDenied',
            'ThrottlingException',
            'NetworkError',
            'DeploymentFailed',
        ]))
        occurrences = draw(st.integers(min_value=1, max_value=100))
        patterns.append({
            'pattern': pattern_name,
            'occurrences': occurrences
        })
    
    return {
        'error_patterns': patterns,
        'stack_traces': [],
        'relevant_excerpts': []
    }


# Strategy for generating similar incidents
@st.composite
def similar_incidents_strategy(draw):
    """Generate list of similar past incidents."""
    incident_count = draw(st.integers(min_value=0, max_value=5))
    
    if incident_count == 0:
        return None
    
    incidents = []
    for i in range(incident_count):
        category = draw(st.sampled_from([
            'configuration_error',
            'resource_exhaustion',
            'dependency_failure'
        ]))
        similarity = draw(st.floats(min_value=0.5, max_value=1.0))
        
        incidents.append({
            'incident_id': f'inc-{i:03d}',
            'failure_type': category,
            'similarity_score': similarity,
            'root_cause': f'{category.replace("_", " ").title()} detected',
            'resolution': 'Fixed by adjusting configuration'
        })
    
    return incidents


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_in_classification(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 8: Confidence Score Bounds - Classification
    
    For any root cause identification via classify_failure, the confidence
    score should be a number between 0 and 100 (inclusive).
    
    Validates: Requirements 3.3
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: All confidence scores in ranked categories must be in [0, 100]
    for category, confidence in ranked_categories:
        assert isinstance(confidence, (int, float)), (
            f"Confidence score must be numeric, got {type(confidence)}"
        )
        assert 0 <= confidence <= 100, (
            f"Confidence score for {category.value} must be in [0, 100], got {confidence}"
        )
        
        # Additional check: confidence should be an integer
        assert confidence == int(confidence), (
            f"Confidence score should be an integer, got {confidence}"
        )


@given(
    category=st.sampled_from([
        FailureCategory.CONFIGURATION_ERROR,
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.DEPENDENCY_FAILURE
    ]),
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_in_calculation(
    category,
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 8: Confidence Score Bounds - Direct Calculation
    
    For any direct confidence score calculation, the result should be
    a number between 0 and 100 (inclusive).
    
    Validates: Requirements 3.3
    """
    # Calculate confidence score directly
    confidence = calculate_confidence_score(
        category=category,
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Confidence score must be in [0, 100]
    assert isinstance(confidence, int), (
        f"Confidence score must be an integer, got {type(confidence)}"
    )
    assert 0 <= confidence <= 100, (
        f"Confidence score must be in [0, 100], got {confidence}"
    )


@given(error_message=st.text(min_size=1, max_size=1000))
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_with_arbitrary_input(error_message):
    """
    Property 8: Confidence Score Bounds - Arbitrary Input
    
    For any arbitrary error message (even random text), the confidence
    score should always be bounded to [0, 100].
    
    Validates: Requirements 3.3
    """
    # Filter out empty or whitespace-only messages
    assume(error_message.strip())
    
    # Classify with minimal input
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Property: All confidence scores must be in [0, 100]
    for category, confidence in ranked_categories:
        assert 0 <= confidence <= 100, (
            f"Confidence score for {category.value} must be in [0, 100], "
            f"got {confidence} for input: {error_message[:50]}..."
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_8_confidence_score_is_non_negative(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 8: Confidence Score Bounds - Non-Negative
    
    For any root cause identification, the confidence score should never
    be negative.
    
    Validates: Requirements 3.3
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: All confidence scores must be >= 0
    for category, confidence in ranked_categories:
        assert confidence >= 0, (
            f"Confidence score for {category.value} must be non-negative, got {confidence}"
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_8_confidence_score_does_not_exceed_100(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 8: Confidence Score Bounds - Maximum Bound
    
    For any root cause identification, the confidence score should never
    exceed 100.
    
    Validates: Requirements 3.3
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: All confidence scores must be <= 100
    for category, confidence in ranked_categories:
        assert confidence <= 100, (
            f"Confidence score for {category.value} must not exceed 100, got {confidence}"
        )


@given(
    category=st.sampled_from([
        FailureCategory.CONFIGURATION_ERROR,
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.DEPENDENCY_FAILURE
    ]),
    error_message=st.text(min_size=1, max_size=500)
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_with_minimal_data(category, error_message):
    """
    Property 8: Confidence Score Bounds - Minimal Data
    
    Even with minimal data (no log summary, no similar incidents), the
    confidence score should still be bounded to [0, 100].
    
    Validates: Requirements 3.3
    """
    # Filter out empty or whitespace-only messages
    assume(error_message.strip())
    
    # Calculate confidence with minimal data
    confidence = calculate_confidence_score(
        category=category,
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Property: Confidence score must be in [0, 100]
    assert 0 <= confidence <= 100, (
        f"Confidence score must be in [0, 100] even with minimal data, got {confidence}"
    )


@given(
    error_message=error_message_strategy(),
    pattern_count=st.integers(min_value=0, max_value=20),
    incident_count=st.integers(min_value=0, max_value=10)
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_with_varying_data_volume(
    error_message,
    pattern_count,
    incident_count
):
    """
    Property 8: Confidence Score Bounds - Varying Data Volume
    
    Regardless of the amount of supporting data (many patterns, many incidents,
    or none), the confidence score should always be bounded to [0, 100].
    
    Validates: Requirements 3.3
    """
    # Generate log summary with varying pattern count
    log_summary = None
    if pattern_count > 0:
        patterns = [
            {'pattern': f'Pattern{i}', 'occurrences': i + 1}
            for i in range(pattern_count)
        ]
        log_summary = {
            'error_patterns': patterns,
            'stack_traces': [],
            'relevant_excerpts': []
        }
    
    # Generate similar incidents with varying count
    similar_incidents = None
    if incident_count > 0:
        similar_incidents = [
            {
                'incident_id': f'inc-{i:03d}',
                'failure_type': 'dependency_failure',
                'similarity_score': 0.7,
                'root_cause': 'Test incident',
                'resolution': 'Fixed'
            }
            for i in range(incident_count)
        ]
    
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: All confidence scores must be in [0, 100]
    for category, confidence in ranked_categories:
        assert 0 <= confidence <= 100, (
            f"Confidence score for {category.value} must be in [0, 100] "
            f"with {pattern_count} patterns and {incident_count} incidents, got {confidence}"
        )


@given(
    error_message=st.sampled_from([
        "Configuration error: missing DATABASE_URL",
        "Out of memory: 512MB limit exceeded",
        "Connection timeout to payment-gateway.example.com",
    ]),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_for_clear_failures(
    error_message,
    similar_incidents
):
    """
    Property 8: Confidence Score Bounds - Clear Failure Patterns
    
    Even for very clear failure patterns that should have high confidence,
    the confidence score should not exceed 100.
    
    Validates: Requirements 3.3
    """
    # Classify clear failure patterns
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=similar_incidents
    )
    
    # Property: Even high-confidence classifications must not exceed 100
    primary_confidence = ranked_categories[0][1]
    assert primary_confidence <= 100, (
        f"Even clear failure patterns should not exceed confidence of 100, got {primary_confidence}"
    )
    
    # Property: All confidence scores must be in [0, 100]
    for category, confidence in ranked_categories:
        assert 0 <= confidence <= 100, (
            f"Confidence score for {category.value} must be in [0, 100], got {confidence}"
        )


@given(
    error_message=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(blacklist_categories=('C',))  # Exclude control characters
    )
)
@pytest.mark.property_test
def test_property_8_confidence_score_bounds_with_edge_case_inputs(error_message):
    """
    Property 8: Confidence Score Bounds - Edge Case Inputs
    
    For edge case inputs (very short, special characters, etc.), the
    confidence score should still be bounded to [0, 100].
    
    Validates: Requirements 3.3
    """
    # Filter out empty or whitespace-only messages
    assume(error_message.strip())
    
    try:
        # Classify with edge case input
        primary_category, ranked_categories = classify_failure(
            error_message=error_message,
            log_summary=None,
            similar_incidents=None
        )
        
        # Property: All confidence scores must be in [0, 100]
        for category, confidence in ranked_categories:
            assert 0 <= confidence <= 100, (
                f"Confidence score for {category.value} must be in [0, 100] "
                f"for edge case input, got {confidence}"
            )
    except Exception as e:
        # If classification fails, that's acceptable for edge cases,
        # but we should not get invalid confidence scores
        pytest.fail(f"Classification should handle edge cases gracefully: {str(e)}")
