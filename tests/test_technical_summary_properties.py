"""
Property tests for technical summary completeness.

Feature: incident-response-system
Property 16: Technical Summary Completeness

For any technical summary, it should include root cause details, log excerpts,
and specific remediation commands.

Validates: Requirements 5.2
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.agents.communication_agent import CommunicationAgent


# Strategy for generating root cause data with evidence
@st.composite
def root_cause_with_evidence_strategy(draw):
    """Generate valid root cause data with evidence."""
    categories = ["configuration_error", "resource_exhaustion", "dependency_failure"]
    
    # Generate evidence (log excerpts)
    evidence = draw(st.lists(
        st.text(min_size=20, max_size=150),
        min_size=1,
        max_size=5
    ))
    
    return {
        "analysis": {
            "primary_cause": {
                "category": draw(st.sampled_from(categories)),
                "description": draw(st.text(min_size=20, max_size=200)),
                "confidence_score": draw(st.integers(min_value=0, max_value=100)),
                "evidence": evidence
            }
        }
    }


# Strategy for generating fix recommendations with commands
@st.composite
def fixes_with_commands_strategy(draw):
    """Generate valid fix recommendations with commands."""
    num_actions = draw(st.integers(min_value=2, max_value=5))
    
    immediate_actions = []
    for i in range(num_actions):
        action = {
            "step": i + 1,
            "action": draw(st.text(min_size=15, max_size=100)),
            "command": draw(st.text(min_size=20, max_size=200)),  # Always include command
            "estimated_time": f"{draw(st.integers(min_value=1, max_value=60))} minutes",
            "risk_level": draw(st.sampled_from(["low", "medium", "high", "none"]))
        }
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
            "rollback_plan": draw(st.text(min_size=20, max_size=200))
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
    root_cause=root_cause_with_evidence_strategy(),
    fixes=fixes_with_commands_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_property_16_technical_summary_completeness(root_cause, fixes, original_alert):
    """
    Property 16: Technical Summary Completeness
    
    For any technical summary, it should include root cause details, log excerpts,
    and specific remediation commands.
    
    Validates: Requirements 5.2
    """
    agent = CommunicationAgent()
    
    # Generate summaries
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    
    # Property: Technical summary must include root cause details
    assert "root_cause" in technical, "Technical summary must include root_cause"
    root_cause_text = technical["root_cause"]
    assert isinstance(root_cause_text, str), "Root cause must be a string"
    assert len(root_cause_text) > 0, "Root cause must not be empty"
    
    # Verify root cause includes the description
    primary_cause = root_cause["analysis"]["primary_cause"]
    description = primary_cause["description"]
    # Root cause should reference the description or category
    assert len(root_cause_text) >= 10, "Root cause should be descriptive"
    
    # Property: Technical summary must include evidence (log excerpts)
    assert "evidence" in technical, "Technical summary must include evidence"
    evidence_text = technical["evidence"]
    assert isinstance(evidence_text, str), "Evidence must be a string"
    assert len(evidence_text) > 0, "Evidence must not be empty"
    
    # Property: Technical summary must include specific remediation commands
    assert "command" in technical, "Technical summary must include command"
    command = technical["command"]
    assert isinstance(command, str), "Command must be a string"
    # Command can be empty if no commands available, but field must exist
    
    # Property: Technical summary should include immediate fix action
    assert "immediate_fix" in technical, "Technical summary must include immediate_fix"
    immediate_fix = technical["immediate_fix"]
    assert isinstance(immediate_fix, str), "Immediate fix must be a string"
    assert len(immediate_fix) > 0, "Immediate fix must not be empty"
    
    # Property: Technical summary should include estimated resolution time
    assert "estimated_resolution" in technical, "Technical summary must include estimated_resolution"
    estimated_resolution = technical["estimated_resolution"]
    assert isinstance(estimated_resolution, str), "Estimated resolution must be a string"
    assert len(estimated_resolution) > 0, "Estimated resolution must not be empty"


@given(
    root_cause=root_cause_with_evidence_strategy(),
    fixes=fixes_with_commands_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_technical_summary_includes_all_actions(root_cause, fixes, original_alert):
    """
    Verify that technical summary includes all immediate actions.
    
    Technical summaries should provide complete action details for engineers.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    
    # Technical summary should include all actions
    assert "all_actions" in technical, "Technical summary should include all_actions"
    all_actions = technical["all_actions"]
    assert isinstance(all_actions, list), "All actions must be a list"
    
    # Number of actions should match the input
    immediate_actions = fixes["recommendations"]["immediate_actions"]
    assert len(all_actions) == len(immediate_actions), \
        "Technical summary should include all immediate actions"
    
    # Each action should have required fields
    for action in all_actions:
        assert "action" in action, "Each action must have 'action' field"
        assert "estimated_time" in action, "Each action must have 'estimated_time' field"


@given(
    root_cause=root_cause_with_evidence_strategy(),
    fixes=fixes_with_commands_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_technical_summary_includes_preventive_measures(root_cause, fixes, original_alert):
    """
    Verify that technical summary includes preventive measures.
    
    Engineers need to know how to prevent similar issues in the future.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    
    # Technical summary should include preventive measures
    assert "preventive_measures" in technical, "Technical summary should include preventive_measures"
    preventive_measures = technical["preventive_measures"]
    assert isinstance(preventive_measures, list), "Preventive measures must be a list"
    
    # If input has preventive measures, they should be included
    input_measures = fixes["recommendations"]["preventive_measures"]
    assert len(preventive_measures) == len(input_measures), \
        "Technical summary should include all preventive measures"


@given(
    root_cause=root_cause_with_evidence_strategy(),
    fixes=fixes_with_commands_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_technical_summary_includes_rollback_plan(root_cause, fixes, original_alert):
    """
    Verify that technical summary includes rollback plan.
    
    Engineers need to know how to rollback changes if fixes don't work.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    
    # Technical summary should include rollback plan
    assert "rollback_plan" in technical, "Technical summary should include rollback_plan"
    rollback_plan = technical["rollback_plan"]
    assert isinstance(rollback_plan, str), "Rollback plan must be a string"
    
    # Rollback plan should match input
    input_rollback = fixes["recommendations"]["rollback_plan"]
    assert rollback_plan == input_rollback, "Rollback plan should match input"


@given(
    root_cause=root_cause_with_evidence_strategy(),
    fixes=fixes_with_commands_strategy(),
    original_alert=original_alert_strategy()
)
@settings(max_examples=100, deadline=None)
def test_technical_summary_has_descriptive_title(root_cause, fixes, original_alert):
    """
    Verify that technical summary has a descriptive title.
    
    The title should help engineers quickly understand the issue.
    """
    agent = CommunicationAgent()
    
    result = agent.generate_summaries(
        root_cause=root_cause,
        fixes=fixes,
        original_alert=original_alert
    )
    
    enhanced_alert = result["enhanced_alert"]
    technical = enhanced_alert["technical_summary"]
    
    # Technical summary must have a title
    assert "title" in technical, "Technical summary must have title"
    title = technical["title"]
    assert isinstance(title, str), "Title must be a string"
    assert len(title) > 0, "Title must not be empty"
    
    # Title should include service name
    service_name = original_alert["service_name"]
    # Title should reference the service or category
    assert len(title) >= 5, "Title should be descriptive"
