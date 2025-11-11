/**
 * Authentication handler for the Weather Agent
 *
 * This module implements API key authentication to protect the self-hosted agent.
 * Clients must provide a valid API key in the 'x-api-key' header to access the agent.
 */

import { Auth, HTTPException } from "@langchain/langgraph-sdk/auth";

/**
 * Authentication middleware that validates API keys
 *
 * Expected header: x-api-key: your-secret-api-key
 *
 * The valid API key should be set in the AGENT_API_KEY environment variable.
 * If no key is set, authentication is disabled (not recommended for production).
 */
export const auth = new Auth().authenticate(async (request: Request) => {
  const providedKey = request.headers.get("x-api-key");
  const validKey = process.env.AGENT_API_KEY;

  // If no API key is configured, allow access (development mode)
  if (!validKey) {
    console.warn("⚠️  WARNING: AGENT_API_KEY not set - authentication disabled!");
    return {
      identity: "unauthenticated",
      permissions: [],
      is_authenticated: true,
    };
  }

  // Validate the provided API key
  if (!providedKey || providedKey !== validKey) {
    throw new HTTPException(401, {
      message: "Invalid or missing API key. Please provide a valid 'x-api-key' header."
    });
  }

  // Authentication successful
  return {
    identity: "authenticated-user",
    permissions: [],
    is_authenticated: true,
  };
});
