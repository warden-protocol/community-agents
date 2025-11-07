import dotenv from 'dotenv';
import { runAgentWithSaveResults } from '../src/index';

// Load environment variables
dotenv.config();

/**
 * Weather forecast example
 * This demonstrates querying weather forecasts for multiple days
 */
async function main(): Promise<void> {
  console.log('📅 Weather Forecast Example\n');

  const questions = [
    'Give me a 3-day weather forecast for Paris',
    'What will the weather be like in New York over the next 5 days?',
    'Will it rain in Los Angeles this week?',
    'What is the weather forecast for Berlin for the next 3 days?',
    'Should I plan outdoor activities in Miami for the weekend?',
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
      delayBetweenQuestionsMs: 1000,
    });
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
