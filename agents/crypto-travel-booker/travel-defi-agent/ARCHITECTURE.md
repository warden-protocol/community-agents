# Architecture Overview

## System Components

The Crypto Travel Agent is built on a LangGraph state machine with four main processing nodes:

```
User Input
    ↓
[Parse Node] → Extract destination, budget
    ↓
[Search Node] → Query hotel APIs
    ↓
[Swap Node] → Check if USDC swap needed
    ↓
[Book Node] → Execute booking
    ↓
Agent Output & On-Chain Action
```

## Core Components

### 1. **User Intent Parser** (`parse_intent`)
- **Input**: HumanMessage with natural language request
- **Output**: Extracted destination (string), budget (float), query (string)
- **Logic**: 
  - Searches for location markers ("to", "in", "at")
  - Extracts first word after marker as destination
  - Regex-parses budget from "$" notation
  - Falls back to defaults (Paris, $400) if parsing fails

### 2. **Hotel Search Node** (`search_hotels`)
- **Input**: destination, budget
- **Output**: hotel_name, hotel_price, status message
- **Behavior**:
  - **Mocked mode** (default): Returns "Budget Hotel" at $180/night
  - **Live mode** (with `--live` flag): Calls Booking.com RapidAPI
- **Error Handling**: 
  - Gracefully falls back to mocked price if API fails
  - Validates response structure before extraction
  - Timeout protection (10s)

### 3. **Swap Check Node** (`check_swap`)
- **Input**: hotel_price, budget_usd
- **Output**: needs_swap (bool), swap_amount, decision message
- **Logic**:
  - If hotel_price > budget: Reject (budget too low)
  - If hotel_price ≤ budget×0.8: No swap needed
  - Otherwise: Calculate USDC needed with 1% buffer

### 4. **Booking Node** (`book_hotel`)
- **Input**: hotel_name, destination, hotel_price
- **Output**: final_status, confirmation message
- **Behavior**: Mocked confirmation (ready for Warden on-chain integration)

## State Machine Definition

**AgentState (TypedDict)**:
```python
{
    "messages": List[HumanMessage],      # Message history
    "user_query": str,                    # Parsed user query
    "destination": str,                   # City name
    "budget_usd": float,                  # User's budget
    "hotel_name": str,                    # Selected hotel
    "hotel_price": float,                 # Nightly rate
    "needs_swap": bool,                   # Swap required?
    "swap_amount": float,                 # USDC to swap
    "final_status": str                   # Booking confirmation
}
```

## Execution Flow

1. **Initialization**: Load API keys (Booking, OpenAI/Grok), initialize LLM client
2. **Stream Input**: User provides message in natural language
3. **Node Execution**:
   - Parse node enriches state with destination/budget
   - Search node adds hotel data
   - Swap node calculates crypto amount needed
   - Book node produces final confirmation
4. **Output**: Agent returns booking details and next steps

## LangGraph Advantages

- **Traceability**: Each node is logged; judges can inspect step-by-step decisions
- **Error Isolation**: Failures in one node don't crash the workflow
- **State Management**: TypedDict ensures all data is explicit and validated
- **Extensibility**: Easy to add new nodes (e.g., payment processing, on-chain verification)
- **Testing**: Each node can be tested independently

## Integration Points

### Booking.com API
- **Live Mode**: Calls `https://booking-com.p.rapidapi.com/v1/hotels/search`
- **Fallback**: Returns mocked $180/night budget option
- **Auth**: X-RapidAPI-Key header

### Warden Protocol (Ready for Integration)
- **Current**: Booking confirmation is mocked
- **Future**: Connect to Warden Agent Kit to:
  - Store decision log on-chain
  - Sign transactions with agent identity
  - Execute USDC swap and payment
  - Record confirmation with timestamps

### LangSmith Cloud (Ready for Integration)
- **Tracing**: Every run creates a project in LangSmith
- **Debugging**: Step-by-step execution visible in dashboard
- **Metrics**: Track latency, cost, success rate

## Deployment Architecture

```
Local Development
├── agent.py (CLI)
├── test_agent.py (Unit tests)
└── .env (local keys)

LangSmith Cloud
├── Project registration
├── Environment variables
└── Trace dashboard

On-Chain (Warden)
├── Agent identity & signing
├── Decision log storage
└── USDC swap execution
```

---

See `SAFETY.md` for guardrails, spend limits, and on-chain action protections.
