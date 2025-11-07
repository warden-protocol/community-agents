import dotenv from 'dotenv';
import { runWeatherAgent } from './agent';
import zod from 'zod';

// Load environment variables from .env file
dotenv.config();

function formatWeatherResponse(result: any, index: number, total: number): void {
  console.log(`\n${'─'.repeat(60)}`);
  console.log(`📍 Question ${index + 1}/${total}: ${result.question}`);
  console.log(`${'─'.repeat(60)}`);

  if (typeof result.response === 'string' && result.response.startsWith('ERROR:')) {
    console.log(`\n❌ ${result.response}\n`);
    return;
  }

  // LangGraph response structure: check for structured response
  let structuredResponse: any;

  // First check if there's a direct structuredResponse field
  if (result.response?.structuredResponse) {
    structuredResponse = result.response.structuredResponse;
  } else if (result.response?.messages) {
    // Fall back to checking messages array for the final AI message
    const messages = result.response.messages;
    const lastMessage = messages[messages.length - 1];

    // Check for structured output in additional_kwargs or parsed content
    if (lastMessage?.additional_kwargs?.parsed) {
      structuredResponse = lastMessage.additional_kwargs.parsed;
    } else if (lastMessage?.content && typeof lastMessage.content === 'object') {
      structuredResponse = lastMessage.content;
    } else if (lastMessage?.kwargs?.additional_kwargs?.parsed) {
      structuredResponse = lastMessage.kwargs.additional_kwargs.parsed;
    }
  }

  if (structuredResponse) {
    // Display location and summary prominently
    console.log(`\n📌 ${structuredResponse.location || 'Unknown Location'}`);
    console.log(`☁️  ${structuredResponse.summary || 'N/A'}`);

    // Display the main answer
    console.log(`\n${structuredResponse.answer}`);

    // Display recommendations if available
    if (structuredResponse.recommendations && structuredResponse.recommendations.length > 0) {
      console.log(`\n💡 Recommendations:`);
      structuredResponse.recommendations.forEach((rec: string, i: number) => {
        console.log(`   ${i + 1}. ${rec}`);
      });
    }

    // Display data source
    if (structuredResponse.data_source) {
      console.log(`\n📊 Data source: ${structuredResponse.data_source}`);
    }
  } else {
    console.log('\n⚠️  No structured response available');
    console.log('Raw response structure:', JSON.stringify(result.response, null, 2).substring(0, 500));
  }
}

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
  console.log(`🌤️  Running Weather Agent`);
  console.log(`${'='.repeat(60)}\n`);

  const startTime = Date.now();

  try {
    const results = await runWeatherAgent(questions, options);

    // Display results
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`📋 WEATHER RESULTS`);
    console.log(`${'═'.repeat(60)}`);

    results.forEach((result, index) => {
      formatWeatherResponse(result, index, results.length);
    });

    const duration = Date.now() - startTime;
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`✅ Agent completed in ${duration}ms`);
    console.log(`${'═'.repeat(60)}\n`);
  } catch (error) {
    const duration = Date.now() - startTime;
    console.error(`\n❌ Agent failed after ${duration}ms`);
    throw error;
  }
}

async function main(): Promise<void> {
  const questions = [
    'What is the current weather in London?',
    // 'What will the weather be like in New York over the next 3 days?',
    // 'Should I bring an umbrella in Paris today?',
    // 'What is the temperature in Tokyo right now?',
    // 'Give me a 5-day weather forecast for San Francisco',
    // 'Is it a good day for outdoor activities in Sydney?',
  ];

  // Get model configuration from environment variables
  const modelName = process.env.MODEL_NAME || 'gpt-4o-mini';
  const temperature = process.env.TEMPERATURE
    ? parseFloat(process.env.TEMPERATURE)
    : 0;

  console.log(`Using model: ${modelName}`);
  console.log(`Temperature: ${temperature}\n`);

  try {
    await runAgentWithSaveResults(questions, {
      modelName,
      temperature,
    });
  } catch (error) {
    console.error('Error running Weather agent:', error);
  }
}

main();
