/**
 * Main agent orchestration
 * Creates and runs the yield optimization agent
 */

import { ChatOpenAI } from "@langchain/openai";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import zod from "zod";
import { AgentResponse, Logger } from "../common";
import { retryOnRateLimit } from "../common/utils";
import { SystemPrompt } from "./system-prompt";
import { ResponseSchema, ensureSafetyWarning } from "./output-structure";
import { getYieldAgentTools } from "./tools";

export interface AgentOptions {
  modelName?: string;
  temperature?: number;
  systemPrompt?: string;
  responseSchema?: zod.Schema;
  delayBetweenQuestionsMs?: number;
  maxTokens?: number;
  maxRetries?: number;
}

const DEFAULT_OPTIONS: Required<AgentOptions> = {
  modelName: "gpt-4o-mini",
  temperature: 0,
  systemPrompt: SystemPrompt,
  responseSchema: ResponseSchema,
  delayBetweenQuestionsMs: 2000, // Increased from 500ms to 2s to avoid rate limits
  maxTokens: 4000, // Increased to handle longer responses (was 2000)
  maxRetries: 3,
};

/**
 * Create the yield optimization agent with configured LLM and tools
 */
function createAgent(
  options: Required<AgentOptions>
): ReturnType<typeof createReactAgent> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY environment variable is required");
  }

  const model = new ChatOpenAI({
    modelName: options.modelName,
    temperature: options.temperature,
    apiKey: apiKey,
    maxTokens: options.maxTokens,
    maxRetries: options.maxRetries,
    timeout: 60000, // 60 second timeout
  });

  return createReactAgent({
    llm: model,
    tools: getYieldAgentTools(),
    responseFormat: options.responseSchema as any,
  });
}

/**
 * Process a single question through the agent with retry logic for rate limits
 */
async function processQuestion(
  agent: ReturnType<typeof createReactAgent>,
  question: string,
  systemPrompt: string,
  maxRetries: number = 3,
  logger?: Logger
): Promise<AgentResponse> {
  // Retry logic specifically for 429 rate limit errors
  const response = await retryOnRateLimit(
    async () => {
      return await agent.invoke({
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: question },
        ],
      });
    },
    maxRetries,
    2000, // Start with 2 second delay, exponential backoff
    logger
  );

  // Ensure safety warnings are included
  if (response && typeof response === "object" && "response" in response) {
    const responseData = response.response as any;
    if (responseData && typeof responseData === "object") {
      ensureSafetyWarning(responseData);
    }
  }

  return { question, response };
}

/**
 * Run the yield optimization agent with a list of questions
 */
export async function runYieldAgent(
  questions: string[],
  options: AgentOptions = {}
): Promise<AgentResponse[]> {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const logger = new Logger("YieldAgent");

  logger.info("Starting Yield Optimization Agent...");

  // Validate environment variables
  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY environment variable is required");
  }

  // Log API key status (without exposing the full key)
  const apiKey = process.env.OPENAI_API_KEY;
  logger.info(
    `OpenAI API Key loaded: ${apiKey.substring(0, 7)}...${apiKey.substring(apiKey.length - 4)}`
  );

  if (!process.env.ENSO_API_KEY) {
    logger.warn("ENSO_API_KEY not set - Enso SDK features will not work");
  }

  const agent = createAgent(config);

  logger.info("Running question processing");

  const results: AgentResponse[] = [];

  for (let i = 0; i < questions.length; i++) {
    const question = questions[i];
    const questionNum = `[${i + 1}/${questions.length}]`;

    logger.info(`${questionNum} New question to answer: '${question}'`);

    try {
      const result = await processQuestion(
        agent,
        question,
        config.systemPrompt,
        config.maxRetries,
        logger
      );
      logger.info("Result:", result);
      results.push(result);
      logger.info(`${questionNum} Question answered successfully`);
    } catch (error) {
      const errorMessage = (error as Error).message;
      logger.error("Agent response error:", errorMessage);

      // Provide more helpful error message
      let userFriendlyError = errorMessage;
      if (
        errorMessage.includes("exceeded your current quota") ||
        errorMessage.includes("check your plan and billing")
      ) {
        userFriendlyError =
          "Quota/Billing Issue: Your OpenAI account has exceeded its quota or has billing issues. Please check:\n" +
          "1. https://platform.openai.com/account/billing - Verify you have available credits\n" +
          "2. Ensure a payment method is added if required\n" +
          "3. Check if the API key belongs to the correct account/project\n" +
          "4. Verify your account has spending limits configured correctly";
      } else if (
        errorMessage.includes("429") ||
        errorMessage.includes("rate limit")
      ) {
        userFriendlyError =
          "Rate limit exceeded. Please wait a few minutes and try again.";
      }

      results.push({
        question,
        response: {
          answer: `ERROR: ${userFriendlyError}`,
          step: "error",
          mode: "interactive",
          confidence: "low",
          validationErrors: [errorMessage],
        },
      } as any);
    }

    // Add delay between questions (except for the last one)
    if (i < questions.length - 1 && config.delayBetweenQuestionsMs > 0) {
      logger.info(
        `${questionNum} Delaying for ${config.delayBetweenQuestionsMs}ms`
      );
      await new Promise((resolve) =>
        setTimeout(resolve, config.delayBetweenQuestionsMs)
      );
    }
  }

  logger.info("Finished Agent");
  return results;
}

export * from "./types";
export {
  searchToken,
  getTokenByAddress,
  getTokenInfo,
  getTokenPrice,
} from "./api";
export {
  initializeEnsoClient,
  discoverProtocols,
  discoverProtocolsMultiChain,
  checkApprovalNeeded,
  generateTransactionBundle,
  getTokenPrice as getTokenPriceFromEnso,
} from "./enso-service";
export * from "./safety-service";
export * from "./validation";
export { getYieldAgentTools } from "./tools";
