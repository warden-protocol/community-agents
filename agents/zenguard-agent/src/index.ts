import { createZenGuardWorkflow } from "./graph/workflow";
import { HumanMessage, BaseMessage } from "@langchain/core/messages";
import * as readline from "readline";
import dotenv from "dotenv";
dotenv.config();

// Initialize CLI Interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});
const app = createZenGuardWorkflow();

// Conversation Memory: Maintain history across the session
const conversationHistory: BaseMessage[] = [];

console.log(`
🛡️  ZenGuard Agent (Base Edition) - System Online
=================================================
Type your message to chat. Type 'exit' to quit.
Type 'clear' to reset conversation history.

[Demo Hint] Try simulating panic:
"I lost everything on a rug pull! I'm going to leverage 100x to win it back!"
-------------------------------------------------
`);

const startChat = () => {
  rl.question("👤 User: ", async (input) => {
    if (input.toLowerCase() === "exit") {
      console.log("👋 ZenGuard shutting down.");
      rl.close();
      return;
    }

    if (input.toLowerCase() === "clear") {
      conversationHistory.length = 0;
      console.log("🧹 Conversation history cleared.\n");
      startChat();
      return;
    }

    if (!input.trim()) {
      startChat();
      return;
    }

    // Add user message to history
    conversationHistory.push(new HumanMessage(input));

    console.log("🤖 ZenGuard is thinking...");

    try {
      // Invoke with FULL conversation history
      const result = await app.invoke({ messages: conversationHistory });

      // Get the AI response (last message in result)
      const aiResponse = result.messages[result.messages.length - 1];

      // Add AI response to history for next turn
      conversationHistory.push(aiResponse);

      // Professional Diagnostics Dashboard
      console.log("\n--- 📊 Live Diagnostics ---");
      console.log(
        `Risk Index:       ${result.metrics.irrationalityIndex} / 1.0`,
      );
      console.log(`Intervention:     ${result.interventionLevel}`);
      console.log(`History Length:   ${conversationHistory.length} messages`);
      if (result.metrics.hasTxHash) {
        console.log(`Forensics:        TxHash Detected & Analyzed`);
      }
      if (result.wardenIntent) {
        console.log(
          `🛡️ WARDEN ACTION: Intent Created (ID: ${result.wardenIntent.intentId})`,
        );
        console.log(`                  Payload: Lock Assets -> 0x...dEaD`);
      }
      console.log("---------------------------\n");

      console.log(`🤖 ZenGuard: ${aiResponse.content}\n`);
    } catch (error) {
      console.error("❌ Error:", error);
    }

    startChat();
  });
};

startChat();
