# Bedrock Knowledge Base Configuration

## Overview

The Bedrock Knowledge Base is configured for the Incident Response System to enable RAG-powered root cause analysis by finding similar historical incidents.

## Configuration Details

### Embedding Model
- **Model**: Amazon Titan Embeddings (amazon.titan-embed-text-v1)
- **Dimensions**: 1536
- **Purpose**: Convert incident documents into vector embeddings for semantic search

### Vector Search Configuration
- **Number of Results**: Top 5 most similar incidents
- **Similarity Threshold**: 0.6 (60% similarity minimum)
- **Search Type**: Hybrid (semantic + keyword)

### Hybrid Search
The Knowledge Base uses hybrid search combining:
1. **Semantic Search**: Vector similarity using embeddings
2. **Keyword Search**: Traditional text matching

This provides better results by finding incidents that are:
- Semantically similar (same concepts, different words)
- Keyword matches (exact terms)

### Storage Backend
- **Type**: OpenSearch Serverless (auto-managed by AWS)
- **Index Name**: incident-history-index
- **Field Mapping**:
  - Vector Field: `embedding`
  - Text Field: `text`
  - Metadata Field: `metadata`

### Data Source
- **Type**: S3
- **Bucket**: Configured via `KB_DATA_SOURCE_BUCKET_NAME` environment variable
- **Prefix**: `incidents/` (only documents in this prefix are indexed)
- **Chunking Strategy**: Fixed size
  - Max Tokens: 300
  - Overlap Percentage: 20%

## Usage

### Query the Knowledge Base

```python
from src.infrastructure.setup_bedrock_kb import query_knowledge_base

# Query with default settings (top 5, 0.6 threshold, hybrid search)
response = query_knowledge_base(
    knowledge_base_id="kb-xxxxx",
    query_text="Lambda deployment failure timeout error"
)

# Query with custom settings
response = query_knowledge_base(
    knowledge_base_id="kb-xxxxx",
    query_text="DynamoDB throttling error",
    max_results=3,
    similarity_threshold=0.8,
    enable_hybrid_search=False  # Semantic only
)

# Access results
for result in response["retrievalResults"]:
    score = result["score"]
    content = result["content"]["text"]
    metadata = result["metadata"]
    print(f"Score: {score:.2f} - {content}")
```

### Get Default Configuration

```python
from src.infrastructure.setup_bedrock_kb import get_vector_search_config

config = get_vector_search_config()
# Returns:
# {
#     "numberOfResults": 5,
#     "similarityThreshold": 0.6,
#     "hybridSearch": True,
#     "searchType": "HYBRID"
# }
```

## Query Time Configuration

The vector search and hybrid search settings are applied at query time, not at Knowledge Base creation time. This allows flexibility to:
- Adjust the number of results per query
- Change similarity thresholds based on use case
- Toggle between hybrid and semantic-only search

## Benefits

1. **Automatic Embedding Generation**: No need to manually create or manage embeddings
2. **Semantic Search**: Finds conceptually similar incidents, not just keyword matches
3. **Hybrid Search**: Combines semantic and keyword matching for better results
4. **Configurable Thresholds**: Adjust similarity requirements per query
5. **Scalable Storage**: OpenSearch Serverless auto-scales with data volume
6. **No Vector Database Management**: AWS manages the vector database infrastructure

## Testing

Run the test script to verify configuration:

```bash
python scripts/test_kb_query.py
```

This will:
1. Verify Knowledge Base exists
2. Display vector search configuration
3. Test queries with different settings
4. Show results with similarity scores

## Requirements Satisfied

This implementation satisfies the following requirements:

- **Requirement 3.5**: Query Bedrock Knowledge Base for similar past incidents
- **Requirement 3.6**: Incorporate historical patterns into root cause analysis
- **Task 2.2**: Set up Bedrock Knowledge Base with:
  - Amazon Titan Embeddings (1536 dimensions) ✓
  - S3 data source with sync settings ✓
  - Vector search configuration (top 5 results, 0.6 similarity threshold) ✓
  - Hybrid search (semantic + keyword) ✓

## Next Steps

1. **Task 2.3**: Populate Knowledge Base with sample historical incidents
2. **Task 7**: Implement Root Cause Agent with RAG integration
3. **Task 13.3**: Implement Knowledge Base sync for new incidents

## Troubleshooting

### No Results Returned
- Knowledge Base may be empty (run Task 2.3 to populate)
- Similarity threshold may be too high (try lowering to 0.5)
- Query text may not match any documents

### Low Similarity Scores
- Documents may need better metadata
- Consider adjusting chunking strategy
- Add more diverse sample incidents

### Query Errors
- Verify Knowledge Base ID is correct
- Check IAM permissions for bedrock-agent-runtime
- Ensure Knowledge Base is in the same region

## References

- [AWS Bedrock Knowledge Base Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Amazon Titan Embeddings](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [Hybrid Search in Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html)
