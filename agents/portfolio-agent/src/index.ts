import { writeAgentResult } from './common';
import { runPortfolioAgent } from './agent';
import dotenv from 'dotenv';
import zod from 'zod';

// Load environment variables
dotenv.config();

export async function runAgentWithSaveResults(
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
): Promise<void> {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`🔬 Running Portfolio Agent`);
  console.log(`${'='.repeat(60)}\n`);

  const startTime = Date.now();

  try {
    const results = await runPortfolioAgent(
      questions,
      walletAddresses,
      options,
    );
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
  // Example usage of the portfolio agent
  const questions = [
    'Review my portfolio',
    'Give me a daily report',
    'Analyze my portfolio and show which tokens are underperforming',
    'How has my portfolio changed in the last 7 days?',
    'What is my total profit/loss this month?',
    'Which coins in my portfolio had the highest growth this month?',
  ];

  const walletAddresses = {
    evm: '0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6', // Example Ethereum address
    solana: '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM', // Example Solana address
  };

  console.log('Starting Portfolio Agent...');
  console.log('Wallet addresses:', walletAddresses);
  console.log('Questions to analyze:', questions);

  await runAgentWithSaveResults(questions, walletAddresses, {
    modelName: 'gpt-4o-mini',
    temperature: 0,
    delayBetweenQuestionsMs: 1000,
  });
}

main();
