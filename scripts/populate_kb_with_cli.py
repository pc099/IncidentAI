#!/usr/bin/env python3
"""
Populate Bedrock Knowledge Base using AWS CLI (avoids SSL issues).

This script uses AWS CLI commands instead of boto3 to avoid SSL certificate issues.
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import sample incidents
from populate_kb_samples import SAMPLE_INCIDENTS, create_incident_document


def run_aws_command(command):
    """Run AWS CLI command and return output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        raise


def main():
    """Main function to populate Knowledge Base using AWS CLI"""
    
    print("=" * 80)
    print("Populating Bedrock Knowledge Base with Sample Incidents (AWS CLI)")
    print("=" * 80)
    print()
    
    bucket_name = "incident-response-kb-data"
    print(f"S3 Bucket: {bucket_name}")
    print()
    
    # Create temporary directory for incident files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Creating {len(SAMPLE_INCIDENTS)} sample incidents...")
        print()
        
        uploaded_count = 0
        for incident in SAMPLE_INCIDENTS:
            incident_id = incident['incident_id']
            print(f"  • {incident_id} ({incident['category']}, {incident['aws_service']})...", end=" ")
            
            # Create document
            doc_content = create_incident_document(incident)
            
            # Write to temporary file
            temp_file = Path(temp_dir) / f"{incident_id}.txt"
            temp_file.write_text(doc_content, encoding='utf-8')
            
            # Upload to S3 using AWS CLI
            s3_key = f"incidents/{incident_id}.txt"
            command = f'aws s3 cp "{temp_file}" s3://{bucket_name}/{s3_key}'
            
            try:
                run_aws_command(command)
                print("✓")
                uploaded_count += 1
            except Exception as e:
                print("✗")
                print(f"    Error: {e}")
        
        print()
        print(f"✓ Uploaded {uploaded_count}/{len(SAMPLE_INCIDENTS)} incidents to S3")
        print()
    
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total Incidents: {len(SAMPLE_INCIDENTS)}")
    print(f"  • Configuration Errors: 5")
    print(f"  • Resource Exhaustion: 5")
    print(f"  • Dependency Failures: 5")
    print()
    print("AWS Services Covered:")
    print(f"  • Lambda (deployment, memory, concurrency)")
    print(f"  • DynamoDB (throttling, capacity)")
    print(f"  • RDS (storage, connections)")
    print(f"  • API Gateway (timeouts)")
    print(f"  • Step Functions (state machine errors)")
    print(f"  • SES (email verification)")
    print(f"  • SNS (delivery failures)")
    print(f"  • S3 (consistency)")
    print()
    print("✓ Sample incidents uploaded to S3!")
    print()
    print("Next steps:")
    print("1. Create Bedrock Knowledge Base (if not already created)")
    print("2. Configure S3 as data source for Knowledge Base")
    print("3. Trigger ingestion job to index the documents")
    print("4. Wait 5-10 minutes for ingestion to complete")
    print("5. Test queries with scripts/test_kb_query.py")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
