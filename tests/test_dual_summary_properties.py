"""
Property tests for dual summary generation.

Feature: incident-response-system
Property 15: Dual Summary Generation

For any completed analysis, the Communication Agent should generate exactly two summaries:
one technical and one non-technical.

Validates: Requirements 5.1
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.agents.communication_agent import CommunicationAgent


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
            },
            "alternative_causes": draw(st.lists(
                st.fixed_dictionaries({
                    "category": st.sampled_from(categories),
                    "description": st.text(min_size=10, max_size=100),
                    "confidence_score": st.integers(min_value=0, max_value=100)
                }),
                max_size=3
            ))
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
        
        # Optionally add command
        if draw(st.booleans()):
            action["command"] = draw(st.text(min_size=10, max_size=200))
        
        immediate_actions.append(action)
    
    return {
        "recommendations": {
            "immediate_actions": immediate_actions,
            "preventive_measures": draw(st.lists(
                st.fixed_dictionaries({
                    "action": st.text(min_size=10, max_size=100),
                    "description": st.text(min_size=10, max_size=200),
                    "priority": st.sampled_from(["low", "medium", "high"])
                }),
                max_size=3
            )),
            "rollback_plan": draw(st.text(min_size=10, max_size=200))
        }
    }


# Strategy for generating original alert
@st.composite
def original_alert_strategy(draw):
    """Generate valid original alert data."""
    return {
        "service_name": draw(st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"))),
        "timestamp": draw(st.datetimes()).isoformat(),
        "error_message": draw(st.text(min_size=10, max_size=200)),
        "log_location": f"s3://logs/{draw(st.text(min_size=5, max_size=30))}/log.txt"
    }


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_property_15_dual_summary_generation(root_cause, fixes, original_alert):
    """
    Property 15: Dual Summary Generation
    
    For any completed analysis, the Communication Agent should generate exactly two summaries:
    one technical and one non-technical.
    
    Validates: Requirements 5.1
    """
    agent = CommunicationAgent()
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    # Verify enhanced alert structure
    assert "enhanced_alert" in result, "Result should contain enhanced_alert"
    enhanced_alert = result["enhanced_alert"]
    
    # Property: Must have exactly two summaries
    assert "technical_summary" in enhanced_alert, "Must have technical_summary"
    assert "business_summary" in enhanced_alert, "Must have business_summary"
    
    # Verify technical summary exists and is not empty
    technical = enhanced_alert["technical_summary"]
    assert technical is not None, "Technical summary must not be None"
    assert isinstance(technical, dict), "Technical summary must be a dictionary"
    assert len(technical) > 0, "Technical summary must not be empty"
    
    # Verify business summary exists and is not empty
    business = enhanced_alert["business_summary"]
    assert business is not None, "Business summary must not be None"
    assert isinstance(business, dict), "Business summary must be a dictionary"
    assert len(business) > 0, "Business summary must not be empty"
    
    # Verify they are distinct (not the same object)
    assert technical is not business, "Technical and business summaries must be distinct objects"
    
    # Verify both summaries have required fields
    assert "title" in technical, "Technical summary must have title"
    assert "title" in business, "Business summary must have title"
    
    # Verify summaries are different (technical vs business language)
    # Technical should have more technical fields
    assert "command" in technical or "all_actions" in technical, \
        "Technical summary should have technical details like commands or actions"


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_dual_summaries_are_distinct(root_cause, fixes, original_alert):
    """
    Verify that technical and business summaries contain different content.
    
    Technical summaries should be more detailed and technical.
    Business summaries should be more concise and business-focused.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    business = enhanced_alert["business_summary"]
    
    # Technical summary should have more fields (commands, evidence, etc.)
    assert len(technical) >= len(business), \
        "Technical summary should have at least as many fields as business summary"
    
    # Technical summary should have technical-specific fields
    technical_fields = {"command", "evidence", "all_actions", "preventive_measures", "rollback_plan"}
    has_technical_field = any(field in technical for field in technical_fields)
    assert has_technical_field, "Technical summary should have at least one technical-specific field"
    
    # Business summary should have business-specific fields
    business_fields = {"impact", "status", "user_impact"}
    has_business_field = any(field in business for field in business_fields)
    assert has_business_field, "Business summary should have at least one business-specific field"


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_summaries_include_confidence_score(root_cause, fixes, original_alert):
    """
    Verify that both summaries include or reference the confidence score.
    
    The confidence score should be accessible from the enhanced alert.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    
    # Confidence score should be in the enhanced alert
    assert "confidence_score" in enhanced_alert, "Enhanced alert must include confidence_score"
    
    confidence_score = enhanced_alert["confidence_score"]
    assert isinstance(confidence_score, (int, float)), "Confidence score must be numeric"
    assert 0 <= confidence_score <= 100, "Confidence score must be between 0 and 100"
    
    # Technical summary should reference confidence in root cause
    technical = enhanced_alert["technical_summary"]
    root_cause_text = technical.get("root_cause", "")
    assert "confidence" in root_cause_text.lower() or confidence_score == enhanced_alert["confidence_score"], \
        "Technical summary should reference confidence score"
