/**
 * Token information API service
 * Integrates with CoinGecko API to fetch token metadata
 */

import Coingecko from "@coingecko/coingecko-typescript";
import { TokenInfo } from "./types";
import { Logger } from "../common/logger";
import { getChainById, getChainByName } from "../common/types";
import { isAddress } from "viem";
import { retryWithBackoff } from "../common/utils";

const logger = new Logger("TokenInfoAPI");

// Lazy initialization of CoinGecko client
let coingeckoClient: Coingecko | null = null;

function getCoingeckoClient(): Coingecko | null {
  const apiKey = process.env.COINGECKO_API_KEY;

  if (!apiKey) {
    logger.debug("CoinGecko API key not found in environment variables");
    return null;
  }

  if (!coingeckoClient) {
    logger.info(
      `Initializing CoinGecko client with API key: ${apiKey.substring(0, 7)}...${apiKey.substring(apiKey.length - 4)}`
    );
    coingeckoClient = new Coingecko({
      demoAPIKey: apiKey,
      environment: "demo",
      timeout: 10000,
      maxRetries: 3,
    });
  }

  return coingeckoClient;
}

/**
 * Mock token data for testing when API key is not available
 */
function getMockTokenData(query: string): TokenInfo[] {
  const upperQuery = query.toUpperCase();

  // USDC mock data
  if (upperQuery === "USDC" || upperQuery.includes("USD COIN")) {
    return [
      {
        name: "USD Coin",
        symbol: "USDC",
        address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // Ethereum
        chain: "Ethereum",
        chainId: 1,
        decimals: 6,
        marketCap: 30000000000,
        price: 1.0,
        verified: true,
        allChains: [
          {
            chainId: 1,
            chainName: "Ethereum",
            address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
          },
          {
            chainId: 42161,
            chainName: "Arbitrum",
            address: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
          },
          {
            chainId: 10,
            chainName: "Optimism",
            address: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
          },
          {
            chainId: 137,
            chainName: "Polygon",
            address: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
          },
          {
            chainId: 8453,
            chainName: "Base",
            address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
          },
          {
            chainId: 43114,
            chainName: "Avalanche",
            address: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
          },
          {
            chainId: 56,
            chainName: "BNB Chain",
            address: "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
          },
        ],
      },
    ];
  }

  // ETH mock data
  if (
    upperQuery === "ETH" ||
    upperQuery === "ETHEREUM" ||
    upperQuery.includes("ETHER")
  ) {
    return [
      {
        name: "Ethereum",
        symbol: "ETH",
        address: "0x0000000000000000000000000000000000000000", // Native token
        chain: "Ethereum",
        chainId: 1,
        decimals: 18,
        marketCap: 400000000000,
        price: 3000,
        verified: true,
        allChains: [
          {
            chainId: 1,
            chainName: "Ethereum",
            address: "0x0000000000000000000000000000000000000000",
          },
          {
            chainId: 42161,
            chainName: "Arbitrum",
            address: "0x0000000000000000000000000000000000000000",
          },
          {
            chainId: 10,
            chainName: "Optimism",
            address: "0x0000000000000000000000000000000000000000",
          },
        ],
      },
    ];
  }

  return [];
}

/**
 * Search for tokens by name or symbol
 */
export async function searchToken(query: string): Promise<TokenInfo[]> {
  try {
    logger.info(`Searching for token: ${query}`);

    // Check if API key is available
    const client = getCoingeckoClient();
    if (!client) {
      logger.warn(
        "CoinGecko API key not found. Using fallback token data for testing."
      );
      // Return mock data for common tokens when API key is not available
      return getMockTokenData(query);
    }

    const searchResults = await retryWithBackoff(async () => {
      return await client.search.get({ query });
    });

    if (!searchResults.coins || searchResults.coins.length === 0) {
      logger.warn(`No tokens found for query: ${query}`);
      return [];
    }

    // Get detailed info for top results (limit to 10)
    const topResults = searchResults.coins?.slice(0, 10) || [];
    const tokenInfos: TokenInfo[] = [];

    for (const coin of topResults) {
      // Skip if coin doesn't have an id
      const coinId = coin?.id;
      if (!coinId) {
        continue;
      }

      try {
        const client = getCoingeckoClient();
        if (!client) {
          continue; // Skip if no client available
        }

        const coinData = await retryWithBackoff(async () => {
          return await client.coins.getID(coinId);
        });

        // Find token on supported chains
        const supportedChainEntries = Object.entries(
          coinData.platforms || {}
        ).filter(([platform, address]) => {
          if (!address) return false;
          const chain = getChainByName(platform);
          return chain !== undefined;
        });

        if (supportedChainEntries.length > 0) {
          // Use first supported chain as primary
          const [platform, address] = supportedChainEntries[0];
          const chain = getChainByName(platform);

          if (chain && address) {
            const marketData = coinData.market_data;

            tokenInfos.push({
              name: coinData.name,
              symbol: coinData.symbol.toUpperCase(),
              address: address as string,
              chain: chain.name,
              chainId: chain.id,
              marketCap: marketData?.market_cap?.usd,
              price: marketData?.current_price?.usd,
              decimals:
                coinData.detail_platforms?.[platform]?.decimal_place || 18,
              logoURI: coinData.image?.large,
              description: coinData.description?.en?.substring(0, 500), // Limit description length
              priceChange24h: marketData?.price_change_percentage_24h,
              volume24h: marketData?.total_volume?.usd,
              coingeckoId: coinData.id,
              verified: true, // CoinGecko listed tokens are considered verified
              allChains: supportedChainEntries.map(([p, addr]) => {
                const c = getChainByName(p);
                return {
                  chainId: c?.id || 0,
                  chainName: c?.name || p,
                  address: addr as string,
                };
              }),
            });
          }
        }
      } catch (error) {
        logger.warn(`Failed to fetch details for coin ${coinId}:`, error);
        // Continue with next coin
      }
    }

    logger.info(`Found ${tokenInfos.length} tokens for query: ${query}`);
    return tokenInfos;
  } catch (error) {
    logger.error(`Error searching for token ${query}:`, error);
    throw new Error(
      `Failed to search for token: ${error instanceof Error ? error.message : "Unknown error"}`
    );
  }
}

/**
 * Get token info by contract address and chain
 */
export async function getTokenByAddress(
  address: string,
  chainId: number
): Promise<TokenInfo | null> {
  try {
    logger.info(
      `Fetching token info for address ${address} on chain ${chainId}`
    );

    const chain = getChainById(chainId);
    if (!chain) {
      throw new Error(`Unsupported chain ID: ${chainId}`);
    }

    // CoinGecko uses different platform IDs
    const platformMap: Record<string, string> = {
      ethereum: "ethereum",
      "arbitrum-one": "arbitrum",
      "optimistic-ethereum": "optimism",
      "polygon-pos": "polygon",
      base: "base",
      avalanche: "avalanche",
      "binance-smart-chain": "bsc",
    };

    const platformId = platformMap[chain.chainName] || chain.chainName;

    const client = getCoingeckoClient();
    if (!client) {
      logger.warn(
        "CoinGecko API key not found. Cannot fetch token by address."
      );
      return null;
    }

    const tokenData = await retryWithBackoff(async () => {
      return await client.coins.contract.get(address, {
        id: platformId,
      });
    });

    const marketData = tokenData.market_data;

    return {
      name: tokenData.name,
      symbol: tokenData.symbol.toUpperCase(),
      address: address,
      chain: chain.name,
      chainId: chainId,
      marketCap: marketData?.market_cap?.usd,
      price: marketData?.current_price?.usd,
      decimals: tokenData.detail_platforms?.[platformId]?.decimal_place || 18,
      logoURI: tokenData.image?.large,
      description: tokenData.description?.en?.substring(0, 500),
      priceChange24h: marketData?.price_change_percentage_24h,
      volume24h: marketData?.total_volume?.usd,
      coingeckoId: tokenData.id,
      verified: true,
      allChains: Object.entries(tokenData.platforms || {})
        .filter(([p, addr]) => {
          const c = getChainByName(p);
          return c !== undefined && addr;
        })
        .map(([p, addr]) => {
          const c = getChainByName(p);
          return {
            chainId: c?.id || 0,
            chainName: c?.name || p,
            address: addr as string,
          };
        }),
    };
  } catch (error) {
    logger.error(`Error fetching token by address ${address}:`, error);
    return null;
  }
}

/**
 * Get token info by name, symbol, or address
 */
export async function getTokenInfo(
  input: string,
  chainId?: number,
  chainName?: string
): Promise<TokenInfo | TokenInfo[] | null> {
  try {
    // If input is an address, fetch directly
    if (isAddress(input)) {
      if (!chainId && !chainName) {
        throw new Error("Chain must be provided when using token address");
      }

      const resolvedChainId =
        chainId || (chainName ? getChainByName(chainName)?.id : undefined);

      if (!resolvedChainId) {
        throw new Error("Invalid chain specified");
      }

      const tokenInfo = await getTokenByAddress(input, resolvedChainId);
      return tokenInfo;
    }

    // Otherwise, search by name/symbol
    const searchResults = await searchToken(input);

    if (searchResults.length === 0) {
      return null;
    }

    // If single result, return it with all chains information
    // This allows the agent to show all available chains to the user
    if (searchResults.length === 1) {
      return searchResults[0];
    }

    // Multiple results - return array for user selection
    return searchResults;
  } catch (error) {
    logger.error(`Error getting token info for ${input}:`, error);
    throw error;
  }
}

/**
 * Get token price data
 */
export async function getTokenPrice(coingeckoId: string): Promise<{
  price: number;
  priceChange24h?: number;
  marketCap?: number;
} | null> {
  try {
    const client = getCoingeckoClient();
    if (!client) {
      logger.warn("CoinGecko API key not found. Cannot fetch token price.");
      return null;
    }

    const marketData = await retryWithBackoff(async () => {
      return await client.coins.markets.get({
        ids: coingeckoId,
        vs_currency: "usd",
      });
    });

    if (marketData.length === 0) {
      return null;
    }

    const data = marketData[0];
    return {
      price: data.current_price,
      priceChange24h: data.price_change_percentage_24h,
      marketCap: data.market_cap,
    };
  } catch (error) {
    logger.error(`Error fetching price for ${coingeckoId}:`, error);
    return null;
  }
}
