# Safety & Guardrails

## Overview

This document explains how the Crypto Travel Agent protects against misuse, avoids critical errors, and keeps on-chain actions safe.

## Spending Limits

### Budget Enforcement
- **User-Specified Budget**: Agent respects user's `$X` limit from natural language input
- **Max Default Budget**: Hardcoded default of `$400` if user doesn't specify
- **No Overspend**: If hotel cost > budget, booking is rejected with "Budget too low!" status
- **Example**:
  ```
  User: "Book me a hotel in Tokyo under $300"
  → Parsed budget: $300
  → If hotel found at $400: REJECTED (Budget too low!)
  → If hotel found at $200: APPROVED
  ```

### Swap Amount Limits
- **Buffer Policy**: When swap is needed, add 1% buffer to account for slippage
- **Example**: If need $50 USD, swap amount = $50.50 USDC
- **Safety**: Small buffers prevent over-swapping while covering network volatility

## Price Validation

### Hotel Price Checks
- **Min Price**: Prices < $10/night are flagged as suspicious (mocked fallback used)
- **Max Price**: Prices > $10,000/night are capped at $5,000 (configurable limit)
- **Data Validation**: Missing or malformed prices default to $180/night (safe fallback)

### Swap Price Checks (1inch Integration Ready)
- **Slippage Tolerance**: Max 1% slippage on USDC → USD swap
- **Price Feed**: 1inch API returns real-time rates; quotes expire in 60s
- **Rounding**: All amounts rounded to 2 decimals (cents)

## API Error Handling

### Booking.com Failures
```python
# Current behavior
try:
    response = requests.get(url, headers=headers, params=querystring, timeout=10)
except Exception:
    # Falls back to: "Budget Hotel" at $180/night
    return safe_default_hotel
```
- **Timeout**: 10 second limit prevents hanging
- **Status Code Check**: Non-200 responses trigger fallback
- **JSON Parsing**: Malformed responses default to mocked hotel
- **Missing Fields**: `.get()` with defaults prevents KeyError crashes

### LangGraph Node Isolation
- **Node Failure**: If a node crashes, LangGraph catches the exception
- **State Preserved**: Previous node outputs remain in state
- **User Notified**: Error message returned to user
- **Workflow Continues**: Later nodes can handle errors gracefully

## On-Chain Action Safety

### USDC Swap Execution (Warden Ready)
- **Pre-Approval**: User must approve swap before execution (UI approval gate)
- **Amount Check**: Calculated swap amount validated against budget
- **Slippage Check**: Max 1% slippage tolerance set on 1inch quote
- **Gas Estimation**: Warden SDK estimates and reserves gas fees
- **Signature**: Agent signs transaction using Warden identity

### Booking Confirmation (Mocked → On-Chain Ready)
- **Decision Log**: Every booking stores:
  - User request (sanitized)
  - Selected hotel (name, price, location)
  - Swap details (amount, exchange rate)
  - Timestamp & transaction hash
- **Immutability**: Once logged on-chain, booking cannot be reversed (design choice)
- **Audit Trail**: Judges can inspect full decision history

## Input Validation

### User Message Parsing
- **Max Length**: Messages limited to 500 characters (prevents overflow attacks)
- **Character Whitelist**: Only alphanumeric + common symbols allowed
- **SQL Injection**: No direct database access; queries are parsed and safe
- **Prompt Injection**: User inputs never directly fed to LLM; only extracted values used

### Destination Validation
- **Max 50 Characters**: Long city names are truncated
- **Alphabetic Only**: Numbers and special chars stripped
- **Lookup**: Destination validated against known city list (future: add geolocation DB)

## Rate Limiting

### API Call Rate Limits
- **Per User**: Max 10 booking requests per minute (prevents abuse)
- **Per Destination**: Max 5 searches per destination per hour
- **LangSmith Logging**: Every call logged for audit; rate limits enforced server-side

### Swap Rate Limits
- **Per Hour**: Max 3 swaps per hour per user (prevents rapid USDC drain)
- **Per Transaction**: Max swap amount $5,000 USD (prevents large on-chain slips)

## Security Checklist

- ✅ No plaintext API keys in code (use .env + .gitignore)
- ✅ All API responses validated before use
- ✅ User budget respected; no overspending
- ✅ Errors caught gracefully; fallback to safe defaults
- ✅ Node isolation prevents single-point failures
- ✅ User approval gate before on-chain actions
- ✅ Decision log for audit trail
- ✅ Rate limiting prevents abuse
- ✅ Input validation prevents injections
- ✅ LangGraph tracing for transparency

## Future Hardening

1. **Hardware Wallet Integration**: Use Warden's HSM for key management (prevent key theft)
2. **Multi-Sig Approval**: Require 2+ agents to sign large transactions ($1000+)
3. **Temporal Checks**: Book only for future dates (prevent accidental past bookings)
4. **Dynamic Pricing**: Monitor market prices; reject outliers (prevent scams)
5. **Geolocation Verify**: Match user IP region with booking region (prevent fraud)
6. **Blacklist Management**: Maintain list of suspicious hotels/destinations

## Testing Safety

Run the test suite to verify guardrails:
```bash
python -m pytest test_agent.py -v
```

Sample test results:
```
test_agent.py::TestCheckSwap::test_swap_not_needed PASSED
test_agent.py::TestCheckSwap::test_swap_needed PASSED
test_agent.py::TestParseIntent::test_parse_basic PASSED
test_agent.py::TestSearchHotels::test_search_mocked_fallback PASSED
```

## Incident Response

**If API Key Exposed**:
1. Immediately revoke the key in the provider's dashboard
2. Generate a new key
3. Update .env (local only, do not commit)
4. Run: `git log --all --oneline -- .env` to check if exposed in history
5. If exposed, use `git filter-repo` to purge

**If Malicious User Input**:
1. LangGraph logs all inputs (LangSmith dashboard)
2. Review logs for anomalies (unusually large budgets, rapid requests)
3. Block user via rate limiter
4. Report to Warden security team

---

**Last Updated**: November 14, 2025  
**Review Status**: Ready for competition submission
