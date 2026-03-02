"""
Property-Based Tests for Alert Content Completeness

This module tests Property 25: Alert Content Completeness

Property 25: Alert Content Completeness
For any sent alert, it should include both the original alert information and
the AI-generated analysis (root cause, fixes, confidence score).

Validates: Requirements 7.2
"""

from datetime import datetime
from hypothesis import given, strategies as st, settings
import pytest

from src.alerts.email_formatter import format_html_email, format_text_email, format_email


# Strategy for generating enhanced alerts
@st.composite
def enhanced_alert_strategy(draw):
    """Generate valid enhanced alert dictionaries."""
    incident_id = draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    service_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    error_message = draw(st.text(min_size=10, max_size=100))
    
    return {
        'incident_id': f"inc-{incident_id}",
        'timestamp': datetime.now().isoformat(),
        'original_alert': {
            'service_name': service_name,
            'error_message': error_message,
            'timestamp': datetime.now().isoformat(),
            'log_location': f"s3://logs/{service_name}/2025-01-15.log"
        },
        'root_cause': {
            'category': draw(st.sampled_from(['configuration_error', 'resource_exhaustion', 'dependency_failure'])),
            'description': draw(st.text(min_size=20, max_size=200)),
            'evidence': draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        },
        'confidence_score': draw(st.integers(min_value=0, max_value=100)),
        'recommended_fixes': draw(st.lists(
            st.fixed_dictionaries({
                'step': st.integers(min_value=1, max_value=5),
                'action': st.text(min_size=10, max_size=100),
                'command': st.text(min_size=10, max_size=200),
                'estimated_time': st.text(min_size=5, max_size=20),
                'risk_level': st.sampled_from(['none', 'low', 'medium', 'high'])
            }),
            min_size=2,
            max_size=5
        )),
        'business_summary': {
            'impact': draw(st.text(min_size=20, max_size=200)),
            'estimated_resolution': draw(st.text(min_size=5, max_size=20))
        }
    }


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_html_alert_content_completeness(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (HTML)
    
    For any sent alert, the HTML version should include both original alert
    information and AI-generated analysis.
    
    Validates: Requirements 7.2
    """
    html_content = format_html_email(enhanced_alert)
    
    # Property: HTML must include original alert information
    assert enhanced_alert['incident_id'] in html_content
    assert enhanced_alert['original_alert']['service_name'] in html_content
    
    # Property: HTML must include AI-generated root cause
    assert enhanced_alert['root_cause']['category'] in html_content
    assert enhanced_alert['root_cause']['description'] in html_content
    
    # Property: HTML must include confidence score
    assert str(enhanced_alert['confidence_score']) in html_content
    
    # Property: HTML must include at least one evidence item
    for evidence in enhanced_alert['root_cause']['evidence']:
        assert evidence in html_content
    
    # Property: HTML must include recommended fixes
    for fix in enhanced_alert['recommended_fixes']:
        assert fix['action'] in html_content
    
    # Property: HTML must include business summary
    assert enhanced_alert['business_summary']['impact'] in html_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_text_alert_content_completeness(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (Text)
    
    For any sent alert, the plain text version should include both original
    alert information and AI-generated analysis.
    
    Validates: Requirements 7.2
    """
    text_content = format_text_email(enhanced_alert)
    
    # Property: Text must include original alert information
    assert enhanced_alert['incident_id'] in text_content
    assert enhanced_alert['original_alert']['service_name'] in text_content
    
    # Property: Text must include AI-generated root cause
    assert enhanced_alert['root_cause']['category'] in text_content
    assert enhanced_alert['root_cause']['description'] in text_content
    
    # Property: Text must include confidence score
    assert str(enhanced_alert['confidence_score']) in text_content
    
    # Property: Text must include at least one evidence item
    for evidence in enhanced_alert['root_cause']['evidence']:
        assert evidence in text_content
    
    # Property: Text must include recommended fixes
    for fix in enhanced_alert['recommended_fixes']:
        assert fix['action'] in text_content
    
    # Property: Text must include business summary
    assert enhanced_alert['business_summary']['impact'] in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_both_formats_content_completeness(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (Both Formats)
    
    For any sent alert, both HTML and text versions should contain the same
    essential information.
    
    Validates: Requirements 7.2
    """
    html_content, text_content = format_email(enhanced_alert)
    
    # Property: Both formats must include incident ID
    assert enhanced_alert['incident_id'] in html_content
    assert enhanced_alert['incident_id'] in text_content
    
    # Property: Both formats must include service name
    service_name = enhanced_alert['original_alert']['service_name']
    assert service_name in html_content
    assert service_name in text_content
    
    # Property: Both formats must include root cause category
    category = enhanced_alert['root_cause']['category']
    assert category in html_content
    assert category in text_content
    
    # Property: Both formats must include confidence score
    confidence = str(enhanced_alert['confidence_score'])
    assert confidence in html_content
    assert confidence in text_content
    
    # Property: Both formats must include fix actions
    for fix in enhanced_alert['recommended_fixes']:
        assert fix['action'] in html_content
        assert fix['action'] in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_all_fix_commands_included(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (Commands)
    
    For any sent alert with fix recommendations, all commands should be
    included in the formatted output.
    
    Validates: Requirements 7.2
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: All commands from fixes must be present in both formats
    for fix in enhanced_alert['recommended_fixes']:
        if 'command' in fix and fix['command']:
            # Commands should be in HTML
            assert fix['command'] in html_content, (
                f"Command '{fix['command']}' missing from HTML content"
            )
            
            # Commands should be in text
            assert fix['command'] in text_content, (
                f"Command '{fix['command']}' missing from text content"
            )


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_all_evidence_included(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (Evidence)
    
    For any sent alert with evidence, all evidence items should be included
    in the formatted output.
    
    Validates: Requirements 7.2
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: All evidence items must be present in both formats
    for evidence_item in enhanced_alert['root_cause']['evidence']:
        assert evidence_item in html_content, (
            f"Evidence '{evidence_item}' missing from HTML content"
        )
        
        assert evidence_item in text_content, (
            f"Evidence '{evidence_item}' missing from text content"
        )


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_25_timestamp_included(enhanced_alert):
    """
    Feature: incident-response-system
    Property 25: Alert Content Completeness (Timestamp)
    
    For any sent alert, the timestamp should be included in the formatted output.
    
    Validates: Requirements 7.2
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: Timestamp must be present in both formats
    timestamp = enhanced_alert['timestamp']
    
    assert timestamp in html_content, "Timestamp missing from HTML content"
    assert timestamp in text_content, "Timestamp missing from text content"
