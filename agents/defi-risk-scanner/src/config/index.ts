import dotenv from 'dotenv';

dotenv.config();

export const config = {
  port: process.env.PORT || 3000,

  // OpenAI
  openaiApiKey: process.env.OPENAI_API_KEY || '',

  // API Keys for data sources
  defiLlamaBaseUrl: 'https://api.llama.fi',
  debankApiKey: process.env.DEBANK_API_KEY || '',
  debankBaseUrl: 'https://pro-openapi.debank.com/v1',
  certikApiKey: process.env.CERTIK_API_KEY || '',
  certikBaseUrl: 'https://api.certik.com/api',
  etherscanApiKey: process.env.ETHERSCAN_API_KEY || '',
  etherscanBaseUrl: 'https://api.etherscan.io/api',

  // Risk scoring weights
  riskWeights: {
    contract: 0.40,  // Audit score, contract age, open source
    tvl: 0.30,       // TVL change rate, liquidity depth
    team: 0.15,      // Anonymous vs doxxed
    onchain: 0.15,   // Whale concentration, abnormal withdrawals
  },

  // Risk thresholds
  riskThresholds: {
    high: 50,    // < 50: High risk (red)
    medium: 70,  // 50-70: Medium risk (yellow)
    // > 70: Low risk (green)
  },
};

export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export function getRiskLevel(score: number): RiskLevel {
  if (score < config.riskThresholds.high) return 'HIGH';
  if (score < config.riskThresholds.medium) return 'MEDIUM';
  return 'LOW';
}

export function getRiskColor(level: RiskLevel): string {
  switch (level) {
    case 'HIGH': return 'red';
    case 'MEDIUM': return 'yellow';
    case 'LOW': return 'green';
  }
}
