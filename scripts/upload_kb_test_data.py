#!/usr/bin/env python3
"""
Upload Knowledge Base test data to S3 and trigger ingestion.

This script uploads sample incident documents to the Bedrock Knowledge Base
data source bucket and triggers an ingestion job.
"""

import os
import sys
import json
import boto3
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config


def upload_kb_documents():
    """Upload all Knowledge Base test documents to S3."""
    s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
    
    # Define test data directory
    test_data_dir = Path('test_data/knowledge_base')
    
    if not test_data_dir.exists():
        print(f"Error: Test data directory not found: {test_data_dir}")
        return 0, 0
    
    print(f"Uploading Knowledge Base test data to S3 bucket: {Config.KB_DATA_SOURCE_BUCKET}")
    print("-" * 60)
    
    uploaded_count = 0
    failed_count = 0
    
    # Walk through all subdirectories
    for category_dir in test_data_dir.iterdir():
        if not category_dir.is_dir():
            continue
        
        category_name = category_dir.name
        print(f"\nCategory: {category_name}")
        
        for json_file in category_dir.glob('*.json'):
            try:
                # Read JSON file
                with open(json_file, 'r') as f:
                    incident_data = json.load(f)
                
                # Create S3 key
                s3_key = f"incidents/{category_name}/{json_file.name}"
                
                # Convert to text format for better embedding
                text_content = format_incident_for_kb(incident_data)
                
                # Upload to S3
                s3_client.put_object(
                    Bucket=Config.KB_DATA_SOURCE_BUCKET,
                    Key=s3_key,
                    Body=text_content,
                    ContentType='text/plain',
                    Metadata={
                        'incident_id': incident_data['incident_id'],
                        'category': incident_data['failure_category'],
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                )
                
                print(f"  ✅ {json_file.name}")
                uploaded_count += 1
                
            except Exception as e:
                print(f"  ❌ {json_file.name}: {str(e)}")
                failed_count += 1
    
    print("-" * 60)
    print(f"Upload complete: {uploaded_count} succeeded, {failed_count} failed")
    
    return uploaded_count, failed_count


def format_incident_for_kb(incident: dict) -> str:
    """
    Format incident data as text for Knowledge Base embedding.
    
    This format optimizes for semantic search by including all relevant
    information in a natural language format.
    """
    text_parts = []
    
    # Header
    text_parts.append(f"Incident ID: {incident['incident_id']}")
    text_parts.append(f"Timestamp: {incident['timestamp']}")
    text_parts.append(f"Service: {incident['service_name']}")
    text_parts.append(f"Category: {incident['failure_category']}")
    text_parts.append("")
    
    # Root cause
    text_parts.append(f"Root Cause: {incident['root_cause']}")
    text_parts.append(f"Confidence Score: {incident['confidence_score']}%")
    text_parts.append(f"Error Message: {incident['error_message']}")
    text_parts.append("")
    
    # Evidence
    text_parts.append("Evidence:")
    for evidence in incident['evidence']:
        text_parts.append(f"  - {evidence}")
    text_parts.append("")
    
    # Resolution
    text_parts.append(f"Resolution: {incident['resolution']}")
    text_parts.append(f"Time to Resolution: {incident['time_to_resolution']}")
    text_parts.append("")
    
    # Fix commands
    if incident.get('fix_commands'):
        text_parts.append("Fix Commands:")
        for cmd in incident['fix_commands']:
            text_parts.append(f"  {cmd}")
        text_parts.append("")
    
    # Preventive measures
    if incident.get('preventive_measures'):
        text_parts.append("Preventive Measures:")
        for measure in incident['preventive_measures']:
            text_parts.append(f"  - {measure}")
        text_parts.append("")
    
    # Similar incidents
    if incident.get('similar_incidents'):
        text_parts.append(f"Similar Incidents: {', '.join(incident['similar_incidents'])}")
        text_parts.append("")
    
    # Tags
    if incident.get('tags'):
        text_parts.append(f"Tags: {', '.join(incident['tags'])}")
    
    return '\n'.join(text_parts)


def trigger_kb_ingestion():
    """Trigger Bedrock Knowledge Base ingestion job."""
    bedrock_agent_client = boto3.client('bedrock-agent', region_name=Config.AWS_REGION)
    
    print("\n" + "=" * 60)
    print("Triggering Knowledge Base Ingestion")
    print("=" * 60)
    
    try:
        response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=Config.KNOWLEDGE_BASE_ID,
            dataSourceId=Config.KB_DATA_SOURCE_ID,
            description='Ingesting test incident data for RAG'
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        status = response['ingestionJob']['status']
        
        print(f"✅ Ingestion job started")
        print(f"Job ID: {ingestion_job_id}")
        print(f"Status: {status}")
        print(f"\nMonitor progress:")
        print(f"  aws bedrock-agent get-ingestion-job \\")
        print(f"    --knowledge-base-id {Config.KNOWLEDGE_BASE_ID} \\")
        print(f"    --data-source-id {Config.KB_DATA_SOURCE_ID} \\")
        print(f"    --ingestion-job-id {ingestion_job_id}")
        
        # Wait for ingestion to complete (optional)
        print(f"\nWaiting for ingestion to complete...")
        wait_for_ingestion(bedrock_agent_client, ingestion_job_id)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to trigger ingestion: {str(e)}")
        return False


def wait_for_ingestion(client, ingestion_job_id: str, timeout: int = 300):
    """Wait for ingestion job to complete."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = client.get_ingestion_job(
                knowledgeBaseId=Config.KNOWLEDGE_BASE_ID,
                dataSourceId=Config.KB_DATA_SOURCE_ID,
                ingestionJobId=ingestion_job_id
            )
            
            status = response['ingestionJob']['status']
            
            if status == 'COMPLETE':
                stats = response['ingestionJob'].get('statistics', {})
                print(f"\n✅ Ingestion complete!")
                print(f"Documents processed: {stats.get('numberOfDocumentsScanned', 0)}")
                print(f"Documents indexed: {stats.get('numberOfDocumentsIndexed', 0)}")
                print(f"Documents failed: {stats.get('numberOfDocumentsFailed', 0)}")
                return True
            elif status == 'FAILED':
                print(f"\n❌ Ingestion failed!")
                failure_reasons = response['ingestionJob'].get('failureReasons', [])
                for reason in failure_reasons:
                    print(f"  - {reason}")
                return False
            else:
                print(f"  Status: {status}... (waiting)")
                time.sleep(10)
                
        except Exception as e:
            print(f"Error checking ingestion status: {str(e)}")
            return False
    
    print(f"\n⚠️  Ingestion timeout after {timeout} seconds")
    print("Check status manually using AWS CLI")
    return False


def main():
    print("Knowledge Base Test Data Upload")
    print("=" * 60)
    
    # Upload documents
    uploaded, failed = upload_kb_documents()
    
    if uploaded == 0:
        print("\nNo documents uploaded. Exiting.")
        return 1
    
    # Trigger ingestion
    if trigger_kb_ingestion():
        print("\n" + "=" * 60)
        print("✅ Knowledge Base test data setup complete!")
        print("=" * 60)
        print(f"\nTotal incidents indexed: {uploaded}")
        print("Categories:")
        print("  - Configuration Errors: 5 incidents")
        print("  - Resource Exhaustion: 5 incidents")
        print("  - Dependency Failures: 5 incidents")
        print("\nYou can now test RAG queries:")
        print("  python scripts/test_kb_query.py --query 'Lambda timeout'")
        return 0
    else:
        print("\n⚠️  Documents uploaded but ingestion failed")
        print("Check AWS console for details")
        return 1


if __name__ == "__main__":
    sys.exit(main())
