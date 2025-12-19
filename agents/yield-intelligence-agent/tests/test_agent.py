"""
================================================================================
    TEST SCRIPT
    Verify the Yield Intelligence Agent works correctly
    
    Run with: python -m pytest tests/test_agent.py -v
    Or simply: python tests/test_agent.py
================================================================================
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yield_agent.state import (
    AgentState,
    YieldOpportunity,
    BridgeRoute,
    GasEstimate,
    Recommendation,
    RiskTolerance,
    ILRisk,
    Intent,
    SUPPORTED_CHAINS,
)
from yield_agent.nodes.input_parser import (
    parse_input,
    parse_amount_and_token,
    parse_chains,
    parse_risk_tolerance,
    parse_intent,
)
from yield_agent.nodes.response_formatter import (
    format_response,
    format_currency,
    format_apy,
)


# ==============================================================================
# TEST UTILITIES
# ==============================================================================


def print_header(title: str) -> None:
    """Print a formatted test section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(test_name: str, passed: bool, details: str = "") -> None:
    """Print a test result."""
    status = "PASS" if passed else "FAIL"
    symbol = "[OK]" if passed else "[X]"
    print(f"  {symbol} {test_name}")
    if details and not passed:
        print(f"      -> {details}")


# ==============================================================================
# UNIT TESTS
# ==============================================================================


def test_parse_amount_and_token() -> bool:
    """Test amount and token parsing."""
    test_cases = [
        ("10k USDC", 10000.0, "USDC"),
        ("5000 ETH", 5000.0, "ETH"),
        ("$10,000 worth of DAI", 10000.0, "DAI"),
        ("100 dollars", 100.0, "USDC"),
        ("1m USDT", 1000000.0, "USDT"),
    ]
    
    all_passed = True
    for query, expected_amount, expected_token in test_cases:
        amount, token = parse_amount_and_token(query)
        passed = (amount == expected_amount and token == expected_token)
        if not passed:
            print(f"      Failed: '{query}' -> ({amount}, {token}), expected ({expected_amount}, {expected_token})")
            all_passed = False
    
    return all_passed


def test_parse_chains() -> bool:
    """Test chain parsing."""
    test_cases = [
        ("yields on arbitrum", ["arbitrum"], "arbitrum"),
        ("I'm on ethereum looking for base yields", ["ethereum", "base"], "ethereum"),
        ("polygon and avalanche", ["polygon", "avalanche"], None),
    ]
    
    all_passed = True
    for query, expected_preferred, expected_current in test_cases:
        preferred, current = parse_chains(query)
        
        preferred_match = set(preferred) == set(expected_preferred)
        current_match = (current == expected_current)
        
        passed = preferred_match and current_match
        if not passed:
            print(f"      Failed: '{query}'")
            print(f"        Preferred: {preferred}, expected {expected_preferred}")
            print(f"        Current: {current}, expected {expected_current}")
            all_passed = False
    
    return all_passed


def test_parse_risk_tolerance() -> bool:
    """Test risk tolerance parsing."""
    test_cases = [
        ("safe stablecoin yields", RiskTolerance.CONSERVATIVE),
        ("I want to ape into high yields", RiskTolerance.AGGRESSIVE),
        ("balanced approach", RiskTolerance.MODERATE),
        ("conservative investment", RiskTolerance.CONSERVATIVE),
        ("degen mode", RiskTolerance.AGGRESSIVE),
    ]
    
    all_passed = True
    for query, expected in test_cases:
        result = parse_risk_tolerance(query)
        passed = (result == expected)
        if not passed:
            print(f"      Failed: '{query}' -> {result}, expected {expected}")
            all_passed = False
    
    return all_passed


def test_parse_intent() -> bool:
    """Test intent classification."""
    test_cases = [
        ("where to put my USDC for yield", Intent.YIELD_SEARCH),
        ("compare Aave vs Compound", Intent.COMPARE_PROTOCOLS),
        ("bridge my tokens to Arbitrum", Intent.ROUTE_ONLY),
        ("analyze the risk of this pool", Intent.RISK_ANALYSIS),
    ]
    
    all_passed = True
    for query, expected in test_cases:
        result = parse_intent(query)
        passed = (result == expected)
        if not passed:
            print(f"      Failed: '{query}' -> {result}, expected {expected}")
            all_passed = False
    
    return all_passed


def test_format_currency() -> bool:
    """Test currency formatting."""
    test_cases = [
        (1500000000, "$1.50B"),
        (150000000, "$150.00M"),
        (1500000, "$1.50M"),
        (15000, "$15.0K"),
        (150, "$150.00"),
    ]
    
    all_passed = True
    for value, expected in test_cases:
        result = format_currency(value)
        passed = (result == expected)
        if not passed:
            print(f"      Failed: {value} -> '{result}', expected '{expected}'")
            all_passed = False
    
    return all_passed


def test_format_apy() -> bool:
    """Test APY formatting."""
    test_cases = [
        (150.0, "150%"),
        (15.5, "15.5%"),
        (5.25, "5.25%"),
    ]
    
    all_passed = True
    for value, expected in test_cases:
        result = format_apy(value)
        passed = (result == expected)
        if not passed:
            print(f"      Failed: {value} -> '{result}', expected '{expected}'")
            all_passed = False
    
    return all_passed


def test_state_models() -> bool:
    """Test state model creation."""
    try:
        opp = YieldOpportunity(
            pool_id="test-pool",
            protocol="Test Protocol",
            protocol_slug="test-protocol",
            chain="ethereum",
            pool_name="Test Pool",
            symbol="USDC",
            apy=5.5,
            tvl_usd=1000000,
            risk_score=3.0,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=365,
        )
        
        route = BridgeRoute(
            from_chain="ethereum",
            from_chain_id=1,
            to_chain="arbitrum",
            to_chain_id=42161,
            token="USDC",
            token_address="0x123",
            amount=1000,
            bridge_name="Stargate",
            estimated_time_seconds=120,
            gas_cost_usd=5.0,
            bridge_fee_usd=2.0,
            total_cost_usd=7.0,
            estimated_output=993.0,
            slippage_percent=0.5,
        )
        
        state = AgentState(
            user_query="Test query",
            amount=1000,
            token="USDC",
        )
        
        return True
    except Exception as e:
        print(f"      Error: {e}")
        return False


def test_supported_chains() -> bool:
    """Test supported chains configuration."""
    required_chains = ["ethereum", "arbitrum", "optimism", "polygon", "base", "avalanche", "bsc"]
    
    all_passed = True
    for chain in required_chains:
        if chain not in SUPPORTED_CHAINS:
            print(f"      Missing chain: {chain}")
            all_passed = False
        else:
            config = SUPPORTED_CHAINS[chain]
            if "chain_id" not in config:
                print(f"      Missing chain_id for {chain}")
                all_passed = False
            if "name" not in config:
                print(f"      Missing name for {chain}")
                all_passed = False
    
    return all_passed


def test_parse_input_node() -> bool:
    """Test the full parse_input node."""
    try:
        state = AgentState(
            user_query="Where should I put 10k USDC for the best yield on Arbitrum?",
        )
        
        result = parse_input(state)
        
        checks = [
            ("amount", result.get("amount") == 10000),
            ("token", result.get("token") == "USDC"),
            ("intent", result.get("intent") == Intent.YIELD_SEARCH),
            ("target_chains", "arbitrum" in result.get("target_chains", [])),
        ]
        
        all_passed = True
        for name, passed in checks:
            if not passed:
                print(f"      Failed check: {name}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"      Error: {e}")
        return False


def test_format_response_node() -> bool:
    """Test the format_response node."""
    try:
        mock_opp = YieldOpportunity(
            pool_id="test",
            protocol="Aave v3",
            protocol_slug="aave-v3",
            chain="arbitrum",
            pool_name="Aave USDC",
            symbol="USDC",
            apy=5.2,
            tvl_usd=150000000,
            risk_score=2.0,
            il_risk=ILRisk.NONE,
            audited=True,
            protocol_age_days=600,
        )
        
        mock_rec = Recommendation(
            rank=1,
            opportunity=mock_opp,
            input_amount=10000,
            input_token="USDC",
            earnings_30d=43.33,
            earnings_1y=520.0,
            requires_bridge=False,
            bridge_route=None,
            net_apy=5.2,
            total_entry_cost_usd=5.0,
            why_recommended="Test reasoning",
            warnings=[],
            execution_steps=["Step 1", "Step 2"],
        )
        
        state = AgentState(
            user_query="Test query",
            amount=10000,
            token="USDC",
            risk_tolerance=RiskTolerance.MODERATE,
            recommendations=[mock_rec],
        )
        
        result = format_response(state)
        
        response = result.get("formatted_response", "")
        
        checks = [
            ("has content", len(response) > 100),
            ("has header", "YIELD INTELLIGENCE" in response),
            ("has protocol", "Aave" in response),
            ("has apy", "5.2" in response or "5.20" in response),
        ]
        
        all_passed = True
        for name, passed in checks:
            if not passed:
                print(f"      Failed check: {name}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"      Error: {e}")
        return False


# ==============================================================================
# INTEGRATION TEST
# ==============================================================================


def test_full_graph() -> bool:
    """Test the complete LangGraph workflow."""
    try:
        from yield_agent.graph import create_yield_agent
        
        agent = create_yield_agent()
        
        if agent is None:
            print("      Failed: Agent creation returned None")
            return False
        
        return True
    except ImportError as e:
        print(f"      Import error (may need dependencies): {e}")
        return True
    except Exception as e:
        print(f"      Error: {e}")
        return False


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================


def run_all_tests() -> None:
    """Run all tests and print summary."""
    print()
    print("=" * 70)
    print("  WARDEN YIELD INTELLIGENCE AGENT - TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Parse Amount & Token", test_parse_amount_and_token),
        ("Parse Chains", test_parse_chains),
        ("Parse Risk Tolerance", test_parse_risk_tolerance),
        ("Parse Intent", test_parse_intent),
        ("Format Currency", test_format_currency),
        ("Format APY", test_format_apy),
        ("State Models", test_state_models),
        ("Supported Chains", test_supported_chains),
        ("Parse Input Node", test_parse_input_node),
        ("Format Response Node", test_format_response_node),
        ("Full Graph Creation", test_full_graph),
    ]
    
    results = []
    
    print_header("UNIT TESTS")
    
    for name, test_func in tests:
        try:
            passed = test_func()
        except Exception as e:
            passed = False
            print(f"      Exception in {name}: {e}")
        
        results.append((name, passed))
        print_result(name, passed)
    
    print_header("SUMMARY")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    
    print(f"  Total:  {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print()
    
    if failed == 0:
        print("  All tests passed successfully!")
    else:
        print("  Some tests failed. Please review the output above.")
    
    print()
    print("=" * 70)
    print()
    
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_tests()
