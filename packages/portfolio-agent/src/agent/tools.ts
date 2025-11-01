import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { getPortfolioService } from '../utils/portfolio';

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
      description: 'Array of top gaining tokens in the market during the period',
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
      description: 'Array of top losing tokens in the market during the period',
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
    }
  },
  required: [
    'tokens',
    'startPeriodTotalAmountUsd',
    'totalAmountUsd',
    'totalAmountChange',
    'totalAmountChangePercent',
    'topGainers',
    'topLosers'
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
        'The timeframe for historical analysis. Valid values: daily, weekly, monthly',
      ),
  }),
  func: async (input: {
    evmWalletAddress?: string;
    solanaWalletAddress?: string;
    timeframe: 'daily' | 'weekly' | 'monthly';
  }): Promise<string> => {
    try {
      const portfolioService = getPortfolioService();
      const portfolioChange = await portfolioService.getPortfolioChange(
        {
          evmAddress: input.evmWalletAddress,
          solanaAddress: input.solanaWalletAddress,
        },
        input.timeframe,
      );

      return JSON.stringify(portfolioChange);
    } catch (error) {
      return JSON.stringify({
        error: `Failed to fetch historical data: ${error.message}`,
      });
    }
  },
});
