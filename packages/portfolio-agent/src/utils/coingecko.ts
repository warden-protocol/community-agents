import Coingecko from '@coingecko/coingecko-typescript';
import { ListGetResponse } from '@coingecko/coingecko-typescript/resources/coins/list.mjs';

type CoingeckoToken = ListGetResponse.ListGetResponseItem & {
  decimals: number | undefined;
};
type CoingeckoTokenMetadata = CoingeckoToken & {
  decimals: number | undefined;
};
type PriceChange = {
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
      firstPriceUsd,
      lastPriceUsd,
      priceChangeUsd,
      priceChangePercent,
    };
  }
}
