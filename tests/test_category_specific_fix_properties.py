"""
Property-Based Tests for Category-Specific Fix Content

Property 13: Category-Specific Fix Content
For any root cause in a specific category (configuration_error, resource_exhaustion, or dependency_failure),
the fix recommendations should include category-appropriate details: configuration parameters for config errors,
scaling values for resource exhaustion, or health checks for dependency failures.

Validates: Requirements 4.3, 4.4, 4.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.agents.fix_recommendation_agent import FixRecommendationAgent


# Strategy for generating root cause analysis outputs by category
@st.composite
def configuration_error_strategy(draw):
    """Generate configuration error root causes."""
    config_descriptions = [
        "Invalid configuration parameter",
        "Missing required configuration",
        "Incorrect environment variable",
        "Wrong IAM permissions configured",
        "Invalid timeout setting"
    ]
    
    return {
        "primary_cause": {
            "category": "configuration_error",
            "description": draw(st.sampled_from(config_descriptions)),
            "confidence_score": draw(st.integers(min_value=50, max_value=100)),
            "evidence": draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        }
    }


@st.composite
def resource_exhaustion_strategy(draw):
    """Generate resource exhaustion root causes."""
    resource_descriptions = [
        "Memory limit exceeded",
        "CPU utilization at 100%",
        "Disk space exhausted",
        "Connection pool exhausted",
        "Concurrent execution limit reached"
    ]
    
    return {
        "primary_cause": {
            "category": "resource_exhaustion",
            "description": draw(st.sampled_from(resource_descriptions)),
            "confidence_score": draw(st.integers(min_value=50, max_value=100)),
            "evidence": draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        }
    }


@st.composite
def dependency_failure_strategy(draw):
    """Generate dependency failure root causes."""
    dependency_descriptions = [
        "External API timeout",
        "Database connection failure",
        "Network connectivity issue",
        "Third-party service unavailable",
        "DNS resolution failure"
    ]
    
    return {
        "primary_cause": {
            "category": "dependency_failure",
            "description": draw(st.sampled_from(dependency_descriptions)),
            "confidence_score": draw(st.integers(min_value=50, max_value=100)),
            "evidence": draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        }
    }


@given(
    root_cause=configuration_error_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_13_configuration_error_includes_parameter_details(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 13: Category-Specific Fix Content (Configuration Errors)
    
    For any configuration error root cause, the fix recommendations should include
    configuration parameter details (identify parameter, provide correct value, show update command).
    
    Validates: Requirements 4.3
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name=service_name
    )
    
    # Assert
    immediate_actions = result["recommendations"]["immediate_actions"]
    
    # Property: Configuration errors should have actions related to configuration
    action_texts = " ".join([
        action.get("action", "") + " " + action.get("details", "")
        for action in immediate_actions
    ]).lower()
    
    # Check for configuration-related keywords
    config_keywords = ["configuration", "config", "parameter", "setting", "value", "update", "validate"]
    has_config_content = any(keyword in action_texts for keyword in config_keywords)
    
    assert has_config_content, (
        f"Configuration error fixes must include configuration-related content. "
        f"Actions: {[a.get('action') for a in immediate_actions]}"
    )


@given(
    root_cause=resource_exhaustion_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_13_resource_exhaustion_includes_scaling_details(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 13: Category-Specific Fix Content (Resource Exhaustion)
    
    For any resource exhaustion root cause, the fix recommendations should include
    scaling details (identify resource, calculate scaling, provide scaling commands).
    
    Validates: Requirements 4.4
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name=service_name
    )
    
    # Assert
    immediate_actions = result["recommendations"]["immediate_actions"]
    
    # Property: Resource exhaustion should have actions related to scaling/resources
    action_texts = " ".join([
        action.get("action", "") + " " + action.get("details", "")
        for action in immediate_actions
    ]).lower()
    
    # Check for resource/scaling-related keywords
    resource_keywords = ["resource", "scale", "scaling", "capacity", "memory", "cpu", "disk", "increase", "limit"]
    has_resource_content = any(keyword in action_texts for keyword in resource_keywords)
    
    assert has_resource_content, (
        f"Resource exhaustion fixes must include resource/scaling-related content. "
        f"Actions: {[a.get('action') for a in immediate_actions]}"
    )


@given(
    root_cause=dependency_failure_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_13_dependency_failure_includes_health_checks(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 13: Category-Specific Fix Content (Dependency Failures)
    
    For any dependency failure root cause, the fix recommendations should include
    health check details (verify health, increase timeout/retry, implement fallback).
    
    Validates: Requirements 4.5
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name=service_name
    )
    
    # Assert
    immediate_actions = result["recommendations"]["immediate_actions"]
    
    # Property: Dependency failures should have actions related to health/timeout/retry
    action_texts = " ".join([
        action.get("action", "") + " " + action.get("details", "")
        for action in immediate_actions
    ]).lower()
    
    # Check for dependency-related keywords
    dependency_keywords = ["health", "verify", "timeout", "retry", "fallback", "dependency", "connection", "circuit breaker"]
    has_dependency_content = any(keyword in action_texts for keyword in dependency_keywords)
    
    assert has_dependency_content, (
        f"Dependency failure fixes must include health/timeout/retry-related content. "
        f"Actions: {[a.get('action') for a in immediate_actions]}"
    )


@given(
    category=st.sampled_from(["configuration_error", "resource_exhaustion", "dependency_failure"])
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_13_preventive_measures_match_category(category):
    """
    Feature: incident-response-system
    Property 13 (Extended): Preventive Measures Match Category
    
    For any root cause category, the preventive measures should be appropriate
    for that category type.
    
    Validates: Requirements 4.3, 4.4, 4.5
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    root_cause = {
        "primary_cause": {
            "category": category,
            "description": f"Test {category} description",
            "confidence_score": 75,
            "evidence": ["Evidence 1", "Evidence 2"]
        }
    }
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name="test-service"
    )
    
    # Assert
    preventive_measures = result["recommendations"]["preventive_measures"]
    
    # Property: Preventive measures should exist
    assert len(preventive_measures) > 0, (
        f"Category {category} must have preventive measures"
    )
    
    # Property: Each preventive measure should have required fields
    for measure in preventive_measures:
        assert "action" in measure, "Preventive measure must have 'action' field"
        assert "description" in measure, "Preventive measure must have 'description' field"
        assert "priority" in measure, "Preventive measure must have 'priority' field"
        assert measure["priority"] in ["high", "medium", "low"], (
            f"Priority must be high/medium/low, got {measure['priority']}"
        )


@given(
    category=st.sampled_from(["configuration_error", "resource_exhaustion", "dependency_failure"])
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_13_rollback_plan_exists_for_all_categories(category):
    """
    Feature: incident-response-system
    Property 13 (Extended): Rollback Plan Exists
    
    For any root cause category, a rollback plan should be provided.
    
    Validates: Requirements 4.3, 4.4, 4.5
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    root_cause = {
        "primary_cause": {
            "category": category,
            "description": f"Test {category} description",
            "confidence_score": 75,
            "evidence": ["Evidence 1", "Evidence 2"]
        }
    }
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name="test-service"
    )
    
    # Assert
    rollback_plan = result["recommendations"]["rollback_plan"]
    
    # Property: Rollback plan must exist and be non-empty
    assert rollback_plan, f"Category {category} must have a rollback plan"
    assert isinstance(rollback_plan, str), "Rollback plan must be a string"
    assert len(rollback_plan) > 10, "Rollback plan must be descriptive (>10 characters)"


@given(
    root_cause=st.one_of(
        configuration_error_strategy(),
        resource_exhaustion_strategy(),
        dependency_failure_strategy()
    ),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_13_risk_levels_are_valid(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 13 (Extended): Risk Levels Are Valid
    
    For any fix recommendation, all risk levels should be one of: none, low, medium, high.
    
    Validates: Requirements 4.3, 4.4, 4.5
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name=service_name
    )
    
    # Assert
    immediate_actions = result["recommendations"]["immediate_actions"]
    valid_risk_levels = ["none", "low", "medium", "high"]
    
    # Property: All risk levels must be valid
    for action in immediate_actions:
        risk_level = action.get("risk_level", "")
        assert risk_level in valid_risk_levels, (
            f"Risk level must be one of {valid_risk_levels}, got '{risk_level}' "
            f"for action: {action.get('action')}"
        )
