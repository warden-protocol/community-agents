import { SystemMessage, HumanMessage } from "@langchain/core/messages";
import { routerModel, analystModel, therapistModel } from "../config/models";
import { calculateIrrationalityIndex, determineIntervention } from "../logic/risk_engine";
import { baseForensicsTool } from "../tools/base_forensics";
import { wardenProtectorTool } from "../tools/warden_protector";
import fs from 'fs';
import path from 'path';

// --- Node 1: Perception ---
export const perceptionNode = async (state: any) => {
  const lastMsg = state.messages[state.messages.length - 1].content;

  // 抓取最近 3 則訊息作為上下文
  const recentMessages = state.messages.slice(-3);
  const recentHistory = recentMessages.map((m: any) => {
    const role = m._getType?.() === 'human' ? 'User' : 'Agent';
    return `${role}: ${m.content}`;
  }).join("\n");

  // Context-aware prompt for better scam detection
  const prompt = `You are a sentiment analyzer for a crypto trading protection system.

CONVERSATION CONTEXT (Recent messages):
${recentHistory}

CURRENT INPUT TO ANALYZE: "${lastMsg}"

Analyze the user's CURRENT input considering the conversation context.

CRITICAL RULES:
1. If user is discussing/defending a scam (e.g., "guaranteed 3000% return", "let me transfer"), rate intensity HIGH (0.8+)
2. If user is just anxious but not taking dangerous action, rate intensity MODERATE (0.3-0.5)
3. If user asks neutral questions but context is dangerous (scam discussion), keep intensity MODERATE (0.5+)
4. If completely neutral conversation, rate intensity LOW (0.1-0.2)

Return ONLY a JSON object:
{ "sentimentScore": number (-1.0 to 1.0), "intensity": number (0.0 to 1.0), "hasTxHash": boolean, "txHash": null }`;

  const response = await routerModel.invoke([new HumanMessage(prompt)]);
  const rawContent = response.content.toString();

  let data;
  try {
    // Robust JSON Extraction: Find substring between first { and last }
    const jsonMatch = rawContent.match(/\{[\s\S]*\}/);
    const jsonStr = jsonMatch ? jsonMatch[0] : rawContent;
    data = JSON.parse(jsonStr);
  }
  catch (e) {
    console.warn("⚠️ JSON Parse Failed, using NEUTRAL defaults.");
    // FIX: Default to Neutral (0) instead of Fear (-0.5) to prevent false locks
    data = { sentimentScore: 0, intensity: 0, hasTxHash: false, txHash: null };
  }

  return { metrics: { sentimentScore: data.sentimentScore, sentimentIntensity: data.intensity, hasTxHash: data.hasTxHash, txHash: data.txHash } };
};

// --- Node 2: Analyst ---
export const analystNode = async (state: any) => {
  let volatility = 0.5;
  let evidence = "Market data unavailable.";

  if (state.metrics.hasTxHash && state.metrics.txHash) {
    const toolOutput = await baseForensicsTool.invoke({ txHash: state.metrics.txHash });
    const toolData = JSON.parse(toolOutput);
    if (toolData.status === "SUCCESS") {
      volatility = parseFloat(toolData.data.congestionScore);
      evidence = toolData.data.evidence;
    }
  }

  const riskIndex = calculateIrrationalityIndex(state.metrics.sentimentScore, state.metrics.sentimentIntensity, volatility);
  const level = determineIntervention(riskIndex);

  return {
    metrics: { ...state.metrics, marketVolatility: volatility, irrationalityIndex: riskIndex },
    interventionLevel: level,
    forensicData: evidence
  };
};

// --- Node 3: Protection ---
export const protectionNode = async (state: any) => {
  console.log("\n>>> 🛡️ HARD LOCK TRIGGERED. CALLING WARDEN PROTOCOL...");
  // Simulate Warden Action
  const result = await wardenProtectorTool.invoke({
    reason: `Irrationality Index ${state.metrics.irrationalityIndex}`,
    amount: "ALL"
  });
  return { wardenIntent: JSON.parse(result) };
};

// --- Node 4: Therapist ---
export const therapistNode = async (state: any) => {
  // Use __dirname for compatibility with both ts-node (src/) and compiled (dist/)
  const jsonPath = path.join(__dirname, '../knowledge/grok_curated.json');
  const grokData = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));

  // 注意：grokData 是物件不是陣列，需要取 interaction_examples
  const fewShots = grokData.interaction_examples.map((d: any) =>
    `${d.user_input}\nAI: ${d.ai_response}`
  ).join('\n\n');

  let actionInfo = "";
  if (state.interventionLevel === "HARD_LOCK" && state.wardenIntent) {
    actionInfo = `\n[SYSTEM ACTION] Zen Mode Activated. Warden Intent ID: ${state.wardenIntent.intentId}. Tell user assets are locked.`;
  }

  let systemPrompt = `You are ZenGuard.
  [STATUS] Risk: ${state.metrics.irrationalityIndex} (Level: ${state.interventionLevel})
  Evidence: ${state.forensicData}
  ${actionInfo}

  [INSTRUCTION]
  - If [SYSTEM ACTION], be firm: "I've locked your funds."
  - If risk is low, be helpful and conversational.
  - Respond in the same language as the user's input.
  - Style: Grok (Witty, Data-driven).

  [EXAMPLES]
  ${fewShots}`;

  const response = await therapistModel.invoke([new SystemMessage(systemPrompt), ...state.messages]);
  return { messages: [response] };
};
