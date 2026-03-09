"""
HTML Email Templates for Enhanced Alerts

This module provides HTML and text email templates for incident alerts with
rich formatting including confidence indicators, action items, and commands.

Requirements:
- 7.2: Alert content completeness
- 7.3: Alert section structure
"""

from typing import Dict, Any, List


# HTML Email Template with responsive design
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 24px;
        }}
        .header .metadata {{
            font-size: 14px;
            opacity: 0.9;
            color: #000000;
        }}
        .section {{
            margin: 0;
            padding: 25px 20px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .section:last-child {{
            border-bottom: none;
        }}
        .section h2 {{
            margin: 0 0 15px 0;
            font-size: 20px;
            color: #000000;
        }}
        .section h3 {{
            margin: 15px 0 10px 0;
            font-size: 16px;
            color: #555;
        }}
        .confidence-high {{
            color: #2e7d32;
            font-weight: bold;
            font-size: 18px;
        }}
        .confidence-medium {{
            color: #f57c00;
            font-weight: bold;
            font-size: 18px;
        }}
        .confidence-low {{
            color: #c62828;
            font-weight: bold;
            font-size: 18px;
        }}
        .command {{
            background-color: #263238;
            color: #aed581;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .action-item {{
            margin: 15px 0;
            padding: 15px;
            background-color: #f5f5f5;
            border-left: 4px solid #1976d2;
            border-radius: 3px;
        }}
        .action-item strong {{
            color: #1976d2;
            display: block;
            margin-bottom: 5px;
        }}
        .metadata {{
            font-size: 13px;
            color: #666;
        }}
        .evidence-list {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .evidence-list li {{
            margin: 8px 0;
        }}
        .similar-incident {{
            margin: 10px 0;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 3px;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 20px;
            text-align: center;
            font-size: 13px;
            color: #666;
        }}
        .warning {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 3px;
        }}
        .warning strong {{
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Incident Alert: {incident_id}</h1>
            <p class="metadata">Service: {service_name} | Time: {timestamp}</p>
        </div>
        
        {confidence_warning}
        
        <div class="section">
            <h2>Error Details</h2>
            <p><strong>Error Message:</strong></p>
            <div class="command">{error_message}</div>
        </div>
        
        <div class="section">
            <h2>Root Cause Analysis</h2>
            <p><strong>Category:</strong> {root_cause_category}</p>
            <p><strong>Description:</strong> {root_cause_description}</p>
            <p><strong>Confidence:</strong> <span class="confidence-{confidence_level}">{confidence_score}%</span></p>
            {evidence_section}
        </div>
        
        <div class="section">
            <h2>Immediate Actions</h2>
            {action_items}
        </div>
        
        <div class="section">
            <h2>Commands to Execute</h2>
            <div class="command">{commands}</div>
        </div>
        
        <div class="section">
            <h2>Business Impact</h2>
            <p>{business_summary}</p>
            <p><strong>Estimated Resolution:</strong> {estimated_time}</p>
        </div>
        
        <div class="section">
            <h2>Similar Past Incidents</h2>
            {similar_incidents}
        </div>
        
        <div class="footer">
            <p>This alert was generated by the AI-Powered Incident Response System</p>
            <p>Reply to this email or visit the incident dashboard for more details</p>
            <p class="metadata">Incident ID: {incident_id} | Generated: {timestamp}</p>
        </div>
    </div>
</body>
</html>
"""


# Plain text email template for fallback
TEXT_TEMPLATE = """
================================================================================
INCIDENT ALERT: {incident_id}
================================================================================

Service: {service_name}
Time: {timestamp}

{confidence_warning}

ERROR DETAILS:
--------------------------------------------------------------------------------
{error_message}

ROOT CAUSE ({confidence_score}% confidence):
--------------------------------------------------------------------------------
Category: {root_cause_category}
Description: {root_cause_description}{evidence_section}

IMMEDIATE ACTIONS:
--------------------------------------------------------------------------------
{action_items}

COMMANDS TO EXECUTE:
--------------------------------------------------------------------------------
{commands}

BUSINESS IMPACT:
--------------------------------------------------------------------------------
{business_summary}

Estimated Resolution: {estimated_time}

SIMILAR PAST INCIDENTS:
--------------------------------------------------------------------------------
{similar_incidents}

================================================================================
This alert was generated by the AI-Powered Incident Response System
Incident ID: {incident_id} | Generated: {timestamp}
================================================================================
"""


def get_confidence_level(confidence_score: int) -> str:
    """
    Determine confidence level class based on score.
    
    Args:
        confidence_score: Confidence score (0-100)
    
    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    if confidence_score >= 70:
        return "high"
    elif confidence_score >= 40:
        return "medium"
    else:
        return "low"


def format_confidence_warning(confidence_score: int) -> Dict[str, str]:
    """
    Generate confidence warning if score is low.
    
    Args:
        confidence_score: Confidence score (0-100)
    
    Returns:
        Dictionary with HTML and text warnings
    
    Requirements:
        - 7.4: Low confidence warning
    """
    if confidence_score < 50:
        html_warning = """
        <div class="warning">
            <strong>⚠️ Low Confidence Warning</strong>
            <p>The confidence score for this analysis is below 50%. 
            Please verify the root cause and recommended actions before proceeding.</p>
        </div>
        """
        text_warning = """
⚠️  LOW CONFIDENCE WARNING
The confidence score for this analysis is below 50%.
Please verify the root cause and recommended actions before proceeding.
"""
        return {"html": html_warning, "text": text_warning}
    
    return {"html": "", "text": ""}


def format_action_item_html(action: Dict[str, Any]) -> str:
    """
    Format a single action item as HTML.
    
    Args:
        action: Action dictionary with step, action, estimated_time, risk_level
    
    Returns:
        HTML formatted action item
    """
    return f"""
    <div class="action-item">
        <strong>Step {action.get('step', 'N/A')}:</strong> {action.get('action', 'No action specified')}
        <br>
        <span class="metadata">
            Time: {action.get('estimated_time', 'Unknown')} | 
            Risk: {action.get('risk_level', 'Unknown')}
        </span>
    </div>
    """


def format_action_item_text(action: Dict[str, Any]) -> str:
    """
    Format a single action item as plain text.
    
    Args:
        action: Action dictionary with step, action, estimated_time, risk_level
    
    Returns:
        Plain text formatted action item
    """
    return f"""
{action.get('step', 'N/A')}. {action.get('action', 'No action specified')}
   Time: {action.get('estimated_time', 'Unknown')} | Risk: {action.get('risk_level', 'Unknown')}
"""


def format_similar_incident_html(incident: Dict[str, Any]) -> str:
    """
    Format a similar incident as HTML.
    
    Args:
        incident: Incident dictionary with incident_id, timestamp, resolution, resolution_time
    
    Returns:
        HTML formatted similar incident
    """
    # Extract date from timestamp
    timestamp = incident.get('timestamp', '')
    date_str = timestamp[:10] if timestamp else 'Unknown date'
    
    return f"""
    <div class="similar-incident">
        📋 <strong>{incident.get('incident_id', 'Unknown')}</strong>
        <br>
        <span class="metadata">
            Date: {date_str} | 
            Resolution: {incident.get('resolution', 'No resolution recorded')} | 
            Time to Resolve: {incident.get('resolution_time', 'Unknown')}
        </span>
    </div>
    """


def format_similar_incident_text(incident: Dict[str, Any]) -> str:
    """
    Format a similar incident as plain text.
    
    Args:
        incident: Incident dictionary with incident_id, timestamp, resolution, resolution_time
    
    Returns:
        Plain text formatted similar incident
    """
    timestamp = incident.get('timestamp', '')
    date_str = timestamp[:10] if timestamp else 'Unknown date'
    
    return f"• {incident.get('incident_id', 'Unknown')} ({date_str}) - {incident.get('resolution', 'No resolution recorded')} - Resolved in {incident.get('resolution_time', 'Unknown')}"
