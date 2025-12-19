"""
================================================================================
    TOOLS INDEX
    API clients for DeFi data aggregation
    
    - DeFiLlama: Yield data from all major protocols
    - LI.FI: Cross-chain bridge routing
    - Gas: Real-time gas price estimation
================================================================================
"""

from yield_agent.tools.defillama_client import (
    DeFiLlamaClient,
    get_top_yields,
    search_yield_opportunities,
)
from yield_agent.tools.lifi_client import (
    LiFiClient,
    get_best_bridge_route,
    get_all_bridge_routes,
)
from yield_agent.tools.gas_client import (
    GasClient,
    get_gas_for_chains,
    get_cheapest_chain,
    estimate_total_entry_cost,
)

__all__ = [
    "DeFiLlamaClient",
    "get_top_yields",
    "search_yield_opportunities",
    "LiFiClient",
    "get_best_bridge_route",
    "get_all_bridge_routes",
    "GasClient",
    "get_gas_for_chains",
    "get_cheapest_chain",
    "estimate_total_entry_cost",
]
