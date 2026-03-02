#!/usr/bin/env python3
"""
Test script for Bedrock Knowledge Base query functionality.

This script demonstrates:
1. Vector search configuration (top 5 results, 0.6 similarity threshold)
2. Hybrid search (semantic + keyword)
3. Query filtering by similarity threshold
"""
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.setup_bedrock_kb import (
    get_knowledge_base_id,
    query_knowledge_base,
    get_vector_search_config,
    verify_knowledge_base_exists
)
from aws_lambda_powertools import Logger

logger = Logger()


def main():
    """Test Knowledge Base query functionality"""
    
    print("=" * 80)
    print("Bedrock Knowledge Base Query Test")
    print("=" * 80)
    print()
    
    # Step 1: Verify Knowledge Base exists
    print("Step 1: Verifying Knowledge Base exists...")
    if not verify_knowledge_base_exists():
        print("❌ Knowledge Base not found. Run setup_infrastructure.py first.")
        return 1
    print("✓ Knowledge Base exists")
    print()
    
    # Step 2: Get Knowledge Base ID
    print("Step 2: Getting Knowledge Base ID...")
    try:
        kb_id = get_knowledge_base_id()
        print(f"✓ Knowledge Base ID: {kb_id}")
    except ValueError as e:
        print(f"❌ Error: {e}")
        return 1
    print()
    
    # Step 3: Display vector search configuration
    print("Step 3: Vector Search Configuration")
    config = get_vector_search_config()
    print(f"  • Number of Results: {config['numberOfResults']}")
    print(f"  • Similarity Threshold: {config['similarityThreshold']}")
    print(f"  • Hybrid Search: {config['hybridSearch']}")
    print(f"  • Search Type: {config['searchType']}")
    print()
    
    # Step 4: Test query with default settings
    print("Step 4: Testing query with default settings...")
    print("  Query: 'Lambda deployment failure timeout error'")
    print("  Settings: top 5 results, 0.6 threshold, hybrid search enabled")
    
    try:
        response = query_knowledge_base(
            knowledge_base_id=kb_id,
            query_text="Lambda deployment failure timeout error",
            max_results=5,
            similarity_threshold=0.6,
            enable_hybrid_search=True
        )
        
        results = response.get("retrievalResults", [])
        print(f"✓ Query successful: {len(results)} results returned")
        
        if results:
            print("\n  Results:")
            for i, result in enumerate(results, 1):
                score = result.get("score", 0)
                content = result.get("content", {}).get("text", "")[:100]
                print(f"    {i}. Score: {score:.2f} - {content}...")
        else:
            print("  ℹ No results found (Knowledge Base may be empty)")
            print("  ℹ Run task 2.3 to populate with sample incidents")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return 1
    print()
    
    # Step 5: Test query with custom threshold
    print("Step 5: Testing query with higher similarity threshold (0.8)...")
    try:
        response = query_knowledge_base(
            knowledge_base_id=kb_id,
            query_text="DynamoDB throttling error",
            max_results=5,
            similarity_threshold=0.8,
            enable_hybrid_search=True
        )
        
        results = response.get("retrievalResults", [])
        print(f"✓ Query successful: {len(results)} results returned (threshold: 0.8)")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return 1
    print()
    
    # Step 6: Test semantic-only search
    print("Step 6: Testing semantic-only search (no keyword matching)...")
    try:
        response = query_knowledge_base(
            knowledge_base_id=kb_id,
            query_text="API Gateway timeout",
            max_results=5,
            similarity_threshold=0.6,
            enable_hybrid_search=False
        )
        
        results = response.get("retrievalResults", [])
        print(f"✓ Query successful: {len(results)} results returned (semantic only)")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return 1
    print()
    
    print("=" * 80)
    print("✓ All tests completed successfully!")
    print()
    print("Configuration Summary:")
    print("  • Amazon Titan Embeddings (1536 dimensions)")
    print("  • Vector search: top 5 results, 0.6 similarity threshold")
    print("  • Hybrid search: semantic + keyword enabled")
    print("  • S3 data source with automatic sync")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
