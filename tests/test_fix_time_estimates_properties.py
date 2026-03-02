"""
Property-Based Tests for Fix Time Estimates

Property 14: Fix Time Estimates
For any fix recommendation, each action step should include an estimated time to resolution.

Validates: Requirements 4.6
"""

import pytest
import re
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
        }
    }


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_14_all_actions_have_time_estimates(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 14: Fix Time Estimates
    
    For any fix recommendation, each action step should include an estimated time to resolution.
    
    Validates: Requirements 4.6
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
    
    # Property: Every action must have an estimated_time field
    for idx, action in enumerate(immediate_actions, start=1):
        assert "estimated_time" in action, (
            f"Action {idx} ('{action.get('action', 'unknown')}') must have 'estimated_time' field"
        )
        
        estimated_time = action["estimated_time"]
        
        # Property: estimated_time must be a non-empty string
        assert isinstance(estimated_time, str), (
            f"Action {idx} estimated_time must be a string, got {type(estimated_time)}"
        )
        assert len(estimated_time) > 0, (
            f"Action {idx} estimated_time must not be empty"
        )


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_14_time_estimates_have_valid_format(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 14 (Extended): Time Estimates Have Valid Format
    
    For any fix recommendation, time estimates should follow a recognizable format
    (e.g., "X minutes", "X seconds", "X hours").
    
    Validates: Requirements 4.6
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
    
    # Common time format patterns
    time_patterns = [
        r'\d+\s*(second|seconds|sec|s)',
        r'\d+\s*(minute|minutes|min|m)',
        r'\d+\s*(hour|hours|hr|h)',
        r'\d+-\d+\s*(minute|minutes|min)',  # Range like "5-10 minutes"
        r'<\s*\d+\s*(minute|minutes|min)',  # Less than like "< 5 minutes"
    ]
    
    combined_pattern = '|'.join(time_patterns)
    
    # Property: Time estimates should match common time format patterns
    for idx, action in enumerate(immediate_actions, start=1):
        estimated_time = action["estimated_time"].lower()
        
        # Check if it matches any common time pattern
        matches_pattern = re.search(combined_pattern, estimated_time, re.IGNORECASE)
        
        assert matches_pattern, (
            f"Action {idx} estimated_time '{action['estimated_time']}' should follow a recognizable time format "
            f"(e.g., 'X minutes', 'X seconds', 'X hours')"
        )


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_14_time_estimates_are_reasonable(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 14 (Extended): Time Estimates Are Reasonable
    
    For any fix recommendation, time estimates should be reasonable
    (not negative, not excessively large).
    
    Validates: Requirements 4.6
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
    
    # Property: Time estimates should contain positive numbers
    for idx, action in enumerate(immediate_actions, start=1):
        estimated_time = action["estimated_time"].lower()
        
        # Extract numbers from the time estimate
        numbers = re.findall(r'\d+', estimated_time)
        
        if numbers:
            # Check that all numbers are positive and reasonable
            for num_str in numbers:
                num = int(num_str)
                assert num > 0, (
                    f"Action {idx} time estimate contains non-positive number: {num}"
                )
                
                # Check for unreasonably large values (e.g., > 1000 minutes)
                if 'minute' in estimated_time or 'min' in estimated_time:
                    assert num <= 1000, (
                        f"Action {idx} time estimate seems unreasonably large: {num} minutes"
                    )
                elif 'hour' in estimated_time:
                    assert num <= 100, (
                        f"Action {idx} time estimate seems unreasonably large: {num} hours"
                    )


@given(
    category=st.sampled_from(["configuration_error", "resource_exhaustion", "dependency_failure"])
)
@settings(max_examples=50, deadline=None)
@pytest.mark.property_test
def test_property_14_time_estimates_consistent_across_invocations(category):
    """
    Feature: incident-response-system
    Property 14 (Extended): Time Estimates Consistent
    
    For the same root cause category, time estimates should be consistent
    across multiple invocations.
    
    Validates: Requirements 4.6
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
    
    # Act - invoke twice with same input
    result1 = agent.generate_recommendations(
        root_cause=root_cause,
        service_name="test-service"
    )
    
    result2 = agent.generate_recommendations(
        root_cause=root_cause,
        service_name="test-service"
    )
    
    # Assert
    actions1 = result1["recommendations"]["immediate_actions"]
    actions2 = result2["recommendations"]["immediate_actions"]
    
    # Property: Same input should produce same time estimates
    assert len(actions1) == len(actions2), "Same input should produce same number of actions"
    
    for idx, (action1, action2) in enumerate(zip(actions1, actions2), start=1):
        assert action1["estimated_time"] == action2["estimated_time"], (
            f"Action {idx} time estimates should be consistent across invocations. "
            f"Got '{action1['estimated_time']}' and '{action2['estimated_time']}'"
        )


@given(
    root_cause=root_cause_strategy(),
    service_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')))
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_14_total_resolution_time_calculable(root_cause, service_name):
    """
    Feature: incident-response-system
    Property 14 (Extended): Total Resolution Time Calculable
    
    For any fix recommendation, it should be possible to calculate a total
    estimated resolution time from individual action times.
    
    Validates: Requirements 4.6
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
    
    # Property: Should be able to extract numeric time values
    total_minutes = 0
    parseable_count = 0
    
    for action in immediate_actions:
        estimated_time = action["estimated_time"].lower()
        
        # Try to extract minutes
        if 'minute' in estimated_time or 'min' in estimated_time:
            numbers = re.findall(r'\d+', estimated_time)
            if numbers:
                total_minutes += int(numbers[0])
                parseable_count += 1
        elif 'hour' in estimated_time:
            numbers = re.findall(r'\d+', estimated_time)
            if numbers:
                total_minutes += int(numbers[0]) * 60
                parseable_count += 1
        elif 'second' in estimated_time or 'sec' in estimated_time:
            numbers = re.findall(r'\d+', estimated_time)
            if numbers:
                total_minutes += int(numbers[0]) / 60
                parseable_count += 1
    
    # Property: At least some time estimates should be parseable
    assert parseable_count > 0, (
        "At least some time estimates should be in a parseable format to calculate total time"
    )
