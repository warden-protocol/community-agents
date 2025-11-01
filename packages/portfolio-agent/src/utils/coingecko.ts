import Coingecko from '@coingecko/coingecko-typescript';
import { ListGetResponse } from '@coingecko/coingecko-typescript/resources/coins/list.mjs';
import { TopToken } from './portfolio';
import { TopGainersLoserGetResponse } from '@coingecko/coingecko-typescript/resources/coins/top-gainers-losers.mjs';

export type Duration = '24h' | '7d' | '30d';

type CoingeckoToken = ListGetResponse.ListGetResponseItem & {
  decimals: number | undefined;
};
type CoingeckoTokenMetadata = CoingeckoToken & {
  decimals: number | undefined;
};
export type PriceChange = {
  id: string;
  firstPriceUsd: number;
  lastPriceUsd: number;
  priceChangeUsd: number;
  priceChangePercent: number;
};

export class CoingeckoService {
  private readonly COIN_CACHE_EXPIRATION_MS = 1000 * 60 * 60 * 24; // 24 hours

  private readonly coingeckoClient: Coingecko;

  private cachedAt: Date;
  private cachedCoinsMap: Map<string, CoingeckoToken>;
  private coingeckoTokenMetadataMap: Map<string, CoingeckoTokenMetadata>;

  constructor() {
    this.coingeckoClient = new Coingecko({
      proAPIKey: process.env.COINGECKO_API_KEY,
      environment: 'pro',
    });
    this.cachedAt = new Date(0);
    this.cachedCoinsMap = new Map();
    this.coingeckoTokenMetadataMap = new Map();
  }

  async initializeCoingeckoCoins(): Promise<void> {
    const isCacheExpired =
      this.cachedAt.getTime() + this.COIN_CACHE_EXPIRATION_MS < Date.now();
    if (!isCacheExpired && this.cachedCoinsMap.size > 0) {
      return;
    }

    const coinsList = await this.coingeckoClient.coins.list.get({
      include_platform: true,
      status: 'active',
    });
    for (const cgCoin of coinsList) {
      if (!cgCoin.platforms) {
        continue;
      }

      for (const platformAddress of Object.values(cgCoin.platforms)) {
        this.cachedCoinsMap.set(platformAddress, {
          ...cgCoin,
          decimals: undefined,
        });
      }
    }
    this.cachedAt = new Date();
  }

  async getCoinData(coingeckoId: string): Promise<CoingeckoToken | null> {
    await this.initializeCoingeckoCoins();
    return this.cachedCoinsMap.get(coingeckoId) ?? null;
  }

  async getCoinMetadataByAddress(
    platformId: string,
    tokenAddress: string,
  ): Promise<CoingeckoTokenMetadata | null> {
    const key = `${platformId}-${tokenAddress}`;
    if (this.coingeckoTokenMetadataMap.has(key)) {
      return this.coingeckoTokenMetadataMap.get(key);
    }

    const tokenMetadata = await this.coingeckoClient.coins.contract.get(
      tokenAddress,
      { id: platformId },
    );
    const metadataWithDecimals = {
      ...tokenMetadata,
      decimals: tokenMetadata.detail_platforms[platformId]?.decimal_place,
    };
    this.coingeckoTokenMetadataMap.set(key, {
      ...tokenMetadata,
      decimals: undefined,
    });
    return metadataWithDecimals;
  }

  async getCoinPriceChange(
    coingeckoId: string,
    from: string,
    to: string,
  ): Promise<PriceChange | null> {
    const marketChart = await this.coingeckoClient.coins.marketChart.getRange(
      coingeckoId,
      {
        from,
        interval: 'daily',
        to,
        vs_currency: 'usd',
        precision: '8',
      },
    );

    if (marketChart.prices.length < 2) {
      return null;
    }

    const firstPriceUsd = marketChart.prices[0][1];
    const lastPriceUsd = marketChart.prices[marketChart.prices.length - 1][1];
    const priceChangeUsd = lastPriceUsd - firstPriceUsd;
    const priceChangePercent =
      firstPriceUsd !== 0 ? (priceChangeUsd / firstPriceUsd) * 100 : 0;

    return {
      id: coingeckoId,
      firstPriceUsd,
      lastPriceUsd,
      priceChangeUsd,
      priceChangePercent,
    };
  }

  async getMarketChanges(
    ids: string[],
    priceChange: Duration,
  ): Promise<PriceChange[]> {
    const markets = await this.coingeckoClient.coins.markets.get({
      ids: ids.join(','),
      vs_currency: 'usd',
      price_change_percentage: priceChange,
      per_page: 250,
      precision: '10',
    });

    //Object key example: price_change_percentage_30d_in_currency
    const priceChangeKey = `price_change_percentage_${priceChange}_in_currency`;
    return markets.map((m) => {
      const priceChangePercentage = Number(m[priceChangeKey]);
      const startPeriodPrice =
        m.current_price / (priceChangePercentage / 100.0 + 1.0);
      return {
        id: m.id,
        firstPriceUsd: startPeriodPrice,
        lastPriceUsd: m.current_price,
        priceChangeUsd: m.current_price - startPeriodPrice,
        priceChangePercent: priceChangePercentage,
      };
    });
  }

  async getTopGainersLosers(
    duration: Duration,
  ): Promise<{ topGainers: TopToken[]; topLosers: TopToken[] }> {
    const response = await this.coingeckoClient.coins.topGainersLosers.get({
      vs_currency: 'usd',
      duration,
    });

    const convertToTopToken = (
      coin:
        | TopGainersLoserGetResponse.TopGainer
        | TopGainersLoserGetResponse.TopLoser,
    ): TopToken => {
      const priceChangeKey = `usd_${duration}_change`;
      const priceChange = Number(coin[priceChangeKey]);
      return {
        coingeckoId: coin.id,
        symbol: coin.symbol,
        name: coin.name,
        marketCapRank: coin.market_cap_rank,
        currentPrice: coin.usd,
        priceChange,
      };
    };

    return {
      topGainers: response.top_gainers.map(convertToTopToken),
      topLosers: response.top_losers.map(convertToTopToken),
    };
  }
}
