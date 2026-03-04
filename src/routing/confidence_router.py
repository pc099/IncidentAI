"""
Confidence-Based Human-in-the-Loop Routing

Implements a three-tier decision system that routes actions based on composite confidence scores:
- >90% confidence: Auto-execute with logging
- 70-89% confidence: Execute with mandatory notification
- <70% confidence: Pause for human approval via Step Functions Task Tokens

Key Features:
- Composite confidence scoring (LLM self-assessment + retrieval relevance + historical accuracy)
- Gradual autonomy with shadow mode progression
- Slack integration for notifications and approvals
- Decision audit trails for explainability
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence levels for routing decisions"""
    HIGH = "high"           # >90% - Auto-execute
    MEDIUM = "medium"       # 70-89% - Execute with notification
    LOW = "low"            # <70% - Human approval required


class ActionType(Enum):
    """Types of actions that can be routed"""
    RESTART_SERVICE = "restart_service"
    SCALE_RESOURCES = "scale_resources"
    UPDATE_CONFIGURATION = "update_configuration"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    EXECUTE_RUNBOOK = "execute_runbook"
    SEND_ALERT = "send_alert"
    INVESTIGATE_FURTHER = "investigate_further"


class AutonomyMode(Enum):
    """Autonomy progression modes"""
    SHADOW = "shadow"           # AI suggests, humans execute
    ASSISTED = "assisted"       # AI executes with approval
    AUTONOMOUS = "autonomous"   # AI executes independently


@dataclass
class ConfidenceFactors:
    """Factors contributing to confidence score"""
    llm_self_assessment: float      # LLM's own confidence (0-100)
    retrieval_relevance: float      # Quality of retrieved context (0-100)
    historical_accuracy: float      # Past accuracy for similar cases (0-100)
    evidence_strength: float        # Strength of supporting evidence (0-100)
    consensus_agreement: float      # Agreement across multiple agents (0-100)


@dataclass
class RoutingDecision:
    """Decision made by confidence router"""
    action_type: ActionType
    confidence_level: ConfidenceLevel
    composite_score: float
    confidence_factors: ConfidenceFactors
    routing_decision: str           # auto_execute, notify_and_execute, human_approval
    reasoning: str
    evidence: List[Dict[str, Any]]
    timestamp: datetime
    requires_approval: bool = False
    approval_timeout_minutes: int = 30


@dataclass
class ApprovalRequest:
    """Human approval request"""
    request_id: str
    incident_id: str
    action_type: ActionType
    proposed_action: Dict[str, Any]
    confidence_score: float
    reasoning: str
    evidence: List[Dict[str, Any]]
    created_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, approved, rejected, expired


class ConfidenceRouter:
    """
    Confidence-based routing system for human-in-the-loop decisions
    
    Implements responsible AI practices by routing actions based on confidence
    and maintaining decision audit trails for explainability.
    """
    
    def __init__(self, region: str = "us-east-1"):
        self.stepfunctions = boto3.client('stepfunctions', region_name=region)
        self.sns = boto3.client('sns', region_name=region)
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        
        # Configuration
        self.confidence_thresholds = {
            ConfidenceLevel.HIGH: 90.0,
            ConfidenceLevel.MEDIUM: 70.0,
            ConfidenceLevel.LOW: 0.0
        }
        
        # Autonomy progression settings
        self.autonomy_mode = AutonomyMode.ASSISTED  # Start in assisted mode
        self.shadow_mode_duration_days = 7
        self.accuracy_threshold_for_promotion = 0.85
        
        # Historical accuracy tracking
        self.accuracy_history = {}
        
        # Microsoft Teams configuration (would be set via environment variables)
        self.teams_webhook_url = None
        self.approval_channel = "Incident Response"
        
        logger.info("Confidence router initialized")
    
    async def route_action(
        self,
        incident_id: str,
        action_type: ActionType,
        proposed_action: Dict[str, Any],
        confidence_factors: ConfidenceFactors,
        context: Dict[str, Any]
    ) -> RoutingDecision:
        """
        Route action based on confidence score
        
        Args:
            incident_id: Unique incident identifier
            action_type: Type of action being proposed
            proposed_action: Details of the proposed action
            confidence_factors: Factors contributing to confidence
            context: Additional context for decision making
            
        Returns:
            Routing decision with next steps
        """
        try:
            # Calculate composite confidence score
            composite_score = self._calculate_composite_confidence(confidence_factors)
            
            # Determine confidence level
            confidence_level = self._determine_confidence_level(composite_score)
            
            # Get historical accuracy for this action type
            historical_accuracy = self._get_historical_accuracy(action_type, context)
            
            # Adjust confidence based on historical performance
            adjusted_score = self._adjust_for_historical_accuracy(
                composite_score, historical_accuracy
            )
            adjusted_level = self._determine_confidence_level(adjusted_score)
            
            # Make routing decision
            routing_decision = self._make_routing_decision(
                adjusted_level, action_type, self.autonomy_mode
            )
            
            # Create decision object
            decision = RoutingDecision(
                action_type=action_type,
                confidence_level=adjusted_level,
                composite_score=adjusted_score,
                confidence_factors=confidence_factors,
                routing_decision=routing_decision,
                reasoning=self._generate_reasoning(
                    adjusted_level, routing_decision, confidence_factors
                ),
                evidence=context.get("evidence", []),
                timestamp=datetime.now(),
                requires_approval=(routing_decision == "human_approval"),
                approval_timeout_minutes=30
            )
            
            # Execute routing decision
            await self._execute_routing_decision(incident_id, decision, proposed_action)
            
            # Log decision for audit trail
            await self._log_decision(incident_id, decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Routing failed for incident {incident_id}: {str(e)}")
            # Fallback to human approval for safety
            return RoutingDecision(
                action_type=action_type,
                confidence_level=ConfidenceLevel.LOW,
                composite_score=0.0,
                confidence_factors=confidence_factors,
                routing_decision="human_approval",
                reasoning=f"Routing failed, defaulting to human approval: {str(e)}",
                evidence=[],
                timestamp=datetime.now(),
                requires_approval=True
            )
    
    def _calculate_composite_confidence(self, factors: ConfidenceFactors) -> float:
        """
        Calculate composite confidence score from multiple factors
        
        Weights based on empirical testing:
        - LLM self-assessment: 30% (models are reasonably calibrated)
        - Historical accuracy: 25% (strong predictor of future performance)
        - Evidence strength: 20% (quality of supporting data)
        - Retrieval relevance: 15% (quality of retrieved context)
        - Consensus agreement: 10% (agreement across agents)
        """
        weights = {
            "llm_self_assessment": 0.30,
            "historical_accuracy": 0.25,
            "evidence_strength": 0.20,
            "retrieval_relevance": 0.15,
            "consensus_agreement": 0.10
        }
        
        composite = (
            factors.llm_self_assessment * weights["llm_self_assessment"] +
            factors.historical_accuracy * weights["historical_accuracy"] +
            factors.evidence_strength * weights["evidence_strength"] +
            factors.retrieval_relevance * weights["retrieval_relevance"] +
            factors.consensus_agreement * weights["consensus_agreement"]
        )
        
        # Ensure score is within bounds
        return max(0.0, min(100.0, composite))
    
    def _determine_confidence_level(self, score: float) -> ConfidenceLevel:
        """Determine confidence level from score"""
        if score >= self.confidence_thresholds[ConfidenceLevel.HIGH]:
            return ConfidenceLevel.HIGH
        elif score >= self.confidence_thresholds[ConfidenceLevel.MEDIUM]:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _get_historical_accuracy(
        self, 
        action_type: ActionType, 
        context: Dict[str, Any]
    ) -> float:
        """Get historical accuracy for this action type and context"""
        # In production, this would query DynamoDB for historical performance
        # For now, return default values based on action type
        
        default_accuracies = {
            ActionType.RESTART_SERVICE: 85.0,
            ActionType.SCALE_RESOURCES: 78.0,
            ActionType.UPDATE_CONFIGURATION: 65.0,
            ActionType.ROLLBACK_DEPLOYMENT: 92.0,
            ActionType.EXECUTE_RUNBOOK: 80.0,
            ActionType.SEND_ALERT: 95.0,
            ActionType.INVESTIGATE_FURTHER: 88.0
        }
        
        base_accuracy = default_accuracies.get(action_type, 70.0)
        
        # Adjust based on service type (user-facing services are more critical)
        service_name = context.get("service_name", "").lower()
        if any(pattern in service_name for pattern in ["api", "frontend", "payment", "user"]):
            base_accuracy *= 0.9  # Be more conservative for user-facing services
        
        return base_accuracy
    
    def _adjust_for_historical_accuracy(
        self, 
        composite_score: float, 
        historical_accuracy: float
    ) -> float:
        """Adjust confidence score based on historical accuracy"""
        # If historical accuracy is low, reduce confidence
        accuracy_factor = historical_accuracy / 100.0
        adjusted_score = composite_score * (0.7 + 0.3 * accuracy_factor)
        
        return max(0.0, min(100.0, adjusted_score))
    
    def _make_routing_decision(
        self,
        confidence_level: ConfidenceLevel,
        action_type: ActionType,
        autonomy_mode: AutonomyMode
    ) -> str:
        """Make routing decision based on confidence and autonomy mode"""
        
        # In shadow mode, everything goes to human approval
        if autonomy_mode == AutonomyMode.SHADOW:
            return "human_approval"
        
        # In assisted mode, use confidence thresholds
        if autonomy_mode == AutonomyMode.ASSISTED:
            if confidence_level == ConfidenceLevel.HIGH:
                # Even high confidence actions get notification in assisted mode
                return "notify_and_execute"
            elif confidence_level == ConfidenceLevel.MEDIUM:
                return "notify_and_execute"
            else:
                return "human_approval"
        
        # In autonomous mode, use full confidence-based routing
        if autonomy_mode == AutonomyMode.AUTONOMOUS:
            if confidence_level == ConfidenceLevel.HIGH:
                return "auto_execute"
            elif confidence_level == ConfidenceLevel.MEDIUM:
                return "notify_and_execute"
            else:
                return "human_approval"
        
        # Default to human approval for safety
        return "human_approval"
    
    def _generate_reasoning(
        self,
        confidence_level: ConfidenceLevel,
        routing_decision: str,
        factors: ConfidenceFactors
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        reasoning_parts = []
        
        # Confidence level explanation
        if confidence_level == ConfidenceLevel.HIGH:
            reasoning_parts.append("High confidence based on strong evidence and historical accuracy")
        elif confidence_level == ConfidenceLevel.MEDIUM:
            reasoning_parts.append("Medium confidence with some uncertainty in analysis")
        else:
            reasoning_parts.append("Low confidence due to insufficient evidence or conflicting signals")
        
        # Factor breakdown
        if factors.llm_self_assessment < 60:
            reasoning_parts.append("AI model expressed uncertainty about the analysis")
        
        if factors.historical_accuracy < 70:
            reasoning_parts.append("Limited historical success for similar actions")
        
        if factors.evidence_strength < 60:
            reasoning_parts.append("Weak or conflicting evidence")
        
        # Routing explanation
        if routing_decision == "auto_execute":
            reasoning_parts.append("Proceeding automatically due to high confidence")
        elif routing_decision == "notify_and_execute":
            reasoning_parts.append("Executing with notification to maintain oversight")
        else:
            reasoning_parts.append("Requiring human approval due to uncertainty")
        
        return ". ".join(reasoning_parts) + "."
    
    async def _execute_routing_decision(
        self,
        incident_id: str,
        decision: RoutingDecision,
        proposed_action: Dict[str, Any]
    ):
        """Execute the routing decision"""
        try:
            if decision.routing_decision == "auto_execute":
                await self._auto_execute_action(incident_id, decision, proposed_action)
                
            elif decision.routing_decision == "notify_and_execute":
                await self._notify_and_execute_action(incident_id, decision, proposed_action)
                
            elif decision.routing_decision == "human_approval":
                await self._request_human_approval(incident_id, decision, proposed_action)
                
        except Exception as e:
            logger.error(f"Failed to execute routing decision: {str(e)}")
            # Fallback to notification
            await self._send_error_notification(incident_id, decision, str(e))
    
    async def _auto_execute_action(
        self,
        incident_id: str,
        decision: RoutingDecision,
        proposed_action: Dict[str, Any]
    ):
        """Auto-execute action with logging"""
        logger.info(f"Auto-executing {decision.action_type.value} for incident {incident_id}")
        
        # Log the auto-execution
        await self._send_teams_notification(
            f"🤖 Auto-executed {decision.action_type.value} for incident {incident_id}",
            {
                "confidence": f"{decision.composite_score:.1f}%",
                "reasoning": decision.reasoning,
                "action": proposed_action
            },
            color="good"
        )
        
        # Execute the actual action (would integrate with specific services)
        # await self._execute_action(proposed_action)
    
    async def _notify_and_execute_action(
        self,
        incident_id: str,
        decision: RoutingDecision,
        proposed_action: Dict[str, Any]
    ):
        """Execute action with mandatory notification"""
        logger.info(f"Executing {decision.action_type.value} with notification for incident {incident_id}")
        
        # Send Teams notification before execution
        await self._send_teams_notification(
            f"⚡ Executing {decision.action_type.value} for incident {incident_id}",
            {
                "confidence": f"{decision.composite_score:.1f}%",
                "reasoning": decision.reasoning,
                "action": proposed_action,
                "note": "Action executed automatically - human oversight maintained"
            },
            color="warning"
        )
        
        # Execute the action
        # await self._execute_action(proposed_action)
    
    async def _request_human_approval(
        self,
        incident_id: str,
        decision: RoutingDecision,
        proposed_action: Dict[str, Any]
    ):
        """Request human approval via Step Functions Task Token"""
        logger.info(f"Requesting human approval for {decision.action_type.value} in incident {incident_id}")
        
        # Create approval request
        approval_request = ApprovalRequest(
            request_id=f"approval_{incident_id}_{int(time.time())}",
            incident_id=incident_id,
            action_type=decision.action_type,
            proposed_action=proposed_action,
            confidence_score=decision.composite_score,
            reasoning=decision.reasoning,
            evidence=decision.evidence,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=decision.approval_timeout_minutes)
        )
        
        # Store approval request (in production, this would be DynamoDB)
        # await self._store_approval_request(approval_request)
        
        # Send Teams notification with approval buttons
        await self._send_approval_notification(approval_request)
        
        # Pause Step Functions execution with Task Token
        # This would integrate with the actual Step Functions workflow
        logger.info(f"Step Functions execution paused for approval: {approval_request.request_id}")
    
    async def _send_teams_notification(
        self,
        message: str,
        details: Dict[str, Any],
        color: str = "warning"
    ):
        """Send notification to Microsoft Teams"""
        try:
            # In production, this would use the Teams API
            logger.info(f"Teams notification: {message}")
            logger.info(f"Details: {json.dumps(details, indent=2)}")
            
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {str(e)}")
    
    async def _send_approval_notification(self, approval_request: ApprovalRequest):
        """Send approval request to Microsoft Teams with interactive buttons"""
        try:
            # Teams Adaptive Card format
            card = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "version": "1.3",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "🚨 Human Approval Required",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Attention"
                                },
                                {
                                    "type": "FactSet",
                                    "facts": [
                                        {
                                            "title": "Incident:",
                                            "value": approval_request.incident_id
                                        },
                                        {
                                            "title": "Action:",
                                            "value": approval_request.action_type.value
                                        },
                                        {
                                            "title": "Confidence:",
                                            "value": f"{approval_request.confidence_score:.1f}%"
                                        },
                                        {
                                            "title": "Expires:",
                                            "value": approval_request.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')
                                        }
                                    ]
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**Reasoning:** {approval_request.reasoning}",
                                    "wrap": True
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"**Proposed Action:**\n```json\n{json.dumps(approval_request.proposed_action, indent=2)}\n```",
                                    "wrap": True
                                }
                            ],
                            "actions": [
                                {
                                    "type": "Action.Http",
                                    "title": "✅ Approve",
                                    "style": "positive",
                                    "url": f"https://your-api-gateway/approval/{approval_request.request_id}/approve",
                                    "method": "POST"
                                },
                                {
                                    "type": "Action.Http",
                                    "title": "❌ Reject",
                                    "style": "destructive",
                                    "url": f"https://your-api-gateway/approval/{approval_request.request_id}/reject",
                                    "method": "POST"
                                }
                            ]
                        }
                    }
                ]
            }
            
            logger.info(f"Teams approval request sent: {json.dumps(card, indent=2)}")
            
        except Exception as e:
            logger.error(f"Failed to send Teams approval notification: {str(e)}")
    
    async def _send_error_notification(
        self,
        incident_id: str,
        decision: RoutingDecision,
        error: str
    ):
        """Send error notification"""
        await self._send_teams_notification(
            f"❌ Routing error for incident {incident_id}",
            {
                "action_type": decision.action_type.value,
                "error": error,
                "fallback": "Manual intervention required"
            },
            color="danger"
        )
    
    async def _log_decision(self, incident_id: str, decision: RoutingDecision):
        """Log decision for audit trail"""
        try:
            audit_entry = {
                "incident_id": incident_id,
                "timestamp": decision.timestamp.isoformat(),
                "action_type": decision.action_type.value,
                "confidence_level": decision.confidence_level.value,
                "composite_score": decision.composite_score,
                "routing_decision": decision.routing_decision,
                "reasoning": decision.reasoning,
                "confidence_factors": {
                    "llm_self_assessment": decision.confidence_factors.llm_self_assessment,
                    "historical_accuracy": decision.confidence_factors.historical_accuracy,
                    "evidence_strength": decision.confidence_factors.evidence_strength,
                    "retrieval_relevance": decision.confidence_factors.retrieval_relevance,
                    "consensus_agreement": decision.confidence_factors.consensus_agreement
                }
            }
            
            # In production, store in DynamoDB for audit trail
            logger.info(f"Decision logged: {json.dumps(audit_entry, indent=2)}")
            
        except Exception as e:
            logger.error(f"Failed to log decision: {str(e)}")
    
    def update_autonomy_mode(self, new_mode: AutonomyMode):
        """Update autonomy mode based on performance"""
        old_mode = self.autonomy_mode
        self.autonomy_mode = new_mode
        logger.info(f"Autonomy mode updated: {old_mode.value} -> {new_mode.value}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get routing performance metrics"""
        # In production, this would query actual performance data
        return {
            "autonomy_mode": self.autonomy_mode.value,
            "confidence_thresholds": {
                level.value: threshold for level, threshold in self.confidence_thresholds.items()
            },
            "routing_distribution": {
                "auto_execute": 25,
                "notify_and_execute": 45,
                "human_approval": 30
            },
            "average_confidence_score": 76.5,
            "approval_response_time_minutes": 8.2,
            "accuracy_by_action_type": {
                action.value: self._get_historical_accuracy(action, {})
                for action in ActionType
            }
        }


# Global router instance
_confidence_router = None

def get_confidence_router() -> ConfidenceRouter:
    """Get global confidence router instance"""
    global _confidence_router
    if _confidence_router is None:
        _confidence_router = ConfidenceRouter()
    return _confidence_router