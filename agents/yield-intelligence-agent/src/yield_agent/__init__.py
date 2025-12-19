"""
================================================================================
    WARDEN YIELD INTELLIGENCE AGENT
    Cross-Chain DeFi Yield Discovery & Optimization
    
    Built for Warden Protocol Agent Builder Incentive Programme
================================================================================
"""

__version__ = "1.0.0"
__author__ = "Ludarep"
__description__ = "Cross-Chain Yield Intelligence Agent for Warden Protocol"

from yield_agent.state import (
    AgentState,
    YieldOpportunity,
    BridgeRoute,
    GasEstimate,
    Recommendation,
    RiskTolerance,
)

__all__ = [
    "AgentState",
    "YieldOpportunity",
    "BridgeRoute",
    "GasEstimate",
    "Recommendation",
    "RiskTolerance",
    "__version__",
]
