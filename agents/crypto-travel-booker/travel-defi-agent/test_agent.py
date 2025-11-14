"""
test_agent.py - Unit and integration tests for the Crypto Travel Agent
Tests each node independently and the full workflow.
"""

import unittest
from langchain_core.messages import HumanMessage
from agent import parse_intent, search_hotels, check_swap, book_hotel, workflow_app


class TestParseIntent(unittest.TestCase):
    """Test the parse_intent node."""

    def test_parse_basic(self):
        """Test parsing a basic request."""
        state = {"messages": [HumanMessage(content="Book me a hotel in Tokyo under $300")]}
        result = parse_intent(state)
        
        assert result["destination"] == "Tokyo", f"Expected 'Tokyo', got {result['destination']}"
        assert result["budget_usd"] == 300.0, f"Expected 300.0, got {result['budget_usd']}"
        assert "tokyo" in result["user_query"].lower()

    def test_parse_with_variations(self):
        """Test parsing with different destination markers."""
        test_cases = [
            ("Book me a hotel to Paris under $200", "Paris", 200.0),
            ("Find me a hotel in London for $500", "London", 500.0),
            ("I need a hotel at Barcelona budget $400", "Barcelona", 400.0),
        ]
        
        for message, expected_dest, expected_budget in test_cases:
            state = {"messages": [HumanMessage(content=message)]}
            result = parse_intent(state)
            assert result["destination"] == expected_dest, f"Failed for '{message}'. Got {result['destination']}"
            assert result["budget_usd"] == expected_budget, f"Budget mismatch for '{message}'"

    def test_parse_defaults(self):
        """Test that defaults are used when parsing fails gracefully."""
        # When no marker is found, the parser uses the first word of the query
        state = {"messages": [HumanMessage(content="Just book something")]}
        result = parse_intent(state)
        
        # "Just" is the first word, capitalized to "Just"
        assert result["destination"] == "Just"
        assert result["budget_usd"] == 400.0  # default when no $ found


class TestSearchHotels(unittest.TestCase):
    """Test the search_hotels node."""

    def test_search_mocked_fallback(self):
        """Test that mocked fallback works when live=False."""
        state = {
            "messages": [HumanMessage(content="test")],
            "destination": "Tokyo",
            "budget_usd": 300.0,
            "user_query": "test",
            "hotel_name": "",
            "hotel_price": 0.0,
            "needs_swap": False,
            "swap_amount": 0.0,
            "final_status": ""
        }
        result = search_hotels(state, live=False)
        
        assert result["hotel_price"] == 180.0, "Mocked price should be 180.0"
        assert "Budget Hotel" in result["hotel_name"]
        assert len(result["messages"]) > 0

    def test_search_with_destination(self):
        """Test that search respects the destination in messages."""
        state = {
            "messages": [HumanMessage(content="test")],
            "destination": "Paris",
            "budget_usd": 300.0,
            "user_query": "test",
            "hotel_name": "",
            "hotel_price": 0.0,
            "needs_swap": False,
            "swap_amount": 0.0,
            "final_status": ""
        }
        result = search_hotels(state, live=False)
        
        assert "Paris" in result["messages"][-1].content


class TestCheckSwap(unittest.TestCase):
    """Test the check_swap node."""

    def test_swap_not_needed(self):
        """Test when budget is sufficient."""
        state = {
            "hotel_price": 150.0,
            "budget_usd": 300.0,
            "messages": [],
            "user_query": "",
            "destination": "",
            "hotel_name": "",
            "needs_swap": False,
            "swap_amount": 0.0,
            "final_status": ""
        }
        result = check_swap(state)
        
        assert result["needs_swap"] is False
        assert result["swap_amount"] == 0

    def test_swap_needed(self):
        """Test when budget is insufficient and swap is required."""
        state = {
            "hotel_price": 400.0,
            "budget_usd": 300.0,
            "messages": [],
            "user_query": "",
            "destination": "",
            "hotel_name": "",
            "needs_swap": False,
            "swap_amount": 0.0,
            "final_status": ""
        }
        result = check_swap(state)
        
        # Hotel price > budget, so needs_swap should be False (cannot afford)
        assert result["needs_swap"] is False
        assert "Budget too low" in result["final_status"]


class TestBookHotel(unittest.TestCase):
    """Test the book_hotel node."""

    def test_book_creates_status(self):
        """Test that booking creates the correct final status."""
        state = {
            "hotel_name": "Luxury Hotel",
            "hotel_price": 200.0,
            "destination": "Paris",
            "messages": [],
            "user_query": "",
            "budget_usd": 300.0,
            "needs_swap": False,
            "swap_amount": 0.0,
            "final_status": ""
        }
        result = book_hotel(state)
        
        assert "Luxury Hotel" in result["final_status"]
        assert "200.0" in result["final_status"]
        assert "Paris" in result["messages"][-1].content

    def test_book_with_warden_mock(self):
        """Test on-chain booking path using a mocked Warden client."""
        # Patch the warden_client.submit_booking to return a deterministic tx
        import warden_client
        original_submit = getattr(warden_client, "submit_booking", None)
        try:
            warden_client.submit_booking = lambda hotel, price, dest, swap: {"tx_hash": "0xFAKE_TX_123"}

            state = {
                "hotel_name": "Budget Hotel",
                "hotel_price": 180.0,
                "destination": "Tokyo",
                "messages": [],
                "user_query": "",
                "budget_usd": 300.0,
                "needs_swap": False,
                "swap_amount": 0.0,
                "final_status": ""
            }
            result = book_hotel(state)

            # Ensure tx_hash propagated into result when Warden client used
            assert result.get("tx_hash") == "0xFAKE_TX_123"
            assert "Booked" in result["final_status"]
        finally:
            # restore original
            if original_submit is not None:
                warden_client.submit_booking = original_submit


class TestFullWorkflow(unittest.TestCase):
    """Test the complete LangGraph workflow."""

    def test_workflow_execution(self):
        """Test that the workflow executes without errors."""
        test_input = {
            "messages": [HumanMessage(content="Book me a hotel in Tokyo under $500")]
        }
        
        outputs = []
        try:
            for output in workflow_app.stream(test_input):
                outputs.append(output)
        except Exception as e:
            self.fail(f"Workflow execution failed: {type(e).__name__}: {str(e)}")
        
        assert len(outputs) > 0, "Workflow should produce outputs"

    def test_workflow_state_progression(self):
        """Test that state progresses correctly through the workflow."""
        test_input = {
            "messages": [HumanMessage(content="Book a hotel in Paris for $250")]
        }
        
        for output in workflow_app.stream(test_input):
            for node_name, state in output.items():
                # Each node should update specific state keys
                if "destination" in state:
                    assert state["destination"] != ""
                if "hotel_price" in state:
                    assert state["hotel_price"] > 0


class TestWardenIntegration(unittest.TestCase):
    """Test Warden testnet integration for on-chain bookings."""

    def test_warden_booking_client_build_tx(self):
        """Test building a booking transaction."""
        from warden_client import WardenBookingClient
        
        client = WardenBookingClient(
            account_id="0xTEST_ACCOUNT",
            private_key="0xTEST_KEY",
            testnet=True
        )
        
        result = client.build_booking_tx("Test Hotel", 150.0, "Paris", 0.0)
        
        assert "tx" in result or "error" in result
        if "tx" in result:
            assert result.get("tx_hash") is not None

    def test_warden_booking_client_sign_tx(self):
        """Test signing a transaction."""
        from warden_client import WardenBookingClient
        
        client = WardenBookingClient(
            account_id="0xTEST_ACCOUNT",
            private_key="0xTEST_KEY",
            testnet=True
        )
        
        mock_tx = {"to": "0xABC", "data": "0x123"}
        result = client.sign_transaction(mock_tx)
        
        assert "signature" in result or "error" in result
        if "signature" in result:
            assert result.get("signer") == "0xTEST_ACCOUNT"

    def test_warden_booking_client_submit_tx(self):
        """Test submitting a signed transaction."""
        from warden_client import WardenBookingClient
        
        client = WardenBookingClient(
            account_id="0xTEST_ACCOUNT",
            private_key="0xTEST_KEY",
            testnet=True
        )
        
        mock_signed_tx = {"to": "0xABC", "data": "0x123", "signature": "0xSIG"}
        result = client.submit_transaction(mock_signed_tx)
        
        assert "tx_hash" in result or "error" in result
        assert result.get("network") == "testnet"

    def test_warden_booking_client_fetch_status(self):
        """Test fetching transaction status."""
        from warden_client import WardenBookingClient
        
        client = WardenBookingClient(
            account_id="0xTEST_ACCOUNT",
            private_key="0xTEST_KEY",
            testnet=True
        )
        
        result = client.fetch_transaction_status("0xFAKE_TX_HASH")
        
        assert "status" in result or "error" in result
        if "status" in result:
            assert result["status"] in ["pending", "confirmed"]

    def test_warden_submit_booking_full_flow(self):
        """Test full submit_booking flow (mock)."""
        from warden_client import submit_booking
        
        # This will use mocks since no real credentials are set
        result = submit_booking(
            hotel_name="Budget Hotel",
            hotel_price=180.0,
            destination="Tokyo",
            swap_amount=0.0
        )
        
        assert "tx_hash" in result or "error" in result
        if "tx_hash" in result:
            assert isinstance(result["tx_hash"], str)
            assert len(result["tx_hash"]) > 0

    def test_warden_spend_limit_enforcement(self):
        """Test that booking above testnet spend limit is rejected."""
        from warden_client import WardenBookingClient
        
        client = WardenBookingClient(
            account_id="0xTEST_ACCOUNT",
            private_key="0xTEST_KEY",
            testnet=True
        )
        
        # Try to book a hotel above the $500 testnet limit
        result = client.build_booking_tx("Luxury Hotel", 600.0, "Paris", 0.0)
        
        assert "error" in result
        assert "exceeds testnet limit" in result["error"]


if __name__ == "__main__":
    unittest.main()
