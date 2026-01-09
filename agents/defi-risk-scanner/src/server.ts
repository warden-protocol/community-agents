import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import { config } from './config';
import { runRiskScan, formatRiskReportMessage } from './graph';

const app = express();

app.use(cors({ origin: '*' }));
app.use(express.json());

// --- 1. GET /assistants ---
// LangGraph API standard: return array directly
app.get('/assistants', (req, res) => {
  res.json([{
    assistant_id: 'defi-risk-scanner',
    graph_id: 'defi-risk-scanner',
    config: {},
    metadata: {
      name: 'DeFi Risk Scanner',
      description: 'Analyzes DeFi protocol security risks using multiple data sources',
      created_at: new Date().toISOString(),
    },
  }]);
});

// 2. GET /assistants/:id
app.get('/assistants/:id', (req, res) => {
  res.json({
    assistant_id: req.params.id,
    graph_id: 'defi-risk-scanner',
    config: {},
    metadata: {
      name: 'DeFi Risk Scanner',
      created_at: new Date().toISOString(),
    },
  });
});

// 2b. POST /assistants/search - Search/list assistants (LangGraph API standard)
app.post('/assistants/search', (req, res) => {
  const { metadata = {}, limit = 10, offset = 0 } = req.body || {};
  console.log(`🔍 Searching assistants (limit: ${limit}, offset: ${offset})`);

  const assistants = [{
    assistant_id: 'defi-risk-scanner',
    graph_id: 'defi-risk-scanner',
    name: 'DeFi Risk Scanner',
    description: 'Analyzes DeFi protocol security risks using multiple data sources',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    config: {},
    metadata: {}
  }];

  res.json(assistants); // LangGraph API 標準：直接回傳陣列
});

// --- Thread Management ---

// 3. POST /threads
app.post('/threads', (req, res) => {
  const threadId = uuidv4();
  console.log(`📝 Creating thread: ${threadId}`);
  res.json({
    thread_id: threadId,
    created_at: new Date().toISOString(),
    metadata: {},
  });
});

// 4. GET /threads/:thread_id
app.get('/threads/:thread_id', (req, res) => {
  res.json({
    thread_id: req.params.thread_id,
    created_at: new Date().toISOString(),
    metadata: {},
    values: {},
  });
});

// 5. POST /threads/search
// LangGraph API standard: return array directly
app.post('/threads/search', (req, res) => {
  console.log('🔍 Searching threads');
  res.json([]);
});

// 6. GET /threads/:thread_id/state
app.get('/threads/:thread_id/state', (req, res) => {
  res.json({
    values: {},
    next: [],
    config: {},
    metadata: {},
  });
});

// 7. POST/GET /threads/:thread_id/history
app.post('/threads/:thread_id/history', (req, res) => res.json([]));
app.get('/threads/:thread_id/history', (req, res) => res.json([]));

// --- Run Execution ---

// Helper: Parse user input from various formats
function parseUserInput(body: Record<string, unknown>): string {
  const inputPayload = (body.input as Record<string, unknown>) || body;

  if (inputPayload.messages && Array.isArray(inputPayload.messages)) {
    const lastMsg = inputPayload.messages[inputPayload.messages.length - 1];
    if (typeof lastMsg === 'string') return lastMsg;
    if (lastMsg && typeof lastMsg === 'object') {
      const msg = lastMsg as Record<string, unknown>;
      return String(msg.content || msg.text || '');
    }
  }

  if (typeof inputPayload === 'string') return inputPayload;
  if (body.message) return String(body.message);
  if (inputPayload.content) return String(inputPayload.content);

  return '';
}

// 8. POST /threads/:thread_id/runs
app.post('/threads/:thread_id/runs', async (req, res) => {
  try {
    const userInput = parseUserInput(req.body);
    console.log(`\n🔍 Scan Request: "${userInput}"`);

    if (!userInput) {
      return res.status(400).json({ error: 'No protocol name or address provided' });
    }

    const result = await runRiskScan(userInput);
    const message = formatRiskReportMessage(result);
    const runId = uuidv4();

    res.json({
      run_id: runId,
      thread_id: req.params.thread_id,
      status: 'completed',
      created_at: new Date().toISOString(),
      outputs: {
        messages: [{
          type: 'ai',
          content: message,
          additional_kwargs: {
            risk_score: result.riskReport?.overallScore,
            risk_level: result.riskReport?.riskLevel,
          },
        }],
      },
      metadata: {
        protocol: result.riskReport?.protocol,
        risk_score: result.riskReport?.overallScore,
      },
    });
  } catch (error) {
    console.error('❌ Error:', error);
    res.status(500).json({ error: (error as Error).message });
  }
});

// 9. POST /threads/:thread_id/runs/stream (SSE)
app.post('/threads/:thread_id/runs/stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    const userInput = parseUserInput(req.body);
    console.log(`\n🔄 Stream Scan: "${userInput}"`);

    if (!userInput) {
      res.write(`event: error\n`);
      res.write(`data: ${JSON.stringify({ error: 'No protocol provided' })}\n\n`);
      return res.end();
    }

    const result = await runRiskScan(userInput);
    const message = formatRiskReportMessage(result);
    const runId = uuidv4();
    const messageId = uuidv4();

    // Send metadata event
    res.write(`event: metadata\n`);
    res.write(`data: ${JSON.stringify({ run_id: runId })}\n\n`);

    // Send messages event
    res.write(`event: messages\n`);
    res.write(`data: ${JSON.stringify([{
      id: messageId,
      type: 'ai',
      content: message,
      additional_kwargs: {
        risk_score: result.riskReport?.overallScore,
        risk_level: result.riskReport?.riskLevel,
      },
    }])}\n\n`);

    // Send end event
    res.write(`event: end\n`);
    res.write(`data: {}\n\n`);

    res.end();
  } catch (error) {
    console.error('❌ Stream Error:', error);
    res.write(`event: error\n`);
    res.write(`data: ${JSON.stringify({ error: (error as Error).message })}\n\n`);
    res.end();
  }
});

// 10. POST /runs/wait and /threads/:thread_id/runs/wait
app.post(['/runs/wait', '/threads/:thread_id/runs/wait'], async (req, res) => {
  try {
    const userInput = parseUserInput(req.body);
    console.log(`\n📩 Wait Scan: "${userInput}"`);

    if (!userInput) {
      return res.status(400).json({ error: 'No protocol name or address provided' });
    }

    const result = await runRiskScan(userInput);
    const message = formatRiskReportMessage(result);

    res.json({
      id: uuidv4(),
      status: 'success',
      outputs: {
        messages: [{
          type: 'ai',
          content: message,
          additional_kwargs: {
            risk_score: result.riskReport?.overallScore,
            risk_level: result.riskReport?.riskLevel,
          },
        }],
      },
      metadata: {
        protocol: result.riskReport?.protocol,
        risk_score: result.riskReport?.overallScore,
      },
    });
  } catch (error) {
    console.error('❌ Error:', error);
    res.status(500).json({ error: (error as Error).message });
  }
});

// --- Info & Health ---

app.get('/info', (req, res) => {
  res.json({
    version: '1.0.0',
    name: 'DeFi Risk Scanner',
    description: 'Analyzes DeFi protocol security risks',
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', version: 'LangGraph-Std-1.0' });
});

// Start server
app.listen(config.port, () => {
  console.log(`🔍 DeFi Risk Scanner running on port ${config.port}`);
});
