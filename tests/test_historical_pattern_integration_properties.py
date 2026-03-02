#!/usr/bin/env python3
"""Property 10: Historical Pattern Integration - Validates: Requirements 3.6"""
import pytest
from hypothesis import given, strategies as st
from src.agents.root_cause_classifier import FailureCategory, calculate_confidence_score

@given(
    error_message=st.text(min_size=10, max_size=100),
    category=st.sampled_from(list(FailureCategory))
)
def test_historical_pattern_integration_increases_confidence(error_message, category):
    """Historical data should increase or maintain confidence."""
    log_summary = {"error_patterns": [{"pattern": "Error", "occurrences": 5}], "stack_traces": [], "relevant_excerpts": []}
    
    confidence_without = calculate_confidence_score(category, error_message, log_summary, None)
    
    similar_incidents = [{
        "incident_id": "inc-001",
        "similarity_score": 0.8,
        "failure_type": category.value,
        "root_cause": {"category": category.value},
        "resolution": "Fixed"
    }]
    
    confidence_with = calculate_confidence_score(category, error_message, log_summary, similar_incidents)
    
    assert confidence_with >= confidence_without, f"With history: {confidence_with}, Without: {confidence_without}"
