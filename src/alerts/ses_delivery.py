"""
SES Email Delivery Service

This module handles email delivery via Amazon SES with retry logic,
recipient management, and delivery failure handling.

Requirements:
- 7.1: Alert delivery timing (within 5 seconds)
- 7.5: Incident ID uniqueness
- 7.6: Delivery failure handling with retry
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from .email_formatter import format_email

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SESDeliveryService:
    """
    Handles email delivery via Amazon SES.
    
    Features:
    - HTML and plain text email support
    - Retry logic with exponential backoff
    - Delivery failure logging
    - Recipient management
    
    Requirements:
        - 7.1: Deliver alerts within 5 seconds
        - 7.6: Retry delivery up to 3 times on failure
    """
    
    def __init__(
        self,
        sender_email: str = "incidents@example.com",
        region: str = "us-east-1",
        max_retries: int = 3,
        retry_backoff_base: int = 1
    ):
        """
        Initialize SES delivery service.
        
        Args:
            sender_email: Verified sender email address
            region: AWS region for SES
            max_retries: Maximum number of delivery retries
            retry_backoff_base: Base seconds for exponential backoff
        """
        self.sender_email = sender_email
        self.region = region
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        
        # Initialize SES client
        self.ses_client = boto3.client('ses', region_name=region)
        
        logger.info(
            f"Initialized SESDeliveryService: "
            f"sender={sender_email}, region={region}, max_retries={max_retries}"
        )
    
    def deliver_alert(
        self,
        enhanced_alert: Dict[str, Any],
        recipients: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Deliver enhanced alert via SES email.
        
        Args:
            enhanced_alert: Enhanced alert dictionary from orchestrator
            recipients: List of recipient email addresses (on-call engineers)
            cc_recipients: List of CC email addresses (stakeholders)
        
        Returns:
            Delivery result dictionary with status and message_id
        
        Requirements:
            - 7.1: Deliver within 5 seconds
            - 7.5: Include incident_id in subject
            - 7.6: Retry on failure
        """
        start_time = time.time()
        
        incident_id = enhanced_alert.get('incident_id', 'Unknown')
        
        logger.info(f"Starting email delivery for incident: {incident_id}")
        
        # Default recipients if not provided
        if recipients is None:
            recipients = self._get_default_recipients()
        
        if cc_recipients is None:
            cc_recipients = self._get_default_cc_recipients()
        
        # Format email content
        html_content, text_content = format_email(enhanced_alert)
        
        # Generate subject line
        subject = self._generate_subject(enhanced_alert)
        
        # Attempt delivery with retries
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"Delivery attempt {attempt + 1}/{self.max_retries + 1} "
                    f"for incident: {incident_id}"
                )
                
                # Send email via SES
                response = self._send_email(
                    subject=subject,
                    html_body=html_content,
                    text_body=text_content,
                    recipients=recipients,
                    cc_recipients=cc_recipients
                )
                
                delivery_time = time.time() - start_time
                
                logger.info(
                    f"Email delivered successfully for incident: {incident_id}, "
                    f"message_id={response['MessageId']}, "
                    f"delivery_time={delivery_time:.2f}s"
                )
                
                # Check delivery timing requirement
                if delivery_time > 5.0:
                    logger.warning(
                        f"Email delivery exceeded 5 second target: "
                        f"{delivery_time:.2f}s for incident: {incident_id}"
                    )
                
                return {
                    "success": True,
                    "message_id": response['MessageId'],
                    "incident_id": incident_id,
                    "delivery_time_seconds": delivery_time,
                    "attempt": attempt + 1,
                    "recipients": recipients,
                    "cc_recipients": cc_recipients
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                logger.error(
                    f"SES delivery failed for incident: {incident_id}, "
                    f"attempt {attempt + 1}, error: {error_code} - {error_message}"
                )
                
                # If not last attempt, apply exponential backoff
                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff_base * (2 ** attempt)
                    logger.info(f"Retrying after {backoff_time}s backoff...")
                    time.sleep(backoff_time)
                else:
                    # All retries exhausted
                    delivery_time = time.time() - start_time
                    
                    logger.error(
                        f"Email delivery failed after {self.max_retries + 1} attempts "
                        f"for incident: {incident_id}"
                    )
                    
                    return {
                        "success": False,
                        "error": f"{error_code}: {error_message}",
                        "incident_id": incident_id,
                        "delivery_time_seconds": delivery_time,
                        "attempts": attempt + 1
                    }
            
            except Exception as e:
                logger.error(
                    f"Unexpected error during email delivery for incident: {incident_id}, "
                    f"error: {str(e)}"
                )
                
                if attempt < self.max_retries:
                    backoff_time = self.retry_backoff_base * (2 ** attempt)
                    time.sleep(backoff_time)
                else:
                    delivery_time = time.time() - start_time
                    
                    return {
                        "success": False,
                        "error": str(e),
                        "incident_id": incident_id,
                        "delivery_time_seconds": delivery_time,
                        "attempts": attempt + 1
                    }
    
    def _send_email(
        self,
        subject: str,
        html_body: str,
        text_body: str,
        recipients: List[str],
        cc_recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send email via SES.
        
        Args:
            subject: Email subject line
            html_body: HTML email content
            text_body: Plain text email content
            recipients: List of recipient email addresses
            cc_recipients: List of CC email addresses
        
        Returns:
            SES send_email response
        """
        destination = {
            'ToAddresses': recipients
        }
        
        if cc_recipients:
            destination['CcAddresses'] = cc_recipients
        
        message = {
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_body,
                    'Charset': 'UTF-8'
                },
                'Text': {
                    'Data': text_body,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        response = self.ses_client.send_email(
            Source=self.sender_email,
            Destination=destination,
            Message=message,
            ReplyToAddresses=['incident-response@example.com']
        )
        
        return response
    
    def _generate_subject(self, enhanced_alert: Dict[str, Any]) -> str:
        """
        Generate email subject line with incident ID.
        
        Args:
            enhanced_alert: Enhanced alert dictionary
        
        Returns:
            Email subject line
        
        Requirements:
            - 7.5: Include incident_id in subject
        """
        incident_id = enhanced_alert.get('incident_id', 'Unknown')
        
        # Get service name
        original_alert = enhanced_alert.get('original_alert', {})
        service_name = original_alert.get('service_name', 'Unknown Service')
        
        # Get root cause category if available
        root_cause = enhanced_alert.get('root_cause', {})
        if isinstance(root_cause, dict):
            category = root_cause.get('category', 'Incident')
        else:
            category = 'Incident'
        
        # Format category for display
        category_display = category.replace('_', ' ').title()
        
        return f"🚨 [{incident_id}] {service_name} - {category_display}"
    
    def _get_default_recipients(self) -> List[str]:
        """
        Get default recipient list (on-call engineers).
        
        Returns:
            List of default recipient email addresses
        """
        # In production, this would query an on-call schedule or configuration
        return [
            "oncall-engineer@example.com",
            "incident-response@example.com"
        ]
    
    def _get_default_cc_recipients(self) -> List[str]:
        """
        Get default CC recipient list (stakeholders).
        
        Returns:
            List of default CC email addresses
        """
        # In production, this would be configured based on service ownership
        return [
            "engineering-leads@example.com",
            "operations@example.com"
        ]
    
    def verify_sender_email(self) -> bool:
        """
        Verify that the sender email is verified in SES.
        
        Returns:
            True if sender email is verified
        """
        try:
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[self.sender_email]
            )
            
            attributes = response.get('VerificationAttributes', {})
            sender_status = attributes.get(self.sender_email, {})
            verification_status = sender_status.get('VerificationStatus')
            
            if verification_status == 'Success':
                logger.info(f"Sender email {self.sender_email} is verified")
                return True
            else:
                logger.warning(
                    f"Sender email {self.sender_email} verification status: "
                    f"{verification_status}"
                )
                return False
                
        except ClientError as e:
            logger.error(f"Failed to verify sender email: {str(e)}")
            return False
    
    def get_sending_statistics(self) -> Dict[str, Any]:
        """
        Get SES sending statistics.
        
        Returns:
            Dictionary with sending statistics
        """
        try:
            response = self.ses_client.get_send_statistics()
            
            data_points = response.get('SendDataPoints', [])
            
            if data_points:
                # Calculate totals
                total_sent = sum(dp.get('DeliveryAttempts', 0) for dp in data_points)
                total_bounces = sum(dp.get('Bounces', 0) for dp in data_points)
                total_complaints = sum(dp.get('Complaints', 0) for dp in data_points)
                total_rejects = sum(dp.get('Rejects', 0) for dp in data_points)
                
                return {
                    "total_sent": total_sent,
                    "total_bounces": total_bounces,
                    "total_complaints": total_complaints,
                    "total_rejects": total_rejects,
                    "data_points": len(data_points)
                }
            else:
                return {
                    "total_sent": 0,
                    "total_bounces": 0,
                    "total_complaints": 0,
                    "total_rejects": 0,
                    "data_points": 0
                }
                
        except ClientError as e:
            logger.error(f"Failed to get sending statistics: {str(e)}")
            return {}


# Convenience function for quick email delivery
def send_incident_alert(
    enhanced_alert: Dict[str, Any],
    recipients: Optional[List[str]] = None,
    cc_recipients: Optional[List[str]] = None,
    sender_email: str = "incidents@example.com",
    region: str = "us-east-1"
) -> Dict[str, Any]:
    """
    Send incident alert email via SES.
    
    Args:
        enhanced_alert: Enhanced alert dictionary from orchestrator
        recipients: List of recipient email addresses
        cc_recipients: List of CC email addresses
        sender_email: Verified sender email address
        region: AWS region for SES
    
    Returns:
        Delivery result dictionary
    """
    service = SESDeliveryService(
        sender_email=sender_email,
        region=region
    )
    
    return service.deliver_alert(
        enhanced_alert=enhanced_alert,
        recipients=recipients,
        cc_recipients=cc_recipients
    )
