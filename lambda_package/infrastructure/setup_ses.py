"""SES Email Identity Setup"""
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from .aws_config import get_aws_region, SES_SENDER_EMAIL, SES_VERIFIED_DOMAIN, create_boto3_client

logger = Logger()


def verify_email_identity() -> dict:
    """
    Verify SES email identity for sending incident alerts.
    
    This will send a verification email to the specified address.
    The email must be verified before SES can send from this address.
    
    Returns:
        dict: Verification response
    """
    ses_client = create_boto3_client("ses")
    
    try:
        response = ses_client.verify_email_identity(
            EmailAddress=SES_SENDER_EMAIL
        )
        logger.info(f"Verification email sent to: {SES_SENDER_EMAIL}")
        logger.info("Please check the inbox and click the verification link")
        return response
        
    except ClientError as e:
        logger.error(f"Error verifying email identity: {e}")
        raise


def verify_domain_identity() -> dict:
    """
    Verify SES domain identity for sending incident alerts.
    
    This is an alternative to email verification that allows
    sending from any address in the domain.
    
    Returns:
        dict: Verification response with DNS records to configure
    """
    ses_client = create_boto3_client("ses")
    
    try:
        response = ses_client.verify_domain_identity(
            Domain=SES_VERIFIED_DOMAIN
        )
        logger.info(f"Domain verification initiated for: {SES_VERIFIED_DOMAIN}")
        logger.info(f"Add this TXT record to DNS: {response['VerificationToken']}")
        return response
        
    except ClientError as e:
        logger.error(f"Error verifying domain identity: {e}")
        raise


def check_verification_status() -> dict:
    """
    Check the verification status of email identities.
    
    Returns:
        dict: Verification status for all identities
    """
    ses_client = create_boto3_client("ses")
    
    try:
        response = ses_client.get_identity_verification_attributes(
            Identities=[SES_SENDER_EMAIL, SES_VERIFIED_DOMAIN]
        )
        
        for identity, attrs in response["VerificationAttributes"].items():
            status = attrs.get("VerificationStatus", "NotStarted")
            logger.info(f"{identity}: {status}")
        
        return response
        
    except ClientError as e:
        logger.error(f"Error checking verification status: {e}")
        raise


def configure_ses_configuration_set() -> dict:
    """
    Create SES configuration set for tracking email delivery.
    
    Returns:
        dict: Configuration set creation response
    """
    ses_client = create_boto3_client("ses")
    config_set_name = "incident-response-emails"
    
    try:
        response = ses_client.create_configuration_set(
            ConfigurationSet={
                "Name": config_set_name
            }
        )
        logger.info(f"Created SES configuration set: {config_set_name}")
        return response
        
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConfigurationSetAlreadyExists":
            logger.info(f"Configuration set {config_set_name} already exists")
            return {"ConfigurationSet": {"Name": config_set_name}}
        else:
            logger.error(f"Error creating configuration set: {e}")
            raise
