/**
 * Safety evaluation service
 * Evaluates protocol safety based on TVL, reputation, audits, and history
 */

import { SafetyScore, ProtocolVault, ProtocolWithSafety } from './types';
import { Logger } from '../common/logger';
import { retryWithBackoff } from '../common/utils';

const logger = new Logger('SafetyService');

/**
 * Well-known trusted protocols
 */
const TRUSTED_PROTOCOLS = [
  'aave',
  'compound',
  'lido',
  'yearn',
  'uniswap',
  'curve',
  'balancer',
  'makerdao',
  'convex',
  'frax',
  'morpho',
  'spark',
];

/**
 * Evaluate protocol safety score
 */
export async function evaluateProtocolSafety(
  protocol: ProtocolVault,
): Promise<SafetyScore> {
  logger.info(`Evaluating safety for protocol ${protocol.protocol} on ${protocol.chainName}`);

  const factors = {
    tvl: evaluateTVL(protocol.tvl),
    protocol: evaluateProtocolReputation(protocol.protocol),
    audits: await evaluateAudits(protocol.protocol),
    history: evaluateHistory(protocol.protocol),
  };

  // Calculate overall score (weighted average)
  const weights = {
    tvl: 0.4,
    protocol: 0.3,
    audits: 0.2,
    history: 0.1,
  };

  const overallScore =
    factors.tvl.score * weights.tvl +
    factors.protocol.score * weights.protocol +
    factors.audits.score * weights.audits +
    factors.history.score * weights.history;

  // Determine overall safety level
  let overall: 'very_safe' | 'safe' | 'moderate' | 'risky';
  if (overallScore >= 80) {
    overall = 'very_safe';
  } else if (overallScore >= 60) {
    overall = 'safe';
  } else if (overallScore >= 40) {
    overall = 'moderate';
  } else {
    overall = 'risky';
  }

  const warnings: string[] = [];
  const recommendations: string[] = [];

  // Add warnings based on factors
  if (factors.tvl.level === 'low') {
    warnings.push(`Low TVL ($${formatTVL(protocol.tvl)}) - protocol may be less established`);
  }

  if (factors.protocol.level === 'unknown') {
    warnings.push('Protocol not in trusted list - exercise caution');
    recommendations.push('Research the protocol thoroughly before investing');
  }

  if (factors.audits.auditCount === 0) {
    warnings.push('No audit information found');
    recommendations.push('Verify protocol has been audited before investing');
  }

  if (overall === 'risky') {
    warnings.push('Overall safety score indicates high risk');
    recommendations.push('Consider using smaller amounts or more established protocols');
  }

  return {
    overall,
    score: Math.round(overallScore),
    factors,
    warnings: warnings.length > 0 ? warnings : undefined,
    recommendations: recommendations.length > 0 ? recommendations : undefined,
  };
}

/**
 * Evaluate TVL factor
 */
function evaluateTVL(tvl: number): { score: number; level: string } {
  if (tvl >= 100_000_000) {
    // > $100M
    return { score: 100, level: 'very_high' };
  } else if (tvl >= 10_000_000) {
    // $10M - $100M
    return { score: 75, level: 'high' };
  } else if (tvl >= 1_000_000) {
    // $1M - $10M
    return { score: 50, level: 'medium' };
  } else if (tvl >= 100_000) {
    // $100K - $1M
    return { score: 30, level: 'low' };
  } else {
    // < $100K
    return { score: 10, level: 'very_low' };
  }
}

/**
 * Evaluate protocol reputation
 */
function evaluateProtocolReputation(protocolName: string): {
  score: number;
  level: string;
  reputation: string;
} {
  const normalizedName = protocolName.toLowerCase().replace(/[^a-z0-9]/g, '');

  // Check if protocol is in trusted list
  const isTrusted = TRUSTED_PROTOCOLS.some(
    (trusted) => normalizedName.includes(trusted) || trusted.includes(normalizedName),
  );

  if (isTrusted) {
    return {
      score: 100,
      level: 'trusted',
      reputation: 'Well-established and trusted protocol',
    };
  }

  // Check for known risky patterns
  const riskyPatterns = ['test', 'demo', 'experimental'];
  const hasRiskyPattern = riskyPatterns.some((pattern) => normalizedName.includes(pattern));

  if (hasRiskyPattern) {
    return {
      score: 20,
      level: 'risky',
      reputation: 'Protocol name suggests experimental or test version',
    };
  }

  // Unknown protocol
  return {
    score: 50,
    level: 'unknown',
    reputation: 'Protocol not in trusted list - research recommended',
  };
}

/**
 * Evaluate audit status
 * Note: In production, this would fetch from DefiLlama or audit databases
 */
async function evaluateAudits(protocolName: string): Promise<{
  score: number;
  level: string;
  auditCount: number;
}> {
  try {
    // Try to fetch from DefiLlama API
    const protocolId = protocolName.toLowerCase().replace(/[^a-z0-9]/g, '-');
    const url = `https://api.llama.fi/protocol/${protocolId}`;

    try {
      const response = await retryWithBackoff(async () => {
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      });

      // DefiLlama protocol data might have audit information
      // For now, we'll assume if protocol exists in DefiLlama, it has some level of verification
      const hasData = response && typeof response === 'object';

      if (hasData) {
        return {
          score: 80,
          level: 'verified',
          auditCount: 1, // Assume at least one audit if in DefiLlama
        };
      }
    } catch (error) {
      logger.debug(`Failed to fetch audit data from DefiLlama: ${error}`);
    }

    // Default: no audit information found
    return {
      score: 30,
      level: 'unknown',
      auditCount: 0,
    };
  } catch (error) {
    logger.warn(`Error evaluating audits for ${protocolName}:`, error);
    return {
      score: 30,
      level: 'unknown',
      auditCount: 0,
    };
  }
}

/**
 * Evaluate historical performance
 * Note: In production, this would check for security incidents, hacks, etc.
 */
function evaluateHistory(protocolName: string): { score: number; level: string } {
  // Known protocols with good history get higher scores
  const normalizedName = protocolName.toLowerCase();
  const trustedProtocols = ['aave', 'compound', 'lido', 'yearn', 'uniswap'];

  const isTrusted = trustedProtocols.some((trusted) => normalizedName.includes(trusted));

  if (isTrusted) {
    return {
      score: 90,
      level: 'excellent',
    };
  }

  // Unknown protocols get medium score (no negative history known)
  return {
    score: 60,
    level: 'unknown',
  };
}

/**
 * Add safety scores to protocols
 * @param protocols - Protocols to evaluate
 * @param maxProtocols - Maximum number of protocols to evaluate (default: 30)
 */
export async function addSafetyScores(
  protocols: ProtocolVault[],
  maxProtocols: number = 30,
): Promise<ProtocolWithSafety[]> {
  // Pre-filter by TVL before evaluation to save API credits
  const protocolsToEvaluate = protocols
    .sort((a, b) => b.tvl - a.tvl)
    .slice(0, maxProtocols);

  logger.info(`Adding safety scores to ${protocolsToEvaluate.length} protocols (filtered from ${protocols.length} total)`);

  const protocolsWithSafety: ProtocolWithSafety[] = [];

  // Evaluate protocols in parallel (with limit to avoid rate limits)
  const batchSize = 5;
  for (let i = 0; i < protocolsToEvaluate.length; i += batchSize) {
    const batch = protocolsToEvaluate.slice(i, i + batchSize);
    const evaluations = await Promise.all(
      batch.map((protocol) =>
        evaluateProtocolSafety(protocol).catch((error) => {
          logger.warn(`Failed to evaluate safety for ${protocol.protocol}:`, error);
          // Return default risky score on error
          return {
            overall: 'risky' as const,
            score: 20,
            factors: {
              tvl: { score: 20, level: 'unknown' },
              protocol: { score: 20, level: 'unknown', reputation: 'unknown' },
              audits: { score: 20, level: 'unknown', auditCount: 0 },
              history: { score: 20, level: 'unknown' },
            },
            warnings: ['Could not evaluate safety - exercise caution'],
          };
        }),
      ),
    );

    for (let j = 0; j < batch.length; j++) {
      protocolsWithSafety.push({
        ...batch[j],
        safetyScore: evaluations[j],
      });
    }
  }

  return protocolsWithSafety;
}

/**
 * Sort protocols by safety and yield
 */
export function sortProtocolsBySafetyAndYield(
  protocols: ProtocolWithSafety[],
): ProtocolWithSafety[] {
  return [...protocols].sort((a, b) => {
    // First sort by safety score (higher is better)
    const safetyDiff = b.safetyScore.score - a.safetyScore.score;

    // If safety scores are close (within 10 points), prefer higher APY
    if (Math.abs(safetyDiff) < 10) {
      return b.apy - a.apy;
    }

    return safetyDiff;
  });
}

/**
 * Format TVL for display
 */
function formatTVL(tvl: number): string {
  if (tvl >= 1_000_000_000) {
    return `$${(tvl / 1_000_000_000).toFixed(2)}B`;
  } else if (tvl >= 1_000_000) {
    return `$${(tvl / 1_000_000).toFixed(2)}M`;
  } else if (tvl >= 1_000) {
    return `$${(tvl / 1_000).toFixed(2)}K`;
  }
  return `$${tvl.toFixed(2)}`;
}

