import { AlchemyClient, AlchemyNetwork } from './alchemy';
import { CoingeckoService } from './coingecko';

export interface PortfolioChange {
  tokens: PortfolioToken[];
  startPeriodTotalAmountUsd: number;
  totalAmountUsd: number;
  totalAmountChange: number;
  totalAmountChangePercent: number;
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
    fromDate: Date,
    toDate: Date,
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

      const priceChange = await this.coingeckoService.getCoinPriceChange(
        cgCoin.id,
        fromDate.toISOString().split('T')[0], // get date in YYYY-MM-DD format
        toDate.toISOString().split('T')[0],
      );

      if (!priceChange) {
        console.warn(
          `No price change found for token ${token.tokenAddress} on network ${token.network}`,
        );
        continue;
      }

      portfolioTokens.push({
        coingeckoId: cgCoin.id,
        symbol: cgCoin.symbol,
        name: cgCoin.name,
        chain: token.network,
        amount: tokenAmount,
        amountUsd: tokenAmount * priceChange.lastPriceUsd,
        currentPrice: priceChange.lastPriceUsd,
        startPeriodPrice: priceChange.firstPriceUsd,
        priceChange: priceChange.priceChangeUsd,
        priceChangePercent: priceChange.priceChangePercent,
      });
    }

    return portfolioTokens;
  }

  private getIntervalStartDate(endDate: Date, interval: TimeInterval): Date {
    switch (interval) {
      case 'daily':
        return new Date(endDate.getTime() - 24 * 60 * 60 * 1000);
      case 'weekly':
        return new Date(endDate.getTime() - 7 * 24 * 60 * 60 * 1000);
      case 'monthly':
        return new Date(endDate.getTime() - 30 * 24 * 60 * 60 * 1000);
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

    const toDate = new Date();
    const fromDate = this.getIntervalStartDate(toDate, interval);
    const portfolioTokens = await this.getPortfolioTokens(
      userAddresses,
      fromDate,
      toDate,
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

    return {
      tokens: portfolioTokens,
      startPeriodTotalAmountUsd,
      totalAmountUsd,
      totalAmountChange,
      totalAmountChangePercent,
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
