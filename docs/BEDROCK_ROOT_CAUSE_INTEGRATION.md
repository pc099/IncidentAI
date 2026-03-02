# Bedrock Claude Integration for Root Cause Analysis

## Overview

The Root Cause Agent integrates with Amazon Bedrock Claude models to provide AI-powered root cause analysis. This integration combines:

1. **Knowledge Base Query**: Retrieves similar past incidents using semantic search
2. **Prompt Template Creation**: Formats incident data and historical context for Claude
3. **Claude Model Invocation**: Sends structured prompt to Bedrock Claude
4. **Response Parsing**: Extracts structured JSON with root cause, confidence, and evidence
5. **Fallback Mechanism**: Uses rule-based classification if Bedrock fails

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Root Cause Agent                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              BedrockRootCauseAnalyzer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Query Knowledge Base for similar incidents       │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 2. Create prompt with log summary + historical data  │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 3. Invoke Bedrock Claude model                       │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 4. Parse structured JSON response                    │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 5. Validate and normalize response                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│         Structured Root Cause Analysis Result                │
│  - Primary cause (category, description, confidence)         │
│  - Alternative causes                                        │
│  - Evidence from logs                                        │
│  - Similar incidents referenced                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. BedrockRootCauseAnalyzer Class

Main class for Bedrock integration located in `src/agents/root_cause_classifier.py`.

**Key Methods:**

- `create_prompt()`: Creates structured prompt with incident data and historical context
- `invoke_claude()`: Invokes Bedrock Claude model and parses response
- `analyze_with_bedrock()`: Complete analysis workflow (main entry point)
- `_validate_and_normalize_response()`: Ensures response meets requirements

### 2. Prompt Template

The prompt template includes:

- **Service Information**: Service name and error message
- **Log Analysis**: Error patterns, stack traces, relevant excerpts
- **Historical Context**: Similar incidents from Knowledge Base with resolutions
- **Classification Categories**: Configuration error, resource exhaustion, dependency failure
- **Output Format**: Structured JSON schema for consistent parsing

**Example Prompt Structure:**

```
You are a root cause analysis expert. Analyze this incident:

Service: payment-processor
Error: Connection timeout to payment-gateway.example.com

Log Analysis:
Error Patterns:
  - TimeoutException: 15 occurrences
  - ConnectionRefused: 3 occurrences

Stack Traces:
  - java.net.SocketTimeoutException: Read timed out

Relevant Log Excerpts:
  - ERROR: Failed to connect to payment-gateway.example.com:443
  - WARN: Connection pool exhausted

Similar Past Incidents (from Knowledge Base):
1. Incident inc-2024-11-23-001 (similarity: 78%)
   Root Cause: Payment gateway timeout
   Resolution: Increased timeout threshold to 30s

Classify the root cause into one of:
- configuration_error: Invalid config values, missing parameters
- resource_exhaustion: Memory, CPU, disk space limits exceeded
- dependency_failure: External service timeouts, connection failures

Provide your analysis in JSON format...
```

### 3. Response Structure

Claude returns structured JSON with:

```json
{
  "primary_cause": {
    "category": "dependency_failure",
    "description": "External payment gateway timeout",
    "confidence_score": 85,
    "evidence": [
      "15 consecutive connection timeouts",
      "Gateway health check failed",
      "Similar pattern in incident inc-2024-11-23-001"
    ]
  },
  "alternative_causes": [
    {
      "category": "resource_exhaustion",
      "description": "Network bandwidth saturation",
      "confidence_score": 35,
      "evidence": ["High request volume observed"]
    }
  ]
}
```

### 4. Response Validation

The system validates and normalizes Claude's response:

- **Category Validation**: Ensures category is one of the three valid types
- **Confidence Bounds**: Enforces 0-100 range for all confidence scores
- **Field Presence**: Adds default values for missing required fields
- **Evidence Format**: Ensures evidence is a list

### 5. Fallback Mechanism

If Bedrock invocation fails:

1. **Log Warning**: Records Bedrock failure with error details
2. **Rule-Based Classification**: Uses pattern matching on error messages
3. **Lower Confidence**: Caps confidence at 40% for fallback results
4. **Preserve Functionality**: System continues to operate with degraded accuracy

## Usage

### Basic Usage

```python
from src.agents.root_cause_classifier import BedrockRootCauseAnalyzer

# Initialize analyzer
analyzer = BedrockRootCauseAnalyzer()

# Prepare incident data
log_summary = {
    "error_patterns": [
        {"pattern": "TimeoutException", "occurrences": 15}
    ],
    "stack_traces": [
        {"exception": "SocketTimeoutException", "message": "Read timed out"}
    ],
    "relevant_excerpts": [
        "ERROR: Connection timeout to payment-gateway.example.com"
    ]
}

# Perform analysis
result = analyzer.analyze_with_bedrock(
    service_name="payment-processor",
    error_message="Connection timeout",
    log_summary=log_summary,
    similar_incidents=None  # Optional: from Knowledge Base query
)

# Access results
print(f"Root Cause: {result['primary_cause']['category']}")
print(f"Confidence: {result['primary_cause']['confidence_score']}%")
print(f"Description: {result['primary_cause']['description']}")
```

### With Knowledge Base Integration

```python
from src.agents.root_cause_classifier import BedrockRootCauseAnalyzer
from src.agents.kb_query import query_similar_incidents

# Query Knowledge Base for similar incidents
similar_incidents = query_similar_incidents(
    service_name="payment-processor",
    error_message="Connection timeout",
    log_summary=log_summary
)

# Analyze with historical context
analyzer = BedrockRootCauseAnalyzer()
result = analyzer.analyze_with_bedrock(
    service_name="payment-processor",
    error_message="Connection timeout",
    log_summary=log_summary,
    similar_incidents=similar_incidents  # Include historical context
)

# Similar incidents are included in result
for incident in result['similar_incidents']:
    print(f"Referenced: {incident['incident_id']} ({incident['similarity_score']:.0%})")
```

### Custom Model Configuration

```python
# Use a different Claude model
analyzer = BedrockRootCauseAnalyzer(
    bedrock_model_id="anthropic.claude-3-opus-20240229-v1:0"
)

result = analyzer.analyze_with_bedrock(...)
```

## Testing

### Unit Tests

Run unit tests for Bedrock integration:

```bash
python -m pytest tests/test_bedrock_root_cause_integration.py -v
```

**Test Coverage:**

- Prompt template creation with/without similar incidents
- Claude invocation with valid/invalid responses
- Response validation and normalization
- Confidence score bounds enforcement
- Fallback to rule-based classification
- End-to-end analysis workflow

### Integration Tests

Run integration test script:

```bash
python scripts/test_bedrock_root_cause_integration.py
```

This demonstrates:

1. Complete workflow with Knowledge Base query
2. Analysis without historical context
3. Fallback mechanism when Bedrock fails

## Configuration

### Environment Variables

```bash
# AWS Region for Bedrock
export AWS_REGION=us-east-1

# Bedrock Model ID (optional, defaults to Claude 3.5 Sonnet)
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### IAM Permissions

Required IAM permissions for Bedrock integration:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    }
  ]
}
```

## Performance

### Latency

- **Typical Response Time**: 2-5 seconds
- **With Knowledge Base Query**: 3-7 seconds (includes KB retrieval)
- **Fallback Classification**: <100ms (rule-based, no API call)

### Cost

- **Bedrock Claude 3.5 Sonnet**: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- **Typical Analysis**: ~1,500 input tokens, ~500 output tokens = ~$0.012 per analysis
- **Free Tier**: First 2 months include free usage (check AWS Free Tier limits)

### Token Usage

- **Prompt Size**: 500-2,000 tokens (depends on log summary and similar incidents)
- **Response Size**: 200-800 tokens (depends on complexity)
- **Total per Analysis**: 700-2,800 tokens

## Error Handling

### Common Errors

1. **Bedrock API Timeout**
   - **Cause**: Network issues or high Bedrock load
   - **Handling**: Automatic fallback to rule-based classification
   - **Mitigation**: Retry with exponential backoff (future enhancement)

2. **Invalid JSON Response**
   - **Cause**: Claude returns non-JSON text
   - **Handling**: Fallback to rule-based classification
   - **Logging**: Warning logged with response content

3. **Model Not Found**
   - **Cause**: Invalid model ID or region mismatch
   - **Handling**: Exception raised, fallback triggered
   - **Fix**: Verify model ID and region configuration

4. **Insufficient Permissions**
   - **Cause**: IAM role lacks bedrock:InvokeModel permission
   - **Handling**: Exception raised with permission error
   - **Fix**: Update IAM role with required permissions

### Error Logging

All errors are logged with context:

```python
logger.error(f"Bedrock analysis failed: {str(e)}, falling back to rule-based classification")
```

## Best Practices

1. **Always Provide Log Summary**: More detailed logs = better analysis
2. **Include Similar Incidents**: Historical context improves confidence scores
3. **Monitor Token Usage**: Track costs via CloudWatch metrics
4. **Test Fallback**: Ensure rule-based classification works as backup
5. **Validate Responses**: Use built-in validation to ensure data quality
6. **Log Analysis Results**: Track confidence scores and categories for improvement

## Requirements Validation

This implementation satisfies:

- **Requirement 3.1**: Root Cause Agent analyzes data using Amazon Bedrock Claude models ✅
- **Requirement 3.7**: Produces structured output with primary cause, confidence, and evidence ✅

## Future Enhancements

1. **Retry Logic**: Add exponential backoff for transient Bedrock errors
2. **Response Caching**: Cache similar analyses to reduce API calls
3. **Multi-Model Support**: Allow fallback to different Claude models
4. **Streaming Responses**: Use Bedrock streaming for faster initial results
5. **Fine-Tuning**: Custom model training on historical incident data
6. **Confidence Calibration**: Adjust confidence scores based on historical accuracy

## References

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Claude Model Documentation](https://docs.anthropic.com/claude/docs)
- [Bedrock Knowledge Base Integration](./KNOWLEDGE_BASE_CONFIGURATION.md)
- [Root Cause Classification Logic](../src/agents/root_cause_classifier.py)
