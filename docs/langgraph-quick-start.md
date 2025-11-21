# Get Started with TypeScript LangGraph Agents

## Overview

This guide explains how to quickly get started with building [LangGraph Agents](https://langchain-ai.github.io/langgraph/agents/overview/) in **TypeScript**

You'll copy, run, and extend our template: [`agents/laggraph-quick-start`](../agents/langgraph-quick-start). It's a **single-node** chatbot that answer questions about cryptocurrencies: receives a message, calls an **OpenAI** model, and returns an assistant response.

**Note**: This guide focuses on the essentials: how to deploy and test your agent locally. If you'd rather skip setup details and dive straight into building real-world agent logic, check out the [Weather Agent example](../agents/weather-agent).

## Prerequisites

Before you start, complete the following prerequisites:

- [Install Node.js](https://nodejs.org/en/download).
- [Install TypeScript](https://www.npmjs.com/package/typescript).
- [Get a LangSmith API key](https://docs.langchain.com/langsmith/home).
- [Get an OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key).

## Step 1. Set Up the Example Project

First, set up the example project:

1. Install the LangGraph CLI by running the following command:
    
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

3. Clone this repository:

   ```bash
   git clone https://github.com/warden-protocol/community-agents.git
   ```

4. Create and clone a new repository for your agent.

5. Copy files from [`agents/laggraph-quick-start`](../agents/langgraph-quick-start) to your repository.

   **Note**: This example is based on the [LangGraph project template](https://github.com/langchain-ai/new-langgraphjs-project).

6. Navigate to the root directory of your project and install dependencies:
   
   ```bash
   cd ROOT_DIRECTORY
   npm install
   ```
    
7. Duplicate `.env.example` and rename it to `.env`. Add API keys from [Prerequisites](#prerequisites) and enable tracing in LangSmith (a developer environment for debugging your agents):
    
   ```bash
   LANGSMITH_API_KEY=LANGSMITH_API_KEY
   OPENAI_API_KEY=OPEN_AI_API_KEY
   LANGSMITH_PROJECT=ts-agent
   LANGSMITH_TRACING=true
   ```
## Step 2. Run the Agent Locally

Now you can run the example agent locally:

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
   - [LangSmith Studio](https://smith.langchain.com/studio): A developer environment for visualizing, interacting with, and debugging your agent
   - [LangGraph API reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html): A public API reference where you can view all available endpoints for interacting with agents

3. Run the [Search Assistants](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/assistants/post/assistants/search) endpoint to get your agent's ID:
        
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
    
4. Then interact with your agent using the following endpoint: [Create Run, Wait for Output](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/stateless-runs/post/runs/wait).
      
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
   If everything is fine, you'll receive a response including your prompt, assistant's reply, and other data:
        
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

5. In addition, you can check logs in [LangSmith](https://smith.langchain.com/studio): navigate to **Tracing Project** in the left menu and select your project. The logs will display data on all threads and runs (agent invocations).

## Step 3. Implement Custom Logic

The logic of the template agent is explained in its [README](../agents/langgraph-quick-start/README.md).

After testing the agent, you can proceed with implementing your custom logic:
- If you prefer a different LLM to OpenAI, adjust the example code accordingly and update the `.env` file and dependencies.
- Add new nodes—for example, a node calling a crypto API or a summarize node using another model.
- Integrate memory to store conversation history or facts across sessions.
- Customize the state: add fields for context like topics, confidence, or source URLs.

Alternatively, you can switch to the [Weather Agent example](../agents/weather-agent), which demonstrates how to build real-world agent logic.

To learn more about LangGraph, use the following resources:

- [LangGraph TypeScript documentation](https://docs.langchain.com/oss/javascript/langgraph/overview):
    - [Quickstart](https://docs.langchain.com/oss/javascript/langgraph/quickstart): Learn the basics
    - [Thinking in LangGraph](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph) and other articles: Dive deeper
- [LangGraph Platform API Reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/assistants/post/assistants/search): Explore the endpoints for interacting with agents
- [LangGraph JS/TS SDK](https://reference.langchain.com/javascript/modules/_langchain_langgraph-sdk.html?_gl=1*1a31yho*_gcl_au*ODIzMzk4MTQuMTc1OTIyMjc4NQ..*_ga*MTU4OTIwMTQ0Ni4xNzU5MjIyNzg3*_ga_47WX3HKKY2*czE3NjEwMjQ0NTMkbzMzJGcxJHQxNzYxMDI2NDI3JGo1JGwwJGgw): Install the SDK for interacting with the API

## Step 4. Publish and Share

Once your agent is ready, share it with Warden:

1. Delete the `.env` file to avoid exposing your secrets.

   **Important**: Never commit your API keys to production.

2. Push your local changes to GitHub.

3. Deploy your agent, as explained here: [Deploy Your Agent](deploy-an-agent.md).

4. Add your agent to the list of [Warden Community Agents](../readme.md#community-agents-and-tools) through a PR.
