import { z } from 'zod';

/**
 * Schema-Guided Reasoning (SGR) for Cryptocurrency Analysis
 *
 * Based on SGR principles from https://abdullin.com/schema-guided-reasoning/
 *
 * This implementation enforces a streamlined 6-step reasoning process:
 * 0. Request Validation - validate the user request
 * 1. Token Extraction - identify tokens from user query (max 2)
 * 2. Token Data Fetching - query CoinGecko for comprehensive data
 * 3. Token Data Validation - assess data completeness and quality
 * 4. Token Data Analysis - analyze risk and performance
 * 5. Reasoning Confidence Answer - provide confident, actionable response
 */

// ============================================================================
// Token Data Schema
// ============================================================================

/**
 * Comprehensive token data structure with all metrics needed for analysis
 */
export const TokenDataSchema = z.object({
  tokenId: z
    .string()
    .describe(
      'The CoinGecko ID of the cryptocurrency (e.g., bitcoin, ethereum) extracted from get_search tool',
    ),
  tokenSymbol: z
    .string()
    .describe('The symbol of the cryptocurrency in uppercase (e.g., BTC, ETH)'),
  tokenName: z.string().describe('The full name of the cryptocurrency'),

  // Price metrics
  currentPrice: z
    .number()
    .describe('Current price in USD from get_coins_markets'),
  priceChangePercentage24h: z
    .number()
    .nullable()
    .optional()
    .describe('24-hour price change percentage (if available)'),
  priceChangePercentage7d: z
    .number()
    .nullable()
    .optional()
    .describe('7-day price change percentage (if available)'),

  // Market metrics
  marketCap: z
    .number()
    .nullable()
    .optional()
    .describe('Market capitalization in USD (if available)'),
  marketCapRank: z
    .number()
    .nullable()
    .optional()
    .describe('Market cap ranking (lower is better)'),

  // Liquidity/Volume metrics
  tradingVolume24h: z
    .number()
    .nullable()
    .optional()
    .describe('24-hour trading volume in USD (if available)'),
  volumeToMarketCapRatio: z
    .number()
    .nullable()
    .optional()
    .describe('Trading volume / market cap ratio (indicator of liquidity)'),

  // Volatility metrics
  highLow24h: z
    .object({
      high: z.number().nullable().optional(),
      low: z.number().nullable().optional(),
    })
    .nullable()
    .optional()
    .describe('24-hour high and low prices (for volatility calculation)'),
  athChangePercentage: z
    .number()
    .nullable()
    .optional()
    .describe(
      'Percentage change from all-time high (volatility indicator) (if available)',
    ),
  missingDataPoints: z
    .array(z.string())
    .describe(
      'List any missing data points (e.g., "priceChange24h", "priceChange7d", "marketCap", "marketCapRank", "tradingVolume24h", "volumeToMarketCapRatio"). Field is missing if its value is null or zero. Empty array if complete.',
    ),
});

// ============================================================================
// 6-Step SGR Schema
// ============================================================================

/**
 * Main SGR schema enforcing 6 mandatory reasoning steps
 */
export const ResponseSchema = z
  // ========================================
  // STEP 0: Request Validation
  // ========================================
  .object({
    step0_requestValidation: z
      .object({
        validationReasoning: z
          .string()
          .describe(
            'Explain why the request is valid or invalid and why model can respond to it',
          ),
        requestValid: z
          .boolean()
          .describe(
            'Whether the user request is valid, does not violate the critical rules and model can respond to it',
          ),
        error: z
          .enum([
            'invalid_request_error',
            'investment_advice_error',
            'no_error',
          ])
          .describe(
            'The type of error that occurred. invalid_request_error=the user question contains non-cryptocurrency related content or violates the critical rules, investment_advice_error=the model cannot provide investment advice (e.g., when user asks for buying recommendations and model refuses to provide financial advice), no_error=no error occurred',
          ),
      })
      .describe(
        'STEP 0 (MANDATORY): Validate the user request. Whether the request is valid, does not violate the critical rules and model can respond to it',
      ),
    // ========================================
    // STEP 1: Token Extraction (max 2 tokens)
    // ========================================
    step1_tokenExtraction: z
      .object({
        userQuery: z.string().describe('The original user question'),
        extractionReasoning: z
          .string()
          .describe(
            'Explain how you identified these tokens from the question. Quote the relevant parts of the user query.',
          ),
        extractedTokens: z
          .array(z.string())
          .max(2)
          .describe(
            'Token symbols or names extracted from the user query. MAXIMUM 2 tokens. Extract the exact tokens mentioned by the user.',
          ),
        tokenCount: z
          .number()
          .describe('Number of tokens to analyze (must be 1 or 2)'),
      })
      .describe(
        'STEP 1 (MANDATORY): Extract token identifiers from user query. Maximum 2 tokens allowed. Identify exactly which tokens the user is asking about.',
      ),
    // ========================================
    // STEP 2: Token Data Fetching
    // ========================================
    step2_dataFetching: z
      .object({
        toolsUsed: z
          .array(z.string())
          .describe(
            'List of MCP tools queried (e.g., ["get_search", "get_coins_markets"])',
          ),
        tokensData: z
          .array(TokenDataSchema)
          .max(2)
          .describe(
            'Complete data for each token. Use get_search to find token IDs, then get_coins_markets to fetch all metrics: price, market cap, volume, rank, price changes, etc.',
          )
          .transform((data) =>
            data.filter(
              (token, index, arr) =>
                arr.findIndex((t) => t.tokenId === token.tokenId) === index,
            ),
          ),
        fetchingNotes: z
          .string()
          .describe(
            'Notes about the data fetching process: which tools were used, any issues encountered, data availability',
          ),
      })
      .describe(
        'STEP 2 (MANDATORY): Fetch comprehensive token data using CoinGecko MCP tools. First use get_search to get token IDs, then get_coins_markets for detailed metrics.',
      ),

    // ========================================
    // STEP 3: Token Data Validation
    // ========================================
    step3_validation: z
      .object({
        dataCompleteness: z
          .enum(['complete', 'partial', 'insufficient'])
          .describe(
            'Assess data completeness: complete=all metrics available, partial=some metrics missing, insufficient=cannot provide reliable analysis',
          ),
        dataQualityIssues: z
          .array(z.string())
          .describe(
            'List any data quality concerns (e.g., "stale data", "low volume", "unverified token"). Empty array if no issues.',
          ),
        validationSummary: z
          .string()
          .describe(
            'Summary of data validation: can we proceed with confident analysis or are there limitations?',
          ),
      })
      .describe(
        'STEP 3 (MANDATORY): Validate the fetched data. Assess completeness, identify missing points, flag quality issues. This checkpoint ensures data reliability.',
      ),

    // ========================================
    // STEP 4: Token Data Analysis
    // ========================================
    step4_analysis: z
      .object({
        // Risk Analysis
        riskAnalysis: z
          .object({
            volatilityRisk: z.object({
              reasoning: z
                .string()
                .describe(
                  'Explain volatility: analyze 24h/7d price changes, price swings. High volatility = >5% daily changes, Medium = 2-5%, Low = <2%. Do not make any assumptions if no data available',
                ),
              level: z
                .enum(['low', 'medium', 'high', 'unknown'])
                .describe(
                  'Volatility risk level based on price changes. Use unknown if required data is missing.',
                ),
            }),
            liquidityRisk: z.object({
              reasoning: z
                .string()
                .describe(
                  'Explain liquidity: analyze volume to market cap ratio. High liquidity (low risk) = >5%, Medium = 1-5%, Low liquidity (high risk) = <1%. Do not make any assumptions if no data available.',
                ),
              level: z
                .enum(['low', 'medium', 'high', 'unknown'])
                .describe(
                  'Liquidity risk level based on volume/market cap. Use unknown if required data is missing.',
                ),
            }),
            marketCapRisk: z.object({
              reasoning: z
                .string()
                .describe(
                  'Explain market cap risk: larger market caps = lower risk (more established), smaller = higher risk (more volatile/speculative). Do not make any assumptions if no data available.',
                ),
              level: z
                .enum(['low', 'medium', 'high', 'unknown'])
                .describe(
                  'Market cap risk level. Use unknown if required data is missing.',
                ),
            }),
            overallRiskAssessment: z
              .string()
              .describe(
                'Overall risk summary for the token(s). Combine volatility, liquidity, and market cap risks into a cohesive assessment.',
              ),
          })
          .describe(
            'Risk analysis: evaluate volatility risk, liquidity risk, and market cap risk for each token',
          ),

        // Performance Analysis
        performanceAnalysis: z
          .object({
            trendReasoning: z
              .string()
              .describe(
                'Explain the trend: analyze 24h and 7d price changes, identify momentum direction and strength',
              ),
            priceTrend: z
              .enum(['bullish', 'bearish', 'neutral', 'unknown'])
              .describe(
                'Overall price trend: bullish=positive momentum, bearish=negative momentum, neutral=stable/mixed. Use unknown if no data available.',
              ),
            performanceMetrics: z
              .string()
              .describe(
                'Key performance observations: absolute price changes, percentage changes, comparison to market, momentum indicators',
              ),
            comparativePerformance: z
              .string()
              .nullable()
              .optional()
              .describe(
                'If analyzing multiple tokens, compare their relative performance. Which is performing better and why?',
              ),
          })
          .describe(
            'Performance analysis: evaluate price trends, momentum, and comparative performance',
          ),

        // Analysis Summary
        analysisSummary: z
          .string()
          .describe(
            'Overall analysis summary: synthesize risk and performance findings into key insights. What are the most important takeaways?',
          ),
      })
      .describe(
        'STEP 4 (MANDATORY): Analyze the validated data. Perform risk analysis (volatility, liquidity, market cap) and performance analysis (trends, momentum). Be specific and quantitative.',
      ),

    // ========================================
    // STEP 5: Reasoning Confidence Answer
    // ========================================
    step5_confidenceAnswer: z
      .object({
        confidenceReasoning: z
          .string()
          .describe(
            'Explain your confidence level: do you have all the data needed to answer this specific question? What factors affect confidence?',
          ),
        confidence: z
          .enum(['low', 'medium', 'high'])
          .describe(
            'Confidence level based ONLY on data needed for THIS question: high=have all required data, medium=mixed signals in available data, low=missing data needed for THIS answer. Missing optional/unrelated data should NOT lower confidence.',
          ),
        error: z
          .enum(['tool_error', 'llm_error', 'user_error', 'no_error'])
          .describe(
            'The type of error that occurred. tool_error=the tool call failed, user_error=the user question contains non-cryptocurrency related content or violates the critical rules, llm_error=all other errors, no_error=no error occurred',
          ),
        reasoning: z
          .string()
          .describe(
            'Comprehensive reasoning for your answer: connect insights from steps 1-4. Reference specific metrics, risks, and performance indicators. Make logical connections.',
          ),
        answer: z
          .string()
          .describe(
            'Clear, actionable answer to the user\'s question. Be direct and specific. Reference key findings. If comparison, state your recommendation clearly. Always add "This is not financial advice."',
          ),
        keyTakeaways: z
          .array(z.string())
          .describe(
            '3-5 bullet points summarizing the most important insights from your analysis',
          ),
        caveats: z
          .array(z.string())
          .describe(
            'Important warnings and limitations: data limitations, market volatility, "not financial advice", specific risks identified',
          ),
      })
      .describe(
        'STEP 5 (MANDATORY): Provide confident answer with reasoning. Synthesize all previous steps into actionable insight. Include confidence assessment, comprehensive reasoning, clear answer, key takeaways, and appropriate caveats.',
      ),
  })
  .describe(
    '6-step Schema-Guided Reasoning for cryptocurrency analysis. Complete each step in order. Maximum 2 tokens per analysis.',
  );
