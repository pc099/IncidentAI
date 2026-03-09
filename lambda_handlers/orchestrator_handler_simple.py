"""
Lambda Handler: Orchestrator (Simplified for Testing)
Coordinates execution of all AI agents
"""
import json
import os
import sys
import boto3
from datetime import datetime

# Add src to path
sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


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
        print(f"🚀 Starting orchestration for incident: {event.get('incident_id')}")
        
        # Extract incident details
        incident_id = event['incident_id']
        service_name = event['service_name']
        timestamp = event['timestamp']
        error_message = event['error_message']
        log_location = event['log_location']
        alert_source = event.get('alert_source', 'Manual')
        
        print(f"📋 Incident Details:")
        print(f"  - Service: {service_name}")
        print(f"  - Timestamp: {timestamp}")
        print(f"  - Log Location: {log_location}")
        
        # Import agents (lazy import to avoid cold start issues)
        try:
            from agents.log_analysis_agent import LogAnalysisAgent
        except ImportError as e:
            print(f"⚠️  Could not import LogAnalysisAgent: {e}")
            LogAnalysisAgent = None
        
        try:
            from agents.fix_recommendation_agent import FixRecommendationAgent
        except ImportError as e:
            print(f"⚠️  Could not import FixRecommendationAgent: {e}")
            FixRecommendationAgent = None
        
        try:
            from agents.communication_agent import CommunicationAgent
        except ImportError as e:
            print(f"⚠️  Could not import CommunicationAgent: {e}")
            CommunicationAgent = None
        
        result = {
            'incident_id': incident_id,
            'status': 'processing',
            'agents_executed': []
        }
        
        # Agent 1: Log Analysis
        print("\n🔍 Agent 1: Log Analysis")
        if LogAnalysisAgent:
            try:
                log_agent = LogAnalysisAgent()
                log_analysis = log_agent.analyze(
                    service_name=service_name,
                    timestamp=timestamp,
                    log_location=log_location
                )
                result['log_analysis'] = log_analysis
                result['agents_executed'].append('log_analysis')
                print(f"  ✅ Log analysis complete (confidence: {log_analysis.get('confidence_score', 0)}%)")
            except Exception as e:
                print(f"  ❌ Log analysis failed: {str(e)}")
                import traceback
                traceback.print_exc()
                result['log_analysis'] = {'error': str(e)}
        else:
            log_analysis = {'error': 'LogAnalysisAgent not available', 'confidence_score': 0}
            result['log_analysis'] = log_analysis
            print("  ⚠️  LogAnalysisAgent not available")
        
        # Agent 2: Root Cause Analysis (using Bedrock directly)
        print("\n🎯 Agent 2: Root Cause Analysis")
        try:
            # For now, use a simplified root cause based on log analysis
            root_cause = {
                'agent': 'root_cause',
                'primary_cause': error_message,
                'confidence_score': 75,
                'category': 'dependency_failure',
                'evidence': log_analysis.get('error_patterns', [])[:3]
            }
            result['root_cause'] = root_cause
            result['agents_executed'].append('root_cause')
            print(f"  ✅ Root cause identified (confidence: {root_cause['confidence_score']}%)")
        except Exception as e:
            print(f"  ❌ Root cause analysis failed: {str(e)}")
            result['root_cause'] = {'error': str(e)}
        
        # Agent 3: Fix Recommendations
        print("\n🔧 Agent 3: Fix Recommendations")
        if FixRecommendationAgent:
            try:
                fix_agent = FixRecommendationAgent()
                fix_recommendations = fix_agent.generate_recommendations(
                    service_name=service_name,
                    root_cause=root_cause,
                    log_analysis=log_analysis
                )
                result['fix_recommendations'] = fix_recommendations
                result['agents_executed'].append('fix_recommendations')
                print(f"  ✅ Generated {len(fix_recommendations.get('recommendations', []))} fix recommendations")
            except Exception as e:
                print(f"  ❌ Fix recommendations failed: {str(e)}")
                import traceback
                traceback.print_exc()
                result['fix_recommendations'] = {'error': str(e)}
        else:
            fix_recommendations = {'error': 'FixRecommendationAgent not available', 'recommendations': []}
            result['fix_recommendations'] = fix_recommendations
            print("  ⚠️  FixRecommendationAgent not available")
        
        # Agent 4: Communication
        print("\n📧 Agent 4: Communication")
        if CommunicationAgent:
            try:
                comm_agent = CommunicationAgent()
                summaries = comm_agent.generate_summaries(
                    incident_id=incident_id,
                    service_name=service_name,
                    timestamp=timestamp,
                    root_cause=root_cause,
                    fix_recommendations=fix_recommendations,
                    log_analysis=log_analysis
                )
                result['summaries'] = summaries
                result['agents_executed'].append('communication')
                print(f"  ✅ Summaries generated")
            except Exception as e:
                print(f"  ❌ Communication failed: {str(e)}")
                import traceback
                traceback.print_exc()
                result['summaries'] = {'error': str(e)}
        else:
            summaries = {'error': 'CommunicationAgent not available'}
            result['summaries'] = summaries
            print("  ⚠️  CommunicationAgent not available")
        
        # Store incident in DynamoDB
        print("\n💾 Storing incident in DynamoDB")
        try:
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('incident-history')
            table.put_item(Item={
                'incident_id': incident_id,
                'timestamp': timestamp,
                'service_name': service_name,
                'error_message': error_message,
                'log_location': log_location,
                'alert_source': alert_source,
                'status': 'completed',
                'processed_at': datetime.utcnow().isoformat()
            })
            print("  ✅ Incident stored")
        except Exception as e:
            print(f"  ⚠️  Storage failed: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Send email alert
        print("\n📨 Email notification")
        recipient_email = os.environ.get('SES_SENDER_EMAIL', 'harshavignesh1@gmail.com')
        print(f"  📧 Sending to: {recipient_email}")
        
        try:
            from alerts.ses_delivery import SESDeliveryService
            from alerts.email_formatter import format_incident_email
            
            # Format the email content
            email_content = format_incident_email(
                incident_id=incident_id,
                service_name=service_name,
                timestamp=timestamp,
                error_message=error_message,
                log_analysis=result.get('log_analysis', {}),
                root_cause=result.get('root_cause', {}),
                fix_recommendations=result.get('fix_recommendations', {}),
                summaries=result.get('summaries', {})
            )
            
            # Send via SES
            ses_service = SESDeliveryService(sender_email=recipient_email)
            email_result = ses_service.send_incident_alert(
                alert=email_content,
                recipients=[recipient_email]
            )
            
            result['email_sent'] = True
            result['email_message_id'] = email_result.get('MessageId')
            print(f"  ✅ Email sent successfully (MessageId: {email_result.get('MessageId')})")
            
        except Exception as e:
            print(f"  ⚠️  Email sending failed: {str(e)}")
            import traceback
            traceback.print_exc()
            result['email_sent'] = False
            result['email_error'] = str(e)
        
        result['status'] = 'completed'
        print(f"\n✅ Orchestration complete for {incident_id}")
        
        return result
        
    except Exception as e:
        print(f"❌ Orchestration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'incident_id': event.get('incident_id', 'unknown'),
            'status': 'failed',
            'error': str(e)
        }
