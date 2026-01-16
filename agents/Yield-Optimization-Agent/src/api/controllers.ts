/**
 * API Controllers
 * Handle HTTP requests and responses
 */

import { Request, Response, NextFunction } from "express";
import { runYieldAgent } from "../agent";
import {
  searchToken,
  getTokenInfo,
  discoverProtocols,
  discoverProtocolsMultiChain,
  generateTransactionBundle,
} from "../agent";
import { SUPPORTED_CHAINS } from "../common/types";
import { Logger } from "../common/logger";
import { addSafetyScores, sortProtocolsBySafetyAndYield } from "../agent/safety-service";

const logger = new Logger("API-Controllers");

/**
 * Query the agent with a single question
 */
export async function queryAgent(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { query, options } = req.body;

    logger.info(`Agent query received: ${query}`);

    const results = await runYieldAgent([query], options);

    res.json({
      success: true,
      query,
      result: results[0],
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Batch query the agent with multiple questions
 */
export async function batchQueryAgent(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { queries, options } = req.body;

    logger.info(`Batch query received: ${queries.length} queries`);

    const results = await runYieldAgent(queries, options);

    res.json({
      success: true,
      count: results.length,
      results,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Quick transaction generation (all parameters provided)
 */
export async function quickTransaction(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { tokenAddress, chainId, protocolName, amount, userAddress } = req.body;

    logger.info(`Quick transaction: ${amount} of ${tokenAddress} on chain ${chainId} to ${protocolName}`);

    // Create a natural language query from the parameters
    const query = `Deposit ${amount} ${tokenAddress} on chain ${chainId} to ${protocolName} for user ${userAddress}`;

    const results = await runYieldAgent([query], {
      modelName: "gpt-4o-mini",
      temperature: 0,
    });

    res.json({
      success: true,
      mode: "quick",
      result: results[0],
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Search for tokens by name or symbol
 */
export async function searchTokens(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { query } = req.query as { query: string };

    logger.info(`Token search: ${query}`);

    const tokens = await searchToken(query);

    res.json({
      success: true,
      count: tokens.length,
      tokens,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Get token information
 */
export async function getTokenInformation(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { token, chainId, chainName } = req.query as {
      token: string;
      chainId?: string;
      chainName?: string;
    };

    logger.info(`Get token info: ${token}`);

    const tokenInfo = await getTokenInfo(
      token,
      chainId ? parseInt(chainId) : undefined,
      chainName
    );

    if (!tokenInfo) {
      res.status(404).json({
        success: false,
        error: "Token not found",
        timestamp: new Date().toISOString(),
      });
      return;
    }

    res.json({
      success: true,
      token: tokenInfo,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Discover protocols for a token
 */
export async function discoverProtocolsForToken(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const { tokenAddress, chainId, multiChain = true } = req.body;

    logger.info(`Discover protocols for token: ${tokenAddress}`);

    let protocols;
    if (multiChain) {
      protocols = await discoverProtocolsMultiChain(tokenAddress);
    } else {
      if (!chainId) {
        res.status(400).json({
          success: false,
          error: "chainId is required when multiChain is false",
          timestamp: new Date().toISOString(),
        });
        return;
      }
      protocols = await discoverProtocols(tokenAddress, chainId);
    }

    // Add safety scores and sort
    const maxProtocolsToEvaluate = 20;
    const maxProtocolsToReturn = 15;

    const protocolsWithSafety = await addSafetyScores(
      protocols,
      maxProtocolsToEvaluate
    );
    const sortedProtocols = sortProtocolsBySafetyAndYield(protocolsWithSafety);
    const topProtocols = sortedProtocols.slice(0, maxProtocolsToReturn);

    res.json({
      success: true,
      count: topProtocols.length,
      totalFound: protocols.length,
      protocols: topProtocols,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Generate transaction bundle
 */
export async function generateTransaction(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    const {
      userAddress,
      tokenAddress,
      protocolAddress,
      protocolName,
      chainId,
      amount,
      tokenSymbol,
      decimals,
    } = req.body;

    logger.info(`Generate transaction: ${tokenSymbol} to ${protocolName}`);

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

    res.json({
      success: true,
      bundle,
      warning:
        "⚠️ CRITICAL: This transaction object was generated by an AI agent. Please verify all details before executing. This is not financial advice.",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

/**
 * Get supported chains
 */
export async function getSupportedChains(
  req: Request,
  res: Response,
  next: NextFunction
): Promise<void> {
  try {
    res.json({
      success: true,
      count: SUPPORTED_CHAINS.length,
      chains: SUPPORTED_CHAINS.map((chain) => ({
        id: chain.id,
        name: chain.name,
        chainName: chain.chainName,
      })),
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    next(error);
  }
}

