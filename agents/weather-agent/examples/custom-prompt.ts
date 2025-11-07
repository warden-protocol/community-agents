import dotenv from 'dotenv';
import { runAgentWithSaveResults } from '../src/index';

// Load environment variables
dotenv.config();

/**
 * Custom prompt example
 * This demonstrates using a custom system prompt to change agent behavior
 */
async function main(): Promise<void> {
  console.log('🎨 Custom Prompt Example\n');

  // Custom system prompt that makes the agent more focused on outdoor activities
  const customPrompt = `You are a weather assistant specialized in outdoor activity planning.

Your primary goal is to help users decide what outdoor activities are suitable based on current and forecasted weather conditions.

When providing weather information:
1. Always relate the weather to outdoor activities (hiking, cycling, beach activities, sports, etc.)
2. Provide specific recommendations about which activities are good or bad given the conditions
3. Warn about any weather hazards for outdoor activities (extreme heat, storms, strong winds, etc.)
4. Suggest the best times of day for outdoor activities based on the forecast
5. Be enthusiastic about good weather days and suggest multiple activity options

Available tools:
- get_current_weather: Fetches real-time weather data
- get_weather_forecast: Fetches weather forecast for up to 14 days

Always use the tools to get accurate weather information.`;

  const questions = [
    'What outdoor activities can I do in San Francisco today?',
    'Is it good weather for a picnic in Central Park tomorrow?',
    'Can I go surfing in Hawaii this week?',
    'What is the best day for mountain biking in Colorado over the next 3 days?',
  ];

  try {
    await runAgentWithSaveResults(questions, {
      modelName: 'gpt-4o-mini',
      temperature: 0.5,
      systemPrompt: customPrompt,
      delayBetweenQuestionsMs: 1000,
    });
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

main();
