# Yield Optimization Agent with tx data

An AI-powered agent that helps users find the best and safest staking opportunities for their tokens across multiple DeFi protocols and chains with tx data.

## 🚀 Quick Start - REST API

We now provide a **production-ready REST API** with Swagger documentation!

```bash
# Install dependencies
yarn install

# Start the API server
yarn start:api

# Or with auto-reload for development
yarn dev:api
```

**Access the Swagger UI:** `http://localhost:3000/api-docs`

## Features

- 🔍 **Token Discovery**: Search tokens by name, symbol, or contract address
- 🌐 **Multi-Chain Support**: Ethereum, Arbitrum, Optimism, Polygon, Base, Avalanche, BNB Chain
- 🏦 **Protocol Discovery**: Automatically find all available staking protocols for any token
- 🛡️ **Safety Evaluation**: Comprehensive safety scoring based on TVL, reputation, audits, and history
- 💰 **Transaction Generation**: Generate approval and deposit transactions using Enso SDK
- ⚠️ **Safety First**: Mandatory safety warnings and comprehensive validation
- ⚡ **Optimized**: Returns top protocols only to minimize API usage and token consumption
- 🔄 **Rate Limit Handling**: Automatic retry with exponential backoff for API rate limits
- 🌐 **REST API**: Production-ready HTTP API with Swagger documentation

## Installation

```bash
# Install dependencies
yarn install
```

## Configuration

Create a `.env` file in the root directory:

```env
# Required
OPENAI_API_KEY=your_openai_api_key
ENSO_API_KEY=your_enso_api_key

# Optional but recommended (for token information)
COINGECKO_API_KEY=your_coingecko_demo_api_key

# API Server Configuration (for REST API)
PORT=3000
NODE_ENV=development
CORS_ORIGIN=*
RATE_LIMIT_MAX=100
```

**Note**: The CoinGecko API key is optional. If not provided, the agent will use fallback mock data for common tokens. For production use, a CoinGecko demo API key is recommended.

## Usage

### REST API Usage (Recommended)

```bash
# Start the API server
yarn start:api

# Make requests to the API
curl -X POST http://localhost:3000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Find staking opportunities for USDC on Ethereum"}'
```

**Interactive Documentation:** Visit `http://localhost:3000/api-docs` for the Swagger UI

### API Endpoints

The REST API provides the following endpoints:

- **Agent Endpoints**:

  - `POST /api/v1/agent/query` - Natural language queries to the AI agent
  - `POST /api/v1/agent/batch` - Batch processing (up to 10 queries)
  - `POST /api/v1/agent/quick` - Quick transaction generation

- **Token Endpoints**:

  - `GET /api/v1/tokens/search?query=USDC` - Search tokens by name/symbol
  - `GET /api/v1/tokens/info?token=USDC&chainId=1` - Get detailed token information

- **Protocol Endpoints**:

  - `POST /api/v1/protocols/discover` - Discover staking protocols for a token

- **Transaction Endpoints**:

  - `POST /api/v1/transactions/generate` - Generate transaction bundles

- **Utility Endpoints**:
  - `GET /api/v1/chains` - Get supported chains
  - `GET /health` - Health check

👉 **See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference**

### Programmatic Usage (TypeScript/JavaScript)

```typescript
import { runYieldAgent } from "./src";

const questions = [
  "Find staking opportunities for USDC",
  "What protocols can I stake ETH on Arbitrum?",
];

const results = await runYieldAgent(questions);
```

### Interactive Mode

The agent guides users through a step-by-step process:

1. **Token Input**: User provides token name or address
2. **Token Confirmation**: Agent fetches and displays token information
3. **Protocol Discovery**: Agent finds all available protocols across chains
4. **Safety Evaluation**: Protocols are ranked by safety and yield
5. **Protocol Selection**: User selects preferred protocol
6. **Transaction Generation**: Agent creates transaction bundle (approval + deposit if needed)

### Quick Mode

Users can provide all information in one command:

```
"Deposit 100 USDC on Arbitrum to Aave v3"
```

The agent will:

- Parse all inputs
- Validate everything
- Generate transaction bundle immediately
- Include all safety warnings

## API Reference

### Core Functions

#### `runYieldAgent(questions, options)`

Run the yield optimization agent with a list of questions.

**Parameters:**

- `questions: string[]` - Array of user questions
- `options?: AgentOptions` - Optional configuration
  - `modelName?: string` - OpenAI model name (default: "gpt-4o-mini")
  - `temperature?: number` - Model temperature (default: 0)
  - `maxTokens?: number` - Maximum tokens per response (default: 4000)
  - `maxRetries?: number` - Maximum retries for rate limits (default: 3)
  - `delayBetweenQuestionsMs?: number` - Delay between questions in ms (default: 2000)

**Returns:** `Promise<AgentResponse[]>`

**Example:**

```typescript
const results = await runYieldAgent(["Find staking for USDC on Arbitrum"], {
  modelName: "gpt-4o-mini",
  temperature: 0,
  maxTokens: 4000,
});
```

### Services

#### Token Info API (`src/agent/api.ts`)

- `getTokenInfo(input, chainId?, chainName?)` - Get token information
- `searchToken(query)` - Search tokens by name/symbol
- `getTokenByAddress(address, chainId)` - Get token by contract address

#### Enso Service (`src/agent/enso-service.ts`)

- `discoverProtocols(tokenAddress, chainId)` - Find protocols on a chain
- `discoverProtocolsMultiChain(tokenAddress)` - Find protocols across all chains
- `checkApprovalNeeded(...)` - Check if token approval is needed
- `generateTransactionBundle(...)` - Generate approval + deposit transactions

#### Safety Service (`src/agent/safety-service.ts`)

- `evaluateProtocolSafety(protocol)` - Evaluate protocol safety score
- `addSafetyScores(protocols, maxProtocols?)` - Add safety scores to protocols (limits evaluation to top protocols by TVL)
- `sortProtocolsBySafetyAndYield(protocols)` - Sort protocols by safety and yield

#### Validation (`src/agent/validation.ts`)

- `validateTokenInput(input)` - Validate token input
- `validateChain(chain)` - Validate chain
- `validateAmount(amount, balance, decimals)` - Validate amount
- `detectQuickMode(input)` - Detect quick mode input
- `parseQuickModeInput(input)` - Parse quick mode input

## Safety Features

### Mandatory Safety Warnings

All transaction objects include this warning:

```
⚠️ CRITICAL: This transaction object was generated by an AI agent.
Please verify all details (token address, protocol address, amount, chain)
before executing. Double-check on block explorer and protocol website.
This is not financial advice.
```

### Input Validation

- **Address Validation**: Validates Ethereum address format and checksum
- **Chain Validation**: Ensures chain is supported
- **Amount Validation**: Verifies amount is positive and within balance
- **Address + Chain Requirement**: When address is provided, chain MUST be specified

### Pre-Transaction Checks

Before generating any transaction, the agent verifies:

- Token exists on specified chain
- Protocol exists for token on chain
- User has sufficient balance
- Protocol safety evaluation
- All parameters are valid

## Supported Chains

- Ethereum (Chain ID: 1)
- Arbitrum (Chain ID: 42161)
- Optimism (Chain ID: 10)
- Polygon (Chain ID: 137)
- Base (Chain ID: 8453)
- Avalanche (Chain ID: 43114)
- BNB Chain (Chain ID: 56)

## Safety Scoring

Protocols are evaluated based on:

1. **TVL (Total Value Locked)**

   - > $100M: Very Safe
   - $10M - $100M: Safe
   - < $10M: Risky

2. **Protocol Reputation**

   - Trusted protocols (Aave, Compound, Lido, etc.)
   - Unknown protocols flagged

3. **Audit Status**

   - Verified audits from DefiLlama
   - Audit count and quality

4. **Historical Performance**
   - Protocol age and stability
   - Security incident history

## Transaction Flow

### With Approval Needed

1. Generate approval transaction
2. User executes approval transaction
3. Wait for confirmation
4. Generate deposit transaction
5. User executes deposit transaction

### Without Approval Needed

1. Generate deposit transaction
2. User executes deposit transaction

## Performance & Optimization

### Protocol Limiting

To optimize API usage and prevent token limit errors, the agent:

1. **Pre-filters by TVL**: Sorts protocols by Total Value Locked and selects top 20
2. **Evaluates safety**: Only evaluates safety scores for top 20 protocols (saves API credits)
3. **Returns top results**: Returns top 15 protocols sorted by safety + yield

This approach ensures:

- ✅ Reduced API credit consumption (evaluating 20 instead of 100+ protocols)
- ✅ No token limit errors (returning 15 instead of 100+ protocols)
- ✅ Best protocols still shown (top by TVL, then sorted by safety + yield)

### Rate Limiting & Retries

The agent includes automatic rate limit handling:

- **Automatic retry**: Retries on 429 rate limit errors with exponential backoff
- **Smart detection**: Distinguishes between rate limits (retryable) and quota issues (not retryable)
- **Configurable delays**: 2 second delay between questions by default
- **Max retries**: Configurable retry attempts (default: 3)

## Error Handling

The agent handles various error cases:

- Token not found
- No protocols available
- Invalid address format
- Unsupported chain
- Insufficient balance
- Network errors
- API rate limiting (with automatic retry)
- Quota/billing issues (with helpful error messages)

All errors include clear messages and suggestions.

## Development

### Project Structure

```
yield-agent/
├── src/
│   ├── agent/
│   │   ├── index.ts              # Main agent orchestration
│   │   ├── tools.ts               # LangChain tools
│   │   ├── api.ts                 # CoinGecko integration
│   │   ├── enso-service.ts        # Enso SDK wrapper
│   │   ├── safety-service.ts     # Safety evaluation
│   │   ├── validation.ts          # Input validation
│   │   ├── types.ts               # TypeScript types
│   │   ├── output-structure.ts   # Response schema
│   │   └── system-prompt.ts       # Agent system prompt
│   ├── api/
│   │   ├── server.ts              # Express server setup
│   │   ├── routes.ts              # API route definitions
│   │   ├── controllers.ts         # Request handlers
│   │   ├── middleware.ts          # Validation & error handling
│   │   ├── validation.ts          # Request validation schemas
│   │   ├── swagger.ts             # OpenAPI configuration
│   │   └── index.ts               # API module exports
│   ├── common/
│   │   ├── types.ts
│   │   ├── logger.ts
│   │   └── utils.ts
│   └── index.ts                  # Public API
├── package.json
├── tsconfig.json
├── README.md
├── API_DOCUMENTATION.md          # Complete API reference
└── Yield-Agent-API.postman_collection.json  # Postman collection
```

### Building

```bash
# Build TypeScript
yarn build

# Run linter
yarn lint

# Format code
yarn prettier
```

### Testing

```bash
# Run unit tests
yarn test

# Test API endpoints
yarn test:api
yarn test:api:full  # Includes AI agent tests
```

### API Testing

The API can be tested using:

1. **Swagger UI**: `http://localhost:3000/api-docs` - Interactive testing interface
2. **Postman**: Import `Yield-Agent-API.postman_collection.json`
3. **Test Script**: Run `yarn test:api` for automated tests

## Dependencies

### Core Agent

- **LangGraph**: Agent framework
- **Enso SDK**: Protocol discovery and transaction generation
- **CoinGecko API**: Token information (optional, uses mock data if not provided)
- **viem**: Ethereum utilities
- **Zod**: Schema validation
- **OpenAI API**: LLM for agent reasoning

### REST API

- **Express.js**: Web framework
- **Swagger UI**: Interactive API documentation
- **Helmet**: Security headers
- **CORS**: Cross-origin resource sharing
- **express-rate-limit**: Rate limiting

## API Usage Optimization

The agent is optimized to minimize API usage:

- **Protocol filtering**: Only evaluates top 20 protocols by TVL
- **Result limiting**: Returns top 15 protocols to user
- **Lazy initialization**: CoinGecko client only initialized when API key is available
- **Batch processing**: Safety evaluations processed in batches of 5
- **Token limits**: Configurable max tokens (default: 4000) to handle responses efficiently

## Important Notes

⚠️ **CRITICAL SAFETY REMINDERS:**

1. **Always verify transaction details** before executing
2. **Check token addresses** on block explorer
3. **Verify protocol addresses** on protocol website
4. **Review safety scores** before selecting protocols
5. **Start with small amounts** when trying new protocols
6. **This is not financial advice** - do your own research
