/**
 * Request validation schemas using Zod
 */

import { z } from "zod";

/**
 * Agent query validation schema
 */
export const agentQuerySchema = z.object({
  query: z.string().min(1, "Query cannot be empty"),
  options: z
    .object({
      modelName: z.string().optional(),
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().min(100).max(16000).optional(),
      maxRetries: z.number().min(1).max(10).optional(),
    })
    .optional(),
});

/**
 * Batch query validation schema
 */
export const batchQuerySchema = z.object({
  queries: z.array(z.string().min(1)).min(1, "At least one query is required").max(10, "Maximum 10 queries allowed"),
  options: z
    .object({
      modelName: z.string().optional(),
      temperature: z.number().min(0).max(2).optional(),
      maxTokens: z.number().min(100).max(16000).optional(),
      maxRetries: z.number().min(1).max(10).optional(),
      delayBetweenQuestionsMs: z.number().min(0).max(10000).optional(),
    })
    .optional(),
});

/**
 * Quick transaction validation schema
 */
export const quickTransactionSchema = z.object({
  tokenAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid Ethereum address"),
  chainId: z.number().int().positive(),
  protocolName: z.string().min(1, "Protocol name is required"),
  amount: z.string().min(1, "Amount is required"),
  userAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid Ethereum address"),
});

/**
 * Token search validation schema
 */
export const tokenSearchSchema = z.object({
  query: z.string().min(1, "Search query cannot be empty"),
});

/**
 * Token info validation schema
 */
export const tokenInfoSchema = z.object({
  token: z.string().min(1, "Token identifier is required"),
  chainId: z.string().optional().transform((val) => (val ? parseInt(val) : undefined)),
  chainName: z.string().optional(),
});

/**
 * Protocol discovery validation schema
 */
export const protocolDiscoverySchema = z.object({
  tokenAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid token address"),
  chainId: z.number().int().positive().optional(),
  multiChain: z.boolean().optional().default(true),
});

/**
 * Transaction generation validation schema
 */
export const transactionGenerationSchema = z.object({
  userAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid user address"),
  tokenAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid token address"),
  protocolAddress: z.string().regex(/^0x[a-fA-F0-9]{40}$/, "Invalid protocol address"),
  protocolName: z.string().min(1, "Protocol name is required"),
  chainId: z.number().int().positive(),
  amount: z.string().min(1, "Amount is required"),
  tokenSymbol: z.string().min(1, "Token symbol is required"),
  decimals: z.number().int().min(0).max(18),
});

