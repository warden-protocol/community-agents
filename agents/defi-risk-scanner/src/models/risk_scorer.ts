import { config, getRiskLevel, RiskLevel } from '../config';
import { TVLData } from '../tools/defillama';
import { AuditData, calculateAuditScore } from '../tools/certik';
import { ContractInfo, calculateContractScore } from '../tools/etherscan';
import { OnChainBehavior } from '../tools/debank';

export interface RiskComponents {
  contractScore: number;
  tvlScore: number;
  teamScore: number;
  onchainScore: number;
}

export interface RiskWarning {
  severity: 'critical' | 'warning' | 'info';
  message: string;
  category: string;
}

export interface RiskReport {
  protocol: string;
  overallScore: number;
  riskLevel: RiskLevel;
  components: RiskComponents;
  warnings: RiskWarning[];
  summary: string;
  timestamp: string;
}

export interface RiskInputs {
  tvlData: TVLData | null;
  auditData: AuditData | null;
  contractInfo: ContractInfo | null;
  onchainBehavior: OnChainBehavior | null;
  teamInfo?: {
    isDoxxed: boolean;
    hasPublicTeam: boolean;
  };
}

// Calculate TVL-related risk score
function calculateTVLScore(tvl: TVLData | null): { score: number; warnings: RiskWarning[] } {
  const warnings: RiskWarning[] = [];

  if (!tvl) {
    return {
      score: 30,
      warnings: [{
        severity: 'warning',
        message: 'Unable to fetch TVL data',
        category: 'tvl',
      }],
    };
  }

  let score = 50; // Base score

  // TVL size factor (larger = generally safer)
  if (tvl.tvl >= 1_000_000_000) {
    score += 30; // $1B+
  } else if (tvl.tvl >= 100_000_000) {
    score += 25; // $100M+
  } else if (tvl.tvl >= 10_000_000) {
    score += 15; // $10M+
  } else if (tvl.tvl >= 1_000_000) {
    score += 5; // $1M+
  } else {
    warnings.push({
      severity: 'warning',
      message: `Low TVL: $${(tvl.tvl / 1_000_000).toFixed(2)}M`,
      category: 'tvl',
    });
  }

  // TVL change penalties
  if (tvl.tvlChange24h < -20) {
    score -= 20;
    warnings.push({
      severity: 'critical',
      message: `TVL dropped ${Math.abs(tvl.tvlChange24h).toFixed(1)}% in 24h`,
      category: 'tvl',
    });
  } else if (tvl.tvlChange24h < -10) {
    score -= 10;
    warnings.push({
      severity: 'warning',
      message: `TVL dropped ${Math.abs(tvl.tvlChange24h).toFixed(1)}% in 24h`,
      category: 'tvl',
    });
  }

  if (tvl.tvlChange7d < -30) {
    score -= 15;
    warnings.push({
      severity: 'critical',
      message: `TVL dropped ${Math.abs(tvl.tvlChange7d).toFixed(1)}% in 7d`,
      category: 'tvl',
    });
  }

  // Multi-chain bonus (diversification)
  if (tvl.chains.length >= 5) {
    score += 10;
  } else if (tvl.chains.length >= 3) {
    score += 5;
  }

  return { score: Math.max(0, Math.min(100, score)), warnings };
}

// Calculate team-related risk score
function calculateTeamScore(teamInfo?: { isDoxxed: boolean; hasPublicTeam: boolean }): {
  score: number;
  warnings: RiskWarning[];
} {
  const warnings: RiskWarning[] = [];

  if (!teamInfo) {
    warnings.push({
      severity: 'info',
      message: 'Team information not available',
      category: 'team',
    });
    return { score: 50, warnings };
  }

  let score = 30; // Base score for anonymous team

  if (teamInfo.isDoxxed) {
    score += 50;
  } else {
    warnings.push({
      severity: 'warning',
      message: 'Team is anonymous',
      category: 'team',
    });
  }

  if (teamInfo.hasPublicTeam) {
    score += 20;
  }

  return { score: Math.max(0, Math.min(100, score)), warnings };
}

// Calculate on-chain behavior score
function calculateOnchainScore(behavior: OnChainBehavior | null): {
  score: number;
  warnings: RiskWarning[];
} {
  const warnings: RiskWarning[] = [];

  if (!behavior) {
    return {
      score: 50,
      warnings: [{
        severity: 'info',
        message: 'On-chain behavior data not available',
        category: 'onchain',
      }],
    };
  }

  let score = 70; // Base score

  // Whale concentration penalty
  if (behavior.whaleConcentration > 80) {
    score -= 40;
    warnings.push({
      severity: 'critical',
      message: `Extreme whale concentration: ${behavior.whaleConcentration.toFixed(1)}% in top 10`,
      category: 'onchain',
    });
  } else if (behavior.whaleConcentration > 60) {
    score -= 20;
    warnings.push({
      severity: 'warning',
      message: `High whale concentration: ${behavior.whaleConcentration.toFixed(1)}% in top 10`,
      category: 'onchain',
    });
  } else if (behavior.whaleConcentration > 40) {
    score -= 10;
  }

  // Holder count bonus
  if (behavior.uniqueHolders >= 10000) {
    score += 15;
  } else if (behavior.uniqueHolders >= 1000) {
    score += 10;
  } else if (behavior.uniqueHolders < 100) {
    score -= 10;
    warnings.push({
      severity: 'warning',
      message: `Very few unique holders: ${behavior.uniqueHolders}`,
      category: 'onchain',
    });
  }

  // Abnormal activity flag
  if (behavior.abnormalActivity) {
    score -= 20;
    warnings.push({
      severity: 'critical',
      message: 'Abnormal on-chain activity detected',
      category: 'onchain',
    });
  }

  return { score: Math.max(0, Math.min(100, score)), warnings };
}

// Main risk calculation function
export function calculateRiskScore(inputs: RiskInputs): RiskReport {
  const warnings: RiskWarning[] = [];

  // Calculate component scores
  const contractResult = inputs.contractInfo
    ? { score: calculateContractScore(inputs.contractInfo), warnings: [] as RiskWarning[] }
    : { score: 20, warnings: [{ severity: 'warning' as const, message: 'Contract info unavailable', category: 'contract' }] };

  const auditResult = inputs.auditData
    ? { score: calculateAuditScore(inputs.auditData), warnings: [] as RiskWarning[] }
    : { score: 10, warnings: [{ severity: 'critical' as const, message: 'No audit information found', category: 'contract' }] };

  // Combined contract score (contract info + audit)
  const contractScore = (contractResult.score + auditResult.score) / 2;

  // Add audit-specific warnings
  if (inputs.auditData && !inputs.auditData.isAudited) {
    warnings.push({
      severity: 'critical',
      message: 'Protocol has NOT been audited',
      category: 'contract',
    });
  }

  const tvlResult = calculateTVLScore(inputs.tvlData);
  const teamResult = calculateTeamScore(inputs.teamInfo);
  const onchainResult = calculateOnchainScore(inputs.onchainBehavior);

  // Aggregate warnings
  warnings.push(...contractResult.warnings);
  warnings.push(...auditResult.warnings);
  warnings.push(...tvlResult.warnings);
  warnings.push(...teamResult.warnings);
  warnings.push(...onchainResult.warnings);

  // Calculate weighted overall score
  const weights = config.riskWeights;
  const overallScore =
    contractScore * weights.contract +
    tvlResult.score * weights.tvl +
    teamResult.score * weights.team +
    onchainResult.score * weights.onchain;

  const riskLevel = getRiskLevel(overallScore);

  // Generate summary
  const summary = generateSummary(overallScore, riskLevel, warnings);

  return {
    protocol: inputs.tvlData?.protocol || 'Unknown Protocol',
    overallScore: Math.round(overallScore),
    riskLevel,
    components: {
      contractScore: Math.round(contractScore),
      tvlScore: Math.round(tvlResult.score),
      teamScore: Math.round(teamResult.score),
      onchainScore: Math.round(onchainResult.score),
    },
    warnings: warnings.sort((a, b) => {
      const severityOrder = { critical: 0, warning: 1, info: 2 };
      return severityOrder[a.severity] - severityOrder[b.severity];
    }),
    summary,
    timestamp: new Date().toISOString(),
  };
}

// Generate human-readable summary
function generateSummary(score: number, level: RiskLevel, warnings: RiskWarning[]): string {
  const criticalCount = warnings.filter(w => w.severity === 'critical').length;
  const warningCount = warnings.filter(w => w.severity === 'warning').length;

  let summary = `Risk Score: ${Math.round(score)}/100 (${level} RISK). `;

  if (level === 'HIGH') {
    summary += 'This protocol presents significant risks. ';
  } else if (level === 'MEDIUM') {
    summary += 'This protocol has moderate risk factors. ';
  } else {
    summary += 'This protocol appears relatively safe. ';
  }

  if (criticalCount > 0) {
    summary += `Found ${criticalCount} critical issue(s). `;
  }
  if (warningCount > 0) {
    summary += `Found ${warningCount} warning(s). `;
  }

  summary += 'Always DYOR before investing.';

  return summary;
}
