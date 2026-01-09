# DeFi Risk Scanner Agent

> AI-powered DeFi protocol risk assessment tool for Warden Protocol

## Overview

DeFi Risk Scanner analyzes DeFi protocols across multiple dimensions to generate comprehensive risk scores, helping users make informed investment decisions.

## Features

- **Multi-source Data Collection**: Aggregates data from DeFiLlama, Certik, DeBank, and Etherscan
- **Comprehensive Risk Scoring**: Evaluates contract security, TVL stability, team transparency, and on-chain behavior
- **Real-time Warnings**: Identifies critical risk factors like whale concentration, TVL drops, and missing audits
- **LangGraph Integration**: Built on LangGraph for Warden Protocol compatibility

## Risk Scoring Model

| Component | Weight | Factors |
|-----------|--------|---------|
| Contract Security | 40% | Audit status, contract age, code verification |
| TVL & Liquidity | 30% | TVL size, change rate, multi-chain presence |
| Team Transparency | 15% | Doxxed vs anonymous, public team |
| On-chain Behavior | 15% | Whale concentration, holder count, abnormal activity |

### Risk Levels

- 🔴 **HIGH RISK** (Score < 50): Significant concerns, proceed with extreme caution
- 🟡 **MEDIUM RISK** (Score 50-70): Some risk factors present, DYOR
- 🟢 **LOW RISK** (Score > 70): Relatively safe, standard DeFi risks apply

## Quick Start

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional)

# Run in development
npm run dev

# Build for production
npm run build
npm start
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| PORT | No | Server port (default: 3000) |
| OPENAI_API_KEY | No | For future AI analysis |
| DEBANK_API_KEY | No | DeBank Pro API key |
| CERTIK_API_KEY | No | Certik API key |
| ETHERSCAN_API_KEY | No | Etherscan API key |

> Note: The scanner works without API keys using DeFiLlama (free) and mock data for other sources.

## API Reference

### Health Check

```
GET /health
```

### Scan Protocol

```
POST /threads/{thread_id}/runs/wait
Content-Type: application/json

{
  "input": {
    "messages": [
      { "role": "user", "content": "aave" }
    ]
  }
}
```

Response:
```json
{
  "status": "success",
  "outputs": {
    "messages": [{
      "type": "ai",
      "content": "🟢 DeFi Risk Report: Aave...",
      "additional_kwargs": {
        "risk_score": 82,
        "risk_level": "LOW"
      }
    }]
  }
}
```

### Supported Inputs

- Protocol name: `aave`, `uniswap`, `compound`
- Contract address: `0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9`

## Architecture

```
User Input
    │
    ▼
┌─────────────┐
│ Parse Input │ → Identify protocol/address
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────┐
│        Parallel Data Collection       │
│  ┌──────────┐ ┌────────┐ ┌────────┐  │
│  │DeFiLlama│ │ Certik │ │DeBank  │  │
│  │  (TVL)   │ │(Audit) │ │(Chain) │  │
│  └──────────┘ └────────┘ └────────┘  │
└──────────────────┬───────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │  Risk Scorer   │ → Calculate weighted score
          └───────┬────────┘
                  │
                  ▼
          ┌────────────────┐
          │ Risk Report    │ → Generate warnings & summary
          └────────────────┘
```

## Example Output

```
🟡 DeFi Risk Report: Example Protocol

📊 Overall Score: 58/100 (MEDIUM RISK)

Component Scores:
• Contract Security: 45/100
• TVL & Liquidity: 72/100
• Team Transparency: 50/100
• On-chain Behavior: 65/100

⚠️ Warnings:
🚨 Protocol has NOT been audited
⚠️ Team is anonymous
⚠️ High whale concentration: 62.3% in top 10

💡 Summary: This protocol has moderate risk factors. Found 1 critical issue(s). Found 2 warning(s). Always DYOR before investing.
```

## Data Sources

| Source | Data | Status | Notes |
|--------|------|--------|-------|
| [DeFiLlama](https://defillama.com) | TVL, protocols | ✅ **Real API** | Free, no API key required |
| [Certik](https://certik.com) | Audits, security scores | ⚠️ Mock* | Requires paid API key |
| [DeBank](https://debank.com) | Token holders, on-chain | ⚠️ Mock* | Requires paid API key |
| [Etherscan](https://etherscan.io) | Contract verification | ⚠️ Mock* | Free tier available |

> **\*Mock Data**: Without API keys, these sources return simulated data based on protocol reputation.
> The mock data provides reasonable estimates for well-known protocols (Aave, Uniswap, Compound, etc.)
> but should not be relied upon for investment decisions. Add your API keys in `.env` for real data.

### Current Default Behavior

- **TVL & Protocol Data**: Real-time from DeFiLlama (always accurate)
- **Audit Status**: Mock data assumes major protocols are audited
- **On-chain Behavior**: Mock data with typical whale concentration values
- **Contract Info**: Mock data with estimated contract age

## Deployment

### Render

1. Connect GitHub repository
2. Set environment variables
3. Build command: `npm run build`
4. Start command: `npm start`

### Docker

```bash
docker build -t defi-risk-scanner .
docker run -p 3000:3000 --env-file .env defi-risk-scanner
```

## License

MIT

## Links

- [Warden Protocol](https://wardenprotocol.org)
- [Agent Builder Programme](https://wardenprotocol.org/agent-builder)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)
