#!/usr/bin/env python3
"""
Get the latest Lambda execution logs
"""

import boto3
import time

logs = boto3.client('logs')

# Get the latest log stream
response = logs.describe_log_streams(
    logGroupName='/aws/lambda/incident-orchestrator',
    orderBy='LastEventTime',
    descending=True,
    limit=1
)

if not response['logStreams']:
    print("No log streams found")
    exit(1)

log_stream_name = response['logStreams'][0]['logStreamName']
print(f"Latest log stream: {log_stream_name}")
print("=" * 80)

# Get the log events
response = logs.get_log_events(
    logGroupName='/aws/lambda/incident-orchestrator',
    logStreamName=log_stream_name,
    limit=100
)

for event in response['events']:
    message = event['message'].strip()
    if message:
        # Remove unicode characters that cause encoding issues
        message = message.encode('ascii', 'ignore').decode('ascii')
        print(message)
