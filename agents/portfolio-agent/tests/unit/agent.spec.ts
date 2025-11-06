import { describe, it, beforeAll, expect } from 'vitest';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { ToolName, ToolDescription, ToolSchema } from '../../src/agent/tools';
import { AIMessage, BaseMessage, ToolMessage } from '@langchain/core/messages';
import { ResponseSchema } from '../../src/agent/output-structure';
import { SystemPrompt } from '../../src/agent/system-prompt';
import { DynamicStructuredTool } from '@langchain/core/tools';
import { PortfolioChange, PortfolioToken } from '../../src/utils/portfolio';

const evmWalletAddress = '0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6';
const solanaWalletAddress = '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM';

function formatUserPrompt(prompt: string): string {
  return `Wallet addresses: EVM: ${evmWalletAddress}, Solana: ${solanaWalletAddress}\n\nUser question: ${prompt}`;
}

function createPorfolioData(
  timeframe: 'daily' | 'weekly' | 'monthly',
): PortfolioChange {
  return {
    tokens: [
      {
        coingeckoId: 'ethereum',
        symbol: 'ETH',
        name: 'Ethereum',
        chain: 'eth-mainnet',
        amount: 0.5,
        amountUsd: 2000,
        currentPrice: 4000,
        startPeriodPrice: 3000,
        priceChange: 1000,
        priceChangePercent: 33.33,
      },
      {
        coingeckoId: 'trump',
        symbol: 'TRUMP',
        name: 'Trump',
        chain: 'solana-mainnet',
        amount: 120,
        amountUsd: 960,
        currentPrice: 8,
        startPeriodPrice: 20,
        priceChange: -12,
        priceChangePercent: -40,
      },
      {
        coingeckoId: 'usdc',
        symbol: 'USDC',
        name: 'USDC',
        chain: 'solana-mainnet',
        amount: 100,
        amountUsd: 100.01,
        currentPrice: 1.0001,
        startPeriodPrice: 1,
        priceChange: 0.0001,
        priceChangePercent: 0.01,
      },
    ],
    tokensOrderedByPerformance: ['ETH', 'USDC', 'TRUMP'],
    startPeriodTotalAmountUsd: 4000,
    totalAmountUsd: 3060.01,
    totalAmountChange: -939.99,
    totalAmountChangePercent: -23.5,
    topGainers: [
      {
        coingeckoId: 'ethereum',
        symbol: 'ETH',
        name: 'Ethereum',
        marketCapRank: 2,
        currentPrice: 4000,
        priceChange: 1000,
      },
      {
        coingeckoId: 'gmx',
        symbol: 'GMX',
        name: 'GMX',
        marketCapRank: 200,
        currentPrice: 100,
        priceChange: 10,
      },
      {
        coingeckoId: 'figr_heloc',
        symbol: 'FIGR_HELOC',
        name: 'FIGR_HELOC',
        marketCapRank: 294,
        currentPrice: 1.0447354,
        priceChange: 0.34,
      },
    ],
    topLosers: [
      {
        coingeckoId: 'trump',
        symbol: 'TRUMP',
        name: 'Trump',
        marketCapRank: 1000,
        currentPrice: 8,
        priceChange: -12,
      },
      {
        coingeckoId: 'jelly_my_jelly',
        symbol: 'JELLYJELLY',
        name: 'JELLYJELLY',
        marketCapRank: 335,
        currentPrice: 0.08,
        priceChange: -0.04,
      },
      {
        coingeckoId: 'believe',
        symbol: 'BELIEVE',
        name: 'BELIEVE',
        marketCapRank: 852,
        currentPrice: 0.03,
        priceChange: -0.01,
      },
    ],
    createdAt: new Date().toISOString(),
    timeframe: timeframe,
  };
}

function createTools(porfolioData: PortfolioChange) {
  return [
    new DynamicStructuredTool({
      name: ToolName,
      description: ToolDescription,
      schema: ToolSchema,
      func: async (input: {
        evmWalletAddress?: string;
        solanaWalletAddress?: string;
        timeframe: 'unknown' | 'daily' | 'weekly' | 'monthly';
      }): Promise<string> => {
        return JSON.stringify(porfolioData);
      },
    }),
  ];
}

function filterAIMessagesWithToolCall(messages: BaseMessage[]): AIMessage[] {
  return messages.filter(
    (x: BaseMessage) =>
      x.getType() === 'ai' && ((x as AIMessage).tool_calls?.length ?? 0) > 0,
  ) as AIMessage[];
}

function assertStep1RequestParsing(
  step1: {
    timeframe?: 'unknown' | 'daily' | 'weekly' | 'monthly';
    userQuery?: string;
    walletAddresses?: { evm?: string | null; solana?: string | null };
    parsingReasoning?: string;
  },
  expectedUserQuery: string,
  expectedTimeframe: 'unknown' | 'daily' | 'weekly' | 'monthly',
) {
  expect(step1.userQuery).toBe(expectedUserQuery);
  expect(step1.timeframe).toBe(expectedTimeframe);
  expect(step1.walletAddresses!.evm).toBe(evmWalletAddress);
  expect(step1.walletAddresses!.solana).toBe(solanaWalletAddress);
}

function assertStep2DataFetching(
  step2: {
    toolsUsed?: string[];
    porfolio?: {
      symbol?: string;
      name?: string;
      chain?: string;
      amount?: number;
      amountUsd?: number;
      currentPrice?: number;
      historicalPrice?: number;
      priceChange?: number;
      priceChangePercent?: number;
    }[];
    fetchingNotes?: string;
  },
  expectedPorfolio: PortfolioChange,
) {
  const expectedTokens = new Map<
    string /*chain*/,
    Map<string /*symbol*/, PortfolioToken>
  >();
  for (const token of expectedPorfolio.tokens) {
    if (!expectedTokens.has(token.chain)) {
      expectedTokens.set(
        token.chain,
        new Map<string /*symbol*/, PortfolioToken>(),
      );
    }
    expectedTokens.get(token.chain)!.set(token.symbol, token);
  }

  expect(step2.toolsUsed).toStrictEqual(['get_historical_portfolio_data']);
  for (const token of step2.porfolio!) {
    const expectedToken = expectedTokens.get(token.chain!)?.get(token.symbol!);
    expect(expectedToken).toBeDefined();
    expect(expectedToken!.symbol).toBe(token.symbol);
    expect(expectedToken!.name).toBe(token.name);
    expect(expectedToken!.chain).toBe(token.chain);
    expect(expectedToken!.amount).toBeCloseTo(token.amount!, 10e-6);
    expect(expectedToken!.amountUsd).toBeCloseTo(token.amountUsd!, 10e-6);
    expect(expectedToken!.currentPrice).toBeCloseTo(token.currentPrice!, 10e-6);
    expect(expectedToken!.startPeriodPrice).toBeCloseTo(
      token.historicalPrice!,
      10e-6,
    );
    expect(expectedToken!.priceChange).toBeCloseTo(token.priceChange!, 10e-6);
    expect(expectedToken!.priceChangePercent).toBeCloseTo(
      token.priceChangePercent!,
      10e-6,
    );
  }
}

function assertStep3CompositionAnalysis(
  step3: {
    totalAmountUsd?: number;
    topHoldings?: string[];
    topGainers?: {
      coingeckoId?: string;
      symbol?: string;
      name?: string;
      currentPrice?: number;
      priceChange?: number;
    }[];
    topLosers?: {
      coingeckoId?: string;
      symbol?: string;
      name?: string;
      currentPrice?: number;
      priceChange?: number;
    }[];
    compositionSummary?: string;
  },
  expectedPorfolio: PortfolioChange,
) {
  expect(step3.totalAmountUsd).toBeCloseTo(
    expectedPorfolio.totalAmountUsd,
    10e-6,
  );

  const sortedTokens = expectedPorfolio.tokens.sort(
    (a, b) => b.amountUsd - a.amountUsd,
  );
  expect(step3.topHoldings).toStrictEqual(
    sortedTokens.slice(0, step3.topHoldings!.length).map((t) => t.symbol),
  );

  expect(step3.topGainers).toStrictEqual(expectedPorfolio.topGainers);
  expect(step3.topLosers).toStrictEqual(expectedPorfolio.topLosers);
}

function assertStep4PerformanceAnalysis(
  step4: {
    periodStartValue?: number;
    periodEndValue?: number;
    totalDeltaUSD?: number;
    totalDeltaPercentage?: number;
    tokensOrderedByPerformance?: string[];
    performanceSummary?: string;
  },
  expectedPorfolio: PortfolioChange,
) {
  expect(step4.periodStartValue).toBeCloseTo(
    expectedPorfolio.startPeriodTotalAmountUsd,
    10e-6,
  );
  expect(step4.periodEndValue).toBeCloseTo(
    expectedPorfolio.totalAmountUsd,
    10e-6,
  );
  expect(step4.totalDeltaUSD).toBeCloseTo(
    expectedPorfolio.totalAmountChange,
    10e-6,
  );
  expect(step4.totalDeltaPercentage).toBeCloseTo(
    expectedPorfolio.totalAmountChangePercent,
    10e-6,
  );

  expect(step4.tokensOrderedByPerformance).toStrictEqual(
    expectedPorfolio.tokensOrderedByPerformance,
  );
}

function assertStep5Error(
  step5: {
    error?: 'tool_error' | 'llm_error' | 'user_error' | 'no_error';
  },
  expectedError: 'tool_error' | 'llm_error' | 'user_error' | 'no_error',
) {
  expect(step5.error).toBe(expectedError);
}

function assertToolCall(
  msgs: AIMessage[],
  expectedTimeframe: 'unknown' | 'daily' | 'weekly' | 'monthly',
) {
  expect(msgs).toHaveLength(1);
  const msg = msgs[0];
  expect(msg.tool_calls!.length).toBe(1);
  expect(msg.tool_calls![0].name).toBe('get_historical_portfolio_data');
  expect(msg.tool_calls![0].args).toHaveProperty(
    'evmWalletAddress',
    evmWalletAddress,
  );
  expect(msg.tool_calls![0].args).toHaveProperty(
    'solanaWalletAddress',
    solanaWalletAddress,
  );
  expect(msg.tool_calls![0].args).toHaveProperty(
    'timeframe',
    expectedTimeframe,
  );
}

describe('Portfolio agent', () => {
  let model: ChatOpenAI;
  let dailyPorfolioData: PortfolioChange;
  let tools: DynamicStructuredTool[];

  beforeAll(() => {
    model = new ChatOpenAI({
      modelName: 'gpt-4o-mini',
      temperature: 0,
      apiKey: process.env.OPENAI_API_KEY,
    });
    dailyPorfolioData = createPorfolioData('daily');
    tools = createTools(dailyPorfolioData);
  });

  // Assert if setTimeout was called properly
  it('should fill the fields correctly', async () => {
    const userQuery = 'Give me a daily report';
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: formatUserPrompt(userQuery) },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    const messagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );

    // Check tool calls
    assertToolCall(messagesWithToolCalls, 'daily');

    // Check agent result
    assertStep1RequestParsing(
      response.structuredResponse.step1_requestParsing,
      userQuery,
      'daily',
    );

    assertStep2DataFetching(
      response.structuredResponse.step2_dataFetching,
      dailyPorfolioData,
    );

    assertStep3CompositionAnalysis(
      response.structuredResponse.step3_compositionAnalysis,
      dailyPorfolioData,
    );
    assertStep4PerformanceAnalysis(
      response.structuredResponse.step4_performanceAnalysis,
      dailyPorfolioData,
    );
    assertStep5Error(
      response.structuredResponse.step5_reportGeneration,
      'no_error',
    );
  });

  it('should use monthly timeframe if no timeframe is specified', async () => {
    const userQuery = 'Give me a report';
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: formatUserPrompt(userQuery) },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    const monthlyPorfolioData = createPorfolioData('monthly');
    const messagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );

    // Check tool calls
    assertToolCall(messagesWithToolCalls, 'unknown');

    // Check agent result
    assertStep1RequestParsing(
      response.structuredResponse.step1_requestParsing,
      userQuery,
      'unknown',
    );
    assertStep2DataFetching(
      response.structuredResponse.step2_dataFetching,
      monthlyPorfolioData,
    );
    assertStep3CompositionAnalysis(
      response.structuredResponse.step3_compositionAnalysis,
      monthlyPorfolioData,
    );
    assertStep4PerformanceAnalysis(
      response.structuredResponse.step4_performanceAnalysis,
      monthlyPorfolioData,
    );
    assertStep5Error(
      response.structuredResponse.step5_reportGeneration,
      'no_error',
    );
  });

  it('should return the error if the question is not related to portfolio analysis', async () => {
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: 'What is the weather in Tokyo?' },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    // Check agent result
    assertStep5Error(
      response.structuredResponse.step5_reportGeneration,
      'user_error',
    );
  });
});
