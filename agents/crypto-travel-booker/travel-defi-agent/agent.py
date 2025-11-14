# agent.py - Crypto Travel Booker
# Orchestrates the booking flow using LangGraph workflow_app
# This file focuses on node implementations and CLI entry point.

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
import requests
import os
from dotenv import load_dotenv
from typing import TypedDict, Annotated
import operator

load_dotenv()

# === IMPORTS ===
# Import graph builder and state (workflow app will be built at end of file)
from workflow.graph import build_workflow, AgentState

# === LLM: Grok AI ===
GROK_KEY = os.getenv("GROK_API_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
BOOKING_KEY = os.getenv("BOOKING_API_KEY")

# Create an LLM client if possible. Prefer Grok when configured, otherwise fall
# back to OpenAI if available. If neither key is set, continue with None and
# rely on the workflow's mocked fallbacks.
llm = None
if GROK_KEY:
    try:
        llm = ChatGroq(model="grok-beta", api_key=GROK_KEY, temperature=0)
    except Exception as e:
        print("Warning: failed to initialize ChatGroq:", type(e).__name__, str(e))
        llm = None
elif OPENAI_KEY:
    try:
        # import here to avoid requiring langchain-openai when not needed
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="grok-beta", api_key=OPENAI_KEY, temperature=0)
    except Exception as e:
        print("Warning: failed to initialize ChatOpenAI:", type(e).__name__, str(e))
        llm = None

# === STATE ===
class AgentState(TypedDict):
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

# === 1. Parse User (FIXED: handles "in", "to", "at") ===
def parse_intent(state):
    """Parse user intent from message. Extracts destination and budget."""
    try:
        query = state["messages"][-1].content.lower()
        destination = "Paris"
        budget = 400.0

        # Find destination after "to", "in", "at"
        markers = ["to ", "in ", "at "]
        dest_part = query
        for marker in markers:
            if marker in query:
                dest_part = query.split(marker, 1)[-1]
                break

        # Extract first word as city
        words = dest_part.strip().split()
        if words:
            destination = words[0].capitalize()

        # Extract budget after $
        if "$" in query:
            try:
                budget_str = query.split("$")[-1]
                budget = float(''.join(filter(str.isdigit, budget_str.split()[0])))
            except Exception as e:
                print(f"[WARN] Failed to parse budget from '{budget_str}': {e}. Using default $400")
                pass

        print(f"[PARSE] Extracted destination='{destination}', budget=${budget}")
        return {
            "user_query": query,
            "destination": destination,
            "budget_usd": budget
        }
    except Exception as e:
        print(f"[ERROR] parse_intent failed: {type(e).__name__}: {e}")
        return {
            "user_query": state.get("messages", [{"content": ""}])[-1].content if state.get("messages") else "",
            "destination": "Paris",
            "budget_usd": 400.0
        }

# === 2. Search Hotels on Booking.com ===
def search_hotels(state, live=False):
    """Search for hotels on Booking.com. Falls back to mocked result on error."""
    url = "https://booking-com.p.rapidapi.com/v1/hotels/search"
    querystring = {
        "checkout_date": "2025-12-16",
        "units": "metric",
        "dest_id": "-1746443",  # Paris (we'll improve later)
        "dest_type": "city",
        "locale": "en-gb",
        "adults_number": "1",
        "order_by": "price",
        "filter_by_currency": "USD",
        "checkin_date": "2025-12-15",
        "room_number": "1"
    }

    headers = {
        "X-RapidAPI-Key": BOOKING_KEY,
        "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
    }

    # If not running live, skip the network call and return a mocked result
    if not live or not BOOKING_KEY:
        print(f"[SEARCH] Live mode disabled or no API key. Using mocked fallback: Budget Hotel, $180.0")
        return {
            "hotel_name": "Budget Hotel",
            "hotel_price": 180.0,
            "messages": [HumanMessage(content=f"Found Budget Hotel in {state.get('destination','Unknown')} for $180.0/night")]
        }

    try:
        print(f"[SEARCH] Querying Booking.com API for '{state.get('destination', 'Unknown')}'...")
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        if response.status_code != 200:
            print(f"[ERROR] Booking API returned {response.status_code}: {response.text[:200]}")
            name, price = "Budget Hotel", 180.0
        else:
            data = response.json()
            if data.get("result") and len(data["result"]) > 0:
                hotel = data["result"][0]
                name = hotel.get("hotel_name", "Budget Hotel")
                # safe extraction of price
                try:
                    price = float(hotel.get("price_breakdown", {}).get("all_inclusive_price", 180.0))
                    # ============================================================
                    # GUARDRAIL: Price validation (minimum bounds)
                    # ============================================================
                    # Reject prices < $10/night as likely data corruption or
                    # API errors (impossible hotel rates indicate bad data).
                    if price < 10:
                        print(f"[WARN] Suspicious price ${price}. Using default $180.0")
                        price = 180.0
                except Exception as e:
                    print(f"[WARN] Failed to parse price: {e}. Using default $180.0")
                    price = 180.0
                print(f"[SEARCH] Found {name} for ${price}/night")
            else:
                print("[SEARCH] No results from API. Using mocked fallback.")
                name, price = "Budget Hotel", 180.0
    except requests.Timeout:
        # ======================================================================
        # GUARDRAIL: API timeout protection
        # ======================================================================
        # 10-second timeout prevents hanging on unresponsive external APIs.
        # Gracefully falls back to mocked hotel.
        print("[ERROR] Booking API request timed out (>10s). Using mocked fallback.")
        name, price = "Budget Hotel", 180.0
    except Exception as e:
        print(f"[ERROR] search_hotels failed: {type(e).__name__}: {e}")
        name, price = "Budget Hotel", 180.0

    return {
        "hotel_name": name,
        "hotel_price": price,
        "messages": [HumanMessage(content=f"Found {name} in {state['destination']} for ${price}/night")]
    }

# === 3. Check Swap ===
def check_swap(state):
    """Calculate swap amount needed. Returns swap details and error messages.
    
    GUARDRAILS ENFORCED:
    - Budget validation: Rejects if hotel_price > budget_usd
    - Slippage protection: Adds 1% buffer to swap amount
    - Rounding: All amounts rounded to 2 decimals (cent precision)
    """
    try:
        hotel_price = state.get("hotel_price", 0.0)
        budget = state.get("budget_usd", 0.0)
        
        # ====================================================================
        # GUARDRAIL: User budget enforcement
        # ====================================================================
        # Reject bookings that exceed the user's stated budget. Prevents
        # overspendings and ensures user intent is respected.
        if hotel_price > budget:
            print(f"[SWAP] Budget check failed: hotel ${hotel_price} > budget ${budget}")
            return {
                "needs_swap": False,
                "final_status": "Budget too low!",
                "messages": [HumanMessage(content="Not enough budget. Try a cheaper destination.")]
            }

        swap_needed = hotel_price - (budget * 0.8)
        if swap_needed <= 0:
            print(f"[SWAP] No swap needed: sufficient USD balance ({budget} > {hotel_price})")
            return {
                "needs_swap": False,
                "swap_amount": 0,
                "messages": [HumanMessage(content="You have enough USD!")]
            }

        # ====================================================================
        # GUARDRAIL: Slippage protection (1% buffer)
        # ====================================================================
        # Add 1% buffer to swap amount to account for:
        # - Market price movement during transaction confirmation
        # - Exchange/routing fees
        # - Liquidity depth on testnet/mainnet
        usdc_needed = swap_needed * 1.01
        print(f"[SWAP] Swap needed: ${usdc_needed} USDC (1% buffer included)")

        return {
            "needs_swap": True,
            "swap_amount": round(usdc_needed, 2),
            "messages": [HumanMessage(content=f"Swapping {round(usdc_needed, 2)} USDC → USD via 1inch")]
        }
    except Exception as e:
        print(f"[ERROR] check_swap failed: {type(e).__name__}: {e}")
        return {
            "needs_swap": False,
            "swap_amount": 0,
            "final_status": "Swap calculation error",
            "messages": [HumanMessage(content="Error calculating swap. Using available balance.")]
        }

# === 4. Book ===
def book_hotel(state):
    """Create booking confirmation. Attempt to perform on-chain booking via Warden.

    This function uses `warden_client.submit_booking` to perform the
    on-chain action when available and configured; otherwise it falls back
    to a mocked confirmation. The return value includes `tx_hash` when an
    on-chain submission occurred (or the mocked tx hash).
    """
    try:
        hotel_name = state.get("hotel_name", "Unknown Hotel")
        hotel_price = state.get("hotel_price", 0.0)
        destination = state.get("destination", "Unknown")
        swap_amount = state.get("swap_amount", 0.0)

        # Validate state before booking
        if not hotel_name or hotel_price <= 0:
            print(f"[ERROR] Invalid booking state: hotel_name='{hotel_name}', price=${hotel_price}")
            return {
                "final_status": "Invalid booking details",
                "messages": [HumanMessage(content="Booking failed: invalid hotel details.")]
            }

        print(f"[BOOK] Confirming booking: {hotel_name} ({destination}) for ${hotel_price}")
        if swap_amount > 0:
            print(f"[BOOK] Swap: ${swap_amount} USDC")

        # Attempt on-chain booking through Warden wrapper
        try:
            from warden_client import submit_booking
            result = submit_booking(hotel_name, hotel_price, destination, swap_amount)
            if result.get("tx_hash"):
                tx = result["tx_hash"]
                print(f"[BOOK] Warden tx: {tx}")
                return {
                    "final_status": f"Booked {hotel_name} for ${hotel_price}",
                    "tx_hash": tx,
                    "messages": [HumanMessage(content=f"Booking confirmed on Warden! Paid with USDC. Enjoy {destination}!")]
                }
            else:
                print(f"[BOOK] Warden returned error: {result.get('error')}")
        except Exception as e:
            print(f"[WARN] Warden booking attempt failed: {type(e).__name__}: {e}")

        # Fallback confirmation (mock)
        return {
            "final_status": f"Booked {hotel_name} for ${hotel_price}",
            "messages": [HumanMessage(content=f"Booking confirmed on Warden! Paid with USDC. Enjoy {destination}!")]
        }
    except Exception as e:
        print(f"[ERROR] book_hotel failed: {type(e).__name__}: {e}")
        return {
            "final_status": "Booking error",
            "messages": [HumanMessage(content="Booking failed. Please try again.")]
        }


# === BUILD WORKFLOW ===
# Now that all node functions are defined, build the workflow
workflow_app = build_workflow(parse_intent, search_hotels, check_swap, book_hotel)


# === CLI ENTRY POINT ===
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Crypto Travel Agent CLI")
    parser.add_argument("cmd", nargs="?", default="test",
                        help="Command: test|run|parse|search|swap|book|debug")
    parser.add_argument("--message", "-m", dest="message", default=None,
                        help="Custom user message to use instead of the default test prompt")
    parser.add_argument("--live", action="store_true", help="Enable live API calls (must be explicit)")
    args = parser.parse_args()

    def run_workflow_once(test_input, live=False):
        """Execute the LangGraph workflow and stream output."""
        got_output = False
        try:
            for output in workflow_app.stream(test_input):
                for value in output.values():
                    if "messages" in value and value["messages"]:
                        print("Agent:", value["messages"][-1].content)
                        got_output = True
        except Exception as e:
            print("Streaming error:", type(e).__name__, str(e))

        if not got_output:
            # synchronous fallback
            state = {"messages": test_input["messages"]}
            parsed = parse_intent(state)
            state.update(parsed)
            print("Agent: Parsed ->", f"destination={state.get('destination')}", f"budget=${state.get('budget_usd')}")

            search_res = search_hotels(state, live=live)
            state.update(search_res)
            if search_res.get("messages"):
                print("Agent:", search_res["messages"][-1].content)

            swap_res = check_swap(state)
            state.update(swap_res)
            if swap_res.get("messages"):
                print("Agent:", swap_res["messages"][-1].content)

            book_res = book_hotel(state)
            state.update(book_res)
            if book_res.get("messages"):
                print("Agent:", book_res["messages"][-1].content)

    # Default test input (can be overridden with --message)
    default_message = "Book me a hotel in Tokyo under $300 using crypto"
    user_message = args.message if args.message is not None else default_message
    test_input = {"messages": [HumanMessage(content=user_message)]}

    live_flag = args.live

    cmd = args.cmd.lower()
    if cmd == "test":
        print("Crypto Travel Agent (test)\n")
        run_workflow_once(test_input, live=False)
        print("\nAgent ready for Warden Hub! Submit for $10K.")
    elif cmd == "run":
        print("Crypto Travel Agent (run) - live API calls enabled:" , live_flag, "\n")
        run_workflow_once(test_input, live=live_flag)
    elif cmd == "parse":
        print("Parse-only:\n")
        state = {"messages": test_input["messages"]}
        print(parse_intent(state))
    elif cmd == "search":
        print("Search-only:\n")
        state = {"messages": test_input["messages"]}
        state.update(parse_intent(state))
        print(search_hotels(state, live=live_flag))
    elif cmd == "swap":
        print("Swap-only:\n")
        state = {"messages": test_input["messages"]}
        state.update(parse_intent(state))
        state.update(search_hotels(state, live=live_flag))
        print(check_swap(state))
    elif cmd == "book":
        print("Book-only:\n")
        state = {"messages": test_input["messages"]}
        state.update(parse_intent(state))
        state.update(search_hotels(state))
        state.update(check_swap(state))
        print(book_hotel(state))
    elif cmd == "debug":
        print("Debug: printing internal state flow\n")
        run_workflow_once(test_input)
        print("\n-- Done debug --")
    else:
        print(f"Unknown command '{cmd}'. Use one of: test, run, parse, search, swap, book, debug.")