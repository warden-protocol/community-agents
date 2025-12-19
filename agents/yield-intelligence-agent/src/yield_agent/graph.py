"""
================================================================================
    LANGGRAPH DEFINITION
    Core agent graph that orchestrates the yield intelligence workflow
    
    Graph Flow:
    START -> parse_input -> fetch_yields -> find_routes -> rank -> format -> END
================================================================================
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import StateGraph, END

from yield_agent.state import AgentState, Intent
from yield_agent.nodes import (
    parse_input,
    fetch_yields,
    find_routes,
    rank_opportunities,
    format_response,
)


# ==============================================================================
# ROUTING FUNCTIONS
# ==============================================================================


def route_by_intent(state: AgentState) -> Literal["fetch_yields", "find_routes_only", "error"]:
    """
    Route based on classified intent.
    
    - YIELD_SEARCH, COMPARE_PROTOCOLS, RISK_ANALYSIS -> fetch_yields
    - ROUTE_ONLY -> find_routes_only
    - Error cases -> error
    """
    if state.error:
        return "error"
    
    intent = state.intent
    
    if intent == Intent.ROUTE_ONLY:
        return "find_routes_only"
    
    return "fetch_yields"


def should_find_routes(state: AgentState) -> Literal["find_routes", "skip_routes"]:
    """
    Determine if bridge route finding is needed.
    
    Skip if:
    - No current chain specified
    - No yield opportunities found
    - Error occurred
    """
    if state.error:
        return "skip_routes"
    
    if not state.current_chain:
        return "skip_routes"
    
    if not state.yield_opportunities:
        return "skip_routes"
    
    return "find_routes"


def should_continue_to_ranking(state: AgentState) -> Literal["rank", "skip_rank"]:
    """
    Determine if ranking should proceed.
    """
    if state.error:
        return "skip_rank"
    
    if not state.yield_opportunities:
        return "skip_rank"
    
    return "rank"


# ==============================================================================
# ERROR HANDLER NODE
# ==============================================================================


def handle_error(state: AgentState) -> dict[str, Any]:
    """
    Handle error states gracefully.
    """
    error_msg = state.error or "An unknown error occurred"
    
    return {
        "formatted_response": f"Error: {error_msg}",
        "processing_step": "error_handled",
    }


# ==============================================================================
# ROUTE-ONLY NODE
# ==============================================================================


def find_routes_only(state: AgentState) -> dict[str, Any]:
    """
    Handle route-only queries without yield fetching.
    """
    from yield_agent.nodes.route_finder import find_routes_async
    import asyncio
    
    if not state.current_chain:
        return {
            "error": "Please specify your current chain for routing",
            "processing_step": "route_only_no_chain",
        }
    
    if not state.preferred_chains:
        return {
            "error": "Please specify a destination chain",
            "processing_step": "route_only_no_destination",
        }
    
    return asyncio.run(find_routes_async(state))


def format_route_response(state: AgentState) -> dict[str, Any]:
    """
    Format response for route-only queries.
    """
    routes = state.bridge_routes
    
    if not routes:
        return {
            "formatted_response": "No bridge routes found for your request.",
            "processing_step": "route_format_no_routes",
        }
    
    lines = [
        "",
        "=" * 70,
        "  BRIDGE ROUTE FINDER",
        "=" * 70,
        "",
    ]
    
    for route in routes:
        if route.bridge_name == "No bridge needed":
            continue
            
        lines.extend([
            f"  {route.from_chain.title()} -> {route.to_chain.title()}",
            f"  Bridge:    {route.bridge_name}",
            f"  Amount:    {route.amount:,.2f} {route.token}",
            f"  Output:    {route.estimated_output:,.2f} {route.token}",
            f"  Time:      ~{route.estimated_time_seconds // 60} minutes",
            f"  Gas Cost:  ${route.gas_cost_usd:.2f}",
            f"  Fee:       ${route.bridge_fee_usd:.2f}",
            f"  Total:     ${route.total_cost_usd:.2f}",
            "",
            "-" * 70,
        ])
    
    lines.extend([
        "",
        "=" * 70,
        "",
    ])
    
    return {
        "formatted_response": "\n".join(lines),
        "processing_step": "route_format_complete",
    }


# ==============================================================================
# GRAPH BUILDER
# ==============================================================================


def create_yield_agent() -> StateGraph:
    """
    Create the LangGraph StateGraph for the Yield Intelligence Agent.
    
    Returns a compiled graph ready for invocation.
    """
    graph = StateGraph(AgentState)
    
    graph.add_node("parse_input", parse_input)
    graph.add_node("fetch_yields", fetch_yields)
    graph.add_node("find_routes", find_routes)
    graph.add_node("rank_opportunities", rank_opportunities)
    graph.add_node("format_response", format_response)
    graph.add_node("handle_error", handle_error)
    graph.add_node("find_routes_only", find_routes_only)
    graph.add_node("format_route_response", format_route_response)
    
    graph.set_entry_point("parse_input")
    
    graph.add_conditional_edges(
        "parse_input",
        route_by_intent,
        {
            "fetch_yields": "fetch_yields",
            "find_routes_only": "find_routes_only",
            "error": "handle_error",
        },
    )
    
    graph.add_conditional_edges(
        "fetch_yields",
        should_find_routes,
        {
            "find_routes": "find_routes",
            "skip_routes": "rank_opportunities",
        },
    )
    
    graph.add_edge("find_routes", "rank_opportunities")
    
    graph.add_conditional_edges(
        "rank_opportunities",
        should_continue_to_ranking,
        {
            "rank": "format_response",
            "skip_rank": "format_response",
        },
    )
    
    graph.add_edge("format_response", END)
    
    graph.add_edge("find_routes_only", "format_route_response")
    graph.add_edge("format_route_response", END)
    
    graph.add_edge("handle_error", END)
    
    return graph.compile()


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


def run_agent(query: str, **kwargs) -> str:
    """
    Run the yield agent with a natural language query.
    
    Args:
        query: Natural language question about yields
        **kwargs: Optional overrides (amount, token, current_chain, etc.)
        
    Returns:
        Formatted response string
    """
    agent = create_yield_agent()
    
    initial_state = AgentState(
        user_query=query,
        amount=kwargs.get("amount"),
        token=kwargs.get("token"),
        current_chain=kwargs.get("current_chain"),
        risk_tolerance=kwargs.get("risk_tolerance", "moderate"),
        preferred_chains=kwargs.get("preferred_chains", []),
        excluded_protocols=kwargs.get("excluded_protocols", []),
        min_tvl=kwargs.get("min_tvl", 100_000),
    )
    
    final_state = agent.invoke(initial_state)
    
    return final_state.get("formatted_response", "No response generated")


async def run_agent_async(query: str, **kwargs) -> str:
    """
    Run the yield agent asynchronously.
    
    Args:
        query: Natural language question about yields
        **kwargs: Optional overrides
        
    Returns:
        Formatted response string
    """
    agent = create_yield_agent()
    
    initial_state = AgentState(
        user_query=query,
        amount=kwargs.get("amount"),
        token=kwargs.get("token"),
        current_chain=kwargs.get("current_chain"),
        risk_tolerance=kwargs.get("risk_tolerance", "moderate"),
        preferred_chains=kwargs.get("preferred_chains", []),
        excluded_protocols=kwargs.get("excluded_protocols", []),
        min_tvl=kwargs.get("min_tvl", 100_000),
    )
    
    final_state = await agent.ainvoke(initial_state)
    
    return final_state.get("formatted_response", "No response generated")


def get_graph_visualization() -> str:
    """
    Get a text representation of the graph structure.
    """
    return """
    YIELD INTELLIGENCE AGENT - GRAPH STRUCTURE
    ==========================================
    
                    +-------------+
                    |    START    |
                    +------+------+
                           |
                           v
                    +-------------+
                    | parse_input |
                    +------+------+
                           |
              +------------+------------+
              |                         |
              v                         v
       +-------------+          +----------------+
       | fetch_yields|          | find_routes_only|
       +------+------+          +--------+-------+
              |                          |
              v                          v
       +-------------+          +------------------+
       | find_routes |          |format_route_resp |
       +------+------+          +--------+---------+
              |                          |
              v                          |
       +-----------------+               |
       | rank_opportunities|             |
       +--------+--------+               |
                |                        |
                v                        |
       +----------------+                |
       | format_response|                |
       +--------+-------+                |
                |                        |
                +------------+-----------+
                             |
                             v
                       +----------+
                       |   END    |
                       +----------+
    """


# ==============================================================================
# TESTING
# ==============================================================================


def test_graph() -> None:
    """Test the graph with a sample query."""
    print("\nTesting Yield Intelligence Agent")
    print("=" * 50)
    
    print("\nGraph Structure:")
    print(get_graph_visualization())
    
    print("\nRunning test query...")
    print("-" * 50)
    
    response = run_agent(
        query="Where should I put 10k USDC for the best yield?",
        amount=10000,
        token="USDC",
        current_chain="ethereum",
        risk_tolerance="moderate",
    )
    
    print(response)


if __name__ == "__main__":
    test_graph()
