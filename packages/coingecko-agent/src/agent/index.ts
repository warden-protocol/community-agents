import { SystemPrompt } from './system-prompt';
import { ResponseSchema } from './output-structure';
import { MultiServerMCPClient } from '@langchain/mcp-adapters';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import zod from 'zod';
import { Logger } from '@warden-community-agents/common';

export async function runCoinGeckoAgent(
  questions: string[],
  options: {
    modelName: string;
    temperature: number;
    systemPrompt: string;
    responseSchema: zod.Schema;
    delayBetweenQuestionsMs: number;
  } = {
    modelName: 'gpt-4o-mini',
    temperature: 0,
    systemPrompt: SystemPrompt,
    responseSchema: ResponseSchema,
    delayBetweenQuestionsMs: 500,
  },
): Promise<
  { question: string; response: { messages: any[]; structuredResponse: any } }[]
> {
  const logger = new Logger('CoinGeckoAgent');
  logger.info('Starting...');
  const mcpClient = new MultiServerMCPClient({
    mcpServers: {
      'coingecko-mcp': {
        command: 'npx',
        args: ['-y', '@coingecko/coingecko-mcp'],
        env: process.env,
      },
    },
  });
  const model = new ChatOpenAI({
    modelName: options.modelName,
    temperature: options.temperature,
  });

  const agent = createReactAgent({
    llm: model,
    tools: await mcpClient.getTools(),
    responseFormat: options.responseSchema as any,
  });

  logger.info('Running question processing');

  const results = [];
  for (let i = 0; i < questions.length; i++) {
    const question = questions[i];
    logger.info(
      `[${i + 1}/${questions.length}] New question to answer: '${question}'`,
    );
    try {
      const response = await agent.invoke({
        messages: [
          {
            role: 'system',
            content: options.systemPrompt,
          },
          { role: 'user', content: question },
        ],
      });
      results.push({ question, response });
      logger.info(
        `[${i + 1}/${questions.length}] Question answered successfully`,
      );
      if (i < questions.length - 1 && options.delayBetweenQuestionsMs > 0) {
        logger.info(
          `[${i + 1}/${questions.length}] Delaying for ${options.delayBetweenQuestionsMs}ms`,
        );
        await new Promise((resolve) =>
          setTimeout(resolve, options.delayBetweenQuestionsMs),
        );
      }
    } catch (error) {
      logger.error('Agent response error:', error.message);
      results.push({ question, response: `ERROR: ${error.message}` });
    }
  }

  await mcpClient.close();
  logger.info('Finished Agent');
  return results;
}
