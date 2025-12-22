"""
Tests for Live Balance Display with Visual Indicator (Phase 12D Task 2).

This test suite verifies:
1. Balance display uses LiveStateProvider.cash when is_connected is True
2. Visual indicator shows green for LIVE mode
3. Visual indicator shows gray for LOCAL mode
4. Balance updates correctly when PLAYER_UPDATE events fire
"""

import tkinter as tk
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from core.game_state import GameState
from services.event_bus import EventBus, Events
from services.live_state_provider import LiveStateProvider


@pytest.fixture
def mock_root():
    """Create a mock Tk root."""
    root = MagicMock(spec=tk.Tk)
    root.after = MagicMock()
    return root


@pytest.fixture
def event_bus():
    """Create and start real EventBus for testing."""
    bus = EventBus()
    bus.start()  # Start the processing thread
    yield bus
    bus.stop()  # Clean up after test


@pytest.fixture
def game_state():
    """Create real GameState for testing."""
    return GameState()


@pytest.fixture
def live_state_provider(event_bus):
    """Create real LiveStateProvider for testing."""
    return LiveStateProvider(event_bus)


@pytest.fixture
def mock_main_window(mock_root, event_bus, game_state, live_state_provider):
    """
    Create a minimal MainWindow-like object for testing _update_balance_from_live_state.

    This avoids complex MainWindow initialization by creating a simple mock.
    """
    # Create a simple object with required attributes
    window = MagicMock()
    window.state = game_state
    window.event_bus = event_bus
    window.live_state_provider = live_state_provider
    window.balance_locked = True
    window.balance_label = MagicMock(spec=tk.Label)

    # Create mock UI dispatcher that executes immediately
    window.ui_dispatcher = MagicMock()
    window.ui_dispatcher.submit = MagicMock(side_effect=lambda fn: fn())

    # Import the actual method from MainWindow
    from ui.main_window import MainWindow

    # Bind the method to our mock window
    window._update_balance_from_live_state = MainWindow._update_balance_from_live_state.__get__(
        window
    )
    window._handle_player_update = MainWindow._handle_player_update.__get__(window)
    window._reset_server_state = MainWindow._reset_server_state.__get__(window)

    # Mock additional attributes needed by _reset_server_state
    window.server_username = None
    window.server_balance = None
    window.server_authenticated = False
    window.player_profile_label = MagicMock(spec=tk.Label)

    return window


class TestLiveBalanceDisplay:
    """Test live balance display functionality."""

    def test_local_mode_shows_gray_balance(self, mock_main_window, game_state):
        """Test that LOCAL mode shows GameState balance in gray."""
        # Setup: Set local balance
        game_state.update(balance=Decimal("10.5000"))

        # Execute: Update balance from live state (should use local)
        mock_main_window._update_balance_from_live_state()

        # Verify: Balance label shows local balance in gray
        mock_main_window.balance_label.config.assert_called_once()
        call_args = mock_main_window.balance_label.config.call_args

        assert call_args[1]["text"] == "WALLET: 10.5000 SOL"
        assert call_args[1]["fg"] == "#888888"  # Gray = LOCAL

    def test_live_mode_shows_green_balance(self, mock_main_window, live_state_provider, event_bus):
        """Test that LIVE mode shows LiveStateProvider balance in green."""
        import time

        # Setup: Simulate PLAYER_UPDATE event to set live state
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "25.7500",
                "positionQty": "0",
                "avgCost": "0",
                "cumulativePnL": "0",
                "totalInvested": "0",
                "playerId": "test_player_123",
                "username": "TestUser",
                "gameId": "game_456",
            },
        )

        # Wait for event to be processed
        time.sleep(0.1)

        # Verify LiveStateProvider received data
        assert live_state_provider.is_connected is True
        assert live_state_provider.cash == Decimal("25.7500")
        assert live_state_provider.username == "TestUser"

        # Execute: Update balance from live state (should use server)
        mock_main_window._update_balance_from_live_state()

        # Verify: Balance label shows server balance in green
        mock_main_window.balance_label.config.assert_called_once()
        call_args = mock_main_window.balance_label.config.call_args

        assert call_args[1]["text"] == "WALLET: 25.7500 SOL"
        assert call_args[1]["fg"] == "#00ff88"  # Green = LIVE

    def test_balance_updates_on_player_update(
        self, mock_main_window, live_state_provider, event_bus
    ):
        """Test that balance updates when PLAYER_UPDATE event fires."""
        import time

        # Setup: Initial PLAYER_UPDATE to LiveStateProvider
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "15.0000",
                "positionQty": "0",
                "avgCost": "0",
                "cumulativePnL": "0",
                "totalInvested": "0",
                "playerId": "test_player",
                "username": "Player1",
                "gameId": "game_1",
            },
        )

        # Wait for event to be processed
        time.sleep(0.1)

        # Execute: Trigger _handle_player_update via event
        # Create a server_state mock object with cash attribute
        server_state = MagicMock()
        server_state.cash = Decimal("15.0000")

        mock_main_window._handle_player_update({"data": {"server_state": server_state}})

        # Verify: Balance was updated
        assert mock_main_window.balance_label.config.called

        # Verify: Balance shows LIVE value
        call_args = mock_main_window.balance_label.config.call_args
        assert call_args[1]["text"] == "WALLET: 15.0000 SOL"
        assert call_args[1]["fg"] == "#00ff88"

    def test_balance_transitions_from_local_to_live(
        self, mock_main_window, game_state, live_state_provider, event_bus
    ):
        """Test balance display transitions from LOCAL to LIVE mode."""
        import time

        # Setup: Start in LOCAL mode
        game_state.update(balance=Decimal("10.0000"))
        mock_main_window._update_balance_from_live_state()

        # Verify: Shows local balance in gray
        call_args_1 = mock_main_window.balance_label.config.call_args
        assert call_args_1[1]["text"] == "WALLET: 10.0000 SOL"
        assert call_args_1[1]["fg"] == "#888888"  # Gray

        # Execute: Connect to live feed
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "20.0000",
                "positionQty": "0",
                "avgCost": "0",
                "cumulativePnL": "0",
                "totalInvested": "0",
                "playerId": "test_player",
                "username": "LiveUser",
                "gameId": "game_1",
            },
        )

        # Wait for event processing
        time.sleep(0.1)

        # Update balance display
        mock_main_window._update_balance_from_live_state()

        # Verify: Shows server balance in green
        call_args_2 = mock_main_window.balance_label.config.call_args
        assert call_args_2[1]["text"] == "WALLET: 20.0000 SOL"
        assert call_args_2[1]["fg"] == "#00ff88"  # Green

    def test_balance_transitions_from_live_to_local(
        self, mock_main_window, game_state, live_state_provider, event_bus
    ):
        """Test balance display transitions from LIVE to LOCAL mode."""
        import time

        # Setup: Start in LIVE mode
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "30.0000",
                "positionQty": "0",
                "avgCost": "0",
                "cumulativePnL": "0",
                "totalInvested": "0",
                "playerId": "test_player",
                "username": "DisconnectUser",
                "gameId": "game_1",
            },
        )

        time.sleep(0.1)
        mock_main_window._update_balance_from_live_state()

        # Verify: Shows server balance in green
        call_args_1 = mock_main_window.balance_label.config.call_args
        assert call_args_1[1]["fg"] == "#00ff88"

        # Execute: Disconnect from live feed
        event_bus.publish(Events.WS_SOURCE_CHANGED, {"source": "replay"})
        time.sleep(0.1)

        # Update local balance
        game_state.update(balance=Decimal("12.0000"))
        mock_main_window._update_balance_from_live_state()

        # Verify: Shows local balance in gray
        call_args_2 = mock_main_window.balance_label.config.call_args
        assert call_args_2[1]["text"] == "WALLET: 12.0000 SOL"
        assert call_args_2[1]["fg"] == "#888888"  # Gray

    def test_balance_unlocked_skips_update(self, mock_main_window, game_state):
        """Test that balance updates are skipped when balance is unlocked."""
        # Setup: Unlock balance
        mock_main_window.balance_locked = False
        game_state.update(balance=Decimal("10.0000"))

        # Execute: Try to update balance
        mock_main_window._update_balance_from_live_state()

        # Verify: No update occurred
        mock_main_window.balance_label.config.assert_not_called()

    def test_reset_server_state_calls_update_balance(self, mock_main_window):
        """Test that _reset_server_state calls _update_balance_from_live_state."""
        # Mock the _update_balance_from_live_state method
        with patch.object(mock_main_window, "_update_balance_from_live_state") as mock_update:
            # Execute: Reset server state
            mock_main_window._reset_server_state()

            # Verify: Balance update was called
            mock_update.assert_called_once()

    def test_live_state_provider_properties(self, live_state_provider, event_bus):
        """Test LiveStateProvider properties used by balance display."""
        import time

        # Setup: Publish PLAYER_UPDATE
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "50.1234",
                "positionQty": "0",
                "avgCost": "0",
                "cumulativePnL": "0",
                "totalInvested": "0",
                "playerId": "player_xyz",
                "username": "TestPlayer",
                "gameId": "game_abc",
            },
        )

        # Wait for event processing (EventBus is async)
        time.sleep(0.1)

        # Verify: Properties are accessible
        assert live_state_provider.is_connected is True
        assert live_state_provider.cash == Decimal("50.1234")
        assert live_state_provider.username == "TestPlayer"
        assert live_state_provider.player_id == "player_xyz"

    def test_multiple_player_updates(self, mock_main_window, live_state_provider, event_bus):
        """Test that multiple PLAYER_UPDATE events update balance correctly."""
        import time

        balances = ["10.0000", "15.5000", "20.7500", "18.2500"]

        for balance in balances:
            # Publish update
            event_bus.publish(
                Events.PLAYER_UPDATE,
                {
                    "cash": balance,
                    "positionQty": "0",
                    "avgCost": "0",
                    "cumulativePnL": "0",
                    "totalInvested": "0",
                    "playerId": "test_player",
                    "username": "MultiUser",
                    "gameId": "game_1",
                },
            )

            # Wait for event processing
            time.sleep(0.1)

            # Update display
            mock_main_window._update_balance_from_live_state()

            # Verify: Balance matches current value
            call_args = mock_main_window.balance_label.config.call_args
            assert call_args[1]["text"] == f"WALLET: {balance} SOL"
            assert call_args[1]["fg"] == "#00ff88"
