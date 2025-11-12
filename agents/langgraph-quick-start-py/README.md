# LangGraph Quick Start Agent in Python

## Overview

This is an example **LangGraph Python agent** using the **OpenAI LLM** to answer questions about cryptocurrencies. This agent is **A2A-compatible**.

You can run this code locally and extend it to build your own Agent, as shown in this guide:

- [Get Started with Python LangGraph agents](../../docs/langgraph-quick-start-py.md)

## What the Agent Does

This agent is a crypto-focused **single-node** chatbot that receives a message, calls an **OpenAI** model, and returns an assistant response.

## How It Works

### Nodes and Graphs

In LangGraph, a **graph** is a map of how your agent thinks and acts. It defines what steps the agent can take and how those steps connect.

Each **node** is one of those steps—for example:

- calling an AI model
- fetching data from an API
- deciding what to do next

When you build a LangGraph agent, you're basically creating a small workflow made of these nodes. The graph handles how messages move between them—so your agent can reason, make calls, and respond in a structured way.

In this example, there is only one node, which calls OpenAI.

### The Agent's Main Logic

The agent logic is defined in [`src/agent/graph.py`](src/agent/graph.ts):

- The code imports the `langgraph.graph` and `langgraph.runtime` components for building and running the agent.
- `Context` is a class defining configurable parameters accessible to the runtime.
- `State` is a dataclass defining the agent's working memory  (a list of message objects forming the conversation).
- `call_model` is a **node** responsible for interacting with the LLM (`gpt-4o-mini` from OpenAI). It receives the current conversation state and runtime context, sends the latest user message to the model, an updated message list that includes the assistant's response.
- `graph` defines the **graph**. `StateGraph` describes the workflow, with one node (`call_model`) that runs as soon as the graph starts. The `compile()` function finalizes the workflow into an executable runtime graph.
- The agent follows the **A2A protocol**, meaning it can receive and send structured conversational messages to other agents. The `State` and `Context` schemas make it interoperable with other A2A-compatible components
