"""
Property-Based Tests for Fix Recommendation Count

Property 12: Fix Recommendation Count
For any fix recommendation output, the number of immediate action steps should be between 2 and 5 (inclusive).

Validates: Requirements 4.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.agents.fix_recommendation_agent import FixRecommendationAgent


# Strategy for generating root cause analysis outputs
@st.composite
def root_cause_strategy(draw):
    """Generate valid root cause analysis outputs."""
    categories = ["configuration_error", "resource_exhaustion", "dependency_failure"]
    category = draw(st.sampled_from(categories))
    
    return {
        "primary_cause": {
            "category": category,
            "description": draw(st.text(min_size=10, max_size=200)),
            "confidence_score": draw(st.integers(min_value=0, max_value=100)),
            "evidence": draw(st.lists(st.text(min_size=5, max_size=100), min_size=1, max_size=5))
        },
        "alternative_causes": draw(st.lists(
            st.fixed_dictionaries({
                "category": st.sampled_from(categories),
                "description": st.text(min_size=10, max_size=200),
                "confidence_score": st.integers(min_value=0, max_value=100),
                "evidence": st.lists(st.text(min_size=5, max_size=100), min_size=0, max_size=3)
            }),
            min_size=0,
            max_size=3
        ))
    }


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_12_fix_recommendation_count(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 12: Fix Recommendation Count
    
    For any fix recommendation output, the number of immediate action steps 
    should be between 2 and 5 (inclusive).
    
    Validates: Requirements 4.2
    """
    # Arrange
    agent = FixRecommendationAgent()
    
    # Act
    result = agent.generate_recommendations(
        root_cause=root_cause,
        service_name=service_name
    )
    
    # Assert
    assert "recommendations" in result, "Result must contain recommendations"
    assert "immediate_actions" in result["recommendations"], "Recommendations must contain immediate_actions"
    
    immediate_actions = result["recommendations"]["immediate_actions"]
    action_count = len(immediate_actions)
    
    # Property: Action count must be between 2 and 5 (inclusive)
    assert 2 <= action_count <= 5, (
        f"Fix recommendations must have 2-5 immediate actions, got {action_count}. "
        f"Root cause category: {root_cause['primary_cause']['category']}"
    )


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_12_action_steps_numbered_sequentially(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 12 (Extended): Action Steps Numbered Sequentially
    
    For any fix recommendation output, the action steps should be numbered 
    sequentially starting from 1.
    
    Validates: Requirements 4.2
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
    
    # Property: Steps should be numbered 1, 2, 3, ...
    for idx, action in enumerate(immediate_actions, start=1):
        assert "step" in action, f"Action {idx} must have a 'step' field"
        assert action["step"] == idx, (
            f"Action step numbers must be sequential. Expected {idx}, got {action['step']}"
        )


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_12_all_actions_have_required_fields(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 12 (Extended): All Actions Have Required Fields
    
    For any fix recommendation output, each immediate action should have 
    all required fields: step, action, details, estimated_time, risk_level.
    
    Validates: Requirements 4.2
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
    
    required_fields = ["step", "action", "details", "estimated_time", "risk_level"]
    
    # Property: Each action must have all required fields
    for idx, action in enumerate(immediate_actions, start=1):
        for field in required_fields:
            assert field in action, (
                f"Action {idx} missing required field '{field}'. "
                f"Action: {action.get('action', 'unknown')}"
            )
        
        # Verify field types
        assert isinstance(action["step"], int), f"Step must be an integer, got {type(action['step'])}"
        assert isinstance(action["action"], str), f"Action must be a string, got {type(action['action'])}"
        assert isinstance(action["details"], str), f"Details must be a string, got {type(action['details'])}"
        assert isinstance(action["estimated_time"], str), f"Estimated time must be a string, got {type(action['estimated_time'])}"
        assert isinstance(action["risk_level"], str), f"Risk level must be a string, got {type(action['risk_level'])}"


@given(
    category=st.sampled_from(["configuration_error", "resource_exhaustion", "dependency_failure"])
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_12_consistent_count_for_same_category(category):
    """
    Feature: incident-response-system
    Property 12 (Extended): Consistent Count for Same Category
    
    For any root cause category, the fix recommendation count should be 
    consistent (between 2-5) regardless of other parameters.
    
    Validates: Requirements 4.2
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
    immediate_actions = result["recommendations"]["immediate_actions"]
    action_count = len(immediate_actions)
    
    # Property: Count must always be between 2 and 5
    assert 2 <= action_count <= 5, (
        f"Category {category} must produce 2-5 actions, got {action_count}"
    )
