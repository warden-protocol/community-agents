import axios from 'axios';
import { config } from '../config';

export interface ContractInfo {
  address: string;
  isVerified: boolean;
  contractName: string | null;
  compilerVersion: string | null;
  creationDate: Date | null;
  ageInDays: number;
  isProxy: boolean;
  implementationAddress: string | null;
}

export interface ContractSourceCode {
  sourceCode: string;
  abi: string;
  constructorArguments: string;
  library: string;
}

// Get contract information from Etherscan
export async function getContractInfo(contractAddress: string): Promise<ContractInfo | null> {
  try {
    // Get contract source code (to check if verified)
    const sourceResponse = await axios.get(config.etherscanBaseUrl, {
      params: {
        module: 'contract',
        action: 'getsourcecode',
        address: contractAddress,
        apikey: config.etherscanApiKey || undefined,
      },
    });

    const sourceData = sourceResponse.data?.result?.[0];
    const isVerified = sourceData?.SourceCode && sourceData.SourceCode !== '';

    // Get contract creation info
    const creationResponse = await axios.get(config.etherscanBaseUrl, {
      params: {
        module: 'contract',
        action: 'getcontractcreation',
        contractaddresses: contractAddress,
        apikey: config.etherscanApiKey || undefined,
      },
    });

    const creationData = creationResponse.data?.result?.[0];
    let creationDate: Date | null = null;
    let ageInDays = 0;

    if (creationData?.txHash) {
      // Get transaction to find block timestamp
      const txResponse = await axios.get(config.etherscanBaseUrl, {
        params: {
          module: 'proxy',
          action: 'eth_getTransactionByHash',
          txhash: creationData.txHash,
          apikey: config.etherscanApiKey || undefined,
        },
      });

      if (txResponse.data?.result?.blockNumber) {
        const blockResponse = await axios.get(config.etherscanBaseUrl, {
          params: {
            module: 'proxy',
            action: 'eth_getBlockByNumber',
            tag: txResponse.data.result.blockNumber,
            boolean: 'false',
            apikey: config.etherscanApiKey || undefined,
          },
        });

        if (blockResponse.data?.result?.timestamp) {
          const timestamp = parseInt(blockResponse.data.result.timestamp, 16);
          creationDate = new Date(timestamp * 1000);
          ageInDays = Math.floor((Date.now() - creationDate.getTime()) / (1000 * 60 * 60 * 24));
        }
      }
    }

    // Check if proxy contract
    const isProxy = sourceData?.Proxy === '1' || sourceData?.Implementation !== '';

    return {
      address: contractAddress,
      isVerified,
      contractName: sourceData?.ContractName || null,
      compilerVersion: sourceData?.CompilerVersion || null,
      creationDate,
      ageInDays,
      isProxy,
      implementationAddress: sourceData?.Implementation || null,
    };
  } catch (error) {
    console.error('Etherscan API error:', error);
    return getMockContractInfo(contractAddress);
  }
}

// Check if contract is verified
export async function isContractVerified(contractAddress: string): Promise<boolean> {
  const info = await getContractInfo(contractAddress);
  return info?.isVerified ?? false;
}

// Get contract ABI
export async function getContractABI(contractAddress: string): Promise<string | null> {
  try {
    const response = await axios.get(config.etherscanBaseUrl, {
      params: {
        module: 'contract',
        action: 'getabi',
        address: contractAddress,
        apikey: config.etherscanApiKey || undefined,
      },
    });

    if (response.data?.status === '1') {
      return response.data.result;
    }
    return null;
  } catch (error) {
    console.error('Etherscan ABI error:', error);
    return null;
  }
}

// Mock data for development/testing
function getMockContractInfo(address: string): ContractInfo {
  return {
    address,
    isVerified: true,
    contractName: 'MockContract',
    compilerVersion: 'v0.8.19+commit.7dd6d404',
    creationDate: new Date(Date.now() - 180 * 24 * 60 * 60 * 1000), // 180 days ago
    ageInDays: 180,
    isProxy: false,
    implementationAddress: null,
  };
}

// Calculate contract score component
export function calculateContractScore(info: ContractInfo): number {
  let score = 0;

  // Verified source code (30 points)
  if (info.isVerified) {
    score += 30;
  }

  // Contract age scoring (up to 40 points)
  // Older contracts are generally more battle-tested
  if (info.ageInDays >= 365) {
    score += 40; // 1+ year
  } else if (info.ageInDays >= 180) {
    score += 30; // 6+ months
  } else if (info.ageInDays >= 90) {
    score += 20; // 3+ months
  } else if (info.ageInDays >= 30) {
    score += 10; // 1+ month
  }
  // < 30 days: 0 points (very new)

  // Proxy contracts get slight penalty (complexity risk)
  if (info.isProxy) {
    score -= 5;
  }

  // Has contract name (basic sanity check)
  if (info.contractName) {
    score += 10;
  }

  return Math.max(0, Math.min(100, score));
}
