import { StateGraph, Annotation, messagesStateReducer, MemorySaver } from '@langchain/langgraph';
import { BaseMessage, AIMessage, ToolMessage } from '@langchain/core/messages';
import { ChatOpenAI } from '@langchain/openai';
import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';

/**
 * Step 1: Define the state
 * The state keeps track of all messages in the conversation
 */
export const StateAnnotation = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: messagesStateReducer,
    default: () => [],
  }),
});

/**
 * Step 2: Create the weather tools
 * These tools fetch real weather data from WeatherAPI
 */
function getWeatherTools(apiKey: string) {
  // Tool 1: Get current weather
  const currentWeatherTool = new DynamicStructuredTool({
    name: 'get_current_weather',
    description: 'Get the current weather for a location',
    schema: z.object({
      location: z.string().describe('The city name, e.g. London'),
    }),
    func: async (input: { location: string }) => {
      const { location } = input;
      const url = `https://api.weatherapi.com/v1/current.json?key=${apiKey}&q=${encodeURIComponent(location)}`;
      const response = await fetch(url);
      const data = await response.json();

      return `Current weather in ${data.location.name}, ${data.location.country}:
Temperature: ${data.current.temp_c}°C (${data.current.temp_f}°F)
Condition: ${data.current.condition.text}
Humidity: ${data.current.humidity}%
Wind: ${data.current.wind_kph} km/h`;
    },
  });

  // Tool 2: Get weather forecast
  const forecastTool = new DynamicStructuredTool({
    name: 'get_forecast',
    description: 'Get the weather forecast for a location',
    schema: z.object({
      location: z.string().describe('The city name, e.g. London'),
      days: z.number().optional().describe('Number of days (1-14), defaults to 3'),
    }),
    func: async (input: { location: string; days?: number }) => {
      const { location, days } = input;
      const numDays = days || 3;
      const url = `https://api.weatherapi.com/v1/forecast.json?key=${apiKey}&q=${encodeURIComponent(location)}&days=${numDays}`;
      const response = await fetch(url);
      const data = await response.json();

      let forecast = `Weather forecast for ${data.location.name}, ${data.location.country}:\n\n`;
      data.forecast.forecastday.forEach((day: any) => {
        forecast += `${day.date}:
  High: ${day.day.maxtemp_c}°C, Low: ${day.day.mintemp_c}°C
  Condition: ${day.day.condition.text}
  Rain chance: ${day.day.daily_chance_of_rain}%\n\n`;
      });

      return forecast;
    },
  });

  return [currentWeatherTool, forecastTool];
}

/**
 * Step 3: Create the agent node
 * This node calls the AI model with access to weather tools
 */
async function callAgent(state: typeof StateAnnotation.State) {
  // Get the API key
  const apiKey = process.env.WEATHER_API_KEY || '';

  // Create the tools
  const tools = getWeatherTools(apiKey);

  // Create the AI model
  const model = new ChatOpenAI({
    modelName: process.env.MODEL_NAME || 'gpt-4o-mini',
    temperature: 0,
  });

  // Bind the tools to the model
  const modelWithTools = model.bindTools(tools);

  // Build the messages array with a system message
  const messages = [
    {
      role: 'system',
      content: `You are a helpful weather assistant. Use the available tools to get accurate weather information.

When responding to weather queries:
1. Use the tools to fetch current weather data
2. Present the information in a friendly, conversational way
3. Include helpful recommendations based on the weather (e.g., "Bring an umbrella", "Great day for outdoor activities", "Dress warmly")
4. Explain what the weather means for the user's activities

Always provide context and be conversational in your responses.`,
    } as any,
    ...state.messages,
  ];

  // Call the model with the conversation history
  const response = await modelWithTools.invoke(messages);

  // Return the response to add it to the state
  return { messages: [response] };
}

/**
 * Step 4: Create the tools node
 * This node executes the tools that the AI requested
 */
async function callTools(state: typeof StateAnnotation.State) {
  const apiKey = process.env.WEATHER_API_KEY || '';
  const tools = getWeatherTools(apiKey);

  // Get the last message (which should be from the AI)
  const lastMessage = state.messages[state.messages.length - 1] as AIMessage;

  // Get the tool calls from the AI's message
  const toolCalls = lastMessage.tool_calls || [];

  // Execute each tool call
  const toolMessages: ToolMessage[] = [];
  for (const toolCall of toolCalls) {
    // Find the tool
    const tool = tools.find((t) => t.name === toolCall.name);

    if (tool) {
      // Execute the tool
      const result = await tool.invoke(toolCall.args);

      // Create a tool message with the result
      toolMessages.push(
        new ToolMessage({
          content: result,
          tool_call_id: toolCall.id,
        }),
      );
    }
  }

  return { messages: toolMessages };
}

/**
 * Step 5: Create the routing function
 * This decides whether to call tools or end the conversation
 */
function shouldContinue(state: typeof StateAnnotation.State) {
  const lastMessage = state.messages[state.messages.length - 1];

  // If the AI wants to use tools, route to the tools node
  if (lastMessage._getType() === 'ai') {
    const aiMessage = lastMessage as AIMessage;
    if (aiMessage.tool_calls && aiMessage.tool_calls.length > 0) {
      return 'tools';
    }
  }

  // Otherwise, end the conversation
  return '__end__';
}

/**
 * Step 6: Build the graph
 * This connects all the pieces together
 */
const workflow = new StateGraph(StateAnnotation)
  // Add the nodes
  .addNode('agent', callAgent)
  .addNode('tools', callTools)

  // Define the flow
  .addEdge('__start__', 'agent')  // Start with the agent
  .addConditionalEdges('agent', shouldContinue)  // Agent decides what's next
  .addEdge('tools', 'agent');  // After tools, go back to agent

/**
 * Step 7: Compile the graph
 * This creates the final runnable agent
 */
export const graph = workflow.compile({
  checkpointer: new MemorySaver(),  // Saves conversation history
});

graph.name = 'Weather Agent';
