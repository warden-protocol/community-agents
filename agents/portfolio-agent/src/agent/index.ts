import { SystemPrompt } from './system-prompt';
import { ResponseSchema } from './output-structure';
import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import zod from 'zod';
import { AgentResponse, Logger } from '../common';
import { getHistoricalPortfolioDataTool } from './tools';

export async function runPortfolioAgent(
  questions: string[],
  walletAddresses: {
    evm?: string;
    solana?: string;
  },
  options: {
    modelName?: string;
    temperature?: number;
    systemPrompt?: string;
    responseSchema?: zod.Schema;
    delayBetweenQuestionsMs?: number;
  } = {},
): Promise<AgentResponse[]> {
  const {
    modelName = 'gpt-4o-mini',
    temperature = 0,
    systemPrompt = SystemPrompt,
    responseSchema = ResponseSchema,
    delayBetweenQuestionsMs = 500,
  } = options;

  const logger = new Logger('PortfolioAgent');
  logger.info('Starting...');
  const model = new ChatOpenAI({
    modelName,
    temperature,
  });

  const customTools = [getHistoricalPortfolioDataTool];

  const agent = createReactAgent({
    llm: model,
    tools: customTools,
    responseFormat: responseSchema as any,
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
            content: systemPrompt,
          },
          {
            role: 'user',
            content: `Wallet addresses: EVM: ${walletAddresses.evm || 'Not provided'}, Solana: ${walletAddresses.solana || 'Not provided'}\n\nUser question: ${question}`,
          },
        ],
      });
      results.push({ question, response });
      logger.info(
        `[${i + 1}/${questions.length}] Question answered successfully`,
      );
      if (i < questions.length - 1 && delayBetweenQuestionsMs > 0) {
        logger.info(
          `[${i + 1}/${questions.length}] Delaying for ${delayBetweenQuestionsMs}ms`,
        );
        await new Promise((resolve) =>
          setTimeout(resolve, delayBetweenQuestionsMs),
        );
      }
    } catch (error) {
      logger.error('Agent response error:', error.message);
      results.push({ question, response: `ERROR: ${error.message}` });
    }
  }

  logger.info('Finished Agent');
  return results;
}
