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
        knowledge_base_id: Bedrock Knowledge Base ID
        service_name: Name of the service that failed
        error_message: Error message from the incident
        log_summary: Optional log analysis summary
        max_results: Maximum number of results to return (default: 5)
        similarity_threshold: Minimum similarity score (default: 0.6)
        region_name: AWS region name (default: us-east-1)
    
    Returns:
        List[Dict]: List of similar incidents with metadata
    
    Example:
        >>> similar = query_similar_incidents(
        ...     "kb-12345",
        ...     "payment-processor", 
        ...     "Connection timeout",
        ...     max_results=3
        ... )
        >>> len(similar) <= 3
        True
        >>> all("similarity_score" in incident for incident in similar)
        True
    """
    try:
        # Initialize Bedrock Agent Runtime client
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=region_name
        )
        
        # Convert incident to query text
        query_text = convert_incident_to_query(
            service_name=service_name,
            error_message=error_message,
            log_summary=log_summary
        )
        
        logger.info(f"Querying Knowledge Base {knowledge_base_id} for similar incidents")
        
        # Query the Knowledge Base
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query_text
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results,
                    'overrideSearchType': 'HYBRID'  # Use both semantic and keyword search
                }
            }
        )
        
        # Process results
        similar_incidents = []
        
        if 'retrievalResults' in response:
            for result in response['retrievalResults']:
                # Extract similarity score
                similarity_score = result.get('score', 0.0)
                
                # Skip results below threshold
                if similarity_score < similarity_threshold:
                    continue
                
                # Extract content
                content = result.get('content', {}).get('text', '')
                
                # Parse incident metadata from content
                incident_metadata = parse_incident_metadata(content)
                
                # Add similarity score
                incident_metadata['similarity_score'] = similarity_score
                
                # Add source information
                if 'location' in result:
                    incident_metadata['source'] = result['location']
                
                similar_incidents.append(incident_metadata)
        
        # Sort by similarity score (descending)
        similar_incidents.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        logger.info(f"Found {len(similar_incidents)} similar incidents above threshold {similarity_threshold}")
        
        return similar_incidents
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            logger.error(f"Knowledge Base {knowledge_base_id} not found")
        elif error_code == 'AccessDeniedException':
            logger.error("Access denied to Knowledge Base - check IAM permissions")
        else:
            logger.error(f"Bedrock Knowledge Base query failed: {str(e)}")
        
        return []
        
    except Exception as e:
        logger.error(f"Unexpected error querying Knowledge Base: {str(e)}")
        return []


def parse_incident_metadata(content: str) -> Dict:
    """
    Parse incident metadata from Knowledge Base content.
    
    Args:
        content: Raw content from Knowledge Base
    
    Returns:
        Dict: Parsed incident metadata
    
    Example:
        >>> content = '''
        ... Incident ID: INC-2024-001
        ... Root Cause: Database connection timeout
        ... Resolution: Increased connection pool size
        ... Service: payment-processor
        ... '''
        >>> metadata = parse_incident_metadata(content)
        >>> metadata['incident_id']
        'INC-2024-001'
    """
    metadata = {
        'incident_id': 'unknown',
        'root_cause': '',
        'resolution': '',
        'service_name': '',
        'content': content
    }
    
    try:
        # Parse common patterns from incident documentation
        import re
        
        # Extract incident ID
        incident_id_patterns = [
            r'incident[_\s-]?id[:\s]+([a-zA-Z0-9-]+)',
            r'id[:\s]+([a-zA-Z0-9-]+)',
            r'incident[:\s]+([a-zA-Z0-9-]+)'
        ]
        
        for pattern in incident_id_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['incident_id'] = match.group(1)
                break
        
        # Extract root cause
        root_cause_patterns = [
            r'root[_\s-]?cause[:\s]+([^\n]+)',
            r'cause[:\s]+([^\n]+)',
            r'reason[:\s]+([^\n]+)'
        ]
        
        for pattern in root_cause_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['root_cause'] = match.group(1).strip()
                break
        
        # Extract resolution
        resolution_patterns = [
            r'resolution[:\s]+([^\n]+)',
            r'fix[:\s]+([^\n]+)',
            r'solution[:\s]+([^\n]+)',
            r'resolved[_\s-]?by[:\s]+([^\n]+)'
        ]
        
        for pattern in resolution_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['resolution'] = match.group(1).strip()
                break
        
        # Extract service name
        service_patterns = [
            r'service[_\s-]?name[:\s]+([a-zA-Z0-9_-]+)',
            r'service[:\s]+([a-zA-Z0-9_-]+)',
            r'component[:\s]+([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata['service_name'] = match.group(1)
                break
        
        # If no structured data found, try to extract from JSON
        try:
            import json
            # Look for JSON blocks in the content
            json_pattern = r'\{[^}]+\}'
            json_matches = re.findall(json_pattern, content, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    json_data = json.loads(json_str)
                    
                    # Update metadata with JSON data
                    if 'incident_id' in json_data:
                        metadata['incident_id'] = json_data['incident_id']
                    if 'root_cause' in json_data:
                        metadata['root_cause'] = json_data['root_cause']
                    if 'resolution' in json_data:
                        metadata['resolution'] = json_data['resolution']
                    if 'service_name' in json_data:
                        metadata['service_name'] = json_data['service_name']
                    
                    break  # Use first valid JSON found
                    
                except json.JSONDecodeError:
                    continue
                    
        except Exception:
            pass  # JSON parsing is optional
        
        logger.debug(f"Parsed incident metadata: {metadata['incident_id']}")
        
    except Exception as e:
        logger.warning(f"Failed to parse incident metadata: {str(e)}")
    
    return metadata


def format_similar_incidents_for_analysis(similar_incidents: List[Dict]) -> str:
    """
    Format similar incidents for inclusion in analysis prompts.
    
    Args:
        similar_incidents: List of similar incident dictionaries
    
    Returns:
        str: Formatted text for analysis prompts
    """
    if not similar_incidents:
        return "No similar incidents found in Knowledge Base."
    
    formatted_text = f"Found {len(similar_incidents)} similar incidents:\n\n"
    
    for i, incident in enumerate(similar_incidents, 1):
        similarity = incident.get('similarity_score', 0) * 100
        incident_id = incident.get('incident_id', 'unknown')
        root_cause = incident.get('root_cause', 'Not specified')
        resolution = incident.get('resolution', 'Not specified')
        
        formatted_text += f"{i}. Incident {incident_id} (Similarity: {similarity:.1f}%)\n"
        formatted_text += f"   Root Cause: {root_cause}\n"
        formatted_text += f"   Resolution: {resolution}\n\n"
    
    return formatted_text


def get_knowledge_base_statistics(
    knowledge_base_id: str,
    region_name: str = "us-east-1"
) -> Dict:
    """
    Get statistics about the Knowledge Base.
    
    Args:
        knowledge_base_id: Bedrock Knowledge Base ID
        region_name: AWS region name
    
    Returns:
        Dict: Knowledge Base statistics
    """
    try:
        bedrock_agent = boto3.client('bedrock-agent', region_name=region_name)
        
        # Get Knowledge Base details
        response = bedrock_agent.get_knowledge_base(
            knowledgeBaseId=knowledge_base_id
        )
        
        kb_info = response.get('knowledgeBase', {})
        
        return {
            'knowledge_base_id': knowledge_base_id,
            'name': kb_info.get('name', 'Unknown'),
            'status': kb_info.get('status', 'Unknown'),
            'description': kb_info.get('description', ''),
            'created_at': kb_info.get('createdAt', ''),
            'updated_at': kb_info.get('updatedAt', '')
        }
        
    except Exception as e:
        logger.error(f"Failed to get Knowledge Base statistics: {str(e)}")
        return {
            'knowledge_base_id': knowledge_base_id,
            'error': str(e)
        }