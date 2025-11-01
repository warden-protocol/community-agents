import { AlchemyClient, AlchemyNetwork } from './alchemy';
import { CoingeckoService, PriceChange, Duration } from './coingecko';

export interface PortfolioChange {
  tokens: PortfolioToken[];
  startPeriodTotalAmountUsd: number;
  totalAmountUsd: number;
  totalAmountChange: number;
  totalAmountChangePercent: number;
  topGainers: TopToken[];
  topLosers: TopToken[];
}

export interface PortfolioToken {
  coingeckoId: string;
  symbol: string;
  name: string;
  chain: AlchemyNetwork;
  amount: number;
  amountUsd: number;
  currentPrice: number;
  startPeriodPrice: number;
  priceChange: number;
  priceChangePercent: number;
}

export interface TopToken {
  coingeckoId: string;
  symbol: string;
  name: string;
  marketCapRank: number;
  currentPrice: number;
  priceChange: number;
}

type TimeInterval = 'daily' | 'weekly' | 'monthly';

type NativeToken = {
  id: string;
  symbol: string;
  name: string;
  decimals: number;
};

type UserAddresses = {
  evmAddress?: string;
  solanaAddress?: string;
};

export class UserPortfolioService {
  private readonly coingeckoService: CoingeckoService;
  private readonly alchemyClient: AlchemyClient;

  private nativeTokensMap: Map<AlchemyNetwork, NativeToken>;

  constructor() {
    this.coingeckoService = new CoingeckoService();
    this.alchemyClient = new AlchemyClient(process.env.ALCHEMY_API_KEY);
    this.initializeCoingeckoNativeTokens();
  }

  private initializeCoingeckoNativeTokens(): void {
    this.nativeTokensMap = new Map();
    this.nativeTokensMap.set('eth-mainnet', {
      id: 'ethereum',
      symbol: 'ETH',
      name: 'Ethereum',
      decimals: 18,
    });

    this.nativeTokensMap.set('base-mainnet', {
      id: 'ethereum',
      symbol: 'ETH',
      name: 'Ethereum',
      decimals: 18,
    });

    this.nativeTokensMap.set('bnb-mainnet', {
      id: 'binancecoin',
      symbol: 'BNB',
      name: 'BNB',
      decimals: 18,
    });

    this.nativeTokensMap.set('solana-mainnet', {
      id: 'solana',
      symbol: 'SOL',
      name: 'Solana',
      decimals: 9,
    });
  }

  private convertToCoingeckoPlatformId(network: AlchemyNetwork): string {
    switch (network) {
      case 'eth-mainnet':
        return 'ethereum';
      case 'base-mainnet':
        return 'base';
      case 'bnb-mainnet':
        return 'binance-smart-chain';
      case 'solana-mainnet':
        return 'solana';
      default:
        throw new Error(`Unsupported network: ${network}`);
    }
  }
  private convertToAlchemyAddressesArgs(
    userAddresses: UserAddresses,
  ): { address: string; networks: string[] }[] {
    const alchemyAddresses = [];
    if (userAddresses.evmAddress) {
      alchemyAddresses.push({
        address: userAddresses.evmAddress,
        networks: ['eth-mainnet', 'base-mainnet', 'bnb-mainnet'],
      });
    }

    if (userAddresses.solanaAddress) {
      alchemyAddresses.push({
        address: userAddresses.solanaAddress,
        networks: ['solana-mainnet'],
      });
    }

    return alchemyAddresses;
  }

  private async getPortfolioTokens(
    userAddresses: UserAddresses,
    interval: TimeInterval,
  ): Promise<PortfolioToken[]> {
    const addresses = this.convertToAlchemyAddressesArgs(userAddresses);

    const walletBalances =
      await this.alchemyClient.getAllTokenWalletBalances(addresses);

    const portfolioTokens: PortfolioToken[] = [];
    for (const token of walletBalances.data.tokens) {
      const tokenBalanceRaw = BigInt(token.tokenBalance);
      if (tokenBalanceRaw === 0n) {
        //skip token with 0 balance
        continue;
      }

      let cgCoin = null;
      if (
        token.tokenAddress === '0x0000000000000000000000000000000000000000' ||
        token.tokenAddress == null
      ) {
        // native token
        cgCoin = this.nativeTokensMap.get(token.network);
      } else {
        // erc-20 or spl token
        cgCoin = await this.coingeckoService.getCoinData(token.tokenAddress);
      }

      if (!cgCoin) {
        continue;
      }

      //get tokenAmount
      let tokenAmount = token.scaledTokenBalance;
      if (!tokenAmount) {
        //get metadata
        let decimals = cgCoin.decimals;
        if (!decimals) {
          const metadata = await this.coingeckoService.getCoinMetadataByAddress(
            this.convertToCoingeckoPlatformId(token.network),
            token.tokenAddress,
          );
          decimals = metadata.decimals;
        }

        if (!decimals) {
          console.warn(
            `No decimals found for token ${token.tokenAddress} on network ${token.network}`,
          );
          continue;
        }

        tokenAmount = Number(tokenBalanceRaw) / 10 ** decimals;
      }

      portfolioTokens.push({
        coingeckoId: cgCoin.id,
        symbol: cgCoin.symbol,
        name: cgCoin.name,
        chain: token.network,
        amount: tokenAmount,
        amountUsd: 0,
        currentPrice: 0,
        startPeriodPrice: 0,
        priceChange: 0,
        priceChangePercent: 0,
      });
    }

    const marketChangesMap = new Map<string, PriceChange>();
    (
      await this.coingeckoService.getMarketChanges(
        portfolioTokens.map((t) => t.coingeckoId),
        this.convertToDuration(interval),
      )
    ).forEach((m) => marketChangesMap.set(m.id, m));

    for (const portfolioToken of portfolioTokens) {
      const marketChange = marketChangesMap.get(portfolioToken.coingeckoId);
      if (!marketChange) {
        continue;
      }

      portfolioToken.amountUsd =
        marketChange.lastPriceUsd * portfolioToken.amount;
      portfolioToken.currentPrice = marketChange.lastPriceUsd;
      portfolioToken.startPeriodPrice = marketChange.firstPriceUsd;
      portfolioToken.priceChange = marketChange.priceChangeUsd;
      portfolioToken.priceChangePercent = marketChange.priceChangePercent;
    }

    return portfolioTokens;
  }

  private convertToDuration(interval: TimeInterval): Duration {
    switch (interval) {
      case 'daily':
        return '24h';
      case 'weekly':
        return '7d';
      case 'monthly':
        return '30d';
      default:
        throw new Error(`Unsupported interval: ${interval}`);
    }
  }

  async getPortfolioChange(
    userAddresses: UserAddresses,
    interval: TimeInterval,
  ): Promise<PortfolioChange> {
    const { evmAddress, solanaAddress } = userAddresses;

    if (!evmAddress && !solanaAddress) {
      throw new Error('Minimum one address is required');
    }

    const portfolioTokens = await this.getPortfolioTokens(
      userAddresses,
      interval,
    );

    let startPeriodTotalAmountUsd = 0;
    let totalAmountUsd = 0;

    for (const token of portfolioTokens) {
      startPeriodTotalAmountUsd += token.startPeriodPrice * token.amount;
      totalAmountUsd += token.currentPrice * token.amount;
    }

    const totalAmountChange = totalAmountUsd - startPeriodTotalAmountUsd;
    const totalAmountChangePercent =
      startPeriodTotalAmountUsd !== 0
        ? (totalAmountChange / startPeriodTotalAmountUsd) * 100
        : 0;

    const topGainersLosers = await this.coingeckoService.getTopGainersLosers(
      this.convertToDuration(interval),
    );

    return {
      tokens: portfolioTokens,
      startPeriodTotalAmountUsd,
      totalAmountUsd,
      totalAmountChange,
      totalAmountChangePercent,
      topGainers: topGainersLosers.topGainers,
      topLosers: topGainersLosers.topLosers,
    };
  }
}

let portfolioService: UserPortfolioService | undefined = undefined;

export function getPortfolioService(): UserPortfolioService {
  if (portfolioService === undefined) {
    portfolioService = new UserPortfolioService();
  }
  return portfolioService;
}
