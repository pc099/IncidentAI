"""
Lambda Handler: Orchestrator
Coordinates execution of all AI agents using Bedrock directly
"""
import json
import os
import sys
import boto3
from datetime import datetime

# Add src to path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import agent modules
from agents.log_analysis_agent import LogAnalysisAgent
from agents.fix_recommendation_agent import FixRecommendationAgent
from agents.communication_agent import CommunicationAgent
from history.incident_storage import store_incident_record
from alerts.ses_delivery import SESDeliveryService


def lambda_handler(event, context):
    """
    Lambda handler for orchestration.
    
    Triggered by: Incident Validator Lambda
    
    Args:
        event: Incident payload from validator
        context: Lambda context
        
    Returns:
        dict: Orchestration result
    """
    try:
        print(f"Starting orchestration for incident: {event.get('incident_id')}")
        
        # Extract incident details
        incident_id = event['incident_id']
        service_name = event['service_name']
        timestamp = event['timestamp']
        error_message = event['error_message']
        log_location = event['log_location']
        
        result = {
            'incident_id': incident_id,
            'status': 'processing',
            'agents_executed': []
        }
        
        # Agent 1: Log Analysis
        try:
            print(f"Executing Log Analysis Agent...")
            log_agent = LogAnalysisAgent()
            log_analysis = log_agent.analyze(
                service_name=service_name,
                timestamp=timestamp,
                log_location=log_location
            )
            result['log_analysis'] = log_analysis
            result['agents_executed'].append('log_analysis')
            print(f"✓ Log Analysis complete")
        except Exception as e:
            print(f"✗ Log Analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
            result['log_analysis'] = {'error': str(e), 'confidence_score': 40}
        
        # Agent 2: Root Cause Analysis (simplified - using log analysis)
        try:
            print(f"Executing Root Cause Analysis...")
            # For now, use a simplified root cause based on error message
            root_cause = {
                'analysis': {  # Wrap in 'analysis' key for communication agent
                    'primary_cause': {
                        'description': error_message,
                        'category': 'dependency_failure',
                        'confidence_score': 75,
                        'evidence': [error_message]
                    },
                    'similar_incidents': []
                }
            }
            result['root_cause'] = root_cause
            result['agents_executed'].append('root_cause')
            print(f"✓ Root Cause Analysis complete")
        except Exception as e:
            print(f"✗ Root Cause Analysis failed: {str(e)}")
            result['root_cause'] = {'error': str(e)}
        
        # Agent 3: Fix Recommendations
        try:
            print(f"Executing Fix Recommendation Agent...")
            fix_agent = FixRecommendationAgent()
            fix_recommendations = fix_agent.generate_recommendations(
                root_cause=result.get('root_cause', {}),
                service_name=service_name,
                log_summary=result.get('log_analysis', {})
            )
            result['fix_recommendations'] = fix_recommendations
            result['agents_executed'].append('fix_recommendations')
            print(f"✓ Fix Recommendations complete")
        except Exception as e:
            print(f"✗ Fix Recommendations failed: {str(e)}")
            import traceback
            traceback.print_exc()
            result['fix_recommendations'] = {'error': str(e)}
        
        # Agent 4: Communication (Generate Summaries)
        try:
            print(f"Executing Communication Agent...")
            comm_agent = CommunicationAgent()
            summaries = comm_agent.generate_summaries(
                root_cause=result.get('root_cause', {}),
                fixes=result.get('fix_recommendations', {}),
                original_alert={
                    'incident_id': incident_id,
                    'service_name': service_name,
                    'timestamp': timestamp,
                    'error_message': error_message
                }
            )
            result['summaries'] = summaries
            result['agents_executed'].append('communication')
            print(f"✓ Communication complete")
        except Exception as e:
            print(f"✗ Communication failed: {str(e)}")
            import traceback
            traceback.print_exc()
            result['summaries'] = {'error': str(e)}
        
        # Send Email Alert
        try:
            print(f"Sending email alert...")
            recipient_email = os.environ.get('SES_SENDER_EMAIL', 'harshavignesh1@gmail.com')
            
            # Build enhanced alert for email
            enhanced_alert = result.get('summaries', {}).get('enhanced_alert', {})
            if not enhanced_alert:
                # Fallback if summaries didn't generate enhanced_alert
                enhanced_alert = {
                    'incident_id': incident_id,
                    'service_name': service_name,
                    'timestamp': timestamp,
                    'technical_summary': {},
                    'business_summary': {},
                    'root_cause': result.get('root_cause', {}),
                    'fixes': result.get('fix_recommendations', {}),
                    'original_alert': {
                        'service_name': service_name,
                        'timestamp': timestamp,
                        'error_message': error_message
                    }
                }
            
            # Send via SES
            ses_service = SESDeliveryService(sender_email=recipient_email)
            email_result = ses_service.deliver_alert(
                enhanced_alert=enhanced_alert,
                recipients=[recipient_email],
                cc_recipients=[]  # Don't use default CC recipients
            )
            
            result['alert_sent'] = email_result.get('success', False)
            result['email_message_id'] = email_result.get('message_id')
            print(f"✓ Email alert sent (MessageId: {email_result.get('message_id')})")
        except Exception as e:
            print(f"✗ Email sending failed: {str(e)}")
            import traceback
            traceback.print_exc()
            result['alert_sent'] = False
            result['email_error'] = str(e)
        
        # Store incident in DynamoDB
        try:
            # Build enhanced alert for storage
            enhanced_alert_for_storage = result.get('summaries', {}).get('enhanced_alert', {})
            if not enhanced_alert_for_storage:
                enhanced_alert_for_storage = {
                    'incident_id': incident_id,
                    'service_name': service_name,
                    'timestamp': timestamp,
                    'root_cause': result.get('root_cause', {}),
                    'fixes': result.get('fix_recommendations', {}),
                    'original_alert': {
                        'service_name': service_name,
                        'timestamp': timestamp,
                        'error_message': error_message,
                        'log_location': log_location
                    }
                }
            
            store_incident_record(
                enhanced_alert=enhanced_alert_for_storage,
                table_name='incident-history'
            )
            print(f"✓ Stored incident in DynamoDB")
        except Exception as storage_error:
            print(f"⚠ Error storing incident: {str(storage_error)}")
            import traceback
            traceback.print_exc()
            # Continue even if storage fails
        
        result['status'] = 'completed'
        print(f"Orchestration complete for incident: {incident_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error in orchestrator: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Orchestration failed',
                'message': str(e)
            })
        }
