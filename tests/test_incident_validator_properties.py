"""
Property-based tests for incident validator Lambda function.

**Property 2: Alert Payload Validation**
**Validates: Requirements 1.3, 1.4, 1.5**

These tests use property-based testing to verify that the API validation
behaves correctly across a wide range of inputs, including edge cases.
"""

import json
from hypothesis import given, strategies as st
from src.api.incident_validator import (
    validate_payload,
    validate_required_fields,
    validate_timestamp,
    validate_service_name,
    validate_error_message,
    validate_log_location,
    extract_incident_context,
    lambda_handler
)


# Strategy for generating valid ISO 8601 timestamps
@st.composite
def iso8601_timestamp(draw):
    """Generate valid ISO 8601 timestamp strings."""
    year = draw(st.integers(min_value=2020, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    
    # Choose between Z and +00:00 timezone format
    tz_format = draw(st.sampled_from(['Z', '+00:00', '-05:00', '+08:00']))
    
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}{tz_format}"


# Strategy for generating valid S3 URIs
@st.composite
def s3_uri(draw):
    """Generate valid S3 URI strings."""
    bucket = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-'),
        min_size=3,
        max_size=20
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    path = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='/-_.'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x and '//' not in x))
    
    return f"s3://{bucket}/{path}"


# Strategy for generating valid payloads
@st.composite
def valid_payload(draw):
    """Generate valid incident alert payloads."""
    return {
        "service_name": draw(st.text(min_size=1, max_size=100).filter(lambda x: x.strip())),
        "timestamp": draw(iso8601_timestamp()),
        "error_message": draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip())),
        "log_location": draw(s3_uri()),
        "alert_source": draw(st.sampled_from(["CloudWatch", "EventBridge", "Manual"]))
    }


class TestProperty2_AlertPayloadValidation:
    """
    Property 2: Alert Payload Validation
    Validates: Requirements 1.3, 1.4, 1.5
    
    This property ensures that:
    1. Valid payloads with all required fields are accepted (Req 1.3)
    2. Invalid payloads return appropriate error messages (Req 1.4)
    3. Valid payloads allow extraction of incident context (Req 1.5)
    """
    
    @given(valid_payload())
    def test_valid_payloads_always_pass_validation(self, payload):
        """
        Property: Any payload with all required fields in correct format should validate successfully.
        Validates: Requirement 1.3 - validate alert payload structure
        """
        is_valid, error = validate_payload(payload)
        assert is_valid is True, f"Valid payload failed validation: {error}"
        assert error is None
    
    @given(valid_payload())
    def test_valid_payloads_return_202_accepted(self, payload):
        """
        Property: Any valid payload should result in 202 Accepted response.
        Validates: Requirement 1.3 - validate alert payload structure
        """
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps(payload)
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202, \
            f"Valid payload did not return 202: {response}"
        
        body = json.loads(response["body"])
        assert "incident_id" in body
        assert body["status"] == "processing"
    
    @given(valid_payload())
    def test_valid_payloads_allow_context_extraction(self, payload):
        """
        Property: Any valid payload should allow extraction of incident context.
        Validates: Requirement 1.5 - extract failure timestamp, service name, and error context
        """
        context = extract_incident_context(payload)
        
        # Verify all required fields are extracted
        assert context["service_name"] == payload["service_name"]
        assert context["timestamp"] == payload["timestamp"]
        assert context["error_message"] == payload["error_message"]
        assert context["log_location"] == payload["log_location"]
        
        # Verify alert_source is present (either from payload or default)
        assert "alert_source" in context
    
    @given(
        st.dictionaries(
            keys=st.sampled_from(["service_name", "timestamp", "error_message", "log_location"]),
            values=st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=3  # Missing at least one required field
        )
    )
    def test_missing_required_fields_always_fail(self, incomplete_payload):
        """
        Property: Any payload missing required fields should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        required_fields = {"service_name", "timestamp", "error_message", "log_location"}
        present_fields = set(incomplete_payload.keys())
        
        # Only test if at least one field is missing
        if present_fields != required_fields:
            is_valid, error = validate_required_fields(incomplete_payload)
            assert is_valid is False, \
                f"Incomplete payload passed validation: {incomplete_payload}"
            assert error is not None
            
            # Verify error message mentions missing fields
            missing = required_fields - present_fields
            for field in missing:
                assert field in error, \
                    f"Error message should mention missing field '{field}': {error}"
    
    @given(
        st.dictionaries(
            keys=st.sampled_from(["service_name", "timestamp", "error_message", "log_location"]),
            values=st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=3
        )
    )
    def test_incomplete_payloads_return_400(self, incomplete_payload):
        """
        Property: Any incomplete payload should return 400 Bad Request.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        required_fields = {"service_name", "timestamp", "error_message", "log_location"}
        
        # Only test if at least one field is missing
        if set(incomplete_payload.keys()) != required_fields:
            event = {
                "headers": {
                    "x-api-key": "test-api-key-12345678901234567890"
                },
                "requestContext": {
                    "identity": {}
                },
                "body": json.dumps(incomplete_payload)
            }
            response = lambda_handler(event, None)
            
            assert response["statusCode"] == 400, \
                f"Incomplete payload did not return 400: {response}"
            
            body = json.loads(response["body"])
            assert "error" in body
            assert "details" in body
    
    @given(
        st.text(min_size=1, max_size=100).filter(lambda x: 'T' not in x)
    )
    def test_invalid_timestamp_format_fails(self, invalid_timestamp):
        """
        Property: Any timestamp without 'T' separator should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_timestamp(invalid_timestamp)
        assert is_valid is False, \
            f"Invalid timestamp passed validation: {invalid_timestamp}"
        assert error is not None
        assert "ISO 8601" in error
    
    @given(
        st.one_of(
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
            st.none()
        )
    )
    def test_non_string_timestamps_fail(self, non_string_value):
        """
        Property: Any non-string timestamp value should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_timestamp(non_string_value)
        assert is_valid is False
        assert error is not None
        assert "must be a string" in error
    
    @given(st.text(max_size=0))
    def test_empty_service_name_fails(self, empty_or_whitespace):
        """
        Property: Empty or whitespace-only service names should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_service_name(empty_or_whitespace)
        assert is_valid is False
        assert error is not None
    
    @given(
        st.text(min_size=1, max_size=100).filter(lambda x: not x.startswith("s3://") and x.strip())
    )
    def test_non_s3_uri_fails(self, non_s3_uri):
        """
        Property: Any log_location not starting with 's3://' should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_log_location(non_s3_uri)
        assert is_valid is False
        assert error is not None
        assert "S3 URI" in error
    
    @given(
        st.one_of(
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
            st.none()
        )
    )
    def test_non_string_service_names_fail(self, non_string_value):
        """
        Property: Any non-string service_name value should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_service_name(non_string_value)
        assert is_valid is False
        assert error is not None
        assert "must be a string" in error
    
    @given(
        st.one_of(
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
            st.none()
        )
    )
    def test_non_string_error_messages_fail(self, non_string_value):
        """
        Property: Any non-string error_message value should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_error_message(non_string_value)
        assert is_valid is False
        assert error is not None
        assert "must be a string" in error
    
    @given(
        st.one_of(
            st.integers(),
            st.floats(),
            st.lists(st.text()),
            st.dictionaries(st.text(), st.text()),
            st.none()
        )
    )
    def test_non_string_log_locations_fail(self, non_string_value):
        """
        Property: Any non-string log_location value should fail validation.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        is_valid, error = validate_log_location(non_string_value)
        assert is_valid is False
        assert error is not None
        assert "must be a string" in error
    
    @given(valid_payload())
    def test_incident_id_always_generated_for_valid_payload(self, payload):
        """
        Property: Every valid payload should result in a unique incident_id.
        Validates: Requirement 1.5 - extract failure timestamp, service name, and error context
        """
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps(payload)
        }
        response = lambda_handler(event, None)
        
        body = json.loads(response["body"])
        incident_id = body["incident_id"]
        
        # Verify incident_id format: inc-YYYY-MM-DD-xxxxxxxx
        assert incident_id.startswith("inc-")
        parts = incident_id.split("-")
        assert len(parts) == 5, f"Incident ID has wrong format: {incident_id}"
        
        # Verify date components are numeric
        assert parts[1].isdigit() and len(parts[1]) == 4  # Year
        assert parts[2].isdigit() and len(parts[2]) == 2  # Month
        assert parts[3].isdigit() and len(parts[3]) == 2  # Day
        assert len(parts[4]) == 8  # UUID prefix
    
    @given(
        st.text(min_size=1, max_size=1000).filter(
            lambda x: not (x.strip().startswith('{') or x.strip().startswith('['))
        )
    )
    def test_malformed_json_returns_400(self, malformed_json):
        """
        Property: Any malformed JSON should return 400 Bad Request.
        Validates: Requirement 1.4 - return 400 for malformed payloads
        """
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": malformed_json
        }
        response = lambda_handler(event, None)
        
        # Should return 400 for invalid JSON
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "Invalid JSON" in body["details"] or "Missing required fields" in body["details"] or "JSON object" in body["details"]
    
    @given(valid_payload())
    def test_context_preserves_all_payload_data(self, payload):
        """
        Property: Context extraction should preserve all data from the payload.
        Validates: Requirement 1.5 - extract failure timestamp, service name, and error context
        """
        context = extract_incident_context(payload)
        
        # All required fields must be present and unchanged
        assert context["service_name"] == payload["service_name"]
        assert context["timestamp"] == payload["timestamp"]
        assert context["error_message"] == payload["error_message"]
        assert context["log_location"] == payload["log_location"]
        
        # Optional field should be preserved or defaulted
        if "alert_source" in payload:
            assert context["alert_source"] == payload["alert_source"]
        else:
            assert context["alert_source"] == "Manual"
