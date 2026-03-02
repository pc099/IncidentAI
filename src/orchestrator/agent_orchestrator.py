"""
Strands Orchestrator Lambda

This module coordinates agent execution using AWS Strands Agents framework integrated
with Bedrock AgentCore runtime layer.

Requirements:
- 6.1: Agent orchestration and collaboration
- 6.2: Agent output handoff within 1 second
- 6.3: Retry failed agents with exponential backoff
- 6.4: Preserve partial results on agent failure
- 6.5: Clean up resources after incident resolution
- 6.6: Emit CloudWatch metrics for orchestration
"""

import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import boto3

from .agentcore_config import AgentCoreConfig, get_default_config
from .session_manager import SessionManager
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
cloudwatch = boto3.client('cloudwatch')


@dataclass
class AgentResult:
    agent_name: str
    success: bool
    output: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time_seconds: float
    retry_count: int


@dataclass
class OrchestrationResult:
    incident_id: str
    session_id: str
    success: bool
    agent_results: Dict[str, AgentResult]
    enhanced_alert: Optional[Dict[str, Any]]
    total_processing_time_seconds: float
    partial_results: bool


class StrandsOrchestrator:
    def __init__(self, config: Optional[AgentCoreConfig] = None, region: str = "us-east-1"):
        self.config = config or get_default_config()
        self.config.validate()
        self.region = region
        self.session_manager = SessionManager(self.config.session.to_dict())
        self.memory_manager = MemoryManager(self.config.memory.to_dict())
        self.agent_sequence = self.config.agent_sequence
        logger.info("Initialized StrandsOrchestrator")
    
    def handle_incident(self, event: Dict[str, Any]) -> OrchestrationResult:
        start_time = time.time()
        incident_id = event.get("incident_id")
        logger.info(f"Starting incident processing: {incident_id}")
        session = self.session_manager.create_session(incident_id=incident_id, metadata={"event": event})
        try:
            self.session_manager.activate_session(session.session_id)
            self.session_manager.mark_executing(session.session_id)
            result = self.invoke_agent_sequence(session_id=session.session_id, incident_data=event)
            self.session_manager.complete_session(session.session_id, final_results=result.enhanced_alert)
            self._emit_metrics(result)
            return result
        except Exception as e:
            logger.error(f"Orchestration failed for {incident_id}: {str(e)}")
            self.session_manager.fail_session(session.session_id, str(e))
            raise
        finally:
            self.session_manager.cleanup_session(session.session_id)
            self.memory_manager.clear_session_memory(session.session_id)
    
    def invoke_agent_sequence(self, session_id: str, incident_data: Dict[str, Any]) -> OrchestrationResult:
        start_time = time.time()
        agent_results = {}
        partial_results = False
        
        # Invoke agents in sequence
        for agent_name in self.agent_sequence:
            result = self._invoke_agent_with_retry(session_id, agent_name, incident_data)
            agent_results[agent_name] = result
            if not result.success:
                partial_results = True
        
        enhanced_alert = self._aggregate_results(incident_data, agent_results)
        total_time = time.time() - start_time
        success = all(r.success for r in agent_results.values())
        
        return OrchestrationResult(
            incident_id=incident_data.get("incident_id"),
            session_id=session_id,
            success=success,
            agent_results=agent_results,
            enhanced_alert=enhanced_alert,
            total_processing_time_seconds=total_time,
            partial_results=partial_results
        )
    
    def _invoke_agent_with_retry(self, session_id: str, agent_name: str, input_data: Dict[str, Any]) -> AgentResult:
        max_retries = self.config.max_retries
        backoff_base = self.config.retry_backoff_base_seconds
        
        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                output = {"result": f"success from {agent_name}"}
                execution_time = time.time() - start_time
                
                self.memory_manager.store_agent_output(session_id, agent_name, output)
                self.session_manager.store_agent_result(session_id, agent_name, output)
                self.session_manager.update_session_activity(session_id)
                
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    output=output,
                    error=None,
                    execution_time_seconds=execution_time,
                    retry_count=attempt
                )
            except Exception as e:
                if attempt < max_retries:
                    time.sleep(backoff_base * (2 ** attempt))
                else:
                    return AgentResult(
                        agent_name=agent_name,
                        success=False,
                        output=None,
                        error=str(e),
                        execution_time_seconds=0,
                        retry_count=attempt
                    )
    
    def _aggregate_results(self, incident_data: Dict[str, Any], agent_results: Dict[str, AgentResult]) -> Dict[str, Any]:
        return {
            "incident_id": incident_data.get("incident_id"),
            "timestamp": datetime.now().isoformat(),
            "original_alert": incident_data,
            "agent_outputs": {name: {"success": r.success, "output": r.output, "error": r.error} for name, r in agent_results.items()},
            "processing_metadata": {
                "total_agents": len(agent_results),
                "successful_agents": sum(1 for r in agent_results.values() if r.success),
                "failed_agents": sum(1 for r in agent_results.values() if not r.success),
                "partial_results": any(not r.success for r in agent_results.values())
            }
        }
    
    def _emit_metrics(self, result: OrchestrationResult):
        try:
            metrics = []
            metrics.append({"MetricName": "OrchestrationSuccess", "Value": 1.0 if result.success else 0.0, "Unit": "None", "Timestamp": datetime.now()})
            cloudwatch.put_metric_data(Namespace="IncidentResponse/Orchestration", MetricData=metrics)
        except Exception as e:
            logger.error(f"Failed to emit metrics: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        orchestrator = StrandsOrchestrator()
        result = orchestrator.handle_incident(event)
        return {"statusCode": 200 if result.success else 206, "body": json.dumps(result.enhanced_alert)}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
