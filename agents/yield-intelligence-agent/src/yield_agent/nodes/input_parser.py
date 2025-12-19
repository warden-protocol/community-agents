"""
================================================================================
    INPUT PARSER NODE
    Extracts structured data from natural language queries
    
    Parses user intent, amount, token, chain preferences, and risk tolerance
    from free-form text input.
================================================================================
"""

from __future__ import annotations

import re
from typing import Any, Optional

from yield_agent.state import (
    AgentState,
    Intent,
    RiskTolerance,
    SUPPORTED_CHAINS,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


TOKEN_PATTERNS = [
    r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Za-z]{2,10})\b",
    r"\b([A-Za-z]{2,10})\s+(\d+(?:,\d{3})*(?:\.\d+)?)\b",
    r"\$(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:worth\s+of\s+)?([A-Za-z]{2,10})?\b",
    r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dollars?|usd)\b",
]

KNOWN_TOKENS = {
    "USDC", "USDT", "DAI", "FRAX", "LUSD", "BUSD", "TUSD",
    "ETH", "WETH", "STETH", "WSTETH", "RETH", "CBETH",
    "BTC", "WBTC", "TBTC",
    "MATIC", "WMATIC",
    "BNB", "WBNB",
    "AVAX", "WAVAX",
    "ARB", "OP", "BASE",
}

CHAIN_ALIASES: dict[str, str] = {
    "eth": "ethereum",
    "mainnet": "ethereum",
    "arb": "arbitrum",
    "arbitrum one": "arbitrum",
    "op": "optimism",
    "matic": "polygon",
    "poly": "polygon",
    "bnb": "bsc",
    "binance": "bsc",
    "bnb chain": "bsc",
    "avax": "avalanche",
}

RISK_KEYWORDS: dict[str, list[str]] = {
    "conservative": [
        "safe", "low risk", "conservative", "stable", "secure",
        "blue chip", "established", "trusted", "reliable",
    ],
    "moderate": [
        "moderate", "balanced", "normal", "medium risk",
    ],
    "aggressive": [
        "aggressive", "high risk", "risky", "degen", "ape",
        "maximum yield", "highest apy", "best returns",
    ],
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "yield_search": [
        "yield", "apy", "apr", "earn", "stake", "deposit",
        "farm", "farming", "best", "where", "find", "invest",
        "put", "place", "returns", "interest", "passive",
    ],
    "compare": [
        "compare", "versus", "vs", "or", "difference", "better",
        "which", "between",
    ],
    "route_only": [
        "bridge", "transfer", "move", "send", "cross-chain",
        "swap chain", "get to",
    ],
    "risk_analysis": [
        "risk", "safe", "audit", "security", "trust", "rug",
        "analyze", "analysis", "how safe",
    ],
}

EXCLUSION_KEYWORDS = [
    "not", "no", "avoid", "exclude", "without", "except", "skip",
]


# ==============================================================================
# PARSER FUNCTIONS
# ==============================================================================


def parse_amount_and_token(query: str) -> tuple[Optional[float], Optional[str]]:
    """
    Extract amount and token from query.
    
    Examples:
        "10k USDC" -> (10000.0, "USDC")
        "5000 dollars" -> (5000.0, "USD")
        "$10,000 worth of ETH" -> (10000.0, "ETH")
    """
    query_clean = query.lower()
    
    query_normalized = query_clean
    query_normalized = re.sub(r"(\d+)k\b", lambda m: str(int(m.group(1)) * 1000), query_normalized)
    query_normalized = re.sub(r"(\d+)m\b", lambda m: str(int(m.group(1)) * 1000000), query_normalized)
    
    amount: Optional[float] = None
    token: Optional[str] = None
    
    pattern1 = r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*([A-Za-z]{2,10})\b"
    matches = re.findall(pattern1, query_normalized)
    for num_str, tok in matches:
        num = float(num_str.replace(",", ""))
        tok_upper = tok.upper()
        if tok_upper in KNOWN_TOKENS:
            amount = num
            token = tok_upper
            break
    
    if amount is None:
        pattern2 = r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)"
        matches = re.findall(pattern2, query_normalized)
        if matches:
            amount = float(matches[0].replace(",", ""))
            
            for tok in KNOWN_TOKENS:
                if tok.lower() in query_clean:
                    token = tok
                    break
            
            if token is None:
                token = "USDC"
    
    if amount is None:
        pattern3 = r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dollars?|usd)\b"
        matches = re.findall(pattern3, query_normalized)
        if matches:
            amount = float(matches[0].replace(",", ""))
            token = "USDC"
    
    if token is None and amount is None:
        for tok in KNOWN_TOKENS:
            if tok.lower() in query_clean or tok in query:
                token = tok
                break
    
    return amount, token


def parse_chains(query: str) -> tuple[list[str], Optional[str]]:
    """
    Extract preferred chains and current chain from query.
    
    Returns:
        (preferred_chains, current_chain)
    """
    query_lower = query.lower()
    preferred: list[str] = []
    current: Optional[str] = None
    
    current_patterns = [
        r"(?:i'm on|i am on|currently on|on)\s+(\w+)",
        r"(?:from|have .* on)\s+(\w+)",
        r"(\w+)\s+(?:wallet|account)",
    ]
    
    for pattern in current_patterns:
        match = re.search(pattern, query_lower)
        if match:
            chain_name = match.group(1)
            resolved = _resolve_chain(chain_name)
            if resolved:
                current = resolved
                break
    
    for chain_key in SUPPORTED_CHAINS.keys():
        if chain_key in query_lower:
            if chain_key not in preferred:
                preferred.append(chain_key)
    
    for alias, chain_key in CHAIN_ALIASES.items():
        if alias in query_lower:
            if chain_key not in preferred:
                preferred.append(chain_key)
    
    chain_config = SUPPORTED_CHAINS
    for key, config in chain_config.items():
        if config["name"].lower() in query_lower:
            if key not in preferred:
                preferred.append(key)
    
    return preferred, current


def parse_risk_tolerance(query: str) -> RiskTolerance:
    """
    Determine risk tolerance from query keywords.
    """
    query_lower = query.lower()
    
    for keyword in RISK_KEYWORDS["conservative"]:
        if keyword in query_lower:
            return RiskTolerance.CONSERVATIVE
    
    for keyword in RISK_KEYWORDS["aggressive"]:
        if keyword in query_lower:
            return RiskTolerance.AGGRESSIVE
    
    for keyword in RISK_KEYWORDS["moderate"]:
        if keyword in query_lower:
            return RiskTolerance.MODERATE
    
    return RiskTolerance.MODERATE


def parse_intent(query: str) -> Intent:
    """
    Classify the user's intent from query.
    """
    query_lower = query.lower()
    
    intent_scores: dict[str, int] = {
        "yield_search": 0,
        "compare": 0,
        "route_only": 0,
        "risk_analysis": 0,
    }
    
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower:
                intent_scores[intent] += 1
    
    max_intent = max(intent_scores, key=intent_scores.get)
    max_score = intent_scores[max_intent]
    
    if max_score == 0:
        return Intent.YIELD_SEARCH
    
    intent_map = {
        "yield_search": Intent.YIELD_SEARCH,
        "compare": Intent.COMPARE_PROTOCOLS,
        "route_only": Intent.ROUTE_ONLY,
        "risk_analysis": Intent.RISK_ANALYSIS,
    }
    
    return intent_map.get(max_intent, Intent.YIELD_SEARCH)


def parse_exclusions(query: str) -> list[str]:
    """
    Extract protocols or chains to exclude.
    """
    query_lower = query.lower()
    exclusions: list[str] = []
    
    for keyword in EXCLUSION_KEYWORDS:
        pattern = rf"{keyword}\s+(\w+)"
        matches = re.findall(pattern, query_lower)
        exclusions.extend(matches)
    
    return exclusions


def _resolve_chain(name: str) -> Optional[str]:
    """Resolve chain name or alias to standard key."""
    name_lower = name.lower()
    
    if name_lower in SUPPORTED_CHAINS:
        return name_lower
    
    if name_lower in CHAIN_ALIASES:
        return CHAIN_ALIASES[name_lower]
    
    for key, config in SUPPORTED_CHAINS.items():
        if config["name"].lower() == name_lower:
            return key
    
    return None


# ==============================================================================
# NODE FUNCTION
# ==============================================================================


def parse_input(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Parse user query into structured fields.
    
    Extracts:
        - amount: Investment amount
        - token: Token symbol
        - preferred_chains: Chains to search
        - current_chain: User's current chain
        - risk_tolerance: Risk preference
        - intent: Query intent classification
        - excluded_protocols: Protocols to avoid
    """
    query = state.user_query
    
    amount, token = parse_amount_and_token(query)
    
    preferred_chains, current_chain = parse_chains(query)
    
    risk_tolerance = parse_risk_tolerance(query)
    
    intent = parse_intent(query)
    
    exclusions = parse_exclusions(query)
    
    if not preferred_chains:
        target_chains = list(SUPPORTED_CHAINS.keys())
    else:
        target_chains = preferred_chains
    
    return {
        "amount": amount,
        "token": token,
        "preferred_chains": preferred_chains,
        "current_chain": current_chain,
        "risk_tolerance": risk_tolerance,
        "intent": intent,
        "excluded_protocols": exclusions,
        "target_chains": target_chains,
        "processing_step": "input_parsed",
    }


# ==============================================================================
# TESTING UTILITY
# ==============================================================================


def test_parser(query: str) -> None:
    """Test parser with a sample query."""
    print(f"\nQuery: {query}")
    print("-" * 50)
    
    amount, token = parse_amount_and_token(query)
    print(f"Amount: {amount}")
    print(f"Token: {token}")
    
    preferred, current = parse_chains(query)
    print(f"Preferred chains: {preferred}")
    print(f"Current chain: {current}")
    
    risk = parse_risk_tolerance(query)
    print(f"Risk tolerance: {risk}")
    
    intent = parse_intent(query)
    print(f"Intent: {intent}")
    
    exclusions = parse_exclusions(query)
    print(f"Exclusions: {exclusions}")


if __name__ == "__main__":
    test_queries = [
        "Where should I put 10k USDC for the best yield?",
        "I have $5,000 on Ethereum and want safe stablecoin yields",
        "Find me the highest APY for ETH staking on Arbitrum",
        "Compare Aave vs Compound for USDC lending",
        "Bridge my tokens from Polygon to Base",
        "Is the Yearn USDC vault safe?",
        "I want to ape 50k into the highest yield, don't care about risk",
    ]
    
    for q in test_queries:
        test_parser(q)
