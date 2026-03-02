"""
Property-Based Tests for Low Confidence Warning

This module tests Property 27: Low Confidence Warning

Property 27: Low Confidence Warning
For any alert with a confidence score below 50, the alert should include a
warning that manual investigation is recommended.

Validates: Requirements 7.4
"""

from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
import pytest

from src.alerts.email_formatter import format_html_email, format_text_email
from src.alerts.email_templates import format_confidence_warning


# Strategy for generating enhanced alerts with specific confidence scores
@st.composite
def enhanced_alert_with_confidence(draw, confidence_score):
    """Generate enhanced alert with specific confidence score."""
    incident_id = draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    service_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    
    return {
        'incident_id': f"inc-{incident_id}",
        'timestamp': datetime.now().isoformat(),
        'original_alert': {
            'service_name': service_name,
            'error_message': draw(st.text(min_size=10, max_size=100))
        },
        'root_cause': {
            'category': draw(st.sampled_from(['configuration_error', 'resource_exhaustion', 'dependency_failure'])),
            'description': draw(st.text(min_size=20, max_size=200)),
            'evidence': draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5))
        },
        'confidence_score': confidence_score,
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


@given(
    confidence_score=st.integers(min_value=0, max_value=49),
    alert_data=st.data()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_low_confidence_warning_present(confidence_score, alert_data):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Present)
    
    For any alert with confidence score < 50, the alert should include a
    warning about low confidence.
    
    Validates: Requirements 7.4
    """
    enhanced_alert = alert_data.draw(enhanced_alert_with_confidence(confidence_score))
    
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: HTML must contain low confidence warning
    assert 'warning' in html_content.lower(), (
        f"HTML alert with confidence {confidence_score} should contain warning"
    )
    assert 'low confidence' in html_content.lower() or 'below 50' in html_content.lower(), (
        f"HTML alert with confidence {confidence_score} should mention low confidence"
    )
    
    # Property: Text must contain low confidence warning
    assert 'WARNING' in text_content or 'warning' in text_content.lower(), (
        f"Text alert with confidence {confidence_score} should contain warning"
    )
    assert 'low confidence' in text_content.lower() or 'below 50' in text_content.lower(), (
        f"Text alert with confidence {confidence_score} should mention low confidence"
    )


@given(
    confidence_score=st.integers(min_value=50, max_value=100),
    alert_data=st.data()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_high_confidence_no_warning(confidence_score, alert_data):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Absent for High Confidence)
    
    For any alert with confidence score >= 50, the alert should NOT include
    a low confidence warning.
    
    Validates: Requirements 7.4
    """
    enhanced_alert = alert_data.draw(enhanced_alert_with_confidence(confidence_score))
    
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: HTML should NOT contain low confidence warning
    # (It's okay to have the word "warning" in other contexts, but not "low confidence warning")
    if 'warning' in html_content.lower():
        assert 'low confidence' not in html_content.lower(), (
            f"HTML alert with confidence {confidence_score} should not have low confidence warning"
        )


@given(confidence_score=st.integers(min_value=0, max_value=49))
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_warning_template_function(confidence_score):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Template Function)
    
    The format_confidence_warning function should return warnings for
    confidence scores < 50.
    
    Validates: Requirements 7.4
    """
    warnings = format_confidence_warning(confidence_score)
    
    # Property: Should return dict with html and text keys
    assert isinstance(warnings, dict)
    assert 'html' in warnings
    assert 'text' in warnings
    
    # Property: Both HTML and text warnings should be non-empty
    assert len(warnings['html']) > 0, (
        f"HTML warning should be non-empty for confidence {confidence_score}"
    )
    assert len(warnings['text']) > 0, (
        f"Text warning should be non-empty for confidence {confidence_score}"
    )
    
    # Property: Warnings should mention low confidence or verification
    assert 'confidence' in warnings['html'].lower() or 'verify' in warnings['html'].lower()
    assert 'confidence' in warnings['text'].lower() or 'verify' in warnings['text'].lower()


@given(confidence_score=st.integers(min_value=50, max_value=100))
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_no_warning_template_function(confidence_score):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (No Warning for High Confidence)
    
    The format_confidence_warning function should return empty warnings for
    confidence scores >= 50.
    
    Validates: Requirements 7.4
    """
    warnings = format_confidence_warning(confidence_score)
    
    # Property: Should return dict with html and text keys
    assert isinstance(warnings, dict)
    assert 'html' in warnings
    assert 'text' in warnings
    
    # Property: Both HTML and text warnings should be empty
    assert len(warnings['html']) == 0, (
        f"HTML warning should be empty for confidence {confidence_score}"
    )
    assert len(warnings['text']) == 0, (
        f"Text warning should be empty for confidence {confidence_score}"
    )


@given(
    confidence_score=st.integers(min_value=0, max_value=49),
    alert_data=st.data()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_warning_recommends_manual_investigation(confidence_score, alert_data):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Manual Investigation)
    
    For any alert with confidence score < 50, the warning should recommend
    manual investigation or verification.
    
    Validates: Requirements 7.4
    """
    enhanced_alert = alert_data.draw(enhanced_alert_with_confidence(confidence_score))
    
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: Warning should recommend manual action
    manual_keywords = ['verify', 'manual', 'investigation', 'review', 'check']
    
    html_lower = html_content.lower()
    text_lower = text_content.lower()
    
    # At least one manual action keyword should be present
    assert any(keyword in html_lower for keyword in manual_keywords), (
        f"HTML warning should recommend manual action for confidence {confidence_score}"
    )
    
    assert any(keyword in text_lower for keyword in manual_keywords), (
        f"Text warning should recommend manual action for confidence {confidence_score}"
    )


@given(
    confidence_score=st.integers(min_value=0, max_value=49),
    alert_data=st.data()
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_warning_mentions_threshold(confidence_score, alert_data):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Threshold Mention)
    
    For any alert with confidence score < 50, the warning should mention
    the 50% threshold or that confidence is low.
    
    Validates: Requirements 7.4
    """
    enhanced_alert = alert_data.draw(enhanced_alert_with_confidence(confidence_score))
    
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: Warning should mention threshold or low confidence
    threshold_keywords = ['50', 'below', 'low confidence', 'low']
    
    html_lower = html_content.lower()
    text_lower = text_content.lower()
    
    # At least one threshold keyword should be present
    assert any(keyword in html_lower for keyword in threshold_keywords), (
        f"HTML warning should mention threshold for confidence {confidence_score}"
    )
    
    assert any(keyword in text_lower for keyword in threshold_keywords), (
        f"Text warning should mention threshold for confidence {confidence_score}"
    )


@given(confidence_score=st.integers(min_value=0, max_value=100))
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_27_warning_threshold_boundary(confidence_score):
    """
    Feature: incident-response-system
    Property 27: Low Confidence Warning (Boundary Test)
    
    The warning should appear if and only if confidence < 50.
    Test the exact boundary at 49 and 50.
    
    Validates: Requirements 7.4
    """
    warnings = format_confidence_warning(confidence_score)
    
    if confidence_score < 50:
        # Property: Warning should be present
        assert len(warnings['html']) > 0
        assert len(warnings['text']) > 0
    else:
        # Property: Warning should be absent
        assert len(warnings['html']) == 0
        assert len(warnings['text']) == 0
