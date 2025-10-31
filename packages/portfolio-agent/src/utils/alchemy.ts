export interface WalletBalanceResponse {
  data: {
    tokens: {
      network: AlchemyNetwork;
      address: string;
      tokenAddress: string;
      tokenBalance: string;
      scaledTokenBalance: number | undefined;
    }[];
  };
  pageKey?: string;
}

export type AlchemyNetwork =
  | 'eth-mainnet'
  | 'base-mainnet'
  | 'bnb-mainnet'
  | 'solana-mainnet';

export class AlchemyClient {
  constructor(private readonly apiKey: string) {}

  async getTokenWalletBalance(
    addresses: { address: string; networks: string[] }[],
    pageKey?: string,
  ): Promise<any> {
    if (addresses.length > 3) {
      throw new Error('Maximum 3 addresses allowed');
    }

    let url = `https://api.g.alchemy.com/data/v1/${this.apiKey}/assets/tokens/balances/by-address?`;
    if (pageKey) {
      url += `&pageKey=${pageKey}`;
    }
    const options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        addresses,
      }),
    };

    try {
      const response = await fetch(url, options);
      const data = await response.json();
      return data as WalletBalanceResponse;
    } catch (error) {
      console.error(error);
      console.error(addresses);
      throw new Error('Failed to get token wallet balance');
    }
  }

  async getAllTokenWalletBalances(
    addresses: { address: string; networks: string[] }[],
  ): Promise<WalletBalanceResponse> {
    let pageKey: string | undefined;

    const mergedData: WalletBalanceResponse = {
      data: {
        tokens: [],
      },
    };

    while (true) {
      const pageData = await this.getTokenWalletBalance(addresses, pageKey);

      mergedData.data.tokens.push(...pageData.data.tokens);

      if (pageData.pageKey) {
        pageKey = pageData.pageKey;
      } else {
        break;
      }
    }
    return mergedData;
  }
}
