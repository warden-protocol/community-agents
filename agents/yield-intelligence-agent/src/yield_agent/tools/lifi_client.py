"""
================================================================================
    LI.FI BRIDGE CLIENT
    Cross-chain bridge routing and quotes
    
    API Documentation: https://docs.li.fi/
    Free tier available
================================================================================
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from yield_agent.state import BridgeRoute, SUPPORTED_CHAINS


# ==============================================================================
# CONSTANTS
# ==============================================================================


BASE_URL = "https://li.quest/v1"

ROUTES_ENDPOINT = "/routes"
QUOTE_ENDPOINT = "/quote"
STATUS_ENDPOINT = "/status"
CHAINS_ENDPOINT = "/chains"
TOKENS_ENDPOINT = "/tokens"

REQUEST_TIMEOUT = 30.0

NATIVE_TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"

COMMON_TOKENS: dict[str, dict[str, str]] = {
    "USDC": {
        "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
        "bsc": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    },
    "USDT": {
        "ethereum": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "arbitrum": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "optimism": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        "polygon": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "avalanche": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
        "bsc": "0x55d398326f99059fF775485246999027B3197955",
    },
    "ETH": {
        "ethereum": NATIVE_TOKEN_ADDRESS,
        "arbitrum": NATIVE_TOKEN_ADDRESS,
        "optimism": NATIVE_TOKEN_ADDRESS,
        "base": NATIVE_TOKEN_ADDRESS,
    },
    "WETH": {
        "ethereum": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "optimism": "0x4200000000000000000000000000000000000006",
        "polygon": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        "base": "0x4200000000000000000000000000000000000006",
    },
    "DAI": {
        "ethereum": "0x6B175474E89094C44Da98b954EesafaB3E4B50db",
        "arbitrum": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "optimism": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "polygon": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    },
}


# ==============================================================================
# CLIENT CLASS
# ==============================================================================


class LiFiClient:
    """
    Async client for LI.FI Bridge Aggregator API.
    
    Provides methods to find optimal bridge routes and get
    quotes for cross-chain token transfers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BASE_URL,
        timeout: float = REQUEST_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> LiFiClient:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-lifi-api-key"] = self.api_key
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
    # API METHODS
    # --------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_routes(
        self,
        from_chain: str,
        to_chain: str,
        from_token: str,
        to_token: str,
        amount: float,
        from_address: Optional[str] = None,
        slippage: float = 0.5,
    ) -> list[BridgeRoute]:
        """
        Get available bridge routes between chains.
        
        Args:
            from_chain: Source chain identifier
            to_chain: Destination chain identifier
            from_token: Source token symbol or address
            to_token: Destination token symbol or address
            amount: Amount to bridge (in token units)
            from_address: User's wallet address (optional)
            slippage: Slippage tolerance percentage
            
        Returns:
            List of BridgeRoute options sorted by best value
        """
        from_chain_config = SUPPORTED_CHAINS.get(from_chain.lower())
        to_chain_config = SUPPORTED_CHAINS.get(to_chain.lower())
        
        if not from_chain_config or not to_chain_config:
            return []
        
        from_chain_id = from_chain_config["chain_id"]
        to_chain_id = to_chain_config["chain_id"]
        
        from_token_address = self._resolve_token_address(from_token, from_chain)
        to_token_address = self._resolve_token_address(to_token, to_chain)
        
        if not from_token_address or not to_token_address:
            return []
        
        decimals = self._get_token_decimals(from_token)
        amount_wei = int(amount * (10 ** decimals))
        
        payload = {
            "fromChainId": from_chain_id,
            "toChainId": to_chain_id,
            "fromTokenAddress": from_token_address,
            "toTokenAddress": to_token_address,
            "fromAmount": str(amount_wei),
            "options": {
                "slippage": slippage / 100,
                "order": "RECOMMENDED",
            },
        }
        
        if from_address:
            payload["fromAddress"] = from_address
        
        response = await self.client.post(
            f"{self.base_url}{ROUTES_ENDPOINT}",
            json=payload,
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        routes = data.get("routes", [])
        
        return [
            self._parse_route(route, from_chain, to_chain, from_token, amount)
            for route in routes[:5]
            if route
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_quote(
        self,
        from_chain: str,
        to_chain: str,
        from_token: str,
        to_token: str,
        amount: float,
        from_address: str,
        to_address: Optional[str] = None,
        slippage: float = 0.5,
    ) -> Optional[BridgeRoute]:
        """
        Get a specific quote with transaction data.
        
        Args:
            from_chain: Source chain identifier
            to_chain: Destination chain identifier
            from_token: Source token symbol or address
            to_token: Destination token symbol or address
            amount: Amount to bridge
            from_address: User's source wallet address
            to_address: Destination address (defaults to from_address)
            slippage: Slippage tolerance percentage
            
        Returns:
            BridgeRoute with transaction data, or None
        """
        from_chain_config = SUPPORTED_CHAINS.get(from_chain.lower())
        to_chain_config = SUPPORTED_CHAINS.get(to_chain.lower())
        
        if not from_chain_config or not to_chain_config:
            return None
        
        from_chain_id = from_chain_config["chain_id"]
        to_chain_id = to_chain_config["chain_id"]
        
        from_token_address = self._resolve_token_address(from_token, from_chain)
        to_token_address = self._resolve_token_address(to_token, to_chain)
        
        if not from_token_address or not to_token_address:
            return None
        
        decimals = self._get_token_decimals(from_token)
        amount_wei = int(amount * (10 ** decimals))
        
        params = {
            "fromChain": from_chain_id,
            "toChain": to_chain_id,
            "fromToken": from_token_address,
            "toToken": to_token_address,
            "fromAmount": str(amount_wei),
            "fromAddress": from_address,
            "toAddress": to_address or from_address,
            "slippage": slippage / 100,
        }
        
        response = await self.client.get(
            f"{self.base_url}{QUOTE_ENDPOINT}",
            params=params,
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        return self._parse_quote(data, from_chain, to_chain, from_token, amount)

    async def get_supported_chains(self) -> list[dict[str, Any]]:
        """Get list of chains supported by LI.FI."""
        response = await self.client.get(f"{self.base_url}{CHAINS_ENDPOINT}")
        response.raise_for_status()
        data = response.json()
        return data.get("chains", [])

    async def get_bridge_status(self, tx_hash: str, bridge: str) -> dict[str, Any]:
        """
        Check the status of a bridge transaction.
        
        Args:
            tx_hash: Transaction hash
            bridge: Bridge name used
            
        Returns:
            Status information dictionary
        """
        params = {"txHash": tx_hash, "bridge": bridge}
        response = await self.client.get(
            f"{self.base_url}{STATUS_ENDPOINT}",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    # --------------------------------------------------------------------------
    # HELPER METHODS
    # --------------------------------------------------------------------------

    def _resolve_token_address(
        self, token: str, chain: str
    ) -> Optional[str]:
        """Resolve token symbol to address."""
        if token.startswith("0x") and len(token) == 42:
            return token
        
        token_upper = token.upper()
        chain_lower = chain.lower()
        
        if token_upper in COMMON_TOKENS:
            return COMMON_TOKENS[token_upper].get(chain_lower)
        
        return None

    def _get_token_decimals(self, token: str) -> int:
        """Get token decimals (simplified)."""
        token_upper = token.upper()
        
        if token_upper in ["USDC", "USDT"]:
            return 6
        if token_upper in ["WBTC"]:
            return 8
        return 18

    def _parse_route(
        self,
        route: dict[str, Any],
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float,
    ) -> BridgeRoute:
        """Parse LI.FI route response into BridgeRoute."""
        from_chain_config = SUPPORTED_CHAINS[from_chain.lower()]
        to_chain_config = SUPPORTED_CHAINS[to_chain.lower()]
        
        steps = route.get("steps", [])
        
        bridge_name = "Unknown"
        estimated_time = 300
        
        if steps:
            first_step = steps[0]
            tool_details = first_step.get("toolDetails", {})
            bridge_name = tool_details.get("name", "Unknown")
            
            estimate = first_step.get("estimate", {})
            estimated_time = estimate.get("executionDuration", 300)
        
        gas_costs = route.get("gasCostUSD", "0")
        gas_cost_usd = float(gas_costs) if gas_costs else 0
        
        fee_costs = route.get("feeCostUSD", "0")
        bridge_fee_usd = float(fee_costs) if fee_costs else 0
        
        to_amount = route.get("toAmount", "0")
        decimals = self._get_token_decimals(token)
        estimated_output = int(to_amount) / (10 ** decimals) if to_amount else amount
        
        return BridgeRoute(
            from_chain=from_chain,
            from_chain_id=from_chain_config["chain_id"],
            to_chain=to_chain,
            to_chain_id=to_chain_config["chain_id"],
            token=token,
            token_address=self._resolve_token_address(token, from_chain) or "",
            amount=amount,
            bridge_name=bridge_name,
            estimated_time_seconds=estimated_time,
            gas_cost_usd=round(gas_cost_usd, 2),
            bridge_fee_usd=round(bridge_fee_usd, 2),
            total_cost_usd=round(gas_cost_usd + bridge_fee_usd, 2),
            estimated_output=round(estimated_output, 6),
            slippage_percent=0.5,
            tx_data=None,
        )

    def _parse_quote(
        self,
        quote: dict[str, Any],
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float,
    ) -> BridgeRoute:
        """Parse LI.FI quote response into BridgeRoute with tx data."""
        from_chain_config = SUPPORTED_CHAINS[from_chain.lower()]
        to_chain_config = SUPPORTED_CHAINS[to_chain.lower()]
        
        tool_details = quote.get("toolDetails", {})
        bridge_name = tool_details.get("name", "Unknown")
        
        estimate = quote.get("estimate", {})
        estimated_time = estimate.get("executionDuration", 300)
        
        gas_costs = estimate.get("gasCosts", [])
        gas_cost_usd = sum(
            float(g.get("amountUSD", 0)) for g in gas_costs
        )
        
        fee_costs = estimate.get("feeCosts", [])
        bridge_fee_usd = sum(
            float(f.get("amountUSD", 0)) for f in fee_costs
        )
        
        to_amount = estimate.get("toAmount", "0")
        decimals = self._get_token_decimals(token)
        estimated_output = int(to_amount) / (10 ** decimals) if to_amount else amount
        
        tx_data = quote.get("transactionRequest")
        
        return BridgeRoute(
            from_chain=from_chain,
            from_chain_id=from_chain_config["chain_id"],
            to_chain=to_chain,
            to_chain_id=to_chain_config["chain_id"],
            token=token,
            token_address=self._resolve_token_address(token, from_chain) or "",
            amount=amount,
            bridge_name=bridge_name,
            estimated_time_seconds=estimated_time,
            gas_cost_usd=round(gas_cost_usd, 2),
            bridge_fee_usd=round(bridge_fee_usd, 2),
            total_cost_usd=round(gas_cost_usd + bridge_fee_usd, 2),
            estimated_output=round(estimated_output, 6),
            slippage_percent=0.5,
            tx_data=tx_data,
        )


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================


async def get_best_bridge_route(
    from_chain: str,
    to_chain: str,
    token: str,
    amount: float,
    api_key: Optional[str] = None,
) -> Optional[BridgeRoute]:
    """
    Get the best bridge route for a transfer.
    
    Args:
        from_chain: Source chain
        to_chain: Destination chain
        token: Token symbol
        amount: Amount to bridge
        api_key: Optional LI.FI API key
        
    Returns:
        Best BridgeRoute or None
    """
    async with LiFiClient(api_key=api_key) as client:
        routes = await client.get_routes(
            from_chain=from_chain,
            to_chain=to_chain,
            from_token=token,
            to_token=token,
            amount=amount,
        )
    
    if not routes:
        return None
    
    return routes[0]


async def get_all_bridge_routes(
    from_chain: str,
    to_chains: list[str],
    token: str,
    amount: float,
    api_key: Optional[str] = None,
) -> dict[str, Optional[BridgeRoute]]:
    """
    Get bridge routes to multiple destination chains.
    
    Args:
        from_chain: Source chain
        to_chains: List of destination chains
        token: Token symbol
        amount: Amount to bridge
        api_key: Optional LI.FI API key
        
    Returns:
        Dictionary mapping chain to best route
    """
    results: dict[str, Optional[BridgeRoute]] = {}
    
    async with LiFiClient(api_key=api_key) as client:
        for to_chain in to_chains:
            if to_chain.lower() == from_chain.lower():
                results[to_chain] = None
                continue
            
            routes = await client.get_routes(
                from_chain=from_chain,
                to_chain=to_chain,
                from_token=token,
                to_token=token,
                amount=amount,
            )
            
            results[to_chain] = routes[0] if routes else None
    
    return results
