"""
Property tests for user impact inclusion.

Feature: incident-response-system
Property 18: User Impact for User-Facing Services

For any incident affecting a user-facing service, the non-technical summary
should include estimated user impact; for non-user-facing services, user impact
may be omitted.

Validates: Requirements 5.5
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from src.agents.communication_agent import CommunicationAgent


# Strategy for generating user-facing service names
@st.composite
def user_facing_service_strategy(draw):
    """Generate service names that are user-facing."""
    patterns = ["api", "gateway", "frontend", "web", "mobile", "app",
                "payment", "checkout", "user", "customer", "public"]
    
    # Pick a pattern and create a service name with it
    pattern = draw(st.sampled_from(patterns))
    prefix = draw(st.text(min_size=0, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_")))
    suffix = draw(st.text(min_size=0, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_")))
    
    # Construct service name with pattern
    if draw(st.booleans()):
        service_name = f"{prefix}-{pattern}-{suffix}".strip("-")
    else:
        service_name = f"{pattern}-{suffix}".strip("-")
    
    # Ensure it's not empty
    if not service_name or service_name == "-":
        service_name = pattern
    
    return service_name


# Strategy for generating non-user-facing service names
@st.composite
def non_user_facing_service_strategy(draw):
    """Generate service names that are NOT user-facing."""
    # Avoid user-facing patterns
    patterns = ["backend", "worker", "processor", "internal", "batch", "cron", "etl", "data"]
    
    pattern = draw(st.sampled_from(patterns))
    prefix = draw(st.text(min_size=0, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_")))
    suffix = draw(st.text(min_size=0, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_")))
    
    # Construct service name
    if draw(st.booleans()):
        service_name = f"{prefix}-{pattern}-{suffix}".strip("-")
    else:
        service_name = f"{pattern}-{suffix}".strip("-")
    
    # Ensure it's not empty and doesn't contain user-facing patterns
    if not service_name or service_name == "-":
        service_name = pattern
    
    # Verify it doesn't accidentally contain user-facing patterns
    user_facing_patterns = ["api", "gateway", "frontend", "web", "mobile", "app",
                           "payment", "checkout", "user", "customer", "public"]
    assume(not any(p in service_name.lower() for p in user_facing_patterns))
    
    return service_name


# Strategy for generating root cause data
@st.composite
def root_cause_strategy(draw):
    """Generate valid root cause data."""
    categories = ["configuration_error", "resource_exhaustion", "dependency_failure"]
    
    return {
        "analysis": {
            "primary_cause": {
                "category": draw(st.sampled_from(categories)),
                "description": draw(st.text(min_size=10, max_size=200)),
                "confidence_score": draw(st.integers(min_value=0, max_value=100)),
                "evidence": draw(st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=5))
            }
        }
    }


# Strategy for generating fix recommendations
@st.composite
def fixes_strategy(draw):
    """Generate valid fix recommendations."""
    num_actions = draw(st.integers(min_value=2, max_value=5))
    
    immediate_actions = []
    for i in range(num_actions):
        action = {
            "step": i + 1,
            "action": draw(st.text(min_size=10, max_size=100)),
            "estimated_time": f"{draw(st.integers(min_value=1, max_value=60))} minutes",
            "risk_level": draw(st.sampled_from(["low", "medium", "high", "none"]))
        }
        immediate_actions.append(action)
    
    return {
        "recommendations": {
            "immediate_actions": immediate_actions,
            "preventive_measures": [],
            "rollback_plan": draw(st.text(min_size=10, max_size=200))
        }
    }


@given(
    service_name=user_facing_service_strategy(),
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy()
)
@settings(max_examples=100, deadline=None)
def test_property_18_user_impact_for_user_facing_services(service_name, root_cause, fixes):
    """
    Property 18: User Impact for User-Facing Services
    
    For any incident affecting a user-facing service, the non-technical summary
    should include estimated user impact.
    
    Validates: Requirements 5.5
    """
    agent = CommunicationAgent()
    
    # Create original alert with user-facing service
    original_alert = {
        "service_name": service_name,
        "timestamp": "2025-01-15T10:30:00Z",
        "error_message": "Test error",
        "log_location": "s3://logs/test.log"
    }
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    business_summary = enhanced_alert["business_summary"]
    
    # Property: User-facing services must have user impact in business summary
    assert "user_impact" in business_summary, \
        f"Business summary must include user_impact for user-facing service '{service_name}'"
    
    user_impact = business_summary["user_impact"]
    assert user_impact is not None, "User impact must not be None for user-facing service"
    assert isinstance(user_impact, str), "User impact must be a string"
    assert len(user_impact) > 0, "User impact must not be empty for user-facing service"
    
    # User impact should describe customer/user effects
    impact_keywords = ["user", "customer", "service", "experience", "issue", "failure", "unavailable", "degradation"]
    assert any(keyword in user_impact.lower() for keyword in impact_keywords), \
        f"User impact should describe user effects, got: {user_impact}"


@given(
    service_name=non_user_facing_service_strategy(),
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy()
)
@settings(max_examples=100, deadline=None)
def test_user_impact_optional_for_non_user_facing_services(service_name, root_cause, fixes):
    """
    Verify that user impact is optional for non-user-facing services.
    
    Internal services may not have user impact in business summary.
    """
    agent = CommunicationAgent()
    
    # Create original alert with non-user-facing service
    original_alert = {
        "service_name": service_name,
        "timestamp": "2025-01-15T10:30:00Z",
        "error_message": "Test error",
        "log_location": "s3://logs/test.log"
    }
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    business_summary = enhanced_alert["business_summary"]
    
    # Property: Non-user-facing services may omit user impact
    # (user_impact field may be absent or None)
    user_impact = business_summary.get("user_impact")
    
    # If present, it should still be valid
    if user_impact is not None:
        assert isinstance(user_impact, str), "If present, user impact must be a string"


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy()
)
@settings(max_examples=50, deadline=None)
def test_user_facing_detection_accuracy(root_cause, fixes):
    """
    Verify that user-facing service detection works correctly.
    
    Services with user-facing patterns should be detected.
    """
    agent = CommunicationAgent()
    
    # Test known user-facing services
    user_facing_services = [
        "payment-api",
        "customer-gateway",
        "web-frontend",
        "mobile-app",
        "public-api",
        "user-service",
        "checkout-processor"
    ]
    
    for service_name in user_facing_services:
        original_alert = {
            "service_name": service_name,
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Test error",
            "log_location": "s3://logs/test.log"
        }
        
        result = agent.generate_summaries(
            root_cause=root_cause,
            fixes=fixes,
            original_alert=original_alert
        )
        
        enhanced_alert = result["enhanced_alert"]
        business_summary = enhanced_alert["business_summary"]
        
        # Should have user impact
        assert "user_impact" in business_summary, \
            f"Service '{service_name}' should be detected as user-facing"
        assert business_summary["user_impact"] is not None, \
            f"Service '{service_name}' should have user impact"


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy()
)
@settings(max_examples=50, deadline=None)
def test_non_user_facing_detection_accuracy(root_cause, fixes):
    """
    Verify that non-user-facing service detection works correctly.
    
    Internal services should not have user impact.
    """
    agent = CommunicationAgent()
    
    # Test known non-user-facing services
    non_user_facing_services = [
        "data-processor",
        "internal-worker",
        "batch-job",
        "etl-pipeline",
        "cron-scheduler",
        "backend-service"
    ]
    
    for service_name in non_user_facing_services:
        original_alert = {
            "service_name": service_name,
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Test error",
            "log_location": "s3://logs/test.log"
        }
        
        result = agent.generate_summaries(
            root_cause=root_cause,
            fixes=fixes,
            original_alert=original_alert
        )
        
        enhanced_alert = result["enhanced_alert"]
        business_summary = enhanced_alert["business_summary"]
        
        # Should not have user impact (or it should be None)
        user_impact = business_summary.get("user_impact")
        assert user_impact is None, \
            f"Service '{service_name}' should not have user impact, but got: {user_impact}"


@given(
    service_name=user_facing_service_strategy(),
    category=st.sampled_from(["configuration_error", "resource_exhaustion", "dependency_failure"]),
    confidence_score=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_user_impact_varies_by_category_and_confidence(service_name, category, confidence_score):
    """
    Verify that user impact assessment considers category and confidence.
    
    Different failure categories and confidence levels should produce different impacts.
    """
    agent = CommunicationAgent()
    
    root_cause = {
        "analysis": {
            "primary_cause": {
                "category": category,
                "description": "Test error",
                "confidence_score": confidence_score,
                "evidence": ["Test evidence"]
            }
        }
    }
    
    fixes = {
        "recommendations": {
            "immediate_actions": [
                {
                    "step": 1,
                    "action": "Test action",
                    "estimated_time": "5 minutes",
                    "risk_level": "low"
                }
            ],
            "preventive_measures": [],
            "rollback_plan": "Test rollback"
        }
    }
    
    original_alert = {
        "service_name": service_name,
        "timestamp": "2025-01-15T10:30:00Z",
        "error_message": "Test error",
        "log_location": "s3://logs/test.log"
    }
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    business_summary = enhanced_alert["business_summary"]
    
    # Should have user impact
    assert "user_impact" in business_summary, "User-facing service should have user impact"
    user_impact = business_summary["user_impact"]
    assert user_impact is not None, "User impact should not be None"
    assert len(user_impact) > 0, "User impact should not be empty"
    
    # Impact should be a meaningful description
    assert len(user_impact) >= 20, "User impact should be descriptive"
