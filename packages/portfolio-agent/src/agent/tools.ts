import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { getPortfolioService } from '../utils/portfolio';

export const ToolName = 'get_historical_portfolio_data';
export const ToolDescription = `This endpoint allows you to **query historical portfolio data for EVM and Solana wallets with token balances, prices, and performance metrics**

# Response Schema
\`\`\`json
{
  type: 'object',
  properties: {
    tokens: {
      type: 'array',
      description: 'Array of tokens in the portfolio with their statistics',
      items: {
        type: 'object',
        properties: {
          coingeckoId: {
            type: 'string',
            description: 'CoinGecko token identifier'
          },
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
            description: 'blockchain network (e.g., eth-mainnet, base-mainnet, bnb-mainnet, solana-mainnet)'
          },
          amount: {
            type: 'number',
            description: 'token balance amount held in wallet'
          },
          amountUsd: {
            type: 'number',
            description: 'current token balance value in USD'
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
          'coingeckoId',
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
    tokensPerformanceOrdered: {
      type: 'array',
      description: 'Array of token symbols sorted by performance in the portfolio',
      items: {
        type: 'string',
        description: 'token symbol'
      }
    },
    startPeriodTotalAmountUsd: {
      type: 'number',
      description: 'total portfolio value in USD at start of period'
    },
    totalAmountUsd: {
      type: 'number',
      description: 'current total portfolio value in USD'
    },
    totalAmountChange: {
      type: 'number',
      description: 'absolute change in portfolio value in USD (current - start)'
    },
    totalAmountChangePercent: {
      type: 'number',
      description: 'percentage change in portfolio value over the period'
    },
    topGainers: {
      type: 'array',
      description: 'Top gaining tokens from the overall cryptocurrency market (NOT from the user portfolio - this is market-wide data for comparison)',
      items: {
        type: 'object',
        properties: {
          coingeckoId: {
            type: 'string',
            description: 'CoinGecko token identifier'
          },
          symbol: {
            type: 'string',
            description: 'token symbol'
          },
          name: {
            type: 'string',
            description: 'token name'
          },
          marketCapRank: {
            type: 'number',
            description: 'market capitalization rank'
          },
          currentPrice: {
            type: 'number',
            description: 'current token price in USD'
          },
          priceChange: {
            type: 'number',
            description: 'price change percentage over the period'
          }
        },
        required: [
          'coingeckoId',
          'symbol',
          'name',
          'marketCapRank',
          'currentPrice',
          'priceChange'
        ]
      }
    },
    topLosers: {
      type: 'array',
      description: 'Top losing tokens from the overall cryptocurrency market (NOT from the user portfolio - this is market-wide data for comparison)',
      items: {
        type: 'object',
        properties: {
          coingeckoId: {
            type: 'string',
            description: 'CoinGecko token identifier'
          },
          symbol: {
            type: 'string',
            description: 'token symbol'
          },
          name: {
            type: 'string',
            description: 'token name'
          },
          marketCapRank: {
            type: 'number',
            description: 'market capitalization rank'
          },
          currentPrice: {
            type: 'number',
            description: 'current token price in USD'
          },
          priceChange: {
            type: 'number',
            description: 'price change percentage over the period'
          }
        },
        required: [
          'coingeckoId',
          'symbol',
          'name',
          'marketCapRank',
          'currentPrice',
          'priceChange'
        ]
      }
    },
    createdAt: {
      type: 'string',
      description: 'Date and time of the portfolio analysis in ISO format'
    },
    timeframe: {
      type: 'string',
      description: 'The timeframe for historical analysis. Valid values: daily, weekly, monthly'
    }
  },
  required: [
    'tokens',
    'tokensPerformanceOrdered',
    'startPeriodTotalAmountUsd',
    'totalAmountUsd',
    'totalAmountChange',
    'totalAmountChangePercent',
    'topGainers',
    'topLosers',
    'createdAt',
    'timeframe'
  ]
}
\`\`\``;

export const ToolSchema = z.object({
  evmWalletAddress: z
    .string()
    .describe('The EVM wallet address to analyze (e.g., 0x...)'),
  solanaWalletAddress: z
    .string()
    .describe(
      'The Solana wallet address to analyze (e.g., base58 encoded address)',
    ),
  timeframe: z
    .enum(['unknown', 'daily', 'weekly', 'monthly'])
    .describe(
      'The timeframe for historical analysis. Valid values: daily, weekly, monthly',
    ),
});

/**
 * Custom tool for fetching historical portfolio data
 * This tool combines wallet balance data with historical price data
 */
export const getHistoricalPortfolioDataTool = new DynamicStructuredTool({
  name: ToolName,
  description: ToolDescription,
  schema: ToolSchema,
  func: async (input: {
    evmWalletAddress?: string;
    solanaWalletAddress?: string;
    timeframe: 'unknown' | 'daily' | 'weekly' | 'monthly';
  }): Promise<string> => {
    try {
      const portfolioService = getPortfolioService();
      const portfolioChange = await portfolioService.getPortfolioChange(
        {
          evmAddress: input.evmWalletAddress,
          solanaAddress: input.solanaWalletAddress,
        },
        input.timeframe === 'unknown' ? 'monthly' : input.timeframe,
      );

      return JSON.stringify(portfolioChange);
    } catch (error) {
      return JSON.stringify({
        error: `Failed to fetch historical data: ${error.message}`,
      });
    }
  },
});
