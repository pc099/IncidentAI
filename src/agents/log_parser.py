"""
Log Parser Module for Log Analysis Agent

This module handles parsing logs to extract error patterns, stack traces,
and relevant excerpts. It also implements PII redaction.
"""

import re
from typing import Dict, List, Tuple
from collections import Counter
import logging

logger = logging.getLogger(__name__)


# PII patterns for redaction (Requirement 10.4)
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
}


def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.
    
    Args:
        text: Text that may contain PII
        
    Returns:
        Text with PII redacted
        
    Validates: Requirements 10.4
    """
    redacted_text = text
    
    # Redact emails
    redacted_text = re.sub(PII_PATTERNS['email'], '[EMAIL_REDACTED]', redacted_text)
    
    # Redact phone numbers
    redacted_text = re.sub(PII_PATTERNS['phone'], '[PHONE_REDACTED]', redacted_text)
    
    # Redact SSNs
    redacted_text = re.sub(PII_PATTERNS['ssn'], '[SSN_REDACTED]', redacted_text)
    
    # Redact credit card numbers
    redacted_text = re.sub(PII_PATTERNS['credit_card'], '[CC_REDACTED]', redacted_text)
    
    return redacted_text


def extract_error_patterns(log_content: str) -> List[Dict]:
    """
    Extract error patterns from log content using regex and frequency analysis.
    
    Args:
        log_content: Raw log content
        
    Returns:
        List of error patterns with occurrence counts
        
    Validates: Requirements 2.4, 2.5
    """
    if not log_content:
        return []
    
    # Common error patterns to look for
    error_keywords = [
        r'ERROR',
        r'FATAL',
        r'CRITICAL',
        r'Exception',
        r'Error',
        r'Failed',
        r'Timeout',
        r'Connection\s+(?:refused|timeout|failed)',
        r'Out\s+of\s+memory',
        r'Throttling',
        r'Access\s+denied',
        r'Permission\s+denied',
        r'Not\s+found',
        r'Invalid',
        r'Deployment\s+failed'
    ]
    
    # Extract error lines
    error_lines = []
    for line in log_content.split('\n'):
        for pattern in error_keywords:
            if re.search(pattern, line, re.IGNORECASE):
                error_lines.append(line.strip())
                break
    
    # Extract specific error patterns
    patterns = []
    
    # Look for common error types
    error_types = Counter()
    for line in error_lines:
        # Extract exception types (e.g., "java.net.SocketTimeoutException")
        exception_match = re.search(r'(\w+(?:\.\w+)*Exception)', line)
        if exception_match:
            error_types[exception_match.group(1)] += 1
        
        # Extract error keywords
        for keyword in ['Timeout', 'Connection', 'Memory', 'Throttling', 'Failed', 'Denied']:
            if keyword.lower() in line.lower():
                error_types[keyword] += 1
    
    # Convert to pattern list with timestamps
    for error_type, count in error_types.most_common(10):
        # Find first and last occurrence
        first_seen = None
        last_seen = None
        
        for line in log_content.split('\n'):
            if error_type.lower() in line.lower():
                # Try to extract timestamp from line
                timestamp_match = re.search(
                    r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)',
                    line
                )
                if timestamp_match:
                    timestamp = timestamp_match.group(1)
                    if first_seen is None:
                        first_seen = timestamp
                    last_seen = timestamp
        
        patterns.append({
            "pattern": error_type,
            "occurrences": count,
            "first_seen": first_seen or "unknown",
            "last_seen": last_seen or "unknown"
        })
    
    return patterns


def extract_stack_traces(log_content: str) -> List[Dict]:
    """
    Extract stack traces from log content.
    
    Args:
        log_content: Raw log content
        
    Returns:
        List of stack traces with exception details
        
    Validates: Requirements 2.4, 2.5
    """
    if not log_content:
        return []
    
    stack_traces = []
    lines = log_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for exception lines
        exception_match = re.search(
            r'(\w+(?:\.\w+)*(?:Exception|Error))(?::\s*(.+))?',
            line
        )
        
        if exception_match:
            exception_type = exception_match.group(1)
            message = exception_match.group(2) or ""
            
            # Try to find the location (file and line number)
            location = None
            
            # Look ahead for stack trace lines
            j = i + 1
            while j < len(lines) and j < i + 20:  # Look at next 20 lines max
                trace_line = lines[j]
                
                # Look for "at" or "in" patterns indicating stack trace
                location_match = re.search(
                    r'(?:at|in)\s+([^\s]+)\s*(?:\(([^)]+)\))?',
                    trace_line
                )
                if location_match and not location:
                    location = location_match.group(1)
                    if location_match.group(2):
                        location += f" ({location_match.group(2)})"
                
                # Stop if we hit a non-stack-trace line
                if not trace_line.strip().startswith(('at', 'in', '\t', ' ' * 4)):
                    break
                
                j += 1
            
            stack_traces.append({
                "exception": exception_type,
                "location": location or "unknown",
                "message": message.strip()
            })
            
            i = j
        else:
            i += 1
    
    # Remove duplicates
    unique_traces = []
    seen = set()
    for trace in stack_traces:
        key = (trace['exception'], trace['location'])
        if key not in seen:
            seen.add(key)
            unique_traces.append(trace)
    
    return unique_traces[:10]  # Return top 10


def extract_relevant_excerpts(log_content: str, max_excerpts: int = 5) -> List[str]:
    """
    Extract the most relevant log excerpts.
    
    Args:
        log_content: Raw log content
        max_excerpts: Maximum number of excerpts to return
        
    Returns:
        List of relevant log excerpts
        
    Validates: Requirements 2.5
    """
    if not log_content:
        return []
    
    # Score lines by relevance
    scored_lines = []
    
    for line in log_content.split('\n'):
        if not line.strip():
            continue
        
        score = 0
        
        # High priority keywords
        if re.search(r'ERROR|FATAL|CRITICAL', line, re.IGNORECASE):
            score += 10
        
        # Exception indicators
        if re.search(r'Exception|Error', line):
            score += 8
        
        # Failure indicators
        if re.search(r'Failed|Failure|Timeout|Denied', line, re.IGNORECASE):
            score += 6
        
        # Connection issues
        if re.search(r'Connection|Network|Socket', line, re.IGNORECASE):
            score += 5
        
        # Resource issues
        if re.search(r'Memory|CPU|Disk|Throttling', line, re.IGNORECASE):
            score += 5
        
        # Timestamps make logs more useful
        if re.search(r'\d{4}-\d{2}-\d{2}', line):
            score += 2
        
        if score > 0:
            scored_lines.append((score, line.strip()))
    
    # Sort by score and take top excerpts
    scored_lines.sort(reverse=True, key=lambda x: x[0])
    excerpts = [line for score, line in scored_lines[:max_excerpts]]
    
    return excerpts


def parse_logs(log_content: str) -> Dict:
    """
    Parse logs to extract error messages, stack traces, and patterns.
    
    Args:
        log_content: Raw log content
        
    Returns:
        Dictionary containing parsed log information
        
    Validates: Requirements 2.4, 2.5, 10.4
    """
    # Redact PII first (Requirement 10.4)
    redacted_content = redact_pii(log_content)
    
    # Extract patterns and traces
    error_patterns = extract_error_patterns(redacted_content)
    stack_traces = extract_stack_traces(redacted_content)
    relevant_excerpts = extract_relevant_excerpts(redacted_content)
    
    return {
        "error_patterns": error_patterns,
        "stack_traces": stack_traces,
        "relevant_excerpts": relevant_excerpts
    }
