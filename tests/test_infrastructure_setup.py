"""Tests for infrastructure setup modules."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


class TestS3Setup:
    """Tests for S3 bucket setup."""
    
    @patch("src.infrastructure.setup_s3.boto3.client")
    def test_create_log_bucket_success(self, mock_boto_client):
        """Test successful S3 bucket creation."""
        from src.infrastructure.setup_s3 import create_log_bucket
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.create_bucket.return_value = {"Location": "/test-bucket"}
        
        result = create_log_bucket()
        
        assert result["Location"] == "/test-bucket"
        mock_s3.create_bucket.assert_called_once()
        mock_s3.put_bucket_versioning.assert_called_once()
        mock_s3.put_bucket_lifecycle_configuration.assert_called_once()
        mock_s3.put_bucket_encryption.assert_called_once()
    
    @patch("src.infrastructure.setup_s3.boto3.client")
    def test_verify_bucket_exists(self, mock_boto_client):
        """Test bucket existence verification."""
        from src.infrastructure.setup_s3 import verify_bucket_exists
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        result = verify_bucket_exists()
        
        assert result is True
        mock_s3.head_bucket.assert_called_once()
    
    @patch("src.infrastructure.setup_s3.boto3.client")
    @patch.dict("os.environ", {"AWS_ACCOUNT_ID": "123456789012"})
    def test_create_kb_data_source_bucket_success(self, mock_boto_client):
        """Test successful Knowledge Base S3 bucket creation."""
        from src.infrastructure.setup_s3 import create_kb_data_source_bucket
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.create_bucket.return_value = {"Location": "/test-kb-bucket"}
        
        result = create_kb_data_source_bucket()
        
        assert result["Location"] == "/test-kb-bucket"
        mock_s3.create_bucket.assert_called_once()
        mock_s3.put_bucket_versioning.assert_called_once()
        mock_s3.put_bucket_encryption.assert_called_once()
        mock_s3.put_bucket_policy.assert_called_once()
        
        # Verify versioning is enabled
        versioning_call = mock_s3.put_bucket_versioning.call_args
        assert versioning_call[1]["VersioningConfiguration"]["Status"] == "Enabled"
        
        # Verify bucket policy includes Bedrock access
        policy_call = mock_s3.put_bucket_policy.call_args
        import json
        policy = json.loads(policy_call[1]["Policy"])
        assert policy["Statement"][0]["Principal"]["Service"] == "bedrock.amazonaws.com"
        assert "s3:GetObject" in policy["Statement"][0]["Action"]
        assert "s3:ListBucket" in policy["Statement"][0]["Action"]
    
    @patch("src.infrastructure.setup_s3.boto3.client")
    def test_verify_kb_bucket_exists(self, mock_boto_client):
        """Test Knowledge Base bucket existence verification."""
        from src.infrastructure.setup_s3 import verify_kb_bucket_exists
        
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}
        
        result = verify_kb_bucket_exists()
        
        assert result is True
        mock_s3.head_bucket.assert_called_once()


class TestDynamoDBSetup:
    """Tests for DynamoDB table setup."""
    
    @patch("src.infrastructure.setup_dynamodb.boto3.client")
    def test_create_incident_table_success(self, mock_boto_client):
        """Test successful DynamoDB table creation."""
        from src.infrastructure.setup_dynamodb import create_incident_table
        
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        mock_dynamodb.create_table.return_value = {
            "TableDescription": {"TableName": "incident-history"}
        }
        
        # Mock waiter
        mock_waiter = Mock()
        mock_dynamodb.get_waiter.return_value = mock_waiter
        
        result = create_incident_table()
        
        assert result["TableDescription"]["TableName"] == "incident-history"
        mock_dynamodb.create_table.assert_called_once()
        
        # Verify table configuration
        call_args = mock_dynamodb.create_table.call_args
        assert call_args[1]["BillingMode"] == "PAY_PER_REQUEST"
        assert len(call_args[1]["GlobalSecondaryIndexes"]) == 1
        assert call_args[1]["GlobalSecondaryIndexes"][0]["IndexName"] == "service-timestamp-index"
    
    @patch("src.infrastructure.setup_dynamodb.boto3.client")
    def test_verify_table_exists(self, mock_boto_client):
        """Test table existence verification."""
        from src.infrastructure.setup_dynamodb import verify_table_exists
        
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        mock_dynamodb.describe_table.return_value = {}
        
        result = verify_table_exists()
        
        assert result is True
        mock_dynamodb.describe_table.assert_called_once()


class TestSESSetup:
    """Tests for SES email identity setup."""
    
    @patch("src.infrastructure.setup_ses.boto3.client")
    def test_verify_email_identity(self, mock_boto_client):
        """Test SES email identity verification."""
        from src.infrastructure.setup_ses import verify_email_identity
        
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.verify_email_identity.return_value = {}
        
        result = verify_email_identity()
        
        assert result == {}
        mock_ses.verify_email_identity.assert_called_once()
    
    @patch("src.infrastructure.setup_ses.boto3.client")
    def test_check_verification_status(self, mock_boto_client):
        """Test checking SES verification status."""
        from src.infrastructure.setup_ses import check_verification_status
        
        mock_ses = Mock()
        mock_boto_client.return_value = mock_ses
        mock_ses.get_identity_verification_attributes.return_value = {
            "VerificationAttributes": {
                "incidents@example.com": {"VerificationStatus": "Success"}
            }
        }
        
        result = check_verification_status()
        
        assert "VerificationAttributes" in result
        assert result["VerificationAttributes"]["incidents@example.com"]["VerificationStatus"] == "Success"


class TestIAMSetup:
    """Tests for IAM role setup."""
    
    @patch("src.infrastructure.setup_iam.boto3.client")
    def test_create_lambda_execution_role(self, mock_boto_client):
        """Test Lambda execution role creation."""
        from src.infrastructure.setup_iam import create_lambda_execution_role
        
        mock_iam = Mock()
        mock_boto_client.return_value = mock_iam
        mock_iam.create_role.return_value = {
            "Role": {"RoleName": "incident-response-lambda-role"}
        }
        
        result = create_lambda_execution_role()
        
        assert result["Role"]["RoleName"] == "incident-response-lambda-role"
        mock_iam.create_role.assert_called_once()
        mock_iam.attach_role_policy.assert_called_once()
        mock_iam.put_role_policy.assert_called_once()
    
    @patch("src.infrastructure.setup_iam.boto3.client")
    def test_get_role_arn(self, mock_boto_client):
        """Test getting IAM role ARN."""
        from src.infrastructure.setup_iam import get_role_arn
        
        mock_iam = Mock()
        mock_boto_client.return_value = mock_iam
        mock_iam.get_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/test-role"}
        }
        
        result = get_role_arn("test-role")
        
        assert result == "arn:aws:iam::123456789012:role/test-role"
        mock_iam.get_role.assert_called_once_with(RoleName="test-role")


class TestAWSConfig:
    """Tests for AWS configuration."""
    
    def test_get_aws_region(self):
        """Test getting AWS region."""
        from src.infrastructure.aws_config import get_aws_region
        
        region = get_aws_region()
        assert isinstance(region, str)
        assert len(region) > 0
    
    def test_get_log_bucket_name(self):
        """Test getting log bucket name."""
        from src.infrastructure.aws_config import get_log_bucket_name
        
        bucket_name = get_log_bucket_name()
        assert isinstance(bucket_name, str)
        assert len(bucket_name) > 0
    
    def test_get_kb_data_source_bucket_name(self):
        """Test getting Knowledge Base data source bucket name."""
        from src.infrastructure.aws_config import get_kb_data_source_bucket_name
        
        bucket_name = get_kb_data_source_bucket_name()
        assert isinstance(bucket_name, str)
        assert len(bucket_name) > 0
    
    def test_get_incident_table_name(self):
        """Test getting incident table name."""
        from src.infrastructure.aws_config import get_incident_table_name
        
        table_name = get_incident_table_name()
        assert table_name == "incident-history"
