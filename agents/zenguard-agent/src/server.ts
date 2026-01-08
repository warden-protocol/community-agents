import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import { createZenGuardWorkflow } from './graph/workflow';
import { HumanMessage } from '@langchain/core/messages';
import dotenv from 'dotenv';
import { v4 as uuidv4 } from 'uuid';

dotenv.config();
const app = express();
const port = process.env.PORT || 3000;

app.use(cors({ origin: '*' }));
// Note: cors() middleware already handles OPTIONS preflight requests
app.use(bodyParser.json());

// --- Middleware: API Key Authentication (Soft Mode for Debugging) ---
// Warden Studio sends 'x-api-key' header.
// In debug mode: warn on mismatch but allow request to proceed
app.use((req, res, next) => {
  const envKey = process.env.API_KEY;
  const reqKey = req.header('x-api-key');

  if (envKey && reqKey && reqKey !== envKey) {
    console.warn(`⚠️ API Key mismatch - allowing request for debugging (got: ${reqKey?.substring(0,4)}...)`);
  } else if (reqKey) {
    console.log(`🔑 Request received with Key: ${reqKey.substring(0,4)}...`);
  } else {
    console.log(`📨 Request received without API Key (path: ${req.path})`);
  }
  // Always allow request to proceed (soft auth for debugging)
  next();
});

// --- 1. GET /assistants (The Validation Handshake) ---
// CRITICAL: Must return { "assistants": [...] } structure
app.get('/assistants', (req, res) => {
  res.json({
    assistants: [{
      assistant_id: "zenguard",
      graph_id: "zenguard",
      config: {},
      metadata: {
        name: "ZenGuard",
        description: "AI Psychological Firewall for Warden Protocol",
        created_at: new Date().toISOString()
      }
    }]
  });
});

// 2. GET /assistants/:id
app.get('/assistants/:id', (req, res) => {
  res.json({
    assistant_id: req.params.id,
    graph_id: "zenguard",
    config: {},
    metadata: {
      name: "ZenGuard",
      created_at: new Date().toISOString()
    }
  });
});

// --- Thread Management Endpoints ---

// 3. POST /threads - Create a new thread
app.post('/threads', (req, res) => {
  const threadId = uuidv4();
  console.log(`📝 Creating new thread: ${threadId}`);
  res.json({
    thread_id: threadId,
    created_at: new Date().toISOString(),
    metadata: {}
  });
});

// 4. GET /threads/:thread_id - Get thread info
app.get('/threads/:thread_id', (req, res) => {
  console.log(`📖 Getting thread: ${req.params.thread_id}`);
  res.json({
    thread_id: req.params.thread_id,
    created_at: new Date().toISOString(),
    metadata: {},
    values: {}
  });
});

// 5. POST /threads/search - Search threads
app.post('/threads/search', (req, res) => {
  console.log(`🔍 Searching threads`);
  res.json({
    threads: []
  });
});

// 6. GET /threads/:thread_id/state - Get thread state
app.get('/threads/:thread_id/state', (req, res) => {
  console.log(`📊 Getting thread state: ${req.params.thread_id}`);
  res.json({
    values: {},
    next: [],
    config: {},
    metadata: {}
  });
});

// 6b. POST /threads/:thread_id/history - Get thread history
app.post('/threads/:thread_id/history', (req, res) => {
  console.log(`📜 History request for thread: ${req.params.thread_id}`);

  // Return empty array (LangGraph SDK expects array format)
  res.json([]);
});

// 6c. GET /threads/:thread_id/history - Get thread history (alternative)
app.get('/threads/:thread_id/history', (req, res) => {
  console.log(`📜 History GET request for thread: ${req.params.thread_id}`);

  // Return empty array (LangGraph SDK expects array format)
  res.json([]);
});

// --- Run Execution Endpoints ---

// 7. POST /threads/:thread_id/runs - Create a run (async style, but we execute sync)
app.post('/threads/:thread_id/runs', async (req, res) => {
  try {
    console.log(`\n🏃 Incoming Run Request for thread: ${req.params.thread_id}`);

    const inputPayload = req.body.input || req.body;
    let userText = "Hello";

    if (inputPayload.messages && Array.isArray(inputPayload.messages)) {
      const lastMsg = inputPayload.messages[inputPayload.messages.length - 1];
      userText = typeof lastMsg === 'string' ? lastMsg : lastMsg.content;
    } else if (typeof inputPayload === 'string') {
      userText = inputPayload;
    } else if (req.body.message) {
      userText = req.body.message;
    }

    console.log(`🗣️ User Input: "${userText.substring(0, 50)}..."`);

    const workflow = createZenGuardWorkflow();
    const result = await workflow.invoke({
      messages: [new HumanMessage(userText)]
    });

    const lastMsg = result.messages[result.messages.length - 1];
    const runId = uuidv4();

    res.json({
      run_id: runId,
      thread_id: req.params.thread_id,
      status: "completed",
      created_at: new Date().toISOString(),
      outputs: {
        messages: [{
          type: "ai",
          content: lastMsg.content,
          additional_kwargs: {
            risk_index: result.metrics?.irrationalityIndex,
            warden_action: result.wardenIntent ? "TRIGGERED" : "NONE"
          }
        }]
      },
      metadata: {
        risk_index: result.metrics?.irrationalityIndex
      }
    });

  } catch (error: any) {
    console.error('❌ Error:', error);
    res.status(500).json({ error: error.message });
  }
});

// 8. POST /threads/:thread_id/runs/stream - SSE Streaming endpoint
app.post('/threads/:thread_id/runs/stream', async (req, res) => {
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    // Improved input parsing
    let userText = "Hello";
    const inputPayload = req.body.input || req.body;

    if (inputPayload.messages && Array.isArray(inputPayload.messages)) {
      const lastMsg = inputPayload.messages[inputPayload.messages.length - 1];
      if (typeof lastMsg === 'string') {
        userText = lastMsg;
      } else if (lastMsg && typeof lastMsg === 'object') {
        const rawContent = lastMsg.content || lastMsg.text;
        userText = typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent || lastMsg);
      }
    } else if (typeof inputPayload === 'string') {
      userText = inputPayload;
    } else if (inputPayload.content) {
      userText = inputPayload.content;
    }

    console.log(`🔄 Stream Request for thread: ${req.params.thread_id}`);
    console.log(`📝 User Input (parsed): "${userText}"`);

    // Invoke workflow
    const workflow = createZenGuardWorkflow();
    const result = await workflow.invoke({ messages: [new HumanMessage(userText)] });

    const lastMsg = result.messages[result.messages.length - 1];
    const riskIndex = result.metrics?.irrationalityIndex || 0.05;

    // Build response data with message ID and run ID
    const messageId = uuidv4();
    const runId = uuidv4();
    const responseData = {
      id: messageId,
      type: "ai",
      content: lastMsg.content,
      additional_kwargs: {
        risk_index: riskIndex,
        warden_action: result.wardenIntent ? "TRIGGERED" : "NONE"
      }
    };

    // Send metadata event (LangGraph standard)
    res.write(`event: metadata\n`);
    res.write(`data: ${JSON.stringify({ run_id: runId })}\n\n`);

    // Send messages event (array format for Agent Chat compatibility)
    res.write(`event: messages\n`);
    res.write(`data: ${JSON.stringify([responseData])}\n\n`);

    // Send end event
    res.write(`event: end\n`);
    res.write(`data: {}\n\n`);

    res.end();

  } catch (error: any) {
    console.error('❌ Stream Error:', error.message);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
    res.end();
  }
});

// --- 9. POST /runs/wait (The Chat Execution) ---
// Handles standard LangGraph input format: { input: { messages: [...] } }
app.post(['/runs/wait', '/threads/:thread_id/runs/wait'], async (req, res) => {
  try {
    console.log(`\n📩 Incoming Run Request`);

    // 1. Parse Input
    const inputPayload = req.body.input || req.body;
    let userText = "Hello";

    if (inputPayload.messages && Array.isArray(inputPayload.messages)) {
        const lastMsg = inputPayload.messages[inputPayload.messages.length - 1];
        userText = typeof lastMsg === 'string' ? lastMsg : lastMsg.content;
    } else if (typeof inputPayload === 'string') {
        userText = inputPayload;
    } else if (req.body.message) {
        userText = req.body.message; // Legacy fallback
    }

    console.log(`🗣️ User Input: "${userText.substring(0, 50)}..."`);

    // 2. Invoke ZenGuard Logic
    const workflow = createZenGuardWorkflow();
    const result = await workflow.invoke({
      messages: [new HumanMessage(userText)]
    });

    const lastMsg = result.messages[result.messages.length - 1];

    // 3. Format Response (Standard LangGraph Schema)
    // This ensures Studio can parse the reply
    res.json({
      id: uuidv4(),
      status: "success",
      outputs: {
        // Studio expects 'messages' inside outputs
        messages: [
            {
                type: "ai",
                content: lastMsg.content,
                additional_kwargs: {
                    risk_index: result.metrics?.irrationalityIndex,
                    warden_action: result.wardenIntent ? "TRIGGERED" : "NONE"
                }
            }
        ]
      },
      metadata: {
         risk_index: result.metrics?.irrationalityIndex
      }
    });

  } catch (error: any) {
    console.error('❌ Error:', error);
    res.status(500).json({ error: error.message });
  }
});

// --- Info & Health Endpoints ---

// GET /info - Service information (required by Agent Chat)
app.get('/info', (req, res) => {
  console.log(`ℹ️ Info endpoint called`);
  res.json({
    version: "1.0.0",
    name: "ZenGuard Agent",
    description: "AI Psychological Firewall for Warden Protocol"
  });
});

// GET /health - Health check
app.get('/health', (req, res) => res.json({ status: 'ok', version: 'LangGraph-Std-1.0' }));

app.listen(port, () => {
  console.log(`🛡️ ZenGuard Standard Server running on port ${port}`);
});
