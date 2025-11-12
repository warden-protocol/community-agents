# CoinGecko Agent

A cryptocurrency analysis agent that uses Schema-Guided Reasoning (SGR) to provide detailed, quantitative analysis of digital assets.

## Features

- Real-time cryptocurrency data from CoinGecko API
- AI-powered analysis using OpenAI GPT models
- Structured 5-step reasoning process
- Risk assessment (volatility, liquidity, market cap)
- Performance analysis and price trend evaluation
- Comparative token analysis (up to 2 tokens)

## Prerequisites

- Node.js 20+
- Yarn package manager
- OpenAI API key
- CoinGecko API key

## Installation

From the root of the monorepo:

```bash
yarn install
```

## Configuration

Copy the `.env.example` file to `.env` and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env` with your actual API keys.

## Running the Agent

### Start the Agent

```bash
yarn start
```

The agent will process predefined questions about cryptocurrencies and output structured analysis for each.

### Example Questions

The default questions in `src/index.ts`:
- "What is the price of the BTC?"
- "Which token has the highest 24h price change?"
- "What is the price of the eth token at 3 Jan 2025?"
- "What do you think about polkadot?"
- "Which token should I buy: sui or polkadot?"
- "What market cap has the eth?"
- "Compare bitcoin and ethereum"

You can modify these questions in `src/index.ts`.

## Output Structure

The agent provides structured responses with:

1. **Token Extraction** - Identifies tokens from the question
2. **Data Fetching** - Retrieves comprehensive data from CoinGecko
3. **Data Validation** - Assesses data completeness and quality
4. **Data Analysis** - Evaluates risk and performance metrics
5. **Confident Answer** - Provides actionable insights with reasoning

See [EXAMPLES.md](./EXAMPLES.md) for complete examples of agent output.

### Full Data Examples

Complete JSON response files are available in the [examples](./examples) directory. Each file contains:

```json
{
  "question": "string - the original question",
  "response": {
    "messages": "array - internal processing steps and tool calls",
    "structuredResponse": "object - the structured agent analysis and answer"
  }
}
```

## Development

### Available Commands

```bash
# Build the package
yarn build

# Run tests
yarn test

# Lint code
yarn lint

# Clean build artifacts
yarn clean
```

## Testing

Run the test suite:

```bash
yarn test
```

Tests are located in the `tests/` directory and use Vitest.

## Technology Stack

- **TypeScript** - Type-safe JavaScript
- **LangChain** - AI application framework
- **OpenAI API** - Language models
- **CoinGecko MCP** - Cryptocurrency data provider

## Important Notes

- The agent analyzes a maximum of 2 cryptocurrencies per request
- Only tokens explicitly mentioned in questions are analyzed
- All analysis is for informational purposes only - **not financial advice**
