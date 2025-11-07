# Weather Agent - Your First LangGraph Agent

A beginner-friendly agent that shows you how to build AI agents using **LangGraph** and **TypeScript**. This agent fetches real-time weather data and provides helpful recommendations.

> **New to AI agents?** This project is designed as a learning resource. The code is simple, well-commented, and easy to understand!

## What Does This Agent Do?

Ask questions like:
- "What's the weather in London?"
- "Give me a 5-day forecast for New York"
- "Should I bring an umbrella in Paris?"

The agent will:
1. ✅ Understand your question
2. ✅ Fetch real weather data from WeatherAPI
3. ✅ Give you friendly answers with recommendations

## Quick Start (2 minutes)

### Step 1: Get Your API Keys

You need two free API keys:

**1. WeatherAPI** (for weather data)
- Sign up: https://www.weatherapi.com/signup.aspx
- Copy your API key from the dashboard

**2. OpenAI** (for the AI brain)
- Sign up: https://platform.openai.com/
- Create an API key in your account settings

### Step 2: Install and Configure

```bash
# Navigate to the weather-agent directory
cd agents/weather-agent

# Install dependencies
yarn install

# Create your environment file
cp .env.example .env
```

Now edit the `.env` file and add your API keys. The file looks like this:

```bash
# ============================================
# REQUIRED: API Keys
# ============================================

# WeatherAPI Key
WEATHER_API_KEY=your_weather_api_key_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# ============================================
# OPTIONAL: Model Configuration (already set to good defaults)
# ============================================

MODEL_NAME=gpt-4o-mini
TEMPERATURE=0
```

**Just replace the two API keys** with your actual keys. The other settings have good defaults already!

### Step 3: Run the Agent

```bash
# Run the agent in your terminal
yarn start
```

You'll see the agent answer weather questions!

## How to Use the Interactive UI

Want to chat with your agent in a nice web interface? Use **LangSmith Studio**:

```bash
# Start the development server
yarn dev
```

Then open your browser to:
- **LangSmith Studio**: https://smith.langchain.com/studio?baseUrl=http://localhost:2024

In the Studio, you can:
- Chat with the agent in real-time
- See how it thinks and makes decisions
- Watch it call the weather API
- Debug any issues

## Understanding the Code

### The Main File: `src/graph.ts`

This file contains the entire agent in **7 simple steps**:

```typescript
// Step 1: Define the state (conversation memory)
// Step 2: Create weather tools (API connections)
// Step 3: Create the agent node (AI brain)
// Step 4: Create the tools node (executes API calls)
// Step 5: Create routing (decides what to do next)
// Step 6: Build the graph (connect everything)
// Step 7: Compile (make it ready to run)
```

#### What is a "Graph"?

Think of the agent as a flowchart:
1. User asks a question → **Agent** thinks about it
2. Agent needs weather data? → Call **Tools** to get it
3. Got the data? → Go back to **Agent** to answer
4. Answer ready? → **End**

This flowchart is called a "graph" in LangGraph!

### The Weather Tools

The agent has two tools (like apps on your phone):

**Tool 1: `get_current_weather`**
- Gets current weather for a location
- Returns: temperature, conditions, humidity, wind

**Tool 2: `get_forecast`**
- Gets weather forecast (1-14 days)
- Returns: daily high/low temps, rain chance, conditions

### How the Agent Thinks

1. **User**: "What's the weather in Paris?"
2. **Agent** (thinking): "I need to call get_current_weather for Paris"
3. **Tools Node**: *Calls WeatherAPI*
4. **Agent**: "Got the data! Let me write a nice response with recommendations"
5. **User**: Gets friendly answer like:
   > "It's 15°C and sunny in Paris! Perfect weather for sightseeing. Don't forget your sunglasses!"

## Project Structure

```
weather-agent/
├── src/
│   └── graph.ts           # Main agent code (the whole agent in one file!)
├── .env                   # Your API keys (you create this)
├── .env.example          # Template for .env
├── package.json          # Dependencies
└── README.md            # This file
```

Simple, right? One main file to understand!

## Configuration Options

Edit your `.env` file to change settings:

```bash
# Required
WEATHER_API_KEY=your_key
OPENAI_API_KEY=your_key

# Optional: Choose different AI models
MODEL_NAME=gpt-4o-mini     # Fast and cheap (default)
# MODEL_NAME=gpt-4o        # Smarter but costs more
# MODEL_NAME=gpt-3.5-turbo # Cheaper alternative

# Optional: Creativity level (0 = consistent, 1 = creative)
TEMPERATURE=0

# Optional: For LangSmith tracing
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=weather-agent
LANGSMITH_TRACING=true
```

## Common Questions

### Can I use a different AI model?

Yes! Just change `MODEL_NAME` in your `.env` file:
- `gpt-4o-mini` - Default, fast, cheap ($0.15 per 1M tokens)
- `gpt-4o` - Smarter ($2.50 per 1M tokens)
- `gpt-3.5-turbo` - Budget option ($0.50 per 1M tokens)

### How much does it cost to run?

With the free tiers:
- **WeatherAPI**: 1 million calls/month for free
- **OpenAI**: You pay per request (around $0.0001 per weather question with gpt-4o-mini)

A typical weather question costs less than **1 cent**!

### Can I customize the responses?

Yes! Open [src/graph.ts](src/graph.ts:95-103) and edit the system prompt to change how the agent talks.

### Where does the weather data come from?

[WeatherAPI.com](https://www.weatherapi.com/) - a free weather data service. The free tier gives you:
- Current weather for any location
- 3-day forecasts
- 1 million API calls per month

### What locations can I ask about?

Almost anything:
- City names: "London", "New York", "Tokyo"
- Zip codes: "10001", "SW1"
- Coordinates: "48.8567,2.3508"
- Even: "auto:ip" (your current location)

## Troubleshooting

**"WEATHER_API_KEY is required" error**
- Make sure your `.env` file exists in the `weather-agent` directory
- Check that you copied the API key correctly (no spaces or quotes)

**"Rate limit exceeded"**
- You've used up your free API calls
- Wait until next month or upgrade your WeatherAPI plan

**Agent gives weird responses**
- Try lowering the `TEMPERATURE` in `.env` (set it to 0)
- Make sure you're using a good model like `gpt-4o-mini`

**"Cannot find module" errors**
- Run `yarn install` again
- Make sure you're in the `weather-agent` directory

## Next Steps

### Learn More About LangGraph

- **Official Docs**: https://langchain-ai.github.io/langgraph/
- **Tutorials**: https://docs.langchain.com/oss/javascript/langgraph/quickstart
- **Thinking in LangGraph**: https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph

### Customize Your Agent

1. **Add More Tools**: Create tools for other APIs (news, stocks, etc.)
2. **Change Personality**: Edit the system prompt to make it funny, serious, or professional
3. **Add Memory**: Make it remember previous conversations
4. **Deploy It**: Put it online so anyone can use it

### Build Your Own Agent

Use this weather agent as a template! The pattern is:
1. Define your state (what to remember)
2. Create tools (what the agent can do)
3. Build the graph (how it flows)
4. Compile and run!

## Help and Support

- **Questions?** Open an issue on GitHub
- **Found a bug?** Submit a pull request
- **Want to learn more?** Check the LangGraph documentation

## Contributing

This is a learning project! Contributions that make it easier to understand are especially welcome:
- Better comments
- More examples
- Clearer explanations
- Bug fixes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Happy learning! 🚀**

Built with ❤️ using [LangGraph](https://github.com/langchain-ai/langgraph) and [WeatherAPI](https://www.weatherapi.com/)
