"""
Log Analysis Agent

This agent retrieves and analyzes logs to identify error patterns.
It integrates with Amazon Bedrock Claude for intelligent log analysis.
"""

import boto3
import json
import logging
from typing import Dict
from .log_retrieval import retrieve_logs_from_s3, calculate_time_window
from .log_parser import parse_logs

logger = logging.getLogger(__name__)


class LogAnalysisAgent:
    """
    Log Analysis Agent for incident response system.
    
    Responsibilities:
    - Retrieve logs from S3 for the failure time window
    - Parse logs to extract error patterns and stack traces
    - Use Bedrock Claude to generate structured log analysis
    - Return log summary with error patterns, stack traces, and excerpts
    
    Validates: Requirements 2.1-2.7, 10.4
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """
        Initialize the Log Analysis Agent.
        
        Args:
            bedrock_model_id: Bedrock model ID to use for analysis
        """
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.model_id = bedrock_model_id
    
    def _create_analysis_prompt(
        self,
        service_name: str,
        timestamp: str,
        log_content: str,
        parsed_data: Dict
    ) -> str:
        """
        Create the Bedrock prompt for log analysis.
        
        Args:
            service_name: Name of the failed service
            timestamp: Failure timestamp
            log_content: Raw log content (truncated if needed)
            parsed_data: Pre-parsed error patterns and stack traces
            
        Returns:
            Formatted prompt string
        """
        # Truncate log content for prompt if too long
        max_log_chars = 8000
        truncated_logs = log_content[:max_log_chars]
        if len(log_content) > max_log_chars:
            truncated_logs += "\n... (logs truncated for analysis)"
        
        prompt = f"""Analyze the following logs from a failed service and identify error patterns:

Service: {service_name}
Failure Time: {timestamp}

Pre-identified Error Patterns:
{json.dumps(parsed_data.get('error_patterns', []), indent=2)}

Pre-identified Stack Traces:
{json.dumps(parsed_data.get('stack_traces', []), indent=2)}

Log Content:
{truncated_logs}

Provide a structured analysis with:
1. Primary error patterns with occurrence counts
2. Stack traces if present (exception type, location, message)
3. Most relevant log excerpts (max 5)
4. Any anomalies or unusual patterns

Format your response as valid JSON with this structure:
{{
  "error_patterns": [
    {{
      "pattern": "string",
      "occurrences": number,
      "first_seen": "ISO8601 timestamp",
      "last_seen": "ISO8601 timestamp"
    }}
  ],
  "stack_traces": [
    {{
      "exception": "string",
      "location": "string",
      "message": "string"
    }}
  ],
  "relevant_excerpts": ["string"],
  "anomalies": ["string"],
  "summary": "Brief summary of the log analysis"
}}

Respond ONLY with valid JSON, no additional text."""
        
        return prompt
    
    def _invoke_bedrock(self, prompt: str) -> Dict:
        """
        Invoke Bedrock Claude model for log analysis.
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            Parsed JSON response from Claude
            
        Raises:
            Exception if Bedrock invocation fails
        """
        try:
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1  # Low temperature for consistent analysis
            }
            
            # Invoke Bedrock
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract content from Claude response
            content = response_body.get('content', [])
            if content and len(content) > 0:
                text_content = content[0].get('text', '{}')
            else:
                text_content = '{}'
            
            # Parse JSON from response
            try:
                analysis_result = json.loads(text_content)
            except json.JSONDecodeError:
                # If Claude didn't return valid JSON, extract what we can
                logger.warning("Claude response was not valid JSON, using fallback")
                analysis_result = {
                    "error_patterns": [],
                    "stack_traces": [],
                    "relevant_excerpts": [],
                    "anomalies": [],
                    "summary": text_content[:500]
                }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock: {str(e)}")
            raise
    
    def analyze(
        self,
        log_location: str,
        timestamp: str,
        service_name: str
    ) -> Dict:
        """
        Analyze logs for the given incident.
        
        Args:
            log_location: S3 URI of the log file
            timestamp: ISO 8601 formatted failure timestamp
            service_name: Name of the failed service
            
        Returns:
            Dictionary containing log analysis results:
            - agent: "log-analysis"
            - summary: Structured log analysis
            - status: "success" or "failed"
            
        Validates: Requirements 2.1-2.7, 10.4
        """
        try:
            logger.info(f"Starting log analysis for {service_name} at {timestamp}")
            
            # Step 1: Retrieve logs from S3 (Requirements 2.1, 2.2, 2.3, 2.7)
            log_data = retrieve_logs_from_s3(log_location, timestamp, service_name)
            
            # Check if logs were found
            if log_data.get('confidence_score') == 0:
                logger.warning(f"Logs not found for {service_name}")
                return {
                    "agent": "log-analysis",
                    "status": "failed",
                    "summary": {
                        "error_patterns": [],
                        "stack_traces": [],
                        "relevant_excerpts": [],
                        "log_volume": "0 MB",
                        "time_range": log_data.get('time_range', 'unknown'),
                        "error": log_data.get('error', 'Logs not available')
                    },
                    "confidence_score": 0
                }
            
            log_content = log_data['log_content']
            
            # Step 2: Parse logs (Requirements 2.4, 2.5, 10.4)
            parsed_data = parse_logs(log_content)
            
            # Step 3: Use Bedrock for enhanced analysis (Requirement 2.6)
            try:
                prompt = self._create_analysis_prompt(
                    service_name,
                    timestamp,
                    log_content,
                    parsed_data
                )
                
                bedrock_analysis = self._invoke_bedrock(prompt)
                
                # Merge parsed data with Bedrock analysis
                # Prefer Bedrock results but fall back to parsed data
                final_analysis = {
                    "error_patterns": bedrock_analysis.get('error_patterns') or parsed_data['error_patterns'],
                    "stack_traces": bedrock_analysis.get('stack_traces') or parsed_data['stack_traces'],
                    "relevant_excerpts": bedrock_analysis.get('relevant_excerpts') or parsed_data['relevant_excerpts'],
                    "anomalies": bedrock_analysis.get('anomalies', []),
                    "summary": bedrock_analysis.get('summary', 'Log analysis completed'),
                    "log_volume": log_data['log_volume'],
                    "time_range": log_data['time_range'],
                    "truncated": log_data.get('truncated', False)
                }
                
            except Exception as bedrock_error:
                logger.warning(f"Bedrock analysis failed, using parsed data: {str(bedrock_error)}")
                # Fall back to parsed data if Bedrock fails
                final_analysis = {
                    "error_patterns": parsed_data['error_patterns'],
                    "stack_traces": parsed_data['stack_traces'],
                    "relevant_excerpts": parsed_data['relevant_excerpts'],
                    "anomalies": [],
                    "summary": "Log analysis completed (Bedrock unavailable)",
                    "log_volume": log_data['log_volume'],
                    "time_range": log_data['time_range'],
                    "truncated": log_data.get('truncated', False)
                }
            
            logger.info(f"Log analysis completed for {service_name}")
            
            return {
                "agent": "log-analysis",
                "status": "success",
                "summary": final_analysis
            }
            
        except Exception as e:
            logger.error(f"Log analysis failed: {str(e)}")
            return {
                "agent": "log-analysis",
                "status": "failed",
                "error": str(e),
                "summary": {
                    "error_patterns": [],
                    "stack_traces": [],
                    "relevant_excerpts": [],
                    "log_volume": "0 MB",
                    "time_range": "unknown"
                }
            }
