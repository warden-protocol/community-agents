# Get started with Python LangGraph Agents

## Overview

This guide explains how to quickly get started with building [LangGraph agents](https://langchain-ai.github.io/langgraph/agents/overview/) with [A2A support](https://docs.langchain.com/langsmith/server-a2a) in **Python**.

You'll copy, run, and extend our template: [`agents/laggraph-quick-start-py`](../agents/langgraph-quick-start-py). It's a **single-node** chatbot that answer questions about cryptocurrencies: receives a message, calls an **OpenAI** model, and returns an assistant response.

**Note**: This guide focuses on the essentials (how to deploy and test your agent locally) rather than on real-world agent logic.

## Prerequisites

Before you start, complete the following prerequisites:

- [Install Python 3.12](https://www.python.org/downloads/) or higher.
- [Get a LangSmith API key](https://docs.langchain.com/langsmith/home).
- [Get an OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-openai-api-key).

## Step 1. Set Up the Example Project

First, set up the example project:

1. Install the LangGraph CLI by running the following command:
    
   ```bash
   pip install --upgrade"langgraph-cli[inmem]"
   ```

2. Install the required packages:
    
   ```bash
   pip install langchain_community
   pip install langchain-openai
   ```

3. Clone this repository:

   ```bash
   git clone https://github.com/warden-protocol/community-agents.git
   ```

4. Create and clone a new repository for your agent.

5. Copy files from [`agents/laggraph-quick-start-py`](../agents/langgraph-quick-start-py) to your repository.

   **Note**: This example is based on the [LangGraph project template](https://github.com/langchain-ai/new-langgraph-project).

6. Navigate to the root directory of your project and install dependencies in the editable mode. When you run a LangGraph server locally, it'll automatically pick up any code edits.
   
   ```bash
   cd ROOT_DIRECTORY
   pip install -e .
   ```
    
7. Duplicate `.env.example` and rename it to `.env`. Add API keys from [Prerequisites](#prerequisites) and enable tracing in LangSmith (a developer environment for debugging your agents):
    
   ```bash
   LANGSMITH_API_KEY=LANGSMITH_API_KEY
   OPENAI_API_KEY=OPEN_AI_API_KEY
   LANGSMITH_PROJECT=py-agent
   LANGSMITH_TRACING=true
   ```
## Step 2. Run the Agent Locally

Now you can run the example agent locally:

1. In your project's root directory, execute the following command to launch LangGraph:
   
   ```bash
   langgraph dev
   ```
   
   If the run succeeds, a welcome message and live logs will appear in your terminal:
   
   ```text
           Welcome to
   
   ╦  ┌─┐┌┐┌┌─┐╔═╗┬─┐┌─┐┌─┐┬ ┬
   ║  ├─┤││││ ┬║ ╦├┬┘├─┤├─┘├─┤
   ╩═╝┴ ┴┘└┘└─┘╚═╝┴└─┴ ┴┴  ┴ ┴
   - 🚀 API: http://127.0.0.1:2024
   - 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
   - 📚 API Docs: http://127.0.0.1:2024/docs
      
   This in-memory server is designed for development and testing.
   For production use, please use LangGraph Platform.

   2025-10-15T09:39:33.264996Z [info     ] Using langgraph_runtime_inmem  [langgraph_runtime] api_variant=local_dev langgraph_api_version=0.4.37 thread_name=MainThread
   2025-10-15T09:39:33.284558Z [info     ] Using auth of type=noop        [langgraph_api.auth.middleware] api_variant=local_dev langgraph_api_version=0.4.37 thread_name=MainThread
   2025-10-15T09:39:33.294531Z [info     ] Starting In-Memory runtime with langgraph-api=0.4.37 and in-memory runtime=0.14.1 [langgraph_runtime_inmem.lifespan] api_variant=local_dev langgraph_api_version=0.4.37 langgraph_runtime_inmem_version=0.14.1 thread_name=asyncio_0 version=0.4.37
   ```
2. Visit the following links:
   - [LangSmith Studio](https://smith.langchain.com/studio): A local developer environment for visualizing, interacting with, and debugging your agent
   - [LangGraph API reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html): A public API reference where you can view all available endpoints for interacting with agents
   - http://localhost:2024/docs: An API reference on your localhost where you can test all endpoints

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

4. Now you can access your A2A Agent Card:
   
   ```text
   http://localhost:2024/.well-known/agent-card.json?assistant_id=fe096781-5601-53d2-b2f6-0d3403f7e9ca
   ```
   
   The card will display something like this:

   ```json
   {
       "protocolVersion": "0.3.0",
       "name": "agent",
       "description": "agent assistant",
       "url": "http://127.0.0.1:2024/a2a/fe096781-5601-53d2-b2f6-0d3403f7e9ca",
       "preferredTransport": "JSONRPC",
       "capabilities": {
           "streaming": true,
           "pushNotifications": false,
           "stateTransitionHistory": false
       },
       "defaultInputModes": [
           "application/json",
           "text/plain"
       ],
       "defaultOutputModes": [
           "application/json",
           "text/plain"
       ],
       "skills": [
           {
               "id": "fe096781-5601-53d2-b2f6-0d3403f7e9ca-main",
               "name": "agent Capabilities",
               "description": "agent assistant",
               "tags": [
                   "assistant",
                   "langgraph"
               ],
               "examples": [],
               "inputModes": [
                   "application/json",
                   "text/plain"
               ],
               "outputModes": [
                   "application/json",
                   "text/plain"
               ],
               "metadata": {
                   "inputSchema": {
                       "required": [
                           "messages"
                       ],
                       "properties": [
                           "messages"
                       ],
                       "supportsA2A": true
                   }
               }
           }
       ],
       "version": "0.4.37"
   }
   ```

5. Finally, try the A2A Post endpoint:
      
   **POST** `http://localhost:2024/a2a/fe096781-5601-53d2-b2f6-0d3403f7e9ca`  
   **Headers**: `Accept`: `application/json`, `Content-Type`: `application/json`  
   **Body**:
        
   ```json
   {
     "jsonrpc": "2.0",
     "id": "",
     "method": "message/send",
     "params": {
       "message": {
         "role": "user",
         "parts": [
           {
             "kind": "text",
             "text": "What can you do?"
           }
         ],
         "messageId": ""
       },
       "thread": {
         "threadId": ""
       }
     }
   }
   ```        
   ```bash
   curl http://localhost:2024/a2a/fe096781-5601-53d2-b2f6-0d3403f7e9ca \
     --request POST \
     --header 'Accept: application/json' \
     --header 'Content-Type: application/json' \
     --data '{
       "jsonrpc": "2.0",
       "id": "",
       "method": "message/send",
       "params": {
         "message": {
           "role": "user",
           "parts": [
             {
               "kind": "text",
               "text": "What can you do?"
             }
           ],
           "messageId": ""
         },
         "thread": {
           "threadId": ""
         }
       }
     }'
   ```
   If everything is fine, you'll receive a response including your prompt, assistant's reply, and other data:
        
   ```json
   {
     "jsonrpc": "2.0",
     "id": "",
     "result": {
       "id": "019a05c7-3a0b-738f-9913-ce6436b6efee",
       "contextId": "369baffd-b0fe-4f8c-9ed7-4959a3638906",
       "history": [
         {
           "role": "agent",
           "parts": [
             {
               "kind": "text",
               "text": "What can you do?"
             }
           ],
           "messageId": "fef9625f-b031-4265-a20a-b44ecd802f26",
           "taskId": "019a05c7-3a0b-738f-9913-ce6436b6efee",
           "contextId": "369baffd-b0fe-4f8c-9ed7-4959a3638906",
           "kind": "message"
         },
         {
           "role": "agent",
           "parts": [
             {
               "kind": "text",
               "text": "I can provide information about cryptocurrencies, including their technology, market trends, investment strategies, and specific coins or tokens. I can also explain concepts related to blockchain, wallets, exchanges, and more. If you have any specific questions about crypto, feel free to ask!"
             }
           ],
           "messageId": "93c8ca89-1411-4bd3-99e5-1a0b42e6b4df",
           "taskId": "019a05c7-3a0b-738f-9913-ce6436b6efee",
           "contextId": "369baffd-b0fe-4f8c-9ed7-4959a3638906",
           "kind": "message"
         }
       ],
       "kind": "task",
       "status": {
         "state": "completed",
         "timestamp": "2025-10-21T07:58:57.909704+00:00"
       },
       "artifacts": [
         {
           "artifactId": "d62ee97c-3a81-4e69-ba34-fe57de9ce9ae",
           "name": "Assistant Response",
           "description": "Response from assistant fe096781-5601-53d2-b2f6-0d3403f7e9ca",
           "parts": [
             {
               "kind": "text",
               "text": "I can provide information about cryptocurrencies, including their technology, market trends, investment strategies, and specific coins or tokens. I can also explain concepts related to blockchain, wallets, exchanges, and more. If you have any specific questions about crypto, feel free to ask!"
             }
           ]
         }
       ]
     }
   }
   ```

6. In addition, you can check logs in [LangSmith](https://smith.langchain.com/studio): navigate to **Tracing Project** in the left menu and select your project. The logs will display data on all threads and runs (agent invocations).

## Step 3. Implement Custom Logic

The logic of the template agent is explained in its [README](../agents/langgraph-quick-start-py/README.md).

After testing the agent, you can proceed with implementing your custom logic:
- If you prefer a different LLM to OpenAI, adjust the example code accordingly and update the `.env` file and dependencies.
- Add new nodes—for example, a node calling a crypto API or a summarize node using another model.
- Integrate memory to store conversation history or facts across sessions.
- Customize the state: add fields for context like topics, confidence, or source URLs.

To learn more about LangGraph, use the following resources:

- [LangGraph Python documentation](https://docs.langchain.com/oss/python/langgraph/overview):
    - [Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart): Learn the basics
    - [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) and other articles: Dive deeper
    - [A2A endpoint in LangGraph Server](https://docs.langchain.com/langgraph-platform/server-a2a): Learn more about the A2A compatibility
- [LangGraph Platform API Reference](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/assistants/post/assistants/search): Explore the endpoints for interacting with agents
- [LangGraph Python SDK](https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/): Install the SDK for interacting with the API

## Step 4. Publish and Share

Once your agent is ready, share it with Warden:

1. Delete the `.env` file to avoid exposing your secrets.
   **Important**: Never commit your API keys to production.
2. Push your local changes to GitHub.
3. Deploy your agent, as explained here: [Deploy Your Agent](deploy-an-agent.md).
4. Add your agent to the list of [Warden Community Agents](../readme.md#community-agents-and-tools) through a PR.