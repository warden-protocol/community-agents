import { StateGraph, END } from '@langchain/langgraph';
import {
  ScannerState,
  parseInputNode,
  fetchTVLNode,
  fetchAuditNode,
  fetchContractNode,
  fetchOnchainNode,
  analyzeRiskNode,
  shouldContinue,
} from './nodes';

// Create the workflow graph
export function createScannerWorkflow() {
  const workflow = new StateGraph<any>({
    channels: {
      query: {
        reducer: (prev: string, next: string) => next ?? prev,
        default: () => '',
      },
      contractAddress: {
        reducer: (prev: string | undefined, next: string | undefined) => next ?? prev,
        default: () => undefined,
      },
      protocolSlug: {
        reducer: (prev: string | undefined, next: string | undefined) => next ?? prev,
        default: () => undefined,
      },
      tvlData: {
        reducer: (prev: any, next: any) => next ?? prev,
        default: () => null,
      },
      auditData: {
        reducer: (prev: any, next: any) => next ?? prev,
        default: () => null,
      },
      contractInfo: {
        reducer: (prev: any, next: any) => next ?? prev,
        default: () => null,
      },
      onchainBehavior: {
        reducer: (prev: any, next: any) => next ?? prev,
        default: () => null,
      },
      riskReport: {
        reducer: (prev: any, next: any) => next ?? prev,
        default: () => undefined,
      },
      error: {
        reducer: (prev: string | undefined, next: string | undefined) => next ?? prev,
        default: () => undefined,
      },
    },
  })
    .addNode('parseInput', parseInputNode)
    .addNode('fetchTVL', fetchTVLNode)
    .addNode('fetchAudit', fetchAuditNode)
    .addNode('fetchContract', fetchContractNode)
    .addNode('fetchOnchain', fetchOnchainNode)
    .addNode('analyzeRisk', analyzeRiskNode)
    .setEntryPoint('parseInput')
    .addConditionalEdges('parseInput', shouldContinue, {
      continue: 'fetchTVL',
      error: END,
    })
    .addEdge('fetchTVL', 'fetchAudit')
    .addEdge('fetchAudit', 'fetchContract')
    .addEdge('fetchContract', 'fetchOnchain')
    .addEdge('fetchOnchain', 'analyzeRisk')
    .addEdge('analyzeRisk', END);

  return workflow.compile();
}

// Helper function to run a scan
export async function runRiskScan(query: string, contractAddress?: string): Promise<ScannerState> {
  const workflow = createScannerWorkflow();

  const initialState: Partial<ScannerState> = {
    query,
    contractAddress,
  };

  const result = await workflow.invoke(initialState);
  return result as ScannerState;
}

// Format risk report as readable message
export function formatRiskReportMessage(state: ScannerState): string {
  if (state.error) {
    return `❌ Error: ${state.error}`;
  }

  if (!state.riskReport) {
    return '❌ Unable to generate risk report';
  }

  const report = state.riskReport;
  const riskEmoji = report.riskLevel === 'HIGH' ? '🔴' : report.riskLevel === 'MEDIUM' ? '🟡' : '🟢';

  let message = `
${riskEmoji} **DeFi Risk Report: ${report.protocol}**

📊 **Overall Score: ${report.overallScore}/100** (${report.riskLevel} RISK)

**Component Scores:**
• Contract Security: ${report.components.contractScore}/100
• TVL & Liquidity: ${report.components.tvlScore}/100
• Team Transparency: ${report.components.teamScore}/100
• On-chain Behavior: ${report.components.onchainScore}/100
`;

  if (report.warnings.length > 0) {
    message += '\n**⚠️ Warnings:**\n';
    for (const warning of report.warnings) {
      const icon = warning.severity === 'critical' ? '🚨' : warning.severity === 'warning' ? '⚠️' : 'ℹ️';
      message += `${icon} ${warning.message}\n`;
    }
  }

  message += `\n💡 **Summary:** ${report.summary}`;
  message += `\n\n_Report generated at ${report.timestamp}_`;

  return message.trim();
}
