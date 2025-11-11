import { describe, it, beforeAll, expect } from 'vitest';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { AgentResponse, convertToDynamicTool } from '../../src/common';
import getCoinsMarkets from '@coingecko/coingecko-mcp/tools/coins/markets/get-coins-markets';
import getCoinsSearch from '@coingecko/coingecko-mcp/tools/search/get-search';
import { AIMessage, BaseMessage, ToolMessage } from '@langchain/core/messages';
import { ResponseSchema } from '../../src/agent/output-structure';
import { SystemPrompt } from '../../src/agent/system-prompt';

const BTC_PRICE = 100_005;
const ETH_PRICE = 4_001;
const CUSTOM1_PRICE = 1.23;

interface TokenData {
  tokenId: string;
  tokenSymbol: string;
  tokenName: string;
  currentPrice: number;
  priceChangePercentage24h?: number | null;
  priceChangePercentage7d?: number | null;
  marketCap?: number | null;
  marketCapRank?: number | null;
  tradingVolume24h?: number | null;
  volumeToMarketCapRatio?: number | null;
  highLow24h?: {
    high?: number | null;
    low?: number | null;
  } | null;
  athChangePercentage?: number | null;
  missingDataPoints: string[];
}

function createTools() {
  const getCoinsMarketToolHandler = async (
    input: Record<string, any>,
  ): Promise<any> => {
    const prices: { name: string; current_price: number }[] = [];
    if (input.ids.includes('bitcoin')) {
      prices.push({
        name: 'BTC',
        current_price: BTC_PRICE,
      });
    }
    if (input.ids.includes('ethereum')) {
      prices.push({
        name: 'ETH',
        current_price: ETH_PRICE,
      });
    }
    if (input.ids.includes('custom_token_1')) {
      prices.push({
        name: 'CUSTOM1',
        current_price: CUSTOM1_PRICE,
      });
    }
    return JSON.stringify(prices);
  };
  const getCoinsMarketTool = convertToDynamicTool(
    getCoinsMarkets.tool,
    getCoinsMarketToolHandler,
  );

  const getCoinsSearchToolHandler = async (
    input: Record<string, any>,
  ): Promise<any> => {
    const query = input.query.toLowerCase() as string;
    if (query.includes('custom1')) {
      return JSON.stringify({
        coins: [{ id: 'custom_token_1', symbol: 'CUSTOM1' }],
      });
    }
    if (query.includes('btc') || query.includes('bitcoin')) {
      return JSON.stringify({ coins: [{ id: 'bitcoin', symbol: 'BTC' }] });
    }
    return JSON.stringify({});
  };
  const getCoinsSearchTool = convertToDynamicTool(
    getCoinsSearch.tool,
    getCoinsSearchToolHandler,
  );
  return [getCoinsMarketTool, getCoinsSearchTool];
}

function filterToolResponseMessages(messages: BaseMessage[]): ToolMessage[] {
  return messages.filter(
    (x: BaseMessage) => x.getType() === 'tool',
  ) as ToolMessage[];
}

function filterAIMessagesWithToolCall(messages: BaseMessage[]): AIMessage[] {
  return messages.filter(
    (x: BaseMessage) =>
      x.getType() === 'ai' && ((x as AIMessage).tool_calls?.length ?? 0) > 0,
  ) as AIMessage[];
}

function assertStep0RequestValidation(
  step0_requestValidation: {
    validationReasoning: string;
    requestValid: boolean;
    error: 'no_error' | 'invalid_request_error' | 'investment_advice_error';
  },
  expectedError:
    | 'no_error'
    | 'invalid_request_error'
    | 'investment_advice_error',
) {
  expect(step0_requestValidation.error).toBe(expectedError);
  expect(step0_requestValidation.requestValid).toBe(
    expectedError === 'no_error',
  );
}

function assertStep1TokenExtraction(
  step1_tokenExtraction: {
    tokenCount: number;
    extractedTokens: string[];
  },
  expectedTokens: string[],
) {
  const extractedTokens = new Set(step1_tokenExtraction.extractedTokens);
  expect(extractedTokens.size).toBe(expectedTokens.length);
  for (const token of expectedTokens) {
    expect(extractedTokens.has(token)).toBe(true);
  }
}

function assertStep2DataFetching(
  step2_dataFetching: {
    toolsUsed: string[];
    tokensData: TokenData[];
    fetchingNotes: string;
  },
  expectedPrices: { symbol: string; price: number }[],
) {
  const uniqueTokenSymbols = new Set(
    step2_dataFetching.tokensData.map((token) => token.tokenSymbol),
  );
  expect(uniqueTokenSymbols.size).toBe(step2_dataFetching.tokensData.length);

  for (const { symbol, price } of expectedPrices) {
    const tokenData = step2_dataFetching.tokensData.find(
      (token) => token.tokenSymbol === symbol,
    );
    expect(tokenData).toBeDefined();
    expect(tokenData!.currentPrice).toBe(price);
  }
}

function assertStep4AnalysisHasUnknownLevels(step4_analysis: {
  riskAnalysis: {
    volatilityRisk: {
      reasoning: string;
      level: 'low' | 'medium' | 'high' | 'unknown';
    };
    liquidityRisk: {
      reasoning: string;
      level: 'low' | 'medium' | 'high' | 'unknown';
    };
    marketCapRisk: {
      reasoning: string;
      level: 'low' | 'medium' | 'high' | 'unknown';
    };
    overallRiskAssessment: string;
  };
}) {
  expect(step4_analysis.riskAnalysis.volatilityRisk.level).toBe('unknown');
  expect(step4_analysis.riskAnalysis.liquidityRisk.level).toBe('unknown');
  expect(step4_analysis.riskAnalysis.marketCapRisk.level).toBe('unknown');
}

function assertStep5ConfidenceAnswer(
  step5_confidenceAnswer: {
    confidenceReasoning: string;
    confidence: 'low' | 'medium' | 'high';
    error: 'tool_error' | 'llm_error' | 'user_error' | 'no_error';
    reasoning: string;
    answer: string;
    keyTakeaways: string[];
    caveats: string[];
  },
  expectedError: 'tool_error' | 'llm_error' | 'user_error' | 'no_error',
) {
  expect(step5_confidenceAnswer.error).toBe(expectedError);
}

describe('CoinGecko agent', () => {
  let model: ChatOpenAI;

  beforeAll(() => {
    model = new ChatOpenAI({
      modelName: 'gpt-4o-mini',
      temperature: 0,
      apiKey: process.env.OPENAI_API_KEY,
    });
  });

  // Assert if setTimeout was called properly
  it('should return the price of the BTC', async () => {
    const tools = createTools();
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: 'What is the price of the BTC?' },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    const aiMessagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );
    const toolMessages = filterToolResponseMessages(response.messages);

    // Check tool calls:
    expect(aiMessagesWithToolCalls.length).toBeGreaterThanOrEqual(1);
    expect(aiMessagesWithToolCalls.length).toBeLessThanOrEqual(2);
    if (aiMessagesWithToolCalls.length === 2) {
      const searchMsg = aiMessagesWithToolCalls[0];
      expect(searchMsg.tool_calls!.length).toBe(1);
      expect(searchMsg.tool_calls![0].name).toBe('get_search');
      expect(Object.keys(searchMsg.tool_calls![0].args)).toContain('query');
    }
    const getMarketMsg =
      aiMessagesWithToolCalls[aiMessagesWithToolCalls.length - 1];
    expect(getMarketMsg.tool_calls!.length).toBe(1);
    expect(getMarketMsg.tool_calls![0].name).toBe('get_coins_markets');
    expect(Object.keys(getMarketMsg.tool_calls![0].args)).toContain('ids');
    expect(getMarketMsg.tool_calls![0].args.ids).toBe('bitcoin');
    if (getMarketMsg.tool_calls![0].args['vs_currency'] !== undefined) {
      expect(getMarketMsg.tool_calls![0].args.vs_currency).toBe('usd');
    }

    // Check tool responses:
    expect(toolMessages.length).toBeGreaterThanOrEqual(1);
    expect(toolMessages.length).toBeLessThanOrEqual(2);
    if (toolMessages.length === 2) {
      expect(toolMessages[0].name).toBe('get_search');
    }

    const getMarketToolMessage = toolMessages[toolMessages.length - 1];
    expect(getMarketToolMessage.name).toBe('get_coins_markets');
    const getMarketToolResponse = JSON.parse(
      getMarketToolMessage.content as string,
    ) as Record<string, string | number>[];
    expect(getMarketToolResponse.length).toBe(1);
    expect(getMarketToolResponse[0]).toHaveProperty('name', 'BTC');
    expect(getMarketToolResponse[0]).toHaveProperty('current_price', BTC_PRICE);

    // Check agent result
    assertStep0RequestValidation(
      response.structuredResponse.step0_requestValidation,
      'no_error',
    );
    assertStep1TokenExtraction(
      response.structuredResponse.step1_tokenExtraction,
      ['BTC'],
    );
    assertStep2DataFetching(response.structuredResponse.step2_dataFetching, [
      { symbol: 'BTC', price: BTC_PRICE },
    ]);
    assertStep4AnalysisHasUnknownLevels(
      response.structuredResponse.step4_analysis,
    );
    assertStep5ConfidenceAnswer(
      response.structuredResponse.step5_confidenceAnswer,
      'no_error',
    );
  });

  it('should search unknown token and return correct price', async () => {
    const tools = createTools();
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: 'What is the price of the CUSTOM1 token?' },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    const aiMessagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );
    const toolMessages = filterToolResponseMessages(response.messages);

    // Check tool calls:
    expect(aiMessagesWithToolCalls.length).toBe(2);
    const searchMsg = aiMessagesWithToolCalls[0];
    expect(searchMsg.tool_calls!.length).toBe(1);
    expect(searchMsg.tool_calls![0].name).toBe('get_search');
    expect(Object.keys(searchMsg.tool_calls![0].args)).toContain('query');
    expect(searchMsg.tool_calls![0].args.query).toBe('CUSTOM1');

    const getMarketMsg = aiMessagesWithToolCalls[1];
    expect(getMarketMsg.tool_calls!.length).toBe(1);
    expect(getMarketMsg.tool_calls![0].name).toBe('get_coins_markets');
    expect(Object.keys(getMarketMsg.tool_calls![0].args)).toContain('ids');
    expect(getMarketMsg.tool_calls![0].args.ids).toBe('custom_token_1');
    if (getMarketMsg.tool_calls![0].args['vs_currency'] !== undefined) {
      expect(getMarketMsg.tool_calls![0].args.vs_currency).toBe('usd');
    }

    // Check tool responses:
    expect(toolMessages.length).toBe(2);
    expect(toolMessages[0].name).toBe('get_search');
    expect(toolMessages[1].name).toBe('get_coins_markets');
    const getMarketCallResponse = JSON.parse(
      toolMessages[1].content as string,
    ) as Record<string, string | number>[];
    expect(getMarketCallResponse.length).toBe(1);
    expect(getMarketCallResponse[0]).toHaveProperty('name', 'CUSTOM1');
    expect(getMarketCallResponse[0]).toHaveProperty(
      'current_price',
      CUSTOM1_PRICE,
    );

    // Check agent result
    assertStep0RequestValidation(
      response.structuredResponse.step0_requestValidation,
      'no_error',
    );
    assertStep1TokenExtraction(
      response.structuredResponse.step1_tokenExtraction,
      ['CUSTOM1'],
    );
    assertStep2DataFetching(response.structuredResponse.step2_dataFetching, [
      { symbol: 'CUSTOM1', price: CUSTOM1_PRICE },
    ]);
    assertStep4AnalysisHasUnknownLevels(
      response.structuredResponse.step4_analysis,
    );
    assertStep5ConfidenceAnswer(
      response.structuredResponse.step5_confidenceAnswer,
      'no_error',
    );
  });

  it('should return the error if the token is unknown', async () => {
    const tools = createTools();
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: 'What is the price of the UNKNOWN token?' },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    const aiMessagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );
    const toolMessages = filterToolResponseMessages(response.messages);

    // Check tool calls:
    expect(aiMessagesWithToolCalls.length).toBe(1);
    const searchMsg = aiMessagesWithToolCalls[0];
    expect(searchMsg.tool_calls!.length).toBe(1);
    expect(searchMsg.tool_calls![0].name).toBe('get_search');
    expect(Object.keys(searchMsg.tool_calls![0].args)).toContain('query');
    expect(searchMsg.tool_calls![0].args.query).toBe('UNKNOWN');

    // Check tool responses:
    expect(toolMessages.length).toBe(1);
    expect(toolMessages[0].name).toBe('get_search');

    // Check agent result
    expect(
      ['no_error', 'invalid_request_error'].includes(
        response.structuredResponse.step0_requestValidation.error,
      ),
    ).toBe(true);
    assertStep1TokenExtraction(
      response.structuredResponse.step1_tokenExtraction,
      ['UNKNOWN'],
    );
    assertStep2DataFetching(response.structuredResponse.step2_dataFetching, []);
    assertStep4AnalysisHasUnknownLevels(
      response.structuredResponse.step4_analysis,
    );
    expect(
      ['no_error', 'user_error'].includes(
        response.structuredResponse.step5_confidenceAnswer.error,
      ),
    ).toBe(true);
  });

  it('should return the error if the question is not related to cryptocurrencies', async () => {
    const tools = createTools();
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

    const aiMessagesWithToolCalls = filterAIMessagesWithToolCall(
      response.messages,
    );
    const toolMessages = filterToolResponseMessages(response.messages);

    // Check tool calls:
    expect(aiMessagesWithToolCalls.length).toBe(0);
    expect(toolMessages.length).toBe(0);

    // Check agent result
    assertStep0RequestValidation(
      response.structuredResponse.step0_requestValidation,
      'invalid_request_error',
    );
    assertStep1TokenExtraction(
      response.structuredResponse.step1_tokenExtraction,
      [],
    );
    assertStep2DataFetching(response.structuredResponse.step2_dataFetching, []);
    assertStep4AnalysisHasUnknownLevels(
      response.structuredResponse.step4_analysis,
    );
    assertStep5ConfidenceAnswer(
      response.structuredResponse.step5_confidenceAnswer,
      'user_error',
    );
  });

  it('should enforce a maximum of 2 cryptocurrencies per request', async () => {
    const tools = createTools();
    const agent = createReactAgent({
      llm: model,
      tools,
      responseFormat: ResponseSchema,
    });
    const response = await agent.invoke({
      messages: [
        { role: 'system', content: SystemPrompt },
        { role: 'user', content: 'What is the price of the BTC, ETH and SOL?' },
      ],
    });
    console.log(JSON.stringify(response, null, 2));

    // Check agent result
    assertStep0RequestValidation(
      response.structuredResponse.step0_requestValidation,
      'no_error',
    );
    assertStep1TokenExtraction(
      response.structuredResponse.step1_tokenExtraction,
      ['BTC', 'ETH'],
    );
    assertStep0RequestValidation(
      response.structuredResponse.step0_requestValidation,
      'no_error',
    );
    assertStep2DataFetching(response.structuredResponse.step2_dataFetching, [
      { symbol: 'BTC', price: BTC_PRICE },
      { symbol: 'ETH', price: ETH_PRICE },
    ]);
    assertStep4AnalysisHasUnknownLevels(
      response.structuredResponse.step4_analysis,
    );
    assertStep5ConfidenceAnswer(
      response.structuredResponse.step5_confidenceAnswer,
      'no_error',
    );
  });
});
