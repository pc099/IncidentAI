"""
Knowledge Base Sync Module

This module handles syncing incident records from DynamoDB to Bedrock Knowledge Base
for RAG-powered root cause analysis.

Requirements:
- 8.1: Sync incidents to Knowledge Base
"""

import json
import logging
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class KnowledgeBaseSync:
    """
    Handles syncing incidents to Bedrock Knowledge Base.
    
    Features:
    - Convert DynamoDB records to Knowledge Base document format
    - Write documents to S3 data source bucket
    - Trigger Knowledge Base ingestion jobs
    
    Requirements:
        - 8.1: Sync incidents to Knowledge Base for RAG
    """
    
    def __init__(
        self,
        kb_bucket: str,
        kb_id: Optional[str] = None,
        data_source_id: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Initialize Knowledge Base sync.
        
        Args:
            kb_bucket: S3 bucket for Knowledge Base data source
            kb_id: Bedrock Knowledge Base ID (optional)
            data_source_id: Knowledge Base data source ID (optional)
            region: AWS region
        """
        self.kb_bucket = kb_bucket
        self.kb_id = kb_id
        self.data_source_id = data_source_id
        self.region = region
        
        # Initialize AWS clients
        self.s3_client = boto3.client('s3', region_name=region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        
        logger.info(
            f"Initialized KnowledgeBaseSync: "
            f"bucket={kb_bucket}, kb_id={kb_id}, region={region}"
        )
    
    def sync_incident(
        self,
        incident_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync incident to Knowledge Base.
        
        Args:
            incident_record: Incident record from DynamoDB
        
        Returns:
            Sync result with success status
        
        Requirements:
            - 8.1: Convert and sync to Knowledge Base
        """
        try:
            incident_id = incident_record.get('incident_id', 'unknown')
            
            logger.info(f"Syncing incident to Knowledge Base: {incident_id}")
            
            # Convert to Knowledge Base document format
            kb_document = self._convert_to_kb_document(incident_record)
            
            # Write to S3 data source bucket
            s3_key = f"incidents/{incident_id}.json"
            self._write_to_s3(kb_document, s3_key)
            
            # Trigger ingestion job (if KB ID provided)
            ingestion_job_id = None
            if self.kb_id and self.data_source_id:
                ingestion_job_id = self._trigger_ingestion()
            
            logger.info(
                f"Successfully synced incident to Knowledge Base: {incident_id}"
            )
            
            return {
                "success": True,
                "incident_id": incident_id,
                "s3_key": s3_key,
                "ingestion_job_id": ingestion_job_id
            }
            
        except Exception as e:
            logger.error(f"Failed to sync incident to Knowledge Base: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "incident_id": incident_record.get('incident_id', 'unknown')
            }
    
    def _convert_to_kb_document(
        self,
        incident_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert DynamoDB incident record to Knowledge Base document format.
        
        Args:
            incident_record: Incident record from DynamoDB
        
        Returns:
            Knowledge Base document
        """
        # Extract key information
        incident_id = incident_record.get('incident_id', 'unknown')
        service_name = incident_record.get('service_name', 'unknown')
        failure_type = incident_record.get('failure_type', 'unknown')
        timestamp = incident_record.get('timestamp', '')
        
        # Extract root cause
        root_cause = incident_record.get('root_cause', {})
        if isinstance(root_cause, dict):
            root_cause_category = root_cause.get('category', 'unknown')
            root_cause_description = root_cause.get('description', '')
            confidence_score = root_cause.get('confidence_score', 0)
            evidence = root_cause.get('evidence', [])
        else:
            root_cause_category = 'unknown'
            root_cause_description = str(root_cause) if root_cause else ''
            confidence_score = 0
            evidence = []
        
        # Extract error patterns
        error_patterns = incident_record.get('error_patterns', [])
        
        # Extract fix applied
        fix_applied = incident_record.get('fix_applied', {})
        if isinstance(fix_applied, dict):
            fix_action = fix_applied.get('action', '')
            fix_command = fix_applied.get('command', '')
        else:
            fix_action = ''
            fix_command = ''
        
        # Extract resolution info
        resolution_time_seconds = incident_record.get('resolution_time_seconds', 0)
        
        # Create log summary for embedding
        log_summary = f"""
Service: {service_name}
Failure Type: {failure_type}
Error Patterns: {', '.join(error_patterns)}
Root Cause: {root_cause_description}
Evidence: {'; '.join(evidence)}
        """.strip()
        
        # Build Knowledge Base document
        kb_document = {
            "incident_id": incident_id,
            "service_name": service_name,
            "failure_type": failure_type,
            "error_patterns": error_patterns,
            "root_cause": {
                "category": root_cause_category,
                "description": root_cause_description,
                "confidence_score": confidence_score,
                "evidence": evidence
            },
            "resolution": {
                "action": fix_action,
                "command": fix_command,
                "success": True if fix_action else False,
                "resolution_time_seconds": resolution_time_seconds
            },
            "log_summary": log_summary,
            "timestamp": timestamp,
            "metadata": {
                "incident_id": incident_id,
                "service_name": service_name,
                "failure_type": failure_type,
                "root_cause": root_cause_category,
                "timestamp": timestamp
            }
        }
        
        return kb_document
    
    def _write_to_s3(
        self,
        kb_document: Dict[str, Any],
        s3_key: str
    ) -> None:
        """
        Write Knowledge Base document to S3.
        
        Args:
            kb_document: Knowledge Base document
            s3_key: S3 object key
        """
        try:
            # Convert to JSON
            document_json = json.dumps(kb_document, indent=2)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.kb_bucket,
                Key=s3_key,
                Body=document_json,
                ContentType='application/json'
            )
            
            logger.info(f"Wrote document to S3: s3://{self.kb_bucket}/{s3_key}")
            
        except ClientError as e:
            logger.error(f"Failed to write to S3: {str(e)}")
            raise
    
    def _trigger_ingestion(self) -> Optional[str]:
        """
        Trigger Knowledge Base ingestion job.
        
        Returns:
            Ingestion job ID or None if failed
        """
        try:
            if not self.kb_id or not self.data_source_id:
                logger.warning(
                    "Knowledge Base ID or Data Source ID not provided, "
                    "skipping ingestion trigger"
                )
                return None
            
            logger.info(
                f"Triggering Knowledge Base ingestion: "
                f"kb_id={self.kb_id}, data_source_id={self.data_source_id}"
            )
            
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id
            )
            
            ingestion_job = response.get('ingestionJob', {})
            job_id = ingestion_job.get('ingestionJobId')
            
            logger.info(f"Started ingestion job: {job_id}")
            
            return job_id
            
        except ClientError as e:
            logger.error(f"Failed to trigger ingestion: {str(e)}")
            return None
    
    def get_ingestion_job_status(
        self,
        ingestion_job_id: str
    ) -> Optional[str]:
        """
        Get status of ingestion job.
        
        Args:
            ingestion_job_id: Ingestion job ID
        
        Returns:
            Job status or None if failed
        """
        try:
            if not self.kb_id or not self.data_source_id:
                return None
            
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                ingestionJobId=ingestion_job_id
            )
            
            ingestion_job = response.get('ingestionJob', {})
            status = ingestion_job.get('status')
            
            logger.info(f"Ingestion job {ingestion_job_id} status: {status}")
            
            return status
            
        except ClientError as e:
            logger.error(f"Failed to get ingestion job status: {str(e)}")
            return None


# Convenience function
def sync_incident_to_kb(
    incident_record: Dict[str, Any],
    kb_bucket: str,
    kb_id: Optional[str] = None,
    data_source_id: Optional[str] = None,
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Sync incident to Knowledge Base.
    
    Args:
        incident_record: Incident record from DynamoDB
        kb_bucket: S3 bucket for Knowledge Base data source
        kb_id: Bedrock Knowledge Base ID
        data_source_id: Knowledge Base data source ID
        region: AWS region
    
    Returns:
        Sync result
    """
    sync = KnowledgeBaseSync(
        kb_bucket=kb_bucket,
        kb_id=kb_id,
        data_source_id=data_source_id,
        region=region
    )
    return sync.sync_incident(incident_record)
