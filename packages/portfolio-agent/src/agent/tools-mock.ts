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
        {
          symbol: 'ETH',
          chain: 'ethereum',
          startPrice: 3800,
          currentPrice: 4100,
          balance: 0.5,
        },
        {
          symbol: 'TRUMP',
          chain: 'solana',
          startPrice: 20.1,
          currentPrice: 8.08,
          balance: 120,
        },
        {
          symbol: 'WBTC',
          chain: 'ethereum',
          startPrice: 109000,
          currentPrice: 117000,
          balance: 0.0001,
        },
        {
          symbol: 'LINK',
          chain: 'ethereum',
          startPrice: 15.5,
          currentPrice: 17.28,
          balance: 100,
        },
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

function generateStats(
  tokens: {
    symbol: string;
    chain: string;
    startPrice: number;
    currentPrice: number;
    balance: number;
  }[],
): Portfolio {
  let startPeriodAmountUsd = 0;
  let currentTotalAmountUsd = 0;
  const portfolio = new Map<string, TokenStats>();
  for (const { symbol, chain, startPrice, currentPrice, balance } of tokens) {
    startPeriodAmountUsd += startPrice * balance;
    currentTotalAmountUsd += currentPrice * balance;
    portfolio.set(symbol, {
      symbol,
      name: symbol,
      chain,
      amount: balance,
      amountUsd: currentPrice * balance,
      currentPrice: currentPrice,
      startPeriodPrice: startPrice,
      priceChange: currentPrice - startPrice,
      priceChangePercent: ((currentPrice - startPrice) / startPrice) * 100,
    });
  }
  return {
    tokens: portfolio,
    startPeriodAmountUsd,
    currentTotalAmountUsd,
  };
}
