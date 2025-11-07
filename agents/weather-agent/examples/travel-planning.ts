import dotenv from 'dotenv';
import { runAgentWithSaveResults } from '../src/index';

// Load environment variables
dotenv.config();

/**
 * Travel planning example
 * This demonstrates using the weather agent for travel planning scenarios
 */
async function main(): Promise<void> {
  console.log('✈️  Travel Planning Weather Example\n');

  const questions = [
    'I am planning a trip to Barcelona next week. What should I pack based on the weather?',
    'Is it a good time to visit Iceland? What is the weather like there?',
    'Should I bring an umbrella for my trip to London tomorrow?',
    'What will the weather be like in Dubai over the next 3 days? Is it too hot?',
    'I am going hiking in Denver this weekend. What is the weather forecast?',
    'What is the best clothing to wear in Singapore based on current weather?',
  ];

  // Get configuration from environment or use defaults
  // Override with slightly higher temperature for more conversational responses
  const modelName = process.env.MODEL_NAME || 'gpt-4o-mini';
  const temperature = 0.3;

  try {
    await runAgentWithSaveResults(questions, {
      modelName,
      temperature,
      delayBetweenQuestionsMs: 1500,
    });
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
