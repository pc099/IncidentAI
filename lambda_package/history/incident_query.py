"""
Incident Query Module

This module handles querying incidents from DynamoDB using GSI and
ranking similar incidents by similarity score.

Requirements:
- 8.3: Query by service_name and failure pattern
- 8.4: Return top 5 similar incidents ranked by similarity
- 8.5: Handle empty result sets gracefully
"""

import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IncidentQuery:
    """
    Handles querying incidents from DynamoDB.
    
    Features:
    - Query by service_name and failure pattern using GSI
    - Rank similar incidents by similarity score
    - Return top 5 most similar incidents
    - Handle empty results gracefully
    
    Requirements:
        - 8.3: Query by service_name and failure pattern
        - 8.4: Return top 5 similar incidents
        - 8.5: Handle empty results
    """
    
    def __init__(
        self,
        table_name: str = "incident-history",
        region: str = "us-east-1",
        gsi_name: str = "service-timestamp-index"
    ):
        """
        Initialize incident query.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
            gsi_name: Global Secondary Index name
        """
        self.table_name = table_name
        self.region = region
        self.gsi_name = gsi_name
        
        # Initialize DynamoDB resource
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb_resource.Table(table_name)
        
        logger.info(
            f"Initialized IncidentQuery: "
            f"table={table_name}, region={region}, gsi={gsi_name}"
        )
    
    def query_by_service(
        self,
        service_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Query incidents by service name using GSI.
        
        Args:
            service_name: Service name to query
            limit: Maximum number of results
        
        Returns:
            List of incident records
        
        Requirements:
            - 8.3: Query by service_name
            - 8.5: Handle empty results
        """
        try:
            logger.info(f"Querying incidents for service: {service_name}")
            
            response = self.table.query(
                IndexName=self.gsi_name,
                KeyConditionExpression='service_name = :service',
                ExpressionAttributeValues={
                    ':service': service_name
                },
                Limit=limit,
                ScanIndexForward=False  # Most recent first
            )
            
            incidents = response.get('Items', [])
            
            logger.info(
                f"Found {len(incidents)} incidents for service: {service_name}"
            )
            
            return incidents
            
        except ClientError as e:
            logger.error(
                f"Failed to query incidents for {service_name}: {str(e)}"
            )
            return []  # Handle empty results gracefully
        
        except Exception as e:
            logger.error(f"Unexpected error querying incidents: {str(e)}")
            return []
    
    def find_similar_incidents(
        self,
        service_name: str,
        failure_pattern: str,
        error_patterns: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar incidents ranked by similarity score.
        
        Args:
            service_name: Service name to query
            failure_pattern: Failure pattern or error message
            error_patterns: List of error patterns to match
            top_k: Number of top similar incidents to return (default 5)
        
        Returns:
            List of top K similar incidents with similarity scores
        
        Requirements:
            - 8.3: Query by service_name and failure pattern
            - 8.4: Return top 5 similar incidents ranked by similarity
            - 8.5: Handle empty results
        """
        try:
            logger.info(
                f"Finding similar incidents for service: {service_name}, "
                f"pattern: {failure_pattern}"
            )
            
            # Query incidents for this service
            incidents = self.query_by_service(service_name)
            
            if not incidents:
                logger.info(f"No incidents found for service: {service_name}")
                return []  # Handle empty results gracefully
            
            # Calculate similarity scores
            scored_incidents = []
            for incident in incidents:
                similarity_score = self._calculate_similarity(
                    incident,
                    failure_pattern,
                    error_patterns
                )
                
                if similarity_score > 0:
                    incident_with_score = incident.copy()
                    incident_with_score['similarity_score'] = similarity_score
                    scored_incidents.append(incident_with_score)
            
            # Sort by similarity score (descending) and return top K
            scored_incidents.sort(
                key=lambda x: x['similarity_score'],
                reverse=True
            )
            
            top_incidents = scored_incidents[:top_k]
            
            logger.info(
                f"Found {len(top_incidents)} similar incidents "
                f"(out of {len(incidents)} total)"
            )
            
            return top_incidents
            
        except Exception as e:
            logger.error(f"Error finding similar incidents: {str(e)}")
            return []  # Handle errors gracefully
    
    def _calculate_similarity(
        self,
        incident: Dict[str, Any],
        failure_pattern: str,
        error_patterns: Optional[List[str]] = None
    ) -> float:
        """
        Calculate similarity score between current failure and stored incident.
        
        Args:
            incident: Stored incident record
            failure_pattern: Current failure pattern
            error_patterns: Current error patterns
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        similarity_scores = []
        
        # Compare error message
        incident_error = incident.get('error_message', '')
        if incident_error and failure_pattern:
            error_similarity = SequenceMatcher(
                None,
                failure_pattern.lower(),
                incident_error.lower()
            ).ratio()
            similarity_scores.append(error_similarity * 0.4)  # 40% weight
        
        # Compare root cause description
        root_cause = incident.get('root_cause', {})
        if isinstance(root_cause, dict):
            root_cause_desc = root_cause.get('description', '')
            if root_cause_desc and failure_pattern:
                root_cause_similarity = SequenceMatcher(
                    None,
                    failure_pattern.lower(),
                    root_cause_desc.lower()
                ).ratio()
                similarity_scores.append(root_cause_similarity * 0.3)  # 30% weight
        
        # Compare error patterns
        if error_patterns:
            incident_patterns = incident.get('error_patterns', [])
            if incident_patterns:
                pattern_matches = sum(
                    1 for pattern in error_patterns
                    if any(
                        pattern.lower() in inc_pattern.lower()
                        for inc_pattern in incident_patterns
                    )
                )
                pattern_similarity = pattern_matches / len(error_patterns)
                similarity_scores.append(pattern_similarity * 0.3)  # 30% weight
        
        # Return average similarity
        if similarity_scores:
            return sum(similarity_scores) / len(similarity_scores)
        else:
            return 0.0
    
    def query_by_failure_type(
        self,
        failure_type: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Query incidents by failure type.
        
        Args:
            failure_type: Failure type (configuration_error, resource_exhaustion, dependency_failure)
            limit: Maximum number of results
        
        Returns:
            List of incident records
        """
        try:
            logger.info(f"Querying incidents by failure type: {failure_type}")
            
            response = self.table.scan(
                FilterExpression='failure_type = :type',
                ExpressionAttributeValues={
                    ':type': failure_type
                },
                Limit=limit
            )
            
            incidents = response.get('Items', [])
            
            logger.info(
                f"Found {len(incidents)} incidents with failure type: {failure_type}"
            )
            
            return incidents
            
        except ClientError as e:
            logger.error(
                f"Failed to query by failure type {failure_type}: {str(e)}"
            )
            return []
    
    def get_recent_incidents(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most recent incidents across all services.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            List of recent incident records
        """
        try:
            logger.info(f"Getting {limit} most recent incidents")
            
            response = self.table.scan(
                Limit=limit
            )
            
            incidents = response.get('Items', [])
            
            # Sort by timestamp (most recent first)
            incidents.sort(
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            return incidents[:limit]
            
        except ClientError as e:
            logger.error(f"Failed to get recent incidents: {str(e)}")
            return []


# Convenience function
def find_similar_incidents(
    service_name: str,
    failure_pattern: str,
    error_patterns: Optional[List[str]] = None,
    table_name: str = "incident-history",
    region: str = "us-east-1",
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Find similar incidents for a service and failure pattern.
    
    Args:
        service_name: Service name
        failure_pattern: Failure pattern or error message
        error_patterns: List of error patterns
        table_name: DynamoDB table name
        region: AWS region
        top_k: Number of top similar incidents to return
    
    Returns:
        List of similar incidents with similarity scores
    """
    query = IncidentQuery(table_name=table_name, region=region)
    return query.find_similar_incidents(
        service_name=service_name,
        failure_pattern=failure_pattern,
        error_patterns=error_patterns,
        top_k=top_k
    )
