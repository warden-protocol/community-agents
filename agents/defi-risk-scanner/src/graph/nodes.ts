import { getProtocolTVL, searchProtocol, TVLData } from '../tools/defillama';
import { getAuditData, AuditData } from '../tools/certik';
import { getContractInfo, ContractInfo } from '../tools/etherscan';
import { getOnChainBehavior, OnChainBehavior } from '../tools/debank';
import { calculateRiskScore, RiskReport, RiskInputs } from '../models/risk_scorer';

// State interface for the graph
export interface ScannerState {
  // Input
  query: string;
  contractAddress?: string;

  // Intermediate data
  protocolSlug?: string;
  tvlData?: TVLData | null;
  auditData?: AuditData | null;
  contractInfo?: ContractInfo | null;
  onchainBehavior?: OnChainBehavior | null;

  // Output
  riskReport?: RiskReport;
  error?: string;
}

// Node 1: Parse input and identify protocol
export async function parseInputNode(state: ScannerState): Promise<Partial<ScannerState>> {
  const query = state.query.trim().toLowerCase();

  // Check if it's an Ethereum address
  if (query.startsWith('0x') && query.length === 42) {
    return {
      contractAddress: query,
      protocolSlug: undefined, // Will try to identify from contract
    };
  }

  // Try to find protocol by name
  const slug = await searchProtocol(query);

  if (!slug) {
    return {
      error: `Could not find protocol: ${state.query}. Try entering a contract address or exact protocol name.`,
    };
  }

  return { protocolSlug: slug };
}

// Node 2: Fetch TVL data from DeFiLlama
export async function fetchTVLNode(state: ScannerState): Promise<Partial<ScannerState>> {
  if (state.error) return {};
  if (!state.protocolSlug) return { tvlData: null };

  const tvlData = await getProtocolTVL(state.protocolSlug);
  return { tvlData };
}

// Node 3: Fetch audit data from Certik
export async function fetchAuditNode(state: ScannerState): Promise<Partial<ScannerState>> {
  if (state.error) return {};

  const searchTerm = state.protocolSlug || state.query;
  const auditData = await getAuditData(searchTerm);
  return { auditData };
}

// Node 4: Fetch contract info from Etherscan
export async function fetchContractNode(state: ScannerState): Promise<Partial<ScannerState>> {
  if (state.error) return {};
  if (!state.contractAddress) return { contractInfo: null };

  const contractInfo = await getContractInfo(state.contractAddress);
  return { contractInfo };
}

// Node 5: Fetch on-chain behavior from DeBank
export async function fetchOnchainNode(state: ScannerState): Promise<Partial<ScannerState>> {
  if (state.error) return {};
  if (!state.contractAddress) return { onchainBehavior: null };

  const onchainBehavior = await getOnChainBehavior(state.contractAddress);
  return { onchainBehavior };
}

// Node 6: Calculate risk score and generate report
export async function analyzeRiskNode(state: ScannerState): Promise<Partial<ScannerState>> {
  if (state.error) return {};

  const inputs: RiskInputs = {
    tvlData: state.tvlData || null,
    auditData: state.auditData || null,
    contractInfo: state.contractInfo || null,
    onchainBehavior: state.onchainBehavior || null,
  };

  const riskReport = calculateRiskScore(inputs);
  return { riskReport };
}

// Node 7: Format output for response
export async function formatOutputNode(state: ScannerState): Promise<Partial<ScannerState>> {
  // This node just passes through - formatting happens in the response
  return {};
}

// Check if we should continue or stop
export function shouldContinue(state: ScannerState): string {
  if (state.error) {
    return 'error';
  }
  return 'continue';
}
