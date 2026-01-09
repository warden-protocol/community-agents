import { ChatOpenAI } from '@langchain/openai';
import { createReactAgent } from '@langchain/langgraph/prebuilt';
import zod from 'zod';
import { AgentResponse, Logger } from '../common';
import { SystemPrompt } from './system-prompt';
import { ResponseSchema } from './output-structure';
import { getHyperliquidTools } from './tools';

export interface AgentOptions {
  modelName?: string;
  temperature?: number;
  systemPrompt?: string;
  responseSchema?: zod.Schema;
  delayBetweenQuestionsMs?: number;
}

const DEFAULT_OPTIONS: Required<AgentOptions> = {
  modelName: 'gpt-4o-mini',
  temperature: 0,
  systemPrompt: SystemPrompt,
  responseSchema: ResponseSchema,
  delayBetweenQuestionsMs: 500,
};

/**
 * Create the Hyperliquid agent with configured LLM and tools
 */
function createAgent(options: Required<AgentOptions>) {
  const model = new ChatOpenAI({
    modelName: options.modelName,
    temperature: options.temperature,
  });

  return createReactAgent({
    llm: model,
    tools: getHyperliquidTools(),
    responseFormat: options.responseSchema as any,
  });
}

/**
 * Process a single question through the agent
 */
async function processQuestion(
  agent: ReturnType<typeof createReactAgent>,
  question: string,
  systemPrompt: string,
): Promise<AgentResponse> {
  const response = await agent.invoke({
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: question },
    ],
  });

  return { question, response };
}

/**
 * Run the Hyperliquid funding rate agent with a list of questions
 */
export async function runHyperliquidAgent(
  questions: string[],
  options: AgentOptions = {},
): Promise<AgentResponse[]> {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const logger = new Logger('HyperliquidAgent');

  logger.info('Starting...');

  const agent = createAgent(config);

  logger.info('Running question processing');

  const results: AgentResponse[] = [];

  for (let i = 0; i < questions.length; i++) {
    const question = questions[i];
    const questionNum = `[${i + 1}/${questions.length}]`;

    logger.info(`${questionNum} New question to answer: '${question}'`);

    try {
      const result = await processQuestion(agent, question, config.systemPrompt);
      results.push(result);
      logger.info(`${questionNum} Question answered successfully`);
    } catch (error) {
      const errorMessage = (error as Error).message;
      logger.error('Agent response error:', errorMessage);
      results.push({
        question,
        response: `ERROR: ${errorMessage}`,
      } as any);
    }

    // Add delay between questions (except for the last one)
    if (i < questions.length - 1 && config.delayBetweenQuestionsMs > 0) {
      logger.info(`${questionNum} Delaying for ${config.delayBetweenQuestionsMs}ms`);
      await new Promise((resolve) => setTimeout(resolve, config.delayBetweenQuestionsMs));
    }
  }

  logger.info('Finished Agent');
  return results;
}

export * from './types';
export * from './api';
export { getHyperliquidTools } from './tools';
