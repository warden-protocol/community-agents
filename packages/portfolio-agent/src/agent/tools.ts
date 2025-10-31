import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';

// const chains = ['eth-mainnet', 'sol-mainnet'];

export interface Portfolio {
  tokens: Map<string, TokenStats>;
  startPeriodAmountUsd: number;
  currentTotalAmountUsd: number;
}

export interface TokenStats {
  symbol: string;
  name: string;
  chain: string;
  amount: number;
  amountUsd: number;
  currentPrice: number;
  startPeriodPrice: number;
  priceChange: number;
  priceChangePercent: number;
}

/**
 * Custom tool for fetching historical portfolio data
 * This tool combines wallet balance data with historical price data
 */
export const getHistoricalPortfolioDataTool = new DynamicStructuredTool({
  name: 'get_historical_portfolio_data',
  description:
    'Fetch historical portfolio data including token balances and prices for a specific time period',
  schema: z.object({
    evmWalletAddress: z.string().describe('The EVM wallet address to analyze'),
    solanaWalletAddress: z
      .string()
      .describe('The Solana wallet address to analyze'),
    timeframe: z
      .enum(['daily', 'weekly', 'monthly'])
      .describe('The time period for analysis'),
  }),
  func: async ({
    // evmWalletAddress,
    // solanaWalletAddress,д
    timeframe,
  }): Promise<string> => {
    try {
      const now = new Date();
      let startDate: Date;
      let points: number;

      switch (timeframe) {
        case 'daily':
          startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          points = 24;
          break;
        case 'weekly':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          points = 7;
          break;
        case 'monthly':
          startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          points = 30;
          break;
        default:
          startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      }
      const portfolio = generateStats(['ETH', 'KSM'], points);
      return JSON.stringify(portfolio);
    } catch (error) {
      return JSON.stringify({
        error: `Failed to fetch historical data: ${error.message}`,
      });
    }
  },
});

function generateStats(tokens: string[], points: number): Portfolio {
  // todo

  return {};
}
