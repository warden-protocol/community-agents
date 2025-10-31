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
  symbol: z.string().describe('Token symbol (e.g., BTC, ETH)'),
  name: z.string().describe('Full token name'),
  chain: z.string().describe('Blockchain network (e.g., ethereum, solana)'),
  amount: z.number().describe('Amount of tokens held'),
  amountUsd: z.number().describe('Amount of tokens held in USD'),
  currentPrice: z.number().describe('Current price in USD'),
  historicalPrice: z.number().describe('Price at start of period in USD'),
  priceChange: z
    .number()
    .describe('Price change in USD (currentPrice - historicalPrice)'),
  priceChangePercent: z
    .number()
    .describe(
      'Price change percentage (currentPrice - historicalPrice) / historicalPrice',
    ),
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
          .describe(
            'Extracted time period from user query, default to monthly if not specified',
          ),
        reportType: z
          .enum([
            'portfolio_review',
            'daily_report',
            'weekly_report',
            'monthly_report',
          ])
          .describe('Type of report requested by user'),
        walletAddresses: z
          .object({
            evm: z
              .string()
              .nullable()
              .describe('EVM wallet address if provided'),
            solana: z
              .string()
              .nullable()
              .describe('Solana wallet address if provided'),
          })
          .describe('Wallet addresses to analyze'),
        parsingReasoning: z
          .string()
          .describe(
            'Explain how you identified the time period and report type from the user query',
          ),
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
          .describe(
            'List of used tools (e.g., ["get_historical_portfolio_data"])',
          ),
        porfolio: z
          .array(TokenHoldingSchema)
          .describe(
            'Complete token holdings data with current and historical values',
          ),
        fetchingNotes: z
          .string()
          .describe(
            'Notes about the data fetching process: which tools were used, any issues encountered, data availability',
          ),
      })
      .describe(
        'STEP 2 (MANDATORY): Call get_historical_portfolio_data tool EXACTLY ONCE using the timeframe from STEP 1. DO NOT call the tool multiple times with different timeframes.',
      ),

    // ========================================
    // STEP 3: Portfolio Composition Analysis
    // ========================================
    step3_compositionAnalysis: z
      .object({
        totalPortfolioValue: z
          .number()
          .describe('Total portfolio value in USD across all tokens'),
        topHoldings: z
          .array(z.string())
          .max(5)
          .describe('Top 5 tokens by USD value in portfolio'),
        compositionSummary: z
          .string()
          .describe('Summary of portfolio composition and diversification'),
      })
      .describe(
        'STEP 3 (MANDATORY): Analyze portfolio composition including total value, top tokens by USD value in portfolio, and summary of portfolio composition and diversification.',
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
          .describe('Total percentage change in portfolio USD value'),
        bestPerformers: z
          .array(z.string())
          .max(3)
          .describe('Top 3 performing tokens by USD value change'),
        worstPerformers: z
          .array(z.string())
          .max(3)
          .describe('Bottom 3 performing tokens by USD value change'),
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
          .describe(
            'Confidence level in the analysis based on data completeness',
          ),
        error: z
          .enum(['tool_error', 'llm_error', 'user_error', 'no_error'])
          .describe(
            'The type of error that occurred. tool_error=the tool call failed, user_error=the user question contains non-cryptocurrency related content or violates the critical rules, llm_error=all other errors, no_error=no error occurred',
          ),
        keyTakeaways: z
          .array(z.string())
          .describe('3-5 key takeaways from the portfolio analysis'),
        recommendations: z
          .array(z.string())
          .describe(
            'Observations about portfolio composition and performance (not investment advice)',
          ),
        limitations: z
          .array(z.string())
          .describe('Data limitations and analysis constraints'),
        summary: z
          .string()
          .describe(
            'Summary of the portfolio analysis. Always include "This is not financial advice."',
          ),
      })
      .describe(
        'STEP 5 (MANDATORY): Generate comprehensive portfolio report with graph data, insights, and final analysis. Include confidence assessment and limitations.',
      ),
  })
  .describe(
    '5-step Schema-Guided Reasoning for portfolio analysis. Complete each step in order to provide comprehensive portfolio reports.',
  );
