import dotenv from 'dotenv';
import { runCoinGeckoAgent } from './agent';

// Load environment variables from .env file
dotenv.config();

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
    const responses = await runCoinGeckoAgent(questions);
    console.log(`\nResults: `);
    for (let i = 0; i < responses.length; i++) {
      console.log(
        `[${i + 1}/${responses.length}] Question: ${responses[i].question}`,
      );
      console.log(
        `[${i + 1}/${responses.length}] Response: ${JSON.stringify(responses[i].response.structuredResponse, null, 2)}`,
      );
    }
  } catch (error) {
    console.error('Error running CoinGecko agent:', error);
  }
}

main();
