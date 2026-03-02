"""
Unit tests for incident validator Lambda function.

Tests validation logic for required fields, timestamp format, and response codes.
"""

import json
import pytest
from src.api.incident_validator import (
    validate_required_fields,
    validate_timestamp,
    validate_service_name,
    validate_error_message,
    validate_log_location,
    validate_payload,
    extract_incident_context,
    lambda_handler
)


class TestValidateRequiredFields:
    """Tests for required field validation."""
    
    def test_all_required_fields_present(self):
        """Test validation passes when all required fields are present."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Service failed",
            "log_location": "s3://bucket/logs"
        }
        is_valid, error = validate_required_fields(payload)
        assert is_valid is True
        assert error is None
    
    def test_missing_single_field(self):
        """Test validation fails when a single required field is missing."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Service failed"
        }
        is_valid, error = validate_required_fields(payload)
        assert is_valid is False
        assert "log_location" in error
    
    def test_missing_multiple_fields(self):
        """Test validation fails when multiple required fields are missing."""
        payload = {
            "service_name": "payment-processor"
        }
        is_valid, error = validate_required_fields(payload)
        assert is_valid is False
        assert "timestamp" in error
        assert "error_message" in error
        assert "log_location" in error


class TestValidateTimestamp:
    """Tests for timestamp validation."""
    
    def test_valid_iso8601_with_z(self):
        """Test validation passes for ISO 8601 format with Z."""
        is_valid, error = validate_timestamp("2025-01-15T10:30:00Z")
        assert is_valid is True
        assert error is None
    
    def test_valid_iso8601_with_offset(self):
        """Test validation passes for ISO 8601 format with timezone offset."""
        is_valid, error = validate_timestamp("2025-01-15T10:30:00+00:00")
        assert is_valid is True
        assert error is None
    
    def test_invalid_format(self):
        """Test validation fails for invalid timestamp format."""
        is_valid, error = validate_timestamp("2025-01-15 10:30:00")
        assert is_valid is False
        assert "ISO 8601" in error
    
    def test_non_string_timestamp(self):
        """Test validation fails when timestamp is not a string."""
        is_valid, error = validate_timestamp(12345)
        assert is_valid is False
        assert "must be a string" in error


class TestValidateServiceName:
    """Tests for service name validation."""
    
    def test_valid_service_name(self):
        """Test validation passes for valid service name."""
        is_valid, error = validate_service_name("payment-processor")
        assert is_valid is True
        assert error is None
    
    def test_empty_service_name(self):
        """Test validation fails for empty service name."""
        is_valid, error = validate_service_name("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_whitespace_only_service_name(self):
        """Test validation fails for whitespace-only service name."""
        is_valid, error = validate_service_name("   ")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_non_string_service_name(self):
        """Test validation fails when service name is not a string."""
        is_valid, error = validate_service_name(123)
        assert is_valid is False
        assert "must be a string" in error


class TestValidateErrorMessage:
    """Tests for error message validation."""
    
    def test_valid_error_message(self):
        """Test validation passes for valid error message."""
        is_valid, error = validate_error_message("Connection timeout")
        assert is_valid is True
        assert error is None
    
    def test_empty_error_message(self):
        """Test validation fails for empty error message."""
        is_valid, error = validate_error_message("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_non_string_error_message(self):
        """Test validation fails when error message is not a string."""
        is_valid, error = validate_error_message(None)
        assert is_valid is False
        assert "must be a string" in error


class TestValidateLogLocation:
    """Tests for log location validation."""
    
    def test_valid_s3_uri(self):
        """Test validation passes for valid S3 URI."""
        is_valid, error = validate_log_location("s3://bucket/path/to/logs")
        assert is_valid is True
        assert error is None
    
    def test_invalid_uri_scheme(self):
        """Test validation fails for non-S3 URI."""
        is_valid, error = validate_log_location("http://example.com/logs")
        assert is_valid is False
        assert "S3 URI" in error
    
    def test_empty_log_location(self):
        """Test validation fails for empty log location."""
        is_valid, error = validate_log_location("")
        assert is_valid is False
        assert "cannot be empty" in error
    
    def test_non_string_log_location(self):
        """Test validation fails when log location is not a string."""
        is_valid, error = validate_log_location(["s3://bucket/logs"])
        assert is_valid is False
        assert "must be a string" in error


class TestValidatePayload:
    """Tests for complete payload validation."""
    
    def test_valid_payload(self):
        """Test validation passes for completely valid payload."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Service health check failed",
            "log_location": "s3://incident-logs/payment-processor/2025-01-15.log"
        }
        is_valid, error = validate_payload(payload)
        assert is_valid is True
        assert error is None
    
    def test_invalid_timestamp_in_payload(self):
        """Test validation fails when timestamp is invalid."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "invalid-timestamp",
            "error_message": "Service failed",
            "log_location": "s3://bucket/logs"
        }
        is_valid, error = validate_payload(payload)
        assert is_valid is False
        assert "ISO 8601" in error


class TestExtractIncidentContext:
    """Tests for incident context extraction."""
    
    def test_extract_all_fields(self):
        """Test extraction of all incident context fields."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Service failed",
            "log_location": "s3://bucket/logs",
            "alert_source": "CloudWatch"
        }
        context = extract_incident_context(payload)
        assert context["service_name"] == "payment-processor"
        assert context["timestamp"] == "2025-01-15T10:30:00Z"
        assert context["error_message"] == "Service failed"
        assert context["log_location"] == "s3://bucket/logs"
        assert context["alert_source"] == "CloudWatch"
    
    def test_extract_with_default_alert_source(self):
        """Test extraction uses default alert_source when not provided."""
        payload = {
            "service_name": "payment-processor",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Service failed",
            "log_location": "s3://bucket/logs"
        }
        context = extract_incident_context(payload)
        assert context["alert_source"] == "Manual"


class TestLambdaHandler:
    """Tests for Lambda handler function."""
    
    def test_valid_request_returns_202(self):
        """Test valid request returns 202 Accepted with incident_id."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service health check failed",
                "log_location": "s3://incident-logs/payment-processor/2025-01-15.log"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        assert "Content-Type" in response["headers"]
        
        body = json.loads(response["body"])
        assert "incident_id" in body
        assert body["status"] == "processing"
        assert body["message"] == "Incident analysis initiated"
        assert "context" in body
    
    def test_missing_required_field_returns_400(self):
        """Test missing required field returns 400 Bad Request."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "log_location" in body["details"]
    
    def test_invalid_json_returns_400(self):
        """Test malformed JSON returns 400 Bad Request."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": "{ invalid json }"
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
    
    def test_missing_body_returns_400(self):
        """Test missing request body returns 400 Bad Request."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            }
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "body is required" in body["details"]
    
    def test_invalid_timestamp_format_returns_400(self):
        """Test invalid timestamp format returns 400 Bad Request."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15 10:30:00",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "ISO 8601" in body["details"]
    
    def test_incident_id_format(self):
        """Test incident_id follows expected format."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        body = json.loads(response["body"])
        incident_id = body["incident_id"]
        
        # Check format: inc-YYYY-MM-DD-xxxxxxxx
        assert incident_id.startswith("inc-")
        parts = incident_id.split("-")
        assert len(parts) == 5  # inc, YYYY, MM, DD, uuid
        assert len(parts[4]) == 8  # UUID prefix
    
    def test_unauthenticated_request_returns_401(self):
        """Test request without authentication returns 401 Unauthorized."""
        event = {
            "headers": {},
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body["error"] == "Unauthorized"
        assert "authentication" in body["details"].lower() or "api key" in body["details"].lower()
    
    def test_authenticated_with_iam_returns_202(self):
        """Test request with IAM authentication returns 202 Accepted."""
        event = {
            "headers": {},
            "requestContext": {
                "identity": {
                    "userArn": "arn:aws:iam::123456789012:user/test-user"
                }
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "incident_id" in body



class TestAPIEdgeCases:
    """
    Unit tests for API edge cases.
    
    Tests malformed JSON payloads, missing required fields, and invalid timestamp formats.
    Validates Requirements 1.4 and 12.4.
    """
    
    def test_malformed_json_missing_closing_brace(self):
        """Test malformed JSON with missing closing brace returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": '{"service_name": "test-service", "timestamp": "2025-01-15T10:30:00Z"'
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
    
    def test_malformed_json_invalid_syntax(self):
        """Test malformed JSON with invalid syntax returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": '{"service_name": "test", "timestamp": invalid}'
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
    
    def test_malformed_json_trailing_comma(self):
        """Test malformed JSON with trailing comma returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": '{"service_name": "test", "timestamp": "2025-01-15T10:30:00Z",}'
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
    
    def test_malformed_json_single_quotes(self):
        """Test malformed JSON with single quotes instead of double quotes returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": "{'service_name': 'test', 'timestamp': '2025-01-15T10:30:00Z'}"
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
    
    def test_json_array_instead_of_object(self):
        """Test JSON array instead of object returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps(["service_name", "timestamp"])
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "must be a JSON object" in body["details"]
    
    def test_json_string_instead_of_object(self):
        """Test JSON string instead of object returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps("just a string")
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "must be a JSON object" in body["details"]
    
    def test_json_number_instead_of_object(self):
        """Test JSON number instead of object returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps(12345)
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "must be a JSON object" in body["details"]
    
    def test_missing_service_name_field(self):
        """Test missing service_name field returns 400 with specific error."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "service_name" in body["details"]
    
    def test_missing_timestamp_field(self):
        """Test missing timestamp field returns 400 with specific error."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "timestamp" in body["details"]
    
    def test_missing_error_message_field(self):
        """Test missing error_message field returns 400 with specific error."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "error_message" in body["details"]
    
    def test_missing_log_location_field(self):
        """Test missing log_location field returns 400 with specific error."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00Z",
                "error_message": "Service failed"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "log_location" in body["details"]
    
    def test_missing_all_required_fields(self):
        """Test missing all required fields returns 400 with all field names."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({})
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "service_name" in body["details"]
        assert "timestamp" in body["details"]
        assert "error_message" in body["details"]
        assert "log_location" in body["details"]
    
    def test_invalid_timestamp_format_date_only(self):
        """Test timestamp with date only (no time) returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_invalid_timestamp_format_space_separator(self):
        """Test timestamp with space separator instead of T returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15 10:30:00",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_invalid_timestamp_format_slash_separators(self):
        """Test timestamp with slash separators returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "01/15/2025 10:30:00",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_invalid_timestamp_format_unix_epoch(self):
        """Test timestamp as Unix epoch integer returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": 1705318200,
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "must be a string" in body["details"]
    
    def test_invalid_timestamp_format_invalid_date(self):
        """Test timestamp with invalid date values returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-13-45T10:30:00Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_invalid_timestamp_format_invalid_time(self):
        """Test timestamp with invalid time values returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T25:70:99Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_invalid_timestamp_empty_string(self):
        """Test timestamp as empty string returns 400."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "ISO 8601" in body["details"]
    
    def test_valid_timestamp_with_milliseconds(self):
        """Test valid timestamp with milliseconds is accepted."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00.123Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "incident_id" in body
    
    def test_valid_timestamp_with_microseconds(self):
        """Test valid timestamp with microseconds is accepted."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00.123456Z",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "incident_id" in body
    
    def test_valid_timestamp_with_negative_offset(self):
        """Test valid timestamp with negative timezone offset is accepted."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00-05:00",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "incident_id" in body
    
    def test_valid_timestamp_with_positive_offset(self):
        """Test valid timestamp with positive timezone offset is accepted."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "payment-processor",
                "timestamp": "2025-01-15T10:30:00+08:00",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert "incident_id" in body
    
    def test_error_response_includes_details(self):
        """Test error responses include detailed error information per Requirement 12.4."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": json.dumps({
                "service_name": "",
                "timestamp": "invalid",
                "error_message": "Service failed",
                "log_location": "s3://bucket/logs"
            })
        }
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body
        assert "details" in body
        assert body["error"] == "Bad Request"
        # Should have specific details about what's wrong
        assert len(body["details"]) > 0
    
    def test_malformed_payload_logs_error_and_returns_400(self):
        """Test malformed payload returns 400 status code per Requirement 1.4."""
        event = {
            "headers": {
                "x-api-key": "test-api-key-12345678901234567890"
            },
            "requestContext": {
                "identity": {}
            },
            "body": "not valid json at all"
        }
        response = lambda_handler(event, None)
        
        # Requirement 1.4: IF an alert payload is malformed, 
        # THEN THE Incident_Response_System SHALL log the error and return a 400 status code
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "Bad Request"
        assert "Invalid JSON" in body["details"]
