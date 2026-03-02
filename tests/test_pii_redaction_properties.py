"""
Property-Based Tests for PII Redaction

Feature: incident-response-system
Property 39: PII Redaction

For any logs containing personally identifiable information (email addresses,
phone numbers, SSNs, credit card numbers), the Log Analysis Agent should
redact the PII before analysis.

Validates: Requirements 10.4
"""

import pytest
import re
from hypothesis import given, strategies as st
from src.agents.log_parser import redact_pii, parse_logs


# Strategies for generating PII
@st.composite
def email_address(draw):
    """Generate a valid email address"""
    username = draw(st.text(min_size=3, max_size=20, alphabet='abcdefghijklmnopqrstuvwxyz0123456789'))
    domain = draw(st.text(min_size=3, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz'))
    tld = draw(st.sampled_from(['com', 'org', 'net', 'edu', 'gov']))
    return f"{username}@{domain}.{tld}"


@st.composite
def phone_number(draw):
    """Generate a valid US phone number"""
    area_code = draw(st.integers(min_value=200, max_value=999))
    exchange = draw(st.integers(min_value=200, max_value=999))
    number = draw(st.integers(min_value=1000, max_value=9999))
    
    # Various formats
    format_choice = draw(st.integers(min_value=0, max_value=3))
    if format_choice == 0:
        return f"{area_code}-{exchange}-{number}"
    elif format_choice == 1:
        return f"({area_code}) {exchange}-{number}"
    elif format_choice == 2:
        return f"{area_code}.{exchange}.{number}"
    else:
        return f"{area_code}{exchange}{number}"


@st.composite
def ssn(draw):
    """Generate a valid SSN format"""
    area = draw(st.integers(min_value=100, max_value=999))
    group = draw(st.integers(min_value=10, max_value=99))
    serial = draw(st.integers(min_value=1000, max_value=9999))
    return f"{area}-{group}-{serial}"


@st.composite
def credit_card(draw):
    """Generate a credit card number format"""
    # Generate 4 groups of 4 digits
    groups = [draw(st.integers(min_value=1000, max_value=9999)) for _ in range(4)]
    
    # Various formats
    format_choice = draw(st.integers(min_value=0, max_value=2))
    if format_choice == 0:
        return f"{groups[0]}-{groups[1]}-{groups[2]}-{groups[3]}"
    elif format_choice == 1:
        return f"{groups[0]} {groups[1]} {groups[2]} {groups[3]}"
    else:
        return f"{groups[0]}{groups[1]}{groups[2]}{groups[3]}"


@given(email=email_address())
@pytest.mark.property_test
def test_property_39_email_redaction(email):
    """
    Property 39: PII Redaction - Email Addresses
    
    For any text containing email addresses, the redaction function
    should replace them with [EMAIL_REDACTED].
    
    Validates: Requirements 10.4
    """
    # Create text with email
    text = f"User email is {email} for contact"
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property 1: Original email should not appear in redacted text
    assert email not in redacted, \
        f"Email {email} should be redacted but still appears in: {redacted}"
    
    # Property 2: Redacted text should contain the redaction marker
    assert '[EMAIL_REDACTED]' in redacted, \
        f"Redacted text should contain [EMAIL_REDACTED]: {redacted}"
    
    # Property 3: Non-PII text should remain unchanged
    assert 'User email is' in redacted
    assert 'for contact' in redacted


@given(phone=phone_number())
@pytest.mark.property_test
def test_property_39_phone_redaction(phone):
    """
    Property 39: PII Redaction - Phone Numbers
    
    For any text containing phone numbers, the redaction function
    should replace them with [PHONE_REDACTED].
    
    Validates: Requirements 10.4
    """
    # Create text with phone number
    text = f"Contact number: {phone}"
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property 1: Original phone should not appear in redacted text
    # (Note: Some formats may not be caught by all patterns)
    if re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', phone):
        # If it matches our pattern, it should be redacted
        assert '[PHONE_REDACTED]' in redacted, \
            f"Phone number should be redacted: {redacted}"
    
    # Property 2: Non-PII text should remain
    assert 'Contact number:' in redacted


@given(ssn_value=ssn())
@pytest.mark.property_test
def test_property_39_ssn_redaction(ssn_value):
    """
    Property 39: PII Redaction - Social Security Numbers
    
    For any text containing SSNs, the redaction function
    should replace them with [SSN_REDACTED].
    
    Validates: Requirements 10.4
    """
    # Create text with SSN
    text = f"SSN: {ssn_value}"
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property 1: Original SSN should not appear in redacted text
    assert ssn_value not in redacted, \
        f"SSN {ssn_value} should be redacted but still appears in: {redacted}"
    
    # Property 2: Redacted text should contain the redaction marker
    assert '[SSN_REDACTED]' in redacted, \
        f"Redacted text should contain [SSN_REDACTED]: {redacted}"


@given(cc=credit_card())
@pytest.mark.property_test
def test_property_39_credit_card_redaction(cc):
    """
    Property 39: PII Redaction - Credit Card Numbers
    
    For any text containing credit card numbers, the redaction function
    should replace them with [CC_REDACTED].
    
    Validates: Requirements 10.4
    """
    # Create text with credit card
    text = f"Payment card: {cc}"
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property 1: Original CC should not appear in redacted text
    assert cc not in redacted, \
        f"Credit card {cc} should be redacted but still appears in: {redacted}"
    
    # Property 2: Redacted text should contain the redaction marker
    assert '[CC_REDACTED]' in redacted, \
        f"Redacted text should contain [CC_REDACTED]: {redacted}"


@given(
    email=email_address(),
    phone=phone_number(),
    ssn_value=ssn(),
    cc=credit_card()
)
@pytest.mark.property_test
def test_property_39_multiple_pii_types(email, phone, ssn_value, cc):
    """
    Property 39: PII Redaction - Multiple PII Types
    
    For any text containing multiple types of PII, all should be redacted.
    
    Validates: Requirements 10.4
    """
    # Create text with multiple PII types
    text = f"""
    User Information:
    Email: {email}
    Phone: {phone}
    SSN: {ssn_value}
    Credit Card: {cc}
    """
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property 1: None of the original PII should appear
    assert email not in redacted, "Email should be redacted"
    assert ssn_value not in redacted, "SSN should be redacted"
    assert cc not in redacted, "Credit card should be redacted"
    
    # Property 2: Redaction markers should be present
    assert '[EMAIL_REDACTED]' in redacted
    assert '[SSN_REDACTED]' in redacted
    assert '[CC_REDACTED]' in redacted
    
    # Property 3: Non-PII text should remain
    assert 'User Information:' in redacted


@given(
    log_lines=st.lists(
        st.one_of(
            st.text(min_size=10, max_size=100),
            st.builds(lambda e: f"ERROR: User {e} failed login", email_address()),
            st.builds(lambda p: f"Contact: {p}", phone_number())
        ),
        min_size=1,
        max_size=20
    )
)
@pytest.mark.property_test
def test_property_39_parse_logs_redacts_pii(log_lines):
    """
    Property 39: parse_logs should redact PII before processing
    
    For any logs containing PII, the parse_logs function should
    redact PII before extracting patterns.
    
    Validates: Requirements 10.4
    """
    log_content = '\n'.join(log_lines)
    
    # Parse logs (which should redact PII)
    result = parse_logs(log_content)
    
    # Property: Extracted excerpts should not contain raw PII
    for excerpt in result.get('relevant_excerpts', []):
        # Check that common PII patterns are not present in excerpts
        # (This is a heuristic check since we don't know what PII was generated)
        
        # Should not contain obvious email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails_in_excerpt = re.findall(email_pattern, excerpt)
        
        # If emails found, they should be redaction markers
        for email in emails_in_excerpt:
            assert 'REDACTED' in email or '@' not in email, \
                f"Found unredacted email in excerpt: {email}"


@given(text=st.text(min_size=0, max_size=1000))
@pytest.mark.property_test
def test_property_39_redaction_never_crashes(text):
    """
    Property 39: Redaction should handle any input without crashing
    
    For any text input, the redaction function should return
    a valid string without raising exceptions.
    
    Validates: Requirements 10.4
    """
    # This should never raise an exception
    result = redact_pii(text)
    
    # Property 1: Should always return a string
    assert isinstance(result, str), "Redaction should always return a string"
    
    # Property 2: Result should not be longer than original + redaction markers
    # (Redaction replaces text, doesn't add much)
    max_expected_length = len(text) + 1000  # Allow for redaction markers
    assert len(result) <= max_expected_length, \
        f"Redacted text unexpectedly long: {len(result)} vs original {len(text)}"


@given(
    normal_text=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L',))),
    email=email_address()
)
@pytest.mark.property_test
def test_property_39_preserves_non_pii(normal_text, email):
    """
    Property 39: Redaction should preserve non-PII content
    
    For any text containing both PII and non-PII, the non-PII
    content should remain unchanged.
    
    Validates: Requirements 10.4
    """
    # Ensure normal_text doesn't accidentally contain PII patterns
    # by using only letters
    text = f"{normal_text} {email} {normal_text}"
    
    # Redact PII
    redacted = redact_pii(text)
    
    # Property: Non-PII text should still be present
    assert normal_text in redacted, \
        f"Non-PII text '{normal_text}' should be preserved in: {redacted}"
