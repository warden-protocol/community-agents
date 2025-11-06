import dotenv from 'dotenv';
import { runCoinGeckoAgent } from './agent';
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
  console.log(`🔬 Running CoinGecko Agent`);
  console.log(`${'='.repeat(60)}\n`);

  const startTime = Date.now();

  try {
    const results = await runCoinGeckoAgent(questions, options);
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
    'What is the price of the BTC?',
    'Which token has the highest 24h price change?',
    'What is the price of the eth token at 3 Jan 2025?',
    'What do you think about polkadot?',
    'Which token should I buy: sui or polkadot?',
    'What market cap has the eth?',
    'Compare bitcoin and ethereum',
  ];
  try {
    await runAgentWithSaveResults(questions);
  } catch (error) {
    console.error('Error running CoinGecko agent:', error);
  }
}

main();
