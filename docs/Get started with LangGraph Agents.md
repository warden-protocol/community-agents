# Get started with LangGraph Agents

## Overview

This guide walks you through building a basic [LangGraph Agent](https://langchain-ai.github.io/langgraph/agents/overview/) in **TypeScript**.

The sample Agent uses **OpenAI** by default, but you can switch to a different LLM. 

## Prerequisites

Before you start, complete the following prerequisites:

- [Install Node.js](https://nodejs.org/en/download).
- [Install TypeScript](https://www.npmjs.com/package/typescript).
- [Get a LangSmith API key](https://docs.langchain.com/langsmith/home).
- [Get an OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key).

## Step 1. Create an example Agent

To create a LangGraph Agent, take the following steps:

1. Install the LangGraph CLI by running the folowing command:
    
   ```bash
   npx @langchain/langgraph-cli
   ```
    
2. Install the required packages:
    
   ```bash
   npm install @langchain/langgraph@latest
   npm install @langchain/core@latest
   npm install @langchain/langgraph-checkpoint@latest
   npm install langchain@latest
   npm install @langchain/openai@latest
   ```

   **Note**: If you prefer a different LLM instead of OpenAI, install the corresponding package.
    
3. Fork the [LangGraph project template](https://github.com/langchain-ai/new-langgraphjs-project) on GitHub. Then clone your fork and navigate to its root directory:
    
   ```bash
   git clone FORK_URL
   cd ROOT_DIRECTORY
   ```
  
   **Note**: Alternatively, you can create a repository from scratch and copy the template code there.
    
4. In `package.json`, make sure there're no mismatches in the `dependencies` section:
    
   ```json
     "dependencies": {
       "@langchain/core": "^1.0.1",
       "@langchain/langgraph": "^1.0.0",
       "@langchain/openai": "^1.0.0"
     },    
   ```
    
5. Install dependencies:
   
   ```bash
   npm install
   ```
    
6. In the root directory, duplicate `.env.example` and rename it to `.env`. Add API keys from [Prerequisites](https://www.notion.so/Build-a-TypeScript-LangGraph-Agent-292fb9f091ca806f8380c00b85fed494?pvs=21) and enable tracing in LangSmith (a developer environment for debugging your Agents):
    
   ```bash
   LANGSMITH_API_KEY=LANGSMITH_API_KEY
   OPENAI_API_KEY=OPEN_AI_API_KEY
   LANGSMITH_PROJECT=ts-agent
   LANGSMITH_TRACING=true
    ```
   
   **Notes**:
   - If you prefer a different LLM, provide the corresponding API key.    
   - Never commit API keys to production. [When publishing the Agent](#step-4-publish-and-share), delete the `.env` file.
    
7. Edit the `src/agent/graph.ts` file, which defines the Agent's main logic. You can start with the [example code below](#example-agent-code) and implement your own logic later.

## Step 2. Run the Agent locally

Run your Agent locally to ensure it works as expected:

1. In your project's root directory, execute the following command to launch LangGraph:
   
   ```bash
   npx @langchain/langgraph-cli dev
   ```
   
   If the run succeeds, a welcome message and live logs will appear in your terminal:
   
   ```text
             Welcome to
   
   ╦  ┌─┐┌┐┌┌─┐╔═╗┬─┐┌─┐┌─┐┬ ┬
   ║  ├─┤││││ ┬║ ╦├┬┘├─┤├─┘├─┤
   ╩═╝┴ ┴┘└┘└─┘╚═╝┴└─┴ ┴┴  ┴ ┴.js
   
   - 🚀 API: http://localhost:2024
   - 🎨 Studio UI: https://smith.langchain.com/studio?baseUrl=http://localhost:2024
   
   This in-memory server is designed for development and testing.
   For production use, please use LangGraph Cloud.
   
   info:    ▪ Starting server...
   info:    ▪ Initializing storage...
   ```
    
2. Visit the following links:
   - [LangSmith Studio](https://smith.langchain.com/studio): A developer environment for visualizing, interacting with, and debugging your Agent
   - [LangGraph API reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html): A public API reference where you can view all available endpoints for interacting with Agents
3. Run the [Search Assistants](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/assistants/post/assistants/search) endpoint to get your Agent ID:
        
   **POST** `http://localhost:2024/assistants/search`  
   **Headers**: `Content-Type`: `application/json`  
   **Body**:       
   ```json
   {
     "metadata": {},
     "graph_id": "agent",
     "limit": 10,
     "offset": 0,
     "sort_by": "assistant_id",
     "sort_order": "asc",
     "select": [
       "assistant_id"
     ]
   }
   ```        
   ```bash
   curl http://localhost:2024/assistants/search \
     --request POST \
     --header 'Content-Type: application/json' \
     --data '{
       "metadata": {},
       "graph_id": "",
       "limit": 10,
       "offset": 0,
       "sort_by": "assistant_id",
       "sort_order": "asc",
       "select": [
         "assistant_id"
       ]
     }'
   ```    
   The ID will be returned in the `assistant_id` field. Typically, it's `fe096781-5601-53d2-b2f6-0d3403f7e9ca`.
    
4. Then interact with your Agent using the following endpoint: [Create Run, Wait for Output](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/stateless-runs/post/runs/wait).
      
   **POST** `http://localhost:2024/runs/wait`  
   **Headers**: `Content-Type`: `application/json`  
   **Body**:
        
        ```json
        {
          "assistant_id": "fe096781-5601-53d2-b2f6-0d3403f7e9ca",
          "input": {
            "messages": [
              {
                "role": "user",
                "content": "What can you do?"
              }
            ]
          }
        }
        ```
        
        ```bash
        curl http://localhost:2024/runs/wait \
          --request POST \
          --header 'Content-Type: application/json' \
          --data '{
            "assistant_id": "fe096781-5601-53d2-b2f6-0d3403f7e9ca",
            "input": {
              "messages": [
                {
                  "role": "user",
                  "content": "What can you do?"
                }
              ]
            }
          }'
        ```
   If everything is fine, you'll receive a response including your propmt, assistant's reply, and other data:
        
   ```json
   {
     "messages": [
       {
         "content": "What can you do?",
         "additional_kwargs": {},
         "response_metadata": {},
         "id": "de20753f-7082-4728-bda6-309f23e81573",
         "type": "human"
       },
       {
         "content": "I can provide information and answer questions about cryptocurrencies, blockchain technology, market trends, trading strategies, and related topics. If you have any specific questions about crypto, feel free to ask!",
         "tool_calls": [],
         "invalid_tool_calls": [],
         "additional_kwargs": {},
         "response_metadata": {},
         "id": "34fac7fb-b829-4d0f-b863-5bc9b5971010",
         "type": "ai"
       }
     ]
   }
   ```
        
5. In addition, you can check logs in [LangSmith](https://smith.langchain.com/studio): navigate to **Tracing Project** in the left menu and select your project. The logs will display data on all threads and runs (Agent invocations).

## Step 3. Implement custom logic

After testing the example Agent, you can proceed with implementing your custom logic.

To learn more about LangGraph, use the following resources:

- [LangGraph TypeScript documentation](https://docs.langchain.com/oss/javascript/langgraph/overview):
    - [Quickstart](https://docs.langchain.com/oss/javascript/langgraph/quickstart): Learn the basics
    - [Thinking in LangGraph](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph) and other articles: Dive deeper
- [LangGraph Platform API Reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/assistants/post/assistants/search): Explore the endpoints for interacting with Agents
- [LangGraph JS/TS SDK](https://reference.langchain.com/javascript/modules/_langchain_langgraph-sdk.html?_gl=1*1a31yho*_gcl_au*ODIzMzk4MTQuMTc1OTIyMjc4NQ..*_ga*MTU4OTIwMTQ0Ni4xNzU5MjIyNzg3*_ga_47WX3HKKY2*czE3NjEwMjQ0NTMkbzMzJGcxJHQxNzYxMDI2NDI3JGo1JGwwJGgw): Install the SDK for interacting with the API

## Step 4. Publish and share

Once your Agent is ready, share it with Warden.:

1. Delete the `.env` file to avoid exposing your secrets.
2. Push your local changes to GitHub.
3. Share the link to your repository with Warden.

## Example Agent code

The following code is a basic conversational LangGraph Agent for a quick start:

```tsx
import { StateGraph } from "@langchain/langgraph";
import { RunnableConfig } from "@langchain/core/runnables";
import { StateAnnotation } from "./state.js";
import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage } from "@langchain/core/messages";

/**
 * Define a node, these do the work of the graph and should have most of the logic.
 * Must return a subset of the properties set in StateAnnotation.
 * @param state The current state of the graph.
 * @param config Extra parameters passed into the state graph.
 * @returns Some subset of parameters of the graph state, used to update the state
 * for the edges and nodes executed next.
 */
const callModel = async (
  state: typeof StateAnnotation.State,
  _config: RunnableConfig,
): Promise<typeof StateAnnotation.Update> => {
  const model = new ChatOpenAI({
    modelName: "gpt-4o-mini",
    temperature: 0.7,
    apiKey: process.env.OPENAI_API_KEY,
  });

  const response = await model.invoke([
    {
      role: "system",
      content: "You are a helpful assistant that only answers questions about crypto."
    },
    new HumanMessage(state.messages[0].content),
  ]);

  console.log("Model response:", response);

  return {
    messages: [
      {
        role: "assistant",
        content: response.content,
      },
    ],
  };
};
/**
 * Routing function: Determines whether to continue research or end the builder.
 * This function decides if the gathered information is satisfactory or if more research is needed.
 *
 * @param state - The current state of the research builder
 * @returns Either "callModel" to continue research or END to finish the builder
 */
export const route = (
  state: typeof StateAnnotation.State,
): "__end__" | "callModel" => {
  if (state.messages.length > 0) {
    return "__end__";
  }
  return "callModel";
};

// Finally, create the graph itself.
const builder = new StateGraph(StateAnnotation)
  // Add the nodes to do the work.
  // Chaining the nodes together in this way
  // updates the types of the StateGraph instance
  // so you have static type checking when it comes time
  // to add the edges.
  .addNode("callModel", callModel)
  // Regular edges mean "always transition to node B after node A is done"
  // The "__start__" and "__end__" nodes are "virtual" nodes that are always present
  // and represent the beginning and end of the builder.
  .addEdge("__start__", "callModel")
  // Conditional edges optionally route to different nodes (or end)
  .addConditionalEdges("callModel", route);

export const graph = builder.compile();
graph.name = "New Agent";
```
