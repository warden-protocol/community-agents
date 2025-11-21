# Deploy a LangGraph Agent

## Overview

This guide explains how to deploy a LangGraph agent. There are two options:

- [LangGraph Cloud](#option-1-langgraph-cloud)
- [Self-hosting](#option-2-self-hosting)

## Option 1: LangGraph Cloud

The simplest and fastest way to deploy a LangGraph agent is through **LangGraph Cloud deployment**.

You can learn more in LangGraph official documentation:

- [Deploy your app to Cloud](https://docs.langchain.com/langsmith/deployment-quickstart)
- [Application structure](https://docs.langchain.com/langsmith/application-structure)

To deploy your agent, simply take these steps:

1. Keep your API keys in a safe space and delete the `.env` file. Then push local changes to GitHub. **Important**: Never commit your API keys to production.

2. In [LangSmith](https://smith.langchain.com/studio), click **Deployments** in the left menu, then click **New Deployment**.

3. Connect your GitHub account and select the repository with the project.

4. Enter the deployment name.

5. Add your `OPENAI_API_KEY` as an environment variable.

6. Click **Submit** at the top and wait for your deployment.

7. If everything is fine, you'll see the *Currently deployed* status. In the right panel, under **API URL**, you'll also find your agent's URL.

8. Now you can interact with your agent:

   - Use you **agent's API URL** as the base URL for the calls.
   - The assistant will have the same ID as locally: `fe096781-5601-53d2-b2f6-0d3403f7e9ca`.
   - All production API calls require the `x-api-key` header for authorization. In this header, pass your **LangSmith API key**.

### Example Call 1

Once your agent is deployed, you can test it by running [Create Run, Wait for Output](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/stateless-runs/post/runs/wait).

**POST** `AGENT_API_URL:2024/runs/wait`  
**Headers**: `Content-Type`: `application/json`, `x-api-key`: `LANGSMITH_API_KEY`   
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
curl AGENT_API_URL/runs/wait \
 --request POST \
 --header 'Content-Type: application/json' \
 --header 'x-api-key: LANGSMITH_API_KEY' \
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
### Example Call 2 (Python Agents Only)

If you Agent is in Python, you can also try [A2A Post](https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/a2a/post/a2a/%7Bassistant_id%7D).

**POST** `AGENT_API_URL/a2a/fe096781-5601-53d2-b2f6-0d3403f7e9ca`  
**Headers**: `Accept`: `application/json`, `Content-Type`: `application/json`, `x-api-key`: `LANGSMITH_API_KEY`  
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
curl AGENT_API_URL/a2a/fe096781-5601-53d2-b2f6-0d3403f7e9ca \
  --request POST \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: LANGSMITH_API_KEY' \
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

## Option 2: Self-Hosting

You can also **self-host the LangGraph runtime**. While this setup doesn't include LangSmith, the LangGraph Server API remains fully accessible.

You can use **any hosting stack**.

For a simple example walkthrough, check out this video tutorial: [Deploy ANY Langgraph AI Agent in Minutes!](https://youtu.be/SGt786ne_Mk?si=ALlsNJwzSNSECUr-)

If you choose the self-hosting option, here are the main steps to take:

1. Create a [Dockerfile](https://docs.docker.com/build/concepts/dockerfile/).

2. Keep your API keys in a safe space and delete the `.env` file. Then push local changes to GitHub. **Important**: Never commit your API keys to production.
    
3. Get environment variables for your Postgres database and key-value storage.

4. Set up a hosting:

   - Add environment variables
   - Set up a key-value storage
   - Connect to your GitHub project

5. Deploy. Your agent and LangGraph API endpoints will be available on a public URL.
