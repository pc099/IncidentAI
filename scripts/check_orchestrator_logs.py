"""
Check recent CloudWatch logs for orchestrator Lambda
"""

import boto3
from datetime import datetime, timedelta

def get_recent_logs(function_name="incident-orchestrator", minutes=5):
    """Get recent CloudWatch logs for Lambda function"""
    logs_client = boto3.client('logs')
    
    log_group = f"/aws/lambda/{function_name}"
    
    # Get log streams from last N minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=minutes)
    
    print(f"Fetching logs from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Get log events
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            limit=100
        )
        
        events = response.get('events', [])
        
        if not events:
            print("No recent log events found")
            return
        
        print(f"Found {len(events)} log events:\n")
        
        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
        
    except Exception as e:
        print(f"Error fetching logs: {e}")


if __name__ == "__main__":
    get_recent_logs()
