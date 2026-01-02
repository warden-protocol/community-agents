/**
 * API Testing Script
 * Test the REST API endpoints
 */

import axios from "axios";

const API_BASE_URL = process.env.API_BASE_URL || "http://localhost:3000";

// Colors for console output
const colors = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  cyan: "\x1b[36m",
};

function log(color: string, message: string) {
  console.log(`${color}${message}${colors.reset}`);
}

async function testHealthCheck() {
  log(colors.blue, "\n=== Testing Health Check ===");
  try {
    const response = await axios.get(`${API_BASE_URL}/health`);
    log(colors.green, "✓ Health check passed");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Health check failed: ${error.message}`);
  }
}

async function testGetChains() {
  log(colors.blue, "\n=== Testing Get Supported Chains ===");
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/chains`);
    log(colors.green, `✓ Found ${response.data.count} supported chains`);
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Get chains failed: ${error.message}`);
  }
}

async function testSearchToken() {
  log(colors.blue, "\n=== Testing Token Search ===");
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/tokens/search`, {
      params: { query: "USDC" },
    });
    log(colors.green, `✓ Found ${response.data.count} tokens`);
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Token search failed: ${error.message}`);
  }
}

async function testGetTokenInfo() {
  log(colors.blue, "\n=== Testing Get Token Info ===");
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/tokens/info`, {
      params: {
        token: "USDC",
        chainId: 1,
      },
    });
    log(colors.green, "✓ Token info retrieved");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Get token info failed: ${error.message}`);
  }
}

async function testDiscoverProtocols() {
  log(colors.blue, "\n=== Testing Protocol Discovery ===");
  try {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/protocols/discover`,
      {
        tokenAddress: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // USDC on Ethereum
        chainId: 1,
        multiChain: false,
      }
    );
    log(
      colors.green,
      `✓ Found ${response.data.count} protocols (${response.data.totalFound} total)`
    );
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Protocol discovery failed: ${error.message}`);
    if (error.response) {
      console.log(JSON.stringify(error.response.data, null, 2));
    }
  }
}

async function testAgentQuery() {
  log(colors.blue, "\n=== Testing Agent Query ===");
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/agent/query`, {
      query: "Find staking opportunities for USDC on Ethereum",
      options: {
        modelName: "gpt-4o-mini",
        temperature: 0,
      },
    });
    log(colors.green, "✓ Agent query successful");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Agent query failed: ${error.message}`);
    if (error.response) {
      console.log(JSON.stringify(error.response.data, null, 2));
    }
  }
}

async function testQuickTransaction() {
  log(colors.blue, "\n=== Testing Quick Transaction ===");
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/agent/quick`, {
      tokenAddress: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", // USDC
      chainId: 1,
      protocolName: "aave",
      amount: "100",
      userAddress: "0x2a360629a7332e468b2d30dD0f76e5c41D6cEaA9",
    });
    log(colors.green, "✓ Quick transaction generated");
    console.log(JSON.stringify(response.data, null, 2));
  } catch (error: any) {
    log(colors.red, `✗ Quick transaction failed: ${error.message}`);
    if (error.response) {
      console.log(JSON.stringify(error.response.data, null, 2));
    }
  }
}

async function testInvalidRequest() {
  log(colors.blue, "\n=== Testing Invalid Request (Error Handling) ===");
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/agent/query`, {
      // Missing required 'query' field
      options: {},
    });
    log(colors.yellow, "⚠ Should have failed but didn't");
  } catch (error: any) {
    if (error.response && error.response.status === 400) {
      log(colors.green, "✓ Validation error handled correctly");
      console.log(JSON.stringify(error.response.data, null, 2));
    } else {
      log(colors.red, `✗ Unexpected error: ${error.message}`);
    }
  }
}

async function runAllTests() {
  log(colors.cyan, "\n╔════════════════════════════════════════╗");
  log(colors.cyan, "║   Yield Agent API Test Suite          ║");
  log(colors.cyan, "╚════════════════════════════════════════╝");

  log(colors.yellow, `\nTesting API at: ${API_BASE_URL}`);
  log(
    colors.yellow,
    "Make sure the server is running: yarn start:api\n"
  );

  // Run tests
  await testHealthCheck();
  await testGetChains();
  await testSearchToken();
  await testGetTokenInfo();
  await testDiscoverProtocols();
  await testInvalidRequest();

  // These tests require OpenAI API and may take longer
  log(colors.yellow, "\n⚠️  The following tests require API keys and may take longer...");
  
  const shouldRunLongTests = process.argv.includes("--full");
  
  if (shouldRunLongTests) {
    await testAgentQuery();
    await testQuickTransaction();
  } else {
    log(colors.cyan, "\nSkipping long-running tests. Use --full flag to run all tests.");
  }

  log(colors.cyan, "\n╔════════════════════════════════════════╗");
  log(colors.cyan, "║   Test Suite Complete!                 ║");
  log(colors.cyan, "╚════════════════════════════════════════╝\n");
}

// Run tests
runAllTests().catch((error) => {
  log(colors.red, `\n✗ Test suite failed: ${error.message}`);
  process.exit(1);
});

