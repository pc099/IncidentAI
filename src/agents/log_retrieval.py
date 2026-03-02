"""
Log Retrieval Module for Log Analysis Agent

This module handles retrieving logs from S3 for incident analysis.
It calculates the appropriate time window and handles large log files.
"""

import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LogRetrievalError(Exception):
    """Exception raised when log retrieval fails"""
    pass


def calculate_time_window(timestamp: str) -> Tuple[datetime, datetime]:
    """
    Calculate the time window for log retrieval.
    
    Args:
        timestamp: ISO 8601 formatted timestamp of the failure
        
    Returns:
        Tuple of (start_time, end_time) where:
        - start_time is 15 minutes before the failure
        - end_time is 5 minutes after the failure
        
    Validates: Requirements 2.2
    """
    failure_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    start_time = failure_time - timedelta(minutes=15)
    end_time = failure_time + timedelta(minutes=5)
    
    return start_time, end_time


def retrieve_logs_from_s3(
    log_location: str,
    timestamp: str,
    service_name: str,
    max_size_mb: int = 10
) -> Dict:
    """
    Retrieve logs from S3 for the specified time window.
    
    Args:
        log_location: S3 URI of the log file (e.g., s3://bucket/path/to/log.log)
        timestamp: ISO 8601 formatted timestamp of the failure
        service_name: Name of the service that failed
        max_size_mb: Maximum log size to retrieve in MB (default: 10)
        
    Returns:
        Dictionary containing:
        - log_content: The log content as a string
        - log_volume: Size of logs retrieved
        - time_range: Time window used for retrieval
        - truncated: Whether logs were truncated
        - confidence_score: 0 if logs missing, otherwise not set here
        
    Validates: Requirements 2.1, 2.2, 2.3, 2.7
    """
    try:
        # Parse S3 URI
        if not log_location.startswith('s3://'):
            raise LogRetrievalError(f"Invalid S3 URI: {log_location}")
        
        # Extract bucket and key from S3 URI
        s3_path = log_location[5:]  # Remove 's3://'
        parts = s3_path.split('/', 1)
        if len(parts) != 2:
            raise LogRetrievalError(f"Invalid S3 path format: {log_location}")
        
        bucket_name = parts[0]
        object_key = parts[1]
        
        # Calculate time window
        start_time, end_time = calculate_time_window(timestamp)
        time_range = f"{start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}"
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Get object metadata first to check size
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            object_size = response['ContentLength']
        except s3_client.exceptions.NoSuchKey:
            # Handle missing logs gracefully (Requirement 2.7)
            logger.warning(f"Log file not found: {log_location}")
            return {
                "log_content": "",
                "log_volume": "0 MB",
                "time_range": time_range,
                "truncated": False,
                "confidence_score": 0,
                "error": "Log file not found"
            }
        except Exception as e:
            logger.error(f"Error checking log file: {str(e)}")
            return {
                "log_content": "",
                "log_volume": "0 MB",
                "time_range": time_range,
                "truncated": False,
                "confidence_score": 0,
                "error": f"Error accessing log file: {str(e)}"
            }
        
        # Handle logs >10MB by retrieving most recent 10MB (Requirement 2.3)
        max_size_bytes = max_size_mb * 1024 * 1024
        truncated = False
        
        if object_size > max_size_bytes:
            # Retrieve only the last 10MB
            byte_range = f"bytes={object_size - max_size_bytes}-{object_size - 1}"
            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=object_key,
                Range=byte_range
            )
            truncated = True
            log_volume = f"{max_size_mb} MB"
        else:
            # Retrieve entire file
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            log_volume = f"{object_size / (1024 * 1024):.1f} MB"
        
        # Read log content
        log_content = response['Body'].read().decode('utf-8', errors='replace')
        
        logger.info(
            f"Retrieved logs for {service_name}: {log_volume}, "
            f"truncated={truncated}, time_range={time_range}"
        )
        
        return {
            "log_content": log_content,
            "log_volume": log_volume,
            "time_range": time_range,
            "truncated": truncated
        }
        
    except Exception as e:
        logger.error(f"Error retrieving logs from S3: {str(e)}")
        raise LogRetrievalError(f"Failed to retrieve logs: {str(e)}")
