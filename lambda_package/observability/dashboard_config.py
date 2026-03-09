"""CloudWatch dashboard configuration for incident response system."""

import boto3
import json
from typing import Optional


class DashboardConfig:
    """Creates and manages CloudWatch dashboard for incident response metrics."""
    
    def __init__(self, dashboard_name: str = "IncidentResponseDashboard", region: str = "us-east-1"):
        """
        Initialize the dashboard configuration.
        
        Args:
            dashboard_name: Name of the CloudWatch dashboard
            region: AWS region
        """
        self.cloudwatch = boto3.client('cloudwatch', region_name=region)
        self.dashboard_name = dashboard_name
        self.region = region
        self.namespace = "IncidentResponse"
        
    def create_dashboard(self):
        """Create the CloudWatch dashboard with all widgets."""
        dashboard_body = {
            "widgets": [
                self._create_incident_volume_widget(),
                self._create_resolution_time_widget(),
                self._create_confidence_score_widget(),
                self._create_agent_success_rate_widget(),
                self._create_token_usage_widget(),
                self._create_latency_warnings_widget(),
                self._create_cost_warnings_widget(),
                self._create_agent_execution_time_widget(),
                self._create_error_count_widget()
            ]
        }
        
        try:
            self.cloudwatch.put_dashboard(
                DashboardName=self.dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            return {
                "status": "success",
                "dashboard_name": self.dashboard_name,
                "message": f"Dashboard created successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create dashboard: {str(e)}"
            }
            
    def _create_incident_volume_widget(self) -> dict:
        """Create widget for incident volume over time."""
        return {
            "type": "metric",
            "x": 0,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "IncidentProcessed", {"stat": "Sum", "label": "Incidents Processed"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Incident Volume Over Time",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Count"
                    }
                }
            }
        }
        
    def _create_resolution_time_widget(self) -> dict:
        """Create widget for average resolution time."""
        return {
            "type": "metric",
            "x": 12,
            "y": 0,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "ProcessingTime", {"stat": "Average", "label": "Avg Resolution Time"}],
                    ["...", {"stat": "Maximum", "label": "Max Resolution Time"}],
                    ["...", {"stat": "Minimum", "label": "Min Resolution Time"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Resolution Time",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Seconds"
                    }
                }
            }
        }
        
    def _create_confidence_score_widget(self) -> dict:
        """Create widget for confidence score distribution."""
        return {
            "type": "metric",
            "x": 0,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "ConfidenceScore", {"stat": "Average", "label": "Avg Confidence"}],
                    ["...", {"stat": "Maximum", "label": "Max Confidence"}],
                    ["...", {"stat": "Minimum", "label": "Min Confidence"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Confidence Score Distribution",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Score (0-100)",
                        "min": 0,
                        "max": 100
                    }
                }
            }
        }
        
    def _create_agent_success_rate_widget(self) -> dict:
        """Create widget for agent success rates."""
        return {
            "type": "metric",
            "x": 12,
            "y": 6,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "AgentSuccess", "Agent", "log-analysis", {"stat": "Sum", "label": "Log Analysis"}],
                    ["...", "root-cause", {"stat": "Sum", "label": "Root Cause"}],
                    ["...", "fix-recommendation", {"stat": "Sum", "label": "Fix Recommendation"}],
                    ["...", "communication", {"stat": "Sum", "label": "Communication"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Agent Success Rates",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Success Count"
                    }
                }
            }
        }
        
    def _create_token_usage_widget(self) -> dict:
        """Create widget for Bedrock token usage trends."""
        return {
            "type": "metric",
            "x": 0,
            "y": 12,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "BedrockInputTokens", {"stat": "Sum", "label": "Input Tokens"}],
                    [self.namespace, "BedrockOutputTokens", {"stat": "Sum", "label": "Output Tokens"}],
                    [self.namespace, "BedrockTotalTokens", {"stat": "Sum", "label": "Total Tokens"}]
                ],
                "view": "timeSeries",
                "stacked": True,
                "region": self.region,
                "title": "Bedrock Token Usage Trends",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Token Count"
                    }
                }
            }
        }
        
    def _create_latency_warnings_widget(self) -> dict:
        """Create widget for latency warnings."""
        return {
            "type": "metric",
            "x": 12,
            "y": 12,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "LatencyWarning", {"stat": "Sum", "label": "Latency Warnings"}]
                ],
                "view": "singleValue",
                "region": self.region,
                "title": "Latency Warnings (>60s)",
                "period": 300
            }
        }
        
    def _create_cost_warnings_widget(self) -> dict:
        """Create widget for cost warnings."""
        return {
            "type": "metric",
            "x": 18,
            "y": 12,
            "width": 6,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "CostWarning", "Service", "Bedrock", {"stat": "Sum", "label": "Bedrock"}],
                    ["...", "Lambda", {"stat": "Sum", "label": "Lambda"}],
                    ["...", "DynamoDB", {"stat": "Sum", "label": "DynamoDB"}],
                    ["...", "S3", {"stat": "Sum", "label": "S3"}]
                ],
                "view": "singleValue",
                "region": self.region,
                "title": "Cost Warnings (>80% Free Tier)",
                "period": 300
            }
        }
        
    def _create_agent_execution_time_widget(self) -> dict:
        """Create widget for agent execution times."""
        return {
            "type": "metric",
            "x": 0,
            "y": 18,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "AgentExecutionTime", "Agent", "log-analysis", {"stat": "Average", "label": "Log Analysis"}],
                    ["...", "root-cause", {"stat": "Average", "label": "Root Cause"}],
                    ["...", "fix-recommendation", {"stat": "Average", "label": "Fix Recommendation"}],
                    ["...", "communication", {"stat": "Average", "label": "Communication"}]
                ],
                "view": "timeSeries",
                "stacked": False,
                "region": self.region,
                "title": "Agent Execution Time (Average)",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Milliseconds"
                    }
                }
            }
        }
        
    def _create_error_count_widget(self) -> dict:
        """Create widget for error counts by agent."""
        return {
            "type": "metric",
            "x": 12,
            "y": 18,
            "width": 12,
            "height": 6,
            "properties": {
                "metrics": [
                    [self.namespace, "AgentError", "Agent", "log-analysis", {"stat": "Sum", "label": "Log Analysis"}],
                    ["...", "root-cause", {"stat": "Sum", "label": "Root Cause"}],
                    ["...", "fix-recommendation", {"stat": "Sum", "label": "Fix Recommendation"}],
                    ["...", "communication", {"stat": "Sum", "label": "Communication"}]
                ],
                "view": "timeSeries",
                "stacked": True,
                "region": self.region,
                "title": "Error Count by Agent",
                "period": 300,
                "yAxis": {
                    "left": {
                        "label": "Error Count"
                    }
                }
            }
        }
        
    def delete_dashboard(self):
        """Delete the CloudWatch dashboard."""
        try:
            self.cloudwatch.delete_dashboards(
                DashboardNames=[self.dashboard_name]
            )
            return {
                "status": "success",
                "message": f"Dashboard {self.dashboard_name} deleted successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete dashboard: {str(e)}"
            }
            
    def get_dashboard_url(self) -> str:
        """
        Get the URL to view the dashboard in AWS Console.
        
        Returns:
            Dashboard URL
        """
        return (
            f"https://console.aws.amazon.com/cloudwatch/home?"
            f"region={self.region}#dashboards:name={self.dashboard_name}"
        )
