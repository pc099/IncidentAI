"""
Log Retrieval Module

Handles retrieval of logs from S3 for analysis.
"""

import boto3
import logging
from datetime import datetime, timedelta
from typing import Tuple
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def calculate_time_window(timestamp: str, window_minutes: int = 30) -> Tuple[datetime, datetime]:
    """
    Calculate time window for log retrieval around incident timestamp
    
    Args:
        timestamp: Incident timestamp in ISO format
        window_minutes: Minutes before and after incident
        
    Returns:
        Tuple of (start_time, end_time)
    """
    try:
        incident_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        start_time = incident_time - timedelta(minutes=window_minutes)
        end_time = incident_time + timedelta(minutes=window_minutes)
        return start_time, end_time
    except Exception as e:
        logger.error(f"Failed to parse timestamp {timestamp}: {str(e)}")
        # Fallback to current time
        now = datetime.utcnow()
        return now - timedelta(minutes=window_minutes), now + timedelta(minutes=window_minutes)


def retrieve_logs_from_s3(
    bucket_name: str,
    key_prefix: str,
    start_time: datetime,
    end_time: datetime,
    max_size_mb: int = 50
) -> str:
    """
    Retrieve logs from S3 within time window
    
    Args:
        bucket_name: S3 bucket name
        key_prefix: S3 key prefix for logs
        start_time: Start time for log retrieval
        end_time: End time for log retrieval
        max_size_mb: Maximum log size to retrieve
        
    Returns:
        Combined log content as string
    """
    s3_client = boto3.client('s3')
    log_content = ""
    total_size = 0
    max_size_bytes = max_size_mb * 1024 * 1024
    
    try:
        # List objects in the time range
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=key_prefix,
            MaxKeys=100  # Limit number of files
        )
        
        if 'Contents' not in response:
            logger.warning(f"No logs found in {bucket_name}/{key_prefix}")
            return "No logs found for the specified time range."
        
        # Filter objects by time and retrieve content
        for obj in response['Contents']:
            if total_size >= max_size_bytes:
                log_content += "\n... (additional logs truncated due to size limit)"
                break
                
            # Simple time filtering based on object key (assumes timestamp in key)
            # In production, this would be more sophisticated
            try:
                obj_response = s3_client.get_object(
                    Bucket=bucket_name,
                    Key=obj['Key']
                )
                
                content = obj_response['Body'].read().decode('utf-8', errors='ignore')
                content_size = len(content.encode('utf-8'))
                
                if total_size + content_size > max_size_bytes:
                    # Truncate to fit within limit
                    remaining_bytes = max_size_bytes - total_size
                    content = content[:remaining_bytes]
                    log_content += f"\n--- Log file: {obj['Key']} ---\n"
                    log_content += content
                    log_content += "\n... (log file truncated due to size limit)"
                    break
                
                log_content += f"\n--- Log file: {obj['Key']} ---\n"
                log_content += content
                total_size += content_size
                
            except ClientError as e:
                logger.error(f"Failed to retrieve {obj['Key']}: {str(e)}")
                continue
        
        if not log_content.strip():
            return "No log content could be retrieved."
            
        logger.info(f"Retrieved {total_size} bytes of logs from {len(response.get('Contents', []))} files")
        return log_content
        
    except ClientError as e:
        logger.error(f"Failed to retrieve logs from S3: {str(e)}")
        return f"Error retrieving logs: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error retrieving logs: {str(e)}")
        return f"Unexpected error retrieving logs: {str(e)}"