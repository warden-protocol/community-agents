/**
 * LangChain tools for the yield agent
 * Wraps service functions as tools that the agent can use
 */

import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { isAddress } from "viem";
import { getTokenInfo, searchToken } from "./api";
import {
  discoverProtocols,
  discoverProtocolsMultiChain,
  generateTransactionBundle,
  checkApprovalNeeded,
} from "./enso-service";
import {
  addSafetyScores,
  sortProtocolsBySafetyAndYield,
  evaluateProtocolSafety,
} from "./safety-service";
import {
  validateTokenInput,
  validateChain,
  validateAmount,
} from "./validation";
import { Logger } from "../common/logger";
import { ProtocolVault } from "./types";
import { getChainByName, getChainById } from "../common/types";

const logger = new Logger("AgentTools");

/**
 * Tool: Get token information
 */
export const getTokenInfoTool = tool(
  async (input): Promise<string> => {
    const { token, chainId, chainName } = input;
    try {
      logger.info(`Getting token info for: ${token}`);

      // Validate input
      const validation = validateTokenInput({ token, chainId, chainName });
      if (!validation.valid) {
        return JSON.stringify({
          error: validation.error || validation.errors?.join(", "),
          validationErrors: validation.errors,
        });
      }

      // Check if token is an address
      const isTokenAddress = isAddress(token);

      // If address provided but no chain, return error
      if (isTokenAddress && !chainId && !chainName) {
        return JSON.stringify({
          error:
            "Chain must be provided when using token address. Please specify the chain (e.g., ethereum, arbitrum, base).",
          requiresChain: true,
        });
      }

      const tokenInfo = await getTokenInfo(token, chainId, chainName);

      if (!tokenInfo) {
        return JSON.stringify({
          error:
            "Token not found. Please check spelling or provide contract address with chain.",
        });
      }

      // If multiple tokens found, return array
      if (Array.isArray(tokenInfo)) {
        return JSON.stringify({
          multipleMatches: true,
          tokens: tokenInfo,
          message: `Multiple tokens found. Please select one: ${tokenInfo.map((t) => `${t.name} (${t.symbol})`).join(", ")}`,
        });
      }

      // If only name/symbol provided (not address), show all chains
      if (
        !isTokenAddress &&
        tokenInfo.allChains &&
        tokenInfo.allChains.length > 0
      ) {
        return JSON.stringify({
          success: true,
          token: {
            name: tokenInfo.name,
            symbol: tokenInfo.symbol,
            coingeckoId: tokenInfo.coingeckoId,
            marketCap: tokenInfo.marketCap,
            price: tokenInfo.price,
            verified: tokenInfo.verified,
            description: tokenInfo.description,
          },
          allChains: tokenInfo.allChains.map((chain) => ({
            chainId: chain.chainId,
            chainName: chain.chainName,
            address: chain.address,
          })),
          requiresConfirmation: true,
          message: `Found ${tokenInfo.name} (${tokenInfo.symbol}) on ${tokenInfo.allChains.length} chain(s). Please confirm which chain and address you want to use:`,
          warning:
            "⚠️ Please verify token details and select the correct chain before proceeding",
        });
      }

      // If address + chain provided, return single token info
      return JSON.stringify({
        success: true,
        token: tokenInfo,
        warning: "⚠️ Please verify token details before proceeding",
      });
    } catch (error) {
      logger.error("Error in getTokenInfoTool:", error);
      return JSON.stringify({
        error: `Failed to get token info: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  },
  {
    name: "get_token_info",
    description:
      "Get token information by name, symbol, or address. IMPORTANT: If token is an address, chainId or chainName MUST be provided (will return error otherwise). If only name/symbol is provided, returns token info for ALL supported chains - user must then confirm which chain to use.",
    schema: z.object({
      token: z.string().describe("Token name, symbol, or contract address"),
      chainId: z
        .number()
        .optional()
        .describe(
          "Chain ID (REQUIRED if token is an address, optional for name/symbol)"
        ),
      chainName: z
        .string()
        .optional()
        .describe(
          "Chain name (REQUIRED if token is an address, optional for name/symbol)"
        ),
    }),
  }
);

/**
 * Tool: Search for tokens
 */
export const searchTokenTool = tool(
  async (input): Promise<string> => {
    const { query } = input;
    try {
      logger.info(`Searching for token: ${query}`);
      const results = await searchToken(query);

      if (results.length === 0) {
        return JSON.stringify({
          error: "No tokens found. Please try a different search term.",
        });
      }

      return JSON.stringify({
        success: true,
        count: results.length,
        tokens: results,
      });
    } catch (error) {
      logger.error("Error in searchTokenTool:", error);
      return JSON.stringify({
        error: `Failed to search tokens: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  },
  {
    name: "search_token",
    description: "Search for tokens by name or symbol (fuzzy search)",
    schema: z.object({
      query: z.string().describe("Search query (token name or symbol)"),
    }),
  }
);

/**
 * Tool: Discover protocols for a token
 */
export const discoverProtocolsTool = tool(
  async (input): Promise<string> => {
    const { tokenAddress, chainId, multiChain } = input;
    try {
      logger.info(`Discovering protocols for token ${tokenAddress}`);

      let protocols: ProtocolVault[];

      if (multiChain) {
        protocols = await discoverProtocolsMultiChain(tokenAddress);
      } else {
        if (!chainId) {
          return JSON.stringify({
            error: "chainId is required when multiChain is false",
          });
        }

        const chainValidation = validateChain(chainId);
        if (!chainValidation.valid) {
          return JSON.stringify({
            error: chainValidation.error || "Invalid chain",
          });
        }

        protocols = await discoverProtocols(tokenAddress, chainId);
      }

      if (protocols.length === 0) {
        return JSON.stringify({
          error:
            "No staking protocols found for this token on supported chains.",
          suggestion:
            "Try searching on different chains or check if token supports staking.",
        });
      }

      // Limit protocols before safety evaluation to save on API credits
      // Pre-filter by TVL to get top protocols first, then evaluate safety for top 20
      const maxProtocolsToEvaluate = 20; // Only evaluate safety for top 20 by TVL
      const maxProtocolsToReturn = 15; // Return top 15 after sorting by safety+yield

      logger.info(
        `Found ${protocols.length} protocols. Evaluating safety for top ${maxProtocolsToEvaluate} by TVL.`
      );

      // Add safety scores (only for top protocols by TVL)
      const protocolsWithSafety = await addSafetyScores(
        protocols,
        maxProtocolsToEvaluate
      );

      // Sort by safety and yield
      const sortedProtocols =
        sortProtocolsBySafetyAndYield(protocolsWithSafety);

      // Return only top protocols to avoid token limit issues
      const topProtocols = sortedProtocols.slice(0, maxProtocolsToReturn);

      logger.info(
        `Returning top ${topProtocols.length} protocols (sorted by safety and yield) out of ${protocols.length} total found`
      );

      return JSON.stringify({
        success: true,
        count: topProtocols.length,
        totalFound: protocols.length,
        message: `Found ${protocols.length} total protocols. Showing top ${topProtocols.length} by safety and yield.`,
        protocols: topProtocols.map((p) => ({
          address: p.address,
          name: p.name,
          protocol: p.protocol,
          chainId: p.chainId,
          chainName: p.chainName,
          apy: p.apy,
          tvl: p.tvl,
          safetyScore: p.safetyScore,
        })),
      });
    } catch (error) {
      logger.error("Error in discoverProtocolsTool:", error);
      return JSON.stringify({
        error: `Failed to discover protocols: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  },
  {
    name: "discover_protocols",
    description:
      "Discover all available staking protocols/vaults for a token. Can search single chain or all supported chains.",
    schema: z.object({
      tokenAddress: z.string().describe("Token contract address"),
      chainId: z
        .number()
        .optional()
        .describe("Chain ID (required if multiChain is false)"),
      multiChain: z
        .boolean()
        .default(true)
        .describe("Whether to search across all supported chains"),
    }),
  }
);

/**
 * Tool: Generate transaction bundle
 */
export const generateTransactionTool = tool(
  async (input): Promise<string> => {
    const {
      userAddress,
      tokenAddress,
      protocolAddress,
      protocolName,
      chainId,
      amount,
      tokenSymbol,
      decimals,
    } = input;
    try {
      logger.info(`Generating transaction bundle for ${tokenSymbol} deposit`);

      // Validate inputs
      const amountValidation = validateAmount(
        amount,
        BigInt("999999999999999999999999999"), // Max balance placeholder - should be checked separately
        decimals
      );

      if (!amountValidation.valid) {
        return JSON.stringify({
          error: amountValidation.error || "Invalid amount",
        });
      }

      const bundle = await generateTransactionBundle(
        userAddress,
        tokenAddress,
        protocolAddress,
        protocolName,
        chainId,
        BigInt(amount),
        tokenSymbol,
        decimals
      );

      return JSON.stringify({
        success: true,
        bundle: {
          approvalTransaction: bundle.approvalTransaction,
          depositTransaction: bundle.depositTransaction,
          executionOrder: bundle.executionOrder,
          totalGasEstimate: bundle.totalGasEstimate,
        },
        warning:
          "⚠️ CRITICAL: This transaction object was generated by an AI agent. Please verify all details before executing. This is not financial advice.",
      });
    } catch (error) {
      logger.error("Error in generateTransactionTool:", error);
      return JSON.stringify({
        error: `Failed to generate transaction: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  },
  {
    name: "generate_transaction",
    description:
      "Generate transaction bundle (approval + deposit) for staking tokens. Returns approval transaction if needed, and deposit transaction.",
    schema: z.object({
      userAddress: z.string().describe("User wallet address"),
      tokenAddress: z.string().describe("Token contract address"),
      protocolAddress: z.string().describe("Protocol/vault contract address"),
      protocolName: z.string().describe('Protocol name (e.g., "aave-v3")'),
      chainId: z.number().describe("Chain ID"),
      amount: z.string().describe("Amount to deposit (in wei)"),
      tokenSymbol: z.string().describe("Token symbol"),
      decimals: z.number().describe("Token decimals"),
    }),
  }
);

/**
 * Tool: Validate input
 */
export const validateInputTool = tool(
  async (input): Promise<string> => {
    const { input: userInput, inputType } = input;
    try {
      if (inputType === "token") {
        // Type guard: ensure userInput is an object for TokenInput
        if (
          typeof userInput === "object" &&
          userInput !== null &&
          !Array.isArray(userInput)
        ) {
          const validation = validateTokenInput(userInput as any);
          return JSON.stringify({
            valid: validation.valid,
            errors: validation.errors,
            warnings: validation.warnings,
          });
        }
        return JSON.stringify({
          valid: false,
          error:
            "Token input must be an object with token, chainId, and chainName properties",
        });
      }

      if (inputType === "chain") {
        // Type guard: ensure userInput is string or number for chain
        if (typeof userInput === "string" || typeof userInput === "number") {
          const validation = validateChain(userInput);
          return JSON.stringify({
            valid: validation.valid,
            error: validation.error,
            supportedChains: validation.supportedChains,
          });
        }
        return JSON.stringify({
          valid: false,
          error: "Chain input must be a string or number",
        });
      }

      return JSON.stringify({
        error: "Unknown input type",
      });
    } catch (error) {
      logger.error("Error in validateInputTool:", error);
      return JSON.stringify({
        error: `Validation failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      });
    }
  },
  {
    name: "validate_input",
    description: "Validate user input (token, chain, etc.)",
    schema: z.object({
      input: z
        .union([z.string(), z.number(), z.object({})])
        .describe("Input to validate"),
      inputType: z
        .enum(["token", "chain", "amount"])
        .describe("Type of input to validate"),
    }),
  }
);

/**
 * Tool: Quick transaction generation (when all parameters provided)
 */
export const quickTransactionTool = tool(
  async (input): Promise<string> => {
    const {
      tokenAddress,
      chainId,
      chainName,
      protocolName,
      amount,
      userAddress,
    } = input;
    try {
      logger.info(
        `Quick transaction mode: ${amount} ${tokenAddress} on ${chainName || chainId} to ${protocolName}`
      );

      // Validate inputs using viem's isAddress (handles checksum properly)
      if (!isAddress(tokenAddress)) {
        return JSON.stringify({
          error:
            "Invalid token address format. Must be a valid Ethereum address",
        });
      }

      if (!isAddress(userAddress)) {
        return JSON.stringify({
          error:
            "Invalid user address format. Must be a valid Ethereum address",
        });
      }

      const resolvedChainId =
        chainId || (chainName ? getChainByName(chainName)?.id : undefined);

      if (!resolvedChainId) {
        return JSON.stringify({
          error: `Invalid chain: ${chainName || chainId}. Supported chains: Ethereum, Arbitrum, Optimism, Polygon, Base, Avalanche, BNB Chain`,
        });
      }

      if (!protocolName || protocolName.trim().length === 0) {
        return JSON.stringify({
          error: "Protocol name is required",
        });
      }

      if (!amount || parseFloat(amount) <= 0) {
        return JSON.stringify({
          error: "Amount must be a positive number",
        });
      }

      // Get token info
      const tokenInfo = await getTokenInfo(
        tokenAddress,
        resolvedChainId,
        chainName
      );

      if (!tokenInfo || Array.isArray(tokenInfo)) {
        return JSON.stringify({
          error: "Token not found or multiple tokens found",
        });
      }

      // Discover protocols on the specified chain only (quick mode - no multi-chain search)
      const allProtocols = await discoverProtocols(
        tokenAddress,
        resolvedChainId
      );

      if (allProtocols.length === 0) {
        return JSON.stringify({
          error: `No protocols found for token ${tokenInfo.symbol} on ${chainName || getChainById(resolvedChainId)?.name || resolvedChainId}`,
          suggestion:
            "Try a different chain or check if the token supports staking on this chain",
        });
      }

      // Find protocol by name (case-insensitive, partial match)
      const protocolLower = protocolName.toLowerCase();
      const matchingProtocols = allProtocols.filter(
        (p) =>
          p.protocol.toLowerCase().includes(protocolLower) ||
          p.name.toLowerCase().includes(protocolLower)
      );

      if (matchingProtocols.length === 0) {
        return JSON.stringify({
          error: `Protocol "${protocolName}" not found for token ${tokenInfo.symbol} on ${chainName || getChainById(resolvedChainId)?.name || resolvedChainId}`,
          suggestion: `Available protocols on this chain: ${allProtocols
            .slice(0, 10)
            .map((p) => `${p.protocol} (${p.name})`)
            .join(", ")}`,
        });
      }

      // If multiple vaults match, select the one with highest APY
      // Sort by APY (descending), then by TVL as tiebreaker
      const selectedProtocol = matchingProtocols.sort((a, b) => {
        const apyDiff = b.apy - a.apy;
        if (Math.abs(apyDiff) > 0.01) {
          // If APY difference is significant (>0.01%), prioritize APY
          return apyDiff;
        }
        // If APY is similar, prefer higher TVL (more established)
        return b.tvl - a.tvl;
      })[0];

      logger.info(
        `Selected vault: ${selectedProtocol.name} (APY: ${selectedProtocol.apy}%, TVL: $${selectedProtocol.tvl.toLocaleString()})`
      );

      // Evaluate safety for this protocol
      const safetyScore = await evaluateProtocolSafety(selectedProtocol);

      // Convert amount to wei
      const amountNum = parseFloat(amount);
      const amountWei = BigInt(
        Math.floor(amountNum * Math.pow(10, tokenInfo.decimals))
      );

      // Check if approval is needed
      const approvalCheck = await checkApprovalNeeded(
        userAddress,
        tokenAddress,
        selectedProtocol.address,
        resolvedChainId,
        amountWei
      );

      // Generate transaction bundle
      // CRITICAL: Use the EXACT protocol field from Enso's token data
      // In Parifi (line 70 of enso.tsx), they pass the protocol field directly
      // This is the protocol identifier that Enso expects in getBundleData
      const protocolNameForTx = selectedProtocol.protocol;

      logger.info(
        `Using protocol name "${protocolNameForTx}" for transaction generation (vault: ${selectedProtocol.name}, project: ${selectedProtocol.project}, protocol: ${selectedProtocol.protocol})`
      );

      const bundle = await generateTransactionBundle(
        userAddress,
        tokenAddress,
        selectedProtocol.address,
        protocolNameForTx,
        resolvedChainId,
        amountWei,
        tokenInfo.symbol,
        tokenInfo.decimals
      );

      return JSON.stringify({
        success: true,
        mode: "quick",
        tokenInfo: {
          name: tokenInfo.name,
          symbol: tokenInfo.symbol,
          address: tokenAddress,
          chain: chainName || getChainById(resolvedChainId)?.name || "",
          chainId: resolvedChainId,
          decimals: tokenInfo.decimals,
          price: tokenInfo.price,
          marketCap: tokenInfo.marketCap,
        },
        protocol: {
          address: selectedProtocol.address,
          name: selectedProtocol.name,
          protocol: selectedProtocol.protocol,
          chainId: resolvedChainId,
          chainName: selectedProtocol.chainName,
          apy: selectedProtocol.apy,
          tvl: selectedProtocol.tvl,
          safetyScore: safetyScore,
        },
        approvalNeeded: approvalCheck.approvalNeeded,
        bundle: {
          approvalTransaction: bundle.approvalTransaction,
          depositTransaction: bundle.depositTransaction,
          executionOrder: bundle.executionOrder,
          totalGasEstimate: bundle.totalGasEstimate,
        },
        warning:
          "⚠️ CRITICAL: This transaction object was generated by an AI agent. Please verify all details (token address, protocol address, amount, chain) before executing. Double-check on block explorer and protocol website. This is not financial advice.",
      });
    } catch (error) {
      logger.error("Error in quickTransactionTool:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      // Resolve chainId for fallback
      const fallbackChainId =
        chainId || (chainName ? getChainByName(chainName)?.id : undefined);

      // If transaction generation failed, try to at least return protocol info
      // This allows the user to see available protocols even if tx generation fails
      if (fallbackChainId) {
        try {
          const allProtocols = await discoverProtocols(
            tokenAddress,
            fallbackChainId
          );

          // Filter for Aave protocol specifically
          const aaveProtocols = allProtocols.filter(
            (p) =>
              p.protocol.toLowerCase().includes("aave") ||
              p.name.toLowerCase().includes("aave")
          );

          if (aaveProtocols.length > 0) {
            // Add safety scores to Aave protocols
            const protocolsWithSafety = await addSafetyScores(aaveProtocols, 5);
            const sortedProtocols =
              sortProtocolsBySafetyAndYield(protocolsWithSafety);

            // Return the selected vault info even if transaction failed
            const selectedVault = sortedProtocols[0];
            return JSON.stringify({
              error: `Failed to generate transaction: ${errorMessage}. This may be due to API limitations.`,
              mode: "quick",
              failed: true,
              transactionGenerationFailed: true,
              message:
                "Could not generate transaction bundle, but here is the selected Aave protocol information:",
              tokenInfo: {
                name: tokenInfo.name,
                symbol: tokenInfo.symbol,
                address: tokenAddress,
                decimals: tokenInfo.decimals,
                chain: chainName || getChainById(fallbackChainId)?.name,
                chainId: fallbackChainId,
              },
              vault: {
                address: selectedVault.address,
                name: selectedVault.name,
                symbol: selectedVault.symbol,
                protocol: selectedVault.protocol,
                project: selectedVault.project,
                apy: selectedVault.apy,
                tvl: selectedVault.tvl,
                chainId: selectedVault.chainId,
                chainName: selectedVault.chainName,
                safetyScore: selectedVault.safetyScore,
              },
              protocols: sortedProtocols.map((p) => ({
                address: p.address,
                name: p.name,
                protocol: p.protocol,
                chainId: p.chainId,
                chainName: p.chainName,
                apy: p.apy,
                tvl: p.tvl,
                safetyScore: p.safetyScore,
              })),
              suggestion:
                "Transaction generation failed due to API limitations. You can interact with the protocol directly using the vault address above, or contact support to upgrade API access.",
            });
          }
        } catch (fallbackError) {
          logger.error(
            "Fallback protocol discovery also failed:",
            fallbackError
          );
        }
      }

      // If everything fails, return error with basic info
      return JSON.stringify({
        error: `Failed to generate quick transaction: ${errorMessage}. This is likely due to Enso API limitations (free tier may not support transaction bundling).`,
        mode: "quick",
        failed: true,
        suggestion:
          "The Enso API's getBundleData endpoint returned a 400 error. This typically means the API key doesn't have access to transaction bundling features. You can still use the protocol information to interact directly with the vault.",
      });
    }
  },
  {
    name: "quick_transaction",
    description:
      "Generate transaction bundle directly when user provides token address, chain, protocol, amount, and user address. Use this for quick mode when all parameters are available. Returns vault info and transaction objects immediately.",
    schema: z.object({
      tokenAddress: z.string().describe("Token contract address"),
      chainId: z.number().optional().describe("Chain ID"),
      chainName: z
        .string()
        .optional()
        .describe("Chain name (e.g., Ethereum, Arbitrum)"),
      protocolName: z
        .string()
        .describe("Protocol name (e.g., aave, morpho, compound)"),
      amount: z
        .string()
        .describe(
          "Amount to deposit (human-readable, e.g., '100' for 100 tokens)"
        ),
      userAddress: z.string().describe("User wallet address"),
    }),
  }
);

/**
 * Get all tools for the agent
 */
export function getYieldAgentTools(): Array<ReturnType<typeof tool>> {
  return [
    getTokenInfoTool,
    searchTokenTool,
    discoverProtocolsTool,
    generateTransactionTool,
    quickTransactionTool,
    validateInputTool,
  ];
}
