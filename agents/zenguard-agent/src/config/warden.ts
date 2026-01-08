import { WardenAgentKit } from "@wardenprotocol/warden-agent-kit-core";
import dotenv from "dotenv";
dotenv.config();

// Initializes Warden Kit with graceful fallback
export const setupWardenKit = async () => {
  const privateKey = process.env.WARDEN_PRIVATE_KEY;
  if (!privateKey) {
    console.warn(
      "⚠️ WARDEN_PRIVATE_KEY not found in .env. Running in MOCK MODE (Simulation).",
    );
    return null;
  }

  try {
    return new WardenAgentKit({
      // FIX: Cast to any to allow our "mock_demo_key" to pass TypeScript validation
      privateKeyOrAccount: privateKey as any,
    });
  } catch (e) {
    // This catch block is expected when using a mock key!
    // It returns null, which triggers the simulation logic in the tool.
    return null;
  }
};
