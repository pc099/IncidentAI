"""
Log Analysis Agent

Basic log analysis agent for incident response system.
"""

import json
import logging
import boto3
from typing import Dict, Any
from agents.log_retrieval import retrieve_logs_from_s3, calculate_time_window
from agents.log_parser import parse_logs

logger = logging.getLogger(__name__)


class LogAnalysisAgent:
    """
    Log Analysis Agent for incident response system.
    
    Responsibilities:
    - Retrieve logs from S3 for the failure time window
    - Parse logs to extract error patterns and stack traces
    - Use Bedrock Claude to generate structured log analysis
    - Return log summary with error patterns, stack traces, and excerpts
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """
        Initialize the Log Analysis Agent.
        
        Args:
            bedrock_model_id: Bedrock model ID to use for analysis
        """
        # Lazy initialization to avoid import-time credential requirements
        self.bedrock_runtime = None
        self.model_id = bedrock_model_id
    
    def get_bedrock_client(self):
        """Get Bedrock client with lazy initialization"""
        if self.bedrock_runtime is None:
            self.bedrock_runtime = boto3.client('bedrock-runtime')
        return self.bedrock_runtime
    
    def analyze(
        self,
        service_name: str,
        timestamp: str,
        log_location: str
    ) -> Dict[str, Any]:
        """
        Analyze logs for the given incident
        
        Args:
            service_name: Name of the failed service
            timestamp: Failure timestamp
            log_location: S3 location of logs
            
        Returns:
            Log analysis results
        """
        try:
            # Calculate time window
            start_time, end_time = calculate_time_window(timestamp)
            
            # Extract bucket and prefix from S3 location
            if log_location.startswith("s3://"):
                s3_parts = log_location.replace("s3://", "").split("/", 1)
                bucket_name = s3_parts[0]
                key_prefix = s3_parts[1] if len(s3_parts) > 1 else ""
            else:
                raise ValueError(f"Invalid S3 location: {log_location}")
            
            # Retrieve logs
            log_content = retrieve_logs_from_s3(
                bucket_name=bucket_name,
                key_prefix=key_prefix,
                start_time=start_time,
                end_time=end_time
            )
            
            # Parse logs
            parsed_data = parse_logs(log_content)
            
            # Generate analysis using Bedrock
            analysis_prompt = self._create_analysis_prompt(
                service_name, timestamp, log_content, parsed_data
            )
            
            bedrock_response = self._invoke_bedrock(analysis_prompt)
            
            # Combine parsed data with Bedrock analysis
            result = {
                "agent": "log_analysis",
                "service_name": service_name,
                "timestamp": timestamp,
                "log_location": log_location,
                "error_patterns": parsed_data.get("error_patterns", []),
                "stack_traces": parsed_data.get("stack_traces", []),
                "log_levels": parsed_data.get("log_levels", []),
                "bedrock_analysis": bedrock_response,
                "confidence_score": self._calculate_confidence_score(parsed_data, bedrock_response),
                "log_summary": {
                    "total_lines": parsed_data.get("parsing_metadata", {}).get("total_lines", 0),
                    "error_count": len(parsed_data.get("error_patterns", [])),
                    "stack_trace_count": len(parsed_data.get("stack_traces", []))
                }
            }
            
            logger.info(f"Log analysis completed for {service_name}")
            return result
            
        except Exception as e:
            logger.error(f"Log analysis failed: {str(e)}")
            return {
                "agent": "log_analysis",
                "service_name": service_name,
                "timestamp": timestamp,
                "error": str(e),
                "confidence_score": 0,
                "error_patterns": [],
                "stack_traces": []
            }
    
    def _create_analysis_prompt(
        self,
        service_name: str,
        timestamp: str,
        log_content: str,
        parsed_data: Dict[str, Any]
    ) -> str:
        """Create the Bedrock prompt for log analysis"""
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
1. Key error patterns and their significance
2. Root cause indicators from stack traces
3. Timeline of events leading to failure
4. Severity assessment
5. Recommended next steps

Format your response as JSON with the following structure:
{{
    "key_findings": ["finding1", "finding2", ...],
    "root_cause_indicators": ["indicator1", "indicator2", ...],
    "timeline": ["event1", "event2", ...],
    "severity": "low|medium|high|critical",
    "recommendations": ["rec1", "rec2", ...],
    "confidence_score": 0-100
}}"""
        
        return prompt
    
    def _invoke_bedrock(self, prompt: str) -> Dict[str, Any]:
        """Invoke Bedrock model for analysis"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            bedrock_runtime = self.get_bedrock_client()
            response = bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "analysis_text": content,
                    "confidence_score": 60
                }
                
        except Exception as e:
            logger.error(f"Bedrock invocation failed: {str(e)}")
            return {
                "error": str(e),
                "confidence_score": 0
            }
    
    def _calculate_confidence_score(
        self, 
        parsed_data: Dict[str, Any], 
        bedrock_response: Dict[str, Any]
    ) -> int:
        """Calculate confidence score for the analysis"""
        score = 0
        
        # Base score from parsed data
        if parsed_data.get("error_patterns"):
            score += 30
        if parsed_data.get("stack_traces"):
            score += 20
        if not parsed_data.get("parsing_error"):
            score += 10
        
        # Score from Bedrock analysis
        bedrock_confidence = bedrock_response.get("confidence_score", 0)
        if bedrock_confidence > 0:
            score += min(40, bedrock_confidence * 0.4)
        
        return min(100, score)