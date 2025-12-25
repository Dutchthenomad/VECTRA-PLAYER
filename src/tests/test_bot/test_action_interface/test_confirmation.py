"""
Tests for ConfirmationMonitor and MockConfirmationMonitor.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from bot.action_interface.confirmation import ConfirmationMonitor, MockConfirmationMonitor
from bot.action_interface.types import ActionType
from models.events.player_action import PlayerState
from services.event_bus import EventBus, Events


@pytest.fixture
def event_bus():
    """Create EventBus instance."""
    bus = EventBus()
    bus.start()
    yield bus
    bus.stop()


@pytest.fixture
def monitor(event_bus):
    """Create ConfirmationMonitor instance."""
    return ConfirmationMonitor(event_bus)


class TestConfirmationMonitor:
    """Test suite for ConfirmationMonitor."""

    def test_init(self, monitor):
        """Test monitor initialization."""
        assert monitor._max_pending == 100
        assert monitor._latency_window == 100
        assert not monitor._subscribed

    def test_start_subscribes_to_events(self, monitor, event_bus):
        """Test that start() subscribes to PLAYER_UPDATE events."""
        monitor.start()

        assert monitor._subscribed
        assert event_bus.has_subscribers(Events.PLAYER_UPDATE)

    def test_start_idempotent(self, monitor, event_bus):
        """Test that calling start() twice is safe."""
        monitor.start()
        monitor.start()  # Should not raise

        assert monitor._subscribed

    def test_stop_unsubscribes_from_events(self, monitor, event_bus):
        """Test that stop() unsubscribes from events."""
        monitor.start()
        monitor.stop()

        assert not monitor._subscribed
        # Note: event_bus.has_subscribers() may still return True if other
        # tests have subscribed, so we just check our flag

    def test_stop_clears_pending_actions(self, monitor):
        """Test that stop() clears pending actions."""
        monitor.start()

        # Register some pending actions
        monitor.register_pending("action1", ActionType.BUY)
        monitor.register_pending("action2", ActionType.SELL)

        assert len(monitor._pending) == 2

        monitor.stop()

        assert len(monitor._pending) == 0

    def test_register_pending_stores_action(self, monitor):
        """Test that register_pending() stores the action."""
        monitor.start()

        state = PlayerState(
            cash=Decimal("100"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )

        monitor.register_pending("action1", ActionType.BUY, state_before=state)

        assert len(monitor._pending) == 1
        pending = monitor._pending[0]
        assert pending.action_id == "action1"
        assert pending.action_type == ActionType.BUY
        assert pending.state_before == state

    def test_register_pending_with_callback(self, monitor):
        """Test registering pending action with callback."""
        monitor.start()

        callback = MagicMock()
        monitor.register_pending("action1", ActionType.BUY, callback=callback)

        assert len(monitor._pending) == 1
        assert monitor._pending[0].callback == callback

    def test_on_player_update_confirms_action(self, monitor, event_bus):
        """Test that PLAYER_UPDATE event confirms pending action."""
        monitor.start()

        # Register pending action
        state_before = PlayerState(
            cash=Decimal("100"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )

        callback = MagicMock()
        monitor.register_pending("action1", ActionType.BUY, state_before, callback)

        assert len(monitor._pending) == 1

        # Publish PLAYER_UPDATE event
        event_data = {
            "walletAddress": "test_wallet",
            "currentBalance": 90,
            "position": {
                "qty": 10,
                "avgCost": 1.0,
                "totalInvested": 10,
            },
            "cumulativePnl": -10,
        }

        event_bus.publish(Events.PLAYER_UPDATE, event_data)

        # Wait for event processing
        import time

        time.sleep(0.2)

        # Action should be confirmed
        assert len(monitor._pending) == 0

        # Callback should have been invoked
        callback.assert_called_once()

        # Check ActionResult
        result = callback.call_args[0][0]
        assert result.success
        assert result.action_id == "action1"
        assert result.action_type == ActionType.BUY
        assert result.state_before == state_before
        assert result.state_after is not None
        assert result.state_after.cash == Decimal("90")
        assert result.state_after.position_qty == Decimal("10")

    def test_latency_calculation(self, monitor, event_bus):
        """Test that latency is calculated correctly."""
        monitor.start()

        # Register pending action
        monitor.register_pending("action1", ActionType.BUY)

        assert len(monitor._latency_samples) == 0

        # Publish PLAYER_UPDATE event
        event_data = {
            "walletAddress": "test_wallet",
            "currentBalance": 100,
            "position": {"qty": 0, "avgCost": 0, "totalInvested": 0},
            "cumulativePnl": 0,
        }

        event_bus.publish(Events.PLAYER_UPDATE, event_data)

        # Wait for event processing
        import time

        time.sleep(0.2)

        # Latency sample should be recorded (>= 0ms, fast processing may be 0ms)
        assert len(monitor._latency_samples) == 1
        assert monitor._latency_samples[0] >= 0

    def test_get_latency_stats_empty(self, monitor):
        """Test latency stats with no samples."""
        stats = monitor.get_latency_stats()

        assert stats["avg_ms"] == 0.0
        assert stats["min_ms"] == 0
        assert stats["max_ms"] == 0
        assert stats["count"] == 0

    def test_get_latency_stats_with_samples(self, monitor):
        """Test latency stats with samples."""
        monitor.start()

        # Add some latency samples manually
        monitor._latency_samples.extend([10, 20, 30, 40, 50])

        stats = monitor.get_latency_stats()

        assert stats["avg_ms"] == 30.0
        assert stats["min_ms"] == 10
        assert stats["max_ms"] == 50
        assert stats["count"] == 5

    def test_fifo_matching(self, monitor, event_bus):
        """Test FIFO matching of pending actions."""
        monitor.start()

        # Register multiple pending actions
        callback1 = MagicMock()
        callback2 = MagicMock()

        monitor.register_pending("action1", ActionType.BUY, callback=callback1)
        monitor.register_pending("action2", ActionType.SELL, callback=callback2)

        assert len(monitor._pending) == 2

        # Publish PLAYER_UPDATE event (should confirm action1)
        event_data = {
            "walletAddress": "test_wallet",
            "currentBalance": 100,
            "position": {"qty": 0, "avgCost": 0, "totalInvested": 0},
            "cumulativePnl": 0,
        }

        event_bus.publish(Events.PLAYER_UPDATE, event_data)

        # Wait for event processing
        import time

        time.sleep(0.2)

        # First action should be confirmed
        callback1.assert_called_once()
        callback2.assert_not_called()
        assert len(monitor._pending) == 1

    def test_callback_error_handling(self, monitor, event_bus):
        """Test that callback errors don't crash the monitor."""
        monitor.start()

        # Register action with failing callback
        def failing_callback(result):
            raise ValueError("Test error")

        monitor.register_pending("action1", ActionType.BUY, callback=failing_callback)

        # Publish PLAYER_UPDATE event
        event_data = {
            "walletAddress": "test_wallet",
            "currentBalance": 100,
            "position": {"qty": 0, "avgCost": 0, "totalInvested": 0},
            "cumulativePnl": 0,
        }

        event_bus.publish(Events.PLAYER_UPDATE, event_data)

        # Wait for event processing
        import time

        time.sleep(0.2)

        # Action should still be confirmed (callback error handled)
        assert len(monitor._pending) == 0

    def test_no_pending_actions(self, monitor, event_bus):
        """Test that PLAYER_UPDATE with no pending actions is ignored."""
        monitor.start()

        # Publish PLAYER_UPDATE event with no pending actions
        event_data = {
            "walletAddress": "test_wallet",
            "currentBalance": 100,
            "position": {"qty": 0, "avgCost": 0, "totalInvested": 0},
            "cumulativePnl": 0,
        }

        event_bus.publish(Events.PLAYER_UPDATE, event_data)

        # Wait for event processing
        import time

        time.sleep(0.2)

        # No latency samples should be added
        assert len(monitor._latency_samples) == 0

    def test_max_pending_limit(self, monitor):
        """Test that pending actions are limited by maxlen."""
        monitor.start()

        # Fill up pending queue
        for i in range(150):
            monitor.register_pending(f"action{i}", ActionType.BUY)

        # Should only keep last 100 (max_pending)
        assert len(monitor._pending) == 100


class TestMockConfirmationMonitor:
    """Test suite for MockConfirmationMonitor."""

    def test_init(self):
        """Test mock monitor initialization."""
        mock = MockConfirmationMonitor()
        assert mock._simulated_latency_ms == 50

    def test_init_custom_latency(self):
        """Test mock monitor with custom latency."""
        mock = MockConfirmationMonitor(simulated_latency_ms=100)
        assert mock._simulated_latency_ms == 100

    def test_instant_confirm_success(self):
        """Test instant_confirm with successful action."""
        mock = MockConfirmationMonitor()

        state_before = PlayerState(
            cash=Decimal("100"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )

        state_after = PlayerState(
            cash=Decimal("90"),
            position_qty=Decimal("10"),
            avg_cost=Decimal("1.0"),
            total_invested=Decimal("10"),
            cumulative_pnl=Decimal("0"),
        )

        result = mock.instant_confirm(
            action_id="action1",
            action_type=ActionType.BUY,
            state_before=state_before,
            state_after=state_after,
            success=True,
            executed_price=Decimal("1.0"),
            executed_amount=Decimal("10"),
        )

        assert result.success
        assert result.action_id == "action1"
        assert result.action_type == ActionType.BUY
        assert result.state_before == state_before
        assert result.state_after == state_after
        assert result.executed_price == Decimal("1.0")
        assert result.executed_amount == Decimal("10")

    def test_instant_confirm_failure(self):
        """Test instant_confirm with failed action."""
        mock = MockConfirmationMonitor()

        result = mock.instant_confirm(
            action_id="action1",
            action_type=ActionType.BUY,
            success=False,
            error="Insufficient funds",
        )

        assert not result.success
        assert result.error == "Insufficient funds"

    def test_instant_confirm_timestamps(self):
        """Test that instant_confirm generates valid timestamps."""
        mock = MockConfirmationMonitor(simulated_latency_ms=100)

        result = mock.instant_confirm(
            action_id="action1",
            action_type=ActionType.BUY,
        )

        assert result.client_ts > 0
        assert result.server_ts is not None
        assert result.confirmed_ts is not None
        assert result.server_ts > result.client_ts
        assert result.confirmed_ts > result.server_ts
        assert result.total_latency_ms == 100

    def test_get_latency_stats(self):
        """Test latency stats for mock monitor."""
        mock = MockConfirmationMonitor(simulated_latency_ms=75)

        stats = mock.get_latency_stats()

        assert stats["avg_ms"] == 75.0
        assert stats["min_ms"] == 75
        assert stats["max_ms"] == 75
        assert stats["count"] == 0  # No actual samples in mock
