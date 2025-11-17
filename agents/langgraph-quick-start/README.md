# LangGraph Quick Start Agent in TypeScript

## Overview

This is an example **LangGraph TypeScript agent** using the **OpenAI LLM** to answer questions about cryptocurrencies.

You can run this code locally and extend it to build your own agent, as shown in this guide:

- [Get Started with TypeScript LangGraph agents](../../docs/langgraph-quick-start.md)

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

The agent logic is defined in [`src/agent/graph.ts`](src/agent/graph.ts):

- The code imports key **LangChain** and **LangGraph** components.
- `callModel` is a **node** responsible for interacting with the LLM (`gpt-4o-mini` from OpenAI). It reads the current conversation from the graph state, sends the first user message to the model, and returns an assistant reply, updating the `messages` field of the state. The system prompt limits the agent to crypto-related answers only.
- `StateAnnotation` defines the shared state structure between nodes—typically a schema for messages, actions, and intermediate results.
- `route` is a router node that decides whether to continue querying or end the process—based on the state.
- `StateGraph` connects nodes, defining their execution order and dependencies. This example includes only one node—`callModel`.
- `compile()` is a function compiles the **graph** (`graph`) into a runnable agent processing input messages and updates the state through each step.
