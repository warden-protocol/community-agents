"""
================================================================================
    DEFILLAMA API CLIENT
    Fetches yield data from DeFi protocols across all chains
    
    API Documentation: https://defillama.com/docs/api
    No API key required - completely free
================================================================================
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from yield_agent.state import (
    ILRisk,
    SUPPORTED_CHAINS,
    YieldOpportunity,
)


# ==============================================================================
# CONSTANTS
# ==============================================================================


BASE_URL = "https://yields.llama.fi"

POOL_ENDPOINT = "/pools"
CHART_ENDPOINT = "/chart"

REQUEST_TIMEOUT = 30.0

KNOWN_AUDITED_PROTOCOLS = {
    "aave-v3",
    "aave-v2",
    "compound-v3",
    "compound-v2",
    "lido",
    "rocket-pool",
    "maker",
    "curve-dex",
    "convex-finance",
    "yearn-finance",
    "uniswap-v3",
    "uniswap-v2",
    "sushiswap",
    "balancer-v2",
    "frax-ether",
    "instadapp",
    "morpho",
    "spark",
    "eigenlayer",
    "pendle",
    "gmx",
    "radiant-v2",
    "stargate",
    "velodrome-v2",
    "aerodrome",
    "benqi",
    "trader-joe",
    "pancakeswap-amm-v3",
}

PROTOCOL_LAUNCH_DATES: dict[str, str] = {
    "aave-v3": "2023-01-27",
    "aave-v2": "2020-12-03",
    "compound-v3": "2022-08-26",
    "compound-v2": "2019-05-07",
    "lido": "2020-12-18",
    "rocket-pool": "2021-11-08",
    "maker": "2017-12-18",
    "curve-dex": "2020-01-20",
    "convex-finance": "2021-05-17",
    "yearn-finance": "2020-07-17",
    "uniswap-v3": "2021-05-05",
    "uniswap-v2": "2020-05-18",
}


# ==============================================================================
# CLIENT CLASS
# ==============================================================================


class DeFiLlamaClient:
    """
    Async client for DeFiLlama Yields API.
    
    Provides methods to fetch and filter yield opportunities
    from all major DeFi protocols across supported chains.
    """

    def __init__(self, base_url: str = BASE_URL, timeout: float = REQUEST_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> DeFiLlamaClient:
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    # --------------------------------------------------------------------------
    # API METHODS
    # --------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_all_pools(self) -> list[dict[str, Any]]:
        """
        Fetch all yield pools from DeFiLlama.
        
        Returns raw pool data from the API.
        """
        response = await self.client.get(f"{self.base_url}{POOL_ENDPOINT}")
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def fetch_pools_by_chain(
        self,
        chain: str,
        min_tvl: float = 100_000,
        min_apy: float = 0.1,
    ) -> list[YieldOpportunity]:
        """
        Fetch and filter pools for a specific chain.
        
        Args:
            chain: Chain identifier (e.g., 'ethereum', 'arbitrum')
            min_tvl: Minimum TVL in USD
            min_apy: Minimum APY percentage
            
        Returns:
            List of YieldOpportunity objects
        """
        all_pools = await self.fetch_all_pools()
        
        chain_config = SUPPORTED_CHAINS.get(chain.lower())
        if not chain_config:
            return []
        
        defillama_chain = chain_config["defillama_slug"]
        
        filtered_pools = []
        for pool in all_pools:
            if self._matches_chain(pool, defillama_chain):
                if self._meets_criteria(pool, min_tvl, min_apy):
                    opportunity = self._parse_pool(pool, chain)
                    if opportunity:
                        filtered_pools.append(opportunity)
        
        return filtered_pools

    async def fetch_pools_multi_chain(
        self,
        chains: list[str],
        min_tvl: float = 100_000,
        min_apy: float = 0.1,
        max_results_per_chain: int = 50,
    ) -> list[YieldOpportunity]:
        """
        Fetch pools from multiple chains in parallel.
        
        Args:
            chains: List of chain identifiers
            min_tvl: Minimum TVL in USD
            min_apy: Minimum APY percentage
            max_results_per_chain: Maximum pools per chain
            
        Returns:
            Combined list of YieldOpportunity objects
        """
        all_pools = await self.fetch_all_pools()
        
        results: list[YieldOpportunity] = []
        chain_counts: dict[str, int] = {c: 0 for c in chains}
        
        sorted_pools = sorted(
            all_pools,
            key=lambda p: (p.get("tvlUsd") or 0),
            reverse=True,
        )
        
        for pool in sorted_pools:
            for chain in chains:
                chain_config = SUPPORTED_CHAINS.get(chain.lower())
                if not chain_config:
                    continue
                    
                defillama_chain = chain_config["defillama_slug"]
                
                if chain_counts[chain] >= max_results_per_chain:
                    continue
                    
                if self._matches_chain(pool, defillama_chain):
                    if self._meets_criteria(pool, min_tvl, min_apy):
                        opportunity = self._parse_pool(pool, chain)
                        if opportunity:
                            results.append(opportunity)
                            chain_counts[chain] += 1
                        break
        
        return results

    async def search_pools(
        self,
        query: str,
        chains: Optional[list[str]] = None,
        min_tvl: float = 50_000,
    ) -> list[YieldOpportunity]:
        """
        Search pools by token symbol or protocol name.
        
        Args:
            query: Search term (e.g., 'USDC', 'Aave')
            chains: Optional list of chains to filter
            min_tvl: Minimum TVL
            
        Returns:
            Matching YieldOpportunity objects
        """
        all_pools = await self.fetch_all_pools()
        query_lower = query.lower()
        
        results: list[YieldOpportunity] = []
        
        for pool in all_pools:
            symbol = (pool.get("symbol") or "").lower()
            project = (pool.get("project") or "").lower()
            
            if query_lower not in symbol and query_lower not in project:
                continue
            
            tvl = pool.get("tvlUsd") or 0
            if tvl < min_tvl:
                continue
            
            pool_chain = (pool.get("chain") or "").lower()
            
            if chains:
                chain_match = False
                for chain in chains:
                    chain_config = SUPPORTED_CHAINS.get(chain.lower())
                    if chain_config:
                        if pool_chain == chain_config["defillama_slug"].lower():
                            chain_match = True
                            opportunity = self._parse_pool(pool, chain)
                            if opportunity:
                                results.append(opportunity)
                            break
                if not chain_match:
                    continue
            else:
                chain_key = self._get_chain_key(pool_chain)
                if chain_key:
                    opportunity = self._parse_pool(pool, chain_key)
                    if opportunity:
                        results.append(opportunity)
        
        return sorted(results, key=lambda x: x.tvl_usd, reverse=True)

    # --------------------------------------------------------------------------
    # HELPER METHODS
    # --------------------------------------------------------------------------

    def _matches_chain(self, pool: dict[str, Any], defillama_chain: str) -> bool:
        """Check if pool matches the target chain."""
        pool_chain = (pool.get("chain") or "").lower()
        return pool_chain == defillama_chain.lower()

    def _meets_criteria(
        self, pool: dict[str, Any], min_tvl: float, min_apy: float
    ) -> bool:
        """Check if pool meets minimum criteria."""
        tvl = pool.get("tvlUsd") or 0
        apy = pool.get("apy") or 0
        
        if tvl < min_tvl:
            return False
        if apy < min_apy:
            return False
        if apy > 1000:
            return False
            
        return True

    def _parse_pool(
        self, pool: dict[str, Any], chain: str
    ) -> Optional[YieldOpportunity]:
        """Parse raw pool data into YieldOpportunity."""
        try:
            pool_id = pool.get("pool", "")
            project = pool.get("project", "unknown")
            symbol = pool.get("symbol", "")
            
            apy = pool.get("apy") or 0
            apy_base = pool.get("apyBase") or 0
            apy_reward = pool.get("apyReward") or 0
            
            tvl = pool.get("tvlUsd") or 0
            
            il_risk = self._calculate_il_risk(pool)
            risk_score = self._calculate_risk_score(pool, il_risk)
            
            project_slug = project.lower().replace(" ", "-")
            audited = project_slug in KNOWN_AUDITED_PROTOCOLS
            
            protocol_age = self._get_protocol_age(project_slug)
            
            pool_url = self._build_pool_url(project_slug, pool_id, chain)
            
            return YieldOpportunity(
                pool_id=pool_id,
                protocol=project,
                protocol_slug=project_slug,
                chain=chain,
                pool_name=f"{project} {symbol}",
                symbol=symbol,
                underlying_tokens=pool.get("underlyingTokens") or [],
                reward_tokens=(pool.get("rewardTokens") or "").split(", ") if pool.get("rewardTokens") else [],
                apy=round(apy, 2),
                apy_base=round(apy_base, 2),
                apy_reward=round(apy_reward, 2),
                apy_7d_avg=pool.get("apyMean7d"),
                apy_30d_avg=pool.get("apyMean30d"),
                tvl_usd=round(tvl, 2),
                risk_score=risk_score,
                il_risk=il_risk,
                audited=audited,
                audit_links=[],
                protocol_age_days=protocol_age,
                pool_url=pool_url,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            return None

    def _calculate_il_risk(self, pool: dict[str, Any]) -> ILRisk:
        """Calculate impermanent loss risk based on pool type."""
        symbol = (pool.get("symbol") or "").upper()
        
        stable_indicators = ["USD", "DAI", "FRAX", "LUSD", "USDT", "USDC"]
        is_single = "-" not in symbol and "/" not in symbol
        
        if is_single:
            return ILRisk.NONE
        
        tokens = symbol.replace("/", "-").split("-")
        
        stable_count = sum(
            1 for t in tokens
            if any(s in t.upper() for s in stable_indicators)
        )
        
        if stable_count == len(tokens):
            return ILRisk.LOW
        
        correlated_pairs = [
            ("ETH", "STETH"), ("ETH", "WSTETH"), ("ETH", "RETH"),
            ("ETH", "CBETH"), ("BTC", "WBTC"), ("BTC", "TBTC"),
        ]
        
        for t1, t2 in correlated_pairs:
            if t1 in symbol.upper() and t2 in symbol.upper():
                return ILRisk.MEDIUM
        
        if stable_count >= 1:
            return ILRisk.MEDIUM
            
        return ILRisk.HIGH

    def _calculate_risk_score(
        self, pool: dict[str, Any], il_risk: ILRisk
    ) -> float:
        """
        Calculate composite risk score from 1-10.
        
        Factors:
        - TVL (higher = safer)
        - Protocol reputation (audited = safer)
        - APY sustainability (very high APY = riskier)
        - Impermanent loss risk
        """
        score = 5.0
        
        tvl = pool.get("tvlUsd") or 0
        if tvl > 1_000_000_000:
            score -= 2.0
        elif tvl > 100_000_000:
            score -= 1.5
        elif tvl > 10_000_000:
            score -= 1.0
        elif tvl > 1_000_000:
            score -= 0.5
        elif tvl < 500_000:
            score += 1.0
        
        project_slug = (pool.get("project") or "").lower().replace(" ", "-")
        if project_slug in KNOWN_AUDITED_PROTOCOLS:
            score -= 1.5
        
        apy = pool.get("apy") or 0
        if apy > 100:
            score += 2.5
        elif apy > 50:
            score += 1.5
        elif apy > 20:
            score += 0.5
        
        il_adjustments = {
            ILRisk.NONE: -0.5,
            ILRisk.LOW: 0,
            ILRisk.MEDIUM: 0.5,
            ILRisk.HIGH: 1.5,
        }
        score += il_adjustments.get(il_risk, 0)
        
        return round(max(1.0, min(10.0, score)), 1)

    def _get_protocol_age(self, project_slug: str) -> int:
        """Get protocol age in days."""
        launch_date_str = PROTOCOL_LAUNCH_DATES.get(project_slug)
        if not launch_date_str:
            return 0
        
        try:
            launch_date = datetime.strptime(launch_date_str, "%Y-%m-%d")
            age = datetime.now() - launch_date
            return age.days
        except ValueError:
            return 0

    def _build_pool_url(
        self, project_slug: str, pool_id: str, chain: str
    ) -> Optional[str]:
        """Build URL to the pool on the protocol's site."""
        return f"https://defillama.com/yields/pool/{pool_id}"

    def _get_chain_key(self, defillama_chain: str) -> Optional[str]:
        """Get chain key from DeFiLlama chain name."""
        defillama_lower = defillama_chain.lower()
        for key, config in SUPPORTED_CHAINS.items():
            if config["defillama_slug"].lower() == defillama_lower:
                return key
        return None


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


async def get_top_yields(
    chains: Optional[list[str]] = None,
    min_tvl: float = 100_000,
    min_apy: float = 1.0,
    limit: int = 20,
) -> list[YieldOpportunity]:
    """
    Get top yield opportunities across chains.
    
    Args:
        chains: Chains to search (None = all supported)
        min_tvl: Minimum TVL in USD
        min_apy: Minimum APY percentage
        limit: Maximum results to return
        
    Returns:
        List of top YieldOpportunity objects sorted by APY
    """
    if chains is None:
        chains = list(SUPPORTED_CHAINS.keys())
    
    async with DeFiLlamaClient() as client:
        opportunities = await client.fetch_pools_multi_chain(
            chains=chains,
            min_tvl=min_tvl,
            min_apy=min_apy,
        )
    
    sorted_opps = sorted(opportunities, key=lambda x: x.apy, reverse=True)
    return sorted_opps[:limit]


async def search_yield_opportunities(
    token: str,
    chains: Optional[list[str]] = None,
    min_tvl: float = 50_000,
) -> list[YieldOpportunity]:
    """
    Search for yield opportunities by token.
    
    Args:
        token: Token symbol (e.g., 'USDC', 'ETH')
        chains: Optional chain filter
        min_tvl: Minimum TVL
        
    Returns:
        Matching opportunities sorted by TVL
    """
    async with DeFiLlamaClient() as client:
        return await client.search_pools(
            query=token,
            chains=chains,
            min_tvl=min_tvl,
        )
