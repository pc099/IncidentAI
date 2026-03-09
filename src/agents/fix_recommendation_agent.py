"""
Fix Recommendation Agent

Generates actionable remediation steps based on root cause analysis.
Provides category-specific fix templates and AWS-specific recommendations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import boto3
import logging

logger = logging.getLogger(__name__)


class FixRecommendationAgent:
    """
    Agent responsible for generating fix recommendations based on root cause analysis.
    
    Provides:
    - Category-specific fix templates (configuration, resource, dependency)
    - AWS-specific recommendations for common services
    - Immediate action steps with commands
    - Preventive measures and rollback plans
    """
    
    def __init__(self):
        """Initialize the Fix Recommendation Agent with fix templates."""
        self.fix_templates = self._initialize_fix_templates()
        self.aws_service_fixes = self._initialize_aws_service_fixes()
    
    def _initialize_fix_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize fix templates for each root cause category.
        
        Returns:
            Dictionary mapping categories to fix template configurations
        """
        return {
            "configuration_error": {
                "description": "Invalid configuration values or missing parameters",
                "template_steps": [
                    {
                        "action": "Identify misconfigured parameter",
                        "details": "Review configuration and identify the incorrect parameter",
                        "estimated_time": "2 minutes",
                        "risk_level": "low"
                    },
                    {
                        "action": "Update configuration with correct value",
                        "details": "Apply the correct configuration value",
                        "estimated_time": "3 minutes",
                        "risk_level": "medium"
                    },
                    {
                        "action": "Validate configuration change",
                        "details": "Verify the configuration is now correct",
                        "estimated_time": "2 minutes",
                        "risk_level": "low"
                    }
                ],
                "preventive_measures": [
                    {
                        "action": "Implement configuration validation",
                        "description": "Add validation checks before applying configuration changes",
                        "priority": "high"
                    },
                    {
                        "action": "Use configuration management tools",
                        "description": "Adopt tools like AWS Systems Manager Parameter Store for centralized config",
                        "priority": "medium"
                    }
                ]
            },
            "resource_exhaustion": {
                "description": "Memory, CPU, disk space, or other resource limits exceeded",
                "template_steps": [
                    {
                        "action": "Identify exhausted resource",
                        "details": "Determine which resource (memory, CPU, disk) is exhausted",
                        "estimated_time": "2 minutes",
                        "risk_level": "low"
                    },
                    {
                        "action": "Scale resource capacity",
                        "details": "Increase resource allocation (typically 2x current limit)",
                        "estimated_time": "5 minutes",
                        "risk_level": "medium"
                    },
                    {
                        "action": "Monitor resource usage",
                        "details": "Set up monitoring and alerts for resource thresholds",
                        "estimated_time": "3 minutes",
                        "risk_level": "low"
                    }
                ],
                "preventive_measures": [
                    {
                        "action": "Enable auto-scaling",
                        "description": "Configure automatic scaling based on resource utilization",
                        "priority": "high"
                    },
                    {
                        "action": "Set up proactive monitoring",
                        "description": "Create CloudWatch alarms for resource thresholds (80% utilization)",
                        "priority": "high"
                    },
                    {
                        "action": "Implement resource optimization",
                        "description": "Review and optimize resource usage patterns",
                        "priority": "medium"
                    }
                ]
            },
            "dependency_failure": {
                "description": "External service timeouts, database connection failures, or API errors",
                "template_steps": [
                    {
                        "action": "Verify dependency health",
                        "details": "Check if the external dependency is available and responding",
                        "estimated_time": "2 minutes",
                        "risk_level": "none"
                    },
                    {
                        "action": "Increase timeout and retry settings",
                        "details": "Adjust timeout thresholds and implement exponential backoff",
                        "estimated_time": "4 minutes",
                        "risk_level": "low"
                    },
                    {
                        "action": "Implement fallback mechanism",
                        "details": "Add circuit breaker or fallback logic for resilience",
                        "estimated_time": "10 minutes",
                        "risk_level": "medium"
                    }
                ],
                "preventive_measures": [
                    {
                        "action": "Implement circuit breaker pattern",
                        "description": "Add circuit breaker to prevent cascade failures",
                        "priority": "high"
                    },
                    {
                        "action": "Add dependency health monitoring",
                        "description": "Monitor external dependency availability proactively",
                        "priority": "high"
                    },
                    {
                        "action": "Implement retry with exponential backoff",
                        "description": "Add intelligent retry logic for transient failures",
                        "priority": "medium"
                    },
                    {
                        "action": "Add fallback/degraded mode",
                        "description": "Implement graceful degradation when dependencies fail",
                        "priority": "medium"
                    }
                ]
            }
        }
    
    def _initialize_aws_service_fixes(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize AWS-specific fix recommendations for common services.
        
        Returns:
            Dictionary mapping AWS services to their specific fix patterns
        """
        return {
            "lambda": {
                "deployment_failure": {
                    "patterns": ["deployment", "package size", "code storage"],
                    "fixes": [
                        {
                            "action": "Check deployment package size",
                            "command": "aws lambda get-function --function-name {service_name} --query 'Configuration.CodeSize'",
                            "details": "Lambda deployment package must be <50MB zipped, <250MB unzipped",
                            "estimated_time": "2 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Reduce package size by removing unused dependencies",
                            "command": "# Review requirements.txt or package.json and remove unused packages",
                            "details": "Use Lambda Layers for shared dependencies",
                            "estimated_time": "15 minutes",
                            "risk_level": "low"
                        }
                    ]
                },
                "iam_permissions": {
                    "patterns": ["access denied", "unauthorized", "permission"],
                    "fixes": [
                        {
                            "action": "Review Lambda execution role configuration",
                            "command": "aws lambda get-function --function-name {service_name} --query 'Configuration.Role'",
                            "details": "Verify IAM role configuration has necessary permissions configured",
                            "estimated_time": "3 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Update IAM policy configuration",
                            "command": "aws iam attach-role-policy --role-name {role_name} --policy-arn arn:aws:iam::aws:policy/{policy}",
                            "details": "Update configuration to grant least-privilege permissions for required actions",
                            "estimated_time": "5 minutes",
                            "risk_level": "medium"
                        }
                    ]
                },
                "timeout": {
                    "patterns": ["timeout", "task timed out"],
                    "fixes": [
                        {
                            "action": "Increase Lambda timeout",
                            "command": "aws lambda update-function-configuration --function-name {service_name} --timeout 30",
                            "details": "Current timeout may be insufficient for operation",
                            "estimated_time": "2 minutes",
                            "risk_level": "low"
                        },
                        {
                            "action": "Optimize function execution time",
                            "command": "# Review CloudWatch Logs for performance bottlenecks",
                            "details": "Consider code optimization or increasing memory allocation",
                            "estimated_time": "20 minutes",
                            "risk_level": "low"
                        }
                    ]
                },
                "concurrency": {
                    "patterns": ["concurrent execution", "throttling", "rate exceeded"],
                    "fixes": [
                        {
                            "action": "Check current concurrency limits",
                            "command": "aws lambda get-function-concurrency --function-name {service_name}",
                            "details": "Verify reserved and unreserved concurrency settings",
                            "estimated_time": "2 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Increase reserved concurrency",
                            "command": "aws lambda put-function-concurrency --function-name {service_name} --reserved-concurrent-executions 100",
                            "details": "Allocate dedicated concurrency for critical functions",
                            "estimated_time": "3 minutes",
                            "risk_level": "medium"
                        }
                    ]
                }
            },
            "dynamodb": {
                "throttling": {
                    "patterns": ["throttling", "provisionedthroughputexceeded", "capacity"],
                    "fixes": [
                        {
                            "action": "Check current read/write capacity",
                            "command": "aws dynamodb describe-table --table-name {table_name} --query 'Table.ProvisionedThroughput'",
                            "details": "Review current capacity units and usage patterns",
                            "estimated_time": "2 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Enable auto-scaling",
                            "command": "aws application-autoscaling register-scalable-target --service-namespace dynamodb --resource-id table/{table_name} --scalable-dimension dynamodb:table:ReadCapacityUnits --min-capacity 5 --max-capacity 100",
                            "details": "Auto-scaling adjusts capacity based on demand",
                            "estimated_time": "5 minutes",
                            "risk_level": "low"
                        },
                        {
                            "action": "Consider on-demand billing mode",
                            "command": "aws dynamodb update-table --table-name {table_name} --billing-mode PAY_PER_REQUEST",
                            "details": "On-demand mode eliminates throttling for unpredictable workloads",
                            "estimated_time": "3 minutes",
                            "risk_level": "medium"
                        },
                        {
                            "action": "Implement exponential backoff in application",
                            "command": "# Add retry logic with exponential backoff in application code",
                            "details": "AWS SDK includes built-in retry logic; ensure it's enabled",
                            "estimated_time": "10 minutes",
                            "risk_level": "low"
                        }
                    ]
                }
            },
            "rds": {
                "storage_full": {
                    "patterns": ["storage", "disk full", "space"],
                    "fixes": [
                        {
                            "action": "Check current storage usage",
                            "command": "aws rds describe-db-instances --db-instance-identifier {db_instance} --query 'DBInstances[0].[AllocatedStorage,DBInstanceStatus]'",
                            "details": "Review allocated vs. used storage",
                            "estimated_time": "2 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Increase allocated storage",
                            "command": "aws rds modify-db-instance --db-instance-identifier {db_instance} --allocated-storage 100 --apply-immediately",
                            "details": "Increase storage allocation (typically 2x current)",
                            "estimated_time": "10 minutes",
                            "risk_level": "medium"
                        },
                        {
                            "action": "Enable storage auto-scaling",
                            "command": "aws rds modify-db-instance --db-instance-identifier {db_instance} --max-allocated-storage 200",
                            "details": "Auto-scaling prevents future storage issues",
                            "estimated_time": "3 minutes",
                            "risk_level": "low"
                        },
                        {
                            "action": "Implement data archival strategy",
                            "command": "# Archive or delete old data to free up space",
                            "details": "Move historical data to S3 or delete unnecessary records",
                            "estimated_time": "30 minutes",
                            "risk_level": "high"
                        }
                    ]
                }
            },
            "apigateway": {
                "timeout": {
                    "patterns": ["timeout", "integration timeout", "endpoint request timed out"],
                    "fixes": [
                        {
                            "action": "Check API Gateway timeout configuration",
                            "command": "aws apigateway get-integration --rest-api-id {api_id} --resource-id {resource_id} --http-method {method}",
                            "details": "API Gateway has a maximum timeout of 29 seconds",
                            "estimated_time": "2 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Increase integration timeout",
                            "command": "aws apigateway update-integration --rest-api-id {api_id} --resource-id {resource_id} --http-method {method} --patch-operations op=replace,path=/timeoutInMillis,value=29000",
                            "details": "Set to maximum 29 seconds if not already configured",
                            "estimated_time": "3 minutes",
                            "risk_level": "low"
                        },
                        {
                            "action": "Implement async processing pattern",
                            "command": "# Use SQS or Step Functions for long-running operations",
                            "details": "Return 202 Accepted immediately and process asynchronously",
                            "estimated_time": "30 minutes",
                            "risk_level": "medium"
                        },
                        {
                            "action": "Add circuit breaker pattern",
                            "command": "# Implement circuit breaker in backend service",
                            "details": "Prevent cascading failures from slow dependencies",
                            "estimated_time": "20 minutes",
                            "risk_level": "medium"
                        }
                    ]
                }
            },
            "stepfunctions": {
                "execution_failure": {
                    "patterns": ["state machine", "execution failed", "states."],
                    "fixes": [
                        {
                            "action": "Review execution history",
                            "command": "aws stepfunctions describe-execution --execution-arn {execution_arn}",
                            "details": "Identify which state failed and why",
                            "estimated_time": "3 minutes",
                            "risk_level": "none"
                        },
                        {
                            "action": "Configure retry policy for failed state",
                            "command": "# Update state machine definition with Retry configuration",
                            "details": "Add exponential backoff retry for transient errors",
                            "estimated_time": "10 minutes",
                            "risk_level": "low"
                        },
                        {
                            "action": "Add error handling with Catch",
                            "command": "# Update state machine definition with Catch configuration",
                            "details": "Define fallback states for error scenarios",
                            "estimated_time": "15 minutes",
                            "risk_level": "medium"
                        }
                    ]
                }
            }
        }
    
    def generate_recommendations(
        self,
        root_cause: Dict[str, Any],
        service_name: str,
        log_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate fix recommendations based on root cause analysis.
        
        Args:
            root_cause: Root cause analysis output containing category, description, confidence
            service_name: Name of the affected service
            log_summary: Optional log analysis summary for additional context
            
        Returns:
            Dictionary containing immediate actions, preventive measures, and rollback plan
        """
        # Handle both direct and nested structures
        if "analysis" in root_cause:
            primary_cause = root_cause.get("analysis", {}).get("primary_cause", {})
        else:
            primary_cause = root_cause.get("primary_cause", {})
        
        category = primary_cause.get("category", "unknown")
        description = primary_cause.get("description", "")
        evidence = primary_cause.get("evidence", [])
        
        # Check for AWS-specific fixes first
        aws_result = self._get_aws_specific_fixes(description, evidence, service_name, category)
        
        if aws_result:
            # Use AWS-specific recommendations with AWS-specific preventive measures
            immediate_actions = aws_result["actions"]
            preventive_measures = aws_result.get("preventive_measures", [])
            # Add category-specific preventive measures if not already included
            template = self.fix_templates.get(category, self._get_default_template())
            for measure in template.get("preventive_measures", []):
                if measure not in preventive_measures:
                    preventive_measures.append(measure)
        else:
            # Fall back to generic template
            template = self.fix_templates.get(category, self._get_default_template())
            immediate_actions = self._generate_immediate_actions(
                template, category, description, service_name, log_summary
            )
            preventive_measures = template.get("preventive_measures", [])
        
        # Generate rollback plan
        rollback_plan = self._generate_rollback_plan(immediate_actions, category)
        
        return {
            "agent": "fix-recommendation",
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": {
                "immediate_actions": immediate_actions,
                "preventive_measures": preventive_measures,
                "rollback_plan": rollback_plan
            }
        }
    
    def _get_aws_specific_fixes(
        self,
        description: str,
        evidence: List[str],
        service_name: str,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get AWS-specific fix recommendations if applicable.
        
        Args:
            description: Root cause description
            evidence: List of evidence items
            service_name: Affected service name
            category: Root cause category
            
        Returns:
            Dictionary with actions and preventive_measures or None if not applicable
        """
        description_lower = description.lower()
        evidence_text = " ".join(evidence).lower() if evidence else ""
        combined_text = f"{description_lower} {evidence_text}"
        
        # Check for service-specific keywords first to determine which service
        service_matches = []
        if any(keyword in combined_text for keyword in ["dynamodb", "table", "provisionedthroughput"]):
            service_matches.append("dynamodb")
        if any(keyword in combined_text for keyword in ["rds", "database", "db instance", "allocated storage"]):
            service_matches.append("rds")
        if any(keyword in combined_text for keyword in ["api gateway", "apigateway", "integration timeout", "endpoint request"]):
            service_matches.append("apigateway")
        if any(keyword in combined_text for keyword in ["lambda", "function"]) and "apigateway" not in service_matches:
            service_matches.append("lambda")
        
        # For dependency failures without specific AWS service mentions, use template-based fixes
        if category == "dependency_failure" and not service_matches:
            # Check if it's a generic dependency failure (external API, etc.)
            generic_dependency_patterns = ["external api", "external service", "third-party"]
            if any(pattern in description_lower for pattern in generic_dependency_patterns):
                return None
        
        # If we identified specific services, check only those
        services_to_check = service_matches if service_matches else self.aws_service_fixes.keys()
        
        # Check each AWS service for pattern matches
        for service in services_to_check:
            if service not in self.aws_service_fixes:
                continue
                
            scenarios = self.aws_service_fixes[service]
            for scenario_name, scenario_data in scenarios.items():
                patterns = scenario_data.get("patterns", [])
                
                # Check if any pattern matches
                if any(pattern.lower() in combined_text for pattern in patterns):
                    # Verify category alignment before returning AWS-specific fixes
                    if not self._is_category_aligned(scenario_name, category):
                        continue
                    
                    # Found a match - return the fixes with service_name substituted
                    fixes = scenario_data.get("fixes", [])
                    actions = self._customize_aws_fixes(fixes, service_name)
                    
                    # Get AWS-specific preventive measures based on scenario
                    preventive_measures = self._get_aws_preventive_measures(service, scenario_name, category)
                    
                    return {
                        "actions": actions,
                        "preventive_measures": preventive_measures
                    }
        
        return None
    
    def _is_category_aligned(self, scenario_name: str, category: str) -> bool:
        """
        Check if a scenario aligns with the root cause category.
        
        Args:
            scenario_name: AWS scenario name (e.g., "throttling", "storage_full", "timeout")
            category: Root cause category (configuration_error, resource_exhaustion, dependency_failure)
            
        Returns:
            True if the scenario aligns with the category
        """
        # Map scenarios to their appropriate categories
        resource_exhaustion_scenarios = ["throttling", "storage_full", "concurrency", "timeout"]
        configuration_scenarios = ["iam_permissions", "deployment_failure"]
        dependency_scenarios = ["timeout"]  # timeout can be both resource exhaustion and dependency failure
        
        if category == "resource_exhaustion":
            return scenario_name in resource_exhaustion_scenarios
        elif category == "configuration_error":
            return scenario_name in configuration_scenarios
        elif category == "dependency_failure":
            return scenario_name in dependency_scenarios
        
        # If no specific alignment, allow it (for flexibility)
        return True
    
    def _get_aws_preventive_measures(
        self,
        service: str,
        scenario: str,
        category: str
    ) -> List[Dict[str, str]]:
        """
        Get AWS-specific preventive measures for a scenario.
        
        Args:
            service: AWS service name (lambda, dynamodb, rds, apigateway)
            scenario: Specific scenario (throttling, storage_full, etc.)
            category: Root cause category
            
        Returns:
            List of preventive measure dictionaries
        """
        measures = []
        
        if service == "dynamodb" and scenario == "throttling":
            measures.extend([
                {
                    "action": "Enable DynamoDB auto-scaling",
                    "description": "Configure auto-scaling to handle traffic spikes automatically",
                    "priority": "high"
                },
                {
                    "action": "Consider on-demand billing mode",
                    "description": "Switch to on-demand mode for unpredictable workloads",
                    "priority": "medium"
                },
                {
                    "action": "Implement exponential backoff",
                    "description": "Add retry logic with exponential backoff in application code",
                    "priority": "high"
                }
            ])
        elif service == "rds" and scenario == "storage_full":
            measures.extend([
                {
                    "action": "Enable RDS storage auto-scaling",
                    "description": "Configure automatic storage scaling to prevent future issues",
                    "priority": "high"
                },
                {
                    "action": "Implement data archival strategy",
                    "description": "Archive old data to S3 or implement data retention policies",
                    "priority": "medium"
                },
                {
                    "action": "Set up storage monitoring",
                    "description": "Create CloudWatch alarms for storage utilization (80% threshold)",
                    "priority": "high"
                }
            ])
        elif service == "apigateway" and scenario == "timeout":
            measures.extend([
                {
                    "action": "Implement async processing pattern",
                    "description": "Use SQS or Step Functions for long-running operations",
                    "priority": "high"
                },
                {
                    "action": "Add circuit breaker pattern",
                    "description": "Implement circuit breaker to prevent cascading failures",
                    "priority": "high"
                },
                {
                    "action": "Optimize backend performance",
                    "description": "Review and optimize backend service response times",
                    "priority": "medium"
                }
            ])
        
        return measures
    
    def _customize_aws_fixes(
        self,
        fixes: List[Dict[str, Any]],
        service_name: str
    ) -> List[Dict[str, Any]]:
        """
        Customize AWS fix commands with actual service name.
        
        Args:
            fixes: List of fix templates
            service_name: Actual service name to substitute
            
        Returns:
            List of customized fix actions with step numbers
        """
        customized = []
        for idx, fix in enumerate(fixes, start=1):
            customized_fix = {
                "step": idx,
                "action": fix["action"],
                "details": fix["details"],
                "estimated_time": fix["estimated_time"],
                "risk_level": fix["risk_level"]
            }
            
            # Substitute service name in command if present
            if "command" in fix:
                command = fix["command"].replace("{service_name}", service_name)
                command = command.replace("{table_name}", service_name)
                command = command.replace("{db_instance}", service_name)
                customized_fix["command"] = command
            
            customized.append(customized_fix)
        
        return customized
    
    def _generate_immediate_actions(
        self,
        template: Dict[str, Any],
        category: str,
        description: str,
        service_name: str,
        log_summary: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate immediate action steps from template.
        
        Args:
            template: Fix template for the category
            category: Root cause category
            description: Root cause description
            service_name: Affected service name
            log_summary: Optional log analysis summary
            
        Returns:
            List of immediate action steps with commands
        """
        actions = []
        template_steps = template.get("template_steps", [])
        
        for idx, step in enumerate(template_steps, start=1):
            action = {
                "step": idx,
                "action": step["action"],
                "details": step["details"],
                "estimated_time": step["estimated_time"],
                "risk_level": step["risk_level"]
            }
            
            # Add command if applicable
            command = self._generate_command(category, step["action"], service_name, description)
            if command:
                action["command"] = command
            
            actions.append(action)
        
        return actions
    
    def _generate_command(
        self,
        category: str,
        action: str,
        service_name: str,
        description: str
    ) -> Optional[str]:
        """
        Generate specific command for an action.
        
        Args:
            category: Root cause category
            action: Action description
            service_name: Affected service name
            description: Root cause description
            
        Returns:
            Command string or None if no command applicable
        """
        action_lower = action.lower()
        description_lower = description.lower()
        
        # Configuration error commands
        if category == "configuration_error":
            if "update configuration" in action_lower or "modify" in action_lower:
                # Check for specific configuration types
                if "iam" in description_lower or "permission" in description_lower:
                    return f"aws iam attach-role-policy --role-name {service_name}-role --policy-arn arn:aws:iam::aws:policy/SERVICE_POLICY"
                elif "environment" in description_lower or "variable" in description_lower:
                    return f"aws lambda update-function-configuration --function-name {service_name} --environment Variables={{CONFIG_KEY=CORRECT_VALUE}}"
                else:
                    return f"aws lambda update-function-configuration --function-name {service_name} --environment Variables={{KEY=VALUE}}"
            elif "validate" in action_lower or "review" in action_lower:
                return f"aws lambda get-function-configuration --function-name {service_name}"
            elif "parameter" in action_lower:
                return f"aws ssm get-parameter --name /{service_name}/config/parameter"
        
        # Resource exhaustion commands
        elif category == "resource_exhaustion":
            if "scale resource" in action_lower or "increase" in action_lower:
                if "memory" in description_lower:
                    return f"aws lambda update-function-configuration --function-name {service_name} --memory-size 512"
                elif "timeout" in description_lower:
                    return f"aws lambda update-function-configuration --function-name {service_name} --timeout 30"
                elif "disk" in description_lower or "storage" in description_lower:
                    return f"aws rds modify-db-instance --db-instance-identifier {service_name} --allocated-storage 100"
                elif "capacity" in description_lower or "throughput" in description_lower:
                    return f"aws dynamodb update-table --table-name {service_name} --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10"
            elif "monitor" in action_lower:
                return f"aws cloudwatch put-metric-alarm --alarm-name {service_name}-resource-alarm --metric-name ResourceUtilization"
        
        # Dependency failure commands
        elif category == "dependency_failure":
            if "verify" in action_lower and "health" in action_lower:
                return "curl -I https://dependency-endpoint/health"
            elif "timeout" in action_lower or "increase timeout" in action_lower:
                return f"aws lambda update-function-configuration --function-name {service_name} --timeout 30"
            elif "retry" in action_lower or "backoff" in action_lower:
                return "# Implement exponential backoff in application code using AWS SDK retry configuration"
            elif "circuit breaker" in action_lower or "fallback" in action_lower:
                return "# Add circuit breaker pattern using libraries like resilience4j or implement custom logic"
        
        return None
    
    def _generate_rollback_plan(
        self,
        immediate_actions: List[Dict[str, Any]],
        category: str
    ) -> str:
        """
        Generate rollback plan for the recommended changes.
        
        Args:
            immediate_actions: List of immediate actions
            category: Root cause category
            
        Returns:
            Rollback plan description
        """
        if category == "configuration_error":
            return "Revert configuration to previous known-good state using AWS Systems Manager or version control"
        elif category == "resource_exhaustion":
            return "Reduce resource allocation to previous values if issues persist or costs become prohibitive"
        elif category == "dependency_failure":
            return "Revert timeout/retry changes if they cause other issues; disable circuit breaker if needed"
        else:
            return "Document current state before changes; revert changes if service stability worsens"
    
    def _get_default_template(self) -> Dict[str, Any]:
        """
        Get default template for unknown categories.
        
        Returns:
            Default fix template
        """
        return {
            "description": "Unknown failure category",
            "template_steps": [
                {
                    "action": "Review error logs and metrics",
                    "details": "Manually investigate the failure using available logs and metrics",
                    "estimated_time": "10 minutes",
                    "risk_level": "none"
                },
                {
                    "action": "Consult documentation and runbooks",
                    "details": "Check service documentation for troubleshooting guidance",
                    "estimated_time": "15 minutes",
                    "risk_level": "none"
                }
            ],
            "preventive_measures": [
                {
                    "action": "Improve monitoring and alerting",
                    "description": "Add comprehensive monitoring to catch similar issues earlier",
                    "priority": "high"
                }
            ]
        }



class BedrockFixRecommendationGenerator:
    """
    Bedrock Claude integration for AI-powered fix recommendation generation.
    
    This class provides:
    - Bedrock prompt template creation for fix recommendations
    - Claude model invocation with root cause and historical context
    - Structured JSON response parsing with immediate actions, preventive measures, rollback plan
    
    Requirements: 4.1, 4.2, 4.6, 4.7
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        """
        Initialize Bedrock fix recommendation generator.
        
        Args:
            bedrock_model_id: Bedrock model ID to use for fix generation
        """
        # Lazy initialization to avoid import-time credential requirements
        self.bedrock_runtime = None
        self.model_id = bedrock_model_id
    
    def get_bedrock_client(self):
        """Get Bedrock client with lazy initialization"""
        if self.bedrock_runtime is None:
            self.bedrock_runtime = boto3.client('bedrock-runtime')
        return self.bedrock_runtime
    
    def create_prompt(
        self,
        root_cause: Dict[str, Any],
        service_name: str,
        similar_fixes: Optional[List[Dict]] = None
    ) -> str:
        """
        Create Bedrock prompt template for fix recommendations.
        
        Args:
            root_cause: Root cause analysis output
            service_name: Name of the affected service
            similar_fixes: Optional list of previously successful fixes from incident history
            
        Returns:
            Formatted prompt for Claude model
        """
        primary_cause = root_cause.get("primary_cause", {})
        category = primary_cause.get("category", "unknown")
        description = primary_cause.get("description", "")
        confidence = primary_cause.get("confidence_score", 0)
        evidence = primary_cause.get("evidence", [])
        
        # Format evidence
        evidence_text = "\n".join([f"  - {item}" for item in evidence]) if evidence else "  None provided"
        
        # Format similar fixes from incident history
        similar_fixes_text = ""
        if similar_fixes:
            similar_fixes_text = "\n\nPreviously Successful Fixes:\n"
            similar_fixes_text += "These fixes were successful in similar past incidents:\n\n"
            
            for idx, fix in enumerate(similar_fixes[:3], 1):  # Top 3
                incident_id = fix.get("incident_id", "unknown")
                fix_action = fix.get("fix_action", "")
                resolution_time = fix.get("resolution_time_seconds", 0)
                
                similar_fixes_text += f"{idx}. Incident {incident_id}\n"
                similar_fixes_text += f"   Fix Applied: {fix_action}\n"
                similar_fixes_text += f"   Resolution Time: {resolution_time // 60} minutes\n\n"
        
        # Create the prompt
        prompt = f"""You are a fix recommendation expert. Generate actionable remediation steps for this incident:

Service: {service_name}
Root Cause Category: {category}
Root Cause Description: {description}
Confidence Score: {confidence}%

Evidence:
{evidence_text}
{similar_fixes_text}
Generate fix recommendations in the following JSON format:
{{
  "immediate_actions": [
    {{
      "step": 1,
      "action": "Brief action description",
      "command": "Specific command to execute (if applicable)",
      "details": "Detailed explanation of what this action does",
      "estimated_time": "X minutes",
      "risk_level": "none|low|medium|high"
    }}
  ],
  "preventive_measures": [
    {{
      "action": "Preventive action description",
      "description": "How this prevents future incidents",
      "priority": "high|medium|low"
    }}
  ],
  "rollback_plan": "Description of how to revert changes if needed"
}}

Requirements:
- Provide 2-5 immediate action steps (MUST be between 2 and 5)
- Each action must include estimated time to resolution
- Include specific commands where applicable (AWS CLI, curl, etc.)
- Risk levels: none (read-only), low (safe changes), medium (requires testing), high (potential impact)
- Prioritize preventive measures (high/medium/low)
- Provide clear rollback instructions

Category-Specific Guidelines:
- configuration_error: Identify parameter, provide correct value, show update command
- resource_exhaustion: Identify resource, calculate scaling (typically 2x), provide scaling commands
- dependency_failure: Verify health, increase timeout/retry, implement fallback

AWS Service-Specific Considerations:
- Lambda: deployment package size, IAM permissions, timeout, concurrency
- DynamoDB: throttling, auto-scaling, on-demand billing, exponential backoff
- RDS: storage full, auto-scaling, archival strategies
- API Gateway: timeout configuration, async processing, circuit breaker
- Step Functions: retry configuration, error handling

If similar fixes exist, incorporate their successful approaches into your recommendations."""

        return prompt
    
    def invoke_claude(
        self,
        root_cause: Dict[str, Any],
        service_name: str,
        similar_fixes: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Invoke Claude model to generate fix recommendations.
        
        Args:
            root_cause: Root cause analysis output
            service_name: Name of the affected service
            similar_fixes: Optional list of previously successful fixes
            
        Returns:
            Dictionary containing immediate actions, preventive measures, and rollback plan
            
        Raises:
            Exception: If Bedrock invocation fails
        """
        try:
            # Create prompt
            prompt = self.create_prompt(
                root_cause=root_cause,
                service_name=service_name,
                similar_fixes=similar_fixes
            )
            
            logger.info(f"Invoking Bedrock Claude for fix recommendations for {service_name}")
            
            # Prepare request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 3000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,  # Lower temperature for more consistent recommendations
                "top_p": 0.9
            }
            
            # Invoke Bedrock
            bedrock_runtime = self.get_bedrock_client()
            response = bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract content from Claude response
            content = response_body.get('content', [])
            if not content:
                raise ValueError("Empty response from Bedrock Claude")
            
            # Get the text content
            text_content = content[0].get('text', '')
            
            # Parse JSON from response
            # Claude might wrap JSON in markdown code blocks
            if '```json' in text_content:
                json_start = text_content.find('```json') + 7
                json_end = text_content.find('```', json_start)
                text_content = text_content[json_start:json_end].strip()
            elif '```' in text_content:
                json_start = text_content.find('```') + 3
                json_end = text_content.find('```', json_start)
                text_content = text_content[json_start:json_end].strip()
            
            recommendations = json.loads(text_content)
            
            # Validate and normalize response
            validated_recommendations = self._validate_and_normalize_response(recommendations)
            
            logger.info(f"Successfully generated {len(validated_recommendations['immediate_actions'])} fix recommendations")
            
            return validated_recommendations
            
        except Exception as e:
            logger.error(f"Error invoking Bedrock for fix recommendations: {str(e)}")
            raise
    
    def _validate_and_normalize_response(self, response: Dict) -> Dict:
        """
        Validate and normalize Bedrock response.
        
        Args:
            response: Raw response from Bedrock
            
        Returns:
            Validated and normalized response
            
        Raises:
            ValueError: If response is invalid
        """
        # Ensure immediate_actions exists and has 2-5 items
        immediate_actions = response.get("immediate_actions", [])
        if not immediate_actions:
            raise ValueError("Response must include immediate_actions")
        
        if len(immediate_actions) < 2:
            raise ValueError(f"Must have at least 2 immediate actions, got {len(immediate_actions)}")
        
        if len(immediate_actions) > 5:
            # Truncate to 5 if more provided
            immediate_actions = immediate_actions[:5]
        
        # Ensure each action has required fields
        for idx, action in enumerate(immediate_actions, start=1):
            if "action" not in action:
                raise ValueError(f"Action {idx} missing 'action' field")
            if "estimated_time" not in action:
                raise ValueError(f"Action {idx} missing 'estimated_time' field")
            
            # Ensure step number is set
            action["step"] = idx
            
            # Set defaults for optional fields
            action.setdefault("details", action["action"])
            action.setdefault("risk_level", "low")
            action.setdefault("command", None)
        
        # Ensure preventive_measures exists
        preventive_measures = response.get("preventive_measures", [])
        for measure in preventive_measures:
            measure.setdefault("priority", "medium")
        
        # Ensure rollback_plan exists
        rollback_plan = response.get("rollback_plan", "Document current state before changes; revert if issues occur")
        
        return {
            "immediate_actions": immediate_actions,
            "preventive_measures": preventive_measures,
            "rollback_plan": rollback_plan
        }
    
    def generate_with_bedrock(
        self,
        root_cause: Dict[str, Any],
        service_name: str,
        incident_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate fix recommendations using Bedrock Claude with incident history context.
        
        Args:
            root_cause: Root cause analysis output
            service_name: Name of the affected service
            incident_history: Optional list of similar past incidents with their fixes
            
        Returns:
            Complete fix recommendation response
        """
        # Extract similar fixes from incident history
        similar_fixes = []
        if incident_history:
            for incident in incident_history:
                if incident.get("fix_applied"):
                    similar_fixes.append({
                        "incident_id": incident.get("incident_id", "unknown"),
                        "fix_action": incident["fix_applied"].get("action", ""),
                        "resolution_time_seconds": incident.get("resolution_time_seconds", 0)
                    })
        
        # Invoke Claude
        recommendations = self.invoke_claude(
            root_cause=root_cause,
            service_name=service_name,
            similar_fixes=similar_fixes if similar_fixes else None
        )
        
        return {
            "agent": "fix-recommendation",
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": recommendations
        }
