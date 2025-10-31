import { describe, it, beforeAll, expect } from 'vitest';
import { UserPortfolioService } from '../../src/utils/portfolio';

it('check whale portfolio', async () => {
  const portfolioService = new UserPortfolioService();
  const result = await portfolioService.getPortfolioChange(
    {
      evmAddress: '0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6',
      solanaAddress: '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',
    },
    'weekly',
  );

  console.log(result);
});
