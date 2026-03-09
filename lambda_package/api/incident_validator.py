"""
Request validation Lambda function for incident response system.

This module validates incoming incident alert payloads and returns appropriate responses.
Validates required fields and returns 202 Accepted with incident_id for valid requests,
or 400 Bad Request for invalid payloads.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional


def validate_required_fields(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required fields are present in the payload.
    
    Args:
        payload: The incident alert payload
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["service_name", "timestamp", "error_message", "log_location"]
    missing_fields = [field for field in required_fields if field not in payload]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def validate_timestamp(timestamp: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that the timestamp is in ISO 8601 format.
    
    Args:
        timestamp: The timestamp string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(timestamp, str):
        return False, "timestamp must be a string"
    
    # Try to parse ISO 8601 format - must contain 'T' separator
    if 'T' not in timestamp:
        return False, "timestamp must be in ISO 8601 format (e.g., '2025-01-15T10:30:00Z')"
    
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return True, None
    except (ValueError, AttributeError):
        return False, "timestamp must be in ISO 8601 format (e.g., '2025-01-15T10:30:00Z')"


def validate_service_name(service_name: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that the service_name is a non-empty string.
    
    Args:
        service_name: The service name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(service_name, str):
        return False, "service_name must be a string"
    
    if not service_name.strip():
        return False, "service_name cannot be empty"
    
    return True, None


def validate_error_message(error_message: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that the error_message is a non-empty string.
    
    Args:
        error_message: The error message to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(error_message, str):
        return False, "error_message must be a string"
    
    if not error_message.strip():
        return False, "error_message cannot be empty"
    
    return True, None


def validate_log_location(log_location: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that the log_location is a valid S3 URI.
    
    Args:
        log_location: The log location to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(log_location, str):
        return False, "log_location must be a string"
    
    if not log_location.strip():
        return False, "log_location cannot be empty"
    
    # Basic S3 URI validation
    if not log_location.startswith("s3://"):
        return False, "log_location must be a valid S3 URI (e.g., 's3://bucket/path/to/logs')"
    
    return True, None


def validate_payload(payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate the complete incident alert payload.
    
    Args:
        payload: The incident alert payload
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields presence
    is_valid, error = validate_required_fields(payload)
    if not is_valid:
        return False, error
    
    # Validate service_name
    is_valid, error = validate_service_name(payload.get("service_name"))
    if not is_valid:
        return False, error
    
    # Validate timestamp
    is_valid, error = validate_timestamp(payload.get("timestamp"))
    if not is_valid:
        return False, error
    
    # Validate error_message
    is_valid, error = validate_error_message(payload.get("error_message"))
    if not is_valid:
        return False, error
    
    # Validate log_location
    is_valid, error = validate_log_location(payload.get("log_location"))
    if not is_valid:
        return False, error
    
    return True, None


def extract_incident_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract failure timestamp, service name, and error context from payload.
    
    Args:
        payload: The validated incident alert payload
        
    Returns:
        Dictionary with extracted context
    """
    return {
        "service_name": payload["service_name"],
        "timestamp": payload["timestamp"],
        "error_message": payload["error_message"],
        "log_location": payload["log_location"],
        "alert_source": payload.get("alert_source", "Manual")
    }


def validate_authentication(event: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate API key or IAM authentication from API Gateway event.
    
    API Gateway passes authentication information in the requestContext:
    - For API key auth: requestContext.identity.apiKey or headers['x-api-key']
    - For IAM auth: requestContext.identity.userArn or requestContext.authorizer
    
    Args:
        event: API Gateway event containing authentication info
        
    Returns:
        Tuple of (is_authenticated, error_message)
    """
    # Check for API key in headers (most common)
    headers = event.get("headers", {})
    
    # Headers can be case-insensitive in API Gateway
    api_key = None
    for header_name, header_value in headers.items():
        if header_name.lower() == "x-api-key":
            api_key = header_value
            break
    
    # Check for IAM authentication in requestContext
    request_context = event.get("requestContext", {})
    identity = request_context.get("identity", {})
    
    # IAM authentication indicators
    user_arn = identity.get("userArn")
    caller_id = identity.get("caller")
    account_id = identity.get("accountId")
    
    # Check for authorizer (custom or IAM)
    authorizer = request_context.get("authorizer")
    
    # Valid authentication if any of these are present:
    # 1. API key in headers
    # 2. IAM user ARN
    # 3. Authorizer context
    # 4. Valid account ID (indicates IAM auth)
    
    if api_key:
        # API key authentication
        if len(api_key.strip()) == 0:
            return False, "API key cannot be empty"
        return True, None
    
    if user_arn:
        # IAM user authentication
        return True, None
    
    if authorizer:
        # Custom authorizer or IAM authorizer
        return True, None
    
    if account_id and account_id != "anonymous":
        # IAM authentication with account ID
        return True, None
    
    # No valid authentication found
    return False, "Missing authentication: API key or IAM credentials required"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for incident alert validation.
    
    Validates incoming incident alert payloads and returns:
    - 202 Accepted with incident_id for valid requests
    - 400 Bad Request for invalid payloads with error details
    - 401 Unauthorized for missing or invalid authentication
    
    Args:
        event: API Gateway event containing the request
        context: Lambda context object
        
    Returns:
        API Gateway response with status code and body
    """
    try:
        # Validate authentication first (Requirements 10.5, 12.6)
        is_authenticated, auth_error = validate_authentication(event)
        if not is_authenticated:
            return {
                "statusCode": 401,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Unauthorized",
                    "details": auth_error
                })
            }
        # Parse request body
        if "body" not in event:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Bad Request",
                    "details": "Request body is required"
                })
            }
        
        # Handle both string and dict body (API Gateway can pass either)
        body = event["body"]
        if isinstance(body, str):
            try:
                payload = json.loads(body)
            except json.JSONDecodeError as e:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "error": "Bad Request",
                        "details": f"Invalid JSON: {str(e)}"
                    })
                }
        else:
            payload = body
        
        # Ensure payload is a dictionary
        if not isinstance(payload, dict):
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Bad Request",
                    "details": "Request body must be a JSON object"
                })
            }
        
        # Validate payload
        is_valid, error_message = validate_payload(payload)
        
        if not is_valid:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json"
                },
                "body": json.dumps({
                    "error": "Bad Request",
                    "details": error_message
                })
            }
        
        # Extract incident context
        incident_context = extract_incident_context(payload)
        
        # Generate unique incident ID
        incident_id = f"inc-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}"
        
        # Return 202 Accepted with incident_id
        return {
            "statusCode": 202,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "incident_id": incident_id,
                "status": "processing",
                "message": "Incident analysis initiated",
                "context": incident_context
            })
        }
        
    except Exception as e:
        # Handle unexpected errors
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Internal Server Error",
                "details": f"An unexpected error occurred: {str(e)}"
            })
        }
