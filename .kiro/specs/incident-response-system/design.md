# Design Document: AI-Powered Incident Response System

## Overview

The AI-Powered Incident Response System is a serverless, multi-agent architecture built on AWS that automatically analyzes operational failures and provides actionable remediation guidance. The system leverages AWS Strands Agents framework to orchestrate four specialized AI agents, each powered by Amazon Bedrock's Claude models, to collaboratively analyze incidents from detection through resolution recommendation. The system uses Bedrock AgentCore as the runtime platform for agent execution, providing memory management, security controls, and observability. Historical incident data is stored in a Bedrock Knowledge Base to enable RAG-powered root cause analysis.

### Architecture Philosophy

The design follows these core principles:

1. **Serverless-First**: All components use serverless AWS services to minimize operational overhead and costs
2. **Agent Specialization**: Each agent has a single, well-defined responsibility following the single responsibility principle
3. **Sequential Orchestration**: Agents execute in a deterministic sequence with clear data handoffs
4. **Fail-Safe Design**: Partial results are preserved even when individual agents fail
5. **Cost-Conscious**: Architecture stays within AWS Free Tier limits through careful resource selection and usage patterns

### Key Design Decisions

- **AWS Strands Agents over Step Functions**: Strands provides built-in memory, security, and observability specifically designed for multi-agent AI workflows
- **Bedrock AgentCore for Agent Runtime**: AgentCore provides a managed runtime layer with memory management, security gateway, policy controls, and session management, reducing operational complexity
- **Bedrock Knowledge Base for RAG**: Automatically manages embeddings and vector search for historical incidents, eliminating the need for a separate vector database like OpenSearch
- **SES over SNS for Email Delivery**: SES enables rich HTML email formatting with better presentation of incident details, while SNS is retained only for internal system notifications
- **Sequential vs Parallel Agent Execution**: Sequential execution ensures each agent builds on previous results, improving accuracy over parallel execution
- **DynamoDB for Incident History**: NoSQL design supports flexible schema evolution as failure patterns are discovered
- **S3 for Log Storage**: Cost-effective storage with lifecycle policies for aging data
- **API Gateway for Ingestion**: Provides rate limiting, authentication, and request validation out of the box

## Architecture

### System Context Diagram

```
┌─────────────────┐
│   CloudWatch    │
│   EventBridge   │
└────────┬────────┘
         │ Alert Trigger
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                               │
│                  /incidents endpoint                         │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Lambda                             │
│         (AWS Strands Agents Framework)                       │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│           Bedrock AgentCore Runtime Layer                    │
│  (Memory, Security Gateway, Policy Controls, Observability)  │
└────────┬────────────────────────────────────────────────────┘
         │
         ├──────────────────┬──────────────────┬──────────────┐
         ▼                  ▼                  ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│Log Analysis  │  │ Root Cause   │  │Fix Recommend │  │Communication │
│   Agent      │→ │   Agent      │→ │   Agent      │→ │   Agent      │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│              Amazon Bedrock (Claude Models)                   │
└──────────────────────────────────────────────────────────────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────┐    ┌──────────────┐    ┌──────────┐
│    S3    │    │  DynamoDB    │    │   SES    │
│  Logs    │    │   Incident   │    │  Email   │
│          │    │   History    │    │ Delivery │
└──────────┘    └──────────────┘    └──────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Bedrock Knowledge│
              │      Base        │
              │  (Vector Search) │
              └──────────────────┘
```

### Component Flow

1. **Alert Ingestion**: CloudWatch/EventBridge → API Gateway → Orchestrator Lambda
2. **Agent Orchestration**: Orchestrator invokes agents sequentially via AWS Strands → Bedrock AgentCore
3. **Log Analysis**: Agent retrieves logs from S3, analyzes patterns
4. **Root Cause Analysis**: Agent receives log analysis, queries Bedrock Knowledge Base for similar incidents, determines root cause
5. **Fix Recommendation**: Agent generates remediation steps based on root cause
6. **Communication**: Agent formats results for different audiences
7. **Alert Delivery**: Enhanced alert sent via SES with rich HTML formatting
8. **Knowledge Base Update**: Incident stored in DynamoDB and indexed in Bedrock Knowledge Base

### Data Flow

```
Alert Event → API Gateway → Orchestrator
                              ↓
                         Bedrock AgentCore
                              ↓
                         Log Analysis Agent
                              ↓ (log summary)
                         Root Cause Agent ←─── Bedrock Knowledge Base (similar incidents)
                              ↓ (root cause + confidence)
                         Fix Recommendation Agent
                              ↓ (remediation steps)
                         Communication Agent
                              ↓ (enhanced alert)
                         SES → Recipients (HTML email)
                              ↓
                         DynamoDB (store incident)
                              ↓
                         Bedrock Knowledge Base (index for future RAG)
```

## Components and Interfaces

### 1. API Gateway Endpoint

**Responsibility**: Receive and validate incident trigger requests

**Interface**:
```
POST /incidents
Content-Type: application/json

Request Body:
{
  "service_name": string,
  "timestamp": ISO8601 string,
  "error_message": string,
  "log_location": string (S3 URI),
  "alert_source": string (CloudWatch | EventBridge | Manual)
}

Response (202 Accepted):
{
  "incident_id": string (UUID),
  "status": "processing",
  "message": "Incident analysis initiated"
}

Response (400 Bad Request):
{
  "error": string,
  "details": string
}
```

**Implementation Notes**:
- Uses API key authentication for external integrations
- IAM authentication for AWS service integrations
- Rate limiting: 100 requests/minute per API key
- Request validation using JSON Schema

### 2. Orchestrator Lambda

**Responsibility**: Coordinate agent execution using AWS Strands Agents framework

**Key Functions**:
- `handle_incident(event)`: Entry point for incident processing
- `invoke_agent_sequence(incident_data)`: Execute agents in order
- `handle_agent_failure(agent_name, error)`: Retry logic and partial result handling
- `aggregate_results(agent_outputs)`: Combine agent outputs into enhanced alert

**Agent Invocation Sequence**:
```python
def invoke_agent_sequence(incident_data):
    # Step 1: Log Analysis
    log_summary = invoke_agent("log-analysis", {
        "log_location": incident_data["log_location"],
        "timestamp": incident_data["timestamp"],
        "service_name": incident_data["service_name"]
    })
    
    # Step 2: Root Cause Analysis
    root_cause = invoke_agent("root-cause", {
        "log_summary": log_summary,
        "service_name": incident_data["service_name"],
        "error_message": incident_data["error_message"]
    })
    
    # Step 3: Fix Recommendation
    fixes = invoke_agent("fix-recommendation", {
        "root_cause": root_cause,
        "service_name": incident_data["service_name"]
    })
    
    # Step 4: Communication
    enhanced_alert = invoke_agent("communication", {
        "root_cause": root_cause,
        "fixes": fixes,
        "original_alert": incident_data
    })
    
    return enhanced_alert
```

**Error Handling**:
- Exponential backoff: 1s, 2s, 4s for retries
- Partial results preserved if later agents fail
- All failures logged to CloudWatch with context

### 2.5. Bedrock AgentCore Runtime Layer

**Responsibility**: Provide managed runtime environment for agent execution with built-in capabilities

**Core Capabilities**:

1. **Memory Management**:
   - Maintains conversation context across agent invocations
   - Stores intermediate results for agent handoffs
   - Provides session persistence for multi-turn interactions

2. **Security Gateway**:
   - Enforces IAM policies for agent actions
   - Validates agent inputs and outputs
   - Prevents unauthorized access to AWS resources

3. **Policy Controls**:
   - Defines allowed actions for each agent
   - Enforces guardrails on agent behavior
   - Limits resource access per agent role

4. **Observability**:
   - Automatic logging of all agent interactions
   - Traces agent execution flow
   - Emits metrics for agent performance

5. **Session Management**:
   - Creates isolated sessions per incident
   - Manages session lifecycle (create, execute, terminate)
   - Cleans up resources after incident resolution

**Architecture Position**:
```
Strands Orchestrator
        ↓
   AgentCore Runtime
        ↓
   Individual Agents
```

**Integration with Agents**:
- All agent invocations go through AgentCore
- AgentCore maintains execution context
- Provides consistent error handling across agents
- Manages agent-to-agent communication

**Configuration**:
```python
agentcore_config = {
    "session_timeout": 300,  # 5 minutes
    "memory_retention": "per_incident",
    "security_policy": "least_privilege",
    "observability": {
        "logging": "detailed",
        "metrics": "enabled",
        "tracing": "enabled"
    }
}
```

**Benefits**:
- Reduces boilerplate code in individual agents
- Centralized security and policy enforcement
- Consistent observability across all agents
- Simplified agent development and maintenance

### 3. Log Analysis Agent

**Responsibility**: Retrieve and analyze logs to identify error patterns

**Input Interface**:
```json
{
  "log_location": "s3://bucket/path/to/logs",
  "timestamp": "2025-01-15T10:30:00Z",
  "service_name": "payment-processor"
}
```

**Output Interface**:
```json
{
  "agent": "log-analysis",
  "summary": {
    "error_patterns": [
      {
        "pattern": "ConnectionTimeout",
        "occurrences": 15,
        "first_seen": "2025-01-15T10:28:45Z",
        "last_seen": "2025-01-15T10:30:12Z"
      }
    ],
    "stack_traces": [
      {
        "exception": "java.net.SocketTimeoutException",
        "location": "PaymentClient.java:142",
        "message": "Read timed out"
      }
    ],
    "relevant_excerpts": [
      "2025-01-15T10:30:00Z ERROR Failed to connect to payment-gateway.example.com:443"
    ],
    "log_volume": "2.3 MB",
    "time_range": "10:15:00 - 10:35:00"
  }
}
```

**Processing Logic**:
1. Calculate time window: [timestamp - 15min, timestamp + 5min]
2. Retrieve logs from S3 using service_name and time window
3. Parse logs to extract error messages, stack traces, timestamps
4. Identify patterns using regex and frequency analysis
5. Extract top 5 most relevant log excerpts
6. Generate structured summary

**Bedrock Prompt Template**:
```
Analyze the following logs from a failed service and identify error patterns:

Service: {service_name}
Failure Time: {timestamp}
Logs:
{log_content}

Provide:
1. Primary error patterns with occurrence counts
2. Stack traces if present
3. Most relevant log excerpts (max 5)
4. Any anomalies or unusual patterns

Format your response as structured JSON.
```

### 4. Root Cause Agent

**Responsibility**: Determine the most likely root cause with confidence scoring, leveraging historical incident data via RAG

**Input Interface**:
```json
{
  "log_summary": { /* output from Log Analysis Agent */ },
  "service_name": "payment-processor",
  "error_message": "Service health check failed"
}
```

**Output Interface**:
```json
{
  "agent": "root-cause",
  "analysis": {
    "primary_cause": {
      "category": "dependency_failure",
      "description": "External payment gateway timeout",
      "confidence_score": 85,
      "evidence": [
        "15 consecutive connection timeouts to payment-gateway.example.com",
        "No similar issues in past 30 days",
        "Service logs show healthy internal state"
      ]
    },
    "alternative_causes": [
      {
        "category": "resource_exhaustion",
        "description": "Network bandwidth saturation",
        "confidence_score": 35,
        "evidence": ["High request volume observed"]
      }
    ],
    "similar_incidents": [
      {
        "incident_id": "inc-2024-11-23-001",
        "similarity_score": 0.78,
        "resolution": "Increased timeout threshold to 30s",
        "root_cause": "Payment gateway timeout"
      }
    ]
  }
}
```

**Processing Logic**:
1. Query Bedrock Knowledge Base for similar past incidents using semantic search
   - Convert current incident to embedding
   - Retrieve top 3-5 most similar incidents by vector similarity
   - Include incident details and resolutions
2. Classify failure into: configuration_error, resource_exhaustion, or dependency_failure
3. Calculate confidence score based on:
   - Pattern clarity (40% weight)
   - Historical similarity (30% weight)
   - Evidence strength (30% weight)
4. Rank alternative causes by confidence
5. Include similar incidents with similarity scores

**Bedrock Knowledge Base Integration**:
```python
def query_similar_incidents(log_summary, service_name, error_message):
    # Create query from current incident
    query_text = f"""
    Service: {service_name}
    Error: {error_message}
    Patterns: {', '.join(log_summary['error_patterns'])}
    """
    
    # Query Bedrock Knowledge Base
    response = bedrock_agent_runtime.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={
            "text": query_text
        },
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": 5
            }
        }
    )
    
    # Extract similar incidents
    similar_incidents = []
    for result in response['retrievalResults']:
        similar_incidents.append({
            "incident_id": result['metadata']['incident_id'],
            "similarity_score": result['score'],
            "resolution": result['content']['text'],
            "root_cause": result['metadata']['root_cause']
        })
    
    return similar_incidents
```

**Bedrock Prompt Template**:
```
You are a root cause analysis expert. Analyze this incident:

Service: {service_name}
Error: {error_message}
Log Analysis: {log_summary}

Similar Past Incidents (from Knowledge Base):
{similar_incidents}

These similar incidents were retrieved using semantic search. Pay special attention to:
- How these past incidents were resolved
- Common patterns between current and past incidents
- Root causes identified in similar scenarios

Classify the root cause into one of:
- configuration_error: Invalid config values, missing parameters
- resource_exhaustion: Memory, CPU, disk space issues
- dependency_failure: External service timeouts, database connection failures

Provide:
1. Primary root cause with confidence score (0-100)
2. Supporting evidence from logs
3. Alternative causes if applicable
4. How similar incidents were resolved

Format as structured JSON.
```

**Confidence Score Calculation**:
```python
def calculate_confidence(pattern_clarity, historical_match, evidence_strength):
    # pattern_clarity: 0-100 (how clear the error pattern is)
    # historical_match: 0-100 (similarity to past incidents from Knowledge Base)
    # evidence_strength: 0-100 (quality of supporting evidence)
    
    confidence = (
        pattern_clarity * 0.4 +
        historical_match * 0.3 +
        evidence_strength * 0.3
    )
    return round(confidence)
```

**Knowledge Base Benefits**:
- Automatic embedding generation (no manual vector management)
- Semantic search finds conceptually similar incidents, not just keyword matches
- Continuously improves as more incidents are added
- No need to manage OpenSearch or other vector databases

### 5. Fix Recommendation Agent

**Responsibility**: Generate actionable remediation steps

**Input Interface**:
```json
{
  "root_cause": { /* output from Root Cause Agent */ },
  "service_name": "payment-processor"
}
```

**Output Interface**:
```json
{
  "agent": "fix-recommendation",
  "recommendations": {
    "immediate_actions": [
      {
        "step": 1,
        "action": "Increase connection timeout",
        "command": "aws lambda update-function-configuration --function-name payment-processor --timeout 30",
        "estimated_time": "2 minutes",
        "risk_level": "low"
      },
      {
        "step": 2,
        "action": "Verify payment gateway health",
        "command": "curl -I https://payment-gateway.example.com/health",
        "estimated_time": "1 minute",
        "risk_level": "none"
      }
    ],
    "preventive_measures": [
      {
        "action": "Implement circuit breaker pattern",
        "description": "Add circuit breaker to prevent cascade failures",
        "priority": "high"
      },
      {
        "action": "Add dependency health monitoring",
        "description": "Monitor payment gateway availability proactively",
        "priority": "medium"
      }
    ],
    "rollback_plan": "Revert timeout to 10s if issues persist: aws lambda update-function-configuration --function-name payment-processor --timeout 10"
  }
}
```

**Processing Logic**:
1. Map root cause category to fix templates
2. Customize fixes based on service_name and specific error details
3. Query incident history for previously successful fixes
4. Generate 2-5 immediate action steps
5. Include preventive measures for long-term reliability
6. Provide rollback plan for each change

**Fix Templates by Category**:

**Configuration Error**:
- Identify misconfigured parameter
- Provide correct value or format
- Show command to update configuration
- Suggest validation steps

**Resource Exhaustion**:
- Identify exhausted resource (memory, CPU, disk)
- Calculate recommended scaling (e.g., 2x current limit)
- Provide scaling commands
- Suggest monitoring thresholds

**Dependency Failure**:
- Verify dependency health
- Increase timeout/retry settings
- Implement fallback mechanisms
- Add circuit breaker if not present

**Common AWS Failure Scenarios**:

1. **Lambda Deployment Failure**:
   - Check deployment package size
   - Verify IAM role permissions
   - Review CloudWatch logs for deployment errors
   - Rollback to previous version if needed

2. **DynamoDB Throttling**:
   - Check current read/write capacity units
   - Enable auto-scaling if not configured
   - Implement exponential backoff in application
   - Consider on-demand billing mode

3. **RDS Storage Full**:
   - Check current storage usage
   - Increase allocated storage
   - Enable storage auto-scaling
   - Archive or delete old data

4. **Lambda Concurrent Execution Limit**:
   - Check current concurrency usage
   - Request limit increase via AWS Support
   - Implement queue-based processing
   - Add reserved concurrency for critical functions

5. **API Gateway Timeout to External Service**:
   - Increase API Gateway timeout (max 29s)
   - Implement async processing pattern
   - Add retry logic with exponential backoff
   - Consider circuit breaker pattern

### 6. Communication Agent

**Responsibility**: Format analysis results for different audiences

**Input Interface**:
```json
{
  "root_cause": { /* output from Root Cause Agent */ },
  "fixes": { /* output from Fix Recommendation Agent */ },
  "original_alert": { /* original incident data */ }
}
```

**Output Interface**:
```json
{
  "agent": "communication",
  "enhanced_alert": {
    "incident_id": "inc-2025-01-15-001",
    "timestamp": "2025-01-15T10:30:00Z",
    "service_name": "payment-processor",
    "technical_summary": {
      "title": "Payment Processor - Dependency Failure",
      "root_cause": "External payment gateway timeout (85% confidence)",
      "evidence": "15 consecutive connection timeouts to payment-gateway.example.com",
      "immediate_fix": "Increase connection timeout to 30s",
      "command": "aws lambda update-function-configuration --function-name payment-processor --timeout 30",
      "estimated_resolution": "3 minutes"
    },
    "business_summary": {
      "title": "Payment Processing Temporarily Unavailable",
      "impact": "Payment transactions are failing due to external gateway connectivity issues",
      "status": "Root cause identified, fix in progress",
      "estimated_resolution": "3 minutes",
      "user_impact": "Customers may experience payment failures"
    },
    "confidence_score": 85,
    "confidence_warning": null
  }
}
```

**Processing Logic**:
1. Extract key information from root cause and fixes
2. Generate technical summary with commands and evidence
3. Generate business summary without technical jargon
4. Add confidence warning if score < 50
5. Include incident_id for tracking
6. Format for email and ticket systems

**Bedrock Prompt Template**:
```
Create two summaries for this incident:

Root Cause: {root_cause}
Fixes: {fixes}
Confidence: {confidence_score}

1. Technical Summary (for engineers):
   - Include specific error details
   - Show exact commands to run
   - Reference log evidence
   
2. Business Summary (for non-technical stakeholders):
   - Explain in plain language
   - Focus on user impact
   - Avoid technical jargon
   - Provide time estimates

Keep both summaries concise (max 5 sentences each).
```

### 7. Alert Delivery Service

**Responsibility**: Send enhanced alerts via SES with rich HTML formatting

**Implementation**:
```python
def deliver_enhanced_alert(enhanced_alert):
    incident_id = enhanced_alert["incident_id"]
    
    # Format HTML email
    email_html = format_html_email(enhanced_alert)
    
    # Send via SES
    ses_client.send_email(
        Source="incidents@example.com",
        Destination={
            "ToAddresses": get_oncall_engineers(),
            "CcAddresses": get_stakeholders()
        },
        Message={
            "Subject": {
                "Data": f"🚨 [{incident_id}] {enhanced_alert['technical_summary']['title']}"
            },
            "Body": {
                "Html": {
                    "Data": email_html,
                    "Charset": "UTF-8"
                },
                "Text": {
                    "Data": format_text_email(enhanced_alert),
                    "Charset": "UTF-8"
                }
            }
        },
        ReplyToAddresses=["incident-response@example.com"]
    )
    
    # Store in DynamoDB
    store_incident_history(enhanced_alert)
    
    # Index in Bedrock Knowledge Base for future RAG
    index_in_knowledge_base(enhanced_alert)
```

**HTML Email Template**:
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background-color: #d32f2f; color: white; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; background-color: #f5f5f5; border-radius: 5px; }
        .confidence-high { color: #2e7d32; font-weight: bold; }
        .confidence-medium { color: #f57c00; font-weight: bold; }
        .confidence-low { color: #c62828; font-weight: bold; }
        .command { background-color: #263238; color: #aed581; padding: 10px; border-radius: 3px; font-family: monospace; }
        .action-item { margin: 10px 0; padding: 10px; background-color: white; border-left: 4px solid #1976d2; }
        .metadata { font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚨 Incident Alert: {incident_id}</h1>
        <p class="metadata">Service: {service_name} | Time: {timestamp}</p>
    </div>
    
    <div class="section">
        <h2>Root Cause Analysis</h2>
        <p><strong>Category:</strong> {root_cause_category}</p>
        <p><strong>Description:</strong> {root_cause_description}</p>
        <p><strong>Confidence:</strong> <span class="confidence-{level}">{confidence_score}%</span></p>
        
        <h3>Evidence:</h3>
        <ul>
            {evidence_items}
        </ul>
    </div>
    
    <div class="section">
        <h2>Immediate Actions</h2>
        {action_items}
    </div>
    
    <div class="section">
        <h2>Commands to Execute</h2>
        <div class="command">
            {commands}
        </div>
    </div>
    
    <div class="section">
        <h2>Business Impact</h2>
        <p>{business_summary}</p>
        <p><strong>Estimated Resolution:</strong> {estimated_time}</p>
    </div>
    
    <div class="section">
        <h2>Similar Past Incidents</h2>
        {similar_incidents}
    </div>
    
    <div class="metadata">
        <p>This alert was generated by the AI-Powered Incident Response System</p>
        <p>Reply to this email or visit the incident dashboard for more details</p>
    </div>
</body>
</html>
```

**Action Item Template**:
```html
<div class="action-item">
    <strong>Step {step_number}:</strong> {action_description}
    <br>
    <span class="metadata">Time: {estimated_time} | Risk: {risk_level}</span>
</div>
```

**Text Email Fallback**:
```
INCIDENT ALERT: {incident_id}
Service: {service_name}
Time: {timestamp}

ROOT CAUSE ({confidence_score}% confidence):
{root_cause_description}

EVIDENCE:
- {evidence_1}
- {evidence_2}

IMMEDIATE ACTIONS:
1. {action_1}
2. {action_2}

COMMANDS:
{commands}

BUSINESS IMPACT:
{business_summary}

Estimated Resolution: {estimated_time}
```

**Email Formatting Logic**:
```python
def format_html_email(enhanced_alert):
    # Determine confidence level class
    confidence = enhanced_alert['confidence_score']
    if confidence >= 70:
        confidence_class = "high"
    elif confidence >= 40:
        confidence_class = "medium"
    else:
        confidence_class = "low"
    
    # Format evidence items
    evidence_html = "\n".join([
        f"<li>{item}</li>" 
        for item in enhanced_alert['technical_summary']['evidence']
    ])
    
    # Format action items
    actions_html = "\n".join([
        f"""
        <div class="action-item">
            <strong>Step {action['step']}:</strong> {action['action']}
            <br>
            <span class="metadata">Time: {action['estimated_time']} | Risk: {action['risk_level']}</span>
        </div>
        """
        for action in enhanced_alert['fixes']['immediate_actions']
    ])
    
    # Format commands
    commands_html = "\n".join([
        action['command'] 
        for action in enhanced_alert['fixes']['immediate_actions']
        if 'command' in action
    ])
    
    # Format similar incidents
    similar_html = "\n".join([
        f"<p>• {inc['incident_id']} (similarity: {inc['similarity_score']:.0%}) - {inc['resolution']}</p>"
        for inc in enhanced_alert['analysis']['similar_incidents']
    ])
    
    # Render template
    return HTML_TEMPLATE.format(
        incident_id=enhanced_alert['incident_id'],
        service_name=enhanced_alert['service_name'],
        timestamp=enhanced_alert['timestamp'],
        root_cause_category=enhanced_alert['analysis']['primary_cause']['category'],
        root_cause_description=enhanced_alert['analysis']['primary_cause']['description'],
        confidence_score=confidence,
        level=confidence_class,
        evidence_items=evidence_html,
        action_items=actions_html,
        commands=commands_html,
        business_summary=enhanced_alert['business_summary']['impact'],
        estimated_time=enhanced_alert['business_summary']['estimated_resolution'],
        similar_incidents=similar_html
    )
```

**SES Configuration**:
- Verified sender domain: incidents.example.com
- DKIM signing enabled for email authentication
- Bounce and complaint handling via SNS
- Email sending rate: 14 emails/second (Free Tier limit)
- Daily sending quota: 200 emails (Free Tier limit)

## Data Models

### Incident Record (DynamoDB)

**Table Name**: `incident-history`

**Primary Key**: 
- Partition Key: `incident_id` (String, UUID)
- Sort Key: `timestamp` (String, ISO8601)

**Global Secondary Index**:
- GSI Name: `service-timestamp-index`
- Partition Key: `service_name` (String)
- Sort Key: `timestamp` (String)

**Attributes**:
```json
{
  "incident_id": "inc-2025-01-15-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "service_name": "payment-processor",
  "failure_type": "dependency_failure",
  "root_cause": {
    "category": "dependency_failure",
    "description": "External payment gateway timeout",
    "confidence_score": 85
  },
  "error_patterns": [
    "ConnectionTimeout",
    "SocketTimeoutException"
  ],
  "fix_applied": {
    "action": "Increased connection timeout to 30s",
    "timestamp": "2025-01-15T10:35:00Z",
    "applied_by": "auto"
  },
  "resolution_time_seconds": 300,
  "similar_to": ["inc-2024-11-23-001"],
  "log_location": "s3://logs/payment-processor/2025-01-15/",
  "enhanced_alert": { /* full enhanced alert object */ },
  "ttl": 1768089000
}
```

**TTL**: 90 days (automatically delete old incidents)

### Bedrock Knowledge Base Document

**Knowledge Base Name**: `incident-history-kb`

**Data Source**: S3 bucket synced from DynamoDB

**Document Structure**:
```json
{
  "incident_id": "inc-2025-01-15-001",
  "service_name": "payment-processor",
  "failure_type": "dependency_failure",
  "error_patterns": ["ConnectionTimeout", "SocketTimeoutException"],
  "root_cause": {
    "category": "dependency_failure",
    "description": "External payment gateway timeout",
    "confidence_score": 85
  },
  "resolution": {
    "action": "Increased connection timeout to 30s",
    "success": true,
    "resolution_time_seconds": 300
  },
  "log_summary": "15 consecutive connection timeouts to payment-gateway.example.com",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Metadata Fields** (for filtering):
- `incident_id`: String
- `service_name`: String
- `failure_type`: String (configuration_error | resource_exhaustion | dependency_failure)
- `root_cause`: String
- `timestamp`: String (ISO8601)

**Embedding Strategy**:
- Bedrock automatically generates embeddings from document text
- Embeddings created from: error_patterns + root_cause.description + log_summary
- Vector dimension: 1536 (Amazon Titan Embeddings)

**Sync Process**:
```python
def sync_to_knowledge_base(incident_record):
    # Convert DynamoDB record to Knowledge Base document
    kb_document = {
        "incident_id": incident_record["incident_id"],
        "service_name": incident_record["service_name"],
        "failure_type": incident_record["failure_type"],
        "error_patterns": incident_record["error_patterns"],
        "root_cause": incident_record["root_cause"],
        "resolution": incident_record["fix_applied"],
        "log_summary": incident_record["enhanced_alert"]["technical_summary"]["evidence"],
        "timestamp": incident_record["timestamp"]
    }
    
    # Write to S3 (Knowledge Base data source)
    s3_client.put_object(
        Bucket=KB_DATA_SOURCE_BUCKET,
        Key=f"incidents/{incident_record['incident_id']}.json",
        Body=json.dumps(kb_document)
    )
    
    # Trigger Knowledge Base sync (automatic or manual)
    bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        dataSourceId=DATA_SOURCE_ID
    )
```

**Query Configuration**:
- Number of results: 5 (top 5 most similar)
- Similarity threshold: 0.6 (60% similarity minimum)
- Hybrid search: Combines semantic and keyword search

**Knowledge Base Benefits**:
- No manual embedding management
- Automatic vector indexing
- Built-in similarity search
- Scales automatically with incident volume
- No OpenSearch infrastructure needed

### Alert Event (API Gateway Input)

```json
{
  "service_name": "payment-processor",
  "timestamp": "2025-01-15T10:30:00Z",
  "error_message": "Service health check failed",
  "log_location": "s3://logs/payment-processor/2025-01-15/10-30.log",
  "alert_source": "CloudWatch",
  "metadata": {
    "alarm_name": "payment-processor-health-check",
    "alarm_state": "ALARM",
    "region": "us-east-1"
  }
}
```

### Agent Communication Schema

**Base Agent Message**:
```json
{
  "agent": "agent-name",
  "execution_id": "uuid",
  "timestamp": "ISO8601",
  "status": "success | failure | partial",
  "execution_time_ms": 1234,
  "payload": { /* agent-specific output */ }
}
```

**Error Message**:
```json
{
  "agent": "agent-name",
  "execution_id": "uuid",
  "timestamp": "ISO8601",
  "status": "failure",
  "error": {
    "code": "BEDROCK_TIMEOUT",
    "message": "Bedrock API call timed out after 30s",
    "retryable": true
  }
}
```

### Log Storage Structure (S3)

**Bucket**: `incident-logs-{account-id}`

**Path Structure**:
```
s3://incident-logs-{account-id}/
  ├── {service-name}/
  │   ├── {year}/
  │   │   ├── {month}/
  │   │   │   ├── {day}/
  │   │   │   │   ├── {hour}-{minute}.log
```

**Example**:
```
s3://incident-logs-123456789/
  ├── payment-processor/
  │   ├── 2025/
  │   │   ├── 01/
  │   │   │   ├── 15/
  │   │   │   │   ├── 10-30.log
```

**Lifecycle Policy**:
- Transition to S3 Standard-IA after 30 days
- Delete after 90 days


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Alert Receipt Timing

*For any* alert event from CloudWatch or EventBridge, the system should receive and begin processing the alert within 5 seconds of the event occurring.

**Validates: Requirements 1.1, 1.2**

### Property 2: Alert Payload Validation

*For any* incoming alert payload, if the payload is valid (contains required fields: service_name, timestamp, error_message, log_location), the system should accept it and extract all fields; if the payload is invalid, the system should reject it with a 400 status code and log the error.

**Validates: Requirements 1.3, 1.4, 1.5**

### Property 3: Orchestrator Invocation Timing

*For any* valid alert received by the API Gateway, the orchestrator should be invoked within 2 seconds.

**Validates: Requirements 1.6**

### Property 4: Log Time Window Calculation

*For any* failure timestamp, the Log Analysis Agent should retrieve logs from exactly 15 minutes before to 5 minutes after the timestamp.

**Validates: Requirements 2.2**

### Property 5: Log Parsing Completeness

*For any* logs containing error messages or stack traces, the Log Analysis Agent should extract and parse all error codes, error messages, and stack trace information present in the logs.

**Validates: Requirements 2.4, 2.5**

### Property 6: Log Analysis Output Structure

*For any* completed log analysis, the output should contain a structured summary with error patterns, timestamps, and relevant log excerpts.

**Validates: Requirements 2.6**

### Property 7: Root Cause Classification

*For any* failure analysis, the Root Cause Agent should classify the failure into exactly one of three categories: configuration_error, resource_exhaustion, or dependency_failure.

**Validates: Requirements 3.2**

### Property 8: Confidence Score Bounds

*For any* root cause identification, the confidence score should be a number between 0 and 100 (inclusive).

**Validates: Requirements 3.3**

### Property 9: Root Cause Ranking

*For any* analysis with multiple potential root causes, the causes should be ranked in descending order by confidence score (highest confidence first).

**Validates: Requirements 3.4**

### Property 10: Historical Pattern Integration

*For any* two identical failure scenarios, when one has similar historical incidents and the other doesn't, the confidence score should be higher for the scenario with historical data.

**Validates: Requirements 3.6**

### Property 11: Root Cause Output Structure

*For any* completed root cause analysis, the output should contain the primary root cause, confidence score, and supporting evidence.

**Validates: Requirements 3.7**

### Property 12: Fix Recommendation Count

*For any* fix recommendation output, the number of immediate action steps should be between 2 and 5 (inclusive).

**Validates: Requirements 4.2**

### Property 13: Category-Specific Fix Content

*For any* root cause in a specific category (configuration_error, resource_exhaustion, or dependency_failure), the fix recommendations should include category-appropriate details: configuration parameters for config errors, scaling values for resource exhaustion, or health checks for dependency failures.

**Validates: Requirements 4.3, 4.4, 4.5**

### Property 14: Fix Time Estimates

*For any* fix recommendation, each action step should include an estimated time to resolution.

**Validates: Requirements 4.6**

### Property 15: Dual Summary Generation

*For any* completed analysis, the Communication Agent should generate exactly two summaries: one technical and one non-technical.

**Validates: Requirements 5.1**

### Property 16: Technical Summary Completeness

*For any* technical summary, it should include root cause details, log excerpts, and specific remediation commands.

**Validates: Requirements 5.2**

### Property 17: Confidence Score in Summaries

*For any* generated summary (technical or non-technical), it should include the confidence score.

**Validates: Requirements 5.4**

### Property 18: User Impact for User-Facing Services

*For any* incident affecting a user-facing service, the non-technical summary should include estimated user impact; for non-user-facing services, user impact may be omitted.

**Validates: Requirements 5.5**

### Property 19: Agent Execution Sequence

*For any* incident processing, agents should be invoked in this exact order: Log_Analysis_Agent, then Root_Cause_Agent, then Fix_Recommendation_Agent, then Communication_Agent.

**Validates: Requirements 6.1**

### Property 20: Agent Output Handoff Timing

*For any* agent completion, the output should be passed to the next agent within 1 second.

**Validates: Requirements 6.2**

### Property 21: Agent Retry Behavior

*For any* agent failure, the orchestrator should retry the agent invocation up to 2 times with exponential backoff (1s, 2s, 4s).

**Validates: Requirements 6.3**

### Property 22: Partial Results Preservation

*For any* agent that fails after all retries, the orchestrator should log the failure and continue processing with partial results from successful agents.

**Validates: Requirements 6.4**

### Property 23: Enhanced Alert Structure

*For any* completed orchestration, the final output should be an Enhanced_Alert containing aggregated results from all agents.

**Validates: Requirements 6.5**

### Property 24: Alert Delivery Timing

*For any* ready Enhanced_Alert, it should be delivered via SES within 10 seconds.

**Validates: Requirements 7.1**

### Property 25: Alert Content Completeness

*For any* sent alert, it should include both the original alert information and the AI-generated analysis (root cause, fixes, confidence score).

**Validates: Requirements 7.2**

### Property 26: Alert Section Structure

*For any* formatted alert, it should contain these sections: Summary, Root Cause, Recommended Fixes, and Confidence Score.

**Validates: Requirements 7.3**

### Property 27: Low Confidence Warning

*For any* alert with a confidence score below 50, the alert should include a warning that manual investigation is recommended.

**Validates: Requirements 7.4**

### Property 28: Incident ID Uniqueness

*For any* two alerts sent by the system, they should have different incident IDs (uniqueness property).

**Validates: Requirements 7.5**

### Property 29: Alert Delivery Retry

*For any* failed alert delivery, the system should retry up to 3 times and log failures to CloudWatch.

**Validates: Requirements 7.6**

### Property 30: Incident Storage Completeness

*For any* stored incident record, it should include service_name, failure_type, root_cause, fix_applied, and resolution_time.

**Validates: Requirements 8.2**

### Property 31: Incident Query Filtering

*For any* incident history query with a service name and failure pattern, the returned incidents should match both the service name and failure pattern.

**Validates: Requirements 8.3**

### Property 32: Similar Incident Ranking and Limiting

*For any* query that finds similar incidents, the system should return at most 5 incidents, ranked by similarity score in descending order.

**Validates: Requirements 8.4**

### Property 33: ISO 8601 Timestamp Format

*For any* stored incident record, all timestamps should be in valid ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ).

**Validates: Requirements 8.6**

### Property 34: Metrics Emission

*For any* agent execution, the system should emit CloudWatch metrics for execution time, success rate, and error count.

**Validates: Requirements 9.1**

### Property 35: Latency Warning Threshold

*For any* incident processing that takes longer than 60 seconds, the system should emit a latency warning metric.

**Validates: Requirements 9.2**

### Property 36: Token Usage Tracking

*For any* Bedrock API call, the system should track and emit token usage metrics to CloudWatch.

**Validates: Requirements 9.3**

### Property 37: Cost Warning Threshold

*For any* AWS service usage that reaches 80% of Free Tier limits, the system should emit a cost warning metric.

**Validates: Requirements 9.4**

### Property 38: Error Logging Detail

*For any* agent failure, the system should log detailed error information (agent name, error message, context) to CloudWatch Logs.

**Validates: Requirements 9.5**

### Property 39: PII Redaction

*For any* logs containing personally identifiable information (email addresses, phone numbers, SSNs, credit card numbers), the Log Analysis Agent should redact the PII before analysis.

**Validates: Requirements 10.4**

### Property 40: API Authentication Validation

*For any* request to the API Gateway, the system should validate API keys or IAM credentials before processing the request.

**Validates: Requirements 10.5, 12.6**

### Property 41: Failure Classification Confidence Threshold

*For any* failure scenario of type configuration_error, resource_exhaustion, or dependency_failure, the system should identify it with at least 70% confidence.

**Validates: Requirements 11.1, 11.2, 11.3**

### Property 42: Root Cause Specificity

*For any* identified root cause, the system should provide specific details: the configuration parameter for config errors, the exhausted resource (memory/CPU/disk) for resource exhaustion, or the dependency name/endpoint for dependency failures.

**Validates: Requirements 11.4, 11.5, 11.6**

### Property 43: API Request Acceptance

*For any* POST request to /incidents with a valid JSON payload containing service_name, timestamp, error_message, and log_location, the system should accept the request and return 202 Accepted with an incident_id.

**Validates: Requirements 12.2, 12.3**

### Property 44: API Error Response

*For any* invalid request to /incidents (malformed JSON, missing required fields), the system should return 400 Bad Request with error details.

**Validates: Requirements 12.4**

### Property 45: Rate Limiting

*For any* API key that sends more than 100 requests per minute, the system should return 429 Too Many Requests for requests exceeding the limit.

**Validates: Requirements 12.5**

### Property 46: Token Usage Limits

*For any* incident processing, the total Bedrock token usage should stay within AWS Free Tier allowances (tracked cumulatively).

**Validates: Requirements 13.1**

### Property 47: Metric Batching

*For any* incident processing that generates multiple CloudWatch metrics, the metrics should be batched into fewer API calls rather than sent individually.

**Validates: Requirements 13.5**

## Error Handling

### Error Categories

The system handles three categories of errors:

1. **Transient Errors**: Temporary failures that may succeed on retry
   - Bedrock API timeouts
   - S3 throttling
   - DynamoDB throttling
   - Network connectivity issues

2. **Permanent Errors**: Failures that won't succeed on retry
   - Invalid log format
   - Missing S3 objects
   - Malformed alert payloads
   - Authentication failures

3. **Partial Failures**: Some agents succeed while others fail
   - Log retrieval succeeds but analysis fails
   - Root cause identified but fix generation fails

### Error Handling Strategies

**Transient Error Handling**:
```python
def invoke_with_retry(agent_name, input_data, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            result = invoke_agent(agent_name, input_data)
            return result
        except TransientError as e:
            if attempt < max_retries:
                backoff_seconds = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(backoff_seconds)
                log_retry(agent_name, attempt + 1, e)
            else:
                log_failure(agent_name, e)
                raise
```

**Permanent Error Handling**:
```python
def handle_permanent_error(agent_name, error):
    # Log error with full context
    logger.error(f"Permanent failure in {agent_name}", extra={
        "agent": agent_name,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "incident_id": current_incident_id
    })
    
    # Emit CloudWatch metric
    cloudwatch.put_metric_data(
        Namespace="IncidentResponse",
        MetricData=[{
            "MetricName": "AgentPermanentFailure",
            "Value": 1,
            "Dimensions": [{"Name": "Agent", "Value": agent_name}]
        }]
    )
    
    # Return error indicator for partial results
    return {"status": "failed", "agent": agent_name, "error": str(error)}
```

**Partial Failure Handling**:
```python
def aggregate_partial_results(agent_results):
    enhanced_alert = {
        "incident_id": generate_incident_id(),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "partial",
        "completed_agents": [],
        "failed_agents": []
    }
    
    for agent_name, result in agent_results.items():
        if result.get("status") == "success":
            enhanced_alert["completed_agents"].append(agent_name)
            enhanced_alert[agent_name] = result["payload"]
        else:
            enhanced_alert["failed_agents"].append(agent_name)
            enhanced_alert[f"{agent_name}_error"] = result.get("error")
    
    # Add warning if critical agents failed
    if "root-cause" in enhanced_alert["failed_agents"]:
        enhanced_alert["warning"] = "Root cause analysis failed - manual investigation required"
    
    return enhanced_alert
```

### Error Response Formats

**API Gateway Errors**:
```json
{
  "error": "ValidationError",
  "message": "Missing required field: service_name",
  "details": {
    "required_fields": ["service_name", "timestamp", "error_message", "log_location"],
    "provided_fields": ["timestamp", "error_message"]
  },
  "incident_id": null
}
```

**Agent Errors**:
```json
{
  "agent": "log-analysis",
  "status": "failed",
  "error": {
    "code": "S3_OBJECT_NOT_FOUND",
    "message": "Log file not found at s3://logs/service/2025-01-15/10-30.log",
    "retryable": false
  },
  "execution_time_ms": 1234
}
```

**Partial Result Alerts**:
```json
{
  "incident_id": "inc-2025-01-15-001",
  "status": "partial",
  "warning": "Some analysis steps failed - results may be incomplete",
  "completed_agents": ["log-analysis", "root-cause"],
  "failed_agents": ["fix-recommendation", "communication"],
  "log_analysis": { /* successful result */ },
  "root_cause": { /* successful result */ },
  "fix_recommendation_error": "Bedrock API timeout after 30s",
  "communication_error": "Cannot generate summary without fix recommendations"
}
```

### Fallback Behaviors

**Missing Logs**:
- Return confidence score of 0
- Include warning in alert: "Log analysis unavailable - logs not found"
- Continue with error message analysis only

**Bedrock API Failures**:
- Retry with exponential backoff
- After retries exhausted, use rule-based fallback:
  - Pattern matching on error messages
  - Simple keyword-based classification
  - Lower confidence scores (max 40)

**Bedrock Knowledge Base Unavailability**:
- Continue without historical context
- Reduce confidence scores by 20 points
- Note in alert: "Historical analysis unavailable - Knowledge Base query failed"

**SES Delivery Failures**:
- Retry up to 3 times with exponential backoff
- Log failure to CloudWatch with full context
- Store alert in DynamoDB for manual retrieval
- Emit high-priority CloudWatch metric for monitoring
- Send fallback notification via SNS if configured

## Testing Strategy

### Dual Testing Approach

The system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Verify specific examples, edge cases, and error conditions
- Specific failure scenarios (e.g., "ConnectionTimeout to payment-gateway.example.com")
- Edge cases (empty logs, logs >10MB, missing fields)
- Error conditions (S3 access denied, Bedrock timeout, invalid JSON)
- Integration points (API Gateway → Lambda, Lambda → Bedrock)

**Property Tests**: Verify universal properties across all inputs
- Universal properties that hold for all inputs (e.g., confidence scores always 0-100)
- Comprehensive input coverage through randomization
- Invariants that must hold regardless of input (e.g., agent execution order)

### Property-Based Testing Configuration

**Testing Library**: Use `hypothesis` for Python or `fast-check` for TypeScript/JavaScript

**Test Configuration**:
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: incident-response-system, Property {number}: {property_text}`

**Example Property Test Structure**:
```python
from hypothesis import given, strategies as st
import pytest

@given(
    service_name=st.text(min_size=1, max_size=100),
    timestamp=st.datetimes(),
    error_message=st.text(min_size=1)
)
@pytest.mark.property_test
def test_property_2_alert_payload_validation(service_name, timestamp, error_message):
    """
    Feature: incident-response-system
    Property 2: Alert Payload Validation
    
    For any incoming alert payload, if the payload is valid, the system should
    accept it and extract all fields; if invalid, reject with 400 status.
    """
    payload = {
        "service_name": service_name,
        "timestamp": timestamp.isoformat(),
        "error_message": error_message,
        "log_location": f"s3://logs/{service_name}/{timestamp.date()}.log"
    }
    
    response = api_gateway_handler(payload)
    
    # Valid payload should be accepted
    assert response["statusCode"] == 202
    assert "incident_id" in response["body"]
    
    # Extracted fields should match input
    incident = get_incident(response["body"]["incident_id"])
    assert incident["service_name"] == service_name
    assert incident["error_message"] == error_message
```

### Unit Test Examples

**Edge Case: Large Logs**:
```python
def test_log_analysis_handles_large_logs():
    """Test that logs >10MB are truncated to most recent 10MB"""
    # Create 15MB of log data
    large_log = "ERROR: Lambda deployment failed\n" * 500000  # ~15MB
    
    result = log_analysis_agent.analyze(large_log, timestamp="2025-01-15T10:30:00Z")
    
    # Should process only most recent 10MB
    assert result["log_volume"] == "10 MB"
    assert result["truncated"] is True
```

**Error Condition: Missing Logs**:
```python
def test_log_analysis_handles_missing_logs():
    """Test behavior when logs are not available in S3"""
    result = log_analysis_agent.analyze(
        log_location="s3://logs/nonexistent/file.log",
        timestamp="2025-01-15T10:30:00Z"
    )
    
    assert result["status"] == "failed"
    assert result["confidence_score"] == 0
    assert "logs not found" in result["error"].lower()
```

**Integration: API Gateway to Orchestrator**:
```python
def test_api_gateway_invokes_orchestrator():
    """Test that valid API requests trigger orchestrator within 2 seconds"""
    start_time = time.time()
    
    response = api_gateway_handler({
        "service_name": "test-service",
        "timestamp": "2025-01-15T10:30:00Z",
        "error_message": "DynamoDB throttling detected",
        "log_location": "s3://logs/test.log"
    })
    
    orchestrator_invocation_time = get_orchestrator_invocation_time(
        response["body"]["incident_id"]
    )
    
    elapsed = orchestrator_invocation_time - start_time
    assert elapsed < 2.0  # Within 2 seconds
```

**AWS-Native Failure Scenarios**:
```python
def test_lambda_deployment_failure_analysis():
    """Test analysis of Lambda deployment failure"""
    result = root_cause_agent.analyze({
        "error_message": "Lambda deployment failed: package size exceeds limit",
        "log_summary": {
            "error_patterns": ["DeploymentPackageTooLarge"],
            "stack_traces": []
        }
    })
    
    assert result["primary_cause"]["category"] == "configuration_error"
    assert "deployment package" in result["primary_cause"]["description"].lower()

def test_dynamodb_throttling_analysis():
    """Test analysis of DynamoDB throttling"""
    result = root_cause_agent.analyze({
        "error_message": "ProvisionedThroughputExceededException",
        "log_summary": {
            "error_patterns": ["ThrottlingException"],
            "stack_traces": []
        }
    })
    
    assert result["primary_cause"]["category"] == "resource_exhaustion"
    assert "throttling" in result["primary_cause"]["description"].lower()

def test_api_gateway_timeout_analysis():
    """Test analysis of API Gateway timeout to external service"""
    result = root_cause_agent.analyze({
        "error_message": "API Gateway timeout after 29s",
        "log_summary": {
            "error_patterns": ["TimeoutException"],
            "stack_traces": []
        }
    })
    
    assert result["primary_cause"]["category"] == "dependency_failure"
    assert "timeout" in result["primary_cause"]["description"].lower()
```

### Test Coverage Goals

- **Unit Test Coverage**: 80% line coverage minimum
- **Property Test Coverage**: All 47 correctness properties implemented
- **Integration Test Coverage**: All agent handoffs and AWS service integrations
- **Error Path Coverage**: All error handling paths exercised

### Testing AWS Services

**Mocking Strategy**:
- Use `moto` for mocking AWS services (S3, DynamoDB, SES, CloudWatch)
- Use `boto3` stubber for fine-grained control
- Mock Bedrock API calls (Claude models and Knowledge Base) with predefined responses
- Mock AgentCore runtime with simulated session management

**Integration Testing**:
- Use LocalStack for local AWS service emulation
- Test against real AWS services in development account
- Use AWS Free Tier resources for cost-effective testing
- Test Bedrock Knowledge Base with sample incident data

**Example Mock Setup**:
```python
from moto import mock_s3, mock_dynamodb, mock_ses
import boto3
from unittest import mock

@mock_s3
@mock_dynamodb
@mock_ses
def test_end_to_end_incident_processing():
    # Setup mock S3 with test logs
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="test-logs")
    s3.put_object(
        Bucket="test-logs",
        Key="service/2025-01-15/10-30.log",
        Body="ERROR: Lambda deployment failed\n" * 100
    )
    
    # Setup mock DynamoDB
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.create_table(
        TableName="incident-history",
        KeySchema=[{"AttributeName": "incident_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "incident_id", "AttributeType": "S"}]
    )
    
    # Setup mock SES
    ses = boto3.client("ses")
    ses.verify_email_identity(EmailAddress="incidents@example.com")
    
    # Mock Bedrock Knowledge Base responses
    mock_kb_response = {
        'retrievalResults': [
            {
                'score': 0.85,
                'metadata': {
                    'incident_id': 'inc-2024-12-01-001',
                    'root_cause': 'Lambda deployment package too large'
                },
                'content': {
                    'text': 'Reduced deployment package size by removing unused dependencies'
                }
            }
        ]
    }
    
    # Run end-to-end test
    with mock.patch('bedrock_agent_runtime.retrieve', return_value=mock_kb_response):
        result = process_incident({
            "service_name": "test-service",
            "timestamp": "2025-01-15T10:30:00Z",
            "error_message": "Lambda deployment failed",
            "log_location": "s3://test-logs/service/2025-01-15/10-30.log"
        })
    
    # Verify complete processing
    assert result["status"] == "success"
    assert "root_cause" in result
    assert "fixes" in result
    assert result["confidence_score"] > 0
    
    # Verify SES email was sent
    sent_emails = ses.list_identities()
    assert len(sent_emails['Identities']) > 0
```

### Continuous Testing

**Pre-commit Hooks**:
- Run unit tests on changed files
- Run linting and type checking
- Verify no secrets in code

**CI/CD Pipeline**:
1. Run all unit tests
2. Run all property tests (100 iterations each)
3. Run integration tests against LocalStack
4. Generate coverage report
5. Deploy to development environment
6. Run smoke tests against real AWS services
7. Deploy to production (manual approval)

**Monitoring in Production**:
- Track property violations in production (if any)
- Alert on confidence score degradation
- Monitor test execution time trends
- Track flaky test occurrences
