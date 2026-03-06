"""
Agent Module

Contains all specialized agents for incident response.
"""

# Import existing agents if they exist
try:
    from agents.log_analysis_agent import LogAnalysisAgent
except ImportError:
    LogAnalysisAgent = None

try:
    from agents.communication_agent import CommunicationAgent
except ImportError:
    CommunicationAgent = None

try:
    from agents.fix_recommendation_agent import FixRecommendationAgent
except ImportError:
    FixRecommendationAgent = None

try:
    from agents.root_cause_classifier import classify_failure
except ImportError:
    classify_failure = None

try:
    from agents.kb_query import query_similar_incidents
except ImportError:
    query_similar_incidents = None

# Import enhanced agents
try:
    from agents.enhanced_log_analysis_agent import EnhancedLogAnalysisAgent
except ImportError:
    EnhancedLogAnalysisAgent = None

__all__ = [
    'LogAnalysisAgent',
    'CommunicationAgent', 
    'FixRecommendationAgent',
    'classify_failure',
    'query_similar_incidents',
    'EnhancedLogAnalysisAgent'
]