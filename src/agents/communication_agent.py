"""
Communication Agent for AI-Powered Incident Response System

This module implements the Communication Agent responsible for:
- Generating technical and business summaries
- Assessing user impact
- Formatting enhanced alerts for different audiences
- Including confidence warnings when appropriate

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.4
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class CommunicationAgent:
    """
    Communication Agent that formats analysis results for different audiences.
    
    Generates dual summaries (technical and business) and assesses user impact.
    """
    
    def __init__(self):
        """Initialize the Communication Agent."""
        # List of user-facing service patterns
        self.user_facing_patterns = [
            "api", "gateway", "frontend", "web", "mobile", "app",
            "payment", "checkout", "user", "customer", "public"
        ]
    
    def generate_summaries(
        self,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any],
        original_alert: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate enhanced alert with technical and business summaries.
        
        Args:
            root_cause: Output from Root Cause Agent
            fixes: Output from Fix Recommendation Agent
            original_alert: Original incident data
            
        Returns:
            Enhanced alert with dual summaries
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 7.4
        """
        # Generate incident ID
        incident_id = self._generate_incident_id()
        
        # Extract key information
        service_name = original_alert.get("service_name", "unknown")
        timestamp = original_alert.get("timestamp", datetime.utcnow().isoformat())
        confidence_score = root_cause.get("analysis", {}).get("primary_cause", {}).get("confidence_score", 0)
        
        # Generate technical summary
        technical_summary = self._generate_technical_summary(
            root_cause=root_cause,
            fixes=fixes,
            service_name=service_name,
            confidence_score=confidence_score
        )
        
        # Assess user impact
        is_user_facing = self._is_user_facing_service(service_name)
        user_impact = None
        if is_user_facing:
            user_impact = self._assess_user_impact(
                service_name=service_name,
                root_cause=root_cause,
                fixes=fixes
            )
        
        # Generate business summary
        business_summary = self._generate_business_summary(
            root_cause=root_cause,
            fixes=fixes,
            service_name=service_name,
            confidence_score=confidence_score,
            user_impact=user_impact
        )
        
        # Add confidence warning if needed
        confidence_warning = None
        if confidence_score < 50:
            confidence_warning = (
                "⚠️ Low confidence score detected. Manual investigation is recommended "
                "to verify the root cause and recommended fixes."
            )
        
        # Build enhanced alert
        enhanced_alert = {
            "agent": "communication",
            "enhanced_alert": {
                "incident_id": incident_id,
                "timestamp": timestamp,
                "service_name": service_name,
                "technical_summary": technical_summary,
                "business_summary": business_summary,
                "confidence_score": confidence_score,
                "confidence_warning": confidence_warning,
                "root_cause": root_cause.get("analysis", {}),
                "fixes": fixes.get("recommendations", {}),
                "original_alert": original_alert
            }
        }
        
        return enhanced_alert
    
    def _generate_technical_summary(
        self,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any],
        service_name: str,
        confidence_score: int
    ) -> Dict[str, Any]:
        """
        Generate technical summary for engineers.
        
        Includes root cause details, evidence, commands, and time estimates.
        
        Requirements: 5.2
        """
        primary_cause = root_cause.get("analysis", {}).get("primary_cause", {})
        recommendations = fixes.get("recommendations", {})
        immediate_actions = recommendations.get("immediate_actions", [])
        
        # Extract evidence
        evidence = primary_cause.get("evidence", [])
        if isinstance(evidence, list):
            evidence_text = "; ".join(evidence[:3])  # Top 3 evidence items
        else:
            evidence_text = str(evidence)
        
        # Get first immediate fix
        first_fix = immediate_actions[0] if immediate_actions else {}
        immediate_fix = first_fix.get("action", "No immediate fix available")
        command = first_fix.get("command", "")
        
        # Calculate total estimated resolution time
        total_time = sum(
            self._parse_time_estimate(action.get("estimated_time", "0 minutes"))
            for action in immediate_actions
        )
        estimated_resolution = f"{total_time} minutes" if total_time > 0 else "Unknown"
        
        # Build title
        category = primary_cause.get("category", "unknown").replace("_", " ").title()
        title = f"{service_name} - {category}"
        
        technical_summary = {
            "title": title,
            "root_cause": f"{primary_cause.get('description', 'Unknown cause')} ({confidence_score}% confidence)",
            "evidence": evidence_text,
            "immediate_fix": immediate_fix,
            "command": command,
            "estimated_resolution": estimated_resolution,
            "all_actions": immediate_actions,
            "preventive_measures": recommendations.get("preventive_measures", []),
            "rollback_plan": recommendations.get("rollback_plan", "")
        }
        
        return technical_summary
    
    def _generate_business_summary(
        self,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any],
        service_name: str,
        confidence_score: int,
        user_impact: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generate business summary for non-technical stakeholders.
        
        Uses plain language without technical jargon.
        
        Requirements: 5.3, 5.5
        """
        primary_cause = root_cause.get("analysis", {}).get("primary_cause", {})
        recommendations = fixes.get("recommendations", {})
        immediate_actions = recommendations.get("immediate_actions", [])
        
        # Map technical categories to business-friendly descriptions
        category_map = {
            "configuration_error": "configuration issue",
            "resource_exhaustion": "capacity limitation",
            "dependency_failure": "external service connectivity issue"
        }
        
        category = primary_cause.get("category", "unknown")
        friendly_category = category_map.get(category, "technical issue")
        
        # Build business-friendly title
        title = f"{service_name.replace('-', ' ').replace('_', ' ').title()} Temporarily Unavailable"
        
        # Build impact description
        description = primary_cause.get("description", "Unknown issue")
        impact = f"Service experiencing issues due to {friendly_category}"
        
        # Determine status
        if confidence_score >= 70:
            status = "Root cause identified, fix in progress"
        elif confidence_score >= 40:
            status = "Investigating issue, preliminary fix identified"
        else:
            status = "Issue detected, investigation in progress"
        
        # Calculate estimated resolution
        total_time = sum(
            self._parse_time_estimate(action.get("estimated_time", "0 minutes"))
            for action in immediate_actions
        )
        estimated_resolution = f"{total_time} minutes" if total_time > 0 else "Under investigation"
        
        business_summary = {
            "title": title,
            "impact": impact,
            "status": status,
            "estimated_resolution": estimated_resolution
        }
        
        # Add user impact if service is user-facing
        if user_impact:
            business_summary["user_impact"] = user_impact
        
        return business_summary
    
    def _is_user_facing_service(self, service_name: str) -> bool:
        """
        Determine if a service is user-facing based on its name.
        
        Requirements: 5.5
        """
        service_lower = service_name.lower()
        return any(pattern in service_lower for pattern in self.user_facing_patterns)
    
    def _assess_user_impact(
        self,
        service_name: str,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any]
    ) -> str:
        """
        Calculate estimated user impact for user-facing services.
        
        Requirements: 5.5
        """
        primary_cause = root_cause.get("analysis", {}).get("primary_cause", {})
        category = primary_cause.get("category", "unknown")
        confidence_score = primary_cause.get("confidence_score", 0)
        
        # Determine severity based on category and confidence
        if category == "dependency_failure":
            if confidence_score >= 70:
                impact = "Customers may experience service failures or timeouts"
            else:
                impact = "Some customers may experience intermittent issues"
        elif category == "resource_exhaustion":
            if confidence_score >= 70:
                impact = "Service degradation affecting all users"
            else:
                impact = "Potential performance issues for some users"
        elif category == "configuration_error":
            if confidence_score >= 70:
                impact = "Service unavailable for all users"
            else:
                impact = "Some features may be unavailable"
        else:
            impact = "Users may experience service disruptions"
        
        return impact
    
    def _parse_time_estimate(self, time_str: str) -> int:
        """
        Parse time estimate string to minutes.
        
        Examples: "2 minutes", "1 minute", "30 seconds"
        """
        time_str = time_str.lower().strip()
        
        if "minute" in time_str:
            try:
                return int(time_str.split()[0])
            except (ValueError, IndexError):
                return 0
        elif "second" in time_str:
            try:
                seconds = int(time_str.split()[0])
                return max(1, seconds // 60)  # Convert to minutes, minimum 1
            except (ValueError, IndexError):
                return 0
        elif "hour" in time_str:
            try:
                hours = int(time_str.split()[0])
                return hours * 60
            except (ValueError, IndexError):
                return 0
        
        return 0
    
    def _generate_incident_id(self) -> str:
        """
        Generate unique incident ID.
        
        Format: inc-YYYY-MM-DD-NNN
        
        Requirements: 7.4
        """
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"inc-{date_str}-{unique_suffix}"



class BedrockCommunicationFormatter:
    """
    Bedrock-powered communication formatter using Claude models.
    
    Generates dual summaries (technical and business) using AI.
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"):
        """
        Initialize Bedrock communication formatter.
        
        Args:
            bedrock_model_id: Bedrock model ID for Claude
        """
        self.bedrock_model_id = bedrock_model_id
        self.bedrock_client = None
    
    def _get_bedrock_client(self):
        """Get or create Bedrock client."""
        if self.bedrock_client is None:
            import boto3
            self.bedrock_client = boto3.client('bedrock-runtime')
        return self.bedrock_client
    
    def create_prompt(
        self,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any],
        service_name: str,
        confidence_score: int
    ) -> str:
        """
        Create Bedrock prompt for dual summary generation.
        
        Requirements: 5.1, 5.2, 5.3
        """
        primary_cause = root_cause.get("analysis", {}).get("primary_cause", {})
        recommendations = fixes.get("recommendations", {})
        
        # Extract evidence
        evidence = primary_cause.get("evidence", [])
        evidence_text = "\n".join(f"- {e}" for e in evidence) if isinstance(evidence, list) else str(evidence)
        
        # Extract immediate actions
        immediate_actions = recommendations.get("immediate_actions", [])
        actions_text = "\n".join(
            f"{i+1}. {action.get('action', 'N/A')} (Time: {action.get('estimated_time', 'Unknown')}, Risk: {action.get('risk_level', 'Unknown')})"
            for i, action in enumerate(immediate_actions)
        )
        
        # Extract commands
        commands = [action.get("command", "") for action in immediate_actions if action.get("command")]
        commands_text = "\n".join(commands) if commands else "No commands available"
        
        prompt = f"""Create two summaries for this incident:

Service: {service_name}
Root Cause Category: {primary_cause.get('category', 'unknown')}
Root Cause Description: {primary_cause.get('description', 'Unknown')}
Confidence Score: {confidence_score}%

Evidence:
{evidence_text}

Recommended Actions:
{actions_text}

Commands to Execute:
{commands_text}

Preventive Measures:
{self._format_preventive_measures(recommendations.get('preventive_measures', []))}

Please generate:

1. Technical Summary (for engineers):
   - Include specific error details and root cause
   - Show exact commands to run
   - Reference log evidence
   - Keep it concise (max 5 sentences)
   - Use technical terminology

2. Business Summary (for non-technical stakeholders):
   - Explain in plain language what happened
   - Focus on user/business impact
   - Avoid technical jargon
   - Provide time estimates
   - Keep it concise (max 5 sentences)

Format your response as JSON with this structure:
{{
  "technical_summary": {{
    "title": "Brief technical title",
    "description": "Technical explanation with details",
    "key_actions": ["Action 1", "Action 2"],
    "estimated_resolution": "X minutes"
  }},
  "business_summary": {{
    "title": "Business-friendly title",
    "description": "Plain language explanation",
    "impact": "User/business impact description",
    "estimated_resolution": "X minutes"
  }}
}}"""
        
        return prompt
    
    def _format_preventive_measures(self, measures: List[Dict[str, Any]]) -> str:
        """Format preventive measures for prompt."""
        if not measures:
            return "None specified"
        
        return "\n".join(
            f"- {m.get('action', 'N/A')} (Priority: {m.get('priority', 'Unknown')})"
            for m in measures
        )
    
    def invoke_claude(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Invoke Claude model via Bedrock.
        
        Args:
            prompt: Prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            
        Returns:
            Claude response
            
        Requirements: 5.1, 5.2, 5.3
        """
        import json
        
        client = self._get_bedrock_client()
        
        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Invoke model
        response = client.invoke_model(
            modelId=self.bedrock_model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        return response_body
    
    def parse_claude_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Claude response to extract summaries.
        
        Args:
            response: Raw Claude response
            
        Returns:
            Parsed summaries
        """
        import json
        
        # Extract content from response
        content = response.get("content", [])
        if not content:
            raise ValueError("Empty response from Claude")
        
        # Get text content
        text_content = ""
        for item in content:
            if item.get("type") == "text":
                text_content = item.get("text", "")
                break
        
        if not text_content:
            raise ValueError("No text content in Claude response")
        
        # Try to parse as JSON
        try:
            # Look for JSON in the response
            start_idx = text_content.find("{")
            end_idx = text_content.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text_content[start_idx:end_idx]
                summaries = json.loads(json_str)
                return summaries
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Claude response as JSON: {e}")
    
    def generate_with_bedrock(
        self,
        root_cause: Dict[str, Any],
        fixes: Dict[str, Any],
        service_name: str,
        confidence_score: int
    ) -> Dict[str, Any]:
        """
        Generate summaries using Bedrock Claude.
        
        Args:
            root_cause: Root cause analysis
            fixes: Fix recommendations
            service_name: Service name
            confidence_score: Confidence score
            
        Returns:
            Technical and business summaries
            
        Requirements: 5.1, 5.2, 5.3
        """
        # Create prompt
        prompt = self.create_prompt(
            root_cause=root_cause,
            fixes=fixes,
            service_name=service_name,
            confidence_score=confidence_score
        )
        
        # Invoke Claude
        response = self.invoke_claude(prompt)
        
        # Parse response
        summaries = self.parse_claude_response(response)
        
        # Validate structure
        if "technical_summary" not in summaries or "business_summary" not in summaries:
            raise ValueError("Invalid summary structure from Claude")
        
        return summaries
