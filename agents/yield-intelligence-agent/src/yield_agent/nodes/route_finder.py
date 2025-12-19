"""
================================================================================
    ROUTE FINDER NODE
    Determines optimal bridge routes for cross-chain yield opportunities
    
    Uses LI.FI to find the best paths between chains.
================================================================================
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from yield_agent.state import (
    AgentState,
    BridgeRoute,
    YieldOpportunity,
    SUPPORTED_CHAINS,
)
from yield_agent.tools.lifi_client import (
    LiFiClient,
    get_best_bridge_route,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


MAX_ROUTES_TO_FETCH = 10

ROUTE_CACHE_KEY = "bridge_routes"

BRIDGE_TIME_ESTIMATES: dict[str, int] = {
    "stargate": 60,
    "hop": 120,
    "across": 90,
    "cbridge": 300,
    "multichain": 600,
    "synapse": 180,
    "orbiter": 60,
    "default": 300,
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def needs_bridge(current_chain: Optional[str], target_chain: str) -> bool:
    """
    Determine if bridging is required.
    """
    if not current_chain:
        return False
    
    return current_chain.lower() != target_chain.lower()


def get_unique_target_chains(
    opportunities: list[YieldOpportunity],
    current_chain: Optional[str],
    limit: int = MAX_ROUTES_TO_FETCH,
) -> list[str]:
    """
    Get unique chains from top opportunities that need bridging.
    """
    seen: set[str] = set()
    chains: list[str] = []
    
    current_lower = current_chain.lower() if current_chain else None
    
    for opp in opportunities:
        chain = opp.chain.lower()
        
        if chain in seen:
            continue
        
        if current_lower and chain == current_lower:
            continue
        
        seen.add(chain)
        chains.append(chain)
        
        if len(chains) >= limit:
            break
    
    return chains


def estimate_bridge_time(bridge_name: str) -> int:
    """
    Estimate bridge time in seconds based on bridge protocol.
    """
    bridge_lower = bridge_name.lower()
    
    for name, time in BRIDGE_TIME_ESTIMATES.items():
        if name in bridge_lower:
            return time
    
    return BRIDGE_TIME_ESTIMATES["default"]


def create_same_chain_route(
    chain: str,
    token: str,
    amount: float,
) -> BridgeRoute:
    """
    Create a placeholder route for same-chain transactions.
    """
    chain_config = SUPPORTED_CHAINS.get(chain.lower(), {})
    chain_id = chain_config.get("chain_id", 0)
    
    return BridgeRoute(
        from_chain=chain,
        from_chain_id=chain_id,
        to_chain=chain,
        to_chain_id=chain_id,
        token=token,
        token_address="",
        amount=amount,
        bridge_name="No bridge needed",
        estimated_time_seconds=0,
        gas_cost_usd=0,
        bridge_fee_usd=0,
        total_cost_usd=0,
        estimated_output=amount,
        slippage_percent=0,
        tx_data=None,
    )


# ==============================================================================
# NODE FUNCTION
# ==============================================================================


async def find_routes_async(state: AgentState) -> dict[str, Any]:
    """
    Async implementation of route finding.
    """
    current_chain = state.current_chain
    token = state.token or "USDC"
    amount = state.amount or 1000
    opportunities = state.yield_opportunities
    
    warnings: list[str] = list(state.warnings) if state.warnings else []
    routes: list[BridgeRoute] = []
    
    if not current_chain:
        return {
            "bridge_routes": [],
            "processing_step": "routes_skipped_no_current_chain",
            "warnings": warnings,
        }
    
    if not opportunities:
        return {
            "bridge_routes": [],
            "processing_step": "routes_skipped_no_opportunities",
            "warnings": warnings,
        }
    
    target_chains = get_unique_target_chains(
        opportunities,
        current_chain,
        limit=MAX_ROUTES_TO_FETCH,
    )
    
    if not target_chains:
        same_chain_route = create_same_chain_route(
            current_chain, token, amount
        )
        return {
            "bridge_routes": [same_chain_route],
            "processing_step": "routes_same_chain",
            "warnings": warnings,
        }
    
    lifi_api_key = os.getenv("LIFI_API_KEY")
    
    try:
        async with LiFiClient(api_key=lifi_api_key) as client:
            for target_chain in target_chains:
                try:
                    route_options = await client.get_routes(
                        from_chain=current_chain,
                        to_chain=target_chain,
                        from_token=token,
                        to_token=token,
                        amount=amount,
                    )
                    
                    if route_options:
                        routes.append(route_options[0])
                    else:
                        warnings.append(
                            f"No bridge route found from {current_chain} to {target_chain}"
                        )
                        
                except Exception as e:
                    warnings.append(
                        f"Failed to get route to {target_chain}: {str(e)}"
                    )
                    continue
                    
    except Exception as e:
        return {
            "bridge_routes": [],
            "processing_step": "routes_fetch_failed",
            "error": f"Bridge routing failed: {str(e)}",
            "warnings": warnings + ["Could not connect to LI.FI API"],
        }
    
    if current_chain:
        same_chain_route = create_same_chain_route(
            current_chain, token, amount
        )
        routes.insert(0, same_chain_route)
    
    return {
        "bridge_routes": routes,
        "processing_step": "routes_found",
        "warnings": warnings,
    }


def find_routes(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Find bridge routes for cross-chain opportunities.
    
    Determines which chains need bridging and fetches optimal
    routes from LI.FI for each destination.
    """
    return asyncio.run(find_routes_async(state))


def get_route_for_chain(
    routes: list[BridgeRoute],
    target_chain: str,
) -> Optional[BridgeRoute]:
    """
    Get the bridge route for a specific target chain.
    """
    target_lower = target_chain.lower()
    
    for route in routes:
        if route.to_chain.lower() == target_lower:
            return route
    
    return None


def calculate_bridge_cost_impact(
    route: BridgeRoute,
    amount: float,
    apy: float,
) -> dict[str, float]:
    """
    Calculate how bridge costs impact effective yield.
    
    Returns:
        Dictionary with cost analysis metrics
    """
    total_cost = route.total_cost_usd
    
    cost_percent = (total_cost / amount) * 100 if amount > 0 else 0
    
    daily_yield = (apy / 365) * amount / 100
    
    days_to_recover = total_cost / daily_yield if daily_yield > 0 else float("inf")
    
    annual_cost_impact = cost_percent
    effective_first_year_apy = apy - annual_cost_impact
    
    return {
        "total_cost_usd": total_cost,
        "cost_percent": round(cost_percent, 2),
        "days_to_recover": round(days_to_recover, 1),
        "effective_first_year_apy": round(effective_first_year_apy, 2),
    }


# ==============================================================================
# TESTING UTILITY
# ==============================================================================


async def test_routes() -> None:
    """Test route finding with sample parameters."""
    print("\nTesting Route Finder")
    print("=" * 50)
    
    from yield_agent.state import AgentState, YieldOpportunity, ILRisk
    
    mock_opportunities = [
        YieldOpportunity(
            pool_id="test-1",
            protocol="Aave",
            protocol_slug="aave-v3",
            chain="arbitrum",
            pool_name="Aave USDC",
            symbol="USDC",
            apy=5.0,
            tvl_usd=100_000_000,
            risk_score=2.0,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=500,
        ),
        YieldOpportunity(
            pool_id="test-2",
            protocol="Compound",
            protocol_slug="compound-v3",
            chain="base",
            pool_name="Compound USDC",
            symbol="USDC",
            apy=4.5,
            tvl_usd=80_000_000,
            risk_score=2.5,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=400,
        ),
    ]
    
    state = AgentState(
        user_query="Where to put 10k USDC?",
        amount=10000,
        token="USDC",
        current_chain="ethereum",
        yield_opportunities=mock_opportunities,
    )
    
    result = await find_routes_async(state)
    
    routes = result.get("bridge_routes", [])
    print(f"\nFound {len(routes)} routes")
    
    for route in routes:
        print(f"\n{route.from_chain} -> {route.to_chain}")
        print(f"   Bridge: {route.bridge_name}")
        print(f"   Time: {route.estimated_time_seconds}s")
        print(f"   Cost: ${route.total_cost_usd:.2f}")
    
    if result.get("warnings"):
        print(f"\nWarnings: {result['warnings']}")


if __name__ == "__main__":
    asyncio.run(test_routes())
