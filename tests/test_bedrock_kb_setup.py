"""Tests for Bedrock Knowledge Base setup"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


@pytest.fixture
def mock_env():
    """Set up environment variables for testing"""
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_ACCOUNT_ID"] = "123456789012"
    os.environ["KB_DATA_SOURCE_BUCKET_NAME"] = "test-kb-bucket"
    os.environ["KB_NAME"] = "test-kb"
    yield
    # Cleanup
    for key in ["AWS_REGION", "AWS_ACCOUNT_ID", "KB_DATA_SOURCE_BUCKET_NAME", "KB_NAME"]:
        if key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_bedrock_agent_client():
    """Mock Bedrock Agent client"""
    with patch("boto3.client") as mock_client:
        mock_bedrock = MagicMock()
        mock_client.return_value = mock_bedrock
        yield mock_bedrock


@pytest.fixture
def mock_iam_client():
    """Mock IAM client"""
    with patch("boto3.client") as mock_client:
        mock_iam = MagicMock()
        mock_client.return_value = mock_iam
        yield mock_iam


class TestKnowledgeBaseSetup:
    """Test Knowledge Base setup functions"""
    
    def test_get_kb_name_default(self):
        """Test getting default Knowledge Base name"""
        from src.infrastructure.setup_bedrock_kb import get_kb_name
        
        # Remove env var if exists
        if "KB_NAME" in os.environ:
            del os.environ["KB_NAME"]
        
        assert get_kb_name() == "incident-response-kb"
    
    def test_get_kb_name_from_env(self, mock_env):
        """Test getting Knowledge Base name from environment"""
        from src.infrastructure.setup_bedrock_kb import get_kb_name
        
        assert get_kb_name() == "test-kb"
    
    def test_get_kb_role_arn(self, mock_env):
        """Test getting Knowledge Base IAM role ARN"""
        from src.infrastructure.setup_bedrock_kb import get_kb_role_arn
        
        arn = get_kb_role_arn()
        assert arn == "arn:aws:iam::123456789012:role/incident-response-kb-role"
    
    def test_get_kb_role_arn_no_account_id(self):
        """Test getting role ARN without AWS_ACCOUNT_ID raises error"""
        from src.infrastructure.setup_bedrock_kb import get_kb_role_arn
        
        if "AWS_ACCOUNT_ID" in os.environ:
            del os.environ["AWS_ACCOUNT_ID"]
        
        with pytest.raises(ValueError, match="AWS_ACCOUNT_ID"):
            get_kb_role_arn()
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_create_kb_iam_role_success(self, mock_boto_client, mock_env):
        """Test successful IAM role creation"""
        from src.infrastructure.setup_bedrock_kb import create_kb_iam_role
        
        mock_iam = MagicMock()
        mock_boto_client.return_value = mock_iam
        
        mock_iam.create_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/incident-response-kb-role"
            }
        }
        
        role_arn = create_kb_iam_role()
        
        assert role_arn == "arn:aws:iam::123456789012:role/incident-response-kb-role"
        assert mock_iam.create_role.called
        assert mock_iam.put_role_policy.call_count == 2  # S3 and Bedrock policies
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_create_kb_iam_role_already_exists(self, mock_boto_client, mock_env):
        """Test IAM role creation when role already exists"""
        from src.infrastructure.setup_bedrock_kb import create_kb_iam_role
        
        mock_iam = MagicMock()
        mock_boto_client.return_value = mock_iam
        
        # Simulate role already exists
        mock_iam.create_role.side_effect = ClientError(
            {"Error": {"Code": "EntityAlreadyExists"}},
            "CreateRole"
        )
        mock_iam.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/incident-response-kb-role"
            }
        }
        
        role_arn = create_kb_iam_role()
        
        assert role_arn == "arn:aws:iam::123456789012:role/incident-response-kb-role"
        assert mock_iam.get_role.called
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    @patch("src.infrastructure.setup_bedrock_kb.create_kb_iam_role")
    @patch("time.sleep")
    def test_create_knowledge_base_success(self, mock_sleep, mock_create_role, mock_boto_client, mock_env):
        """Test successful Knowledge Base creation"""
        from src.infrastructure.setup_bedrock_kb import create_knowledge_base
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_create_role.return_value = "arn:aws:iam::123456789012:role/incident-response-kb-role"
        
        mock_bedrock.create_knowledge_base.return_value = {
            "knowledgeBase": {
                "knowledgeBaseId": "kb-12345",
                "name": "test-kb"
            }
        }
        
        response = create_knowledge_base()
        
        assert response["knowledgeBase"]["knowledgeBaseId"] == "kb-12345"
        assert mock_bedrock.create_knowledge_base.called
        
        # Verify configuration
        call_args = mock_bedrock.create_knowledge_base.call_args[1]
        assert call_args["name"] == "test-kb"
        assert "vectorKnowledgeBaseConfiguration" in call_args["knowledgeBaseConfiguration"]
        assert "amazon.titan-embed-text-v1" in call_args["knowledgeBaseConfiguration"]["vectorKnowledgeBaseConfiguration"]["embeddingModelArn"]
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_create_data_source_success(self, mock_boto_client, mock_env):
        """Test successful data source creation"""
        from src.infrastructure.setup_bedrock_kb import create_data_source
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.create_data_source.return_value = {
            "dataSource": {
                "dataSourceId": "ds-12345",
                "name": "test-kb-s3-source"
            }
        }
        
        response = create_data_source("kb-12345")
        
        assert response["dataSource"]["dataSourceId"] == "ds-12345"
        assert mock_bedrock.create_data_source.called
        
        # Verify configuration
        call_args = mock_bedrock.create_data_source.call_args[1]
        assert call_args["knowledgeBaseId"] == "kb-12345"
        assert call_args["dataSourceConfiguration"]["type"] == "S3"
        assert "chunkingConfiguration" in call_args["vectorIngestionConfiguration"]
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_verify_knowledge_base_exists_true(self, mock_boto_client, mock_env):
        """Test verifying Knowledge Base exists"""
        from src.infrastructure.setup_bedrock_kb import verify_knowledge_base_exists
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": [
                {"name": "test-kb", "knowledgeBaseId": "kb-12345"}
            ]
        }
        
        assert verify_knowledge_base_exists() is True
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_verify_knowledge_base_exists_false(self, mock_boto_client, mock_env):
        """Test verifying Knowledge Base does not exist"""
        from src.infrastructure.setup_bedrock_kb import verify_knowledge_base_exists
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": []
        }
        
        assert verify_knowledge_base_exists() is False
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_get_knowledge_base_id_success(self, mock_boto_client, mock_env):
        """Test getting Knowledge Base ID"""
        from src.infrastructure.setup_bedrock_kb import get_knowledge_base_id
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": [
                {"name": "test-kb", "knowledgeBaseId": "kb-12345"}
            ]
        }
        
        kb_id = get_knowledge_base_id()
        assert kb_id == "kb-12345"
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_get_knowledge_base_id_not_found(self, mock_boto_client, mock_env):
        """Test getting Knowledge Base ID when not found"""
        from src.infrastructure.setup_bedrock_kb import get_knowledge_base_id
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.list_knowledge_bases.return_value = {
            "knowledgeBaseSummaries": []
        }
        
        with pytest.raises(ValueError, match="not found"):
            get_knowledge_base_id()


class TestKnowledgeBaseConfiguration:
    """Test Knowledge Base configuration details"""
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    @patch("src.infrastructure.setup_bedrock_kb.create_kb_iam_role")
    @patch("time.sleep")
    def test_kb_uses_titan_embeddings(self, mock_sleep, mock_create_role, mock_boto_client, mock_env):
        """Test that Knowledge Base uses Amazon Titan Embeddings"""
        from src.infrastructure.setup_bedrock_kb import create_knowledge_base
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_create_role.return_value = "arn:aws:iam::123456789012:role/incident-response-kb-role"
        
        mock_bedrock.create_knowledge_base.return_value = {
            "knowledgeBase": {"knowledgeBaseId": "kb-12345"}
        }
        
        create_knowledge_base()
        
        call_args = mock_bedrock.create_knowledge_base.call_args[1]
        embedding_arn = call_args["knowledgeBaseConfiguration"]["vectorKnowledgeBaseConfiguration"]["embeddingModelArn"]
        
        assert "amazon.titan-embed-text-v1" in embedding_arn
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_data_source_chunking_configuration(self, mock_boto_client, mock_env):
        """Test data source has proper chunking configuration"""
        from src.infrastructure.setup_bedrock_kb import create_data_source
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        
        mock_bedrock.create_data_source.return_value = {
            "dataSource": {"dataSourceId": "ds-12345"}
        }
        
        create_data_source("kb-12345")
        
        call_args = mock_bedrock.create_data_source.call_args[1]
        chunking_config = call_args["vectorIngestionConfiguration"]["chunkingConfiguration"]
        
        assert chunking_config["chunkingStrategy"] == "FIXED_SIZE"
        assert "fixedSizeChunkingConfiguration" in chunking_config
        assert chunking_config["fixedSizeChunkingConfiguration"]["maxTokens"] == 300
        assert chunking_config["fixedSizeChunkingConfiguration"]["overlapPercentage"] == 20
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    @patch("src.infrastructure.setup_bedrock_kb.get_kb_data_source_bucket_name")
    def test_data_source_s3_configuration(self, mock_get_bucket, mock_boto_client, mock_env):
        """Test data source S3 configuration"""
        from src.infrastructure.setup_bedrock_kb import create_data_source
        
        mock_bedrock = MagicMock()
        mock_boto_client.return_value = mock_bedrock
        mock_get_bucket.return_value = "test-kb-bucket"
        
        mock_bedrock.create_data_source.return_value = {
            "dataSource": {"dataSourceId": "ds-12345"}
        }
        
        create_data_source("kb-12345")
        
        call_args = mock_bedrock.create_data_source.call_args[1]
        s3_config = call_args["dataSourceConfiguration"]["s3Configuration"]
        
        assert "test-kb-bucket" in s3_config["bucketArn"]
        assert s3_config["inclusionPrefixes"] == ["incidents/"]



class TestKnowledgeBaseQuery:
    """Test Knowledge Base query functions with vector search and hybrid search"""
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_with_defaults(self, mock_boto_client, mock_env):
        """Test querying Knowledge Base with default configuration"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.return_value = {
            "retrievalResults": [
                {"score": 0.85, "content": {"text": "Incident 1"}},
                {"score": 0.72, "content": {"text": "Incident 2"}},
                {"score": 0.55, "content": {"text": "Incident 3"}},  # Below threshold
            ]
        }
        
        response = query_knowledge_base("kb-12345", "Lambda timeout error")
        
        # Verify only results above 0.6 threshold are returned
        assert len(response["retrievalResults"]) == 2
        assert response["retrievalResults"][0]["score"] == 0.85
        assert response["retrievalResults"][1]["score"] == 0.72
        
        # Verify hybrid search was enabled
        call_args = mock_runtime.retrieve.call_args[1]
        assert call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["overrideSearchType"] == "HYBRID"
        assert call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"] == 5
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_custom_params(self, mock_boto_client, mock_env):
        """Test querying Knowledge Base with custom parameters"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.return_value = {
            "retrievalResults": [
                {"score": 0.95, "content": {"text": "Incident 1"}},
                {"score": 0.80, "content": {"text": "Incident 2"}},
                {"score": 0.70, "content": {"text": "Incident 3"}},
            ]
        }
        
        response = query_knowledge_base(
            "kb-12345",
            "DynamoDB throttling",
            max_results=3,
            similarity_threshold=0.75,
            enable_hybrid_search=False
        )
        
        # Verify only results above 0.75 threshold are returned
        assert len(response["retrievalResults"]) == 2
        assert response["retrievalResults"][0]["score"] == 0.95
        assert response["retrievalResults"][1]["score"] == 0.80
        
        # Verify semantic-only search was used
        call_args = mock_runtime.retrieve.call_args[1]
        assert call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["overrideSearchType"] == "SEMANTIC"
        assert call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"] == 3
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_top_5_results(self, mock_boto_client, mock_env):
        """Test that query returns top 5 results by default"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.return_value = {
            "retrievalResults": [
                {"score": 0.95, "content": {"text": f"Incident {i}"}}
                for i in range(10)  # Return 10 results
            ]
        }
        
        query_knowledge_base("kb-12345", "API Gateway timeout")
        
        # Verify numberOfResults is set to 5
        call_args = mock_runtime.retrieve.call_args[1]
        assert call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["numberOfResults"] == 5
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_similarity_threshold(self, mock_boto_client, mock_env):
        """Test that query filters by 0.6 similarity threshold"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.return_value = {
            "retrievalResults": [
                {"score": 0.90, "content": {"text": "High similarity"}},
                {"score": 0.65, "content": {"text": "Above threshold"}},
                {"score": 0.60, "content": {"text": "At threshold"}},
                {"score": 0.59, "content": {"text": "Below threshold"}},
                {"score": 0.30, "content": {"text": "Low similarity"}},
            ]
        }
        
        response = query_knowledge_base("kb-12345", "RDS storage full")
        
        # Verify only results >= 0.6 are returned
        assert len(response["retrievalResults"]) == 3
        assert all(r["score"] >= 0.6 for r in response["retrievalResults"])
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_hybrid_search_enabled(self, mock_boto_client, mock_env):
        """Test that hybrid search (semantic + keyword) is enabled by default"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.return_value = {"retrievalResults": []}
        
        query_knowledge_base("kb-12345", "Lambda deployment failure")
        
        # Verify hybrid search is enabled
        call_args = mock_runtime.retrieve.call_args[1]
        search_type = call_args["retrievalConfiguration"]["vectorSearchConfiguration"]["overrideSearchType"]
        assert search_type == "HYBRID"
    
    def test_get_vector_search_config(self):
        """Test getting default vector search configuration"""
        from src.infrastructure.setup_bedrock_kb import get_vector_search_config
        
        config = get_vector_search_config()
        
        assert config["numberOfResults"] == 5
        assert config["similarityThreshold"] == 0.6
        assert config["hybridSearch"] is True
        assert config["searchType"] == "HYBRID"
    
    @patch("src.infrastructure.setup_bedrock_kb.boto3.client")
    def test_query_knowledge_base_error_handling(self, mock_boto_client, mock_env):
        """Test error handling in Knowledge Base query"""
        from src.infrastructure.setup_bedrock_kb import query_knowledge_base
        
        mock_runtime = MagicMock()
        mock_boto_client.return_value = mock_runtime
        
        mock_runtime.retrieve.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}},
            "Retrieve"
        )
        
        with pytest.raises(ClientError):
            query_knowledge_base("kb-invalid", "test query")
