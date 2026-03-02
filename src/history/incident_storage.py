"""
DynamoDB Incident Storage Module

This module handles storing incident records in DynamoDB with TTL support
and ISO 8601 timestamp formatting.

Requirements:
- 8.1: Store incident records in DynamoDB
- 8.2: Include all required fields
- 8.6: Use ISO 8601 format for timestamps
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IncidentStorage:
    """
    Handles incident storage in DynamoDB.
    
    Features:
    - Store complete incident records
    - Automatic TTL configuration (90 days)
    - ISO 8601 timestamp formatting
    - Error handling and logging
    
    Requirements:
        - 8.1: Store incidents in DynamoDB
        - 8.2: Include service_name, failure_type, root_cause, fix_applied, resolution_time
        - 8.6: ISO 8601 timestamps
    """
    
    def __init__(
        self,
        table_name: str = "incident-history",
        region: str = "us-east-1",
        ttl_days: int = 90
    ):
        """
        Initialize incident storage.
        
        Args:
            table_name: DynamoDB table name
            region: AWS region
            ttl_days: Days until automatic deletion (default 90)
        """
        self.table_name = table_name
        self.region = region
        self.ttl_days = ttl_days
        
        # Initialize DynamoDB client and resource
        self.dynamodb_client = boto3.client('dynamodb', region_name=region)
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb_resource.Table(table_name)
        
        logger.info(
            f"Initialized IncidentStorage: "
            f"table={table_name}, region={region}, ttl_days={ttl_days}"
        )
    
    def store_incident(
        self,
        enhanced_alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store incident record in DynamoDB.
        
        Args:
            enhanced_alert: Enhanced alert from orchestrator
        
        Returns:
            Storage result with success status
        
        Requirements:
            - 8.1: Store in DynamoDB
            - 8.2: Include all required fields
            - 8.6: ISO 8601 timestamps
        """
        try:
            incident_id = enhanced_alert.get('incident_id', 'unknown')
            
            logger.info(f"Storing incident: {incident_id}")
            
            # Build incident record
            incident_record = self._build_incident_record(enhanced_alert)
            
            # Store in DynamoDB
            response = self.table.put_item(Item=incident_record)
            
            logger.info(f"Successfully stored incident: {incident_id}")
            
            return {
                "success": True,
                "incident_id": incident_id,
                "timestamp": incident_record['timestamp']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                f"Failed to store incident: {incident_id}, "
                f"error: {error_code} - {error_message}"
            )
            
            return {
                "success": False,
                "error": f"{error_code}: {error_message}",
                "incident_id": incident_id
            }
        
        except Exception as e:
            logger.error(f"Unexpected error storing incident: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "incident_id": enhanced_alert.get('incident_id', 'unknown')
            }
    
    def _build_incident_record(
        self,
        enhanced_alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build incident record with all required fields.
        
        Args:
            enhanced_alert: Enhanced alert from orchestrator
        
        Returns:
            Complete incident record for DynamoDB
        
        Requirements:
            - 8.2: Include service_name, failure_type, root_cause, fix_applied, resolution_time
            - 8.6: ISO 8601 timestamps
        """
        # Extract basic information
        incident_id = enhanced_alert.get('incident_id', 'unknown')
        timestamp = enhanced_alert.get('timestamp')
        
        # Ensure timestamp is ISO 8601 format
        if not timestamp:
            timestamp = datetime.utcnow().isoformat() + 'Z'
        elif not timestamp.endswith('Z') and '+' not in timestamp:
            timestamp = timestamp + 'Z'
        
        # Extract original alert info
        original_alert = enhanced_alert.get('original_alert', {})
        
        # Try to get service_name from multiple locations for flexibility
        service_name = (
            enhanced_alert.get('service_name') or  # Direct field
            original_alert.get('service_name') or  # From original_alert
            'unknown'
        )
        
        error_message = (
            enhanced_alert.get('error_message') or
            original_alert.get('error_message') or
            ''
        )
        
        log_location = (
            enhanced_alert.get('log_location') or
            original_alert.get('log_location') or
            ''
        )
        
        # Extract root cause
        root_cause = enhanced_alert.get('root_cause', {})
        if isinstance(root_cause, dict):
            failure_type = (
                enhanced_alert.get('failure_type') or  # Direct field
                root_cause.get('category') or
                'unknown'
            )
            root_cause_description = root_cause.get('description', '')
            confidence_score = root_cause.get('confidence_score', 0)
            evidence = root_cause.get('evidence', [])
        else:
            failure_type = enhanced_alert.get('failure_type', 'unknown')
            root_cause_description = str(root_cause) if root_cause else ''
            confidence_score = 0
            evidence = []
        
        # Extract error patterns from log analysis or direct field
        error_patterns = enhanced_alert.get('error_patterns', [])
        if not error_patterns:
            agent_outputs = enhanced_alert.get('agent_outputs', {})
            log_output = agent_outputs.get('log-analysis', {})
            if log_output and log_output.get('success'):
                log_data = log_output.get('output', {})
                if isinstance(log_data, dict):
                    patterns = log_data.get('error_patterns', [])
                    error_patterns = [p.get('pattern', '') if isinstance(p, dict) else str(p) for p in patterns]
        
        # Extract fix applied from direct field or agent outputs
        fix_applied = enhanced_alert.get('fix_applied', {})
        if not fix_applied:
            fixes = enhanced_alert.get('recommended_fixes', [])
            if not fixes:
                agent_outputs = enhanced_alert.get('agent_outputs', {})
                fix_output = agent_outputs.get('fix-recommendation', {})
                if fix_output and fix_output.get('success'):
                    fix_data = fix_output.get('output', {})
                    fixes = fix_data.get('immediate_actions', [])
            
            if fixes:
                first_fix = fixes[0] if isinstance(fixes, list) else fixes
                if isinstance(first_fix, dict):
                    fix_applied = {
                        "action": first_fix.get('action', ''),
                        "command": first_fix.get('command', ''),
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                        "applied_by": "auto"
                    }
        
        # Calculate resolution time (placeholder - would be updated when resolved)
        resolution_time_seconds = enhanced_alert.get('resolution_time_seconds', 0)
        
        # Extract similar incidents
        similar_to = enhanced_alert.get('similar_to', [])
        if not similar_to:
            agent_outputs = enhanced_alert.get('agent_outputs', {})
            root_cause_output = agent_outputs.get('root-cause', {})
            if root_cause_output and root_cause_output.get('success'):
                root_cause_data = root_cause_output.get('output', {})
                if isinstance(root_cause_data, dict):
                    similar_incidents = root_cause_data.get('similar_incidents', [])
                    similar_to = [inc.get('incident_id', '') for inc in similar_incidents if isinstance(inc, dict)]
        
        # Calculate TTL (90 days from now)
        ttl_timestamp = int(time.time()) + (self.ttl_days * 24 * 60 * 60)
        
        # Build complete record
        incident_record = {
            "incident_id": incident_id,
            "timestamp": timestamp,
            "service_name": service_name,
            "failure_type": failure_type,
            "error_message": error_message,
            "root_cause": {
                "category": failure_type,
                "description": root_cause_description,
                "confidence_score": confidence_score,
                "evidence": evidence
            },
            "error_patterns": error_patterns,
            "fix_applied": fix_applied,
            "resolution_time_seconds": resolution_time_seconds,
            "similar_to": similar_to,
            "log_location": log_location,
            "enhanced_alert": enhanced_alert,  # Store complete alert for reference
            "ttl": ttl_timestamp
        }
        
        return incident_record
    
    def get_incident(
        self,
        incident_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve incident by ID.
        
        Args:
            incident_id: Incident ID to retrieve
        
        Returns:
            Incident record or None if not found
        """
        try:
            response = self.table.get_item(
                Key={'incident_id': incident_id}
            )
            
            if 'Item' in response:
                logger.info(f"Retrieved incident: {incident_id}")
                return response['Item']
            else:
                logger.warning(f"Incident not found: {incident_id}")
                return None
                
        except ClientError as e:
            logger.error(f"Failed to retrieve incident {incident_id}: {str(e)}")
            return None
    
    def update_resolution_time(
        self,
        incident_id: str,
        resolution_time_seconds: int
    ) -> bool:
        """
        Update resolution time for an incident.
        
        Args:
            incident_id: Incident ID
            resolution_time_seconds: Time to resolution in seconds
        
        Returns:
            True if successful
        """
        try:
            self.table.update_item(
                Key={'incident_id': incident_id},
                UpdateExpression='SET resolution_time_seconds = :time',
                ExpressionAttributeValues={
                    ':time': resolution_time_seconds
                }
            )
            
            logger.info(
                f"Updated resolution time for {incident_id}: "
                f"{resolution_time_seconds}s"
            )
            return True
            
        except ClientError as e:
            logger.error(
                f"Failed to update resolution time for {incident_id}: {str(e)}"
            )
            return False
    
    def verify_table_exists(self) -> bool:
        """
        Verify that the DynamoDB table exists.
        
        Returns:
            True if table exists
        """
        try:
            self.dynamodb_client.describe_table(TableName=self.table_name)
            logger.info(f"Table {self.table_name} exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.warning(f"Table {self.table_name} does not exist")
                return False
            else:
                logger.error(f"Error checking table: {str(e)}")
                return False


# Convenience function
def store_incident_record(
    enhanced_alert: Dict[str, Any],
    table_name: str = "incident-history",
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Store incident record in DynamoDB.
    
    Args:
        enhanced_alert: Enhanced alert from orchestrator
        table_name: DynamoDB table name
        region: AWS region
    
    Returns:
        Storage result
    """
    storage = IncidentStorage(table_name=table_name, region=region)
    return storage.store_incident(enhanced_alert)
