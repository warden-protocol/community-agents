/**
 * API Routes
 * Defines all HTTP endpoints for the Yield Agent API
 */

import { Router } from "express";
import {
  queryAgent,
  batchQueryAgent,
  searchTokens,
  getTokenInformation,
  discoverProtocolsForToken,
  generateTransaction,
  getSupportedChains,
  quickTransaction,
} from "./controllers";
import { validateRequest } from "./middleware";
import {
  agentQuerySchema,
  batchQuerySchema,
  tokenSearchSchema,
  tokenInfoSchema,
  protocolDiscoverySchema,
  transactionGenerationSchema,
  quickTransactionSchema,
} from "./validation";

export const router = Router();

/**
 * @swagger
 * /api/v1/agent/query:
 *   post:
 *     tags:
 *       - Agent
 *     summary: Query the yield optimization agent
 *     description: Send a natural language query to the agent and receive a structured response
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - query
 *             properties:
 *               query:
 *                 type: string
 *                 description: Natural language query about yield opportunities
 *                 example: "Find staking opportunities for USDC on Ethereum"
 *               options:
 *                 type: object
 *                 properties:
 *                   modelName:
 *                     type: string
 *                     default: "gpt-4o-mini"
 *                   temperature:
 *                     type: number
 *                     default: 0
 *     responses:
 *       200:
 *         description: Successful response with agent answer
 *       400:
 *         description: Invalid request
 *       500:
 *         description: Internal server error
 */
router.post("/agent/query", validateRequest(agentQuerySchema), queryAgent);

/**
 * @swagger
 * /api/v1/agent/batch:
 *   post:
 *     tags:
 *       - Agent
 *     summary: Batch query the agent
 *     description: Send multiple queries to the agent at once
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - queries
 *             properties:
 *               queries:
 *                 type: array
 *                 items:
 *                   type: string
 *                 example: ["Find staking for USDC", "What protocols support ETH on Arbitrum?"]
 *     responses:
 *       200:
 *         description: Successful batch response
 */
router.post("/agent/batch", validateRequest(batchQuerySchema), batchQueryAgent);

/**
 * @swagger
 * /api/v1/agent/quick:
 *   post:
 *     tags:
 *       - Agent
 *     summary: Quick transaction generation
 *     description: Generate transaction bundle directly with all parameters
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - tokenAddress
 *               - chainId
 *               - protocolName
 *               - amount
 *               - userAddress
 *             properties:
 *               tokenAddress:
 *                 type: string
 *                 example: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
 *               chainId:
 *                 type: number
 *                 example: 1
 *               protocolName:
 *                 type: string
 *                 example: "aave"
 *               amount:
 *                 type: string
 *                 example: "100"
 *               userAddress:
 *                 type: string
 *                 example: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
 *     responses:
 *       200:
 *         description: Transaction bundle generated successfully
 */
router.post("/agent/quick", validateRequest(quickTransactionSchema), quickTransaction);

/**
 * @swagger
 * /api/v1/tokens/search:
 *   get:
 *     tags:
 *       - Tokens
 *     summary: Search for tokens
 *     description: Search tokens by name or symbol
 *     parameters:
 *       - in: query
 *         name: query
 *         required: true
 *         schema:
 *           type: string
 *         description: Token name or symbol to search for
 *         example: "USDC"
 *     responses:
 *       200:
 *         description: List of matching tokens
 */
router.get("/tokens/search", validateRequest(tokenSearchSchema), searchTokens);

/**
 * @swagger
 * /api/v1/tokens/info:
 *   get:
 *     tags:
 *       - Tokens
 *     summary: Get token information
 *     description: Get detailed information about a specific token
 *     parameters:
 *       - in: query
 *         name: token
 *         required: true
 *         schema:
 *           type: string
 *         description: Token name, symbol, or address
 *         example: "USDC"
 *       - in: query
 *         name: chainId
 *         schema:
 *           type: number
 *         description: Chain ID (required if token is an address)
 *         example: 1
 *     responses:
 *       200:
 *         description: Token information
 */
router.get("/tokens/info", validateRequest(tokenInfoSchema), getTokenInformation);

/**
 * @swagger
 * /api/v1/protocols/discover:
 *   post:
 *     tags:
 *       - Protocols
 *     summary: Discover staking protocols
 *     description: Find available staking protocols for a token
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - tokenAddress
 *             properties:
 *               tokenAddress:
 *                 type: string
 *                 example: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
 *               chainId:
 *                 type: number
 *                 example: 1
 *               multiChain:
 *                 type: boolean
 *                 default: true
 *     responses:
 *       200:
 *         description: List of available protocols
 */
router.post(
  "/protocols/discover",
  validateRequest(protocolDiscoverySchema),
  discoverProtocolsForToken
);

/**
 * @swagger
 * /api/v1/transactions/generate:
 *   post:
 *     tags:
 *       - Transactions
 *     summary: Generate transaction bundle
 *     description: Generate approval and deposit transactions for staking
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - userAddress
 *               - tokenAddress
 *               - protocolAddress
 *               - protocolName
 *               - chainId
 *               - amount
 *               - tokenSymbol
 *               - decimals
 *             properties:
 *               userAddress:
 *                 type: string
 *                 example: "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
 *               tokenAddress:
 *                 type: string
 *                 example: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
 *               protocolAddress:
 *                 type: string
 *                 example: "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9"
 *               protocolName:
 *                 type: string
 *                 example: "aave-v3"
 *               chainId:
 *                 type: number
 *                 example: 1
 *               amount:
 *                 type: string
 *                 example: "100000000"
 *               tokenSymbol:
 *                 type: string
 *                 example: "USDC"
 *               decimals:
 *                 type: number
 *                 example: 6
 *     responses:
 *       200:
 *         description: Transaction bundle generated
 */
router.post(
  "/transactions/generate",
  validateRequest(transactionGenerationSchema),
  generateTransaction
);

/**
 * @swagger
 * /api/v1/chains:
 *   get:
 *     tags:
 *       - Chains
 *     summary: Get supported chains
 *     description: List all supported blockchain networks
 *     responses:
 *       200:
 *         description: List of supported chains
 */
router.get("/chains", getSupportedChains);

