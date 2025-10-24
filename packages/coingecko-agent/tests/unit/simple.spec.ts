import { describe, it, beforeAll, expect } from 'vitest';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import { convertCGToolToDynamicTool } from '../utils/tool-converter';
import getCoinsMarkets from '@coingecko/coingecko-mcp/tools/coins/markets/get-coins-markets';
import getCoinsSearch from '@coingecko/coingecko-mcp/tools/search/get-search';
import { AIMessage, BaseMessage, ToolMessage } from '@langchain/core/messages';
import { ResponseSchema } from '../../src/agent/output-structure';
import { SystemPrompt } from '../../src/agent/system-prompt';

function createTools() {
  const getCoinsMarketToolHandler = async (
    input: Record<string, any>,
  ): Promise<any> => {
    const prices: { name: string; current_price: number }[] = [];
    if (input.ids.includes('bitcoin')) {
      prices.push({
        name: 'BTC',
        current_price: 100_005,
      });
    }
    if (input.ids.includes('ethereum')) {
      prices.push({
        name: 'ETH',
        current_price: 4_001,
      });
    }
    if (input.ids.includes('custom_token_1')) {
      prices.push({
        name: 'CUSTOM1',
        current_price: 1.23,
      });
    }
    return JSON.stringify(prices);
  };
  const getCoinsMarketTool = convertCGToolToDynamicTool(
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
  const getCoinsSearchTool = convertCGToolToDynamicTool(
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

describe('CoinGecko agent', () => {
  let model;

  beforeAll(() => {
    model = new ChatOpenAI({
      modelName: 'gpt-4o-mini',
      temperature: 0,
      apiKey: process.env.OPENAI_API_KEY,
    });
  });

  // Assert if setTimeout was called properly
  it.only('should return the price of the BTC', async () => {
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
    expect(aiMessagesWithToolCalls.length).toBe(2);
    const searchMsg = aiMessagesWithToolCalls[0];
    expect(searchMsg.tool_calls!.length).toBe(1);
    expect(searchMsg.tool_calls![0].name).toBe('get_search');
    expect(Object.keys(searchMsg.tool_calls![0].args)).toContain('query');

    const getMarketMsg = aiMessagesWithToolCalls[1];
    expect(getMarketMsg.tool_calls!.length).toBe(1);
    expect(getMarketMsg.tool_calls![0].name).toBe('get_coins_markets');
    expect(Object.keys(getMarketMsg.tool_calls![0].args)).toContain('ids');
    expect(getMarketMsg.tool_calls![0].args.ids).toBe('bitcoin');
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
    expect(getMarketCallResponse[0]).toHaveProperty('name', 'BTC');
    expect(getMarketCallResponse[0]).toHaveProperty('current_price', 100005);

    // Check agent result
    expect(
      response.structuredResponse.step2_dataFetching.tokensData.length,
    ).toBe(1);
    expect(
      response.structuredResponse.step2_dataFetching.tokensData[0].tokenSymbol,
    ).toBe('BTC');
    expect(
      response.structuredResponse.step2_dataFetching.tokensData[0].currentPrice,
    ).toBe(100_005);
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
    expect(getMarketCallResponse[0]).toHaveProperty('current_price', 1.23);

    // Check agent result
    expect(
      response.structuredResponse.step2_dataFetching.tokensData.length,
    ).toBe(1);
    expect(
      response.structuredResponse.step2_dataFetching.tokensData[0].tokenId,
    ).toBe('custom_token_1');
    expect(
      response.structuredResponse.step2_dataFetching.tokensData[0].tokenSymbol,
    ).toBe('CUSTOM1');
    expect(
      response.structuredResponse.step2_dataFetching.tokensData[0].currentPrice,
    ).toBe(1.23);
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
    expect(response.structuredResponse.step5_confidenceAnswer).toHaveProperty(
      'confidence',
      'low',
    );
  });
});
