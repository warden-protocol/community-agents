import axios from 'axios';
import { config } from '../config';

export interface AuditData {
  isAudited: boolean;
  auditor: string | null;
  auditDate: string | null;
  securityScore: number;  // 0-100
  findings: AuditFinding[];
  kycVerified: boolean;
}

export interface AuditFinding {
  severity: 'critical' | 'major' | 'medium' | 'minor' | 'informational';
  title: string;
  resolved: boolean;
}

// Get audit data from Certik
export async function getAuditData(projectName: string): Promise<AuditData | null> {
  // Certik API requires API key
  if (!config.certikApiKey) {
    console.warn('Certik API key not configured, returning mock data');
    return getMockAuditData(projectName);
  }

  try {
    const headers = {
      'Authorization': `Bearer ${config.certikApiKey}`,
    };

    const response = await axios.get(
      `${config.certikBaseUrl}/security-leaderboard`,
      {
        headers,
        params: { search: projectName },
      }
    );

    const project = response.data?.data?.[0];

    if (!project) {
      return getUnauditedData();
    }

    return {
      isAudited: true,
      auditor: 'Certik',
      auditDate: project.auditDate || null,
      securityScore: project.securityScore || 0,
      findings: parseFindings(project.findings),
      kycVerified: project.kycVerified || false,
    };
  } catch (error) {
    console.error('Certik API error:', error);
    return getMockAuditData(projectName);
  }
}

// Search for project in Certik leaderboard
export async function searchCertikProject(query: string): Promise<string | null> {
  if (!config.certikApiKey) {
    return null;
  }

  try {
    const headers = {
      'Authorization': `Bearer ${config.certikApiKey}`,
    };

    const response = await axios.get(
      `${config.certikBaseUrl}/security-leaderboard`,
      {
        headers,
        params: { search: query, limit: 1 },
      }
    );

    return response.data?.data?.[0]?.name || null;
  } catch (error) {
    console.error('Certik search error:', error);
    return null;
  }
}

// Parse audit findings into structured format
function parseFindings(findings: unknown[]): AuditFinding[] {
  if (!Array.isArray(findings)) return [];

  return findings.map((f: unknown) => {
    const finding = f as { severity?: string; title?: string; resolved?: boolean };
    return {
      severity: (finding.severity?.toLowerCase() || 'informational') as AuditFinding['severity'],
      title: finding.title || 'Unknown finding',
      resolved: finding.resolved ?? false,
    };
  });
}

// Return data for unaudited projects
function getUnauditedData(): AuditData {
  return {
    isAudited: false,
    auditor: null,
    auditDate: null,
    securityScore: 0,
    findings: [],
    kycVerified: false,
  };
}

// Mock data for development/testing
function getMockAuditData(projectName: string): AuditData {
  // Simulate some well-known protocols having audits
  const wellKnownProtocols = ['aave', 'uniswap', 'compound', 'curve', 'maker'];
  const isWellKnown = wellKnownProtocols.some(p =>
    projectName.toLowerCase().includes(p)
  );

  if (isWellKnown) {
    return {
      isAudited: true,
      auditor: 'Certik (Mock)',
      auditDate: '2024-01-15',
      securityScore: 85 + Math.floor(Math.random() * 10),
      findings: [
        { severity: 'minor', title: 'Gas optimization', resolved: true },
        { severity: 'informational', title: 'Code style', resolved: true },
      ],
      kycVerified: true,
    };
  }

  return {
    isAudited: false,
    auditor: null,
    auditDate: null,
    securityScore: 30,
    findings: [],
    kycVerified: false,
  };
}

// Calculate audit score component
export function calculateAuditScore(audit: AuditData): number {
  let score = 0;

  // Base score for being audited
  if (audit.isAudited) {
    score += 40;
  }

  // Security score contribution (0-40 points)
  score += (audit.securityScore / 100) * 40;

  // KYC bonus
  if (audit.kycVerified) {
    score += 10;
  }

  // Penalty for unresolved critical/major findings
  const unresolvedCritical = audit.findings.filter(
    f => !f.resolved && (f.severity === 'critical' || f.severity === 'major')
  ).length;
  score -= unresolvedCritical * 10;

  return Math.max(0, Math.min(100, score));
}
