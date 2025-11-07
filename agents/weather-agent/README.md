# Weather Agent

A TypeScript-based LangGraph agent that connects to WeatherAPI to fetch current weather and forecasts for user-specified locations.

## Features

- 🌡️ Get current weather conditions for any location worldwide
- 📅 Fetch weather forecasts for up to 14 days (3 days with free API key)
- 🌍 Support for multiple location formats (city name, zipcode, coordinates, etc.)
- 🤖 Natural language interaction using LangGraph and OpenAI
- 📊 Structured output with recommendations and summaries
- 🛠️ Built with LangChain tools for extensibility

## Prerequisites

- Node.js 20+
- Yarn package manager
- WeatherAPI key (free tier available)
- OpenAI API key

## Setup

### 1. Get API Keys

**WeatherAPI:**
1. Sign up for a free account at [WeatherAPI](https://www.weatherapi.com/signup.aspx)
2. Get your API key from the dashboard

**OpenAI:**
1. Sign up at [OpenAI Platform](https://platform.openai.com/)
2. Create an API key from your account settings

### 2. Install Dependencies

```bash
cd agents/weather-agent
yarn install
```

### 3. Configure Environment Variables

Create a `.env` file in the `weather-agent` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Required: API Keys
WEATHER_API_KEY=your_weather_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Model Configuration
MODEL_NAME=gpt-4o-mini        # Options: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
TEMPERATURE=0                  # Range: 0-1 (0=deterministic, 1=creative)
```

**Configuration Options:**
- `WEATHER_API_KEY` (required): Your WeatherAPI key
- `OPENAI_API_KEY` (required): Your OpenAI API key
- `MODEL_NAME` (optional): LLM model to use (default: `gpt-4o-mini`)
- `TEMPERATURE` (optional): Response creativity (default: `0`)

## Usage

### Run the Default Example

```bash
yarn start
```

This will run the agent with predefined questions about weather in various cities.

### Build the Project

```bash
yarn build
```

### Run Tests

```bash
yarn test
```

### Lint Code

```bash
yarn lint
```

## Project Structure

```
weather-agent/
├── src/
│   ├── agent/
│   │   ├── index.ts              # Main agent implementation
│   │   ├── system-prompt.ts      # Agent system prompt
│   │   └── output-structure.ts   # Response schema definition
│   ├── common/
│   │   ├── logger.ts             # Logging utility
│   │   ├── types.ts              # TypeScript types
│   │   └── utils.ts              # Utility functions
│   ├── tools/
│   │   ├── weather-api.ts        # WeatherAPI tool integration
│   │   └── index.ts              # Tools export
│   └── index.ts                  # Main entry point
├── examples/                      # Example usage scripts
├── tests/                         # Test files
├── outputs/                       # Agent output results
├── package.json
├── tsconfig.json
└── README.md
```

## How It Works

### 1. Weather Tools

The agent uses two main tools to interact with WeatherAPI:

- **get_current_weather**: Fetches real-time weather data
- **get_weather_forecast**: Fetches weather forecast for 1-14 days

### 2. LangGraph Agent

The agent is built using LangGraph's `createReactAgent`, which:
- Processes user questions in natural language
- Decides which tools to use based on the question
- Calls WeatherAPI tools to fetch data
- Generates structured responses with recommendations

### 3. Response Structure

Each response includes:
- **answer**: Natural language response to the user with all weather details
- **location**: The specific location name (e.g., "London, United Kingdom")
- **summary**: Brief one-line weather summary (e.g., "Partly cloudy, 15°C")
- **recommendations**: Array of 2-4 helpful suggestions based on the weather
- **data_source**: Indication of data used (e.g., "current weather", "3-day forecast")

## API Limits

### Free WeatherAPI Tier
- 1,000,000 calls per month
- 3-day forecast maximum
- Real-time weather data
- Astronomical data

For more extended forecasts (up to 14 days), upgrade to a paid plan.

## Supported Location Formats

WeatherAPI supports multiple location formats:
- City name: `"London"`, `"New York"`
- US zipcode: `"10001"`
- UK postcode: `"SW1"`
- Canada postal code: `"G2J"`
- Coordinates: `"48.8567,2.3508"` (lat,lon)
- IP address: `"auto:ip"` (auto-detect)

## Customization

### Custom Questions

Edit [src/index.ts](src/index.ts) to modify the questions array:

```typescript
const questions = [
  'What is the current weather in Tokyo?',
  'Will it rain in Seattle tomorrow?',
  // Add your questions here
];
```

### Custom System Prompt

Modify [src/agent/system-prompt.ts](src/agent/system-prompt.ts) to change agent behavior.

### Different LLM Models

You can configure the model in your `.env` file or pass it programmatically:

**Via Environment Variable (.env):**
```bash
MODEL_NAME=gpt-4o
TEMPERATURE=0.3
```

**Via Code:**
```typescript
await runAgentWithSaveResults(questions, {
  modelName: 'gpt-4o',
  temperature: 0.7,
});
```

**Model Recommendations:**
- `gpt-4o-mini` (default): Fast, cost-effective, good for most weather queries
- `gpt-4o`: More capable, better for complex questions and reasoning
- `gpt-4-turbo`: Balanced performance and cost
- `gpt-3.5-turbo`: Budget option, suitable for simple queries

## Examples

See the [examples/](examples/) directory for more usage examples:

- Basic weather queries
- Custom prompts and configurations
- Different response formats

## Troubleshooting

### API Key Issues

If you get "WEATHER_API_KEY is required" error:
1. Check that `.env` file exists in the project root
2. Verify the API key is correctly set
3. Make sure there are no extra spaces or quotes

### Rate Limiting

If you hit rate limits:
1. Check your API usage at WeatherAPI dashboard
2. Add delays between requests using `delayBetweenQuestionsMs` option
3. Consider upgrading your API plan

### Location Not Found

If a location isn't recognized:
1. Try different location formats
2. Use coordinates for precise locations
3. Check spelling and location names

## Contributing

Contributions are welcome! Please follow the existing code style and add tests for new features.

## License

This project is part of the community-agents repository.

## Resources

- [WeatherAPI Documentation](https://www.weatherapi.com/docs/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Tools](https://js.langchain.com/docs/modules/agents/tools/)
