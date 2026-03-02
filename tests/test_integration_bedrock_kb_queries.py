"""
Integration test for Bedrock Knowledge Base queries.

Tests:
- Similar incident retrieval
- Empty result handling
- Similarity score ranking

Requirements: 3.5, 8.3, 8.4
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Import module to test
from src.agents.kb_query import query_similar_incidents


class TestBedrockKnowledgeBaseQueries:
    """Integration tests for Bedrock Knowledge Base queries."""
    
    def test_similar_incident_retrieval(self):
        """
        Test retrieval of similar incidents from Knowledge Base.
        
        Requirements: 3.5, 8.3
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base response with similar incidents
            mock_client.retrieve.return_value = {
                'retrievalResults': [
                    {
                        'score': 0.85,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-12-01-001',
                                'service_name': 'payment-processor',
                                'failure_type': 'dependency_failure',
                                'root_cause': {
                                    'category': 'dependency_failure',
                                    'description': 'Payment gateway timeout'
                                },
                                'resolution': {
                                    'action': 'Increased timeout to 30s',
                                    'success': True
                                }
                            })
                        },
                        'location': {
                            's3Location': {
                                'uri': 's3://kb-bucket/incidents/inc-2024-12-01-001.json'
                            }
                        },
                        'metadata': {
                            'incident_id': 'inc-2024-12-01-001',
                            'service_name': 'payment-processor',
                            'failure_type': 'dependency_failure'
                        }
                    },
                    {
                        'score': 0.72,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-11-15-003',
                                'service_name': 'payment-processor',
                                'failure_type': 'dependency_failure',
                                'root_cause': {
                                    'category': 'dependency_failure',
                                    'description': 'External API timeout'
                                },
                                'resolution': {
                                    'action': 'Implemented circuit breaker',
                                    'success': True
                                }
                            })
                        },
                        'location': {
                            's3Location': {
                                'uri': 's3://kb-bucket/incidents/inc-2024-11-15-003.json'
                            }
                        },
                        'metadata': {
                            'incident_id': 'inc-2024-11-15-003',
                            'service_name': 'payment-processor',
                            'failure_type': 'dependency_failure'
                        }
                    }
                ]
            }
            
            # Query for similar incidents
            log_summary = {
                'error_patterns': [{'pattern': 'ConnectionTimeout', 'occurrences': 15}],
                'stack_traces': [],
                'relevant_excerpts': ['ERROR: Connection timeout to payment-gateway']
            }
            service_name = 'payment-processor'
            error_message = 'Service health check failed'
            knowledge_base_id = 'test-kb-123'
            
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary
            )
            
            # Verify similar incidents were retrieved
            assert len(results) > 0
            assert len(results) <= 5  # Should return top 5 at most
            
            # Verify incident structure
            for incident in results:
                assert 'incident_id' in incident
                assert 'similarity_score' in incident
                assert 'resolution' in incident or 'root_cause' in incident
            
            # Verify first incident has highest similarity
            assert results[0]['similarity_score'] >= 0.7  # High similarity threshold
    
    def test_empty_result_handling(self):
        """
        Test handling of empty results when no similar incidents found.
        
        Requirements: 8.3
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base response with no results
            mock_client.retrieve.return_value = {
                'retrievalResults': []
            }
            
            # Query for similar incidents
            log_summary = {
                'error_patterns': [{'pattern': 'UniqueError', 'occurrences': 1}],
                'stack_traces': [],
                'relevant_excerpts': ['ERROR: Never seen before']
            }
            service_name = 'new-service'
            error_message = 'Completely new error'
            knowledge_base_id = 'test-kb-123'
            
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary
            )
            
            # Verify empty result set is handled gracefully
            assert isinstance(results, list)
            assert len(results) == 0
            
            # Should not raise an exception
    
    def test_similarity_score_ranking(self):
        """
        Test that similar incidents are ranked by similarity score.
        
        Requirements: 8.4
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base response with multiple incidents (already sorted by Bedrock)
            mock_client.retrieve.return_value = {
                'retrievalResults': [
                    {
                        'score': 0.92,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-11-01-002',
                                'resolution': {'action': 'Fix 2'}
                            })
                        },
                        'metadata': {'incident_id': 'inc-2024-11-01-002'}
                    },
                    {
                        'score': 0.88,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-08-01-004',
                                'resolution': {'action': 'Fix 4'}
                            })
                        },
                        'metadata': {'incident_id': 'inc-2024-08-01-004'}
                    },
                    {
                        'score': 0.78,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-09-01-003',
                                'resolution': {'action': 'Fix 3'}
                            })
                        },
                        'metadata': {'incident_id': 'inc-2024-09-01-003'}
                    },
                    {
                        'score': 0.71,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-07-01-005',
                                'resolution': {'action': 'Fix 5'}
                            })
                        },
                        'metadata': {'incident_id': 'inc-2024-07-01-005'}
                    },
                    {
                        'score': 0.65,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-10-01-001',
                                'resolution': {'action': 'Fix 1'}
                            })
                        },
                        'metadata': {'incident_id': 'inc-2024-10-01-001'}
                    }
                ]
            }
            
            # Query for similar incidents
            log_summary = {
                'error_patterns': [{'pattern': 'TestError', 'occurrences': 5}]
            }
            service_name = 'test-service'
            error_message = 'Test error'
            knowledge_base_id = 'test-kb-123'
            
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary
            )
            
            # Verify results are ranked by similarity score (descending)
            # Bedrock returns results already sorted, so we just verify they're in order
            assert len(results) <= 5  # Top 5 results
            
            for i in range(len(results) - 1):
                assert results[i]['similarity_score'] >= results[i + 1]['similarity_score'], \
                    f"Results not properly ranked: {results[i]['similarity_score']} < {results[i + 1]['similarity_score']}"
            
            # Verify highest similarity is first
            if len(results) > 0:
                assert results[0]['similarity_score'] == 0.92
                assert results[0]['incident_id'] == 'inc-2024-11-01-002'
    
    def test_top_5_limit(self):
        """
        Test that Bedrock Knowledge Base is configured to return top 5 results.
        
        Requirements: 8.4
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base response with exactly 5 incidents
            # (Bedrock limits via numberOfResults parameter)
            mock_results = []
            for i in range(5):
                score = 0.9 - (i * 0.05)  # Decreasing scores: 0.9, 0.85, 0.8, 0.75, 0.7
                mock_results.append({
                    'score': score,
                    'content': {
                        'text': json.dumps({
                            'incident_id': f'inc-2024-{i:02d}-001',
                            'resolution': {'action': f'Fix {i}'}
                        })
                    },
                    'metadata': {'incident_id': f'inc-2024-{i:02d}-001'}
                })
            
            mock_client.retrieve.return_value = {
                'retrievalResults': mock_results
            }
            
            # Query for similar incidents
            log_summary = {'error_patterns': [{'pattern': 'Error', 'occurrences': 1}]}
            service_name = 'test-service'
            error_message = 'Test'
            knowledge_base_id = 'test-kb-123'
            
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary,
                max_results=5  # Request only 5 results
            )
            
            # Verify Bedrock was called with numberOfResults=5
            mock_client.retrieve.assert_called_once()
            call_args = mock_client.retrieve.call_args
            assert call_args[1]['retrievalConfiguration']['vectorSearchConfiguration']['numberOfResults'] == 5
            
            # Verify results match what Bedrock returned (filtered by threshold)
            assert len(results) == 5  # All 5 are above 0.6 threshold
            
            # Verify all returned results are above threshold
            for result in results:
                assert result['similarity_score'] >= 0.6
    
    def test_query_with_service_name_filter(self):
        """
        Test that queries can filter by service name.
        
        Requirements: 8.3
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base response
            mock_client.retrieve.return_value = {
                'retrievalResults': [
                    {
                        'score': 0.85,
                        'content': {
                            'text': json.dumps({
                                'incident_id': 'inc-2024-12-01-001',
                                'service_name': 'payment-processor',
                                'resolution': {'action': 'Fixed'}
                            })
                        },
                        'metadata': {
                            'incident_id': 'inc-2024-12-01-001',
                            'service_name': 'payment-processor'
                        }
                    }
                ]
            }
            
            # Query for similar incidents with service name
            log_summary = {'error_patterns': [{'pattern': 'Error', 'occurrences': 1}]}
            service_name = 'payment-processor'
            error_message = 'Test'
            knowledge_base_id = 'test-kb-123'
            
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary
            )
            
            # Verify query was made with service name
            mock_client.retrieve.assert_called_once()
            call_args = mock_client.retrieve.call_args
            
            # Verify retrievalQuery contains service name context
            assert 'retrievalQuery' in call_args[1]
            query_text = call_args[1]['retrievalQuery']['text']
            assert 'payment-processor' in query_text.lower() or 'Service:' in query_text
    
    def test_knowledge_base_error_handling(self):
        """
        Test handling of Knowledge Base API errors.
        
        Requirements: 3.5
        """
        # Mock Bedrock Agent Runtime client
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            
            # Mock Knowledge Base API error
            mock_client.retrieve.side_effect = Exception("Knowledge Base unavailable")
            
            # Query for similar incidents
            log_summary = {'error_patterns': [{'pattern': 'Error', 'occurrences': 1}]}
            service_name = 'test-service'
            error_message = 'Test'
            knowledge_base_id = 'test-kb-123'
            
            # Should handle error gracefully and return empty list
            results = query_similar_incidents(
                knowledge_base_id=knowledge_base_id,
                service_name=service_name,
                error_message=error_message,
                log_summary=log_summary
            )
            
            # Verify empty result on error
            assert isinstance(results, list)
            assert len(results) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
