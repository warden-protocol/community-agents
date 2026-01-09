import { tool } from '@langchain/core/tools';
import { z } from 'zod';
import {
  fetchFundingHistory,
  fetchLatestFundingRate,
  getActiveMarkets,
  fetchMultipleFundingRates,
  fetchTopFundingRates,
  processFundingEntry,
} from './api';

const fundingHistorySchema = z.object({
  coin: z.string().describe('The coin symbol (e.g., BTC, ETH, SOL)'),
  startTime: z
    .number()
    .describe(
      'Start time in milliseconds since epoch. Use Date.now() - milliseconds for relative times.',
    ),
  endTime: z
    .number()
    .optional()
    .describe(
      'Optional end time in milliseconds since epoch. Defaults to current time if not provided.',
    ),
});

const coinSchema = z.object({
  coin: z.string().describe('The coin symbol (e.g., BTC, ETH, SOL)'),
});

const emptySchema = z.object({});

const multipleCoinsSchema = z.object({
  coins: z
    .array(z.string())
    .describe('Array of coin symbols (e.g., ["BTC", "ETH", "SOL"])'),
});

const topFundingRatesSchema = z.object({
  limit: z
    .number()
    .default(10)
    .describe('Number of top results to return (default: 10)'),
  sortOrder: z
    .enum(['highest', 'lowest'])
    .default('highest')
    .describe('Sort by highest or lowest funding rate APR'),
});

export const getFundingHistoryTool = tool(
  async (input): Promise<string> => {
    const { coin, startTime, endTime } = input;
    const data = await fetchFundingHistory(coin, startTime, endTime);
    const results = data.map((entry) => processFundingEntry(entry, true));
    return JSON.stringify(results, null, 2);
  },
  {
    name: 'get_funding_history',
    description:
      'Get funding rate history for a specific coin on Hyperliquid. Returns historical funding rates with timestamps. Funding rates are settled every hour.',
    schema: fundingHistorySchema,
  },
);

export const getCurrentFundingRateTool = tool(
  async (input): Promise<string> => {
    const { coin } = input;
    const result = await fetchLatestFundingRate(coin);

    if (!result) {
      return JSON.stringify({
        error: `No funding rate data found for ${coin}`,
      });
    }

    return JSON.stringify(result);
  },
  {
    name: 'get_current_funding_rate',
    description:
      'Get the current/latest funding rate for a specific coin on Hyperliquid. Returns the most recent funding rate and calculated APR.',
    schema: coinSchema,
  },
);

export const getAvailableMarketsTool = tool(
  async (): Promise<string> => {
    const activeMarkets = await getActiveMarkets();

    return JSON.stringify({
      totalMarkets: activeMarkets.length,
      markets: activeMarkets,
    });
  },
  {
    name: 'get_available_markets',
    description:
      'Get a list of all available perpetual futures markets on Hyperliquid. Returns coin symbols and their max leverage.',
    schema: emptySchema,
  },
);

export const getMultipleFundingRatesTool = tool(
  async (input): Promise<string> => {
    const { coins } = input;
    const { results, errors } = await fetchMultipleFundingRates(coins);

    return JSON.stringify({ results, errors });
  },
  {
    name: 'get_multiple_funding_rates',
    description:
      'Get current funding rates for multiple coins at once. Useful for comparing funding rates across different assets.',
    schema: multipleCoinsSchema,
  },
);

export const getTopFundingRatesTool = tool(
  async (input): Promise<string> => {
    const { limit, sortOrder } = input;
    const { topRates, totalMarketsAnalyzed } = await fetchTopFundingRates(
      limit,
      sortOrder,
    );

    return JSON.stringify({
      sortOrder,
      topRates,
      totalMarketsAnalyzed,
    });
  },
  {
    name: 'get_top_funding_rates',
    description:
      'Get the top funding rates across all Hyperliquid markets. Can sort by highest or lowest APR. Useful for finding arbitrage opportunities.',
    schema: topFundingRatesSchema,
  },
);

export function getHyperliquidTools() {
  return [
    getFundingHistoryTool,
    getCurrentFundingRateTool,
    getAvailableMarketsTool,
    getMultipleFundingRatesTool,
    getTopFundingRatesTool,
  ];
}
