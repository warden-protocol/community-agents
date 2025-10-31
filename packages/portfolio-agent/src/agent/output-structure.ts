import { z } from 'zod';

/**
 * Schema-Guided Reasoning (SGR) for Portfolio Analysis
 *
 * This implementation enforces a streamlined 5-step reasoning process:
 * 1. Request Parsing - extract time period and user intent
 * 2. Portfolio Data Fetching - get wallet balances and historical prices
 * 3. Portfolio Composition Analysis - analyze current holdings
 * 4. Performance Analysis - calculate wins/losses over time period
 * 5. Report Generation - provide comprehensive portfolio report
 */

// ============================================================================
// Portfolio Data Schemas
// ============================================================================

/**
 * Individual token holding data
 */
export const TokenHoldingSchema = z.object({
  tokenId: z.string().describe('CoinGecko token ID'),
  tokenSymbol: z.string().describe('Token symbol (e.g., BTC, ETH)'),
  tokenName: z.string().describe('Full token name'),
  amount: z.number().describe('Amount of tokens held'),
  currentPrice: z.number().describe('Current price in USD'),
  currentValueUSD: z.number().describe('Current value in USD (amount × currentPrice)'),
  historicalPrice: z.number().describe('Price at start of period in USD'),
  historicalValueUSD: z.number().describe('Value at start of period in USD'),
  deltaUSD: z.number().describe('Change in USD value (currentValueUSD - historicalValueUSD)'),
  deltaPercentage: z.number().describe('Percentage change in value'),
  portfolioPercentage: z.number().describe('Percentage of total portfolio value'),
});

/**
 * Portfolio graph data point
 */
export const GraphDataPointSchema = z.object({
  timestamp: z.string().describe('ISO timestamp'),
  totalValueUSD: z.number().describe('Total portfolio value in USD at this time'),
});

/**
 * Wallet information
 */
export const WalletInfoSchema = z.object({
  address: z.string().describe('Wallet address'),
  chain: z.enum(['evm', 'solana']).describe('Blockchain network'),
  totalValueUSD: z.number().describe('Total value of this wallet in USD'),
  tokenCount: z.number().describe('Number of different tokens held'),
});

// ============================================================================
// 5-Step SGR Schema for Portfolio Analysis
// ============================================================================

/**
 * Main SGR schema enforcing 5 mandatory reasoning steps for portfolio analysis
 */
export const ResponseSchema = z
  .object({
    // ========================================
    // STEP 1: Request Parsing
    // ========================================
    step1_requestParsing: z
      .object({
        userQuery: z.string().describe('The original user question'),
        timePeriod: z
          .enum(['daily', 'weekly', 'monthly'])
          .describe('Extracted time period from user query, default to monthly if not specified'),
        reportType: z
          .enum(['portfolio_review', 'daily_report', 'weekly_report', 'monthly_report'])
          .describe('Type of report requested by user'),
        walletAddresses: z
          .object({
            evm: z.string().nullable().describe('EVM wallet address if provided'),
            solana: z.string().nullable().describe('Solana wallet address if provided'),
          })
          .describe('Wallet addresses to analyze'),
        parsingReasoning: z
          .string()
          .describe('Explain how you identified the time period and report type from the user query'),
      })
      .describe(
        'STEP 1 (MANDATORY): Parse user request to extract time period, report type, and wallet addresses. Default to monthly if no time period specified.',
      ),

    // ========================================
    // STEP 2: Portfolio Data Fetching
    // ========================================
    step2_dataFetching: z
      .object({
        toolsUsed: z
          .array(z.string())
          .describe('List of MCP tools and custom tools used (e.g., ["get_historical_portfolio_data", "alchemy_balance", "coingecko_prices"])'),
        walletData: z
          .array(WalletInfoSchema)
          .describe('Data for each wallet analyzed'),
        tokenHoldings: z
          .array(TokenHoldingSchema)
          .describe('Complete token holdings data with current and historical values'),
        fetchingNotes: z
          .string()
          .describe('Notes about the data fetching process: which tools were used, any issues encountered, data availability'),
      })
      .describe(
        'STEP 2 (MANDATORY): Fetch portfolio data using Alchemy for balances and CoinGecko for prices. Use get_historical_portfolio_data tool for structured historical data.',
      ),

    // ========================================
    // STEP 3: Portfolio Composition Analysis
    // ========================================
    step3_compositionAnalysis: z
      .object({
        totalPortfolioValue: z
          .number()
          .describe('Total portfolio value in USD across all wallets'),
        walletBreakdown: z
          .array(z.object({
            wallet: WalletInfoSchema,
            percentage: z.number().describe('Percentage of total portfolio value'),
          }))
          .describe('Breakdown by wallet'),
        tokenBreakdown: z
          .array(z.object({
            token: TokenHoldingSchema,
            percentage: z.number().describe('Percentage of total portfolio value'),
          }))
          .describe('Breakdown by token'),
        topHoldings: z
          .array(TokenHoldingSchema)
          .max(5)
          .describe('Top 5 holdings by value'),
        compositionSummary: z
          .string()
          .describe('Summary of portfolio composition and diversification'),
      })
      .describe(
        'STEP 3 (MANDATORY): Analyze portfolio composition including total value, wallet breakdown, token breakdown, and top holdings.',
      ),

    // ========================================
    // STEP 4: Performance Analysis
    // ========================================
    step4_performanceAnalysis: z
      .object({
        periodStartValue: z
          .number()
          .describe('Total portfolio value at start of period in USD'),
        periodEndValue: z
          .number()
          .describe('Total portfolio value at end of period in USD'),
        totalDeltaUSD: z
          .number()
          .describe('Total change in USD value (end - start)'),
        totalDeltaPercentage: z
          .number()
          .describe('Total percentage change in portfolio value'),
        bestPerformers: z
          .array(TokenHoldingSchema)
          .max(3)
          .describe('Top 3 performing tokens by delta USD'),
        worstPerformers: z
          .array(TokenHoldingSchema)
          .max(3)
          .describe('Bottom 3 performing tokens by delta USD'),
        performanceSummary: z
          .string()
          .describe('Summary of portfolio performance over the time period'),
      })
      .describe(
        'STEP 4 (MANDATORY): Analyze portfolio performance including wins/losses, best/worst performers, and overall performance metrics.',
      ),

    // ========================================
    // STEP 5: Report Generation
    // ========================================
    step5_reportGeneration: z
      .object({
        confidence: z
          .enum(['low', 'medium', 'high'])
          .describe('Confidence level in the analysis based on data completeness'),
        graphData: z
          .array(GraphDataPointSchema)
          .describe('Data points for portfolio value graph over time period'),
        keyInsights: z
          .array(z.string())
          .describe('3-5 key insights from the portfolio analysis'),
        recommendations: z
          .array(z.string())
          .describe('Observations about portfolio composition and performance (not investment advice)'),
        limitations: z
          .array(z.string())
          .describe('Data limitations and analysis constraints'),
        finalAnswer: z
          .string()
          .describe('Comprehensive portfolio report with all findings. Always include "This is not financial advice."'),
      })
      .describe(
        'STEP 5 (MANDATORY): Generate comprehensive portfolio report with graph data, insights, and final analysis. Include confidence assessment and limitations.',
      ),
  })
  .describe(
    '5-step Schema-Guided Reasoning for portfolio analysis. Complete each step in order to provide comprehensive portfolio reports.',
  );
