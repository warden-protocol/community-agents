# Weather Agent Examples

This document provides detailed examples of how to use the Weather Agent with various scenarios and configurations.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Weather Forecasts](#weather-forecasts)
3. [Travel Planning](#travel-planning)
4. [Custom Prompts](#custom-prompts)
5. [Direct API Usage](#direct-api-usage)

---

## Basic Usage

The simplest way to use the Weather Agent is to ask for current weather conditions.

### Running the Example

```bash
cd agents/weather-agent
tsx examples/basic-usage.ts
```

### Example Questions

```typescript
const questions = [
  'What is the current weather in London?',
  'What is the temperature in Tokyo?',
  'Is it raining in Seattle?',
  'What is the weather like in Sydney?',
];
```

### Expected Output

The agent will provide structured responses with:
- Current temperature (°C and °F)
- Weather conditions (sunny, cloudy, rainy, etc.)
- Humidity and wind information
- UV index
- Helpful recommendations

**Example Response:**

```json
{
  "answer": "The current weather in London is partly cloudy with a temperature of 15°C (59°F). The humidity is at 72% with light winds from the southwest at 15 km/h. The UV index is moderate at 4. It's a pleasant day - perfect for a walk in the park, though you might want to bring a light jacket.",
  "location": "London, United Kingdom",
  "summary": "Partly cloudy, 15°C",
  "recommendations": [
    "Light jacket recommended",
    "Good day for outdoor activities",
    "Moderate UV - consider sunscreen"
  ],
  "data_source": "current weather"
}
```

---

## Weather Forecasts

Get multi-day weather forecasts to plan ahead.

### Running the Example

```bash
tsx examples/forecast-example.ts
```

### Example Questions

```typescript
const questions = [
  'Give me a 3-day weather forecast for Paris',
  'What will the weather be like in New York over the next 5 days?',
  'Will it rain in Los Angeles this week?',
  'What is the weather forecast for Berlin for the next 3 days?',
];
```

### Expected Output

The agent provides detailed forecasts including:
- Daily temperature ranges (min/max)
- Expected conditions for each day
- Precipitation chances
- Sunrise/sunset times
- Day-by-day recommendations

**Example Response:**

```json
{
  "answer": "Here's the 3-day forecast for Paris:\n\nDay 1 (2025-11-08): Partly cloudy with temperatures ranging from 12°C to 18°C. Low chance of rain (10%). Sunrise at 7:42 AM, sunset at 5:23 PM.\n\nDay 2 (2025-11-09): Mostly sunny, 10°C to 16°C. Perfect day for sightseeing!\n\nDay 3 (2025-11-10): Cloudy with possible light showers, 11°C to 15°C. 60% chance of rain. Bring an umbrella.",
  "location": "Paris, France",
  "summary": "Mixed conditions over 3 days with possible rain on day 3",
  "recommendations": [
    "Pack layers for varying temperatures",
    "Umbrella needed for day 3",
    "Day 2 is best for outdoor activities"
  ],
  "data_source": "3-day forecast"
}
```

### Notes

- Free API tier supports up to 3-day forecasts
- Paid plans support up to 14-day forecasts
- Forecasts include hourly data (not shown in structured output but used by agent)

---

## Travel Planning

Use the Weather Agent to help plan trips and decide what to pack.

### Running the Example

```bash
tsx examples/travel-planning.ts
```

### Example Questions

```typescript
const questions = [
  'I am planning a trip to Barcelona next week. What should I pack based on the weather?',
  'Is it a good time to visit Iceland? What is the weather like there?',
  'Should I bring an umbrella for my trip to London tomorrow?',
  'What will the weather be like in Dubai over the next 3 days? Is it too hot?',
  'I am going hiking in Denver this weekend. What is the weather forecast?',
];
```

### Expected Output

The agent provides travel-specific advice:
- What to pack (clothing, accessories)
- Activity recommendations
- Safety considerations
- Best times to visit attractions

**Example Response:**

```json
{
  "answer": "For your trip to Barcelona next week, here's what you should pack based on the forecast:\n\nTemperatures will range from 16°C to 22°C (61-72°F) with mostly sunny conditions. Pack:\n- Light layers (t-shirts, light sweaters)\n- One light jacket for evenings\n- Sunglasses and sunscreen (UV index 6-7)\n- Comfortable walking shoes\n- Light rain jacket just in case (20% chance of showers on one day)\n\nIt's excellent weather for sightseeing, beach visits, and outdoor dining!",
  "location": "Barcelona, Spain",
  "summary": "Warm and sunny, ideal travel weather",
  "recommendations": [
    "Pack light layers",
    "Bring sunscreen (high UV)",
    "Perfect for beach and outdoor activities",
    "Evening temperatures mild, light jacket sufficient"
  ],
  "data_source": "7-day forecast"
}
```

---

## Custom Prompts

Customize the agent's behavior with custom system prompts.

### Running the Example

```bash
tsx examples/custom-prompt.ts
```

### Custom Prompt for Outdoor Activities

This example uses a specialized prompt that focuses on outdoor activity recommendations:

```typescript
const customPrompt = `You are a weather assistant specialized in outdoor activity planning.

Your primary goal is to help users decide what outdoor activities are suitable based on current and forecasted weather conditions.

When providing weather information:
1. Always relate the weather to outdoor activities
2. Provide specific recommendations about which activities are suitable
3. Warn about any weather hazards for outdoor activities
4. Suggest the best times of day for activities
5. Be enthusiastic about good weather days

Available tools:
- get_current_weather: Fetches real-time weather data
- get_weather_forecast: Fetches weather forecast for up to 14 days`;
```

### Example Questions

```typescript
const questions = [
  'What outdoor activities can I do in San Francisco today?',
  'Is it good weather for a picnic in Central Park tomorrow?',
  'Can I go surfing in Hawaii this week?',
  'What is the best day for mountain biking in Colorado over the next 3 days?',
];
```

### Expected Output

With the custom prompt, responses are tailored to outdoor activities:

```json
{
  "answer": "San Francisco has fantastic weather for outdoor activities today! At 20°C (68°F) with partly cloudy skies and light winds at 12 km/h, here's what you can do:\n\n🚴‍♂️ GREAT for: Cycling across the Golden Gate Bridge, hiking in the Presidio, beach walks at Ocean Beach\n\n⚠️ GOOD for: Kayaking in the Bay (winds are light), outdoor photography, picnics in Golden Gate Park\n\n🌊 MAYBE: Swimming (water will be cold despite nice air temp)\n\nBest time: 11 AM - 4 PM when it's warmest. Morning fog should clear by 10 AM. UV index is 5, so wear sunscreen!",
  "location": "San Francisco, California",
  "summary": "Perfect conditions for most outdoor activities",
  "recommendations": [
    "Best window: 11 AM - 4 PM",
    "Bring sunscreen (UV 5)",
    "Light layers for fog/sun transition",
    "Great visibility for photography"
  ],
  "data_source": "current weather"
}
```

---

## Direct API Usage

For programmatic use, you can call the agent functions directly:

```typescript
import { runWeatherAgent } from './src/agent';
import { createWeatherTools } from './src/tools';

// Using the main agent function
const results = await runWeatherAgent(
  ['What is the weather in Berlin?'],
  {
    modelName: 'gpt-4o-mini',
    temperature: 0,
  }
);

// Using tools directly (without LLM)
const tools = createWeatherTools(process.env.WEATHER_API_KEY);
const currentWeatherTool = tools[0];
const result = await currentWeatherTool.invoke({
  location: 'Berlin'
});
console.log(result);
```

### Output Format

Each result includes:
- `question`: The original question asked
- `response`: Object containing:
  - `messages`: Full conversation history
  - `structuredResponse`: Structured output matching ResponseSchema

---

## Configuration Options

All examples support these configuration options:

```typescript
await runAgentWithSaveResults(questions, {
  // LLM model to use
  modelName: 'gpt-4o-mini', // or 'gpt-4', 'gpt-3.5-turbo'

  // Temperature for response generation (0-1)
  temperature: 0, // 0 = deterministic, 1 = creative

  // Custom system prompt
  systemPrompt: 'Your custom prompt here',

  // Custom response schema (Zod schema)
  responseSchema: CustomSchema,

  // Delay between questions (milliseconds)
  delayBetweenQuestionsMs: 1000,
});
```

---

## Tips and Best Practices

### Location Formats

WeatherAPI accepts multiple location formats:
- **City name**: `"London"`, `"New York"`
- **City + Country**: `"Paris, France"`
- **US Zipcode**: `"10001"`
- **UK Postcode**: `"SW1"`
- **Coordinates**: `"48.8567,2.3508"` (latitude,longitude)
- **IP address**: `"auto:ip"` (auto-detect from IP)

### Rate Limiting

To avoid hitting API rate limits:
```typescript
delayBetweenQuestionsMs: 1000 // Add 1 second delay
```

### Error Handling

The agent gracefully handles errors:
- Invalid locations return helpful error messages
- API failures are logged and returned in results
- Network issues are caught and reported

### Output Files

Results are saved to `outputs/` directory:
```
outputs/
└── 1699372800000-gpt-4o-mini.json
```

Filename format: `{timestamp}-{model}.json`

---

## Advanced Usage

### Comparing Weather Across Cities

```typescript
const questions = [
  'Compare the weather in London and Paris today',
  'Which city has better weather: Tokyo or Seoul?',
  'Is it warmer in Miami or Los Angeles right now?',
];
```

### Weather-Based Decisions

```typescript
const questions = [
  'Should I schedule an outdoor wedding in Rome on June 15th?',
  'Is tomorrow a good day for painting the exterior of my house in Seattle?',
  'Can I safely fly a drone in Chicago today?',
];
```

### Historical Context (requires forecast data)

```typescript
const questions = [
  'How does today\'s weather in Boston compare to the forecast?',
  'Is the weather in Singapore typical for this time of year?',
];
```

---

## Troubleshooting Examples

If you encounter issues, try these debug examples:

### Test API Key

```typescript
import { createWeatherTools } from './src/tools';

const tools = createWeatherTools(process.env.WEATHER_API_KEY);
const result = await tools[0].invoke({ location: 'London' });
console.log('API test result:', result);
```

### Verbose Logging

The Logger class outputs helpful information. Check console for:
```
[WeatherAgent] INFO: Starting...
[WeatherAPI] INFO: Fetching current weather for: London
[WeatherAgent] INFO: [1/1] New question to answer: 'What is the weather in London?'
```

---

## Next Steps

- Modify the examples to test different locations
- Create custom system prompts for specialized use cases
- Integrate the agent into your applications
- Extend with additional weather data sources

For more information, see the main [README.md](README.md).
