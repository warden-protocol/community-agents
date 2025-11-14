"""
Run three example scenarios to validate guardrails and normal flows.

Scenarios:
1) Booking exceeding testnet spend limit -> submit_booking should reject
2) Low-liquidity-like scenario (simulated) -> demonstrate not explicitly blocked
3) Simple stable trade (no swap needed) -> full flow returns mock tx_hash

Run: python scripts/run_examples.py
"""
import os
import json
from langchain_core.messages import HumanMessage

# Make repository root importable when running this script from `scripts/`
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import parse_intent, search_hotels, check_swap, book_hotel, workflow_app
import warden_client


def run_full_demo(prompt):
    state = {"messages": [HumanMessage(content=prompt)]}
    # run parse -> search -> swap -> book sequentially using functions
    p = parse_intent(state)
    s = search_hotels(p)
    # merge state for swap
    merged = {**p, **s}
    sw = check_swap(merged)
    merged.update(sw)
    bk = book_hotel(merged)
    merged.update(bk)
    # Convert HumanMessage objects to simple dicts for JSON-friendly output
    def _clean(obj):
        if isinstance(obj, list):
            return [_clean(x) for x in obj]
        if hasattr(obj, 'content'):
            return str(obj.content)
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        return obj

    print(json.dumps({"parse": _clean(p), "search": _clean(s), "swap": _clean(sw), "book": _clean(bk)}, indent=2))
    return merged


def scenario_exceed_spend_limit():
    print('\n=== Scenario 1: Exceed Testnet Spend Limit ===')
    # Call submit_booking directly with a price > TESTNET_MAX_SPEND_USD
    res = warden_client.submit_booking("Expensive Hotel", 600.0, "Expensia", 0.0)
    print('Result:', res)


def scenario_low_liquidity_simulation():
    print('\n=== Scenario 2: Low-Liquidity Simulation ===')
    # Our code does not implement liquidity checks, so simulate expected behavior.
    # We'll simulate a very large swap amount which could indicate low-liquidity risk.
    state = {"messages": [HumanMessage(content="Book me a hotel in SmallTown under $1000")]}
    p = parse_intent(state)
    # simulate search returning very high price near budget to force swap
    s = {"hotel_name": "Thin Liquidity Inn", "hotel_price": 950.0, "messages": [HumanMessage(content="Found Thin Liquidity Inn for $950/night")]}
    merged = {**p, **s}
    sw = check_swap(merged)
    print('Check swap output:', sw)
    # Attempt to book (this will call submit_booking which enforces TESTNET_MAX_SPEND_USD)
    bk = book_hotel({**merged, **sw})
    print('Book output:', bk)
    print('\nNote: Low-liquidity detection is not explicitly implemented; consider adding a 1inch liquidity probe.')


def scenario_simple_stable_trade():
    print('\n=== Scenario 3: Simple Stable Trade (No Swap Needed) ===')
    # User with sufficient budget
    merged = run_full_demo('Book me a hotel in Paris under $400')
    print('\nFinal merged state:\n', merged)


if __name__ == '__main__':
    scenario_exceed_spend_limit()
    scenario_low_liquidity_simulation()
    scenario_simple_stable_trade()
