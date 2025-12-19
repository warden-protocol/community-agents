"""
================================================================================
    STATE DEFINITIONS
    Core data structures for the Yield Intelligence Agent
================================================================================
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# ENUMS
# ==============================================================================


class RiskTolerance(str, Enum):
    """User's risk appetite for yield strategies."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ILRisk(str, Enum):
    """Impermanent Loss risk level for liquidity pools."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Intent(str, Enum):
    """Classified user intent types."""

    YIELD_SEARCH = "yield_search"
    COMPARE_PROTOCOLS = "compare"
    ROUTE_ONLY = "route_only"
    RISK_ANALYSIS = "risk_analysis"
    GENERAL_QUESTION = "general"


# ==============================================================================
# CHAIN CONFIGURATION
# ==============================================================================


SUPPORTED_CHAINS: dict[str, dict[str, Any]] = {
    "ethereum": {
        "chain_id": 1,
        "name": "Ethereum",
        "symbol": "ETH",
        "color": "#627EEA",
        "explorer": "https://etherscan.io",
        "defillama_slug": "Ethereum",
        "lifi_key": "ETH",
    },
    "arbitrum": {
        "chain_id": 42161,
        "name": "Arbitrum One",
        "symbol": "ETH",
        "color": "#28A0F0",
        "explorer": "https://arbiscan.io",
        "defillama_slug": "Arbitrum",
        "lifi_key": "ARB",
    },
    "optimism": {
        "chain_id": 10,
        "name": "Optimism",
        "symbol": "ETH",
        "color": "#FF0420",
        "explorer": "https://optimistic.etherscan.io",
        "defillama_slug": "Optimism",
        "lifi_key": "OPT",
    },
    "polygon": {
        "chain_id": 137,
        "name": "Polygon",
        "symbol": "MATIC",
        "color": "#8247E5",
        "explorer": "https://polygonscan.com",
        "defillama_slug": "Polygon",
        "lifi_key": "POL",
    },
    "base": {
        "chain_id": 8453,
        "name": "Base",
        "symbol": "ETH",
        "color": "#0052FF",
        "explorer": "https://basescan.org",
        "defillama_slug": "Base",
        "lifi_key": "BAS",
    },
    "avalanche": {
        "chain_id": 43114,
        "name": "Avalanche",
        "symbol": "AVAX",
        "color": "#E84142",
        "explorer": "https://snowtrace.io",
        "defillama_slug": "Avalanche",
        "lifi_key": "AVA",
    },
    "bsc": {
        "chain_id": 56,
        "name": "BNB Chain",
        "symbol": "BNB",
        "color": "#F0B90B",
        "explorer": "https://bscscan.com",
        "defillama_slug": "BSC",
        "lifi_key": "BSC",
    },
}


# ==============================================================================
# DATA MODELS
# ==============================================================================


class YieldOpportunity(BaseModel):
    """
    Represents a single yield farming opportunity.
    
    Contains all relevant metrics for evaluating and ranking
    DeFi yield opportunities across different protocols and chains.
    """

    pool_id: str = Field(..., description="Unique pool identifier")
    protocol: str = Field(..., description="Protocol name")
    protocol_slug: str = Field(..., description="Protocol slug for URLs")
    chain: str = Field(..., description="Chain identifier")
    pool_name: str = Field(..., description="Human-readable pool name")

    symbol: str = Field(..., description="Pool symbol")
    underlying_tokens: list[str] = Field(
        default_factory=list, description="Underlying token addresses"
    )
    reward_tokens: list[str] = Field(
        default_factory=list, description="Reward token symbols"
    )

    apy: float = Field(..., ge=0, description="Total APY as percentage")
    apy_base: float = Field(default=0, ge=0, description="Base APY")
    apy_reward: float = Field(default=0, ge=0, description="Reward APY")
    apy_7d_avg: Optional[float] = Field(default=None, description="7-day average APY")
    apy_30d_avg: Optional[float] = Field(default=None, description="30-day average APY")

    tvl_usd: float = Field(..., ge=0, description="Total Value Locked in USD")
    risk_score: float = Field(
        ..., ge=1, le=10, description="Risk score 1-10, lower is safer"
    )
    il_risk: ILRisk = Field(default=ILRisk.NONE, description="Impermanent loss risk")

    audited: bool = Field(default=False, description="Has security audit")
    audit_links: list[str] = Field(
        default_factory=list, description="Links to audit reports"
    )
    protocol_age_days: int = Field(
        default=0, ge=0, description="Days since protocol launch"
    )

    pool_url: Optional[str] = Field(default=None, description="Direct link to pool")
    last_updated: Optional[str] = Field(
        default=None, description="Data freshness timestamp"
    )

    class Config:
        use_enum_values = True


class BridgeRoute(BaseModel):
    """
    Represents a cross-chain bridge route.
    
    Contains routing information, cost estimates, and transaction
    data for bridging assets between chains.
    """

    from_chain: str = Field(..., description="Source chain identifier")
    from_chain_id: int = Field(..., description="Source chain ID")
    to_chain: str = Field(..., description="Destination chain identifier")
    to_chain_id: int = Field(..., description="Destination chain ID")

    token: str = Field(..., description="Token symbol being bridged")
    token_address: str = Field(..., description="Token contract address")
    amount: float = Field(..., description="Amount being bridged")

    bridge_name: str = Field(..., description="Bridge protocol name")
    estimated_time_seconds: int = Field(..., description="Estimated bridge time")

    gas_cost_usd: float = Field(..., ge=0, description="Gas cost in USD")
    bridge_fee_usd: float = Field(..., ge=0, description="Bridge fee in USD")
    total_cost_usd: float = Field(..., ge=0, description="Total cost in USD")

    estimated_output: float = Field(..., description="Expected tokens received")
    slippage_percent: float = Field(default=0.5, description="Expected slippage")

    tx_data: Optional[dict[str, Any]] = Field(
        default=None, description="Raw transaction data"
    )


class GasEstimate(BaseModel):
    """Current gas prices for a chain."""

    chain: str = Field(..., description="Chain identifier")
    chain_id: int = Field(..., description="Chain ID")

    gas_price_slow: float = Field(..., description="Slow gas price in Gwei")
    gas_price_standard: float = Field(..., description="Standard gas price in Gwei")
    gas_price_fast: float = Field(..., description="Fast gas price in Gwei")

    swap_cost_usd: float = Field(..., description="Estimated swap cost in USD")
    deposit_cost_usd: float = Field(..., description="Estimated deposit cost in USD")

    base_fee: Optional[float] = Field(default=None, description="Base fee EIP-1559")
    priority_fee: Optional[float] = Field(
        default=None, description="Priority fee EIP-1559"
    )
    last_updated: str = Field(..., description="Timestamp of gas data")


class Recommendation(BaseModel):
    """
    A ranked yield recommendation with full context.
    
    Combines yield opportunity data with user-specific calculations
    including projected earnings, route costs, and execution steps.
    """

    rank: int = Field(..., ge=1, description="Recommendation rank")
    opportunity: YieldOpportunity = Field(..., description="The yield opportunity")

    input_amount: float = Field(..., description="User input amount")
    input_token: str = Field(..., description="User input token")

    earnings_30d: float = Field(..., description="Projected 30-day earnings")
    earnings_1y: float = Field(..., description="Projected 1-year earnings")

    requires_bridge: bool = Field(default=False, description="Needs bridging")
    bridge_route: Optional[BridgeRoute] = Field(
        default=None, description="Bridge route if needed"
    )

    net_apy: float = Field(..., description="APY after costs, annualized")
    total_entry_cost_usd: float = Field(
        default=0, description="Total cost to enter position"
    )

    why_recommended: str = Field(..., description="Recommendation reasoning")
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")

    execution_steps: list[str] = Field(
        default_factory=list, description="Steps to execute"
    )


# ==============================================================================
# AGENT STATE
# ==============================================================================


class AgentState(BaseModel):
    """
    Complete state of the Yield Intelligence Agent.
    
    This state flows through the LangGraph, being updated by each node.
    Organized into logical sections: Input, Processing, Data, Output, Errors.
    """

    # --------------------------------------------------------------------------
    # INPUT FIELDS
    # --------------------------------------------------------------------------

    user_query: str = Field(..., description="Original natural language query")

    amount: Optional[float] = Field(default=None, description="Amount to invest")
    token: Optional[str] = Field(default=None, description="Token symbol")
    current_chain: Optional[str] = Field(default=None, description="User current chain")

    risk_tolerance: RiskTolerance = Field(
        default=RiskTolerance.MODERATE, description="User risk tolerance"
    )
    preferred_chains: list[str] = Field(
        default_factory=list, description="Preferred chains, empty means all"
    )
    excluded_protocols: list[str] = Field(
        default_factory=list, description="Protocols to exclude"
    )
    min_tvl: float = Field(default=100_000, description="Minimum TVL requirement")

    # --------------------------------------------------------------------------
    # PROCESSING FIELDS
    # --------------------------------------------------------------------------

    intent: Optional[Intent] = Field(default=None, description="Classified intent")
    target_chains: list[str] = Field(
        default_factory=list, description="Chains to search"
    )
    processing_step: str = Field(
        default="initialized", description="Current processing step"
    )

    # --------------------------------------------------------------------------
    # DATA COLLECTION FIELDS
    # --------------------------------------------------------------------------

    yield_opportunities: list[YieldOpportunity] = Field(
        default_factory=list, description="Raw yield opportunities"
    )
    bridge_routes: list[BridgeRoute] = Field(
        default_factory=list, description="Bridge routes from LI.FI"
    )
    gas_estimates: list[GasEstimate] = Field(
        default_factory=list, description="Gas estimates"
    )

    # --------------------------------------------------------------------------
    # OUTPUT FIELDS
    # --------------------------------------------------------------------------

    recommendations: list[Recommendation] = Field(
        default_factory=list, description="Ranked recommendations"
    )
    reasoning: str = Field(default="", description="Agent reasoning explanation")
    execution_steps: list[str] = Field(
        default_factory=list, description="Execution steps"
    )
    warnings: list[str] = Field(default_factory=list, description="Risk warnings")

    formatted_response: str = Field(
        default="", description="Final formatted response"
    )

    # --------------------------------------------------------------------------
    # ERROR HANDLING
    # --------------------------------------------------------------------------

    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_details: Optional[dict[str, Any]] = Field(
        default=None, description="Detailed error information"
    )

    class Config:
        use_enum_values = True


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================


def merge_opportunities(
    existing: list[YieldOpportunity], new: list[YieldOpportunity]
) -> list[YieldOpportunity]:
    """Merge yield opportunities, avoiding duplicates by pool_id."""
    seen_ids = {opp.pool_id for opp in existing}
    merged = list(existing)
    for opp in new:
        if opp.pool_id not in seen_ids:
            merged.append(opp)
            seen_ids.add(opp.pool_id)
    return merged


def merge_warnings(existing: list[str], new: list[str]) -> list[str]:
    """Merge warnings, avoiding duplicates while preserving order."""
    return list(dict.fromkeys(existing + new))


def get_chain_by_id(chain_id: int) -> Optional[dict[str, Any]]:
    """Get chain configuration by chain ID."""
    for key, config in SUPPORTED_CHAINS.items():
        if config["chain_id"] == chain_id:
            return {"key": key, **config}
    return None


def get_chain_by_name(name: str) -> Optional[dict[str, Any]]:
    """Get chain configuration by name or key."""
    name_lower = name.lower()
    if name_lower in SUPPORTED_CHAINS:
        return {"key": name_lower, **SUPPORTED_CHAINS[name_lower]}
    for key, config in SUPPORTED_CHAINS.items():
        if config["name"].lower() == name_lower:
            return {"key": key, **config}
    return None
