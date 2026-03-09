# Implementation Plan: AI-Powered Incident Response System

## Overview

This implementation plan breaks down the AI-Powered Incident Response System into discrete, actionable tasks. The system uses AWS Strands Agents framework to orchestrate four specialized AI agents (Log Analysis, Root Cause, Fix Recommendation, Communication) powered by Amazon Bedrock Claude models. The implementation follows a bottom-up approach: infrastructure setup, Bedrock Knowledge Base configuration, individual agent development, orchestration, and comprehensive testing with AWS-native failure scenarios.

## Tasks

- [x] 1. Set up AWS infrastructure and project foundation
  - Create Python project structure with virtual environment
  - Install dependencies: boto3, aws-lambda-powertools, hypothesis (for property testing)
  - Configure AWS credentials and region
  - Create S3 bucket for log storage with lifecycle policies (Standard-IA after 30 days, delete after 90 days)
  - Create DynamoDB table `incident-history` with partition key `incident_id`, sort key `timestamp`, and GSI `service-timestamp-index`
  - Set up SES email identity verification for incidents@example.com domain
  - Create IAM roles with least-privilege permissions for Lambda functions
  - _Requirements: 10.1, 10.2, 13.2, 13.3_

- [x] 2. Configure Bedrock Knowledge Base for RAG
  - [x] 2.1 Create S3 bucket for Knowledge Base data source
    - Create bucket with versioning enabled
    - Configure bucket policy for Bedrock access
    - _Requirements: 3.5, 8.1_
  
  - [x] 2.2 Set up Bedrock Knowledge Base
    - Create Knowledge Base using Amazon Titan Embeddings (1536 dimensions)
    - Configure S3 data source with sync settings
    - Set vector search configuration (top 5 results, 0.6 similarity threshold)
    - Enable hybrid search (semantic + keyword)
    - _Requirements: 3.5, 3.6_
  
  - [x] 2.3 Populate Knowledge Base with sample historical incidents
    - Create 10-15 sample incident documents covering configuration errors, resource exhaustion, and dependency failures
    - Include AWS-native scenarios: Lambda deployment failures, DynamoDB throttling, RDS storage issues, API Gateway timeouts
    - Upload documents to S3 data source bucket
    - Trigger Knowledge Base ingestion job
    - _Requirements: 3.5, 3.6, 11.1, 11.2, 11.3_

- [x] 3. Implement API Gateway endpoint and request validation
  - [x] 3.1 Create API Gateway REST API with /incidents endpoint
    - Configure POST method with JSON request body
    - Set up API key authentication
    - Configure rate limiting (100 requests/minute)
    - Enable CloudWatch logging
    - _Requirements: 12.1, 12.2, 12.5, 12.6_
  
  - [x] 3.2 Implement request validation Lambda function
    - Validate required fields: service_name, timestamp, error_message, log_location
    - Return 400 Bad Request for invalid payloads with error details
    - Return 202 Accepted with incident_id for valid requests
    - Extract failure timestamp, service name, and error context
    - _Requirements: 1.3, 1.4, 1.5, 12.3, 12.4_
  
  - [x] 3.3 Write property tests for API validation
    - **Property 2: Alert Payload Validation**
    - **Validates: Requirements 1.3, 1.4, 1.5**
  
  - [x] 3.4 Write property test for API authentication
    - **Property 40: API Authentication Validation**
    - **Validates: Requirements 10.5, 12.6**
  
  - [x] 3.5 Write property test for rate limiting
    - **Property 45: Rate Limiting**
    - **Validates: Requirements 12.5**
  
  - [x] 3.6 Write unit tests for API edge cases
    - Test malformed JSON payloads
    - Test missing required fields
    - Test invalid timestamp formats
    - _Requirements: 1.4, 12.4_

- [x] 4. Implement Bedrock AgentCore runtime layer
  - [x] 4.1 Create AgentCore configuration module
    - Define session timeout (300 seconds)
    - Configure memory retention per incident
    - Set up security policy (least privilege)
    - Enable observability (logging, metrics, tracing)
    - _Requirements: 6.1, 10.3_
  
  - [x] 4.2 Implement session management functions
    - Create isolated sessions per incident
    - Manage session lifecycle (create, execute, terminate)
    - Clean up resources after incident resolution
    - _Requirements: 6.1, 6.5_
  
  - [x] 4.3 Implement memory management for agent context
    - Store intermediate results for agent handoffs
    - Maintain conversation context across agent invocations
    - _Requirements: 6.2_

- [x] 5. Implement Log Analysis Agent
  - [x] 5.1 Create log retrieval module
    - Calculate time window: [timestamp - 15min, timestamp + 5min]
    - Retrieve logs from S3 using service_name and time window
    - Handle logs >10MB by retrieving most recent 10MB
    - Handle missing logs gracefully (return confidence score 0)
    - _Requirements: 2.1, 2.2, 2.3, 2.7_
  
  - [x] 5.2 Implement log parsing and pattern extraction
    - Parse logs to extract error messages, stack traces, timestamps
    - Identify error patterns using regex and frequency analysis
    - Extract top 5 most relevant log excerpts
    - Implement PII redaction (email, phone, SSN, credit card)
    - _Requirements: 2.4, 2.5, 10.4_
  
  - [x] 5.3 Integrate with Bedrock Claude for log analysis
    - Create Bedrock prompt template for log analysis
    - Invoke Claude model with log content
    - Parse structured JSON response
    - Generate log summary with error patterns, stack traces, and excerpts
    - _Requirements: 2.6_
  
  - [x] 5.4 Write property test for log time window calculation
    - **Property 4: Log Time Window Calculation**
    - **Validates: Requirements 2.2**
  
  - [x] 5.5 Write property test for log parsing completeness
    - **Property 5: Log Parsing Completeness**
    - **Validates: Requirements 2.4, 2.5**
  
  - [x] 5.6 Write property test for PII redaction
    - **Property 39: PII Redaction**
    - **Validates: Requirements 10.4**
  
  - [x] 5.7 Write unit tests for log analysis edge cases
    - Test empty logs
    - Test logs >10MB
    - Test missing S3 objects
    - Test logs with special characters
    - _Requirements: 2.3, 2.7_

- [x] 6. Checkpoint - Verify log analysis functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement Root Cause Agent with RAG
  - [x] 7.1 Create Bedrock Knowledge Base query module
    - Convert current incident to query text
    - Query Knowledge Base using bedrock-agent-runtime.retrieve()
    - Extract top 5 similar incidents with similarity scores
    - Parse incident metadata (incident_id, root_cause, resolution)
    - _Requirements: 3.5, 3.6_
  
  - [x] 7.2 Implement root cause classification logic
    - Classify failures into: configuration_error, resource_exhaustion, dependency_failure
    - Implement confidence score calculation (pattern clarity 40%, historical match 30%, evidence strength 30%)
    - Rank alternative causes by confidence score
    - _Requirements: 3.2, 3.3, 3.4_
  
  - [x] 7.3 Integrate with Bedrock Claude for root cause analysis
    - Create Bedrock prompt template including similar incidents from Knowledge Base
    - Invoke Claude model with log summary and historical context
    - Parse structured JSON response with primary cause, confidence, evidence, alternatives
    - _Requirements: 3.1, 3.7_
  
  - [x] 7.4 Write property test for root cause classification
    - **Property 7: Root Cause Classification**
    - **Validates: Requirements 3.2**
  
  - [x] 7.5 Write property test for confidence score bounds
    - **Property 8: Confidence Score Bounds**
    - **Validates: Requirements 3.3**
  
  - [x] 7.6 Write property test for root cause ranking
    - **Property 9: Root Cause Ranking**
    - **Validates: Requirements 3.4**
  
  - [x] 7.7 Write property test for historical pattern integration
    - **Property 10: Historical Pattern Integration**
    - **Validates: Requirements 3.6**
  
  - [x] 7.8 Write unit tests for AWS-native failure scenarios
    - Test Lambda deployment failure classification
    - Test DynamoDB throttling classification
    - Test RDS storage full classification
    - Test API Gateway timeout classification
    - Test Step Functions execution failure classification
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

- [x] 8. Implement Fix Recommendation Agent
  - [x] 8.1 Create fix template mapping by root cause category
    - Configuration error templates: identify parameter, provide correct value, show update command
    - Resource exhaustion templates: identify resource, calculate scaling (2x), provide scaling commands
    - Dependency failure templates: verify health, increase timeout/retry, implement fallback
    - _Requirements: 4.3, 4.4, 4.5_
  
  - [x] 8.2 Implement AWS-specific fix recommendations
    - Lambda: deployment package size, IAM permissions, timeout configuration, concurrency limits
    - DynamoDB: throttling, auto-scaling, on-demand billing, exponential backoff
    - RDS: storage full, auto-scaling, archival strategies
    - API Gateway: timeout configuration, async processing, circuit breaker
    - Step Functions: state machine errors, retry configuration, error handling
    - _Requirements: 4.1, 4.3, 4.4, 4.5_
  
  - [x] 8.3 Integrate with Bedrock Claude for fix generation
    - Create Bedrock prompt template for fix recommendations
    - Query incident history for previously successful fixes
    - Generate 2-5 immediate action steps with commands
    - Include estimated time to resolution for each step
    - Add preventive measures and rollback plan
    - _Requirements: 4.1, 4.2, 4.6, 4.7_
  
  - [x] 8.4 Write property test for fix recommendation count
    - **Property 12: Fix Recommendation Count**
    - **Validates: Requirements 4.2**
  
  - [x] 8.5 Write property test for category-specific fix content
    - **Property 13: Category-Specific Fix Content**
    - **Validates: Requirements 4.3, 4.4, 4.5**
  
  - [x] 8.6 Write property test for fix time estimates
    - **Property 14: Fix Time Estimates**
    - **Validates: Requirements 4.6**
  
  - [x] 8.7 Write unit tests for AWS-specific fix recommendations
    - Test Lambda deployment failure fixes
    - Test DynamoDB throttling fixes
    - Test RDS storage full fixes
    - Test API Gateway timeout fixes
    - _Requirements: 4.3, 4.4, 4.5_

- [x] 9. Implement Communication Agent
  - [x] 9.1 Create summary generation module
    - Extract key information from root cause and fixes
    - Generate technical summary with commands and evidence
    - Generate business summary without technical jargon
    - Add confidence warning if score < 50
    - Include incident_id for tracking
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 7.4_
  
  - [x] 9.2 Integrate with Bedrock Claude for summary formatting
    - Create Bedrock prompt template for dual summaries
    - Invoke Claude model with root cause and fixes
    - Parse technical and business summaries
    - _Requirements: 5.1, 5.2, 5.3_
  
  - [x] 9.3 Implement user impact assessment
    - Determine if service is user-facing
    - Calculate estimated user impact for user-facing services
    - Include impact in non-technical summary
    - _Requirements: 5.5_
  
  - [x] 9.4 Write property test for dual summary generation
    - **Property 15: Dual Summary Generation**
    - **Validates: Requirements 5.1**
  
  - [x] 9.5 Write property test for technical summary completeness
    - **Property 16: Technical Summary Completeness**
    - **Validates: Requirements 5.2**
  
  - [x] 9.6 Write property test for confidence score in summaries
    - **Property 17: Confidence Score in Summaries**
    - **Validates: Requirements 5.4**
  
  - [x] 9.7 Write property test for user impact inclusion
    - **Property 18: User Impact for User-Facing Services**
    - **Validates: Requirements 5.5**

- [x] 10. Checkpoint - Verify individual agents work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Strands Orchestrator Lambda
  - [x] 11.1 Create agent invocation sequence function
    - Invoke agents in order: Log Analysis → Root Cause → Fix Recommendation → Communication
    - Pass output from each agent to the next within 1 second
    - Track execution time for each agent
    - _Requirements: 6.1, 6.2_
  
  - [x] 11.2 Implement retry logic with exponential backoff
    - Retry failed agents up to 2 times
    - Use exponential backoff: 1s, 2s, 4s
    - Log retry attempts with context
    - _Requirements: 6.3_
  
  - [x] 11.3 Implement partial result handling
    - Continue processing if agent fails after retries
    - Preserve results from successful agents
    - Log failures with detailed error information
    - _Requirements: 6.4, 9.5_
  
  - [x] 11.4 Implement result aggregation
    - Combine agent outputs into Enhanced_Alert
    - Record total processing time
    - Emit CloudWatch metrics for orchestration
    - _Requirements: 6.5, 6.6_
  
  - [x] 11.5 Write property test for agent execution sequence
    - **Property 19: Agent Execution Sequence**
    - **Validates: Requirements 6.1**
  
  - [x] 11.6 Write property test for agent output handoff timing
    - **Property 20: Agent Output Handoff Timing**
    - **Validates: Requirements 6.2**
  
  - [x] 11.7 Write property test for agent retry behavior
    - **Property 21: Agent Retry Behavior**
    - **Validates: Requirements 6.3**
  
  - [x] 11.8 Write property test for partial results preservation
    - **Property 22: Partial Results Preservation**
    - **Validates: Requirements 6.4**
  
  - [x] 11.9 Write unit tests for orchestration error scenarios
    - Test all agents succeed
    - Test first agent fails
    - Test middle agent fails
    - Test last agent fails
    - Test multiple agents fail
    - _Requirements: 6.3, 6.4_

- [x] 12. Implement alert delivery service with SES
  - [x] 12.1 Create HTML email template
    - Design responsive HTML template with sections: Header, Root Cause, Immediate Actions, Commands, Business Impact, Similar Incidents
    - Style with confidence level indicators (high/medium/low)
    - Format action items with step numbers, time estimates, risk levels
    - Include metadata footer
    - _Requirements: 7.2, 7.3_
  
  - [x] 12.2 Implement email formatting logic
    - Render HTML template with enhanced alert data
    - Format evidence items as bullet list
    - Format action items with styling
    - Format commands in monospace code blocks
    - Format similar incidents with similarity scores
    - Generate plain text fallback
    - _Requirements: 7.2, 7.3_
  
  - [x] 12.3 Implement SES email delivery
    - Send email via SES with HTML and text bodies
    - Configure sender, recipients (on-call engineers, stakeholders)
    - Set subject line with incident_id and title
    - Handle delivery failures with retry (up to 3 times)
    - Log delivery failures to CloudWatch
    - _Requirements: 7.1, 7.5, 7.6_
  
  - [x] 12.4 Write property test for alert delivery timing
    - **Property 24: Alert Delivery Timing**
    - **Validates: Requirements 7.1**
  
  - [x] 12.5 Write property test for alert content completeness
    - **Property 25: Alert Content Completeness**
    - **Validates: Requirements 7.2**
  
  - [x] 12.6 Write property test for alert section structure
    - **Property 26: Alert Section Structure**
    - **Validates: Requirements 7.3**
  
  - [x] 12.7 Write property test for low confidence warning
    - **Property 27: Low Confidence Warning**
    - **Validates: Requirements 7.4**
  
  - [x] 12.8 Write property test for incident ID uniqueness
    - **Property 28: Incident ID Uniqueness**
    - **Validates: Requirements 7.5**
  
  - [x] 12.9 Write unit tests for email delivery
    - Test successful delivery
    - Test delivery retry on failure
    - Test HTML rendering
    - Test plain text fallback
    - _Requirements: 7.1, 7.6_

- [x] 13. Implement incident history management
  - [x] 13.1 Create DynamoDB storage module
    - Store incident records with all required fields
    - Set TTL to 90 days for automatic deletion
    - Use ISO 8601 format for timestamps
    - _Requirements: 8.1, 8.2, 8.6_
  
  - [x] 13.2 Implement incident query functions
    - Query by service_name and failure pattern using GSI
    - Return top 5 most similar incidents ranked by similarity
    - Handle empty result sets gracefully
    - _Requirements: 8.3, 8.4, 8.5_
  
  - [x] 13.3 Implement Knowledge Base sync
    - Convert DynamoDB record to Knowledge Base document format
    - Write document to S3 data source bucket
    - Trigger Knowledge Base ingestion job
    - _Requirements: 8.1_
  
  - [x] 13.4 Write property test for incident storage completeness
    - **Property 30: Incident Storage Completeness**
    - **Validates: Requirements 8.2**
  
  - [x] 13.5 Write property test for incident query filtering
    - **Property 31: Incident Query Filtering**
    - **Validates: Requirements 8.3**
  
  - [x] 13.6 Write property test for similar incident ranking
    - **Property 32: Similar Incident Ranking and Limiting**
    - **Validates: Requirements 8.4**
  
  - [x] 13.7 Write property test for ISO 8601 timestamp format
    - **Property 33: ISO 8601 Timestamp Format**
    - **Validates: Requirements 8.6**

- [x] 14. Implement observability and monitoring
  - [x] 14.1 Create CloudWatch metrics emission module
    - Emit metrics for agent execution time, success rate, error count
    - Track Bedrock token usage per API call
    - Batch metric writes to reduce API calls
    - _Requirements: 9.1, 9.3, 13.5_
  
  - [x] 14.2 Implement warning metrics
    - Emit latency warning when processing exceeds 60 seconds
    - Emit cost warning when Free Tier usage reaches 80%
    - _Requirements: 9.2, 9.4_
  
  - [x] 14.3 Implement detailed error logging
    - Log agent failures with agent name, error message, context
    - Log to CloudWatch Logs with structured JSON
    - Include incident_id in all log entries
    - _Requirements: 9.5_
  
  - [x] 14.4 Create CloudWatch dashboard
    - Display incident volume over time
    - Display average resolution time
    - Display confidence score distribution
    - Display agent success rates
    - Display token usage trends
    - _Requirements: 9.6_
  
  - [x] 14.5 Write property test for metrics emission
    - **Property 34: Metrics Emission**
    - **Validates: Requirements 9.1**
  
  - [x] 14.6 Write property test for latency warning threshold
    - **Property 35: Latency Warning Threshold**
    - **Validates: Requirements 9.2**
  
  - [x] 14.7 Write property test for token usage tracking
    - **Property 36: Token Usage Tracking**
    - **Validates: Requirements 9.3**
  
  - [x] 14.8 Write property test for cost warning threshold
    - **Property 37: Cost Warning Threshold**
    - **Validates: Requirements 9.4**

- [x] 15. Checkpoint - Verify end-to-end orchestration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Implement cost optimization features
  - [x] 16.1 Configure S3 lifecycle policies
    - Transition logs to Standard-IA after 30 days
    - Delete logs after 90 days
    - _Requirements: 13.2_
  
  - [x] 16.2 Configure DynamoDB on-demand billing
    - Use on-demand billing mode to avoid provisioned capacity costs
    - _Requirements: 13.3_
  
  - [x] 16.3 Configure Lambda for cost efficiency
    - Use ARM-based (Graviton) runtimes
    - Optimize memory allocation based on profiling
    - _Requirements: 13.4_
  
  - [x] 16.4 Implement token usage limits
    - Track cumulative Bedrock token usage
    - Stay within Free Tier allowances
    - Emit warning when approaching limits
    - _Requirements: 13.1_
  
  - [x] 16.5 Write property test for token usage limits
    - **Property 46: Token Usage Limits**
    - **Validates: Requirements 13.1**

- [x] 17. Create test data and simulation tools
  - [x] 17.1 Create sample log files for testing
    - Lambda deployment failure logs
    - DynamoDB throttling logs
    - RDS storage full logs
    - API Gateway timeout logs
    - Step Functions execution failure logs
    - Upload to S3 test bucket
    - _Requirements: 11.1, 11.2, 11.3_
  
  - [x] 17.2 Create incident simulation script
    - Generate synthetic alert events for each failure type
    - Trigger API Gateway endpoint with test data
    - Verify end-to-end processing
    - _Requirements: 1.1, 1.2_
  
  - [x] 17.3 Create Knowledge Base test data
    - Add 5 sample incidents for each failure category (15 total)
    - Include resolutions and confidence scores
    - Trigger Knowledge Base sync
    - _Requirements: 3.5, 3.6_

- [x] 18. Integration testing with AWS services
  - [x] 18.1 Write integration test for API Gateway to Orchestrator
    - Test valid request triggers orchestrator within 2 seconds
    - Test invalid request returns 400 with error details
    - Test rate limiting returns 429 after threshold
    - _Requirements: 1.6, 12.3, 12.4, 12.5_
  
  - [x] 18.2 Write integration test for S3 log retrieval
    - Test successful log retrieval
    - Test missing log handling
    - Test large log truncation (>10MB)
    - _Requirements: 2.1, 2.2, 2.3, 2.7_
  
  - [x] 18.3 Write integration test for Bedrock Knowledge Base queries
    - Test similar incident retrieval
    - Test empty result handling
    - Test similarity score ranking
    - _Requirements: 3.5, 8.3, 8.4_
  
  - [x] 18.4 Write integration test for DynamoDB storage and retrieval
    - Test incident storage with all fields
    - Test query by service_name and failure pattern
    - Test TTL configuration
    - _Requirements: 8.1, 8.2, 8.3, 8.6_
  
  - [x] 18.5 Write integration test for SES email delivery
    - Test HTML email sending
    - Test plain text fallback
    - Test delivery retry on failure
    - _Requirements: 7.1, 7.6_
  
  - [x] 18.6 Write end-to-end integration test
    - Test complete flow from alert ingestion to email delivery
    - Test with Lambda deployment failure scenario
    - Test with DynamoDB throttling scenario
    - Test with API Gateway timeout scenario
    - Verify incident stored in DynamoDB and Knowledge Base
    - _Requirements: 1.1, 1.2, 1.6, 6.1, 6.5, 7.1, 8.1_

- [x] 19. Deploy infrastructure with Infrastructure as Code
  - [x] 19.1 Create CloudFormation or Terraform templates
    - Define all AWS resources: S3 buckets, DynamoDB table, Lambda functions, API Gateway, SES configuration, IAM roles
    - Configure Bedrock Knowledge Base and data source
    - Set up CloudWatch dashboard and alarms
    - _Requirements: 10.1, 10.2_
  
  - [x] 19.2 Create deployment script
    - Package Lambda functions with dependencies
    - Deploy CloudFormation/Terraform stack
    - Verify SES email identity
    - Upload sample data to Knowledge Base
    - Run smoke tests
    - _Requirements: 1.1, 1.2_
  
  - [x] 19.3 Create deployment documentation
    - Document prerequisites (AWS account, credentials, SES verification)
    - Document deployment steps
    - Document configuration options
    - Document testing procedures
    - _Requirements: 1.1, 1.2_

- [x] 20. Final checkpoint - End-to-end validation
  - [x] 20.1 Run all property tests (minimum 100 iterations each)
    - Verify all 47 correctness properties pass
    - _Requirements: All_
  
  - [x] 20.2 Run all unit tests
    - Verify 80% line coverage minimum
    - _Requirements: All_
  
  - [x] 20.3 Run all integration tests
    - Verify all AWS service integrations work
    - _Requirements: All_
  
  - [x] 20.4 Test with simulated failure scenarios
    - Lambda deployment failure
    - DynamoDB throttling
    - RDS storage full
    - API Gateway timeout
    - Step Functions execution failure
    - Verify correct root cause identification (>70% confidence)
    - Verify appropriate fix recommendations
    - Verify email delivery with rich HTML formatting
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  
  - [x] 20.5 Verify cost optimization
    - Confirm S3 lifecycle policies active
    - Confirm DynamoDB on-demand billing
    - Confirm Lambda using ARM runtime
    - Verify token usage within Free Tier
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [x] 20.6 Verify observability
    - Check CloudWatch dashboard displays metrics
    - Verify metrics emission for all agents
    - Verify error logging with context
    - Test warning metrics (latency, cost)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 21. Final validation and handoff
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (minimum 100 iterations each)
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests validate AWS service interactions and end-to-end flows
- The implementation uses Python with boto3 for AWS SDK
- Use `hypothesis` library for property-based testing
- Use `moto` for mocking AWS services in tests
- Use AWS Lambda Powertools for structured logging and metrics
- All agents are implemented as separate modules for maintainability
- Bedrock Knowledge Base eliminates need for separate vector database
- SES provides rich HTML email formatting for enhanced alerts
- Cost optimization features keep system within AWS Free Tier limits
