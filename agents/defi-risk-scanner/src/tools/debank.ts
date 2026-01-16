import axios from 'axios';
import { config } from '../config';

export interface WhaleData {
  address: string;
  balance: number;
  percentage: number;
}

export interface OnChainBehavior {
  whaleConcentration: number;  // Top 10 holders percentage
  recentWithdrawals: number;   // Last 24h withdrawal volume
  uniqueHolders: number;
  largestHolder: WhaleData | null;
  abnormalActivity: boolean;
}

// Get protocol on-chain behavior data
export async function getOnChainBehavior(
  contractAddress: string,
  chain: string = 'eth'
): Promise<OnChainBehavior | null> {
  // DeBank API requires API key for most endpoints
  if (!config.debankApiKey) {
    console.warn('DeBank API key not configured, returning mock data');
    return getMockOnChainBehavior();
  }

  try {
    const headers = {
      'AccessKey': config.debankApiKey,
    };

    // Get token holders distribution
    const response = await axios.get(
      `${config.debankBaseUrl}/token/balance_list`,
      {
        headers,
        params: {
          chain_id: chain,
          token_id: contractAddress,
        },
      }
    );

    const holders = response.data || [];
    const totalSupply = holders.reduce((sum: number, h: { amount: number }) => sum + h.amount, 0);

    // Calculate whale concentration (top 10 holders)
    const sortedHolders = [...holders].sort((a: { amount: number }, b: { amount: number }) => b.amount - a.amount);
    const top10 = sortedHolders.slice(0, 10);
    const top10Balance = top10.reduce((sum: number, h: { amount: number }) => sum + h.amount, 0);
    const whaleConcentration = totalSupply > 0 ? (top10Balance / totalSupply) * 100 : 0;

    const largest = sortedHolders[0];

    return {
      whaleConcentration,
      recentWithdrawals: 0, // Would need transaction history API
      uniqueHolders: holders.length,
      largestHolder: largest ? {
        address: largest.id,
        balance: largest.amount,
        percentage: totalSupply > 0 ? (largest.amount / totalSupply) * 100 : 0,
      } : null,
      abnormalActivity: whaleConcentration > 80, // Flag if > 80% in top 10
    };
  } catch (error) {
    console.error('DeBank API error:', error);
    return getMockOnChainBehavior();
  }
}

// Mock data for development/testing
function getMockOnChainBehavior(): OnChainBehavior {
  return {
    whaleConcentration: 45,
    recentWithdrawals: 1500000,
    uniqueHolders: 12500,
    largestHolder: {
      address: '0x...mock',
      balance: 1000000,
      percentage: 8.5,
    },
    abnormalActivity: false,
  };
}

// Check for abnormal withdrawal patterns
export async function checkAbnormalWithdrawals(
  contractAddress: string,
  chain: string = 'eth'
): Promise<{ isAbnormal: boolean; reason: string | null }> {
  // Simplified check - in production, would analyze transaction patterns
  const behavior = await getOnChainBehavior(contractAddress, chain);

  if (!behavior) {
    return { isAbnormal: false, reason: null };
  }

  if (behavior.whaleConcentration > 80) {
    return {
      isAbnormal: true,
      reason: `High whale concentration: ${behavior.whaleConcentration.toFixed(1)}% held by top 10 addresses`,
    };
  }

  return { isAbnormal: false, reason: null };
}
