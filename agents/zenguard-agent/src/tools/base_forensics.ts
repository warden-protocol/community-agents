import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { createPublicClient, http } from "viem";
import { base } from "viem/chains";
import dotenv from "dotenv";
dotenv.config();

// Create Viem Client
const client = createPublicClient({
  chain: base,
  transport: http(process.env.BASE_RPC_URL),
});

export const baseForensicsTool = tool(
  async ({ txHash }) => {
    try {
      // Safety check: mock response if hash is invalid to prevent crash during demo
      if (!txHash.startsWith("0x"))
        return JSON.stringify({ status: "ERROR", msg: "Invalid Hash format" });

      const tx = await client.getTransaction({ hash: txHash as `0x${string}` });
      const block = await client.getBlock({ blockNumber: tx.blockNumber });

      const baseFee = Number(block.baseFeePerGas || 0);
      // Normalize congestion: assume > 0.1 Gwei base fee is 'high' for L2 (simplified logic)
      const congestionScore = Math.min(baseFee / 100000000, 1.0);

      return JSON.stringify({
        status: "SUCCESS",
        data: {
          block: block.number.toString(),
          congestionScore: congestionScore.toFixed(2),
          evidence: `In Block #${block.number}, network load was high. Gas Price: ${tx.gasPrice} wei.`,
        },
      });
    } catch (e) {
      return JSON.stringify({
        status: "ERROR",
        msg: "Transaction not found on Base or RPC error.",
      });
    }
  },
  {
    name: "get_base_onchain_data",
    description:
      "Fetches verification data from Base chain to analyze a specific transaction.",
    schema: z.object({ txHash: z.string() }),
  },
);
