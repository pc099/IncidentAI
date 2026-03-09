#!/usr/bin/env python3
"""
Root cause classification logic for Root Cause Agent.

This module provides functionality to:
- Classify failures into: configuration_error, resource_exhaustion, dependency_failure
- Calculate confidence scores (pattern clarity 40%, historical match 30%, evidence strength 30%)
- Rank alternative causes by confidence score
- Integrate with Bedrock Claude for AI-powered root cause analysis

Requirements: 3.1, 3.2, 3.3, 3.4, 3.7
"""

import json
import logging
import os
import re
from typing import Dict, List, Tuple, Optional
from enum import Enum
import boto3

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """Failure category enumeration."""
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"


# Pattern definitions for each failure category
CATEGORY_PATTERNS = {
    FailureCategory.CONFIGURATION_ERROR: [
        r"configuration",
        r"config",
        r"environment variable",
        r"missing parameter",
        r"invalid.*value",
        r"permission.*denied",
        r"iam.*role",
        r"access.*denied",
        r"unauthorized",
        r"authentication.*failed",
        r"deployment.*failed",
        r"invalid.*json",
        r"syntax.*error",
        r"malformed",
        r"not.*verified",
        r"invalid.*path",
    ],
    FailureCategory.RESOURCE_EXHAUSTION: [
        r"memory",
        r"out.*of.*memory",
        r"oom",
        r"throttl",
        r"capacity",
        r"limit.*reached",
        r"limit.*exceeded",
        r"quota",
        r"storage.*full",
        r"disk.*full",
        r"cpu",
        r"concurrent.*execution",
        r"provisioned.*throughput",
        r"rate.*limit",
    ],
    FailureCategory.DEPENDENCY_FAILURE: [
        r"timeout",
        r"timed.*out",
        r"connection.*failed",
        r"connection.*refused",
        r"connection.*reset",
        r"network",
        r"unreachable",
        r"unavailable",
        r"service.*down",
        r"endpoint",
        r"external.*api",
        r"third.*party",
        r"gateway",
        r"database.*connection",
        r"pool.*exhaustion",
        r"eventual.*consistency",
    ],
}


def classify_failure(
    error_message: str,
    log_summary: Optional[Dict] = None,
    similar_incidents: Optional[List[Dict]] = None
) -> Tuple[FailureCategory, List[Tuple[FailureCategory, int]]]:
    """
    Classify failure into one of three categories and provide alternative causes.
    
    Args:
        error_message: Error message from the incident
        log_summary: Optional log analysis summary containing error patterns
        similar_incidents: Optional list of similar past incidents from Knowledge Base
    
    Returns:
        Tuple containing:
        - Primary failure category
        - List of (category, confidence_score) tuples for all categories, sorted by confidence
    
    Example:
        >>> classify_failure(
        ...     "Lambda deployment failed: missing DATABASE_URL",
        ...     {"error_patterns": [{"pattern": "EnvironmentVariableError"}]}
        ... )
        (FailureCategory.CONFIGURATION_ERROR, [
            (FailureCategory.CONFIGURATION_ERROR, 85),
            (FailureCategory.DEPENDENCY_FAILURE, 25),
            (FailureCategory.RESOURCE_EXHAUSTION, 10)
        ])
    """
    # Calculate confidence scores for each category
    category_scores = {}
    
    for category in FailureCategory:
        confidence = calculate_confidence_score(
            category=category,
            error_message=error_message,
            log_summary=log_summary,
            similar_incidents=similar_incidents
        )
        category_scores[category] = confidence
    
    # Sort by confidence score (descending)
    ranked_categories = sorted(
        category_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Primary cause is the highest confidence
    primary_category = ranked_categories[0][0]
    
    logger.info(
        f"Classified failure as {primary_category.value} "
        f"with confidence {ranked_categories[0][1]}"
    )
    
    return primary_category, ranked_categories


def calculate_confidence_score(
    category: FailureCategory,
    error_message: str,
    log_summary: Optional[Dict] = None,
    similar_incidents: Optional[List[Dict]] = None
) -> int:
    """
    Calculate confidence score for a specific failure category.
    
    Confidence score formula:
    - Pattern clarity: 40% weight
    - Historical match: 30% weight
    - Evidence strength: 30% weight
    
    Args:
        category: Failure category to score
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
        similar_incidents: Optional list of similar past incidents
    
    Returns:
        int: Confidence score between 0 and 100
    
    Example:
        >>> calculate_confidence_score(
        ...     FailureCategory.CONFIGURATION_ERROR,
        ...     "Missing environment variable DATABASE_URL",
        ...     {"error_patterns": [{"pattern": "EnvironmentVariableError"}]}
        ... )
        85
    """
    # Calculate pattern clarity (0-100)
    pattern_clarity = calculate_pattern_clarity(
        category=category,
        error_message=error_message,
        log_summary=log_summary
    )
    
    # Calculate historical match (0-100)
    historical_match = calculate_historical_match(
        category=category,
        similar_incidents=similar_incidents
    )
    
    # Calculate evidence strength (0-100)
    evidence_strength = calculate_evidence_strength(
        category=category,
        error_message=error_message,
        log_summary=log_summary
    )
    
    # Weighted average
    confidence = (
        pattern_clarity * 0.4 +
        historical_match * 0.3 +
        evidence_strength * 0.3
    )
    
    # Round to integer
    confidence = round(confidence)
    
    # Ensure bounds [0, 100]
    confidence = max(0, min(100, confidence))
    
    logger.debug(
        f"Confidence for {category.value}: {confidence} "
        f"(pattern={pattern_clarity}, historical={historical_match}, "
        f"evidence={evidence_strength})"
    )
    
    return confidence


def calculate_pattern_clarity(
    category: FailureCategory,
    error_message: str,
    log_summary: Optional[Dict] = None
) -> float:
    """
    Calculate pattern clarity score (0-100) based on how clearly the error
    patterns match the category.
    
    Args:
        category: Failure category to score
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
    
    Returns:
        float: Pattern clarity score (0-100)
    """
    patterns = CATEGORY_PATTERNS[category]
    
    # Combine error message and log patterns for analysis
    text_to_analyze = error_message.lower()
    
    if log_summary and "error_patterns" in log_summary:
        for pattern_info in log_summary["error_patterns"]:
            if isinstance(pattern_info, dict):
                pattern = pattern_info.get("pattern", "")
            else:
                pattern = str(pattern_info)
            text_to_analyze += " " + pattern.lower()
    
    # Count pattern matches
    matches = 0
    total_patterns = len(patterns)
    
    for pattern in patterns:
        if re.search(pattern, text_to_analyze, re.IGNORECASE):
            matches += 1
    
    # Calculate score based on match ratio
    if matches == 0:
        return 0.0
    
    # Score increases with more matches
    # 1 match = 70, 2 matches = 85, 3+ matches = 95+
    if matches == 1:
        score = 70.0
    elif matches == 2:
        score = 85.0
    elif matches == 3:
        score = 92.0
    else:
        # Cap at 98 for pattern clarity alone
        score = min(98.0, 92.0 + (matches - 3) * 2.0)
    
    return score


def calculate_historical_match(
    category: FailureCategory,
    similar_incidents: Optional[List[Dict]] = None
) -> float:
    """
    Calculate historical match score (0-100) based on similar past incidents.
    
    Args:
        category: Failure category to score
        similar_incidents: Optional list of similar past incidents
    
    Returns:
        float: Historical match score (0-100)
    """
    if not similar_incidents:
        # No historical data = neutral score
        return 50.0
    
    # Count incidents matching this category
    matching_incidents = 0
    total_similarity = 0.0
    
    for incident in similar_incidents:
        incident_category = incident.get("failure_type", "")
        
        # Also check root_cause for category information
        root_cause = incident.get("root_cause", "")
        if isinstance(root_cause, dict):
            incident_category = root_cause.get("category", incident_category)
        
        # Check if this incident matches the category
        if incident_category == category.value:
            matching_incidents += 1
            # Weight by similarity score
            similarity = incident.get("similarity_score", 0.5)
            total_similarity += similarity
    
    if matching_incidents == 0:
        # No matching historical incidents = lower score
        return 30.0
    
    # Calculate score based on:
    # 1. Proportion of matching incidents
    # 2. Average similarity score of matching incidents
    match_ratio = matching_incidents / len(similar_incidents)
    avg_similarity = total_similarity / matching_incidents
    
    # Score formula: weighted combination
    score = (match_ratio * 50.0) + (avg_similarity * 50.0)
    
    return score


def calculate_evidence_strength(
    category: FailureCategory,
    error_message: str,
    log_summary: Optional[Dict] = None
) -> float:
    """
    Calculate evidence strength score (0-100) based on the quality and
    quantity of supporting evidence.
    
    Args:
        category: Failure category to score
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
    
    Returns:
        float: Evidence strength score (0-100)
    """
    evidence_score = 0.0
    
    # Base score from error message presence
    if error_message and len(error_message.strip()) > 0:
        evidence_score += 25.0
    
    if not log_summary:
        return evidence_score
    
    # Score from error patterns
    error_patterns = log_summary.get("error_patterns", [])
    if error_patterns:
        # More patterns = stronger evidence (up to 35 points)
        pattern_count = len(error_patterns)
        evidence_score += min(35.0, pattern_count * 15.0)
    
    # Score from stack traces
    stack_traces = log_summary.get("stack_traces", [])
    if stack_traces:
        # Stack traces provide strong evidence (25 points)
        evidence_score += 25.0
    
    # Score from relevant excerpts
    relevant_excerpts = log_summary.get("relevant_excerpts", [])
    if relevant_excerpts:
        # Log excerpts provide supporting evidence (20 points)
        evidence_score += 20.0
    
    # Score from occurrence frequency (for patterns)
    if error_patterns:
        for pattern_info in error_patterns:
            if isinstance(pattern_info, dict):
                occurrences = pattern_info.get("occurrences", 0)
                if occurrences > 5:
                    # High frequency = stronger evidence (up to 20 points)
                    evidence_score += min(20.0, (occurrences / 5.0) * 5.0)
                    break  # Only count once
    
    # Cap at 100
    evidence_score = min(100.0, evidence_score)
    
    return evidence_score


def format_root_cause_analysis(
    primary_category: FailureCategory,
    ranked_categories: List[Tuple[FailureCategory, int]],
    error_message: str,
    log_summary: Optional[Dict] = None,
    similar_incidents: Optional[List[Dict]] = None
) -> Dict:
    """
    Format root cause analysis results into structured output.
    
    Args:
        primary_category: Primary failure category
        ranked_categories: List of (category, confidence) tuples
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
        similar_incidents: Optional list of similar past incidents
    
    Returns:
        Dict: Structured root cause analysis output
    
    Example:
        >>> format_root_cause_analysis(
        ...     FailureCategory.CONFIGURATION_ERROR,
        ...     [(FailureCategory.CONFIGURATION_ERROR, 85)],
        ...     "Missing DATABASE_URL"
        ... )
        {
            "primary_cause": {
                "category": "configuration_error",
                "description": "Configuration error detected",
                "confidence_score": 85,
                "evidence": [...]
            },
            "alternative_causes": [...]
        }
    """
    # Extract evidence from log summary
    evidence = []
    if error_message:
        evidence.append(f"Error message: {error_message}")
    
    if log_summary:
        error_patterns = log_summary.get("error_patterns", [])
        if error_patterns:
            for pattern_info in error_patterns:
                if isinstance(pattern_info, dict):
                    pattern = pattern_info.get("pattern", "")
                    occurrences = pattern_info.get("occurrences", 0)
                    evidence.append(
                        f"{occurrences} occurrences of {pattern}"
                    )
                else:
                    evidence.append(f"Pattern: {pattern_info}")
    
    # Generate description based on category
    descriptions = {
        FailureCategory.CONFIGURATION_ERROR: 
            "Configuration error: Invalid config values, missing parameters, or permission issues",
        FailureCategory.RESOURCE_EXHAUSTION:
            "Resource exhaustion: Memory, CPU, disk space, or capacity limits exceeded",
        FailureCategory.DEPENDENCY_FAILURE:
            "Dependency failure: External service timeout, connection failure, or unavailability"
    }
    
    # Primary cause
    primary_confidence = ranked_categories[0][1]
    primary_cause = {
        "category": primary_category.value,
        "description": descriptions[primary_category],
        "confidence_score": primary_confidence,
        "evidence": evidence[:5]  # Limit to top 5 evidence items
    }
    
    # Alternative causes (exclude primary)
    alternative_causes = []
    for category, confidence in ranked_categories[1:]:
        alternative_causes.append({
            "category": category.value,
            "description": descriptions[category],
            "confidence_score": confidence,
            "evidence": []  # Alternative causes don't need detailed evidence
        })
    
    # Format similar incidents
    formatted_similar = []
    if similar_incidents:
        for incident in similar_incidents[:3]:  # Top 3 most similar
            formatted_similar.append({
                "incident_id": incident.get("incident_id", "unknown"),
                "similarity_score": incident.get("similarity_score", 0.0),
                "resolution": incident.get("resolution", ""),
                "root_cause": incident.get("root_cause", "")
            })
    
    return {
        "primary_cause": primary_cause,
        "alternative_causes": alternative_causes,
        "similar_incidents": formatted_similar
    }



class BedrockRootCauseAnalyzer:
    """
    Bedrock Claude integration for AI-powered root cause analysis.
    
    This class provides:
    - Bedrock prompt template creation with similar incidents from Knowledge Base
    - Claude model invocation with log summary and historical context
    - Structured JSON response parsing with primary cause, confidence, evidence, alternatives
    
    Requirements: 3.1, 3.7
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
        """
        Initialize Bedrock root cause analyzer.
        
        Args:
            bedrock_model_id: Bedrock model ID to use for analysis
        """
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.model_id = bedrock_model_id
    
    def create_prompt(
        self,
        service_name: str,
        error_message: str,
        log_summary: Dict,
        similar_incidents: Optional[List[Dict]] = None
    ) -> str:
        """
        Create Bedrock prompt template including similar incidents from Knowledge Base.
        
        Args:
            service_name: Name of the failed service
            error_message: Error message from the incident
            log_summary: Log analysis summary containing error patterns, stack traces, excerpts
            similar_incidents: Optional list of similar past incidents from Knowledge Base
        
        Returns:
            str: Formatted prompt for Claude model
        
        Example:
            >>> analyzer = BedrockRootCauseAnalyzer()
            >>> prompt = analyzer.create_prompt(
            ...     "payment-processor",
            ...     "Connection timeout",
            ...     {"error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}]},
            ...     [{"incident_id": "inc-001", "resolution": "Increased timeout"}]
            ... )
        """
        # Format error patterns
        error_patterns_text = ""
        if log_summary.get("error_patterns"):
            error_patterns_text = "\n".join([
                f"  - {p.get('pattern', p)}: {p.get('occurrences', 'N/A')} occurrences"
                if isinstance(p, dict) else f"  - {p}"
                for p in log_summary["error_patterns"]
            ])
        
        # Format stack traces
        stack_traces_text = ""
        if log_summary.get("stack_traces"):
            stack_traces_text = "\n".join([
                f"  - {st.get('exception', 'Unknown')}: {st.get('message', '')}"
                if isinstance(st, dict) else f"  - {st}"
                for st in log_summary["stack_traces"][:3]  # Limit to top 3
            ])
        
        # Format relevant excerpts
        excerpts_text = ""
        if log_summary.get("relevant_excerpts"):
            excerpts_text = "\n".join([
                f"  - {excerpt}"
                for excerpt in log_summary["relevant_excerpts"][:5]  # Limit to top 5
            ])
        
        # Format similar incidents from Knowledge Base
        similar_incidents_text = ""
        if similar_incidents:
            similar_incidents_text = "\n\nSimilar Past Incidents (from Knowledge Base):\n"
            similar_incidents_text += "These similar incidents were retrieved using semantic search. Pay special attention to:\n"
            similar_incidents_text += "- How these past incidents were resolved\n"
            similar_incidents_text += "- Common patterns between current and past incidents\n"
            similar_incidents_text += "- Root causes identified in similar scenarios\n\n"
            
            for idx, incident in enumerate(similar_incidents[:5], 1):  # Top 5
                similarity_score = incident.get("similarity_score", 0.0)
                incident_id = incident.get("incident_id", "unknown")
                root_cause = incident.get("root_cause", "")
                resolution = incident.get("resolution", "")
                
                # Handle root_cause as dict or string
                if isinstance(root_cause, dict):
                    root_cause_text = root_cause.get("description", root_cause.get("category", ""))
                else:
                    root_cause_text = str(root_cause)
                
                # Handle resolution as dict or string
                if isinstance(resolution, dict):
                    resolution_text = resolution.get("action", str(resolution))
                else:
                    resolution_text = str(resolution)
                
                similar_incidents_text += f"{idx}. Incident {incident_id} (similarity: {similarity_score:.0%})\n"
                similar_incidents_text += f"   Root Cause: {root_cause_text}\n"
                similar_incidents_text += f"   Resolution: {resolution_text}\n\n"
        
        # Create the prompt
        prompt = f"""You are a root cause analysis expert. Analyze this incident:

Service: {service_name}
Error: {error_message}

Log Analysis:
Error Patterns:
{error_patterns_text or "  None detected"}

Stack Traces:
{stack_traces_text or "  None found"}

Relevant Log Excerpts:
{excerpts_text or "  None available"}
{similar_incidents_text}
Classify the root cause into one of:
- configuration_error: Invalid config values, missing parameters, permission issues
- resource_exhaustion: Memory, CPU, disk space, capacity limits exceeded
- dependency_failure: External service timeouts, database connection failures, network issues

Provide your analysis in the following JSON format:
{{
  "primary_cause": {{
    "category": "configuration_error|resource_exhaustion|dependency_failure",
    "description": "Detailed description of the root cause",
    "confidence_score": 85,
    "evidence": [
      "Evidence item 1",
      "Evidence item 2",
      "Evidence item 3"
    ]
  }},
  "alternative_causes": [
    {{
      "category": "category_name",
      "description": "Description of alternative cause",
      "confidence_score": 35,
      "evidence": ["Supporting evidence"]
    }}
  ]
}}

Important:
- Confidence scores must be between 0 and 100
- Primary cause should have the highest confidence
- Include 1-3 alternative causes if applicable
- Base your analysis on the log patterns and similar incidents
- If similar incidents exist, incorporate their resolutions into your confidence scoring"""

        return prompt
    
    def invoke_claude(
        self,
        service_name: str,
        error_message: str,
        log_summary: Dict,
        similar_incidents: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Invoke Claude model with log summary and historical context.
        
        Args:
            service_name: Name of the failed service
            error_message: Error message from the incident
            log_summary: Log analysis summary
            similar_incidents: Optional list of similar past incidents
        
        Returns:
            Dict: Parsed structured JSON response with primary cause, confidence, evidence, alternatives
        
        Raises:
            Exception: If Bedrock invocation fails
        
        Example:
            >>> analyzer = BedrockRootCauseAnalyzer()
            >>> result = analyzer.invoke_claude(
            ...     "payment-processor",
            ...     "Connection timeout",
            ...     {"error_patterns": [{"pattern": "TimeoutException"}]},
            ...     [{"incident_id": "inc-001", "resolution": "Increased timeout"}]
            ... )
            >>> result["primary_cause"]["category"]
            'dependency_failure'
        """
        try:
            # Create prompt
            prompt = self.create_prompt(
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary,
                similar_incidents=similar_incidents
            )
            
            logger.info(f"Invoking Bedrock Claude for root cause analysis of {service_name}")
            
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
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
                # If Claude didn't return valid JSON, use fallback
                logger.warning("Claude response was not valid JSON, using fallback classification")
                # Use rule-based classification as fallback
                primary_category, ranked_categories = classify_failure(
                    error_message=error_message,
                    log_summary=log_summary,
                    similar_incidents=similar_incidents
                )
                analysis_result = format_root_cause_analysis(
                    primary_category=primary_category,
                    ranked_categories=ranked_categories,
                    error_message=error_message,
                    log_summary=log_summary,
                    similar_incidents=similar_incidents
                )
            
            # Validate and normalize the response
            analysis_result = self._validate_and_normalize_response(analysis_result)
            
            logger.info(
                f"Root cause analysis complete: {analysis_result['primary_cause']['category']} "
                f"with {analysis_result['primary_cause']['confidence_score']}% confidence"
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock: {str(e)}")
            raise
    
    def _validate_and_normalize_response(self, response: Dict) -> Dict:
        """
        Validate and normalize Claude's response to ensure it meets requirements.
        
        Args:
            response: Raw response from Claude
        
        Returns:
            Dict: Validated and normalized response
        """
        # Ensure primary_cause exists
        if "primary_cause" not in response:
            raise ValueError("Response missing 'primary_cause' field")
        
        primary = response["primary_cause"]
        
        # Validate category
        valid_categories = ["configuration_error", "resource_exhaustion", "dependency_failure"]
        if primary.get("category") not in valid_categories:
            logger.warning(f"Invalid category: {primary.get('category')}, defaulting to dependency_failure")
            primary["category"] = "dependency_failure"
        
        # Validate confidence score bounds (0-100)
        confidence = primary.get("confidence_score", 50)
        if not isinstance(confidence, (int, float)):
            confidence = 50
        primary["confidence_score"] = max(0, min(100, int(confidence)))
        
        # Ensure evidence is a list
        if "evidence" not in primary or not isinstance(primary["evidence"], list):
            primary["evidence"] = []
        
        # Ensure description exists
        if "description" not in primary:
            primary["description"] = f"{primary['category'].replace('_', ' ').title()} detected"
        
        # Validate alternative causes
        if "alternative_causes" not in response:
            response["alternative_causes"] = []
        
        for alt in response["alternative_causes"]:
            if alt.get("category") not in valid_categories:
                alt["category"] = "dependency_failure"
            
            confidence = alt.get("confidence_score", 0)
            if not isinstance(confidence, (int, float)):
                confidence = 0
            alt["confidence_score"] = max(0, min(100, int(confidence)))
            
            if "evidence" not in alt or not isinstance(alt["evidence"], list):
                alt["evidence"] = []
            
            if "description" not in alt:
                alt["description"] = f"{alt['category'].replace('_', ' ').title()}"
        
        return response
    
    def analyze_with_bedrock(
        self,
        service_name: str,
        error_message: str,
        log_summary: Dict,
        similar_incidents: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Perform complete root cause analysis using Bedrock Claude.
        
        This is the main entry point that combines prompt creation, Claude invocation,
        and response parsing into a single operation.
        
        Args:
            service_name: Name of the failed service
            error_message: Error message from the incident
            log_summary: Log analysis summary
            similar_incidents: Optional list of similar past incidents from Knowledge Base
        
        Returns:
            Dict: Complete root cause analysis with primary cause, alternatives, and similar incidents
        
        Example:
            >>> analyzer = BedrockRootCauseAnalyzer()
            >>> result = analyzer.analyze_with_bedrock(
            ...     service_name="payment-processor",
            ...     error_message="Connection timeout to payment-gateway.example.com",
            ...     log_summary={
            ...         "error_patterns": [{"pattern": "TimeoutException", "occurrences": 15}],
            ...         "stack_traces": [],
            ...         "relevant_excerpts": ["ERROR: Connection timeout after 10s"]
            ...     },
            ...     similar_incidents=[{
            ...         "incident_id": "inc-2024-11-23-001",
            ...         "similarity_score": 0.78,
            ...         "resolution": "Increased timeout threshold to 30s",
            ...         "root_cause": "Payment gateway timeout"
            ...     }]
            ... )
            >>> result["primary_cause"]["category"]
            'dependency_failure'
            >>> result["primary_cause"]["confidence_score"] >= 0
            True
            >>> result["primary_cause"]["confidence_score"] <= 100
            True
        """
        try:
            # Invoke Claude for AI-powered analysis
            analysis_result = self.invoke_claude(
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary,
                similar_incidents=similar_incidents
            )
            
            # Add similar incidents to the result if provided
            if similar_incidents:
                # Format similar incidents for output
                formatted_similar = []
                for incident in similar_incidents[:3]:  # Top 3 most similar
                    formatted_similar.append({
                        "incident_id": incident.get("incident_id", "unknown"),
                        "similarity_score": incident.get("similarity_score", 0.0),
                        "resolution": incident.get("resolution", ""),
                        "root_cause": incident.get("root_cause", "")
                    })
                analysis_result["similar_incidents"] = formatted_similar
            else:
                analysis_result["similar_incidents"] = []
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Bedrock analysis failed: {str(e)}, falling back to rule-based classification")
            
            # Fallback to rule-based classification
            primary_category, ranked_categories = classify_failure(
                error_message=error_message,
                log_summary=log_summary,
                similar_incidents=similar_incidents
            )
            
            return format_root_cause_analysis(
                primary_category=primary_category,
                ranked_categories=ranked_categories,
                error_message=error_message,
                log_summary=log_summary,
                similar_incidents=similar_incidents
            )
