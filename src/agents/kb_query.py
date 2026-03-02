#!/usr/bin/env python3
"""
Bedrock Knowledge Base query module for Root Cause Agent.

This module provides functionality to:
- Convert current incident to query text
- Query Knowledge Base using bedrock-agent-runtime.retrieve()
- Extract top 5 similar incidents with similarity scores
- Parse incident metadata (incident_id, root_cause, resolution)

Requirements: 3.5, 3.6
"""

import logging
from typing import Dict, List, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def convert_incident_to_query(
    service_name: str,
    error_message: str,
    log_summary: Optional[Dict] = None
) -> str:
    """
    Convert current incident to query text for Knowledge Base search.
    
    Args:
        service_name: Name of the service that failed
        error_message: Error message from the incident
        log_summary: Optional log analysis summary containing error patterns
    
    Returns:
        str: Query text optimized for semantic search
    
    Example:
        >>> convert_incident_to_query(
        ...     "payment-processor",
        ...     "Service health check failed",
        ...     {"error_patterns": [{"pattern": "ConnectionTimeout"}]}
        ... )
        'Service: payment-processor\\nError: Service health check failed\\nPatterns: ConnectionTimeout'
    """
    query_parts = [
        f"Service: {service_name}",
        f"Error: {error_message}"
    ]
    
    # Add error patterns if available
    if log_summary and "error_patterns" in log_summary:
        patterns = []
        for pattern_info in log_summary["error_patterns"]:
            if isinstance(pattern_info, dict):
                patterns.append(pattern_info.get("pattern", ""))
            else:
                patterns.append(str(pattern_info))
        
        if patterns:
            query_parts.append(f"Patterns: {', '.join(patterns)}")
    
    query_text = "\n".join(query_parts)
    logger.debug(f"Generated query text: {query_text}")
    
    return query_text


def query_similar_incidents(
    knowledge_base_id: str,
    service_name: str,
    error_message: str,
    log_summary: Optional[Dict] = None,
    max_results: int = 5,
    similarity_threshold: float = 0.6,
    region_name: str = "us-east-1"
) -> List[Dict]:
    """
    Query Bedrock Knowledge Base for similar past incidents.
    
    Args:
        knowledge_base_id: ID of the Bedrock Knowledge Base
        service_name: Name of the service that failed
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
        max_results: Maximum number of results to return (default: 5)
        similarity_threshold: Minimum similarity score (default: 0.6)
        region_name: AWS region (default: us-east-1)
    
    Returns:
        List[Dict]: List of similar incidents with metadata
        
    Example:
        >>> query_similar_incidents(
        ...     "kb-123",
        ...     "payment-processor",
        ...     "Connection timeout"
        ... )
        [
            {
                "incident_id": "inc-2024-11-23-001",
                "similarity_score": 0.78,
                "resolution": "Increased timeout threshold to 30s",
                "root_cause": "Payment gateway timeout"
            }
        ]
    """
    # Convert incident to query text
    query_text = convert_incident_to_query(service_name, error_message, log_summary)
    
    # Initialize Bedrock Agent Runtime client
    bedrock_agent_runtime = boto3.client(
        "bedrock-agent-runtime",
        region_name=region_name
    )
    
    try:
        # Query Knowledge Base
        logger.info(f"Querying Knowledge Base {knowledge_base_id} for similar incidents")
        
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                "text": query_text
            },
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": max_results,
                    "overrideSearchType": "HYBRID"  # Semantic + keyword search
                }
            }
        )
        
        # Extract and parse similar incidents
        similar_incidents = []
        for result in response.get("retrievalResults", []):
            score = result.get("score", 0.0)
            
            # Filter by similarity threshold
            if score < similarity_threshold:
                continue
            
            # Parse incident metadata
            incident = parse_incident_metadata(result)
            incident["similarity_score"] = score
            
            similar_incidents.append(incident)
        
        logger.info(
            f"Found {len(similar_incidents)} similar incidents "
            f"(threshold: {similarity_threshold})"
        )
        
        return similar_incidents
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            f"Error querying Knowledge Base: {error_code} - {str(e)}"
        )
        # Return empty list on error to allow processing to continue
        return []
    except Exception as e:
        logger.error(f"Unexpected error querying Knowledge Base: {str(e)}")
        return []


def parse_incident_metadata(retrieval_result: Dict) -> Dict:
    """
    Parse incident metadata from Knowledge Base retrieval result.
    
    Args:
        retrieval_result: Single result from Knowledge Base retrieve() call
    
    Returns:
        Dict: Parsed incident with incident_id, root_cause, and resolution
        
    Example:
        >>> parse_incident_metadata({
        ...     "metadata": {"incident_id": "inc-001", "root_cause": "timeout"},
        ...     "content": {"text": "Increased timeout to 30s"}
        ... })
        {
            "incident_id": "inc-001",
            "root_cause": "timeout",
            "resolution": "Increased timeout to 30s"
        }
    """
    metadata = retrieval_result.get("metadata", {})
    content = retrieval_result.get("content", {})
    
    # Extract incident_id
    incident_id = metadata.get("incident_id", "unknown")
    
    # Extract root_cause (may be string or dict)
    root_cause = metadata.get("root_cause", "")
    if isinstance(root_cause, dict):
        root_cause = root_cause.get("description", root_cause.get("category", ""))
    
    # Extract resolution from content text
    resolution = content.get("text", "")
    
    # Also check metadata for resolution
    if not resolution and "resolution" in metadata:
        resolution_data = metadata.get("resolution", {})
        if isinstance(resolution_data, dict):
            resolution = resolution_data.get("action", "")
        else:
            resolution = str(resolution_data)
    
    incident = {
        "incident_id": incident_id,
        "root_cause": root_cause,
        "resolution": resolution
    }
    
    # Add any additional metadata fields
    for key in ["service_name", "failure_type", "timestamp"]:
        if key in metadata:
            incident[key] = metadata[key]
    
    logger.debug(f"Parsed incident: {incident_id}")
    
    return incident
