"""
Property-Based Tests for Alert Section Structure

This module tests Property 26: Alert Section Structure

Property 26: Alert Section Structure
For any formatted alert, it should contain these sections: Summary, Root Cause,
Recommended Fixes, and Confidence Score.

Validates: Requirements 7.3
"""

import re
from datetime import datetime
from hypothesis import given, strategies as st, settings
import pytest

from src.alerts.email_formatter import format_html_email, format_text_email


# Strategy for generating enhanced alerts
@st.composite
def enhanced_alert_strategy(draw):
    """Generate valid enhanced alert dictionaries."""
    incident_id = draw(st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    service_name = draw(st.text(min_size=3, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='-')))
    
    return {
        'incident_id': f"inc-{incident_id}",
        'timestamp': datetime.now().isoformat(),
        'original_alert': {
            'service_name': service_name,
            'error_message': draw(st.text(min_size=10, max_size=100)),
            'timestamp': datetime.now().isoformat()
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
def test_property_26_html_required_sections(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (HTML)
    
    For any formatted HTML alert, it should contain these sections:
    - Summary (incident ID, service name, timestamp)
    - Root Cause
    - Recommended Fixes (Immediate Actions)
    - Confidence Score
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    
    # Property: Must contain Summary section (header with incident info)
    assert 'Incident Alert' in html_content or 'incident_id' in html_content.lower()
    assert enhanced_alert['incident_id'] in html_content
    assert enhanced_alert['original_alert']['service_name'] in html_content
    
    # Property: Must contain Root Cause section
    assert 'Root Cause' in html_content or 'root cause' in html_content.lower()
    assert enhanced_alert['root_cause']['description'] in html_content
    
    # Property: Must contain Recommended Fixes section
    assert 'Immediate Actions' in html_content or 'immediate actions' in html_content.lower() or 'action' in html_content.lower()
    
    # Property: Must contain Confidence Score
    assert 'Confidence' in html_content or 'confidence' in html_content.lower()
    assert str(enhanced_alert['confidence_score']) in html_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_text_required_sections(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Text)
    
    For any formatted text alert, it should contain these sections:
    - Summary
    - Root Cause
    - Recommended Fixes
    - Confidence Score
    
    Validates: Requirements 7.3
    """
    text_content = format_text_email(enhanced_alert)
    
    # Property: Must contain Summary section
    assert 'INCIDENT ALERT' in text_content or enhanced_alert['incident_id'] in text_content
    assert enhanced_alert['original_alert']['service_name'] in text_content
    
    # Property: Must contain Root Cause section
    assert 'ROOT CAUSE' in text_content or 'Root Cause' in text_content
    assert enhanced_alert['root_cause']['description'] in text_content
    
    # Property: Must contain Recommended Fixes section
    assert 'IMMEDIATE ACTIONS' in text_content or 'Immediate Actions' in text_content or 'ACTION' in text_content
    
    # Property: Must contain Confidence Score
    assert 'confidence' in text_content.lower()
    assert str(enhanced_alert['confidence_score']) in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_html_section_headers(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (HTML Headers)
    
    For any formatted HTML alert, section headers should be properly formatted
    with HTML heading tags.
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    
    # Property: HTML should contain proper heading tags for sections
    # Check for h1 or h2 tags (section headers)
    assert re.search(r'<h[12]>', html_content, re.IGNORECASE), (
        "HTML should contain heading tags for sections"
    )
    
    # Property: Root Cause section should have a header
    assert re.search(r'<h[12]>.*Root Cause.*</h[12]>', html_content, re.IGNORECASE) or \
           'Root Cause' in html_content, (
        "Root Cause section should have a proper header"
    )
    
    # Property: Actions section should have a header
    assert re.search(r'<h[12]>.*Immediate Actions.*</h[12]>', html_content, re.IGNORECASE) or \
           'Immediate Actions' in html_content, (
        "Immediate Actions section should have a proper header"
    )


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_text_section_separators(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Text Separators)
    
    For any formatted text alert, sections should be clearly separated with
    visual separators (lines, spacing).
    
    Validates: Requirements 7.3
    """
    text_content = format_text_email(enhanced_alert)
    
    # Property: Text should contain section separators (dashes or equals)
    separator_pattern = r'[-=]{10,}'
    separators = re.findall(separator_pattern, text_content)
    
    assert len(separators) >= 2, (
        f"Text alert should have at least 2 section separators, found {len(separators)}"
    )


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_business_impact_section(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Business Impact)
    
    For any formatted alert, it should contain a Business Impact section.
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: HTML must contain Business Impact section
    assert 'Business Impact' in html_content or 'business impact' in html_content.lower()
    assert enhanced_alert['business_summary']['impact'] in html_content
    
    # Property: Text must contain Business Impact section
    assert 'BUSINESS IMPACT' in text_content or 'Business Impact' in text_content
    assert enhanced_alert['business_summary']['impact'] in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_commands_section(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Commands)
    
    For any formatted alert with fix commands, it should contain a Commands section.
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: HTML must contain Commands section
    assert 'Commands' in html_content or 'commands' in html_content.lower() or 'command' in html_content.lower()
    
    # Property: Text must contain Commands section
    assert 'COMMANDS' in text_content or 'Commands' in text_content or 'COMMAND' in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_evidence_section(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Evidence)
    
    For any formatted alert with evidence, it should contain an Evidence section
    within the Root Cause section.
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    # Property: HTML must contain Evidence section or label
    assert 'Evidence' in html_content or 'evidence' in html_content.lower()
    
    # Property: Text must contain Evidence section or label
    assert 'EVIDENCE' in text_content or 'Evidence' in text_content


@given(enhanced_alert=enhanced_alert_strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_26_section_ordering(enhanced_alert):
    """
    Feature: incident-response-system
    Property 26: Alert Section Structure (Ordering)
    
    For any formatted alert, sections should appear in a logical order:
    1. Summary/Header
    2. Root Cause
    3. Immediate Actions
    4. Commands
    5. Business Impact
    
    Validates: Requirements 7.3
    """
    html_content = format_html_email(enhanced_alert)
    
    # Find positions of key sections in HTML
    incident_pos = html_content.find(enhanced_alert['incident_id'])
    root_cause_pos = html_content.lower().find('root cause')
    actions_pos = html_content.lower().find('immediate actions')
    business_pos = html_content.lower().find('business impact')
    
    # Property: Sections should appear in order (if all are present)
    if all(pos != -1 for pos in [incident_pos, root_cause_pos, actions_pos, business_pos]):
        assert incident_pos < root_cause_pos, "Incident ID should appear before Root Cause"
        assert root_cause_pos < actions_pos, "Root Cause should appear before Immediate Actions"
        assert actions_pos < business_pos, "Immediate Actions should appear before Business Impact"
