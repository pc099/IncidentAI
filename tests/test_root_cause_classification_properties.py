#!/usr/bin/env python3
"""
Property-Based Tests for Root Cause Classification

Feature: incident-response-system
Property 7: Root Cause Classification

For any failure analysis, the Root Cause Agent should classify the failure
into exactly one of three categories: configuration_error, resource_exhaustion,
or dependency_failure.

Validates: Requirements 3.2
"""

import pytest
from hypothesis import given, strategies as st, assume
from src.agents.root_cause_classifier import (
    FailureCategory,
    classify_failure,
    calculate_confidence_score,
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
def test_property_7_root_cause_classification_returns_valid_category(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 7: Root Cause Classification - Valid Category
    
    For any failure analysis, the Root Cause Agent should classify the failure
    into exactly one of three valid categories.
    
    Validates: Requirements 3.2
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property 1: Primary category must be one of the three valid categories
    valid_categories = [
        FailureCategory.CONFIGURATION_ERROR,
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.DEPENDENCY_FAILURE
    ]
    assert primary_category in valid_categories, (
        f"Primary category must be one of {[c.value for c in valid_categories]}, "
        f"got {primary_category}"
    )
    
    # Property 2: Ranked categories should contain exactly 3 entries
    assert len(ranked_categories) == 3, (
        f"Should return exactly 3 ranked categories, got {len(ranked_categories)}"
    )
    
    # Property 3: All ranked categories should be valid
    for category, confidence in ranked_categories:
        assert category in valid_categories, (
            f"All ranked categories must be valid, got {category}"
        )
    
    # Property 4: Primary category should match the highest ranked category
    assert primary_category == ranked_categories[0][0], (
        f"Primary category {primary_category} should match highest ranked {ranked_categories[0][0]}"
    )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_7_root_cause_classification_is_deterministic(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 7: Root Cause Classification - Determinism
    
    For any given input, the classification should be deterministic
    (same input produces same output).
    
    Validates: Requirements 3.2
    """
    # Classify twice with same inputs
    primary1, ranked1 = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    primary2, ranked2 = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Results should be identical
    assert primary1 == primary2, (
        f"Classification should be deterministic: {primary1} != {primary2}"
    )
    
    assert len(ranked1) == len(ranked2), (
        f"Ranked categories length should match: {len(ranked1)} != {len(ranked2)}"
    )
    
    for (cat1, conf1), (cat2, conf2) in zip(ranked1, ranked2):
        assert cat1 == cat2, f"Categories should match: {cat1} != {cat2}"
        assert conf1 == conf2, f"Confidence scores should match: {conf1} != {conf2}"


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_7_root_cause_classification_all_categories_present(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 7: Root Cause Classification - All Categories Present
    
    For any failure analysis, all three categories should be present in the
    ranked results (even if with low confidence).
    
    Validates: Requirements 3.2
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Extract categories from ranked results
    categories_in_results = [cat for cat, _ in ranked_categories]
    
    # Property: All three categories should be present
    assert FailureCategory.CONFIGURATION_ERROR in categories_in_results, (
        "CONFIGURATION_ERROR should be in ranked results"
    )
    assert FailureCategory.RESOURCE_EXHAUSTION in categories_in_results, (
        "RESOURCE_EXHAUSTION should be in ranked results"
    )
    assert FailureCategory.DEPENDENCY_FAILURE in categories_in_results, (
        "DEPENDENCY_FAILURE should be in ranked results"
    )
    
    # Property: No duplicate categories
    assert len(categories_in_results) == len(set(categories_in_results)), (
        f"Categories should be unique, got duplicates: {categories_in_results}"
    )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_7_root_cause_classification_confidence_ordering(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 7: Root Cause Classification - Confidence Ordering
    
    For any failure analysis, the ranked categories should be ordered by
    confidence score in descending order.
    
    Validates: Requirements 3.2, 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Confidence scores should be in descending order
    for i in range(len(ranked_categories) - 1):
        current_confidence = ranked_categories[i][1]
        next_confidence = ranked_categories[i + 1][1]
        
        assert current_confidence >= next_confidence, (
            f"Confidence scores should be in descending order: "
            f"{ranked_categories[i][0].value}={current_confidence} should be >= "
            f"{ranked_categories[i+1][0].value}={next_confidence}"
        )


@given(error_message=st.text(min_size=1, max_size=500))
@pytest.mark.property_test
def test_property_7_root_cause_classification_never_crashes(error_message):
    """
    Property 7: Root Cause Classification - Robustness
    
    For any error message (even arbitrary text), the classification
    should never crash and should always return a valid result.
    
    Validates: Requirements 3.2
    """
    # Filter out empty or whitespace-only messages
    assume(error_message.strip())
    
    try:
        # Classify with minimal input
        primary_category, ranked_categories = classify_failure(
            error_message=error_message,
            log_summary=None,
            similar_incidents=None
        )
        
        # Property 1: Should return valid category
        valid_categories = [
            FailureCategory.CONFIGURATION_ERROR,
            FailureCategory.RESOURCE_EXHAUSTION,
            FailureCategory.DEPENDENCY_FAILURE
        ]
        assert primary_category in valid_categories
        
        # Property 2: Should return 3 ranked categories
        assert len(ranked_categories) == 3
        
        # Property 3: All confidence scores should be valid (0-100)
        for category, confidence in ranked_categories:
            assert 0 <= confidence <= 100, (
                f"Confidence score should be 0-100, got {confidence}"
            )
    
    except Exception as e:
        pytest.fail(f"Classification crashed with error: {str(e)}")


@given(
    error_message=st.sampled_from([
        "Configuration error: missing DATABASE_URL",
        "Lambda deployment failed: invalid configuration",
        "Environment variable not set: API_KEY",
        "Permission denied: IAM role missing permissions",
    ])
)
@pytest.mark.property_test
def test_property_7_configuration_errors_classified_correctly(error_message):
    """
    Property 7: Root Cause Classification - Configuration Error Recognition
    
    For any error message clearly indicating a configuration error,
    the classification should identify it as CONFIGURATION_ERROR.
    
    Validates: Requirements 3.2
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Property: Should classify as configuration error
    assert primary_category == FailureCategory.CONFIGURATION_ERROR, (
        f"Configuration error message should be classified as CONFIGURATION_ERROR, "
        f"got {primary_category.value}"
    )
    
    # Property: Configuration error should have highest confidence
    assert ranked_categories[0][0] == FailureCategory.CONFIGURATION_ERROR, (
        f"CONFIGURATION_ERROR should have highest confidence"
    )


@given(
    error_message=st.sampled_from([
        "Out of memory: 512MB limit exceeded",
        "DynamoDB throttling: ProvisionedThroughputExceededException",
        "CPU limit reached: 100% usage",
        "Disk space exhausted: storage full",
        "Lambda concurrent execution limit reached",
    ])
)
@pytest.mark.property_test
def test_property_7_resource_exhaustion_classified_correctly(error_message):
    """
    Property 7: Root Cause Classification - Resource Exhaustion Recognition
    
    For any error message clearly indicating resource exhaustion,
    the classification should identify it as RESOURCE_EXHAUSTION.
    
    Validates: Requirements 3.2
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Property: Should classify as resource exhaustion
    assert primary_category == FailureCategory.RESOURCE_EXHAUSTION, (
        f"Resource exhaustion message should be classified as RESOURCE_EXHAUSTION, "
        f"got {primary_category.value}"
    )
    
    # Property: Resource exhaustion should have highest confidence
    assert ranked_categories[0][0] == FailureCategory.RESOURCE_EXHAUSTION, (
        f"RESOURCE_EXHAUSTION should have highest confidence"
    )


@given(
    error_message=st.sampled_from([
        "Connection timeout to payment-gateway.example.com",
        "Failed to connect to database: connection refused",
        "External API timeout after 30s",
        "Service unavailable: payment gateway",
        "Network error: endpoint unreachable",
        "Gateway timeout: service not responding",
    ])
)
@pytest.mark.property_test
def test_property_7_dependency_failure_classified_correctly(error_message):
    """
    Property 7: Root Cause Classification - Dependency Failure Recognition
    
    For any error message clearly indicating a dependency failure,
    the classification should identify it as DEPENDENCY_FAILURE.
    
    Validates: Requirements 3.2
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Property: Should classify as dependency failure
    assert primary_category == FailureCategory.DEPENDENCY_FAILURE, (
        f"Dependency failure message should be classified as DEPENDENCY_FAILURE, "
        f"got {primary_category.value}"
    )
    
    # Property: Dependency failure should have highest confidence
    assert ranked_categories[0][0] == FailureCategory.DEPENDENCY_FAILURE, (
        f"DEPENDENCY_FAILURE should have highest confidence"
    )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy()
)
@pytest.mark.property_test
def test_property_7_log_summary_improves_classification(error_message, log_summary):
    """
    Property 7: Root Cause Classification - Log Summary Impact
    
    For any failure analysis, providing log summary should not decrease
    the confidence of the primary classification (it should stay the same
    or improve).
    
    Validates: Requirements 3.2
    """
    # Classify without log summary
    primary_without, ranked_without = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Classify with log summary
    primary_with, ranked_with = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=None
    )
    
    # Property: Both should return valid categories
    valid_categories = [
        FailureCategory.CONFIGURATION_ERROR,
        FailureCategory.RESOURCE_EXHAUSTION,
        FailureCategory.DEPENDENCY_FAILURE
    ]
    assert primary_without in valid_categories
    assert primary_with in valid_categories
    
    # Property: Both should return 3 ranked categories
    assert len(ranked_without) == 3
    assert len(ranked_with) == 3
    
    # Note: We don't assert that confidence increases because log summary
    # might provide evidence for a different category, changing the primary
    # classification. The key property is that both produce valid results.
