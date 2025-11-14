"""
Warden Protocol integration for on-chain booking confirmations.

This module provides functions to:
1. Build and sign booking transactions on Warden testnet
2. Submit signed transactions to the Warden network
3. Fetch transaction status and confirmation details

It includes a testnet spend limit ($500 max per booking) to prevent
accidental large transactions during testing. Falls back to deterministic
mocks when Warden SDK is unavailable.
"""
import os
import json
from typing import Dict, Optional

# Attempt to import the Warden SDK (testnet-compatible version)
try:
    # In production, this would be: from warden_sdk import WardenClient
    # For now, we define a minimal interface that can be implemented with the real SDK
    import warden_sdk  # type: ignore
    _HAS_WARDEN_SDK = True
except Exception:
    _HAS_WARDEN_SDK = False

# ============================================================================
# GUARDRAIL: Testnet spend limit
# ============================================================================
# Hard limit to prevent accidental large bookings during testnet validation.
# This is enforced in build_booking_tx() before any SDK calls are made.
TESTNET_MAX_SPEND_USD = 500.0


class WardenBookingClient:
    """Lightweight Warden client for booking transactions on testnet."""

    def __init__(self, account_id: str, private_key: str, testnet: bool = True):
        """Initialize Warden client with account and signing credentials.

        Args:
            account_id: Warden account/address identifier
            private_key: Private key for signing transactions (base64 or hex)
            testnet: If True, use testnet; otherwise use mainnet
        """
        self.account_id = account_id
        self.private_key = private_key
        self.testnet = testnet
        self.network = "testnet" if testnet else "mainnet"

        # If SDK is available, initialize it; otherwise we'll use mock stubs
        if _HAS_WARDEN_SDK:
            try:
                self.sdk_client = warden_sdk.WardenClient(
                    api_key=os.getenv("WARDEN_API_KEY", ""),
                    account_id=account_id,
                    network="testnet" if testnet else "mainnet"
                )
            except Exception as e:
                print(f"[WARN] Failed to initialize Warden SDK: {e}. Using mock fallback.")
                self.sdk_client = None
        else:
            self.sdk_client = None

    def build_booking_tx(self, hotel_name: str, hotel_price: float, destination: str, swap_amount: float) -> Dict:
        """Build an unsigned booking transaction payload.

        Args:
            hotel_name: Name of the hotel being booked
            hotel_price: Price in USD
            destination: City/location
            swap_amount: USDC swap amount needed (0 if no swap)

        Returns:
            Dict with tx data or error
        """
        # ========================================================================
        # GUARDRAIL ENFORCEMENT: Testnet spend limit
        # ========================================================================
        # Reject any booking exceeding $500 testnet max. This prevents:
        # - Accidental large transactions during testing
        # - Runaway swaps due to market volatility
        # - Slippage disasters on low-liquidity testnet pairs
        if hotel_price > TESTNET_MAX_SPEND_USD:
            return {
                "error": f"Booking exceeds testnet limit (${hotel_price} > ${TESTNET_MAX_SPEND_USD})"
            }

        if self.sdk_client:
            try:
                # Example SDK call (adjust based on real Warden SDK API)
                tx_data = self.sdk_client.build_booking_tx(
                    to_address="booking_contract_address",
                    hotel_name=hotel_name,
                    price_usd=hotel_price,
                    destination=destination,
                    swap_usd=swap_amount
                )
                return {"tx": tx_data, "tx_hash": getattr(tx_data, "hash", None)}
            except Exception as e:
                print(f"[WARN] SDK tx build failed: {e}. Using mock.")
                return self._mock_booking_tx(hotel_name, hotel_price, destination, swap_amount)
        else:
            return self._mock_booking_tx(hotel_name, hotel_price, destination, swap_amount)

    def _mock_booking_tx(self, hotel_name: str, hotel_price: float, destination: str, swap_amount: float) -> Dict:
        """Generate a mock booking transaction payload."""
        mock_tx_hash = f"0xMOCK_{abs(hash((hotel_name, hotel_price, destination))) & ((1<<64)-1):016x}"
        return {
            "tx": {
                "to": "0xWARDEN_BOOKING_CONTRACT",
                "data": json.dumps({
                    "action": "book_hotel",
                    "hotel": hotel_name,
                    "price_usd": hotel_price,
                    "destination": destination,
                    "swap_usd": swap_amount
                }),
                "value": 0
            },
            "tx_hash": mock_tx_hash
        }

    def sign_transaction(self, tx_data: Dict) -> Dict:
        """Sign a transaction with the stored private key.

        Args:
            tx_data: Unsigned transaction data

        Returns:
            Dict with signed tx and signature
        """
        try:
            if self.sdk_client:
                # Example SDK call: sign transaction
                signed_tx = self.sdk_client.sign_tx(tx_data, self.private_key)
                return {
                    "signed_tx": signed_tx,
                    "signature": getattr(signed_tx, "signature", ""),
                    "signer": self.account_id
                }
            else:
                # Mock signature
                mock_sig = f"0xSIG_{abs(hash((self.account_id, str(tx_data)))) & ((1<<64)-1):016x}"
                return {
                    "signed_tx": tx_data,
                    "signature": mock_sig,
                    "signer": self.account_id
                }
        except Exception as e:
            return {"error": f"Sign failed: {type(e).__name__}: {e}"}

    def submit_transaction(self, signed_tx: Dict) -> Dict:
        """Submit a signed transaction to the network.

        Args:
            signed_tx: Signed transaction data

        Returns:
            Dict with tx_hash and status
        """
        try:
            if self.sdk_client:
                # Example SDK call: send transaction
                result = self.sdk_client.send_tx(signed_tx)
                return {
                    "tx_hash": getattr(result, "hash", ""),
                    "status": "pending",
                    "network": self.network
                }
            else:
                # Mock submission
                mock_tx_hash = getattr(signed_tx, "tx_hash", "") or f"0xMOCK_{abs(hash(str(signed_tx))) & ((1<<64)-1):016x}"
                return {
                    "tx_hash": mock_tx_hash,
                    "status": "pending",
                    "network": self.network
                }
        except Exception as e:
            return {"error": f"Submit failed: {type(e).__name__}: {e}"}

    def fetch_transaction_status(self, tx_hash: str) -> Dict:
        """Fetch the status of a submitted transaction.

        Args:
            tx_hash: Transaction hash to query

        Returns:
            Dict with status, confirmations, block number
        """
        try:
            if self.sdk_client:
                # Example SDK call: get tx receipt
                receipt = self.sdk_client.get_tx_receipt(tx_hash)
                return {
                    "tx_hash": tx_hash,
                    "status": "confirmed" if receipt else "pending",
                    "confirmations": getattr(receipt, "confirmations", 0),
                    "block_number": getattr(receipt, "block_number", None)
                }
            else:
                # Mock status (always confirmed for testing)
                return {
                    "tx_hash": tx_hash,
                    "status": "confirmed",
                    "confirmations": 3,
                    "block_number": 12345
                }
        except Exception as e:
            return {"error": f"Status fetch failed: {type(e).__name__}: {e}"}


def submit_booking(hotel_name: str, hotel_price: float, destination: str, swap_amount: float) -> Dict:
    """High-level function: build, sign, and submit a booking transaction.

    This is the main entry point for the agent's book_hotel node.

    Args:
        hotel_name: Hotel name
        hotel_price: Price in USD
        destination: City/location
        swap_amount: USDC swap amount

    Returns:
        Dict with tx_hash, status, or error
    """
    account_id = os.getenv("WARDEN_ACCOUNT_ID")
    private_key = os.getenv("WARDEN_PRIVATE_KEY")

    # If credentials not set, return mock result
    if not account_id or not private_key:
        print("[WARDEN] No credentials configured. Using mock booking.")
        client = WardenBookingClient(
            account_id="0xMOCK_ACCOUNT",
            private_key="0xMOCK_KEY",
            testnet=True
        )
    else:
        client = WardenBookingClient(account_id, private_key, testnet=True)

    # Step 1: Build unsigned transaction
    print(f"[WARDEN] Building booking tx: {hotel_name} (${hotel_price}) in {destination}")
    tx_result = client.build_booking_tx(hotel_name, hotel_price, destination, swap_amount)
    if "error" in tx_result:
        print(f"[WARDEN] Build failed: {tx_result['error']}")
        return tx_result

    # Step 2: Sign the transaction
    print("[WARDEN] Signing transaction...")
    sign_result = client.sign_transaction(tx_result.get("tx", {}))
    if "error" in sign_result:
        print(f"[WARDEN] Sign failed: {sign_result['error']}")
        return sign_result

    # Step 3: Submit the signed transaction
    print("[WARDEN] Submitting to testnet...")
    submit_result = client.submit_transaction(sign_result.get("signed_tx", {}))
    if "error" in submit_result:
        print(f"[WARDEN] Submit failed: {submit_result['error']}")
        return submit_result

    tx_hash = submit_result.get("tx_hash", "")
    print(f"[WARDEN] Booking submitted! tx_hash={tx_hash}")

    # Step 4: Optionally fetch immediate status
    if tx_hash:
        status_result = client.fetch_transaction_status(tx_hash)
        submit_result.update(status_result)

    return submit_result
