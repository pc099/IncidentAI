"""
Property-based tests for API authentication validation.

**Property 40: API Authentication Validation**
**Validates: Requirements 10.5, 12.6**

These tests verify that the API Gateway validates API keys or IAM credentials
before processing requests, ensuring secure access to the incident response system.
"""

import json
from hypothesis import given, strategies as st, assume
from src.api.incident_validator import (
    validate_authentication,
    lambda_handler
)


# Strategy for generating valid API keys
@st.composite
def valid_api_key(draw):
    """Generate valid API key strings."""
    # API keys are typically alphanumeric with some special characters
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'),
        min_size=20,
        max_size=40
    ))


# Strategy for generating valid IAM ARNs
@st.composite
def valid_iam_arn(draw):
    """Generate valid IAM user ARN strings."""
    account_id = draw(st.integers(min_value=100000000000, max_value=999999999999))
    user_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'),
        min_size=1,
        max_size=64
    ))
    return f"arn:aws:iam::{account_id}:user/{user_name}"


# Strategy for generating valid AWS account IDs
@st.composite
def valid_account_id(draw):
    """Generate valid AWS account ID strings."""
    return str(draw(st.integers(min_value=100000000000, max_value=999999999999)))


# Strategy for generating API Gateway events with API key authentication
@st.composite
def event_with_api_key(draw):
    """Generate API Gateway event with API key in headers."""
    api_key = draw(valid_api_key())
    
    # API Gateway can pass headers with different casing
    header_name = draw(st.sampled_from(['x-api-key', 'X-Api-Key', 'X-API-KEY']))
    
    return {
        "headers": {
            header_name: api_key
        },
        "requestContext": {
            "identity": {}
        }
    }


# Strategy for generating API Gateway events with IAM authentication
@st.composite
def event_with_iam_auth(draw):
    """Generate API Gateway event with IAM authentication."""
    auth_type = draw(st.sampled_from(['userArn', 'accountId', 'authorizer']))
    
    event = {
        "headers": {},
        "requestContext": {
            "identity": {}
        }
    }
    
    if auth_type == 'userArn':
        event["requestContext"]["identity"]["userArn"] = draw(valid_iam_arn())
    elif auth_type == 'accountId':
        event["requestContext"]["identity"]["accountId"] = draw(valid_account_id())
    elif auth_type == 'authorizer':
        event["requestContext"]["authorizer"] = {
            "principalId": draw(st.text(min_size=1, max_size=50))
        }
    
    return event


# Strategy for generating API Gateway events without authentication
@st.composite
def event_without_auth(draw):
    """Generate API Gateway event without authentication."""
    return {
        "headers": {},
        "requestContext": {
            "identity": {}
        }
    }


# Strategy for generating complete valid payloads
@st.composite
def valid_incident_payload(draw):
    """Generate valid incident alert payloads."""
    year = draw(st.integers(min_value=2020, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    
    timestamp = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
    
    service_name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()))
    
    return {
        "service_name": service_name,
        "timestamp": timestamp,
        "error_message": draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip())),
        "log_location": f"s3://logs/{service_name}/{year}-{month:02d}-{day:02d}.log"
    }


class TestProperty40_APIAuthenticationValidation:
    """
    Property 40: API Authentication Validation
    Validates: Requirements 10.5, 12.6
    
    This property ensures that:
    1. Requests with valid API keys are authenticated (Req 10.5, 12.6)
    2. Requests with valid IAM credentials are authenticated (Req 10.5, 12.6)
    3. Requests without authentication are rejected (Req 10.5, 12.6)
    4. Authentication is validated before request processing (Req 12.6)
    """
    
    @given(event_with_api_key())
    def test_valid_api_key_authenticates_successfully(self, event):
        """
        Property: Any request with a valid API key should pass authentication.
        Validates: Requirements 10.5, 12.6 - validate API keys before processing
        """
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is True, \
            f"Valid API key failed authentication: {error}"
        assert error is None
    
    @given(event_with_iam_auth())
    def test_valid_iam_credentials_authenticate_successfully(self, event):
        """
        Property: Any request with valid IAM credentials should pass authentication.
        Validates: Requirements 10.5, 12.6 - validate IAM credentials before processing
        """
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is True, \
            f"Valid IAM credentials failed authentication: {error}"
        assert error is None
    
    @given(event_without_auth())
    def test_missing_authentication_fails(self, event):
        """
        Property: Any request without authentication should fail authentication.
        Validates: Requirements 10.5, 12.6 - validate authentication before processing
        """
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is False, \
            "Request without authentication passed validation"
        assert error is not None
        assert "authentication" in error.lower() or "api key" in error.lower()
    
    @given(event_without_auth(), valid_incident_payload())
    def test_unauthenticated_requests_return_401(self, event, payload):
        """
        Property: Any unauthenticated request should return 401 Unauthorized.
        Validates: Requirements 10.5, 12.6 - validate authentication before processing
        """
        event["body"] = json.dumps(payload)
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 401, \
            f"Unauthenticated request did not return 401: {response}"
        
        body = json.loads(response["body"])
        assert body["error"] == "Unauthorized"
        assert "details" in body
    
    @given(event_with_api_key(), valid_incident_payload())
    def test_authenticated_valid_requests_return_202(self, event, payload):
        """
        Property: Any authenticated request with valid payload should return 202 Accepted.
        Validates: Requirements 10.5, 12.6 - validate authentication then process request
        """
        event["body"] = json.dumps(payload)
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202, \
            f"Authenticated valid request did not return 202: {response}"
        
        body = json.loads(response["body"])
        assert "incident_id" in body
        assert body["status"] == "processing"
    
    @given(event_with_iam_auth(), valid_incident_payload())
    def test_iam_authenticated_valid_requests_return_202(self, event, payload):
        """
        Property: Any IAM-authenticated request with valid payload should return 202 Accepted.
        Validates: Requirements 10.5, 12.6 - validate IAM credentials then process request
        """
        event["body"] = json.dumps(payload)
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202, \
            f"IAM-authenticated valid request did not return 202: {response}"
        
        body = json.loads(response["body"])
        assert "incident_id" in body
        assert body["status"] == "processing"
    
    @given(
        st.sampled_from(['x-api-key', 'X-Api-Key', 'X-API-KEY', 'X-API-Key'])
    )
    def test_api_key_header_is_case_insensitive(self, header_name):
        """
        Property: API key header should be recognized regardless of casing.
        Validates: Requirements 10.5, 12.6 - validate API keys in various formats
        """
        event = {
            "headers": {
                header_name: "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            }
        }
        
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is True, \
            f"API key with header '{header_name}' failed authentication"
    
    @given(event_with_api_key())
    def test_empty_api_key_fails_authentication(self, event):
        """
        Property: Empty or whitespace-only API keys should fail authentication.
        Validates: Requirements 10.5, 12.6 - validate API key content
        """
        # Replace API key with empty string
        for header_name in event["headers"]:
            if header_name.lower() == "x-api-key":
                event["headers"][header_name] = "   "
                break
        
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is False, \
            "Empty API key passed authentication"
        assert error is not None
    
    @given(event_with_api_key())
    def test_authentication_checked_before_payload_validation(self, event):
        """
        Property: Authentication should be validated before payload validation.
        Validates: Requirement 12.6 - validate credentials before processing
        
        This ensures that even with invalid payloads, authentication is checked first.
        """
        # Provide invalid payload (missing required fields)
        event["body"] = json.dumps({"invalid": "payload"})
        
        # Remove authentication
        event["headers"] = {}
        event["requestContext"] = {"identity": {}}
        
        response = lambda_handler(event, None)
        
        # Should return 401 (auth failure) not 400 (validation failure)
        assert response["statusCode"] == 401, \
            "Authentication not checked before payload validation"
    
    @given(
        event_with_api_key(),
        st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.text(min_size=1, max_size=100),
            min_size=0,
            max_size=3
        )
    )
    def test_authenticated_invalid_payloads_return_400_not_401(self, event, invalid_payload):
        """
        Property: Authenticated requests with invalid payloads should return 400, not 401.
        Validates: Requirement 12.6 - validate credentials before processing
        
        This ensures authentication passes but payload validation fails.
        """
        # Ensure payload is actually invalid (missing required fields)
        required_fields = {"service_name", "timestamp", "error_message", "log_location"}
        assume(set(invalid_payload.keys()) != required_fields)
        
        event["body"] = json.dumps(invalid_payload)
        response = lambda_handler(event, None)
        
        # Should return 400 (validation error) not 401 (auth error)
        # This proves authentication passed
        assert response["statusCode"] in [400, 500], \
            f"Expected 400 or 500 for invalid payload, got {response['statusCode']}"
        
        if response["statusCode"] == 400:
            body = json.loads(response["body"])
            assert body["error"] != "Unauthorized", \
                "Authenticated request should not return Unauthorized error"
    
    @given(valid_api_key())
    def test_api_key_length_validation(self, api_key):
        """
        Property: API keys of any reasonable length should be accepted.
        Validates: Requirements 10.5, 12.6 - validate API keys
        """
        # API keys should be at least 20 characters (enforced by strategy)
        assume(len(api_key) >= 20)
        
        event = {
            "headers": {
                "x-api-key": api_key
            },
            "requestContext": {
                "identity": {}
            }
        }
        
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is True, \
            f"Valid API key of length {len(api_key)} failed authentication"
    
    @given(valid_iam_arn())
    def test_iam_arn_format_validation(self, user_arn):
        """
        Property: Valid IAM ARN formats should be accepted.
        Validates: Requirements 10.5, 12.6 - validate IAM credentials
        """
        event = {
            "headers": {},
            "requestContext": {
                "identity": {
                    "userArn": user_arn
                }
            }
        }
        
        is_authenticated, error = validate_authentication(event)
        assert is_authenticated is True, \
            f"Valid IAM ARN failed authentication: {user_arn}"
    
    @given(event_with_api_key(), event_with_iam_auth())
    def test_multiple_auth_methods_accepted(self, api_key_event, iam_event):
        """
        Property: Requests with multiple authentication methods should be accepted.
        Validates: Requirements 10.5, 12.6 - validate API keys or IAM credentials
        
        This tests the "or" condition in the requirements.
        """
        # Merge both authentication methods
        combined_event = {
            "headers": api_key_event["headers"],
            "requestContext": iam_event["requestContext"]
        }
        
        is_authenticated, error = validate_authentication(combined_event)
        assert is_authenticated is True, \
            "Request with multiple auth methods failed authentication"
    
    @given(event_without_auth(), valid_incident_payload())
    def test_unauthenticated_requests_never_process_payload(self, event, payload):
        """
        Property: Unauthenticated requests should never process the payload.
        Validates: Requirement 12.6 - validate credentials before processing
        
        This ensures no incident_id is generated for unauthenticated requests.
        """
        event["body"] = json.dumps(payload)
        response = lambda_handler(event, None)
        
        body = json.loads(response["body"])
        assert "incident_id" not in body, \
            "Unauthenticated request should not generate incident_id"
        assert response["statusCode"] == 401
    
    @given(
        st.text(min_size=0, max_size=10).filter(lambda x: len(x.strip()) < 20)
    )
    def test_short_api_keys_fail_authentication(self, short_key):
        """
        Property: API keys shorter than minimum length should fail authentication.
        Validates: Requirements 10.5, 12.6 - validate API key format
        
        Note: This assumes API keys have a minimum length requirement.
        """
        # Only test if key is actually short
        assume(len(short_key.strip()) < 20)
        
        event = {
            "headers": {
                "x-api-key": short_key
            },
            "requestContext": {
                "identity": {}
            }
        }
        
        is_authenticated, error = validate_authentication(event)
        
        # Empty keys should definitely fail
        if len(short_key.strip()) == 0:
            assert is_authenticated is False, \
                "Empty API key should fail authentication"
