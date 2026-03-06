"""
Integration Wiring Tests

Comprehensive tests to verify all components are properly wired together
and the system can run end-to-end without issues.
"""

import pytest
import asyncio
import json
import sys
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Test all imports work correctly
def test_all_imports():
    """Test that all components can be imported without errors"""
    try:
        # Core system
        from enhanced_system import EnhancedIncidentResponseSystem, get_enhanced_system
        
        # Orchestrator components
        from orchestrator.enhanced_orchestrator import EnhancedOrchestrator
        from orchestrator.session_manager import SessionManager
        from orchestrator.memory_manager import MemoryManager
        from orchestrator.agentcore_config import AgentCoreConfig, get_default_config
        
        # Caching components
        from caching.bedrock_prompt_cache import BedrockPromptCache, get_bedrock_cache
        from caching.semantic_cache import SemanticCache, get_semantic_cache
        from caching.agentic_plan_cache import AgenticPlanCache, get_plan_cache, PlanType
        
        # Routing components
        from routing.confidence_router import (
            ConfidenceRouter, get_confidence_router, ConfidenceLevel,
            ActionType, AutonomyMode, ConfidenceFactors, RoutingDecision
        )
        print("✅ Routing imports successful")
        
        # Agent components
        from agents.enhanced_log_analysis_agent import EnhancedLogAnalysisAgent
        from agents.log_analysis_agent import LogAnalysisAgent
        from agents.communication_agent import CommunicationAgent
        from agents.fix_recommendation_agent import FixRecommendationAgent
        
        # Infrastructure components
        from infrastructure.lambda_functions import lambda_handler
        
        print("✅ All imports successful")
        
    except ImportError as e:
        pytest.fail(f"Import error: {str(e)}")


def test_global_singletons():
    """Test that global singleton instances work correctly"""
    from enhanced_system import get_enhanced_system
    from caching.bedrock_prompt_cache import get_bedrock_cache
    from caching.semantic_cache import get_semantic_cache
    from caching.agentic_plan_cache import get_plan_cache
    from routing.confidence_router import get_confidence_router
    
    # Test singletons return same instance
    system1 = get_enhanced_system()
    system2 = get_enhanced_system()
    assert system1 is system2
    
    cache1 = get_bedrock_cache()
    cache2 = get_bedrock_cache()
    assert cache1 is cache2
    
    router1 = get_confidence_router()
    router2 = get_confidence_router()
    assert router1 is router2
    
    print("✅ Global singletons working correctly")


@pytest.mark.asyncio
async def test_enhanced_system_initialization():
    """Test that enhanced system initializes all components correctly"""
    from enhanced_system import EnhancedIncidentResponseSystem
    
    system = EnhancedIncidentResponseSystem()
    
    # Check all components are initialized
    assert system.orchestrator is not None
    assert system.bedrock_cache is not None
    assert system.semantic_cache is not None
    assert system.plan_cache is not None
    assert system.confidence_router is not None
    
    # Check system metrics structure
    metrics = system.get_system_metrics()
    required_metrics = [
        "incidents_processed",
        "average_processing_time_seconds", 
        "total_cache_cost_savings_usd",
        "human_approval_rate_percent"
    ]
    
    for metric in required_metrics:
        assert metric in metrics
    
    print("✅ Enhanced system initialization working")


@pytest.mark.asyncio
async def test_orchestrator_agent_wiring():
    """Test that orchestrator properly wires to all agents"""
    from orchestrator.enhanced_orchestrator import EnhancedOrchestrator
    
    orchestrator = EnhancedOrchestrator()
    
    # Check all agents are initialized
    assert orchestrator.log_analyzer is not None
    assert orchestrator.metrics_investigator is not None
    assert orchestrator.impact_assessor is not None
    assert orchestrator.synthesis_agent is not None
    assert orchestrator.fix_agent is not None
    assert orchestrator.communication_agent is not None
    
    # Check session and memory managers
    assert orchestrator.session_manager is not None
    assert orchestrator.memory_manager is not None
    
    print("✅ Orchestrator agent wiring working")


@pytest.mark.asyncio
async def test_caching_layer_integration():
    """Test that all caching layers integrate properly"""
    from caching.bedrock_prompt_cache import get_bedrock_cache
    from caching.semantic_cache import get_semantic_cache
    from caching.agentic_plan_cache import get_plan_cache, PlanType
    
    bedrock_cache = get_bedrock_cache()
    semantic_cache = get_semantic_cache()
    plan_cache = get_plan_cache()
    
    # Test bedrock cache
    prompt = bedrock_cache.create_cached_prompt(
        system_prompt="Test system prompt " * 300,  # Make it long enough (>4096 chars = >1024 tokens)
        user_prompt="Test user prompt",
        cache_key="test_key"
    )
    assert "<cache_point>" in prompt
    assert "</cache_point>" in prompt
    
    # Test semantic cache (mock Redis)
    with patch.object(semantic_cache.redis_client, 'keys', return_value=[]):
        with patch.object(semantic_cache, '_get_embedding', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1024
            
            async def mock_compute():
                return {"result": "test"}
            
            result, was_hit = await semantic_cache.get_or_compute(
                query="test query",
                compute_func=mock_compute
            )
            assert result["result"] == "test"
    
    # Test plan cache
    incident_data = {"service_name": "test", "error_message": "test error"}
    plan, was_hit = await plan_cache.get_or_create_plan(incident_data, PlanType.LOG_ANALYSIS)
    assert plan is not None
    assert plan.plan_type == PlanType.LOG_ANALYSIS
    
    print("✅ Caching layer integration working")


@pytest.mark.asyncio
async def test_confidence_router_integration():
    """Test confidence router integration with other components"""
    from routing.confidence_router import get_confidence_router, ActionType, ConfidenceFactors
    
    router = get_confidence_router()
    
    confidence_factors = ConfidenceFactors(
        llm_self_assessment=85.0,
        retrieval_relevance=78.0,
        historical_accuracy=82.0,
        evidence_strength=80.0,
        consensus_agreement=88.0
    )
    
    with patch.multiple(
        router,
        _execute_routing_decision=AsyncMock(),
        _log_decision=AsyncMock()
    ):
        decision = await router.route_action(
            incident_id="test-001",
            action_type=ActionType.RESTART_SERVICE,
            proposed_action={"action": "restart"},
            confidence_factors=confidence_factors,
            context={"service_name": "test"}
        )
        
        assert decision is not None
        assert hasattr(decision, 'confidence_level')
        assert hasattr(decision, 'routing_decision')
        assert hasattr(decision, 'composite_score')
    
    print("✅ Confidence router integration working")


@pytest.mark.asyncio
async def test_teams_integration():
    """Test Microsoft Teams integration structure"""
    from routing.confidence_router import get_confidence_router
    
    router = get_confidence_router()
    
    # Test Teams configuration attributes
    assert hasattr(router, 'teams_webhook_url')
    assert hasattr(router, 'approval_channel')
    
    print("✅ Teams integration structure working")


@pytest.mark.asyncio
async def test_enhanced_log_analysis_agent():
    """Test enhanced log analysis agent integration"""
    from agents.enhanced_log_analysis_agent import EnhancedLogAnalysisAgent
    
    agent = EnhancedLogAnalysisAgent()
    
    # Check caching components are initialized
    assert agent.bedrock_cache is not None
    assert agent.semantic_cache is not None
    
    print("✅ Enhanced log analysis agent integration working")


@pytest.mark.asyncio
async def test_end_to_end_incident_flow():
    """Test complete end-to-end incident processing flow"""
    from enhanced_system import EnhancedIncidentResponseSystem
    
    system = EnhancedIncidentResponseSystem()
    
    incident_data = {
        "incident_id": "integration-test-001",
        "service_name": "test-service",
        "timestamp": "2025-03-04T10:30:00Z",
        "error_message": "Integration test error",
        "log_location": "s3://test-logs/",
        "severity": "medium"
    }
    
    # Mock all external dependencies
    with patch.multiple(
        system,
        _warm_caches_and_get_plan=AsyncMock(),
        _run_enhanced_orchestration=AsyncMock(return_value={
            "enhanced_alert": {"incident_id": "integration-test-001"},
            "investigation_result": {"synthesis": {"confidence_score": 75}},
            "parallel_efficiency_gain": 30.0
        }),
        _apply_confidence_routing=AsyncMock(return_value=[
            {"routing_decision": "notify_and_execute", "confidence_score": 75}
        ])
    ):
        result = await system.process_incident(incident_data)
        
        # Verify result structure
        assert "incident_id" in result
        assert "processing_metadata" in result
        assert "enhanced_alert" in result
        assert "routing_decisions" in result
        
        # Verify processing metadata
        metadata = result["processing_metadata"]
        assert "total_time_seconds" in metadata
        assert "parallel_efficiency_gain" in metadata
        assert "cache_performance" in metadata
        
        # Verify cache performance structure
        cache_perf = metadata["cache_performance"]
        assert "bedrock_prompt_cache" in cache_perf
        assert "semantic_cache" in cache_perf
        assert "agentic_plan_cache" in cache_perf
    
    print("✅ End-to-end incident flow working")


def test_lambda_handler_structure():
    """Test Lambda handler can be imported and has correct structure"""
    from infrastructure.lambda_functions import lambda_handler
    
    # Test handler exists and is callable
    assert callable(lambda_handler)
    
    # Test with mock event
    mock_event = {
        "httpMethod": "POST",
        "path": "/incident",
        "body": json.dumps({
            "service_name": "test",
            "timestamp": "2025-03-04T10:30:00Z",
            "error_message": "test error",
            "log_location": "s3://test/"
        })
    }
    
    mock_context = Mock()
    
    # Mock AWS services
    with patch('infrastructure.lambda_functions.stepfunctions') as mock_sf:
        mock_sf.start_execution.return_value = {"executionArn": "test-arn"}
        
        with patch('infrastructure.lambda_functions.uuid') as mock_uuid:
            mock_uuid.uuid4.return_value.hex = "test123456789012"
            
            result = lambda_handler(mock_event, mock_context)
            
            assert result["statusCode"] == 202
            assert "incident_id" in json.loads(result["body"])
    
    print("✅ Lambda handler structure working")


def test_environment_variable_handling():
    """Test that environment variables are handled correctly"""
    import os
    
    # Test with missing environment variables
    original_env = os.environ.copy()
    
    try:
        # Clear relevant env vars
        for key in ["AWS_REGION", "BEDROCK_MODEL_ID", "TEAMS_WEBHOOK_URL"]:
            if key in os.environ:
                del os.environ[key]
        
        # Test system still initializes with defaults
        from enhanced_system import EnhancedIncidentResponseSystem
        system = EnhancedIncidentResponseSystem()
        assert system is not None
        
        # Test caching components handle missing Redis
        from caching.semantic_cache import SemanticCache
        cache = SemanticCache(redis_host="nonexistent-host")
        assert cache is not None
        
    finally:
        # Restore environment
        os.environ.clear()
        os.environ.update(original_env)
    
    print("✅ Environment variable handling working")


@pytest.mark.asyncio
async def test_error_handling_and_fallbacks():
    """Test error handling and fallback mechanisms"""
    from enhanced_system import EnhancedIncidentResponseSystem
    
    system = EnhancedIncidentResponseSystem()
    
    incident_data = {
        "incident_id": "error-test-001",
        "service_name": "test-service",
        "timestamp": "2025-03-04T10:30:00Z",
        "error_message": "Error handling test",
        "log_location": "s3://test-logs/"
    }
    
    # Test with orchestration failure
    with patch.object(system, '_run_enhanced_orchestration', side_effect=Exception("Test error")):
        result = await system.process_incident(incident_data)
        
        # Should return error response
        assert result["status"] == "failed"
        assert "error" in result
    
    print("✅ Error handling and fallbacks working")


def test_configuration_validation():
    """Test configuration validation"""
    from orchestrator.agentcore_config import AgentCoreConfig, get_default_config
    
    # Test default config
    config = get_default_config()
    assert config is not None
    
    # Test config validation
    try:
        config.validate()
        print("✅ Configuration validation working")
    except Exception as e:
        pytest.fail(f"Configuration validation failed: {str(e)}")


if __name__ == "__main__":
    # Run all integration tests
    print("🔍 Running Integration Wiring Tests...")
    print("=" * 50)
    
    # Run synchronous tests
    test_all_imports()
    test_global_singletons()
    test_lambda_handler_structure()
    test_environment_variable_handling()
    test_configuration_validation()
    
    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(test_enhanced_system_initialization())
        loop.run_until_complete(test_orchestrator_agent_wiring())
        loop.run_until_complete(test_caching_layer_integration())
        loop.run_until_complete(test_confidence_router_integration())
        loop.run_until_complete(test_teams_integration())
        loop.run_until_complete(test_enhanced_log_analysis_agent())
        loop.run_until_complete(test_end_to_end_incident_flow())
        loop.run_until_complete(test_error_handling_and_fallbacks())
    finally:
        loop.close()
    
    print("=" * 50)
    print("✅ All Integration Wiring Tests Passed!")
    print("🚀 System is properly wired and ready to run!")