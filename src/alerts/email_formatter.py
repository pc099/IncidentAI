"""
Email Formatting Logic for Enhanced Alerts

This module formats enhanced alerts into HTML and plain text emails with
proper styling, evidence lists, action items, and commands.

Requirements:
- 7.2: Alert content completeness
- 7.3: Alert section structure
"""

from typing import Dict, Any, Tuple
from datetime import datetime

from .email_templates import (
    HTML_TEMPLATE,
    TEXT_TEMPLATE,
    get_confidence_level,
    format_confidence_warning,
    format_action_item_html,
    format_action_item_text,
    format_similar_incident_html,
    format_similar_incident_text
)


def format_html_email(enhanced_alert: Dict[str, Any]) -> str:
    """
    Format enhanced alert as HTML email.
    
    Args:
        enhanced_alert: Enhanced alert dictionary from orchestrator
    
    Returns:
        HTML formatted email content
    
    Requirements:
        - 7.2: Include all required sections
        - 7.3: Proper section structure
        - 7.4: Low confidence warning
    """
    # Extract basic information
    incident_id = enhanced_alert.get('incident_id', 'Unknown')
    timestamp = enhanced_alert.get('timestamp', datetime.now().isoformat())
    
    # Extract from original alert
    original_alert = enhanced_alert.get('original_alert', {})
    service_name = original_alert.get('service_name', 'Unknown Service')
    error_message = original_alert.get('error_message', 'No error message available')
    
    # Extract root cause information
    root_cause = enhanced_alert.get('root_cause', {})
    if isinstance(root_cause, dict):
        root_cause_category = root_cause.get('category', 'Unknown')
        root_cause_description = root_cause.get('description', 'No description available')
        evidence = root_cause.get('evidence', [])
    else:
        root_cause_category = 'Unknown'
        root_cause_description = str(root_cause) if root_cause else 'No description available'
        evidence = []
    
    # Get confidence score
    confidence_score = enhanced_alert.get('confidence_score', 0)
    if isinstance(confidence_score, dict):
        confidence_score = confidence_score.get('score', 0)
    confidence_level = get_confidence_level(confidence_score)
    
    # Format confidence warning
    warnings = format_confidence_warning(confidence_score)
    confidence_warning_html = warnings['html']
    
    # Format evidence items - only show section if evidence exists
    if evidence and any(evidence):  # Check if evidence list has non-empty items
        evidence_html = "\n".join([f"<li>{item}</li>" for item in evidence if item])
        evidence_section = f"""
            <h3>Evidence:</h3>
            <ul class="evidence-list">
                {evidence_html}
            </ul>
        """
    else:
        evidence_section = ""  # Hide entire evidence section if empty
    
    # Format action items
    fixes = enhanced_alert.get('recommended_fixes', [])
    if not fixes:
        # Try to get from agent outputs
        agent_outputs = enhanced_alert.get('agent_outputs', {})
        fix_output = agent_outputs.get('fix-recommendation', {})
        if fix_output and fix_output.get('success'):
            fix_data = fix_output.get('output', {})
            fixes = fix_data.get('immediate_actions', [])
    
    if fixes:
        actions_html = "\n".join([format_action_item_html(action) for action in fixes])
    else:
        actions_html = '<p class="metadata">No immediate actions available</p>'
    
    # Format commands
    commands = []
    for action in fixes:
        if isinstance(action, dict) and 'command' in action:
            cmd = action['command']
            if cmd:  # Only add non-empty commands
                commands.append(cmd)
    
    if commands:
        commands_html = "\n".join(commands)
    else:
        commands_html = "No commands available"
    
    # Get business summary
    business_summary = enhanced_alert.get('business_summary', {})
    if isinstance(business_summary, dict):
        business_impact = business_summary.get('impact', 'Impact assessment not available')
        estimated_time = business_summary.get('estimated_resolution', 'Unknown')
    else:
        business_impact = str(business_summary) if business_summary else 'Impact assessment not available'
        estimated_time = 'Unknown'
    
    # Format similar incidents - check root_cause directly (orchestrator stores it there)
    similar_incidents = []
    if isinstance(root_cause, dict):
        similar_incidents = root_cause.get('similar_incidents', [])
    
    # Fallback: check agent_outputs (legacy)
    if not similar_incidents:
        agent_outputs = enhanced_alert.get('agent_outputs', {})
        root_cause_output = agent_outputs.get('root-cause', {})
        if root_cause_output and root_cause_output.get('success'):
            root_cause_data = root_cause_output.get('output', {})
            if isinstance(root_cause_data, dict):
                similar_incidents = root_cause_data.get('similar_incidents', [])
    
    if similar_incidents:
        similar_html = "\n".join([
            format_similar_incident_html(inc) for inc in similar_incidents
        ])
    else:
        similar_html = '<p class="metadata">No similar incidents found</p>'
    
    # Render HTML template
    return HTML_TEMPLATE.format(
        incident_id=incident_id,
        service_name=service_name,
        timestamp=timestamp,
        error_message=error_message,
        confidence_warning=confidence_warning_html,
        root_cause_category=root_cause_category,
        root_cause_description=root_cause_description,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        evidence_section=evidence_section,
        action_items=actions_html,
        commands=commands_html,
        business_summary=business_impact,
        estimated_time=estimated_time,
        similar_incidents=similar_html
    )


def format_text_email(enhanced_alert: Dict[str, Any]) -> str:
    """
    Format enhanced alert as plain text email.
    
    Args:
        enhanced_alert: Enhanced alert dictionary from orchestrator
    
    Returns:
        Plain text formatted email content
    
    Requirements:
        - 7.2: Include all required sections
        - 7.3: Proper section structure
    """
    # Extract basic information
    incident_id = enhanced_alert.get('incident_id', 'Unknown')
    timestamp = enhanced_alert.get('timestamp', datetime.now().isoformat())
    
    # Extract from original alert
    original_alert = enhanced_alert.get('original_alert', {})
    service_name = original_alert.get('service_name', 'Unknown Service')
    error_message = original_alert.get('error_message', 'No error message available')
    
    # Extract root cause information
    root_cause = enhanced_alert.get('root_cause', {})
    if isinstance(root_cause, dict):
        root_cause_category = root_cause.get('category', 'Unknown')
        root_cause_description = root_cause.get('description', 'No description available')
        evidence = root_cause.get('evidence', [])
    else:
        root_cause_category = 'Unknown'
        root_cause_description = str(root_cause) if root_cause else 'No description available'
        evidence = []
    
    # Get confidence score
    confidence_score = enhanced_alert.get('confidence_score', 0)
    if isinstance(confidence_score, dict):
        confidence_score = confidence_score.get('score', 0)
    
    # Format confidence warning
    warnings = format_confidence_warning(confidence_score)
    confidence_warning_text = warnings['text']
    
    # Format evidence items - only show section if evidence exists
    if evidence and any(evidence):  # Check if evidence list has non-empty items
        evidence_text = "\n".join([f"- {item}" for item in evidence if item])
        evidence_section = f"\n\nEVIDENCE:\n{evidence_text}"
    else:
        evidence_section = ""  # Hide entire evidence section if empty
    
    # Format action items
    fixes = enhanced_alert.get('recommended_fixes', [])
    if not fixes:
        # Try to get from agent outputs
        agent_outputs = enhanced_alert.get('agent_outputs', {})
        fix_output = agent_outputs.get('fix-recommendation', {})
        if fix_output and fix_output.get('success'):
            fix_data = fix_output.get('output', {})
            fixes = fix_data.get('immediate_actions', [])
    
    if fixes:
        actions_text = "\n".join([format_action_item_text(action) for action in fixes])
    else:
        actions_text = "No immediate actions available"
    
    # Format commands
    commands = []
    for action in fixes:
        if isinstance(action, dict) and 'command' in action:
            cmd = action['command']
            if cmd:  # Only add non-empty commands
                commands.append(cmd)
    
    if commands:
        commands_text = "\n".join(commands)
    else:
        commands_text = "No commands available"
    
    # Get business summary
    business_summary = enhanced_alert.get('business_summary', {})
    if isinstance(business_summary, dict):
        business_impact = business_summary.get('impact', 'Impact assessment not available')
        estimated_time = business_summary.get('estimated_resolution', 'Unknown')
    else:
        business_impact = str(business_summary) if business_summary else 'Impact assessment not available'
        estimated_time = 'Unknown'
    
    # Format similar incidents - check root_cause directly (orchestrator stores it there)
    similar_incidents = []
    if isinstance(root_cause, dict):
        similar_incidents = root_cause.get('similar_incidents', [])
    
    # Fallback: check agent_outputs (legacy)
    if not similar_incidents:
        agent_outputs = enhanced_alert.get('agent_outputs', {})
        root_cause_output = agent_outputs.get('root-cause', {})
        if root_cause_output and root_cause_output.get('success'):
            root_cause_data = root_cause_output.get('output', {})
            if isinstance(root_cause_data, dict):
                similar_incidents = root_cause_data.get('similar_incidents', [])
    
    if similar_incidents:
        similar_text = "\n".join([
            format_similar_incident_text(inc) for inc in similar_incidents
        ])
    else:
        similar_text = "No similar incidents found"
    
    # Render text template
    return TEXT_TEMPLATE.format(
        incident_id=incident_id,
        service_name=service_name,
        timestamp=timestamp,
        error_message=error_message,
        confidence_warning=confidence_warning_text,
        root_cause_category=root_cause_category,
        root_cause_description=root_cause_description,
        confidence_score=confidence_score,
        evidence_section=evidence_section,
        action_items=actions_text,
        commands=commands_text,
        business_summary=business_impact,
        estimated_time=estimated_time,
        similar_incidents=similar_text
    )


def format_email(enhanced_alert: Dict[str, Any]) -> Tuple[str, str]:
    """
    Format enhanced alert as both HTML and plain text emails.
    
    Args:
        enhanced_alert: Enhanced alert dictionary from orchestrator
    
    Returns:
        Tuple of (html_content, text_content)
    
    Requirements:
        - 7.2: Alert content completeness
        - 7.3: Alert section structure
    """
    html_content = format_html_email(enhanced_alert)
    text_content = format_text_email(enhanced_alert)
    
    return html_content, text_content

