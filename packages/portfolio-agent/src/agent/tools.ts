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
  description: `This endpoint allows you to **query historical portfolio data for EVM and Solana wallets with token balances, prices, and performance metrics**

# Response Schema
\`\`\`json
{
  type: 'object',
  properties: {
    tokens: {
      type: 'object',
      description: 'Map of token symbols to their statistics',
      additionalProperties: {
        type: 'object',
        properties: {
          symbol: {
            type: 'string',
            description: 'token symbol (e.g., ETH, PEPE)'
          },
          name: {
            type: 'string',
            description: 'token name'
          },
          chain: {
            type: 'string',
            description: 'blockchain network (e.g., ethereum, solana)'
          },
          amount: {
            type: 'number',
            description: 'token balance amount held in wallet'
          },
          amountUsd: {
            type: 'number',
            description: 'token balance value in USD at start of period'
          },
          currentPrice: {
            type: 'number',
            description: 'current token price in USD'
          },
          startPeriodPrice: {
            type: 'number',
            description: 'token price in USD at start of analysis period'
          },
          priceChange: {
            type: 'number',
            description: 'absolute price change in USD (current - start)'
          },
          priceChangePercent: {
            type: 'number',
            description: 'price change percentage over the period'
          }
        },
        required: [
          'symbol',
          'name',
          'chain',
          'amount',
          'amountUsd',
          'currentPrice',
          'startPeriodPrice',
          'priceChange',
          'priceChangePercent'
        ]
      }
    },
    startPeriodAmountUsd: {
      type: 'number',
      description: 'total portfolio value in USD at start of period'
    },
    currentTotalAmountUsd: {
      type: 'number',
      description: 'current total portfolio value in USD'
    }
  },
  required: [
    'tokens',
    'startPeriodAmountUsd',
    'currentTotalAmountUsd'
  ]
}
\`\`\``,
  schema: z.object({
    evmWalletAddress: z
      .string()
      .describe('The EVM wallet address to analyze (e.g., 0x...)'),
    solanaWalletAddress: z
      .string()
      .describe(
        'The Solana wallet address to analyze (e.g., base58 encoded address)',
      ),
    timeframe: z
      .enum(['daily', 'weekly', 'monthly'])
      .describe(
        'The time period for historical analysis \n Valid values: daily, weekly, monthly',
      ),
  }),
  func: async () // {
  // evmWalletAddress,
  // solanaWalletAddress,
  // timeframe,
  // },
  : Promise<string> => {
    try {
      const portfolio = generateStats([
        { symbol: 'ETH', chain: 'ethereum' },
        { symbol: 'PEPE', chain: 'solana' },
      ]);
      return JSON.stringify({
        ...portfolio,
        tokens: Object.fromEntries(portfolio.tokens),
      });
    } catch (error) {
      return JSON.stringify({
        error: `Failed to fetch historical data: ${error.message}`,
      });
    }
  },
});

function generateStats(tokens: { symbol: string; chain: string }[]): Portfolio {
  let startPeriodAmountUsd = 0;
  let currentTotalAmountUsd = 0;
  const portfolio = new Map<string, TokenStats>();
  for (const token of tokens) {
    const startPeriodPrice = 1000 + Math.random() * 200 - 100;
    const currentPrice = 1000 + Math.random() * 200 - 100;
    const balance = 100 + Math.random() * 20 - 10;
    startPeriodAmountUsd += startPeriodPrice * balance;
    currentTotalAmountUsd += currentPrice * balance;
    portfolio.set(token.symbol, {
      symbol: token.symbol,
      name: token.symbol,
      chain: token.chain,
      amount: balance,
      amountUsd: startPeriodPrice * balance,
      currentPrice: currentPrice,
      startPeriodPrice: startPeriodPrice,
      priceChange: currentPrice - startPeriodPrice,
      priceChangePercent:
        ((currentPrice - startPeriodPrice) / startPeriodPrice) * 100,
    });
  }
  return {
    tokens: portfolio,
    startPeriodAmountUsd,
    currentTotalAmountUsd,
  };
}
