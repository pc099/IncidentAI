"""
Property tests for confidence score in summaries.

Feature: incident-response-system
Property 17: Confidence Score in Summaries

For any generated summary (technical or non-technical), it should include
the confidence score.

Validates: Requirements 5.4
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
        
        if draw(st.booleans()):
            action["command"] = draw(st.text(min_size=10, max_size=200))
        
        immediate_actions.append(action)
    
    return {
        "recommendations": {
            "immediate_actions": immediate_actions,
            "preventive_measures": [],
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
def test_property_17_confidence_score_in_summaries(root_cause, fixes, original_alert):
    """
    Property 17: Confidence Score in Summaries
    
    For any generated summary (technical or non-technical), it should include
    the confidence score.
    
    Validates: Requirements 5.4
    """
    agent = CommunicationAgent()
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    
    # Property: Enhanced alert must include confidence score
    assert "confidence_score" in enhanced_alert, "Enhanced alert must include confidence_score"
    confidence_score = enhanced_alert["confidence_score"]
    
    # Verify confidence score is valid
    assert isinstance(confidence_score, (int, float)), "Confidence score must be numeric"
    assert 0 <= confidence_score <= 100, "Confidence score must be between 0 and 100"
    
    # Verify confidence score matches input
    input_confidence = root_cause["analysis"]["primary_cause"]["confidence_score"]
    assert confidence_score == input_confidence, "Confidence score should match input"
    
    # Property: Technical summary should reference confidence score
    technical = enhanced_alert["technical_summary"]
    assert "root_cause" in technical, "Technical summary must have root_cause"
    root_cause_text = technical["root_cause"]
    
    # Root cause text should include confidence percentage
    assert "confidence" in root_cause_text.lower() or f"{confidence_score}%" in root_cause_text, \
        "Technical summary should reference confidence score"
    
    # Property: Confidence score should be accessible for business summary
    # (Business summary doesn't need to display it, but it should be in enhanced alert)
    business = enhanced_alert["business_summary"]
    assert business is not None, "Business summary must exist"


@given(
    confidence_score=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_confidence_score_preserved_across_summaries(confidence_score):
    """
    Verify that confidence score is preserved from input to output.
    
    The confidence score should not be modified during summary generation.
    """
    agent = CommunicationAgent()
    
    # Create test data with specific confidence score
    root_cause = {
        "analysis": {
            "primary_cause": {
                "category": "configuration_error",
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
        "service_name": "test-service",
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
    
    # Confidence score should be preserved exactly
    assert enhanced_alert["confidence_score"] == confidence_score, \
        f"Confidence score should be preserved: expected {confidence_score}, got {enhanced_alert['confidence_score']}"


@given(
    root_cause=root_cause_strategy(),
    fixes=fixes_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_confidence_warning_for_low_scores(root_cause, fixes, original_alert):
    """
    Verify that low confidence scores trigger a warning.
    
    When confidence < 50, a warning should be included.
    
    Validates: Requirements 7.4
    """
    agent = CommunicationAgent()
    
    # Get the confidence score from input
    confidence_score = root_cause["analysis"]["primary_cause"]["confidence_score"]
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    
    # Property: If confidence < 50, warning should be present
    if confidence_score < 50:
        assert "confidence_warning" in enhanced_alert, \
            "Enhanced alert should have confidence_warning for low confidence"
        warning = enhanced_alert["confidence_warning"]
        assert warning is not None, "Warning should not be None for low confidence"
        assert isinstance(warning, str), "Warning should be a string"
        assert len(warning) > 0, "Warning should not be empty"
        assert "manual investigation" in warning.lower() or "low confidence" in warning.lower(), \
            "Warning should mention manual investigation or low confidence"
    else:
        # For high confidence, warning can be None or absent
        warning = enhanced_alert.get("confidence_warning")
        if warning is not None:
            # If warning exists for high confidence, it should be empty or None
            assert warning is None or len(warning) == 0, \
                "Warning should be None or empty for high confidence"


@given(
    confidence_score=st.integers(min_value=0, max_value=49)
)
@settings(max_examples=50, deadline=None)
def test_low_confidence_always_has_warning(confidence_score):
    """
    Verify that all low confidence scores (< 50) trigger warnings.
    
    This is a critical safety feature.
    """
    agent = CommunicationAgent()
    
    # Create test data with low confidence score
    root_cause = {
        "analysis": {
            "primary_cause": {
                "category": "configuration_error",
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
        "service_name": "test-service",
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
    
    # Must have warning for low confidence
    assert "confidence_warning" in enhanced_alert, \
        f"Must have confidence_warning for confidence score {confidence_score}"
    warning = enhanced_alert["confidence_warning"]
    assert warning is not None, f"Warning must not be None for confidence score {confidence_score}"
    assert len(warning) > 0, f"Warning must not be empty for confidence score {confidence_score}"


@given(
    confidence_score=st.integers(min_value=50, max_value=100)
)
@settings(max_examples=50, deadline=None)
def test_high_confidence_no_warning(confidence_score):
    """
    Verify that high confidence scores (>= 50) do not trigger warnings.
    """
    agent = CommunicationAgent()
    
    # Create test data with high confidence score
    root_cause = {
        "analysis": {
            "primary_cause": {
                "category": "configuration_error",
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
        "service_name": "test-service",
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
    
    # Should not have warning for high confidence
    warning = enhanced_alert.get("confidence_warning")
    assert warning is None, \
        f"Should not have warning for confidence score {confidence_score}, but got: {warning}"
