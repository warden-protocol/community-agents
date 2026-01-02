# Yield Agent API Documentation

Complete REST API documentation for the Yield Optimization Agent.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Getting Started

### Installation

```bash
# Install dependencies
yarn install

# Set up environment variables
# Create a .env file with your API keys
```

### Starting the Server

```bash
# Development mode (with auto-reload)
yarn dev:api

# Production mode
yarn start:api
```

The server will start on `http://localhost:3000` by default.

### Swagger Documentation

Once the server is running, you can access the interactive Swagger documentation at:

```
http://localhost:3000/api-docs
```

This provides a user-friendly interface to test all API endpoints.

## Authentication

Currently, the API does not require authentication for development purposes. For production deployments, you should implement authentication using API keys or JWT tokens.

## Base URL

**Development:** `http://localhost:3000/api/v1`

**Production:** `https://api.yieldagent.io/api/v1` (example)

## Endpoints

### Health Check

```http
GET /health
```

Check API server health status.

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2025-12-31T10:00:00.000Z",
  "uptime": 1234.56,
  "environment": "development",
  "version": "1.0.0"
}
```

---

### Agent Endpoints

#### Query Agent (Single Query)

```http
POST /api/v1/agent/query
```

Send a natural language query to the AI agent.

**Request Body:**

```json
{
  "query": "Find staking opportunities for USDC on Ethereum",
  "options": {
    "modelName": "gpt-4o-mini",
    "temperature": 0,
    "maxTokens": 4000
  }
}
```

**Response:**

```json
{
  "success": true,
  "query": "Find staking opportunities for USDC on Ethereum",
  "result": {
    "question": "Find staking opportunities for USDC on Ethereum",
    "response": {
      "answer": "I found 15 staking protocols for USDC on Ethereum...",
      "step": "protocol_discovery",
      "mode": "interactive",
      "protocols": [...],
      "confidence": "high"
    }
  },
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

#### Batch Query Agent

```http
POST /api/v1/agent/batch
```

Send multiple queries at once.

**Request Body:**

```json
{
  "queries": [
    "Find staking for USDC",
    "What protocols support ETH on Arbitrum?"
  ],
  "options": {
    "modelName": "gpt-4o-mini",
    "delayBetweenQuestionsMs": 2000
  }
}
```

**Response:**

```json
{
  "success": true,
  "count": 2,
  "results": [
    {
      "question": "Find staking for USDC",
      "response": {...}
    },
    {
      "question": "What protocols support ETH on Arbitrum?",
      "response": {...}
    }
  ],
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

#### Quick Transaction

```http
POST /api/v1/agent/quick
```

Generate transaction bundle directly with all parameters provided.

**Request Body:**

```json
{
  "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "chainId": 1,
  "protocolName": "aave",
  "amount": "100",
  "userAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

**Response:**

```json
{
  "success": true,
  "mode": "quick",
  "result": {
    "question": "Deposit 100 0xA0b... on chain 1 to aave...",
    "response": {
      "answer": "Transaction bundle ready...",
      "step": "quick_mode_complete",
      "tokenInfo": {...},
      "protocols": [{...}],
      "approvalTransaction": {...},
      "transaction": {...},
      "executionOrder": ["approve", "deposit"]
    }
  },
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

### Token Endpoints

#### Search Tokens

```http
GET /api/v1/tokens/search?query=USDC
```

Search for tokens by name or symbol.

**Query Parameters:**

- `query` (required): Token name or symbol

**Response:**

```json
{
  "success": true,
  "count": 1,
  "tokens": [
    {
      "name": "USD Coin",
      "symbol": "USDC",
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "chain": "Ethereum",
      "chainId": 1,
      "decimals": 6,
      "price": 1.0,
      "marketCap": 30000000000,
      "verified": true,
      "allChains": [...]
    }
  ],
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

#### Get Token Information

```http
GET /api/v1/tokens/info?token=USDC&chainId=1
```

Get detailed information about a specific token.

**Query Parameters:**

- `token` (required): Token name, symbol, or address
- `chainId` (optional): Chain ID (required if token is an address)
- `chainName` (optional): Chain name (alternative to chainId)

**Response:**

```json
{
  "success": true,
  "token": {
    "name": "USD Coin",
    "symbol": "USDC",
    "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "chain": "Ethereum",
    "chainId": 1,
    "decimals": 6,
    "price": 1.0,
    "marketCap": 30000000000,
    "verified": true,
    "allChains": [
      {
        "chainId": 1,
        "chainName": "Ethereum",
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
      },
      ...
    ]
  },
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

### Protocol Endpoints

#### Discover Protocols

```http
POST /api/v1/protocols/discover
```

Discover available staking protocols for a token.

**Request Body:**

```json
{
  "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "chainId": 1,
  "multiChain": false
}
```

**Parameters:**

- `tokenAddress` (required): Token contract address
- `chainId` (optional): Specific chain ID (required if multiChain is false)
- `multiChain` (optional): Search across all chains (default: true)

**Response:**

```json
{
  "success": true,
  "count": 15,
  "totalFound": 42,
  "protocols": [
    {
      "address": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
      "name": "Aave V3 USDC",
      "protocol": "aave-v3",
      "chainId": 1,
      "chainName": "Ethereum",
      "apy": 5.2,
      "tvl": 1000000000,
      "safetyScore": {
        "overall": "very_safe",
        "score": 95,
        "factors": {
          "tvl": { "score": 100, "level": "very_safe" },
          "protocol": { "score": 100, "level": "trusted", "reputation": "excellent" },
          "audits": { "score": 90, "level": "verified", "auditCount": 5 },
          "history": { "score": 90, "level": "established" }
        },
        "warnings": []
      }
    },
    ...
  ],
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

### Transaction Endpoints

#### Generate Transaction Bundle

```http
POST /api/v1/transactions/generate
```

Generate approval and deposit transactions for staking.

**Request Body:**

```json
{
  "userAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
  "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "protocolAddress": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
  "protocolName": "aave-v3",
  "chainId": 1,
  "amount": "100000000",
  "tokenSymbol": "USDC",
  "decimals": 6
}
```

**Response:**

```json
{
  "success": true,
  "bundle": {
    "approvalTransaction": {
      "to": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "data": "0x095ea7b3...",
      "value": "0",
      "chainId": 1,
      "gasLimit": "50000",
      "type": "approve",
      "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "spender": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
      "amount": "100000000",
      "safetyWarning": "⚠️ CRITICAL: ..."
    },
    "depositTransaction": {
      "to": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
      "data": "0xe8eda9df...",
      "value": "0",
      "chainId": 1,
      "gasLimit": "200000",
      "type": "deposit",
      "protocol": "aave-v3",
      "action": "deposit",
      "tokenIn": {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "symbol": "USDC",
        "amount": "100",
        "amountWei": "100000000"
      },
      "tokenOut": {
        "address": "0x...",
        "symbol": "aUSDC"
      },
      "safetyWarning": "⚠️ CRITICAL: ..."
    },
    "executionOrder": ["approve", "deposit"],
    "totalGasEstimate": "$5.23"
  },
  "warning": "⚠️ CRITICAL: This transaction object was generated by an AI agent...",
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

### Chain Endpoints

#### Get Supported Chains

```http
GET /api/v1/chains
```

List all supported blockchain networks.

**Response:**

```json
{
  "success": true,
  "count": 7,
  "chains": [
    {
      "id": 1,
      "name": "Ethereum",
      "chainName": "ethereum"
    },
    {
      "id": 42161,
      "name": "Arbitrum",
      "chainName": "arbitrum-one"
    },
    ...
  ],
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "success": false,
  "error": "Error type",
  "details": "Detailed error message",
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

### HTTP Status Codes

- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable (API keys not configured)

### Common Errors

#### Validation Error (400)

```json
{
  "success": false,
  "error": "Validation error",
  "details": [
    {
      "field": "query",
      "message": "Query cannot be empty"
    }
  ],
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

#### Rate Limit Error (429)

```json
{
  "success": false,
  "error": "Too many requests from this IP, please try again later.",
  "retryAfter": "15 minutes",
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

#### Resource Not Found (404)

```json
{
  "success": false,
  "error": "Token not found",
  "timestamp": "2025-12-31T10:00:00.000Z"
}
```

---

## Rate Limiting

- **Limit:** 100 requests per 15 minutes per IP address
- **Batch queries:** Limited to 10 queries maximum per request
- **Headers:** Rate limit information is included in response headers:
  - `RateLimit-Limit`: Maximum requests allowed
  - `RateLimit-Remaining`: Remaining requests in current window
  - `RateLimit-Reset`: Time when the rate limit resets

---

## Examples

### Example 1: Find Best USDC Staking on Ethereum

```bash
curl -X POST http://localhost:3000/api/v1/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find the best and safest staking opportunities for USDC on Ethereum"
  }'
```

### Example 2: Quick Transaction for Aave

```bash
curl -X POST http://localhost:3000/api/v1/agent/quick \
  -H "Content-Type: application/json" \
  -d '{
    "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "chainId": 1,
    "protocolName": "aave",
    "amount": "1000",
    "userAddress": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
  }'
```

### Example 3: Search for Token

```bash
curl -X GET "http://localhost:3000/api/v1/tokens/search?query=USDC"
```

### Example 4: Discover Multi-Chain Protocols

```bash
curl -X POST http://localhost:3000/api/v1/protocols/discover \
  -H "Content-Type: application/json" \
  -d '{
    "tokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "multiChain": true
  }'
```

---

## Safety Warnings

⚠️ **CRITICAL REMINDERS:**

1. **Always verify transaction details** before executing
2. **Check token addresses** on a block explorer
3. **Verify protocol addresses** on the official protocol website
4. **Review safety scores** carefully before selecting protocols
5. **Start with small amounts** when trying new protocols
6. **This is not financial advice** - always do your own research

All transaction objects include safety warnings and should be thoroughly reviewed before execution.

---

## Support

For issues, questions, or feature requests:

- GitHub Issues: [link to repo]
- Email: support@yieldagent.io
- Documentation: http://localhost:3000/api-docs
