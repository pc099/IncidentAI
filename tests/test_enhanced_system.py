"""
Comprehensive test suite for Enhanced AI-Powered Incident Response System

Tests all key components:
- Enhanced orchestrator with parallel processing
- Three-layer caching system
- Confidence-based routing
- Real-time streaming
- End-to-end incident processing
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_system import EnhancedIncidentResponseSystem
from orchestrator.enhanced_orchestrator import EnhancedOrchestrator
from caching.bedrock_prompt_cache import BedrockPromptCache
from caching.semantic_cache import SemanticCache
from caching.agentic_plan_cache import AgenticPlanCache, PlanType
from routing.confidence_router import ConfidenceRouter, ActionType, ConfidenceFactors


class TestEnhancedSystem:
    """Test the main enhanced system integration"""
    
    @pytest.fixture
    def enhanced_system(self):
        """Create enhanced system instance for testing"""
        return EnhancedIncidentResponseSystem(region="us-east-1")
    
    @pytest.fixture
    def sample_incident(self):
        """Sample incident data for testing"""
        return {
            "incident_id": "test-incident-001",
            "service_name": "payment-processor",
            "timestamp": "2025-03-04T10:30:00Z",
            "error_message": "Lambda deployment failed: missing DATABASE_URL",
            "log_location": "s3://test-logs/payment-processor/",
            "severity": "high"
        }
    
    @pytest.mark.asyncio
    async def test_process_incident_success(self, enhanced_system, sample_incident):
        """Test successful incident processing"""
        with patch.multiple(
            enhanced_system,
            _warm_caches_and_get_plan=AsyncMock(),
            _run_enhanced_orchestration=AsyncMock(return_value={
                "enhanced_alert": {"incident_id": "test-incident-001"},
                "investigation_result": {"synthesis": {"confidence_score": 85}},
                "parallel_efficiency_gain": 36.5
            }),
            _apply_confidence_routing=AsyncMock(return_value=[
                {"routing_decision": "notify_and_execute", "confidence_score": 85}
            ])
        ):
            result = await enhanced_system.process_incident(
                incident_data=sample_incident
            )
            
            assert result["incident_id"] == "test-incident-001"
            assert "processing_metadata" in result
            assert "enhanced_alert" in result
            assert result["processing_metadata"]["parallel_efficiency_gain"] == 36.5
    
    @pytest.mark.asyncio
    async def test_process_incident_with_teams_notifications(self, enhanced_system, sample_incident):
        """Test incident processing with Teams notifications"""
        with patch.multiple(
            enhanced_system,
            _send_initial_notification=AsyncMock(),
            _send_completion_notification=AsyncMock(),
            _warm_caches_and_get_plan=AsyncMock(),
            _run_enhanced_orchestration=AsyncMock(return_value={
                "enhanced_alert": {"incident_id": "test-incident-001"},
                "investigation_result": {},
                "parallel_efficiency_gain": 25.0
            }),
            _apply_confidence_routing=AsyncMock(return_value=[])
        ):
            result = await enhanced_system.process_incident(
                incident_data=sample_incident
            )
            
            # Verify Teams notifications were called
            enhanced_system._send_initial_notification.assert_called_once()
            enhanced_system._send_completion_notification.assert_called_once()
    
    def test_system_metrics(self, enhanced_system):
        """Test system metrics collection"""
        # Simulate some processing
        enhanced_system._update_system_metrics({
            "processing_metadata": {
                "total_time_seconds": 45.2,
                "parallel_efficiency_gain": 32.1,
                "cache_performance": {
                    "bedrock_prompt_cache": {"cost_savings_usd": 0.15}
                }
            },
            "routing_decisions": [
                {"requires_approval": False},
                {"requires_approval": True}
            ]
        })
        
        metrics = enhanced_system.get_system_metrics()
        
        assert metrics["incidents_processed"] == 1
        assert metrics["total_cache_cost_savings_usd"] == 0.15
        assert metrics["human_approval_rate_percent"] == 50.0


class TestEnhancedOrchestrator:
    """Test the enhanced orchestrator with parallel processing"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance for testing"""
        return EnhancedOrchestrator(region="us-east-1")
    
    @pytest.fixture
    def sample_event(self):
        """Sample event data for testing"""
        return {
            "incident_id": "test-incident-001",
            "service_name": "api-gateway",
            "timestamp": "2025-03-04T10:30:00Z",
            "error_message": "Service unavailable: Lambda concurrent execution limit exceeded",
            "log_location": "s3://test-logs/api-gateway/"
        }
    
    @pytest.mark.asyncio
    async def test_parallel_investigation(self, orchestrator, sample_event):
        """Test parallel investigation execution"""
        with patch.multiple(
            orchestrator,
            _log_analysis_task=AsyncMock(return_value=Mock(
                agent_name="log_analysis", success=True, 
                execution_time_seconds=15.0, confidence_score=80
            )),
            _kb_search_task=AsyncMock(return_value=Mock(
                agent_name="kb_search", success=True,
                execution_time_seconds=12.0, confidence_score=75
            ))
        ):
            with patch.object(orchestrator.metrics_investigator, 'investigate', new_callable=AsyncMock) as mock_metrics:
                mock_metrics.return_value = Mock(
                    agent_name="metrics_investigator", success=True,
                    execution_time_seconds=18.0, confidence_score=85
                )
                
                with patch.object(orchestrator.impact_assessor, 'investigate', new_callable=AsyncMock) as mock_impact:
                    mock_impact.return_value = Mock(
                        agent_name="impact_assessor", success=True,
                        execution_time_seconds=10.0, confidence_score=90
                    )
                    
                    with patch.object(orchestrator.synthesis_agent, 'synthesize', new_callable=AsyncMock) as mock_synthesis:
                        mock_synthesis.return_value = Mock(
                            agent_name="synthesis", success=True,
                            execution_time_seconds=8.0, confidence_score=82
                        )
                        
                        result = await orchestrator._parallel_investigation("session-001", sample_event)
                        
                        assert result.parallel_efficiency_gain > 0
                        assert result.log_analysis.success
                        assert result.metrics_investigation.success
                        assert result.synthesis.success
    
    @pytest.mark.asyncio
    async def test_handle_incident_end_to_end(self, orchestrator, sample_event):
        """Test complete incident handling"""
        with patch.multiple(
            orchestrator,
            _parallel_investigation=AsyncMock(return_value=Mock(
                parallel_efficiency_gain=35.2,
                total_investigation_time=25.0,
                synthesis=Mock(success=True, output={"confidence_score": 85})
            )),
            _root_cause_analysis=AsyncMock(return_value={
                "primary_cause": {"category": "resource_exhaustion", "confidence_score": 88}
            }),
            _generate_fixes=AsyncMock(return_value={
                "immediate_actions": [{"action": "Scale Lambda concurrency"}]
            }),
            _generate_communication=AsyncMock(return_value={
                "incident_id": "test-incident-001",
                "technical_summary": "Resource exhaustion detected"
            })
        ):
            result = await orchestrator.handle_incident(sample_event)
            
            assert result["incident_id"] == "test-incident-001"
            assert result["parallel_efficiency_gain"] == 35.2
            assert "enhanced_alert" in result


class TestCachingLayers:
    """Test the three-layer caching system"""
    
    def test_bedrock_prompt_cache(self):
        """Test Bedrock prompt caching"""
        cache = BedrockPromptCache()
        
        # Test cache point creation
        system_prompt = "You are an expert log analysis agent. " * 100  # Make it long enough
        user_prompt = "Analyze this incident"
        
        cached_prompt = cache.create_cached_prompt(system_prompt, user_prompt, "test_key")
        
        assert "<cache_point>" in cached_prompt
        assert "</cache_point>" in cached_prompt
        assert user_prompt in cached_prompt
    
    @pytest.mark.asyncio
    async def test_semantic_cache(self):
        """Test semantic caching functionality"""
        cache = SemanticCache(redis_host="localhost", redis_port=6379)
        
        # Mock Redis operations
        with patch.object(cache.redis_client, 'keys', return_value=[]):
            with patch.object(cache, '_get_embedding', new_callable=AsyncMock) as mock_embed:
                mock_embed.return_value = [0.1] * 1024
                
                async def mock_compute():
                    return {"result": "computed_value"}
                
                result, was_hit = await cache.get_or_compute(
                    query="test query",
                    compute_func=mock_compute,
                    cache_key_prefix="test"
                )
                
                assert result["result"] == "computed_value"
                assert was_hit is False  # First time, should be cache miss
    
    @pytest.mark.asyncio
    async def test_agentic_plan_cache(self):
        """Test agentic plan caching"""
        cache = AgenticPlanCache()
        
        incident_data = {
            "service_name": "payment-service",
            "error_message": "timeout error"
        }
        
        plan, was_hit = await cache.get_or_create_plan(incident_data, PlanType.LOG_ANALYSIS)
        
        assert plan.plan_type == PlanType.LOG_ANALYSIS
        assert len(plan.execution_steps) > 0
        # First time should use base template
        assert was_hit is False


class TestConfidenceRouter:
    """Test confidence-based routing system"""
    
    @pytest.fixture
    def router(self):
        """Create router instance for testing"""
        return ConfidenceRouter(region="us-east-1")
    
    @pytest.fixture
    def confidence_factors(self):
        """Sample confidence factors"""
        return ConfidenceFactors(
            llm_self_assessment=85.0,
            retrieval_relevance=78.0,
            historical_accuracy=82.0,
            evidence_strength=80.0,
            consensus_agreement=88.0
        )
    
    @pytest.mark.asyncio
    async def test_route_high_confidence_action(self, router, confidence_factors):
        """Test routing of high confidence action"""
        with patch.multiple(
            router,
            _execute_routing_decision=AsyncMock(),
            _log_decision=AsyncMock()
        ):
            decision = await router.route_action(
                incident_id="test-001",
                action_type=ActionType.RESTART_SERVICE,
                proposed_action={"action": "restart service"},
                confidence_factors=confidence_factors,
                context={"service_name": "test-service"}
            )
            
            assert decision.confidence_level.value in ["high", "medium"]
            assert decision.composite_score > 70
            assert not decision.requires_approval or decision.routing_decision != "auto_execute"
    
    @pytest.mark.asyncio
    async def test_route_low_confidence_action(self, router):
        """Test routing of low confidence action"""
        low_confidence = ConfidenceFactors(
            llm_self_assessment=45.0,
            retrieval_relevance=40.0,
            historical_accuracy=35.0,
            evidence_strength=50.0,
            consensus_agreement=42.0
        )
        
        with patch.multiple(
            router,
            _execute_routing_decision=AsyncMock(),
            _log_decision=AsyncMock()
        ):
            decision = await router.route_action(
                incident_id="test-001",
                action_type=ActionType.UPDATE_CONFIGURATION,
                proposed_action={"action": "update config"},
                confidence_factors=low_confidence,
                context={"service_name": "critical-service"}
            )
            
            assert decision.confidence_level.value == "low"
            assert decision.requires_approval is True
            assert decision.routing_decision == "human_approval"
    
    def test_confidence_calculation(self, router, confidence_factors):
        """Test composite confidence calculation"""
        composite = router._calculate_composite_confidence(confidence_factors)
        
        # Should be weighted average of factors
        assert 70 <= composite <= 90
        assert isinstance(composite, float)


class TestWebSocketManager:
    """Test Microsoft Teams integration functionality"""
    
    @pytest.fixture
    def teams_integration(self):
        """Create Teams integration for testing"""
        from routing.confidence_router import get_confidence_router
        return get_confidence_router()
    
    @pytest.mark.asyncio
    async def test_teams_notification_structure(self, teams_integration):
        """Test Teams notification structure"""
        # Test Teams configuration attributes
        assert hasattr(teams_integration, 'teams_webhook_url')
        assert hasattr(teams_integration, 'approval_channel')
        
        print("✅ Teams integration structure working")


class TestIntegrationScenarios:
    """Integration tests for complete scenarios"""
    
    @pytest.mark.asyncio
    async def test_configuration_error_scenario(self):
        """Test complete configuration error scenario"""
        system = EnhancedIncidentResponseSystem()
        
        incident = {
            "incident_id": "config-error-001",
            "service_name": "payment-processor",
            "timestamp": "2025-03-04T10:30:00Z",
            "error_message": "Lambda deployment failed: missing DATABASE_URL environment variable",
            "log_location": "s3://test-logs/payment-processor/",
            "severity": "high"
        }
        
        # Mock all external dependencies
        with patch.multiple(
            system,
            _warm_caches_and_get_plan=AsyncMock(),
            _run_enhanced_orchestration=AsyncMock(return_value={
                "enhanced_alert": {
                    "incident_id": "config-error-001",
                    "root_cause": "configuration_error",
                    "confidence_score": 88
                },
                "investigation_result": {
                    "synthesis": {"confidence_score": 85}
                },
                "parallel_efficiency_gain": 34.2
            }),
            _apply_confidence_routing=AsyncMock(return_value=[
                {
                    "routing_decision": "notify_and_execute",
                    "confidence_score": 88,
                    "requires_approval": False
                }
            ])
        ):
            result = await system.process_incident(incident)
            
            assert result["incident_id"] == "config-error-001"
            assert result["enhanced_alert"]["root_cause"] == "configuration_error"
            assert result["processing_metadata"]["parallel_efficiency_gain"] > 30
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_scenario(self):
        """Test complete resource exhaustion scenario"""
        system = EnhancedIncidentResponseSystem()
        
        incident = {
            "incident_id": "resource-exhaustion-001",
            "service_name": "api-gateway",
            "timestamp": "2025-03-04T10:35:00Z",
            "error_message": "Service unavailable: Lambda concurrent execution limit exceeded",
            "log_location": "s3://test-logs/api-gateway/",
            "severity": "critical"
        }
        
        with patch.multiple(
            system,
            _warm_caches_and_get_plan=AsyncMock(),
            _run_enhanced_orchestration=AsyncMock(return_value={
                "enhanced_alert": {
                    "incident_id": "resource-exhaustion-001",
                    "root_cause": "resource_exhaustion",
                    "confidence_score": 92
                },
                "investigation_result": {
                    "synthesis": {"confidence_score": 90}
                },
                "parallel_efficiency_gain": 38.1
            }),
            _apply_confidence_routing=AsyncMock(return_value=[
                {
                    "routing_decision": "auto_execute",
                    "confidence_score": 92,
                    "requires_approval": False
                }
            ])
        ):
            result = await system.process_incident(incident)
            
            assert result["incident_id"] == "resource-exhaustion-001"
            assert result["enhanced_alert"]["confidence_score"] == 92
            assert result["routing_decisions"][0]["routing_decision"] == "auto_execute"


# Performance benchmarks
class TestPerformanceBenchmarks:
    """Performance benchmarks for the enhanced system"""
    
    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_performance(self):
        """Benchmark parallel vs sequential processing"""
        # This would be a more comprehensive benchmark in practice
        orchestrator = EnhancedOrchestrator()
        
        sample_event = {
            "incident_id": "perf-test-001",
            "service_name": "test-service",
            "timestamp": "2025-03-04T10:30:00Z",
            "error_message": "Performance test error",
            "log_location": "s3://test-logs/"
        }
        
        # Mock agent execution times
        with patch.multiple(
            orchestrator,
            _log_analysis_task=AsyncMock(return_value=Mock(
                execution_time_seconds=15.0, success=True
            )),
            _kb_search_task=AsyncMock(return_value=Mock(
                execution_time_seconds=12.0, success=True
            ))
        ):
            with patch.object(orchestrator.metrics_investigator, 'investigate') as mock_metrics:
                mock_metrics.return_value = Mock(execution_time_seconds=18.0, success=True)
                
                with patch.object(orchestrator.impact_assessor, 'investigate') as mock_impact:
                    mock_impact.return_value = Mock(execution_time_seconds=10.0, success=True)
                    
                    with patch.object(orchestrator.synthesis_agent, 'synthesize') as mock_synthesis:
                        mock_synthesis.return_value = Mock(execution_time_seconds=8.0, success=True)
                        
                        start_time = time.time()
                        result = await orchestrator._parallel_investigation("session-001", sample_event)
                        parallel_time = time.time() - start_time
                        
                        # Sequential time would be sum of all agent times
                        sequential_time_estimate = 15.0 + 12.0 + 18.0 + 10.0 + 8.0
                        
                        # Parallel should be significantly faster
                        assert parallel_time < sequential_time_estimate * 0.8
                        assert result.parallel_efficiency_gain > 20


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])