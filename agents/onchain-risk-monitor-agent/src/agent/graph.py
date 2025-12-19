from typing import Dict, List, TypedDict

from langgraph.graph import StateGraph, END

from .sources import (
    get_env,
    get_latest_block_number,
    get_tx_count,
    get_protocol_tvl,
    detect_large_outflow_stub,
    detect_pause_or_admin_event_stub,
)
from .rules import (
    Signal,
    check_tx_spike,
    check_large_outflow,
    score_signals,
    recommended_actions,
)


# -------------------------
# STATE DEFINITION
# -------------------------

class AgentState(TypedDict, total=False):
    request: Dict
    fetched: Dict
    signals: List[Signal]
    result: Dict


# -------------------------
# GRAPH NODES
# -------------------------

def validate_request(state: AgentState) -> AgentState:
    req = state["request"]

    if req.get("chain") != "ethereum":
        raise ValueError("only ethereum is supported in this version")

    if not isinstance(req.get("targets"), list) or len(req["targets"]) == 0:
        raise ValueError("targets must be a non-empty list")

    if req.get("window_minutes") not in [60, 360, 1440]:
        raise ValueError("window_minutes must be 60, 360, or 1440")

    if req.get("risk_profile") not in ["strict", "balanced", "fast"]:
        raise ValueError("risk_profile must be strict, balanced, or fast")

    return state


def fetch_data(state: AgentState) -> AgentState:
    req = state["request"]
    rpc_url = get_env("RPC_URL_ETH", required=True)

    tx_counts = {}
    for addr in req["targets"]:
        tx_counts[addr] = get_tx_count(addr, rpc_url)

    tvl = None
    if req.get("tvl_protocol_slug"):
        tvl = get_protocol_tvl(req["tvl_protocol_slug"])

    outflow_usd = detect_large_outflow_stub()
    paused, admin_changed = detect_pause_or_admin_event_stub()

    state["fetched"] = {
        "tx_counts": tx_counts,
        "tvl": tvl,
        "outflow_usd": outflow_usd,
        "paused": paused,
        "admin_changed": admin_changed,
    }
    return state


def analyze_risk(state: AgentState) -> AgentState:
    req = state["request"]
    fetched = state["fetched"]

    signals: List[Signal] = []

    baseline = 50
    if req["risk_profile"] == "strict":
        baseline = 20
    elif req["risk_profile"] == "fast":
        baseline = 80

    for addr, tx_count in fetched["tx_counts"].items():
        sig = check_tx_spike(tx_count, baseline)
        if sig:
            signals.append(sig)

    outflow_sig = check_large_outflow(fetched["outflow_usd"])
    if outflow_sig:
        signals.append(outflow_sig)

    state["signals"] = signals
    return state


def build_response(state: AgentState) -> AgentState:
    signals = state.get("signals", [])

    result = {
        "chain": state["request"]["chain"],
        "targets": state["request"]["targets"],
        "window_minutes": state["request"]["window_minutes"],
        "risk_score": score_signals(signals),
        "signals_triggered": [s.__dict__ for s in signals],
        "recommended_actions": recommended_actions(signals),
    }

    state["result"] = result
    return state


# -------------------------
# GRAPH CONSTRUCTION
# -------------------------

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("validate", validate_request)
    graph.add_node("fetch", fetch_data)
    graph.add_node("analyze", analyze_risk)
    graph.add_node("respond", build_response)

    graph.set_entry_point("validate")
    graph.add_edge("validate", "fetch")
    graph.add_edge("fetch", "analyze")
    graph.add_edge("analyze", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
