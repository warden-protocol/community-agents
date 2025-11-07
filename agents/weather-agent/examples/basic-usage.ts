import dotenv from 'dotenv';
import { runAgentWithSaveResults } from '../src/index';

// Load environment variables
dotenv.config();

/**
 * Basic usage example of the Weather Agent
 * This demonstrates simple weather queries for different cities
 */
async function main(): Promise<void> {
  console.log('🌤️  Basic Weather Agent Usage Example\n');

  const questions = [
    'What is the current weather in London?',
    'What is the temperature in Tokyo?',
    'Is it raining in Seattle?',
    'What is the weather like in Sydney?',
  ];

  // Get configuration from environment or use defaults
  const modelName = process.env.MODEL_NAME || 'gpt-4o-mini';
  const temperature = process.env.TEMPERATURE
    ? parseFloat(process.env.TEMPERATURE)
    : 0;

  try {
    await runAgentWithSaveResults(questions, {
      modelName,
      temperature,
      delayBetweenQuestionsMs: 1000, // 1 second delay between questions
    });
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
