#!/usr/bin/env python3
"""
Property-Based Tests for Root Cause Ranking

Feature: incident-response-system
Property 9: Root Cause Ranking

For any analysis with multiple potential root causes, the causes should be
ranked in descending order by confidence score (highest confidence first).

Validates: Requirements 3.4
"""

import pytest
from hypothesis import given, strategies as st, assume
from src.agents.root_cause_classifier import (
    FailureCategory,
    classify_failure,
    format_root_cause_analysis,
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
def test_property_9_root_cause_ranking_descending_order(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - Descending Order
    
    For any analysis with multiple potential root causes, the causes should be
    ranked in descending order by confidence score (highest confidence first).
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property 1: Should have multiple causes (at least 2)
    assert len(ranked_categories) >= 2, (
        f"Should have multiple potential causes, got {len(ranked_categories)}"
    )
    
    # Property 2: Causes should be ranked in descending order by confidence
    for i in range(len(ranked_categories) - 1):
        current_category, current_confidence = ranked_categories[i]
        next_category, next_confidence = ranked_categories[i + 1]
        
        assert current_confidence >= next_confidence, (
            f"Causes should be ranked in descending order by confidence: "
            f"{current_category.value} (confidence={current_confidence}) should be >= "
            f"{next_category.value} (confidence={next_confidence}) at position {i}"
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_primary_is_highest(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - Primary Cause is Highest
    
    For any analysis, the primary cause should have the highest confidence
    score among all potential causes.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Primary category should match the first ranked category
    assert primary_category == ranked_categories[0][0], (
        f"Primary category {primary_category.value} should match "
        f"highest ranked category {ranked_categories[0][0].value}"
    )
    
    # Property: Primary cause should have highest confidence
    primary_confidence = ranked_categories[0][1]
    for category, confidence in ranked_categories[1:]:
        assert primary_confidence >= confidence, (
            f"Primary cause confidence ({primary_confidence}) should be >= "
            f"all other causes (found {category.value} with confidence {confidence})"
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_all_three_categories_ranked(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - All Categories Ranked
    
    For any analysis, all three failure categories should be present in the
    ranked results, each with a confidence score.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Should have exactly 3 ranked categories
    assert len(ranked_categories) == 3, (
        f"Should rank all 3 categories, got {len(ranked_categories)}"
    )
    
    # Property: All three categories should be present
    categories_in_results = [cat for cat, _ in ranked_categories]
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
def test_property_9_root_cause_ranking_confidence_scores_valid(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - Valid Confidence Scores
    
    For any ranked causes, all confidence scores should be valid (0-100)
    and in descending order.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: All confidence scores should be valid (0-100)
    for category, confidence in ranked_categories:
        assert 0 <= confidence <= 100, (
            f"Confidence score for {category.value} should be in [0, 100], got {confidence}"
        )
    
    # Property: Confidence scores should be in descending order
    confidences = [conf for _, conf in ranked_categories]
    assert confidences == sorted(confidences, reverse=True), (
        f"Confidence scores should be in descending order, got {confidences}"
    )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_formatted_output_preserves_order(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - Formatted Output Preserves Order
    
    For any analysis, the formatted output should preserve the ranking order
    with primary cause first and alternatives in descending confidence order.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Format the analysis
    formatted = format_root_cause_analysis(
        primary_category=primary_category,
        ranked_categories=ranked_categories,
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Primary cause should match highest ranked category
    assert formatted["primary_cause"]["category"] == ranked_categories[0][0].value, (
        f"Formatted primary cause should match highest ranked category"
    )
    assert formatted["primary_cause"]["confidence_score"] == ranked_categories[0][1], (
        f"Formatted primary confidence should match highest ranked confidence"
    )
    
    # Property: Alternative causes should be in descending order
    alternative_confidences = [
        alt["confidence_score"] for alt in formatted["alternative_causes"]
    ]
    assert alternative_confidences == sorted(alternative_confidences, reverse=True), (
        f"Alternative causes should be in descending confidence order, got {alternative_confidences}"
    )
    
    # Property: Alternative causes should match ranked categories (excluding primary)
    expected_alternatives = ranked_categories[1:]
    assert len(formatted["alternative_causes"]) == len(expected_alternatives), (
        f"Should have {len(expected_alternatives)} alternative causes, "
        f"got {len(formatted['alternative_causes'])}"
    )
    
    for i, (expected_cat, expected_conf) in enumerate(expected_alternatives):
        actual_alt = formatted["alternative_causes"][i]
        assert actual_alt["category"] == expected_cat.value, (
            f"Alternative cause {i} category should be {expected_cat.value}, "
            f"got {actual_alt['category']}"
        )
        assert actual_alt["confidence_score"] == expected_conf, (
            f"Alternative cause {i} confidence should be {expected_conf}, "
            f"got {actual_alt['confidence_score']}"
        )


@given(
    error_message=st.sampled_from([
        "Connection timeout to payment-gateway.example.com",
        "Out of memory: 512MB limit exceeded",
        "Configuration error: missing DATABASE_URL",
    ])
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_clear_primary_has_highest_confidence(
    error_message
):
    """
    Property 9: Root Cause Ranking - Clear Primary Cause
    
    For error messages with clear failure patterns, the matching category
    should have the highest confidence and be ranked first.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=None,
        similar_incidents=None
    )
    
    # Determine expected category based on error message
    if "timeout" in error_message.lower() or "connection" in error_message.lower():
        expected_category = FailureCategory.DEPENDENCY_FAILURE
    elif "memory" in error_message.lower() or "limit exceeded" in error_message.lower():
        expected_category = FailureCategory.RESOURCE_EXHAUSTION
    elif "configuration" in error_message.lower() or "missing" in error_message.lower():
        expected_category = FailureCategory.CONFIGURATION_ERROR
    else:
        # Skip if we can't determine expected category
        return
    
    # Property: Primary category should match expected category
    assert primary_category == expected_category, (
        f"Clear error pattern should be classified correctly: "
        f"expected {expected_category.value}, got {primary_category.value}"
    )
    
    # Property: Primary category should be ranked first
    assert ranked_categories[0][0] == expected_category, (
        f"Expected category should be ranked first"
    )
    
    # Property: Primary category should have highest confidence
    primary_confidence = ranked_categories[0][1]
    for category, confidence in ranked_categories[1:]:
        assert primary_confidence > confidence, (
            f"Primary cause confidence ({primary_confidence}) should be > "
            f"alternative causes (found {category.value} with confidence {confidence})"
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy()
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_is_stable(
    error_message,
    log_summary
):
    """
    Property 9: Root Cause Ranking - Stability
    
    For any given input, the ranking should be stable (same input produces
    same ranking order).
    
    Validates: Requirements 3.4
    """
    # Classify twice with same inputs
    primary1, ranked1 = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=None
    )
    
    primary2, ranked2 = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=None
    )
    
    # Property: Rankings should be identical
    assert len(ranked1) == len(ranked2), (
        f"Ranking length should be stable: {len(ranked1)} != {len(ranked2)}"
    )
    
    for i, ((cat1, conf1), (cat2, conf2)) in enumerate(zip(ranked1, ranked2)):
        assert cat1 == cat2, (
            f"Category at position {i} should be stable: {cat1.value} != {cat2.value}"
        )
        assert conf1 == conf2, (
            f"Confidence at position {i} should be stable: {conf1} != {conf2}"
        )


@given(
    error_message=error_message_strategy(),
    log_summary=log_summary_strategy(),
    similar_incidents=similar_incidents_strategy()
)
@pytest.mark.property_test
def test_property_9_root_cause_ranking_no_ties_at_top(
    error_message,
    log_summary,
    similar_incidents
):
    """
    Property 9: Root Cause Ranking - No Ambiguous Top Ranking
    
    For any analysis, if there are ties in confidence scores, the ranking
    should still be deterministic and consistent.
    
    Validates: Requirements 3.4
    """
    # Classify the failure
    primary_category, ranked_categories = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    # Property: Primary cause should be unambiguous (first in ranking)
    assert primary_category == ranked_categories[0][0], (
        f"Primary cause should always be the first ranked category"
    )
    
    # Property: Even if there are ties, ranking should be deterministic
    # (same input should produce same ranking)
    primary2, ranked2 = classify_failure(
        error_message=error_message,
        log_summary=log_summary,
        similar_incidents=similar_incidents
    )
    
    assert primary_category == primary2, (
        f"Primary cause should be deterministic even with ties"
    )
    
    for i, ((cat1, conf1), (cat2, conf2)) in enumerate(zip(ranked_categories, ranked2)):
        assert cat1 == cat2, (
            f"Ranking should be deterministic at position {i}"
        )


@given(error_message=st.text(min_size=1, max_size=500))
@pytest.mark.property_test
def test_property_9_root_cause_ranking_never_crashes(error_message):
    """
    Property 9: Root Cause Ranking - Robustness
    
    For any error message (even arbitrary text), the ranking should never
    crash and should always produce a valid descending order.
    
    Validates: Requirements 3.4
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
        
        # Property: Should produce valid ranking
        assert len(ranked_categories) >= 2, (
            f"Should produce multiple ranked causes"
        )
        
        # Property: Should be in descending order
        for i in range(len(ranked_categories) - 1):
            current_conf = ranked_categories[i][1]
            next_conf = ranked_categories[i + 1][1]
            assert current_conf >= next_conf, (
                f"Ranking should be in descending order even for arbitrary input"
            )
    
    except Exception as e:
        pytest.fail(f"Ranking should never crash, got error: {str(e)}")
