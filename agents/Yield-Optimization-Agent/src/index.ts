/**
 * Yield Optimization Agent
 * Main entry point for the agent
 */

import dotenv from "dotenv";
import { runYieldAgent } from "./agent";

// Load environment variables
dotenv.config();

/**
 * Example usage of the yield agent
 */
async function main(): Promise<void> {
  const questions = [
    // Test Quick Mode: All parameters provided (Ethereum has protocols)
    "Deposit 100 USDC (0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48) on Ethereum to Aave for user 0x2a360629a7332e468b2d30dD0f76e5c41D6cEaA9",
    // "Find staking opportunities for USDC", // Scenario 1: Token symbol - should show all chains
    // "Find staking opportunities for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // Scenario 2: Address without chain - should error
    // "Find staking opportunities for 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 on Ethereum on morpho", // Scenario 3: Address with chain - should process directly
  ];

  try {
    const results = await runYieldAgent(questions, {
      modelName: "gpt-4o-mini",
      temperature: 0,
    });

    console.log("\n=== Agent Results ===\n");
    results.forEach((result, index) => {
      console.log(`Question ${index + 1}: ${result.question}`);
      console.log(`Response:`, JSON.stringify(result.response, null, 2));
      console.log("\n---\n");
    });
  } catch (error) {
    console.error("Error running agent:", error);
    process.exit(1);
  }
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}

export { runYieldAgent } from "./agent";
export * from "./agent";
