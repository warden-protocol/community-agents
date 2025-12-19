"""
================================================================================
    RESPONSE FORMATTER NODE
    Generates beautiful, structured output for the user
    
    Creates formatted responses with recommendations, reasoning,
    and execution steps in a clear, professional format.
================================================================================
"""

from __future__ import annotations

from typing import Any

from yield_agent.state import (
    AgentState,
    Recommendation,
    RiskTolerance,
    SUPPORTED_CHAINS,
)


# ==============================================================================
# FORMATTING CONSTANTS
# ==============================================================================


DIVIDER_HEAVY = "=" * 70
DIVIDER_LIGHT = "-" * 70
DIVIDER_DOT = "." * 70

RISK_LABELS = {
    RiskTolerance.CONSERVATIVE: "Conservative (Safety First)",
    RiskTolerance.MODERATE: "Moderate (Balanced)",
    RiskTolerance.AGGRESSIVE: "Aggressive (Maximum Yield)",
}

CHAIN_SYMBOLS = {
    "ethereum": "ETH",
    "arbitrum": "ARB",
    "optimism": "OP",
    "polygon": "MATIC",
    "base": "BASE",
    "avalanche": "AVAX",
    "bsc": "BNB",
}


# ==============================================================================
# FORMATTING FUNCTIONS
# ==============================================================================


def format_currency(value: float, decimals: int = 2) -> str:
    """Format a number as currency."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}K"
    else:
        return f"${value:,.{decimals}f}"


def format_apy(apy: float) -> str:
    """Format APY percentage."""
    if apy >= 100:
        return f"{apy:.0f}%"
    elif apy >= 10:
        return f"{apy:.1f}%"
    else:
        return f"{apy:.2f}%"


def format_risk_bar(risk_score: float) -> str:
    """Create a visual risk indicator."""
    filled = int(risk_score)
    empty = 10 - filled
    
    if risk_score <= 3:
        label = "LOW"
    elif risk_score <= 6:
        label = "MED"
    else:
        label = "HIGH"
    
    return f"[{'*' * filled}{'.' * empty}] {risk_score:.1f}/10 {label}"


def format_time(seconds: int) -> str:
    """Format time duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{hours}h {mins}m"


# ==============================================================================
# SECTION FORMATTERS
# ==============================================================================


def format_header(
    query: str,
    amount: float,
    token: str,
    risk_tolerance: RiskTolerance,
    num_results: int,
) -> str:
    """Format the response header."""
    risk_label = RISK_LABELS.get(risk_tolerance, "Moderate")
    
    lines = [
        "",
        DIVIDER_HEAVY,
        "  YIELD INTELLIGENCE REPORT",
        DIVIDER_HEAVY,
        "",
        f"  Query:        {query[:50]}{'...' if len(query) > 50 else ''}",
        f"  Amount:       {format_currency(amount)} {token}",
        f"  Risk Profile: {risk_label}",
        f"  Results:      {num_results} opportunities found",
        "",
        DIVIDER_HEAVY,
    ]
    
    return "\n".join(lines)


def format_recommendation(rec: Recommendation, detailed: bool = True) -> str:
    """Format a single recommendation."""
    opp = rec.opportunity
    chain_symbol = CHAIN_SYMBOLS.get(opp.chain.lower(), opp.chain.upper())
    
    lines = [
        "",
        f"  #{rec.rank}  {opp.protocol}",
        f"      {opp.symbol} on {opp.chain.title()}",
        "",
        DIVIDER_LIGHT,
        "",
        f"      APY:          {format_apy(opp.apy):<12} Net APY:     {format_apy(rec.net_apy)}",
        f"      TVL:          {format_currency(opp.tvl_usd):<12} Risk:        {format_risk_bar(opp.risk_score)}",
        "",
        f"      30-Day Yield: {format_currency(rec.earnings_30d):<12} 1-Year:      {format_currency(rec.earnings_1y)}",
        f"      Entry Cost:   {format_currency(rec.total_entry_cost_usd)}",
        "",
    ]
    
    if rec.requires_bridge and rec.bridge_route:
        route = rec.bridge_route
        lines.extend([
            f"      Bridge:       {route.from_chain.title()} -> {route.to_chain.title()}",
            f"                    via {route.bridge_name} (~{format_time(route.estimated_time_seconds)}, {format_currency(route.total_cost_usd)})",
            "",
        ])
    
    if detailed:
        lines.extend([
            DIVIDER_DOT,
            "",
            "      REASONING:",
            f"      {_wrap_text(rec.why_recommended, 60, 6)}",
            "",
        ])
        
        if rec.warnings:
            lines.extend([
                "      WARNINGS:",
            ])
            for warning in rec.warnings:
                lines.append(f"      - {warning}")
            lines.append("")
        
        lines.extend([
            "      EXECUTION STEPS:",
        ])
        for step in rec.execution_steps:
            lines.append(f"      {step}")
        lines.append("")
    
    lines.append(DIVIDER_LIGHT)
    
    return "\n".join(lines)


def format_summary(recommendations: list[Recommendation]) -> str:
    """Format a quick summary table."""
    if not recommendations:
        return ""
    
    lines = [
        "",
        "  QUICK COMPARISON",
        DIVIDER_LIGHT,
        "",
        "  Rank  Protocol              Chain       APY      TVL        Risk",
        "  " + "-" * 66,
    ]
    
    for rec in recommendations[:5]:
        opp = rec.opportunity
        risk_indicator = "*" * min(int(opp.risk_score), 5)
        
        lines.append(
            f"  {rec.rank:<5} {opp.protocol:<20} {opp.chain.title():<10} "
            f"{format_apy(opp.apy):<8} {format_currency(opp.tvl_usd):<10} {risk_indicator}"
        )
    
    lines.extend([
        "",
        DIVIDER_LIGHT,
    ])
    
    return "\n".join(lines)


def format_warnings(warnings: list[str]) -> str:
    """Format global warnings."""
    if not warnings:
        return ""
    
    lines = [
        "",
        "  IMPORTANT NOTES",
        DIVIDER_LIGHT,
    ]
    
    for warning in warnings:
        lines.append(f"  * {warning}")
    
    lines.extend([
        "",
        DIVIDER_LIGHT,
    ])
    
    return "\n".join(lines)


def format_footer() -> str:
    """Format the response footer."""
    lines = [
        "",
        DIVIDER_HEAVY,
        "",
        "  DISCLAIMER: This is not financial advice. Always do your own research.",
        "  DeFi protocols carry inherent risks including smart contract vulnerabilities,",
        "  impermanent loss, and protocol insolvency. Never invest more than you can",
        "  afford to lose.",
        "",
        DIVIDER_HEAVY,
        "",
    ]
    
    return "\n".join(lines)


def format_no_results(query: str, risk_tolerance: RiskTolerance) -> str:
    """Format response when no results found."""
    risk_label = RISK_LABELS.get(risk_tolerance, "Moderate")
    
    lines = [
        "",
        DIVIDER_HEAVY,
        "  YIELD INTELLIGENCE REPORT",
        DIVIDER_HEAVY,
        "",
        f"  Query: {query[:50]}{'...' if len(query) > 50 else ''}",
        f"  Risk Profile: {risk_label}",
        "",
        DIVIDER_LIGHT,
        "",
        "  No matching yield opportunities found.",
        "",
        "  Suggestions:",
        "  - Try adjusting your risk tolerance",
        "  - Consider different tokens or chains",
        "  - Lower your minimum TVL requirements",
        "",
        DIVIDER_HEAVY,
        "",
    ]
    
    return "\n".join(lines)


def format_error(error: str, query: str) -> str:
    """Format error response."""
    lines = [
        "",
        DIVIDER_HEAVY,
        "  YIELD INTELLIGENCE REPORT - ERROR",
        DIVIDER_HEAVY,
        "",
        f"  Query: {query[:50]}{'...' if len(query) > 50 else ''}",
        "",
        DIVIDER_LIGHT,
        "",
        "  An error occurred while processing your request:",
        f"  {error}",
        "",
        "  Please try again or adjust your query.",
        "",
        DIVIDER_HEAVY,
        "",
    ]
    
    return "\n".join(lines)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================


def _wrap_text(text: str, width: int, indent: int) -> str:
    """Wrap text to specified width with indentation."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(" ".join(current_line))
    
    indent_str = " " * indent
    return f"\n{indent_str}".join(lines)


# ==============================================================================
# NODE FUNCTION
# ==============================================================================


def format_response(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: Format the final response.
    
    Generates a beautiful, structured text response containing
    all recommendations with reasoning and execution steps.
    """
    if state.error:
        formatted = format_error(state.error, state.user_query)
        return {
            "formatted_response": formatted,
            "processing_step": "formatting_complete_error",
        }
    
    recommendations = state.recommendations
    
    if not recommendations:
        formatted = format_no_results(
            state.user_query,
            state.risk_tolerance,
        )
        return {
            "formatted_response": formatted,
            "processing_step": "formatting_complete_no_results",
        }
    
    risk_tolerance = state.risk_tolerance
    if isinstance(risk_tolerance, str):
        risk_tolerance = RiskTolerance(risk_tolerance)
    
    sections = []
    
    sections.append(
        format_header(
            query=state.user_query,
            amount=state.amount or 0,
            token=state.token or "USD",
            risk_tolerance=risk_tolerance,
            num_results=len(recommendations),
        )
    )
    
    sections.append(format_summary(recommendations))
    
    for i, rec in enumerate(recommendations):
        detailed = i < 3
        sections.append(format_recommendation(rec, detailed=detailed))
    
    if state.warnings:
        sections.append(format_warnings(state.warnings))
    
    sections.append(format_footer())
    
    formatted = "\n".join(sections)
    
    return {
        "formatted_response": formatted,
        "processing_step": "formatting_complete",
    }


# ==============================================================================
# TESTING UTILITY
# ==============================================================================


def test_formatter() -> None:
    """Test formatter with sample data."""
    print("\nTesting Response Formatter")
    print("=" * 50)
    
    from yield_agent.state import (
        AgentState,
        Recommendation,
        YieldOpportunity,
        ILRisk,
        BridgeRoute,
    )
    
    mock_opp = YieldOpportunity(
        pool_id="aave-usdc-arb",
        protocol="Aave v3",
        protocol_slug="aave-v3",
        chain="arbitrum",
        pool_name="Aave USDC",
        symbol="USDC",
        apy=5.2,
        tvl_usd=150_000_000,
        risk_score=2.0,
        il_risk=ILRisk.NONE,
        audited=True,
        protocol_age_days=600,
    )
    
    mock_route = BridgeRoute(
        from_chain="ethereum",
        from_chain_id=1,
        to_chain="arbitrum",
        to_chain_id=42161,
        token="USDC",
        token_address="0x...",
        amount=10000,
        bridge_name="Stargate",
        estimated_time_seconds=120,
        gas_cost_usd=5.0,
        bridge_fee_usd=2.0,
        total_cost_usd=7.0,
        estimated_output=9993.0,
        slippage_percent=0.5,
    )
    
    mock_rec = Recommendation(
        rank=1,
        opportunity=mock_opp,
        input_amount=10000,
        input_token="USDC",
        earnings_30d=43.33,
        earnings_1y=520.0,
        requires_bridge=True,
        bridge_route=mock_route,
        net_apy=5.13,
        total_entry_cost_usd=7.0,
        why_recommended="Aave v3 offers 5.20% APY on Arbitrum. High liquidity with $150M TVL. Protocol is audited. Established protocol (1.6 years). Requires bridging via Stargate (~2 min, $7.00).",
        warnings=["Protocol has been audited"],
        execution_steps=[
            "1. Bridge 10,000.00 USDC from Ethereum to Arbitrum using Stargate",
            "2. Wait for bridge confirmation (~2 minutes)",
            "3. Go to Aave v3 on Arbitrum",
            "4. Navigate to the USDC pool",
            "5. Approve USDC spending (one-time transaction)",
            "6. Deposit 10,000.00 USDC into the pool",
            "7. Confirm transaction and start earning 5.20% APY",
        ],
    )
    
    state = AgentState(
        user_query="Where should I put 10k USDC for the best yield?",
        amount=10000,
        token="USDC",
        current_chain="ethereum",
        risk_tolerance=RiskTolerance.MODERATE,
        recommendations=[mock_rec],
        warnings=["Gas prices are currently elevated on Ethereum"],
    )
    
    result = format_response(state)
    print(result["formatted_response"])


if __name__ == "__main__":
    test_formatter()
