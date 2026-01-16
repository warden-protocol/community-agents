import axios from 'axios';
import { config } from '../config';

export interface TVLData {
  protocol: string;
  tvl: number;
  tvlChange24h: number;
  tvlChange7d: number;
  chainTvls: Record<string, number>;
  category: string;
  chains: string[];
}

export interface LiquidityData {
  pool: string;
  tvl: number;
  volume24h: number;
  apy: number;
}

// Fetch protocol TVL data from DeFiLlama
export async function getProtocolTVL(protocolSlug: string): Promise<TVLData | null> {
  try {
    const response = await axios.get(
      `${config.defiLlamaBaseUrl}/protocol/${protocolSlug}`
    );

    const data = response.data;
    const tvlHistory = data.tvl || [];
    const currentTvl = tvlHistory[tvlHistory.length - 1]?.totalLiquidityUSD || 0;
    const tvl24hAgo = tvlHistory[tvlHistory.length - 2]?.totalLiquidityUSD || currentTvl;
    const tvl7dAgo = tvlHistory[tvlHistory.length - 8]?.totalLiquidityUSD || currentTvl;

    return {
      protocol: data.name || protocolSlug,
      tvl: currentTvl,
      tvlChange24h: tvl24hAgo > 0 ? ((currentTvl - tvl24hAgo) / tvl24hAgo) * 100 : 0,
      tvlChange7d: tvl7dAgo > 0 ? ((currentTvl - tvl7dAgo) / tvl7dAgo) * 100 : 0,
      chainTvls: data.chainTvls || {},
      category: data.category || 'Unknown',
      chains: data.chains || [],
    };
  } catch (error) {
    console.error(`DeFiLlama API error for ${protocolSlug}:`, error);
    return null;
  }
}

// Search protocol by name
export async function searchProtocol(query: string): Promise<string | null> {
  try {
    const response = await axios.get(`${config.defiLlamaBaseUrl}/protocols`);
    const protocols = response.data;

    const match = protocols.find(
      (p: { name: string; slug: string }) =>
        p.name.toLowerCase().includes(query.toLowerCase()) ||
        p.slug.toLowerCase().includes(query.toLowerCase())
    );

    return match?.slug || null;
  } catch (error) {
    console.error('DeFiLlama search error:', error);
    return null;
  }
}

// Get all protocols list
export async function getAllProtocols(): Promise<{ name: string; slug: string; tvl: number }[]> {
  try {
    const response = await axios.get(`${config.defiLlamaBaseUrl}/protocols`);
    return response.data.map((p: { name: string; slug: string; tvl: number }) => ({
      name: p.name,
      slug: p.slug,
      tvl: p.tvl,
    }));
  } catch (error) {
    console.error('DeFiLlama protocols list error:', error);
    return [];
  }
}
