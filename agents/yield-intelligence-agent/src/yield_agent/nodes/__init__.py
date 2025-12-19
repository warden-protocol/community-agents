"""
================================================================================
    NODES INDEX
    LangGraph node functions for the Yield Intelligence Agent
    
    Nodes:
    - parse_input: Extract structured data from natural language
    - fetch_yields: Retrieve yield opportunities from DeFiLlama
    - find_routes: Determine bridge routes via LI.FI
    - rank_opportunities: Score and rank with recommendations
    - format_response: Generate beautiful formatted output
================================================================================
"""

from yield_agent.nodes.input_parser import (
    parse_input,
    parse_amount_and_token,
    parse_chains,
    parse_risk_tolerance,
    parse_intent,
)
from yield_agent.nodes.yield_fetcher import (
    fetch_yields,
    fetch_yields_async,
    filter_by_risk_tolerance,
    filter_by_token,
)
from yield_agent.nodes.route_finder import (
    find_routes,
    find_routes_async,
    get_route_for_chain,
    needs_bridge,
)
from yield_agent.nodes.ranking_engine import (
    rank_opportunities,
    rank_opportunities_async,
    build_recommendation,
    calculate_composite_score,
)
from yield_agent.nodes.response_formatter import (
    format_response,
    format_recommendation,
    format_summary,
    format_currency,
)

__all__ = [
    "parse_input",
    "parse_amount_and_token",
    "parse_chains",
    "parse_risk_tolerance",
    "parse_intent",
    "fetch_yields",
    "fetch_yields_async",
    "filter_by_risk_tolerance",
    "filter_by_token",
    "find_routes",
    "find_routes_async",
    "get_route_for_chain",
    "needs_bridge",
    "rank_opportunities",
    "rank_opportunities_async",
    "build_recommendation",
    "calculate_composite_score",
    "format_response",
    "format_recommendation",
    "format_summary",
    "format_currency",
]
