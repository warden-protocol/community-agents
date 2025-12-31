// Types for Hyperliquid API responses

export interface FundingHistoryEntry {
  coin: string;
  fundingRate: string;
  premium: string;
  time: number;
}

export interface MarketMeta {
  name: string;
  szDecimals: number;
  maxLeverage: number;
  isDelisted?: boolean;
}

export interface MetaResponse {
  universe: MarketMeta[];
}

// Processed funding rate data
export interface ProcessedFundingRate {
  coin: string;
  fundingRate: number;
  fundingRatePercent: number;
  apr: number;
  premium: number;
  timestamp: number;
  date?: string;
}

// API request body types
export interface FundingHistoryRequest {
  type: 'fundingHistory';
  coin: string;
  startTime: number;
  endTime?: number;
}

export interface MetaRequest {
  type: 'meta';
}

export type HyperliquidRequest = FundingHistoryRequest | MetaRequest;
