import {
  FundingHistoryEntry,
  MetaResponse,
  ProcessedFundingRate,
  HyperliquidRequest,
} from './types';

const HYPERLIQUID_API_URL = 'https://api.hyperliquid.xyz/info';
const HOURS_PER_YEAR = 24 * 365;

export async function hyperliquidRequest<T>(body: HyperliquidRequest): Promise<T> {
  const response = await fetch(HYPERLIQUID_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(
      `Hyperliquid API error: ${response.status} ${response.statusText}`,
    );
  }

  return response.json() as Promise<T>;
}

export function calculateApr(fundingRate: number): number {
  return fundingRate * 100 * HOURS_PER_YEAR;
}

export function processFundingEntry(entry: FundingHistoryEntry, includeDate = false): ProcessedFundingRate {
  const fundingRate = parseFloat(entry.fundingRate);
  const result: ProcessedFundingRate = {
    coin: entry.coin,
    fundingRate,
    fundingRatePercent: fundingRate * 100,
    apr: calculateApr(fundingRate),
    premium: parseFloat(entry.premium),
    timestamp: entry.time,
  };

  if (includeDate) {
    result.date = new Date(entry.time).toISOString();
  }

  return result;
}

export async function fetchFundingHistory(
  coin: string,
  startTime: number,
  endTime?: number,
): Promise<FundingHistoryEntry[]> {
  const body: HyperliquidRequest = {
    type: 'fundingHistory',
    coin: coin.toUpperCase(),
    startTime,
    ...(endTime && { endTime }),
  };

  return hyperliquidRequest<FundingHistoryEntry[]>(body);
}

export async function fetchLatestFundingRate(
  coin: string,
): Promise<ProcessedFundingRate | null> {
  const startTime = Date.now() - 2 * 60 * 60 * 1000; // Last 2 hours
  const data = await fetchFundingHistory(coin, startTime);

  if (data.length === 0) {
    return null;
  }

  return processFundingEntry(data[data.length - 1], true);
}

export async function fetchMarketsMeta(): Promise<MetaResponse> {
  return hyperliquidRequest<MetaResponse>({ type: 'meta' });
}

export async function getActiveMarkets(): Promise<Array<{ coin: string; maxLeverage: number }>> {
  const data = await fetchMarketsMeta();

  return data.universe
    .filter((market) => !market.isDelisted)
    .map((market) => ({
      coin: market.name,
      maxLeverage: market.maxLeverage,
    }));
}

export async function fetchMultipleFundingRates(
  coins: string[],
): Promise<{ results: ProcessedFundingRate[]; errors: Array<{ coin: string; error: string }> }> {
  const startTime = Date.now() - 2 * 60 * 60 * 1000;

  const fetchResults = await Promise.all(
    coins.map(async (coin) => {
      try {
        const data = await fetchFundingHistory(coin, startTime);

        if (data.length === 0) {
          return { coin, error: 'No data found' };
        }

        return processFundingEntry(data[data.length - 1]);
      } catch (error) {
        return { coin, error: `Failed to fetch: ${error}` };
      }
    }),
  );

  const results = fetchResults.filter(
    (r): r is ProcessedFundingRate => !('error' in r),
  );
  const errors = fetchResults.filter(
    (r): r is { coin: string; error: string } => 'error' in r,
  );

  // Sort by APR descending
  results.sort((a, b) => b.apr - a.apr);

  return { results, errors };
}

export async function fetchTopFundingRates(
  limit: number,
  sortOrder: 'highest' | 'lowest',
): Promise<{ topRates: ProcessedFundingRate[]; totalMarketsAnalyzed: number }> {
  const activeMarkets = await getActiveMarkets();
  const startTime = Date.now() - 2 * 60 * 60 * 1000;

  const results: ProcessedFundingRate[] = [];

  // Process in batches of 10 to avoid overwhelming the API
  const batchSize = 10;
  for (let i = 0; i < activeMarkets.length; i += batchSize) {
    const batch = activeMarkets.slice(i, i + batchSize);
    const batchResults = await Promise.all(
      batch.map(async (market) => {
        try {
          const data = await fetchFundingHistory(market.coin, startTime);
          if (data.length === 0) return null;
          return processFundingEntry(data[data.length - 1]);
        } catch {
          return null;
        }
      }),
    );

    results.push(
      ...batchResults.filter((r): r is ProcessedFundingRate => r !== null),
    );
  }

  // Sort based on sortOrder
  if (sortOrder === 'highest') {
    results.sort((a, b) => b.apr - a.apr);
  } else {
    results.sort((a, b) => a.apr - b.apr);
  }

  return {
    topRates: results.slice(0, limit),
    totalMarketsAnalyzed: results.length,
  };
}
