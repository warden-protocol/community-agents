"""
Explicit LangGraph workflow definition for the Crypto Travel Agent.

This module defines the graph structure (nodes and edges) without importing
node implementations. Node functions are added dynamically to avoid circular
imports with agent.py.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import HumanMessage


class AgentState(TypedDict):
    """Shared state across all workflow nodes."""
    messages: Annotated[list, operator.add]
    user_query: str
    destination: str
    budget_usd: float
    hotel_name: str
    hotel_price: float
    needs_swap: bool
    swap_amount: float
    final_status: str
    tx_hash: str  # For Warden transaction hash


def build_workflow(parse_fn, search_fn, swap_fn, book_fn):
    """Build and compile the LangGraph workflow.
    
    Args:
        parse_fn: parse_intent function
        search_fn: search_hotels function
        swap_fn: check_swap function
        book_fn: book_hotel function
    
    Returns:
        Compiled workflow (LangGraph app)
    """
    wf = StateGraph(AgentState)
    wf.add_node("parse", parse_fn)
    wf.add_node("search", search_fn)
    wf.add_node("swap", swap_fn)
    wf.add_node("book", book_fn)

    wf.set_entry_point("parse")
    wf.add_edge("parse", "search")
    wf.add_edge("search", "swap")
    wf.add_edge("swap", "book")
    wf.add_edge("book", END)

    return wf.compile()


# Lazy initialization: workflow_app is built in agent.py after imports are resolved
workflow_app = None
