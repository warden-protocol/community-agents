import dotenv from 'dotenv';
import { runHyperliquidAgent } from './agent';
import { writeAgentResult } from './common';
import zod from 'zod';

// Load environment variables from .env file
dotenv.config();

export async function runAgentWithSaveResults(
  questions: string[],
  options: {
    modelName?: string;
    temperature?: number;
    systemPrompt?: string;
    responseSchema?: zod.Schema;
    delayBetweenQuestionsMs?: number;
  } = {},
): Promise<void> {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔬 Running Hyperliquid Funding Rate Agent`);
  console.log(`${'='.repeat(60)}\n`);

  const startTime = Date.now();

  try {
    const results = await runHyperliquidAgent(questions, options);
    writeAgentResult(startTime, options.modelName || 'gpt-4o-mini', results);
    const duration = Date.now() - startTime;
    console.log(`\n✅ Agent completed in ${duration}ms\n`);
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`\n❌ Agent failed after ${duration}ms`);
    throw error;
  }
}

async function main(): Promise<void> {
  const questions = [
    'What is the current funding rate for BTC?',
    'Are there any arbitrage opportunities based on current funding rates?',
  ];

  // 'Show me the funding rate history for BTC over the last 24 hours',
  // 'Which token has the highest funding rate APR right now?',
  // 'Compare the funding rates of ETH and SOL',
  // 'What are the top 5 tokens by funding rate?',
  try {
    await runAgentWithSaveResults(questions);
  } catch (error) {
    console.error('Error running Hyperliquid agent:', error);
  }
}

main();
