/**
 * Agent-specific types and interfaces
 */

/**
 * Token input from user
 */
export interface TokenInput {
  token: string; // Token name, symbol, or address
  chainId?: number; // REQUIRED if token is an address
  chainName?: string; // Alternative to chainId (e.g., "ethereum", "arbitrum")
}

/**
 * Quick mode input (all parameters in one command)
 */
export interface QuickModeInput {
  token: string; // Address or name
  chain: string | number; // Chain name or ID
  protocol: string; // Protocol name/identifier
  amount?: string; // Optional amount
}

/**
 * Token information
 */
export interface TokenInfo {
  name: string;
  symbol: string;
  address: string; // Contract address
  chain: string; // Chain name
  chainId: number; // Chain ID
  marketCap?: number; // USD market cap
  price?: number; // Current USD price
  decimals: number;
  logoURI?: string;
  description?: string; // Token description/news
  priceChange24h?: number; // 24h price change %
  volume24h?: number; // 24h trading volume
  coingeckoId?: string; // CoinGecko ID for further lookups
  allChains?: Array<{
    // All chains where token exists
    chainId: number;
    chainName: string;
    address: string;
  }>;
  verified?: boolean; // Whether token is verified on CoinGecko
  warnings?: string[]; // Any warnings about the token
}

/**
 * Protocol vault information
 */
export interface ProtocolVault {
  address: string; // Vault contract address
  name: string; // Vault name
  symbol: string; // Vault token symbol
  protocol: string; // Protocol name (e.g., "aave", "compound")
  chainId: number; // Chain ID
  chainName: string; // Human-readable chain name
  apy: number; // Annual Percentage Yield
  tvl: number; // Total Value Locked (USD)
  underlyingTokens: Array<{
    // Underlying tokens
    address: string;
    symbol: string;
    name: string;
  }>;
  logosUri?: string[]; // Protocol logo URLs
  project?: string; // Project identifier
}

/**
 * Safety score for a protocol
 */
export interface SafetyScore {
  overall: "very_safe" | "safe" | "moderate" | "risky";
  score: number; // 0-100
  factors: {
    tvl: { score: number; level: string };
    protocol: { score: number; level: string; reputation: string };
    audits: { score: number; level: string; auditCount: number };
    history: { score: number; level: string };
  };
  warnings?: string[]; // Any safety warnings
  recommendations?: string[]; // Safety recommendations
}

/**
 * Protocol with safety evaluation
 */
export interface ProtocolWithSafety extends ProtocolVault {
  safetyScore: SafetyScore;
}

/**
 * Approval transaction
 */
export interface ApprovalTransaction {
  to: string; // Token contract address
  data: string; // Encoded approve() call data
  value: string; // Always "0" for ERC20 approvals
  gasLimit?: string;
  gasPrice?: string;
  chainId: number;
  tokenAddress: string; // Token being approved
  spender: string; // Protocol/vault address to approve
  amount: string; // Amount to approve (in wei)
  type: "approve";
  safetyWarning: string; // Mandatory safety warning
}

/**
 * Deposit transaction
 */
export interface DepositTransaction {
  to: string; // Contract address to interact with
  data: string; // Encoded transaction data
  value: string; // ETH value (if native token)
  gasLimit?: string; // Estimated gas limit
  gasPrice?: string; // Gas price
  chainId: number; // Chain ID
  protocol: string; // Protocol name
  action: "deposit" | "stake"; // Action type
  tokenIn: {
    address: string;
    symbol: string;
    amount: string; // Human-readable amount
    amountWei: string; // Amount in wei
  };
  tokenOut: {
    address: string;
    symbol: string;
  };
  estimatedGas?: string; // Estimated gas cost in USD
  slippage?: number; // Slippage tolerance
  type: "deposit";
  safetyWarning: string; // Mandatory safety warning
}

/**
 * Transaction bundle (approval + deposit if needed)
 */
export interface TransactionBundle {
  approvalTransaction?: ApprovalTransaction; // Required if approval needed
  depositTransaction: DepositTransaction; // Always present
  executionOrder: ("approve" | "deposit")[]; // Order of execution
  totalGasEstimate?: string; // Combined gas estimate
}

/**
 * Approval check result
 */
export interface ApprovalCheckResult {
  approvalNeeded: boolean;
  currentAllowance?: bigint;
  requiredAmount?: bigint;
  approvalTransaction?: ApprovalTransaction;
  error?: string;
  message: string;
}
