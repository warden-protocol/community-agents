import os
import requests
from typing import Optional, Tuple


def get_env(name: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"missing required env var: {name}")
    return value


# ---------- ETHEREUM RPC HELPERS ----------

def get_latest_block_number(rpc_url: str) -> int:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_blockNumber",
        "params": []
    }
    response = requests.post(rpc_url, json=payload, timeout=15)
    response.raise_for_status()
    return int(response.json()["result"], 16)


def get_tx_count(address: str, rpc_url: str) -> int:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getTransactionCount",
        "params": [address, "latest"]
    }
    response = requests.post(rpc_url, json=payload, timeout=15)
    response.raise_for_status()
    return int(response.json()["result"], 16)


# ---------- DEFILLAMA TVL HELPERS ----------

def get_protocol_tvl(protocol_slug: str) -> Optional[float]:
    base = get_env("DEFILLAMA_BASE_URL", default="https://api.llama.fi")
    try:
        response = requests.get(f"{base}/tvl/{protocol_slug}", timeout=15)
        response.raise_for_status()
        return float(response.json())
    except Exception:
        return None


# ---------- PLACEHOLDER / STUBS ----------

def detect_large_outflow_stub() -> float:
    return 0.0


def detect_pause_or_admin_event_stub() -> Tuple[bool, bool]:
    return False, False
