"""
Log Parser Module

Parses log content to extract error patterns, stack traces, and other relevant information.
"""

import re
import logging
from typing import Dict, List, Any
from datetime import datetime

def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text

    Args:
        text: Text content to redact

    Returns:
        Text with PII redacted
    """
    if not isinstance(text, str):
        return str(text)

    redacted = text

    # Email addresses
    redacted = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',
        redacted
    )

    # Phone numbers (various formats)
    redacted = re.sub(
        r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        '[PHONE_REDACTED]',
        redacted
    )

    # SSN (XXX-XX-XXXX)
    redacted = re.sub(
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN_REDACTED]',
        redacted
    )

    # Credit card numbers (13-19 digits)
    redacted = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4,7}\b',
        '[CC_REDACTED]',
        redacted
    )

    return redacted
logger = logging.getLogger(__name__)


def parse_logs(log_content: str) -> Dict[str, Any]:
    """
    Parse log content to extract structured information
    
    Args:
        log_content: Raw log content as string
        
    Returns:
        Dictionary containing parsed log information
    """
    try:
        parsed_data = {
            "error_patterns": extract_error_patterns(log_content),
            "stack_traces": extract_stack_traces(log_content),
            "timestamps": extract_timestamps(log_content),
            "log_levels": extract_log_levels(log_content),
            "service_names": extract_service_names(log_content),
            "request_ids": extract_request_ids(log_content),
            "parsing_metadata": {
                "total_lines": len(log_content.split('\n')),
                "total_chars": len(log_content),
                "parsed_at": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"Parsed logs: {len(parsed_data['error_patterns'])} error patterns, "
                   f"{len(parsed_data['stack_traces'])} stack traces")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Log parsing failed: {str(e)}")
        return {
            "error_patterns": [],
            "stack_traces": [],
            "timestamps": [],
            "log_levels": [],
            "service_names": [],
            "request_ids": [],
            "parsing_error": str(e)
        }


def extract_error_patterns(log_content: str) -> List[Dict[str, Any]]:
    """Extract error patterns from log content"""
    error_patterns = []
    
    # Common error patterns
    patterns = [
        # Exception patterns
        (r'(\w+Exception): (.+)', 'exception'),
        (r'(\w+Error): (.+)', 'error'),
        
        # HTTP error patterns
        (r'HTTP (\d{3}) (.+)', 'http_error'),
        (r'Status: (\d{3})', 'status_code'),
        
        # Timeout patterns
        (r'timeout|timed out|time out', 'timeout'),
        (r'connection timeout', 'connection_timeout'),
        
        # Memory patterns
        (r'out of memory|oom|memory exhausted', 'memory_error'),
        (r'heap space|memory leak', 'memory_issue'),
        
        # Connection patterns
        (r'connection refused|connection failed|connection reset', 'connection_error'),
        (r'unable to connect|connection timeout', 'connection_issue'),
        
        # AWS specific patterns
        (r'AccessDenied|Forbidden|Unauthorized', 'access_denied'),
        (r'ThrottlingException|Rate exceeded', 'throttling'),
        (r'ServiceUnavailable|Service unavailable', 'service_unavailable'),
        
        # Database patterns
        (r'database connection|db connection|sql', 'database_error'),
        (r'deadlock|lock timeout', 'database_lock'),
        
        # Generic error patterns
        (r'failed to|failure|error|exception', 'generic_error')
    ]
    
    for pattern, error_type in patterns:
        matches = re.finditer(pattern, log_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            error_patterns.append({
                "pattern": match.group(0),
                "type": error_type,
                "line_number": log_content[:match.start()].count('\n') + 1,
                "context": _get_context_lines(log_content, match.start(), match.end())
            })
    
    # Remove duplicates and sort by frequency
    unique_patterns = {}
    for pattern in error_patterns:
        key = (pattern["pattern"].lower(), pattern["type"])
        if key in unique_patterns:
            unique_patterns[key]["frequency"] += 1
        else:
            unique_patterns[key] = {
                **pattern,
                "frequency": 1
            }
    
    return sorted(unique_patterns.values(), key=lambda x: x["frequency"], reverse=True)


def extract_stack_traces(log_content: str) -> List[Dict[str, Any]]:
    """Extract stack traces from log content"""
    stack_traces = []
    
    # Stack trace patterns
    stack_patterns = [
        # Java stack traces
        r'(?:Exception|Error).*?\n(?:\s+at\s+.+\n)+',
        # Python stack traces
        r'Traceback \(most recent call last\):.*?(?=\n\S|\n$)',
        # JavaScript stack traces
        r'Error:.*?\n(?:\s+at\s+.+\n)+',
        # C# stack traces
        r'(?:Exception|Error).*?\n(?:\s+at\s+.+\n)+'
    ]
    
    for pattern in stack_patterns:
        matches = re.finditer(pattern, log_content, re.MULTILINE | re.DOTALL)
        for match in matches:
            stack_trace = match.group(0).strip()
            stack_traces.append({
                "trace": stack_trace,
                "line_number": log_content[:match.start()].count('\n') + 1,
                "length": len(stack_trace.split('\n')),
                "type": _identify_stack_trace_type(stack_trace)
            })
    
    return stack_traces


def extract_timestamps(log_content: str) -> List[str]:
    """Extract timestamps from log content"""
    timestamp_patterns = [
        # ISO 8601
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',
        # Common log formats
        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
        r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
        # Syslog format
        r'[A-Za-z]{3} \d{1,2} \d{2}:\d{2}:\d{2}'
    ]
    
    timestamps = []
    for pattern in timestamp_patterns:
        matches = re.findall(pattern, log_content)
        timestamps.extend(matches)
    
    return list(set(timestamps))  # Remove duplicates


def extract_log_levels(log_content: str) -> List[Dict[str, Any]]:
    """Extract log levels and their frequencies"""
    level_pattern = r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b'
    matches = re.findall(level_pattern, log_content, re.IGNORECASE)
    
    level_counts = {}
    for level in matches:
        level_upper = level.upper()
        level_counts[level_upper] = level_counts.get(level_upper, 0) + 1
    
    return [{"level": level, "count": count} for level, count in level_counts.items()]


def extract_service_names(log_content: str) -> List[str]:
    """Extract service names from log content"""
    service_patterns = [
        r'service[_-]name[:\s=]+([a-zA-Z0-9_-]+)',
        r'application[:\s=]+([a-zA-Z0-9_-]+)',
        r'component[:\s=]+([a-zA-Z0-9_-]+)',
        r'\[([a-zA-Z0-9_-]+)\]',  # Service names in brackets
    ]
    
    services = []
    for pattern in service_patterns:
        matches = re.findall(pattern, log_content, re.IGNORECASE)
        services.extend(matches)
    
    return list(set(services))  # Remove duplicates


def extract_request_ids(log_content: str) -> List[str]:
    """Extract request IDs from log content"""
    request_patterns = [
        r'request[_-]?id[:\s=]+([a-zA-Z0-9-]+)',
        r'correlation[_-]?id[:\s=]+([a-zA-Z0-9-]+)',
        r'trace[_-]?id[:\s=]+([a-zA-Z0-9-]+)',
        r'x-request-id[:\s=]+([a-zA-Z0-9-]+)',
    ]
    
    request_ids = []
    for pattern in request_patterns:
        matches = re.findall(pattern, log_content, re.IGNORECASE)
        request_ids.extend(matches)
    
    return list(set(request_ids))  # Remove duplicates


def _get_context_lines(log_content: str, start_pos: int, end_pos: int, context_lines: int = 2) -> List[str]:
    """Get context lines around a match"""
    lines = log_content.split('\n')
    match_line = log_content[:start_pos].count('\n')
    
    start_line = max(0, match_line - context_lines)
    end_line = min(len(lines), match_line + context_lines + 1)
    
    return lines[start_line:end_line]


def _identify_stack_trace_type(stack_trace: str) -> str:
    """Identify the type of stack trace"""
    if 'at ' in stack_trace and '.java:' in stack_trace:
        return 'java'
    elif 'Traceback' in stack_trace and 'File "' in stack_trace:
        return 'python'
    elif 'at ' in stack_trace and '.js:' in stack_trace:
        return 'javascript'
    elif 'at ' in stack_trace and '.cs:' in stack_trace:
        return 'csharp'
    else:
        return 'unknown'