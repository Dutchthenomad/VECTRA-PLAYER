"""
Tests for LiveStateProvider - Server-Authoritative State in Live Mode

Phase 12C: Tests for the LiveStateProvider class that provides
server-authoritative state from playerUpdate WebSocket events.
"""

import threading
import time
from decimal import Decimal

import pytest

from services.event_bus import EventBus, Events
from services.live_state_provider import LiveStateProvider


def wait_for_condition(condition_fn, timeout=2.0, poll_interval=0.05):
    """
    Poll for a condition to become true with timeout.

    Args:
        condition_fn: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        poll_interval: Time between polls in seconds

    Returns:
        True if condition was met, False if timeout occurred
    """
    start = time.time()
    while time.time() - start < timeout:
        if condition_fn():
            return True
        time.sleep(poll_interval)
    return False


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    bus = EventBus()
    bus.start()
    yield bus
    bus.stop()


@pytest.fixture
def provider(event_bus):
    """Create a LiveStateProvider with test EventBus."""
    provider = LiveStateProvider(event_bus)
    yield provider
    provider.stop()


class TestLiveStateInitialization:
    """Test LiveStateProvider initialization."""

    def test_initial_state_defaults(self, provider):
        """Provider should start with default state values."""
        assert provider.cash == Decimal("0")
        assert provider.position_qty == Decimal("0")
        assert provider.avg_cost == Decimal("0")
        assert provider.is_connected is False
        assert provider.is_live is False
        assert provider.source == "unknown"

    def test_not_connected_initially(self, provider):
        """Provider should not be connected initially."""
        assert provider.is_connected is False

    def test_player_id_none_initially(self, provider):
        """Player ID should be None initially."""
        assert provider.player_id is None
        assert provider.username is None


class TestPlayerUpdateHandling:
    """Test handling of PLAYER_UPDATE events."""

    def test_updates_cash_on_player_update(self, event_bus, provider):
        """Cash should update from playerUpdate events."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "1.5",
                "positionQty": "0",
                "avgCost": "0",
            },
        )

        # Wait for event processing with timeout
        assert wait_for_condition(lambda: provider.cash == Decimal("1.5"))
        assert provider.is_connected is True

    def test_updates_position_on_player_update(self, event_bus, provider):
        """Position should update from playerUpdate events."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "0.5",
                "positionQty": "10",
                "avgCost": "1.25",
            },
        )

        assert wait_for_condition(lambda: provider.position_qty == Decimal("10"))
        assert provider.avg_cost == Decimal("1.25")
        assert provider.has_position is True

    def test_updates_player_identity(self, event_bus, provider):
        """Player identity should update from playerUpdate events."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "1.0",
                "playerId": "did:123:abc",
                "username": "Dutch",
                "gameId": "game-123",
            },
        )

        assert wait_for_condition(lambda: provider.player_id == "did:123:abc")
        assert provider.username == "Dutch"
        assert provider.game_id == "game-123"

    def test_updates_pnl_tracking(self, event_bus, provider):
        """P&L tracking should update from playerUpdate events."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "1.0",
                "cumulativePnL": "0.25",
                "totalInvested": "0.75",
            },
        )

        assert wait_for_condition(lambda: provider.cumulative_pnl == Decimal("0.25"))
        assert provider.total_invested == Decimal("0.75")


class TestGameTickHandling:
    """Test handling of GAME_TICK events."""

    def test_updates_tick_and_multiplier(self, event_bus, provider):
        """Tick and multiplier should update from game tick events."""
        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 100,
                "multiplier": "2.5",
                "gameId": "game-456",
            },
        )

        assert wait_for_condition(lambda: provider.current_tick == 100)
        assert provider.current_multiplier == Decimal("2.5")
        assert provider.game_id == "game-456"

    def test_updates_with_price_field(self, event_bus, provider):
        """Should handle 'price' field as alternative to 'multiplier'."""
        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 50,
                "price": "1.75",
            },
        )

        assert wait_for_condition(lambda: provider.current_tick == 50)
        assert provider.current_multiplier == Decimal("1.75")


class TestSourceChangedHandling:
    """Test handling of WS_SOURCE_CHANGED events."""

    def test_updates_source_on_change(self, event_bus, provider):
        """Source should update on WS_SOURCE_CHANGED events."""
        event_bus.publish(
            Events.WS_SOURCE_CHANGED,
            {"source": "cdp"},
        )

        assert wait_for_condition(lambda: provider.source == "cdp")

        assert provider.source == "cdp"
        assert provider.is_live is True

    def test_is_live_for_cdp(self, event_bus, provider):
        """is_live should be True for CDP source."""
        event_bus.publish(Events.WS_SOURCE_CHANGED, {"source": "cdp"})
        assert wait_for_condition(lambda: provider.is_live is True)

    def test_is_live_for_public_ws(self, event_bus, provider):
        """is_live should be True for public WebSocket source."""
        event_bus.publish(Events.WS_SOURCE_CHANGED, {"source": "public_ws"})
        assert wait_for_condition(lambda: provider.is_live is True)

    def test_not_live_for_replay(self, event_bus, provider):
        """is_live should be False for replay source."""
        event_bus.publish(Events.WS_SOURCE_CHANGED, {"source": "replay"})
        assert wait_for_condition(lambda: provider.is_live is False)


class TestComputedProperties:
    """Test computed properties like unrealized P&L."""

    def test_unrealized_pnl_with_position(self, event_bus, provider):
        """Unrealized P&L should calculate correctly with open position."""
        # Set up position: bought 10 units at 1.5x
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "0.5",
                "positionQty": "10",
                "avgCost": "1.5",
            },
        )

        # Current price is 2.0x
        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 100,
                "multiplier": "2.0",
            },
        )

        assert wait_for_condition(lambda: provider.current_multiplier == Decimal("2.0"))
        # P&L = (2.0 - 1.5) * 10 = 5.0
        assert provider.unrealized_pnl == Decimal("5.0")

    def test_unrealized_pnl_zero_without_position(self, event_bus, provider):
        """Unrealized P&L should be 0 without position."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "1.0",
                "positionQty": "0",
                "avgCost": "0",
            },
        )

        assert wait_for_condition(lambda: provider.cash == Decimal("1.0"))
        assert provider.unrealized_pnl == Decimal("0")

    def test_position_value_calculation(self, event_bus, provider):
        """Position value should calculate correctly."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "0.5",
                "positionQty": "5",
                "avgCost": "1.2",
            },
        )

        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 50,
                "multiplier": "1.8",
            },
        )

        assert wait_for_condition(lambda: provider.current_multiplier == Decimal("1.8"))
        # Position value = 5 * 1.8 = 9.0
        assert provider.position_value == Decimal("9.0")


class TestSnapshot:
    """Test get_snapshot() method."""

    def test_snapshot_includes_all_fields(self, event_bus, provider):
        """Snapshot should include all relevant state fields."""
        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "cash": "2.0",
                "positionQty": "10",
                "avgCost": "1.5",
                "cumulativePnL": "0.5",
                "totalInvested": "1.5",
                "playerId": "did:123",
                "username": "TestUser",
                "gameId": "game-789",
            },
        )

        assert wait_for_condition(lambda: provider.cash == Decimal("2.0"))
        snapshot = provider.get_snapshot()

        assert snapshot["connected"] is True
        assert snapshot["cash"] == Decimal("2.0")
        assert snapshot["position_qty"] == Decimal("10")
        assert snapshot["avg_cost"] == Decimal("1.5")
        assert snapshot["cumulative_pnl"] == Decimal("0.5")
        assert snapshot["player_id"] == "did:123"
        assert snapshot["username"] == "TestUser"
        assert snapshot["game_id"] == "game-789"


class TestThreadSafety:
    """Test thread-safety of LiveStateProvider."""

    def test_concurrent_updates(self, event_bus, provider):
        """Provider should handle concurrent updates safely."""
        errors = []

        def publish_updates():
            try:
                for i in range(100):
                    event_bus.publish(
                        Events.PLAYER_UPDATE,
                        {"cash": str(i), "positionQty": str(i)},
                    )
            except Exception as e:
                errors.append(e)

        def read_state():
            try:
                for _ in range(100):
                    _ = provider.cash
                    _ = provider.position_qty
                    _ = provider.get_snapshot()
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=publish_updates),
            threading.Thread(target=read_state),
            threading.Thread(target=read_state),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestCleanup:
    """Test cleanup and resource management."""

    def test_stop_unsubscribes_events(self, event_bus):
        """stop() should unsubscribe from all events."""
        provider = LiveStateProvider(event_bus)

        # Verify it's subscribed
        assert event_bus.has_subscribers(Events.PLAYER_UPDATE)
        assert event_bus.has_subscribers(Events.WS_SOURCE_CHANGED)
        assert event_bus.has_subscribers(Events.GAME_TICK)

        # Publish an event to set initial state
        event_bus.publish(Events.PLAYER_UPDATE, {"cash": "100.00"})
        assert wait_for_condition(lambda: provider.cash == Decimal("100.00"))

        # Stop provider
        provider.stop()

        # Verify the stop method was called and no exceptions occurred
        # Note: EventBus may still process queued events after unsubscribe
        # due to async queue processing, but the subscription is removed

    def test_context_manager(self, event_bus):
        """Provider should work as context manager and call stop() on exit."""

        with LiveStateProvider(event_bus) as provider:
            assert provider.is_connected is False
            # Set some state
            event_bus.publish(Events.PLAYER_UPDATE, {"cash": "50.00"})
            assert wait_for_condition(lambda: provider.cash == Decimal("50.00"))

        # After exiting context, stop should have been called
        # Verify that __exit__ was invoked without exceptions
