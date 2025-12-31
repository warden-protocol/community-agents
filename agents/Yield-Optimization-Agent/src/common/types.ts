/**
 * Common types used across the yield agent
 */

export type AgentResponse = {
  question: string;
  response: unknown;
};

export interface ValidationResult {
  valid: boolean;
  error?: string;
  errors?: string[];
  warnings?: string[];
  data?: unknown;
  requiredFields?: string[];
  supportedChains?: Array<{ id: number; name: string }>;
  suggestion?: string;
}

export interface SupportedChain {
  id: number;
  name: string;
  chainName: string;
}

export const SUPPORTED_CHAINS: SupportedChain[] = [
  { id: 1, name: 'Ethereum', chainName: 'ethereum' },
  { id: 42161, name: 'Arbitrum', chainName: 'arbitrum-one' },
  { id: 10, name: 'Optimism', chainName: 'optimistic-ethereum' },
  { id: 137, name: 'Polygon', chainName: 'polygon-pos' },
  { id: 8453, name: 'Base', chainName: 'base' },
  { id: 43114, name: 'Avalanche', chainName: 'avalanche' },
  { id: 56, name: 'BNB Chain', chainName: 'binance-smart-chain' },
];

export function getChainById(chainId: number): SupportedChain | undefined {
  return SUPPORTED_CHAINS.find((chain) => chain.id === chainId);
}

export function getChainByName(chainName: string): SupportedChain | undefined {
  return SUPPORTED_CHAINS.find(
    (chain) =>
      chain.chainName.toLowerCase() === chainName.toLowerCase() ||
      chain.name.toLowerCase() === chainName.toLowerCase(),
  );
}

