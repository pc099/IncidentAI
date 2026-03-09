"""Lambda configuration for cost efficiency."""

# Lambda runtime configuration for cost optimization
LAMBDA_RUNTIME_CONFIG = {
    # Use ARM-based (Graviton2) runtime for cost efficiency
    # ARM provides up to 34% better price performance than x86
    "runtime": "python3.11",
    "architecture": "arm64",  # Graviton2 architecture
    
    # Memory allocation recommendations based on profiling
    # These values should be adjusted based on actual usage patterns
    "memory_allocations": {
        "api_validator": 256,  # Minimal memory for request validation
        "log_analysis_agent": 1024,  # Moderate memory for log parsing
        "root_cause_agent": 512,  # Moderate memory for classification
        "fix_recommendation_agent": 512,  # Moderate memory for fix generation
        "communication_agent": 256,  # Minimal memory for summary formatting
        "orchestrator": 512,  # Moderate memory for coordination
        "alert_delivery": 256,  # Minimal memory for email sending
        "incident_storage": 256,  # Minimal memory for DynamoDB writes
    },
    
    # Timeout configuration (in seconds)
    "timeouts": {
        "api_validator": 10,
        "log_analysis_agent": 60,
        "root_cause_agent": 30,
        "fix_recommendation_agent": 30,
        "communication_agent": 15,
        "orchestrator": 300,  # 5 minutes for full orchestration
        "alert_delivery": 30,
        "incident_storage": 15,
    },
    
    # Environment variables for cost tracking
    "environment": {
        "ENABLE_COST_TRACKING": "true",
        "ENABLE_METRICS": "true",
        "LOG_LEVEL": "INFO",  # Reduce logging overhead
    }
}


def get_lambda_config(function_name: str) -> dict:
    """
    Get Lambda configuration for a specific function.
    
    Args:
        function_name: Name of the Lambda function
        
    Returns:
        dict: Lambda configuration including runtime, memory, timeout
    """
    return {
        "runtime": LAMBDA_RUNTIME_CONFIG["runtime"],
        "architecture": LAMBDA_RUNTIME_CONFIG["architecture"],
        "memory": LAMBDA_RUNTIME_CONFIG["memory_allocations"].get(function_name, 512),
        "timeout": LAMBDA_RUNTIME_CONFIG["timeouts"].get(function_name, 30),
        "environment": LAMBDA_RUNTIME_CONFIG["environment"]
    }


def get_cost_optimization_recommendations() -> dict:
    """
    Get cost optimization recommendations for Lambda functions.
    
    Returns:
        dict: Cost optimization recommendations
    """
    return {
        "runtime": {
            "recommendation": "Use ARM-based (Graviton2) runtime",
            "benefit": "Up to 34% better price performance than x86",
            "current": LAMBDA_RUNTIME_CONFIG["architecture"]
        },
        "memory": {
            "recommendation": "Right-size memory allocation based on profiling",
            "benefit": "Pay only for memory you use, reduce over-provisioning",
            "note": "Monitor CloudWatch metrics to optimize memory allocation"
        },
        "timeout": {
            "recommendation": "Set appropriate timeouts to avoid unnecessary charges",
            "benefit": "Prevent runaway functions from incurring costs",
            "note": "Monitor execution times and adjust timeouts accordingly"
        },
        "concurrency": {
            "recommendation": "Use reserved concurrency for critical functions",
            "benefit": "Prevent throttling and ensure predictable costs",
            "note": "Set reserved concurrency based on expected load"
        },
        "cold_starts": {
            "recommendation": "Use provisioned concurrency for latency-sensitive functions",
            "benefit": "Eliminate cold starts at the cost of higher baseline charges",
            "note": "Only use for functions with strict latency requirements"
        }
    }


def calculate_estimated_cost(
    invocations_per_month: int,
    avg_duration_ms: int,
    memory_mb: int,
    architecture: str = "arm64"
) -> dict:
    """
    Calculate estimated monthly cost for a Lambda function.
    
    Args:
        invocations_per_month: Number of invocations per month
        avg_duration_ms: Average duration in milliseconds
        memory_mb: Memory allocation in MB
        architecture: Architecture (arm64 or x86_64)
        
    Returns:
        dict: Cost breakdown
    """
    # AWS Lambda pricing (as of 2024, subject to change)
    # Free Tier: 1M requests + 400,000 GB-seconds per month
    
    # Request pricing
    request_price_per_million = 0.20  # $0.20 per 1M requests
    
    # Compute pricing (per GB-second)
    if architecture == "arm64":
        compute_price_per_gb_second = 0.0000133334  # ARM pricing
    else:
        compute_price_per_gb_second = 0.0000166667  # x86 pricing
    
    # Calculate costs
    free_tier_requests = 1_000_000
    free_tier_gb_seconds = 400_000
    
    # Request cost
    billable_requests = max(0, invocations_per_month - free_tier_requests)
    request_cost = (billable_requests / 1_000_000) * request_price_per_million
    
    # Compute cost
    duration_seconds = avg_duration_ms / 1000
    memory_gb = memory_mb / 1024
    gb_seconds = invocations_per_month * duration_seconds * memory_gb
    billable_gb_seconds = max(0, gb_seconds - free_tier_gb_seconds)
    compute_cost = billable_gb_seconds * compute_price_per_gb_second
    
    total_cost = request_cost + compute_cost
    
    return {
        "invocations": invocations_per_month,
        "avg_duration_ms": avg_duration_ms,
        "memory_mb": memory_mb,
        "architecture": architecture,
        "request_cost": round(request_cost, 4),
        "compute_cost": round(compute_cost, 4),
        "total_cost": round(total_cost, 4),
        "free_tier_used": {
            "requests": min(invocations_per_month, free_tier_requests),
            "gb_seconds": min(gb_seconds, free_tier_gb_seconds)
        },
        "savings_vs_x86": round(
            (compute_cost * 0.20) if architecture == "arm64" else 0, 4
        )  # ARM provides ~20% cost savings
    }


def optimize_memory_allocation(
    current_memory_mb: int,
    max_memory_used_mb: int,
    buffer_percentage: float = 0.20
) -> dict:
    """
    Recommend optimal memory allocation based on usage.
    
    Args:
        current_memory_mb: Current memory allocation
        max_memory_used_mb: Maximum memory used during execution
        buffer_percentage: Buffer percentage to add (default 20%)
        
    Returns:
        dict: Memory optimization recommendation
    """
    # Add buffer to max memory used
    recommended_memory = int(max_memory_used_mb * (1 + buffer_percentage))
    
    # Round up to nearest 64 MB (Lambda memory increments)
    recommended_memory = ((recommended_memory + 63) // 64) * 64
    
    # Ensure minimum 128 MB
    recommended_memory = max(128, recommended_memory)
    
    # Calculate potential savings
    if recommended_memory < current_memory_mb:
        savings_percentage = ((current_memory_mb - recommended_memory) / current_memory_mb) * 100
        action = "reduce"
    elif recommended_memory > current_memory_mb:
        savings_percentage = 0
        action = "increase"
    else:
        savings_percentage = 0
        action = "no_change"
    
    return {
        "current_memory_mb": current_memory_mb,
        "max_memory_used_mb": max_memory_used_mb,
        "recommended_memory_mb": recommended_memory,
        "action": action,
        "potential_savings_percentage": round(savings_percentage, 2),
        "note": f"Recommendation includes {int(buffer_percentage * 100)}% buffer for safety"
    }
