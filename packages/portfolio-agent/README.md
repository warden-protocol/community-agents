# Portfolio Analysis Agent

A cryptocurrency portfolio analysis agent that uses Schema-Guided Reasoning (SGR) to provide comprehensive portfolio reports and performance analysis for EVM and Solana wallets.

## Features

- Multi-chain wallet support (EVM networks and Solana)
- Historical portfolio performance tracking (daily, weekly, monthly)
- Real-time token balance and price data
- Portfolio composition and diversification analysis
- Performance comparison against market trends
- AI-powered insights using OpenAI GPT models
- Structured 5-step reasoning process

## Prerequisites

- Node.js 20+
- Yarn package manager
- OpenAI API key
- CoinGecko API key
- Alchemy API key (for EVM wallet data)

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

### Start the agent

```bash
yarn start
```

or in development mode:

```bash
yarn dev
```

The agent will analyze your wallet portfolio and provide comprehensive reports based on your request.

### Example Usage

In `src/index.ts`, configure your wallet addresses and questions:

```typescript
const walletAddresses = {
  evm: '0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6',    // Your Ethereum/EVM address
  solana: '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM', // Your Solana address
};

const questions = [
  'Review my portfolio',
  'Give me a daily report',
  'Analyze my portfolio and show which tokens are underperforming',
  'How has my portfolio changed in the last 7 days?',
  'What is my total profit/loss this month?',
  'Which coins in my portfolio had the highest growth this month?',
];
```


You can modify the wallet addresses and questions in `src/index.ts`.

## Output Structure

The agent provides structured responses with a 5-step analysis process:

1. **Request Parsing** - Extracts time period (daily/weekly/monthly) and wallet addresses
2. **Portfolio Data Fetching** - Retrieves wallet balances and historical price data
3. **Portfolio Composition Analysis** - Analyzes current holdings, top tokens, and diversification
4. **Performance Analysis** - Calculates wins/losses, best/worst performers over the time period
5. **Report Generation** - Provides comprehensive portfolio report with insights and recommendations

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
- **OpenAI API** - Language models (GPT-4o-mini by default)
- **CoinGecko API** - Cryptocurrency price data
- **Alchemy API** - EVM wallet balance and transaction data

## Important Notes

- The agent analyzes complete portfolio holdings across EVM and Solana wallets
- Supports daily, weekly, and monthly performance tracking
- Provides market context by comparing portfolio performance against top gainers/losers
- All analysis is for informational purposes only - **not financial advice**
