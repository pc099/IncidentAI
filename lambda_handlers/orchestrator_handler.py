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
        
        # Agent 2: Root Cause Analysis (using log analysis results)
        try:
            print(f"Executing Root Cause Analysis...")
            
            # Extract data from log analysis
            log_analysis_data = result.get('log_analysis', {})
            bedrock_analysis = log_analysis_data.get('bedrock_analysis', {})
            
            # Get key findings and evidence
            key_findings = bedrock_analysis.get('key_findings', [])
            description = ' '.join(key_findings[:2]) if key_findings else error_message
            
            # Get error patterns as evidence
            error_patterns = log_analysis_data.get('error_patterns', [])
            evidence = [p.get('message', '') for p in error_patterns[:3]] if error_patterns else [error_message]
            
            # Determine category from error message and description
            error_lower = error_message.lower()
            description_lower = description.lower()
            combined_text = f"{error_lower} {description_lower}"
            
            if 'throttl' in combined_text or 'provisionedthroughput' in combined_text or 'capacity' in combined_text:
                category = 'resource_exhaustion'
            elif 'memory' in combined_text or 'oom' in combined_text:
                category = 'resource_exhaustion'
            elif 'timeout' in combined_text or 'connection' in combined_text:
                category = 'dependency_failure'
            elif 'config' in combined_text:
                category = 'configuration_error'
            else:
                category = 'dependency_failure'
            
            # Get confidence score from log analysis
            confidence_score = log_analysis_data.get('confidence_score', 75)
            
            root_cause = {
                'analysis': {
                    'primary_cause': {
                        'description': description,
                        'category': category,
                        'confidence_score': confidence_score,
                        'evidence': evidence
                    },
                    'similar_incidents': []
                }
            }
            
            # Query DynamoDB for similar incidents (same service and category)
            try:
                import boto3
                from boto3.dynamodb.conditions import Attr
                dynamodb = boto3.resource('dynamodb')
                table = dynamodb.Table('incident-history')
                
                # Scan for similar incidents (same service_name, limit to recent)
                response = table.scan(
                    FilterExpression=Attr('service_name').eq(service_name),
                    Limit=10
                )
                
                similar_incidents = []
                for item in response.get('Items', []):
                    # Skip current incident
                    if item.get('incident_id') == incident_id:
                        continue
                    
                    # Check if category matches
                    item_root_cause = item.get('root_cause', {})
                    if isinstance(item_root_cause, dict):
                        item_category = item_root_cause.get('category', '')
                    else:
                        item_category = ''
                    
                    if item_category == category:
                        # Extract resolution info
                        fixes = item.get('fixes', {})
                        if isinstance(fixes, dict):
                            immediate_actions = fixes.get('immediate_actions', [])
                            if immediate_actions and len(immediate_actions) > 0:
                                resolution = immediate_actions[0].get('action', 'No resolution details')
                            else:
                                resolution = 'Applied standard fixes'
                        else:
                            resolution = 'Resolved successfully'
                        
                        similar_incidents.append({
                            'incident_id': item.get('incident_id', 'unknown'),
                            'timestamp': item.get('timestamp', ''),
                            'resolution': resolution,
                            'resolution_time': '8 minutes'  # Default for POC
                        })
                
                root_cause['analysis']['similar_incidents'] = similar_incidents[:3]  # Top 3
                if similar_incidents:
                    print(f"✓ Found {len(similar_incidents)} similar incidents")
                else:
                    print(f"ℹ No similar incidents found in history")
            except Exception as kb_error:
                print(f"⚠ Could not query similar incidents: {str(kb_error)}")
                import traceback
                traceback.print_exc()
            
            result['root_cause'] = root_cause
            result['agents_executed'].append('root_cause')
            print(f"✓ Root Cause Analysis complete: {category} ({confidence_score}% confidence)")
        except Exception as e:
            print(f"✗ Root Cause Analysis failed: {str(e)}")
            import traceback
            traceback.print_exc()
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
            
            # Extract data for email formatter (it expects flat structure)
            # Communication agent stores root_cause as enhanced_alert['root_cause'] = root_cause.get('analysis', {})
            # So root_cause_data contains {primary_cause: {...}, similar_incidents: [...]}
            root_cause_data = enhanced_alert.get('root_cause', {})
            print(f"[DEBUG] root_cause_data keys: {list(root_cause_data.keys()) if isinstance(root_cause_data, dict) else 'not a dict'}")
            
            # Extract primary_cause directly
            primary_cause = root_cause_data.get('primary_cause', {}) if isinstance(root_cause_data, dict) else {}
            print(f"[DEBUG] primary_cause keys: {list(primary_cause.keys()) if isinstance(primary_cause, dict) else 'not a dict'}")
            print(f"[DEBUG] primary_cause confidence: {primary_cause.get('confidence_score', 'NOT FOUND')}")
            print(f"[DEBUG] primary_cause category: {primary_cause.get('category', 'NOT FOUND')}")
            print(f"[DEBUG] primary_cause description: {primary_cause.get('description', 'NOT FOUND')[:100] if primary_cause.get('description') else 'NOT FOUND'}")
            
            # Get fix recommendations
            # Communication agent stores fixes as enhanced_alert['fixes'] = fixes.get('recommendations', {})
            # So fixes_data already contains {immediate_actions: [...], preventive_measures: [...], rollback_plan: "..."}
            fixes_data = enhanced_alert.get('fixes', {})
            print(f"[DEBUG] fixes_data keys: {list(fixes_data.keys()) if isinstance(fixes_data, dict) else 'not a dict'}")
            
            # Extract immediate_actions directly (no nested 'recommendations' key)
            immediate_actions = fixes_data.get('immediate_actions', []) if isinstance(fixes_data, dict) else []
            print(f"[DEBUG] immediate_actions count: {len(immediate_actions)}")
            
            # Rebuild enhanced_alert with flat structure for email formatter
            email_enhanced_alert = {
                'incident_id': enhanced_alert.get('incident_id', incident_id),
                'timestamp': enhanced_alert.get('timestamp', timestamp),
                'service_name': enhanced_alert.get('service_name', service_name),
                'confidence_score': primary_cause.get('confidence_score', 0),
                'root_cause': {
                    'category': primary_cause.get('category', 'Unknown'),
                    'description': primary_cause.get('description', 'No description available'),
                    'evidence': primary_cause.get('evidence', []),
                    'similar_incidents': root_cause_data.get('similar_incidents', [])
                },
                'recommended_fixes': immediate_actions,
                'business_summary': enhanced_alert.get('business_summary', {}),
                'original_alert': enhanced_alert.get('original_alert', {})
            }
            
            # Send via SES
            ses_service = SESDeliveryService(sender_email=recipient_email)
            email_result = ses_service.deliver_alert(
                enhanced_alert=email_enhanced_alert,
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
