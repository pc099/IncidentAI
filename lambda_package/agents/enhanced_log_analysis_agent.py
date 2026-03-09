"""
Enhanced Log Analysis Agent

Upgraded version of the log analysis agent with:
- Async processing capabilities
- Enhanced error pattern recognition
- Integration with caching layers
- Microsoft Teams progress notifications
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from src.agents.log_analysis_agent import LogAnalysisAgent
from src.caching.bedrock_prompt_cache import get_bedrock_cache
from src.caching.semantic_cache import get_semantic_cache

logger = logging.getLogger(__name__)


class EnhancedLogAnalysisAgent(LogAnalysisAgent):
    """
    Enhanced Log Analysis Agent with caching capabilities
    
    Improvements over base agent:
    - Async processing with progress notifications
    - Bedrock prompt caching for cost reduction
    - Semantic caching for similar log patterns
    - Enhanced error pattern recognition
    - Structured confidence scoring
    """
    
    def __init__(self, bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"):
        """Initialize enhanced log analysis agent"""
        super().__init__(bedrock_model_id)
        
        # Initialize caching layers
        self.bedrock_cache = get_bedrock_cache()
        self.semantic_cache = get_semantic_cache()
        
        # Enhanced configuration
        self.max_log_size_mb = 50
        self.pattern_confidence_threshold = 0.7
        
        logger.info("Enhanced Log Analysis Agent initialized")
    
    async def analyze_async(
        self,
        service_name: str,
        timestamp: str,
        log_location: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async log analysis with caching
        
        Args:
            service_name: Name of the failed service
            timestamp: Failure timestamp
            log_location: S3 location of logs
            session_id: Optional session ID for tracking
            
        Returns:
            Enhanced log analysis results
        """
        start_time = time.time()
        
        try:
            # Stream progress: Starting analysis
            logger.info(f"Starting log analysis for {service_name}")
            
            # Phase 1: Retrieve logs (20% progress)
            logger.debug("Retrieving logs from S3")
            log_content, parsed_data = await self._retrieve_and_parse_logs_async(
                service_name, timestamp, log_location
            )
            
            # Phase 2: Check semantic cache (40% progress)
            logger.debug("Checking semantic cache")
            cache_key = f"log_analysis_{service_name}_{self._hash_content(log_content[:1000])}"
            
            # Try semantic cache first
            cached_result, was_cache_hit = await self.semantic_cache.get_or_compute(
                query=f"Log analysis for {service_name}: {log_content[:500]}",
                compute_func=lambda: self._perform_bedrock_analysis(
                    service_name, timestamp, log_content, parsed_data
                ),
                cache_key_prefix=cache_key
            )
            
            if was_cache_hit:
                logger.info(f"Semantic cache hit for log analysis: {service_name}")
                
                # Add cache metadata
                cached_result["cache_metadata"] = {
                    "semantic_cache_hit": True,
                    "execution_time": time.time() - start_time
                }
                return cached_result
            
            # Phase 3: Bedrock analysis with prompt caching (60% progress)
            logger.debug("Analyzing logs with Bedrock")
            result = await self._perform_cached_bedrock_analysis(
                service_name, timestamp, log_content, parsed_data, session_id
            )
            
            # Phase 4: Post-processing and confidence scoring (80% progress)
            logger.debug("Post-processing results")
            enhanced_result = await self._enhance_analysis_result(result, parsed_data)
            
            # Phase 5: Complete (100% progress)
            logger.info("Log analysis completed")
            
            # Add performance metadata
            enhanced_result["performance_metadata"] = {
                "total_execution_time": time.time() - start_time,
                "semantic_cache_hit": False,
                "bedrock_cache_used": True,
                "log_size_mb": len(log_content) / (1024 * 1024)
            }
            
            logger.info(f"Enhanced log analysis completed for {service_name} in {time.time() - start_time:.2f}s")
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Enhanced log analysis failed: {str(e)}")
            raise
    
    async def _retrieve_and_parse_logs_async(
        self, 
        service_name: str, 
        timestamp: str, 
        log_location: str
    ) -> tuple[str, Dict[str, Any]]:
        """Async log retrieval and parsing"""
        loop = asyncio.get_event_loop()
        
        # Run synchronous operations in thread pool
        log_content = await loop.run_in_executor(
            None, 
            self._retrieve_logs_sync, 
            service_name, timestamp, log_location
        )
        
        parsed_data = await loop.run_in_executor(
            None,
            self._parse_logs_sync,
            log_content
        )
        
        return log_content, parsed_data
    
    def _retrieve_logs_sync(self, service_name: str, timestamp: str, log_location: str) -> str:
        """Synchronous log retrieval (runs in thread pool)"""
        try:
            # Import here to avoid circular imports
            from agents.log_retrieval import retrieve_logs_from_s3, calculate_time_window
            
            # Calculate time window
            start_time, end_time = calculate_time_window(timestamp)
            
            # Retrieve logs
            log_content = retrieve_logs_from_s3(
                bucket_name=log_location.replace("s3://", "").split("/")[0],
                key_prefix="/".join(log_location.replace("s3://", "").split("/")[1:]),
                start_time=start_time,
                end_time=end_time
            )
            
            # Limit log size for processing
            max_chars = self.max_log_size_mb * 1024 * 1024
            if len(log_content) > max_chars:
                log_content = log_content[:max_chars] + "\n... (logs truncated for analysis)"
                logger.warning(f"Logs truncated to {self.max_log_size_mb}MB for analysis")
            
            return log_content
            
        except Exception as e:
            logger.error(f"Log retrieval failed: {str(e)}")
            return f"Error retrieving logs: {str(e)}"
    
    def _parse_logs_sync(self, log_content: str) -> Dict[str, Any]:
        """Synchronous log parsing (runs in thread pool)"""
        try:
            # Import here to avoid circular imports
            from agents.log_parser import parse_logs
            return parse_logs(log_content)
        except Exception as e:
            logger.error(f"Log parsing failed: {str(e)}")
            return {"error_patterns": [], "stack_traces": [], "parsing_error": str(e)}
    
    async def _perform_cached_bedrock_analysis(
        self,
        service_name: str,
        timestamp: str,
        log_content: str,
        parsed_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform Bedrock analysis with prompt caching"""
        
        # Create cached prompt for log analysis
        cached_prompt = self.bedrock_cache.create_incident_analysis_prompt(
            incident_data={
                "service_name": service_name,
                "timestamp": timestamp,
                "log_content": log_content[:2000],  # Truncate for prompt
                "parsed_patterns": parsed_data.get("error_patterns", [])
            },
            analysis_type="log"
        )
        
        # Invoke with caching
        response = await self.bedrock_cache.invoke_with_cache(
            model_id=self.model_id,
            prompt=cached_prompt,
            cache_key=f"log_analysis_{service_name}",
            max_tokens=2000,
            temperature=0.1
        )
        
        # Parse response
        try:
            content = response['content'][0]['text']
            analysis_result = json.loads(content)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Bedrock response as JSON: {str(e)}")
            analysis_result = {
                "error_patterns": parsed_data.get("error_patterns", []),
                "stack_traces": parsed_data.get("stack_traces", []),
                "analysis_summary": content if isinstance(content, str) else "Analysis failed",
                "confidence_score": 50
            }
        
        return analysis_result
    
    async def _perform_bedrock_analysis(
        self,
        service_name: str,
        timestamp: str,
        log_content: str,
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback Bedrock analysis without caching"""
        loop = asyncio.get_event_loop()
        
        # Run synchronous Bedrock call in thread pool
        return await loop.run_in_executor(
            None,
            self._bedrock_analysis_sync,
            service_name, timestamp, log_content, parsed_data
        )
    
    def _bedrock_analysis_sync(
        self,
        service_name: str,
        timestamp: str,
        log_content: str,
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous Bedrock analysis"""
        try:
            prompt = self._create_analysis_prompt(service_name, timestamp, log_content, parsed_data)
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {
                    "error_patterns": parsed_data.get("error_patterns", []),
                    "stack_traces": parsed_data.get("stack_traces", []),
                    "analysis_summary": content,
                    "confidence_score": 60
                }
                
        except Exception as e:
            logger.error(f"Bedrock analysis failed: {str(e)}")
            return {
                "error_patterns": parsed_data.get("error_patterns", []),
                "stack_traces": parsed_data.get("stack_traces", []),
                "analysis_summary": f"Analysis failed: {str(e)}",
                "confidence_score": 0
            }
    
    async def _enhance_analysis_result(
        self, 
        result: Dict[str, Any], 
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance analysis result with additional processing"""
        
        # Calculate enhanced confidence score
        confidence_factors = {
            "pattern_clarity": self._calculate_pattern_clarity(result.get("error_patterns", [])),
            "stack_trace_quality": self._calculate_stack_trace_quality(result.get("stack_traces", [])),
            "log_completeness": self._calculate_log_completeness(parsed_data),
            "analysis_depth": self._calculate_analysis_depth(result)
        }
        
        # Weighted confidence calculation
        weights = {"pattern_clarity": 0.3, "stack_trace_quality": 0.3, "log_completeness": 0.2, "analysis_depth": 0.2}
        enhanced_confidence = sum(
            confidence_factors[factor] * weights[factor] 
            for factor in confidence_factors
        )
        
        # Add enhanced fields
        result["enhanced_confidence_score"] = min(100, max(0, enhanced_confidence))
        result["confidence_factors"] = confidence_factors
        result["agent"] = "enhanced_log_analysis"
        result["analysis_timestamp"] = datetime.now().isoformat()
        
        # Add actionable insights
        result["actionable_insights"] = self._generate_actionable_insights(result)
        
        return result
    
    def _calculate_pattern_clarity(self, error_patterns: List[Dict]) -> float:
        """Calculate clarity score for error patterns"""
        if not error_patterns:
            return 0.0
        
        clarity_score = 0.0
        for pattern in error_patterns:
            # Score based on pattern specificity and frequency
            frequency = pattern.get("frequency", 1)
            specificity = len(pattern.get("pattern", "").split()) / 10  # Normalize by word count
            clarity_score += min(1.0, frequency * specificity)
        
        return min(100.0, (clarity_score / len(error_patterns)) * 100)
    
    def _calculate_stack_trace_quality(self, stack_traces: List[Dict]) -> float:
        """Calculate quality score for stack traces"""
        if not stack_traces:
            return 0.0
        
        quality_score = 0.0
        for trace in stack_traces:
            # Score based on trace completeness and relevance
            trace_text = trace.get("trace", "")
            if "at " in trace_text and "line " in trace_text:
                quality_score += 1.0
            elif "Exception" in trace_text or "Error" in trace_text:
                quality_score += 0.7
            else:
                quality_score += 0.3
        
        return min(100.0, (quality_score / len(stack_traces)) * 100)
    
    def _calculate_log_completeness(self, parsed_data: Dict[str, Any]) -> float:
        """Calculate log completeness score"""
        completeness_factors = [
            bool(parsed_data.get("error_patterns")),
            bool(parsed_data.get("stack_traces")),
            bool(parsed_data.get("timestamps")),
            not bool(parsed_data.get("parsing_error"))
        ]
        
        return (sum(completeness_factors) / len(completeness_factors)) * 100
    
    def _calculate_analysis_depth(self, result: Dict[str, Any]) -> float:
        """Calculate analysis depth score"""
        depth_factors = [
            bool(result.get("error_patterns")),
            bool(result.get("stack_traces")),
            bool(result.get("analysis_summary")),
            len(result.get("analysis_summary", "")) > 100,
            result.get("confidence_score", 0) > 50
        ]
        
        return (sum(depth_factors) / len(depth_factors)) * 100
    
    def _generate_actionable_insights(self, result: Dict[str, Any]) -> List[str]:
        """Generate actionable insights from analysis"""
        insights = []
        
        error_patterns = result.get("error_patterns", [])
        stack_traces = result.get("stack_traces", [])
        
        # Pattern-based insights
        for pattern in error_patterns[:3]:  # Top 3 patterns
            pattern_text = pattern.get("pattern", "")
            if "timeout" in pattern_text.lower():
                insights.append("Consider increasing timeout values or optimizing slow operations")
            elif "memory" in pattern_text.lower() or "oom" in pattern_text.lower():
                insights.append("Investigate memory usage and consider increasing memory allocation")
            elif "connection" in pattern_text.lower():
                insights.append("Check network connectivity and connection pool configuration")
            elif "permission" in pattern_text.lower() or "access denied" in pattern_text.lower():
                insights.append("Review IAM permissions and access policies")
        
        # Stack trace insights
        for trace in stack_traces[:2]:  # Top 2 traces
            trace_text = trace.get("trace", "")
            if "NullPointerException" in trace_text:
                insights.append("Add null checks and defensive programming practices")
            elif "SQLException" in trace_text:
                insights.append("Review database queries and connection handling")
            elif "IOException" in trace_text:
                insights.append("Implement proper error handling for I/O operations")
        
        return insights[:5]  # Limit to 5 insights
    
    def _hash_content(self, content: str) -> str:
        """Generate hash for content caching"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    # Maintain backward compatibility
    def analyze(self, service_name: str, timestamp: str, log_location: str) -> Dict[str, Any]:
        """Synchronous wrapper for backward compatibility"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.analyze_async(service_name, timestamp, log_location)
            )
        finally:
            loop.close()