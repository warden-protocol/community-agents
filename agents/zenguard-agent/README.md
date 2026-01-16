# ZenGuard Agent

> AI-powered emotional guardian that protects crypto traders from panic-driven decisions

## Problem Statement

80% of retail crypto traders lose money, primarily due to emotional decisions rather than poor analysis. FOMO buying at peaks and panic selling at bottoms cause more losses than any technical mistake. Currently, no tool actively prevents traders from making irrational decisions in the heat of the moment.

## Solution

ZenGuard is an AI agent that monitors your emotional state through conversation analysis and takes protective action when it detects dangerous trading impulses:

1. **Sentiment Analysis** - Analyzes user messages for fear, greed, panic indicators
2. **Risk Scoring** - Calculates an "Irrationality Index" (0.0 - 1.0)
3. **Context Memory** - Remembers conversation history to understand full context
4. **Protective Action** - Integrates with Warden Protocol to lock assets when needed
5. **Scam Detection** - Warns users about potential fraud (e.g., "guaranteed 3000% returns")

## How It Works

```
User Input
    |
    v
+-------------------+
| Perception Node   | --> Sentiment Score + Intensity
+--------+----------+
         |
         v
+-------------------+
|   Analyst Node    | --> Irrationality Index (0-1)
+--------+----------+
         |
         v
    [ Risk > 0.8? ]
      /         \
    YES          NO
     |            |
     v            v
+---------+  +------------+
| LOCK    |  | Therapist  |
| Assets  |  | Response   |
+---------+  +------------+
```

## Features

- Real-time emotion detection (fear, greed, panic, FOMO)
- Context-aware analysis (remembers last 3 messages for context)
- Conversation memory (full session history)
- Multi-language support (English, Chinese)
- Scam/fraud warning system
- Warden Protocol integration (asset locking)
- Production-ready HTTP API
- Session management with auto-cleanup
- Rate limiting (100 req/15min)

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | LangGraph (StateGraph) |
| Language | TypeScript |
| LLM | OpenAI GPT-4o |
| API Server | Express.js |
| Blockchain | Base (via Viem) |
| Deployment | Docker |

## Quick Start

### Prerequisites
- Node.js 20+
- OpenAI API Key

### Installation

```bash
# Clone the repository
git clone https://github.com/ccclin111/zenguard-agent.git
cd zenguard-agent

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and add your API keys

# Run in CLI mode
npm run dev

# Run in API mode
npm run dev:api

# Build for production
npm run build

# Run production server
npm run start:prod
```

### Environment Variables

```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
BASE_RPC_URL=https://mainnet.base.org
WARDEN_PRIVATE_KEY=your_warden_key
```

## API Reference

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "agent": "ZenGuard",
  "version": "1.0.0",
  "activeSessions": 0,
  "maxSessions": 1000,
  "sessionTTL": "30 minutes"
}
```

### Chat Endpoint

```
POST /api/chat
Content-Type: application/json
```

Request:
```json
{
  "message": "I'm thinking about going all-in on this new meme coin",
  "sessionId": "optional-session-id"
}
```

Response:
```json
{
  "response": "I understand the excitement, but going all-in is rarely wise...",
  "sessionId": "abc-123-def",
  "historyLength": 2,
  "metrics": {
    "sentimentScore": -0.3,
    "sentimentIntensity": 0.7,
    "irrationalityIndex": 0.65
  },
  "interventionLevel": "WARNING",
  "wardenIntent": null
}
```

### Clear Session

```
DELETE /api/session/:sessionId
```

### List Sessions

```
GET /api/sessions
```

## Demo Scenarios

| Input | Risk Index | Intervention | Reason |
|-------|------------|--------------|--------|
| "Hi, how's the market?" | 0.05 | NONE | Neutral inquiry |
| "I'm a bit anxious about the dip" | 0.44 | NONE | Normal concern |
| "BTC will hit 200k!" | 0.55 | WARNING | Excessive optimism |
| "Someone promised 3000% returns" | 0.91 | HARD_LOCK | Scam indicator |
| "I lost everything! 100x leverage!" | 0.91 | HARD_LOCK | Panic + dangerous action |

## Risk Engine

The Irrationality Index is calculated using:

```
Index = (sentiment_weight * |sentiment| * intensity)
      + (volatility_weight * market_volatility)
      + (baseline_weight * baseline)
```

With Sigmoid activation for smooth 0-1 output.

**Intervention Thresholds:**
- `> 0.8` = HARD_LOCK (Assets locked via Warden)
- `> 0.5` = WARNING (Cautionary response)
- `< 0.5` = NONE (Normal conversation)

## Why ZenGuard is Different

| Typical Crypto Bot | ZenGuard |
|--------------------|----------|
| Passively answers queries | Actively protects users |
| Provides information | Prevents harmful actions |
| No emotional awareness | Sentiment-aware |
| Stateless | Remembers context |
| Tool for trading | Shield against self-harm |

## Warden Protocol Integration

ZenGuard leverages Warden Protocol's security infrastructure:

- **Intent Creation**: When HARD_LOCK is triggered, creates a Warden Intent to lock assets
- **Simulation Mode**: Runs in mock mode if no Warden key is configured
- **Future Integration**: Will utilize Warden Keychains and Rules for granular control

## LangGraph Configuration

```json
{
  "$schema": "https://langchain-ai.github.io/langgraph/schemas/langgraph.json",
  "graphs": {
    "zenguard": {
      "file": "./src/graph/workflow.ts",
      "graph": "zenGuardWorkflow"
    }
  },
  "env": ".env",
  "runtime": {
    "node_version": "20"
  }
}
```

## Project Structure

```
zenguard-agent/
├── src/
│   ├── index.ts           # CLI entry point
│   ├── server.ts          # HTTP API server
│   ├── graph/
│   │   ├── nodes.ts       # LangGraph nodes (4 nodes)
│   │   └── workflow.ts    # StateGraph definition
│   ├── logic/
│   │   └── risk_engine.ts # Irrationality Index calculation
│   ├── config/
│   │   ├── models.ts      # LLM configuration
│   │   └── warden.ts      # Warden SDK setup
│   ├── knowledge/
│   │   └── grok_curated.json # Training examples
│   └── tools/
│       ├── warden_protector.ts # Asset locking tool
│       └── base_forensics.ts   # On-chain analysis
├── dist/                  # Compiled JavaScript
├── langgraph.json         # LangGraph Cloud config
├── Dockerfile             # Production container
├── package.json
├── tsconfig.json
└── README.md
```

## Docker Deployment

```bash
# Build the image
docker build -t zenguard-agent .

# Run the container
docker run -p 3000:3000 --env-file .env zenguard-agent
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Run CLI in development |
| `npm run dev:api` | Run API server in development |
| `npm run build` | Compile TypeScript |
| `npm run start:prod` | Run production API server |
| `npm run start` | Run production CLI |

## Security Features

- **Rate Limiting**: 100 requests per 15 minutes per IP
- **Session TTL**: Auto-cleanup after 30 minutes of inactivity
- **Session Limit**: Maximum 1000 concurrent sessions
- **Input Validation**: Message required, proper error responses

## License

MIT

## Author

@xxxaak__

## Links

- [Warden Protocol](https://wardenprotocol.org)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)
- [Warden Agent Builder Programme](https://wardenprotocol.org/agent-builder)
