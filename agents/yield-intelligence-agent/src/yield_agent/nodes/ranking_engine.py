"""
================================================================================
    RANKING ENGINE NODE
    Scores and ranks yield opportunities with full context
    
    Combines yield data, bridge costs, and gas estimates into
    final ranked recommendations.
================================================================================
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from yield_agent.state import (
    AgentState,
    BridgeRoute,
    GasEstimate,
    Recommendation,
    RiskTolerance,
    YieldOpportunity,
    SUPPORTED_CHAINS,
)
from yield_agent.tools.gas_client import (
    GasClient,
    get_gas_for_chains,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


MAX_RECOMMENDATIONS = 10

WEIGHT_PROFILES: dict[RiskTolerance, dict[str, float]] = {
    RiskTolerance.CONSERVATIVE: {
        "apy": 0.25,
        "tvl": 0.25,
        "risk": 0.30,
        "cost": 0.20,
    },
    RiskTolerance.MODERATE: {
        "apy": 0.35,
        "tvl": 0.20,
        "risk": 0.25,
        "cost": 0.20,
    },
    RiskTolerance.AGGRESSIVE: {
        "apy": 0.50,
        "tvl": 0.15,
        "risk": 0.15,
        "cost": 0.20,
    },
}

TVL_TIERS = [
    (1_000_000_000, 10),
    (500_000_000, 9),
    (100_000_000, 8),
    (50_000_000, 7),
    (10_000_000, 6),
    (5_000_000, 5),
    (1_000_000, 4),
    (500_000, 3),
    (100_000, 2),
    (0, 1),
]


# ==============================================================================
# SCORING FUNCTIONS
# ==============================================================================


def calculate_apy_score(apy: float, risk_tolerance: RiskTolerance) -> float:
    """
    Score APY on a 0-10 scale.
    """
    if risk_tolerance == RiskTolerance.CONSERVATIVE:
        if apy > 15:
            return 8 + min((apy - 15) / 10, 2)
        return min(apy / 1.5, 10)
    
    elif risk_tolerance == RiskTolerance.AGGRESSIVE:
        if apy > 50:
            return 9 + min((apy - 50) / 50, 1)
        return min(apy / 5, 10)
    
    else:
        if apy > 30:
            return 8 + min((apy - 30) / 20, 2)
        return min(apy / 3, 10)


def calculate_tvl_score(tvl: float) -> float:
    """
    Score TVL on a 0-10 scale.
    """
    for threshold, score in TVL_TIERS:
        if tvl >= threshold:
            return score
    return 1


def calculate_risk_score(
    opportunity: YieldOpportunity,
    risk_tolerance: RiskTolerance,
) -> float:
    """
    Score risk on a 0-10 scale (higher is better/safer).
    """
    base_score = 10 - opportunity.risk_score
    
    if opportunity.audited:
        base_score += 1.0
    
    if opportunity.protocol_age_days > 365:
        base_score += 0.5
    elif opportunity.protocol_age_days > 730:
        base_score += 1.0
    
    if risk_tolerance == RiskTolerance.CONSERVATIVE:
        if not opportunity.audited:
            base_score -= 2.0
    
    return max(0, min(10, base_score))


def calculate_cost_score(
    opportunity: YieldOpportunity,
    bridge_route: Optional[BridgeRoute],
    gas_estimate: Optional[GasEstimate],
    amount: float,
) -> float:
    """
    Score entry costs on a 0-10 scale (higher is better/cheaper).
    """
    total_cost = 0.0
    
    if bridge_route and bridge_route.bridge_name != "No bridge needed":
        total_cost += bridge_route.total_cost_usd
    
    if gas_estimate:
        total_cost += gas_estimate.deposit_cost_usd
        total_cost += gas_estimate.swap_cost_usd * 0.5
    else:
        total_cost += 5.0
    
    if amount <= 0:
        return 5.0
    
    cost_percent = (total_cost / amount) * 100
    
    if cost_percent <= 0.1:
        return 10.0
    elif cost_percent <= 0.5:
        return 9.0
    elif cost_percent <= 1.0:
        return 8.0
    elif cost_percent <= 2.0:
        return 7.0
    elif cost_percent <= 5.0:
        return 5.0
    elif cost_percent <= 10.0:
        return 3.0
    else:
        return 1.0


def calculate_composite_score(
    apy_score: float,
    tvl_score: float,
    risk_score: float,
    cost_score: float,
    risk_tolerance: RiskTolerance,
) -> float:
    """
    Calculate weighted composite score.
    """
    weights = WEIGHT_PROFILES.get(
        risk_tolerance,
        WEIGHT_PROFILES[RiskTolerance.MODERATE],
    )
    
    composite = (
        apy_score * weights["apy"]
        + tvl_score * weights["tvl"]
        + risk_score * weights["risk"]
        + cost_score * weights["cost"]
    )
    
    return round(composite, 2)


# ==============================================================================
# RECOMMENDATION BUILDER
# ==============================================================================


def _generate_reasoning(
    opportunity: YieldOpportunity,
    requires_bridge: bool,
    bridge_route: Optional[BridgeRoute],
    entry_cost: float,
    risk_tolerance: RiskTolerance,
) -> str:
    """
    Generate human-readable reasoning for the recommendation.
    """
    reasons = []
    
    reasons.append(
        f"{opportunity.protocol} offers {opportunity.apy:.2f}% APY "
        f"on {opportunity.chain.title()}"
    )
    
    if opportunity.tvl_usd >= 100_000_000:
        reasons.append(
            f"High liquidity with ${opportunity.tvl_usd / 1_000_000:.0f}M TVL"
        )
    elif opportunity.tvl_usd >= 10_000_000:
        reasons.append(
            f"Good liquidity with ${opportunity.tvl_usd / 1_000_000:.1f}M TVL"
        )
    
    if opportunity.audited:
        reasons.append("Protocol is audited")
    
    if opportunity.protocol_age_days > 365:
        years = opportunity.protocol_age_days / 365
        reasons.append(f"Established protocol ({years:.1f} years)")
    
    if requires_bridge and bridge_route:
        reasons.append(
            f"Requires bridging via {bridge_route.bridge_name} "
            f"(~{bridge_route.estimated_time_seconds // 60} min, ${bridge_route.total_cost_usd:.2f})"
        )
    
    return ". ".join(reasons) + "."


def _generate_warnings(
    opportunity: YieldOpportunity,
    requires_bridge: bool,
    bridge_route: Optional[BridgeRoute],
    amount: float,
) -> list[str]:
    """
    Generate risk warnings for the recommendation.
    """
    warnings = []
    
    if opportunity.risk_score >= 7:
        warnings.append("High risk score - proceed with caution")
    
    if not opportunity.audited:
        warnings.append("Protocol has not been audited")
    
    if opportunity.tvl_usd < 1_000_000:
        warnings.append("Low TVL - potential liquidity concerns")
    
    if opportunity.apy > 50:
        warnings.append("Very high APY may not be sustainable")
    
    if str(opportunity.il_risk) in ["medium", "high", "ILRisk.MEDIUM", "ILRisk.HIGH"]:
        warnings.append(f"Impermanent loss risk: {opportunity.il_risk}")
    
    if requires_bridge and bridge_route:
        cost_percent = (bridge_route.total_cost_usd / amount) * 100 if amount > 0 else 0
        if cost_percent > 2:
            warnings.append(
                f"Bridge cost is {cost_percent:.1f}% of investment"
            )
    
    return warnings


def _generate_execution_steps(
    opportunity: YieldOpportunity,
    requires_bridge: bool,
    bridge_route: Optional[BridgeRoute],
    token: str,
    amount: float,
) -> list[str]:
    """
    Generate step-by-step execution instructions.
    """
    steps = []
    step_num = 1
    
    if requires_bridge and bridge_route:
        steps.append(
            f"{step_num}. Bridge {amount:,.2f} {token} from "
            f"{bridge_route.from_chain.title()} to {bridge_route.to_chain.title()} "
            f"using {bridge_route.bridge_name}"
        )
        step_num += 1
        
        steps.append(
            f"{step_num}. Wait for bridge confirmation (~{bridge_route.estimated_time_seconds // 60} minutes)"
        )
        step_num += 1
    
    steps.append(
        f"{step_num}. Go to {opportunity.protocol} on {opportunity.chain.title()}"
    )
    step_num += 1
    
    if opportunity.pool_url:
        steps.append(
            f"{step_num}. Navigate to the {opportunity.symbol} pool"
        )
    else:
        steps.append(
            f"{step_num}. Find the {opportunity.symbol} pool"
        )
    step_num += 1
    
    steps.append(
        f"{step_num}. Approve {token} spending (one-time transaction)"
    )
    step_num += 1
    
    steps.append(
        f"{step_num}. Deposit {amount:,.2f} {token} into the pool"
    )
    step_num += 1
    
    steps.append(
        f"{step_num}. Confirm transaction and start earning {opportunity.apy:.2f}% APY"
    )
    
    return steps


def build_recommendation(
    rank: int,
    opportunity: YieldOpportunity,
    amount: float,
    token: str,
    bridge_route: Optional[BridgeRoute],
    gas_estimate: Optional[GasEstimate],
    risk_tolerance: RiskTolerance,
) -> Recommendation:
    """
    Build a complete recommendation with projections and reasoning.
    """
    requires_bridge = (
        bridge_route is not None
        and bridge_route.bridge_name != "No bridge needed"
    )
    
    entry_cost = 0.0
    if requires_bridge and bridge_route:
        entry_cost += bridge_route.total_cost_usd
    if gas_estimate:
        entry_cost += gas_estimate.deposit_cost_usd
    
    earnings_1y = (opportunity.apy / 100) * amount
    earnings_30d = earnings_1y / 12
    
    cost_impact_percent = (entry_cost / amount) * 100 if amount > 0 else 0
    net_apy = opportunity.apy - cost_impact_percent
    
    why = _generate_reasoning(
        opportunity,
        requires_bridge,
        bridge_route,
        entry_cost,
        risk_tolerance,
    )
    
    warnings = _generate_warnings(
        opportunity,
        requires_bridge,
        bridge_route,
        amount,
    )
    
    steps = _generate_execution_steps(
        opportunity,
        requires_bridge,
        bridge_route,
        token,
        amount,
    )
    
    return Recommendation(
        rank=rank,
        opportunity=opportunity,
        input_amount=amount,
        input_token=token,
        earnings_30d=round(earnings_30d, 2),
        earnings_1y=round(earnings_1y, 2),
        requires_bridge=requires_bridge,
        bridge_route=bridge_route if requires_bridge else None,
        net_apy=round(net_apy, 2),
        total_entry_cost_usd=round(entry_cost, 2),
        why_recommended=why,
        warnings=warnings,
        execution_steps=steps,
    )


# ==============================================================================
# NODE FUNCTION
# ==============================================================================


async def rank_opportunities_async(state: AgentState) -> dict[str, Any]:
    """
    Async implementation of opportunity ranking.
    """
    opportunities = state.yield_opportunities
    bridge_routes = state.bridge_routes
    amount = state.amount or 1000
    token = state.token or "USDC"
    current_chain = state.current_chain
    
    risk_tolerance = state.risk_tolerance
    if isinstance(risk_tolerance, str):
        risk_tolerance = RiskTolerance(risk_tolerance)
    
    warnings: list[str] = list(state.warnings) if state.warnings else []
    
    if not opportunities:
        return {
            "recommendations": [],
            "processing_step": "ranking_skipped_no_opportunities",
            "warnings": warnings + ["No opportunities to rank"],
        }
    
    unique_chains = list(set(opp.chain for opp in opportunities))
    
    try:
        gas_estimates = await get_gas_for_chains(
            chains=unique_chains,
            api_key=os.getenv("BLOCKNATIVE_API_KEY"),
        )
    except Exception:
        gas_estimates = {}
        warnings.append("Could not fetch gas estimates")
    
    route_map: dict[str, BridgeRoute] = {}
    for route in bridge_routes:
        route_map[route.to_chain.lower()] = route
    
    scored_opportunities: list[tuple[float, YieldOpportunity]] = []
    
    for opp in opportunities:
        chain_lower = opp.chain.lower()
        
        bridge_route = route_map.get(chain_lower)
        gas_estimate = gas_estimates.get(chain_lower)
        
        apy_score = calculate_apy_score(opp.apy, risk_tolerance)
        tvl_score = calculate_tvl_score(opp.tvl_usd)
        risk_score = calculate_risk_score(opp, risk_tolerance)
        cost_score = calculate_cost_score(opp, bridge_route, gas_estimate, amount)
        
        composite = calculate_composite_score(
            apy_score, tvl_score, risk_score, cost_score, risk_tolerance
        )
        
        scored_opportunities.append((composite, opp))
    
    scored_opportunities.sort(key=lambda x: x[0], reverse=True)
    
    recommendations: list[Recommendation] = []
    
    for rank, (score, opp) in enumerate(scored_opportunities[:MAX_RECOMMENDATIONS], 1):
        chain_lower = opp.chain.lower()
        bridge_route = route_map.get(chain_lower)
        gas_estimate = gas_estimates.get(chain_lower)
        
        rec = build_recommendation(
            rank=rank,
            opportunity=opp,
            amount=amount,
            token=token,
            bridge_route=bridge_route,
            gas_estimate=gas_estimate,
            risk_tolerance=risk_tolerance,
        )
        
        recommendations.append(rec)
    
    return {
        "recommendations": recommendations,
        "gas_estimates": list(gas_estimates.values()),
        "processing_step": "ranking_complete",
        "warnings": warnings,
    }


def rank_opportunities(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Rank opportunities and build recommendations.
    
    Scores each opportunity based on APY, TVL, risk, and costs,
    then builds detailed recommendations with execution steps.
    """
    return asyncio.run(rank_opportunities_async(state))


# ==============================================================================
# TESTING UTILITY
# ==============================================================================


async def test_ranking() -> None:
    """Test ranking with sample data."""
    print("\nTesting Ranking Engine")
    print("=" * 50)
    
    from yield_agent.state import AgentState, YieldOpportunity, ILRisk
    
    mock_opportunities = [
        YieldOpportunity(
            pool_id="aave-usdc-arb",
            protocol="Aave v3",
            protocol_slug="aave-v3",
            chain="arbitrum",
            pool_name="Aave USDC",
            symbol="USDC",
            apy=5.2,
            tvl_usd=150_000_000,
            risk_score=2.0,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=600,
        ),
        YieldOpportunity(
            pool_id="compound-usdc-base",
            protocol="Compound v3",
            protocol_slug="compound-v3",
            chain="base",
            pool_name="Compound USDC",
            symbol="USDC",
            apy=4.8,
            tvl_usd=80_000_000,
            risk_score=2.5,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=500,
        ),
        YieldOpportunity(
            pool_id="new-protocol-usdc",
            protocol="NewYield",
            protocol_slug="newyield",
            chain="arbitrum",
            pool_name="NewYield USDC",
            symbol="USDC",
            apy=15.0,
            tvl_usd=5_000_000,
            risk_score=6.0,
            il_risk=ILRisk.NONE,
            audited=False,
            protocol_age_days=90,
        ),
    ]
    
    state = AgentState(
        user_query="Where to put 10k USDC?",
        amount=10000,
        token="USDC",
        current_chain="ethereum",
        risk_tolerance=RiskTolerance.MODERATE,
        yield_opportunities=mock_opportunities,
        bridge_routes=[],
    )
    
    result = await rank_opportunities_async(state)
    
    recommendations = result.get("recommendations", [])
    print(f"\nGenerated {len(recommendations)} recommendations")
    
    for rec in recommendations:
        print(f"\n#{rec.rank} {rec.opportunity.protocol} - {rec.opportunity.symbol}")
        print(f"   Chain: {rec.opportunity.chain}")
        print(f"   APY: {rec.opportunity.apy:.2f}% (Net: {rec.net_apy:.2f}%)")
        print(f"   30d Earnings: ${rec.earnings_30d:.2f}")
        print(f"   1y Earnings: ${rec.earnings_1y:.2f}")
        print(f"   Entry Cost: ${rec.total_entry_cost_usd:.2f}")
        print(f"   Reasoning: {rec.why_recommended[:100]}...")
        if rec.warnings:
            print(f"   Warnings: {rec.warnings}")


if __name__ == "__main__":
    asyncio.run(test_ranking())
