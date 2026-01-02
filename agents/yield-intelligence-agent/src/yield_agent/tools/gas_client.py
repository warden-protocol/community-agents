"""
================================================================================
    GAS ESTIMATION CLIENT
    Real-time gas prices and transaction cost estimates
    
    Uses Blocknative API with fallback to public RPC endpoints
    Blocknative: https://www.blocknative.com/gas-estimator
================================================================================
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from yield_agent.state import GasEstimate, SUPPORTED_CHAINS


# ==============================================================================
# CONSTANTS
# ==============================================================================


BLOCKNATIVE_URL = "https://api.blocknative.com/gasprices/blockprices"

REQUEST_TIMEOUT = 15.0

GAS_UNITS = {
    "swap": 150_000,
    "deposit": 100_000,
    "approve": 50_000,
    "bridge": 200_000,
    "transfer": 21_000,
}

ETH_PRICE_FALLBACK = 3500.0
MATIC_PRICE_FALLBACK = 0.50
BNB_PRICE_FALLBACK = 600.0
AVAX_PRICE_FALLBACK = 35.0

PUBLIC_RPC_ENDPOINTS: dict[str, str] = {
    "ethereum": "https://eth.llamarpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://mainnet.optimism.io",
    "polygon": "https://polygon-rpc.com",
    "base": "https://mainnet.base.org",
    "avalanche": "https://api.avax.network/ext/bc/C/rpc",
    "bsc": "https://bsc-dataseed.binance.org",
}

NATIVE_TOKEN_PRICES: dict[str, float] = {
    "ethereum": ETH_PRICE_FALLBACK,
    "arbitrum": ETH_PRICE_FALLBACK,
    "optimism": ETH_PRICE_FALLBACK,
    "base": ETH_PRICE_FALLBACK,
    "polygon": MATIC_PRICE_FALLBACK,
    "bsc": BNB_PRICE_FALLBACK,
    "avalanche": AVAX_PRICE_FALLBACK,
}


# ==============================================================================
# CLIENT CLASS
# ==============================================================================


class GasClient:
    """
    Async client for gas price estimation.
    
    Uses Blocknative API when available, falls back to
    direct RPC calls for unsupported chains.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._price_cache: dict[str, float] = dict(NATIVE_TOKEN_PRICES)

    async def __aenter__(self) -> GasClient:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
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
    # PUBLIC METHODS
    # --------------------------------------------------------------------------

    async def get_gas_estimate(self, chain: str) -> Optional[GasEstimate]:
        """
        Get current gas prices for a chain.
        
        Args:
            chain: Chain identifier
            
        Returns:
            GasEstimate with current prices, or None on failure
        """
        chain_lower = chain.lower()
        
        if chain_lower not in SUPPORTED_CHAINS:
            return None
        
        if self.api_key and chain_lower == "ethereum":
            estimate = await self._fetch_blocknative(chain_lower)
            if estimate:
                return estimate
        
        return await self._fetch_from_rpc(chain_lower)

    async def get_gas_estimates_multi(
        self, chains: list[str]
    ) -> dict[str, Optional[GasEstimate]]:
        """
        Get gas estimates for multiple chains.
        
        Args:
            chains: List of chain identifiers
            
        Returns:
            Dictionary mapping chain to GasEstimate
        """
        results: dict[str, Optional[GasEstimate]] = {}
        
        for chain in chains:
            estimate = await self.get_gas_estimate(chain)
            results[chain.lower()] = estimate
        
        return results

    async def estimate_transaction_cost(
        self,
        chain: str,
        operation: str = "swap",
        speed: str = "standard",
    ) -> Optional[float]:
        """
        Estimate cost for a specific operation.
        
        Args:
            chain: Chain identifier
            operation: Operation type (swap, deposit, approve, bridge, transfer)
            speed: Gas speed (slow, standard, fast)
            
        Returns:
            Estimated cost in USD, or None
        """
        estimate = await self.get_gas_estimate(chain)
        if not estimate:
            return None
        
        gas_units = GAS_UNITS.get(operation, GAS_UNITS["swap"])
        
        if speed == "slow":
            gas_price = estimate.gas_price_slow
        elif speed == "fast":
            gas_price = estimate.gas_price_fast
        else:
            gas_price = estimate.gas_price_standard
        
        chain_lower = chain.lower()
        native_price = self._price_cache.get(chain_lower, ETH_PRICE_FALLBACK)
        
        gas_cost_eth = (gas_price * gas_units) / 1e9
        cost_usd = gas_cost_eth * native_price
        
        return round(cost_usd, 2)

    # --------------------------------------------------------------------------
    # PRIVATE METHODS
    # --------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def _fetch_blocknative(self, chain: str) -> Optional[GasEstimate]:
        """Fetch gas prices from Blocknative API."""
        try:
            response = await self.client.get(BLOCKNATIVE_URL)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            block_prices = data.get("blockPrices", [])
            
            if not block_prices:
                return None
            
            latest = block_prices[0]
            estimated_prices = latest.get("estimatedPrices", [])
            
            if not estimated_prices:
                return None
            
            prices_by_confidence: dict[int, dict] = {}
            for price in estimated_prices:
                confidence = price.get("confidence", 0)
                prices_by_confidence[confidence] = price
            
            slow = prices_by_confidence.get(70, estimated_prices[-1])
            standard = prices_by_confidence.get(90, estimated_prices[1] if len(estimated_prices) > 1 else estimated_prices[0])
            fast = prices_by_confidence.get(99, estimated_prices[0])
            
            gas_slow = slow.get("price", 20)
            gas_standard = standard.get("price", 25)
            gas_fast = fast.get("price", 35)
            
            base_fee = latest.get("baseFeePerGas")
            priority_fee = standard.get("maxPriorityFeePerGas")
            
            chain_config = SUPPORTED_CHAINS[chain]
            native_price = self._price_cache.get(chain, ETH_PRICE_FALLBACK)
            
            swap_cost = self._calculate_cost_usd(gas_standard, GAS_UNITS["swap"], native_price)
            deposit_cost = self._calculate_cost_usd(gas_standard, GAS_UNITS["deposit"], native_price)
            
            return GasEstimate(
                chain=chain,
                chain_id=chain_config["chain_id"],
                gas_price_slow=round(gas_slow, 2),
                gas_price_standard=round(gas_standard, 2),
                gas_price_fast=round(gas_fast, 2),
                swap_cost_usd=swap_cost,
                deposit_cost_usd=deposit_cost,
                base_fee=base_fee,
                priority_fee=priority_fee,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            
        except Exception:
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def _fetch_from_rpc(self, chain: str) -> Optional[GasEstimate]:
        """Fetch gas prices from public RPC endpoint."""
        rpc_url = PUBLIC_RPC_ENDPOINTS.get(chain)
        if not rpc_url:
            return None
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_gasPrice",
                "params": [],
                "id": 1,
            }
            
            response = await self.client.post(rpc_url, json=payload)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            result = data.get("result")
            
            if not result:
                return None
            
            gas_price_wei = int(result, 16)
            gas_price_gwei = gas_price_wei / 1e9
            
            gas_slow = gas_price_gwei * 0.9
            gas_standard = gas_price_gwei
            gas_fast = gas_price_gwei * 1.2
            
            chain_config = SUPPORTED_CHAINS[chain]
            native_price = self._price_cache.get(chain, ETH_PRICE_FALLBACK)
            
            swap_cost = self._calculate_cost_usd(gas_standard, GAS_UNITS["swap"], native_price)
            deposit_cost = self._calculate_cost_usd(gas_standard, GAS_UNITS["deposit"], native_price)
            
            return GasEstimate(
                chain=chain,
                chain_id=chain_config["chain_id"],
                gas_price_slow=round(gas_slow, 4),
                gas_price_standard=round(gas_standard, 4),
                gas_price_fast=round(gas_fast, 4),
                swap_cost_usd=swap_cost,
                deposit_cost_usd=deposit_cost,
                base_fee=None,
                priority_fee=None,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )
            
        except Exception:
            return None

    def _calculate_cost_usd(
        self,
        gas_price_gwei: float,
        gas_units: int,
        native_price_usd: float,
    ) -> float:
        """Calculate transaction cost in USD."""
        gas_cost_native = (gas_price_gwei * gas_units) / 1e9
        cost_usd = gas_cost_native * native_price_usd
        return round(cost_usd, 2)


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


async def get_gas_for_chains(
    chains: list[str],
    api_key: Optional[str] = None,
) -> dict[str, Optional[GasEstimate]]:
    """
    Get gas estimates for multiple chains.
    
    Args:
        chains: List of chain identifiers
        api_key: Optional Blocknative API key
        
    Returns:
        Dictionary of chain to GasEstimate
    """
    async with GasClient(api_key=api_key) as client:
        return await client.get_gas_estimates_multi(chains)


async def get_cheapest_chain(
    chains: list[str],
    operation: str = "swap",
    api_key: Optional[str] = None,
) -> Optional[tuple[str, float]]:
    """
    Find the cheapest chain for an operation.
    
    Args:
        chains: List of chains to compare
        operation: Operation type
        api_key: Optional Blocknative API key
        
    Returns:
        Tuple of (chain, cost_usd) or None
    """
    async with GasClient(api_key=api_key) as client:
        estimates = await client.get_gas_estimates_multi(chains)
    
    cheapest_chain: Optional[str] = None
    cheapest_cost: float = float("inf")
    
    for chain, estimate in estimates.items():
        if estimate:
            if operation == "deposit":
                cost = estimate.deposit_cost_usd
            else:
                cost = estimate.swap_cost_usd
            
            if cost < cheapest_cost:
                cheapest_cost = cost
                cheapest_chain = chain
    
    if cheapest_chain:
        return (cheapest_chain, cheapest_cost)
    return None


async def estimate_total_entry_cost(
    target_chain: str,
    current_chain: Optional[str] = None,
    needs_bridge: bool = False,
    needs_swap: bool = False,
    api_key: Optional[str] = None,
) -> float:
    """
    Estimate total cost to enter a yield position.
    
    Args:
        target_chain: Destination chain
        current_chain: User's current chain
        needs_bridge: Whether bridging is required
        needs_swap: Whether a swap is required
        api_key: Optional Blocknative API key
        
    Returns:
        Total estimated cost in USD
    """
    total_cost = 0.0
    
    async with GasClient(api_key=api_key) as client:
        if needs_bridge and current_chain:
            bridge_cost = await client.estimate_transaction_cost(
                current_chain, "bridge"
            )
            if bridge_cost:
                total_cost += bridge_cost
        
        if needs_swap:
            swap_cost = await client.estimate_transaction_cost(
                target_chain, "swap"
            )
            if swap_cost:
                total_cost += swap_cost
        
        approve_cost = await client.estimate_transaction_cost(
            target_chain, "approve"
        )
        if approve_cost:
            total_cost += approve_cost
        
        deposit_cost = await client.estimate_transaction_cost(
            target_chain, "deposit"
        )
        if deposit_cost:
            total_cost += deposit_cost
    
    return round(total_cost, 2)
