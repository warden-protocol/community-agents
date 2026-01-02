# Warden Yield Intelligence Agent

A Cross-Chain DeFi Yield Discovery and Optimization Agent built for the [Warden Protocol Agent Builder Incentive Programme](https://docs.wardenprotocol.org/build-an-agent/introduction).

```
================================================================================
    YIELD INTELLIGENCE AGENT
    Cross-Chain DeFi Yield Discovery & Optimization
================================================================================

    "Where should I put 10k USDC for the best yield?"

                        |
                        v

    +----------------------------------------------------------+
    |  #1  Aave v3                                             |
    |      USDC on Arbitrum                                    |
    |                                                          |
    |      APY: 5.20%        Net APY: 5.13%                    |
    |      TVL: $150.00M     Risk: [**........] 2.0/10 LOW     |
    |                                                          |
    |      30-Day Yield: $43.33    1-Year: $520.00             |
    |      Entry Cost: $7.00                                   |
    |                                                          |
    |      Bridge: Ethereum -> Arbitrum via Stargate (~2m)     |
    +----------------------------------------------------------+

================================================================================
```

## Overview

The Yield Intelligence Agent takes natural language queries and returns ranked yield opportunities across multiple blockchain networks. It analyzes APY, TVL, risk scores, audit status, protocol age, and bridging costs to provide comprehensive recommendations.

### Key Features

- **Natural Language Understanding**: Ask questions like "Where should I put 10k USDC?" or "Find me safe ETH staking yields on Arbitrum"
- **Multi-Chain Support**: Ethereum, Arbitrum, Optimism, Polygon, Base, Avalanche, BNB Chain
- **Risk-Adjusted Ranking**: Composite scoring based on APY, TVL, audits, protocol age, and impermanent loss risk
- **Bridge Cost Analysis**: Factors in cross-chain bridging costs and time via LI.FI
- **Gas Estimation**: Real-time gas prices for accurate entry cost calculations
- **Execution Steps**: Step-by-step instructions to execute each opportunity

## Architecture

```
+------------------------------------------------------------------+
|                    YIELD INTELLIGENCE AGENT                       |
+------------------------------------------------------------------+
|                                                                   |
|   START                                                           |
|     |                                                             |
|     v                                                             |
|   [Parse Input] -----> Extract amount, token, risk preference     |
|     |                                                             |
|     v                                                             |
|   [Fetch Yields] ----> DeFiLlama API (7 chains, 100+ protocols)   |
|     |                                                             |
|     v                                                             |
|   [Find Routes] -----> LI.FI Bridge Aggregator                    |
|     |                                                             |
|     v                                                             |
|   [Rank & Score] ----> Composite scoring with risk weights        |
|     |                                                             |
|     v                                                             |
|   [Format Response] -> Professional structured output             |
|     |                                                             |
|     v                                                             |
|   END                                                             |
|                                                                   |
+------------------------------------------------------------------+
```

## Quick Start

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/rudazy/warden-yield-agent.git
cd warden-yield-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys (optional - agent works without them)
# - ANTHROPIC_API_KEY or OPENAI_API_KEY (for LLM features)
# - LIFI_API_KEY (optional, for better bridge routing)
# - BLOCKNATIVE_API_KEY (optional, for better gas estimates)
```

### Run Locally

```python
from yield_agent import run_agent

response = run_agent(
    query="Where should I put 10k USDC for the best yield?",
    amount=10000,
    token="USDC",
    current_chain="ethereum",
    risk_tolerance="moderate",
)

print(response)
```

### Run with LangGraph CLI

```bash
# Install LangGraph CLI
pip install langgraph-cli

# Start the server
langgraph dev
```

## API Reference

### Main Functions

#### `run_agent(query, **kwargs)`

Run the yield agent with a natural language query.

**Parameters:**
- `query` (str): Natural language question about yields
- `amount` (float, optional): Investment amount
- `token` (str, optional): Token symbol (e.g., "USDC", "ETH")
- `current_chain` (str, optional): User's current chain
- `risk_tolerance` (str, optional): "conservative", "moderate", or "aggressive"
- `preferred_chains` (list, optional): Chains to search
- `excluded_protocols` (list, optional): Protocols to exclude

**Returns:** Formatted response string

### Example Queries

```python
# Basic yield search
run_agent("Where should I put 10k USDC?")

# Risk-aware search
run_agent("Find me safe stablecoin yields", risk_tolerance="conservative")

# Chain-specific search
run_agent("Best ETH staking on Arbitrum", preferred_chains=["arbitrum"])

# High-risk search
run_agent("I want to ape 50k into the highest yields", risk_tolerance="aggressive")
```

## Supported Chains

| Chain     | Chain ID | Native Token |
|-----------|----------|--------------|
| Ethereum  | 1        | ETH          |
| Arbitrum  | 42161    | ETH          |
| Optimism  | 10       | ETH          |
| Polygon   | 137      | MATIC        |
| Base      | 8453     | ETH          |
| Avalanche | 43114    | AVAX         |
| BNB Chain | 56       | BNB          |

## Risk Scoring

The agent uses a composite risk scoring system (1-10, lower is safer):

| Factor | Weight (Conservative) | Weight (Moderate) | Weight (Aggressive) |
|--------|----------------------|-------------------|---------------------|
| APY    | 25%                  | 35%               | 50%                 |
| TVL    | 25%                  | 20%               | 15%                 |
| Risk   | 30%                  | 25%               | 15%                 |
| Cost   | 20%                  | 20%               | 20%                 |

### Risk Factors Considered

- **TVL**: Higher TVL = lower risk
- **Audit Status**: Audited protocols receive bonus
- **Protocol Age**: Older protocols = more trust
- **APY Sustainability**: Very high APYs increase risk score
- **Impermanent Loss**: LP positions assessed for IL risk

## Data Sources

| Source      | Data Provided                    | API Key Required |
|-------------|----------------------------------|------------------|
| DeFiLlama   | Yield pools, TVL, APY            | No               |
| LI.FI       | Bridge routes, quotes            | Optional         |
| Blocknative | Gas prices (Ethereum)            | Optional         |
| Public RPCs | Gas prices (other chains)        | No               |

## Deployment

### LangGraph Cloud (Recommended)

1. Push your repository to GitHub
2. Connect to [LangGraph Cloud](https://www.langchain.com/langgraph)
3. Deploy from the repository

### Self-Hosted

```bash
# Install server dependencies
pip install -e ".[server]"

# Run with uvicorn
uvicorn yield_agent.server:app --host 0.0.0.0 --port 8000
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e ".[server]"

EXPOSE 8000
CMD ["langgraph", "up"]
```

## Project Structure

```
warden-yield-agent/
├── src/
│   └── yield_agent/
│       ├── __init__.py          # Package exports
│       ├── state.py             # State definitions & data models
│       ├── graph.py             # LangGraph definition
│       ├── tools/
│       │   ├── __init__.py      # Tools index
│       │   ├── defillama_client.py  # DeFiLlama API
│       │   ├── lifi_client.py       # LI.FI bridge API
│       │   └── gas_client.py        # Gas estimation
│       └── nodes/
│           ├── __init__.py          # Nodes index
│           ├── input_parser.py      # Query parsing
│           ├── yield_fetcher.py     # Yield data fetching
│           ├── route_finder.py      # Bridge routing
│           ├── ranking_engine.py    # Scoring & ranking
│           └── response_formatter.py # Output formatting
├── langgraph.json               # LangGraph configuration
├── pyproject.toml               # Dependencies
├── .env.example                 # Environment template
└── README.md                    # Documentation
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Warden Protocol](https://wardenprotocol.org/) for the Agent Builder Programme
- [LangGraph](https://www.langchain.com/langgraph) for the agent framework
- [DeFiLlama](https://defillama.com/) for yield data
- [LI.FI](https://li.fi/) for bridge aggregation

---

Built with care for the Warden Protocol ecosystem.
