"""
================================================================================
    YIELD FETCHER NODE
    Retrieves yield opportunities from DeFiLlama
    
    Fetches, filters, and prepares yield data for ranking.
================================================================================
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from yield_agent.state import (
    AgentState,
    RiskTolerance,
    YieldOpportunity,
    SUPPORTED_CHAINS,
)
from yield_agent.tools.defillama_client import (
    DeFiLlamaClient,
    get_top_yields,
    search_yield_opportunities,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


MIN_TVL_BY_RISK: dict[RiskTolerance, float] = {
    RiskTolerance.CONSERVATIVE: 10_000_000,
    RiskTolerance.MODERATE: 1_000_000,
    RiskTolerance.AGGRESSIVE: 100_000,
}

MAX_APY_BY_RISK: dict[RiskTolerance, float] = {
    RiskTolerance.CONSERVATIVE: 15.0,
    RiskTolerance.MODERATE: 50.0,
    RiskTolerance.AGGRESSIVE: 500.0,
}

MIN_APY_THRESHOLD = 0.5

MAX_POOLS_PER_CHAIN = 30

MAX_TOTAL_POOLS = 100


# ==============================================================================
# FILTER FUNCTIONS
# ==============================================================================


def filter_by_risk_tolerance(
    opportunities: list[YieldOpportunity],
    risk_tolerance: RiskTolerance,
) -> list[YieldOpportunity]:
    """
    Filter opportunities based on user's risk tolerance.
    
    Conservative: High TVL, audited protocols, lower APY cap
    Moderate: Balanced approach
    Aggressive: Accept higher risk for higher yields
    """
    min_tvl = MIN_TVL_BY_RISK.get(risk_tolerance, MIN_TVL_BY_RISK[RiskTolerance.MODERATE])
    max_apy = MAX_APY_BY_RISK.get(risk_tolerance, MAX_APY_BY_RISK[RiskTolerance.MODERATE])
    
    filtered: list[YieldOpportunity] = []
    
    for opp in opportunities:
        if opp.tvl_usd < min_tvl:
            continue
        
        if opp.apy > max_apy:
            continue
        
        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            if opp.risk_score > 4.0:
                continue
            if not opp.audited:
                continue
        
        elif risk_tolerance == RiskTolerance.MODERATE:
            if opp.risk_score > 6.0:
                continue
        
        filtered.append(opp)
    
    return filtered


def filter_by_token(
    opportunities: list[YieldOpportunity],
    token: str,
) -> list[YieldOpportunity]:
    """
    Filter opportunities that accept the specified token.
    """
    token_upper = token.upper()
    
    filtered: list[YieldOpportunity] = []
    
    for opp in opportunities:
        symbol_upper = opp.symbol.upper()
        
        if token_upper in symbol_upper:
            filtered.append(opp)
            continue
        
        if token_upper in ["USDC", "USDT", "DAI"]:
            if any(stable in symbol_upper for stable in ["USDC", "USDT", "DAI", "USD"]):
                filtered.append(opp)
                continue
        
        if token_upper in ["ETH", "WETH"]:
            if any(eth in symbol_upper for eth in ["ETH", "WETH", "STETH", "RETH"]):
                filtered.append(opp)
                continue
    
    return filtered


def filter_excluded_protocols(
    opportunities: list[YieldOpportunity],
    excluded: list[str],
) -> list[YieldOpportunity]:
    """
    Remove opportunities from excluded protocols.
    """
    if not excluded:
        return opportunities
    
    excluded_lower = [e.lower() for e in excluded]
    
    return [
        opp for opp in opportunities
        if opp.protocol.lower() not in excluded_lower
        and opp.protocol_slug not in excluded_lower
    ]


def deduplicate_opportunities(
    opportunities: list[YieldOpportunity],
) -> list[YieldOpportunity]:
    """
    Remove duplicate pools based on pool_id.
    """
    seen: set[str] = set()
    unique: list[YieldOpportunity] = []
    
    for opp in opportunities:
        if opp.pool_id not in seen:
            seen.add(opp.pool_id)
            unique.append(opp)
    
    return unique


def sort_opportunities(
    opportunities: list[YieldOpportunity],
    risk_tolerance: RiskTolerance,
) -> list[YieldOpportunity]:
    """
    Sort opportunities by a composite score.
    
    Score considers APY, TVL, and risk based on user preference.
    """
    def calculate_score(opp: YieldOpportunity) -> float:
        apy_score = min(opp.apy / 10, 10)
        
        if opp.tvl_usd >= 1_000_000_000:
            tvl_score = 10
        elif opp.tvl_usd >= 100_000_000:
            tvl_score = 8
        elif opp.tvl_usd >= 10_000_000:
            tvl_score = 6
        elif opp.tvl_usd >= 1_000_000:
            tvl_score = 4
        else:
            tvl_score = 2
        
        risk_score = 10 - opp.risk_score
        
        if risk_tolerance == RiskTolerance.CONSERVATIVE:
            return (apy_score * 0.3) + (tvl_score * 0.3) + (risk_score * 0.4)
        elif risk_tolerance == RiskTolerance.AGGRESSIVE:
            return (apy_score * 0.6) + (tvl_score * 0.2) + (risk_score * 0.2)
        else:
            return (apy_score * 0.4) + (tvl_score * 0.3) + (risk_score * 0.3)
    
    return sorted(opportunities, key=calculate_score, reverse=True)


# ==============================================================================
# NODE FUNCTION
# ==============================================================================


async def fetch_yields_async(state: AgentState) -> dict[str, Any]:
    """
    Async implementation of yield fetching.
    """
    target_chains = state.target_chains
    if not target_chains:
        target_chains = list(SUPPORTED_CHAINS.keys())
    
    risk_tolerance = state.risk_tolerance
    if isinstance(risk_tolerance, str):
        risk_tolerance = RiskTolerance(risk_tolerance)
    
    min_tvl = MIN_TVL_BY_RISK.get(risk_tolerance, 1_000_000)
    
    warnings: list[str] = []
    
    try:
        if state.token:
            opportunities = await search_yield_opportunities(
                token=state.token,
                chains=target_chains,
                min_tvl=min_tvl * 0.5,
            )
        else:
            opportunities = await get_top_yields(
                chains=target_chains,
                min_tvl=min_tvl,
                min_apy=MIN_APY_THRESHOLD,
                limit=MAX_TOTAL_POOLS,
            )
        
    except Exception as e:
        return {
            "yield_opportunities": [],
            "processing_step": "yield_fetch_failed",
            "error": f"Failed to fetch yield data: {str(e)}",
            "warnings": ["Could not connect to DeFiLlama API"],
        }
    
    if not opportunities:
        return {
            "yield_opportunities": [],
            "processing_step": "no_yields_found",
            "warnings": ["No yield opportunities found matching your criteria"],
        }
    
    opportunities = deduplicate_opportunities(opportunities)
    
    opportunities = filter_by_risk_tolerance(opportunities, risk_tolerance)
    
    if state.token:
        opportunities = filter_by_token(opportunities, state.token)
    
    if state.excluded_protocols:
        opportunities = filter_excluded_protocols(
            opportunities, state.excluded_protocols
        )
    
    opportunities = sort_opportunities(opportunities, risk_tolerance)
    
    opportunities = opportunities[:MAX_TOTAL_POOLS]
    
    if len(opportunities) == 0:
        warnings.append(
            "No opportunities match your risk tolerance. "
            "Consider adjusting your preferences."
        )
    elif len(opportunities) < 5:
        warnings.append(
            f"Only {len(opportunities)} opportunities found. "
            "Results may be limited."
        )
    
    return {
        "yield_opportunities": opportunities,
        "processing_step": "yields_fetched",
        "warnings": warnings,
    }


def fetch_yields(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Fetch yield opportunities.
    
    Retrieves yields from DeFiLlama, applies filters based on
    user preferences, and prepares data for ranking.
    """
    return asyncio.run(fetch_yields_async(state))


# ==============================================================================
# TESTING UTILITY
# ==============================================================================


async def test_fetch() -> None:
    """Test yield fetching with sample parameters."""
    print("\nTesting Yield Fetcher")
    print("=" * 50)
    
    from yield_agent.state import AgentState
    
    state = AgentState(
        user_query="Where should I put 10k USDC?",
        amount=10000,
        token="USDC",
        risk_tolerance=RiskTolerance.MODERATE,
        target_chains=["ethereum", "arbitrum", "base"],
    )
    
    result = await fetch_yields_async(state)
    
    opportunities = result.get("yield_opportunities", [])
    print(f"\nFound {len(opportunities)} opportunities")
    
    for i, opp in enumerate(opportunities[:5], 1):
        print(f"\n{i}. {opp.protocol} - {opp.symbol}")
        print(f"   Chain: {opp.chain}")
        print(f"   APY: {opp.apy:.2f}%")
        print(f"   TVL: ${opp.tvl_usd:,.0f}")
        print(f"   Risk: {opp.risk_score}/10")
    
    if result.get("warnings"):
        print(f"\nWarnings: {result['warnings']}")


if __name__ == "__main__":
    asyncio.run(test_fetch())
