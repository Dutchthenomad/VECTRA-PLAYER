"""
Tests for StateTracker - Hybrid state capture for BotActionInterface.
"""

import time
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, PropertyMock

import pytest

from bot.action_interface.state.tracker import StateTracker
from bot.action_interface.types import ActionParams, ActionResult, ActionType, GameContext
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
def mock_game_state():
    """Create mock GameState."""
    state = MagicMock()
    state.get.side_effect = lambda key, default=None: {
        "balance": Decimal("0.150"),
        "position": {
            "status": "active",
            "amount": Decimal("0.05"),
            "entry_price": Decimal("2.0"),
        },
        "initial_balance": Decimal("0.100"),
        "current_tick": 42,
        "current_price": Decimal("2.5"),
        "current_phase": "ACTIVE",
        "game_id": "test_game_123",
        "game_active": True,
    }.get(key, default)

    # Mock get_snapshot
    state.get_snapshot.return_value = MagicMock(
        game_id="test_game_123",
        tick=42,
        price=Decimal("2.5"),
        phase="ACTIVE",
        active=True,
        rugged=False,
    )

    return state


@pytest.fixture
def mock_live_state_provider():
    """Create mock LiveStateProvider."""
    provider = MagicMock()

    # Configure properties
    type(provider).is_live = PropertyMock(return_value=True)
    type(provider).cash = PropertyMock(return_value=Decimal("0.180"))
    type(provider).position_qty = PropertyMock(return_value=Decimal("0.06"))
    type(provider).avg_cost = PropertyMock(return_value=Decimal("2.2"))
    type(provider).total_invested = PropertyMock(return_value=Decimal("0.132"))
    type(provider).cumulative_pnl = PropertyMock(return_value=Decimal("0.025"))

    return provider


class TestStateTrackerInitialization:
    """Test StateTracker initialization."""

    def test_init_without_live_provider(self, mock_game_state, event_bus):
        """Test initialization without LiveStateProvider."""
        tracker = StateTracker(mock_game_state, event_bus)

        assert tracker._game_state == mock_game_state
        assert tracker._event_bus == event_bus
        assert tracker._live_state_provider is None
        assert not tracker._is_live_mode()

    def test_init_with_live_provider(self, mock_game_state, event_bus, mock_live_state_provider):
        """Test initialization with LiveStateProvider."""
        tracker = StateTracker(mock_game_state, event_bus, mock_live_state_provider)

        assert tracker._game_state == mock_game_state
        assert tracker._event_bus == event_bus
        assert tracker._live_state_provider == mock_live_state_provider
        assert tracker._is_live_mode()


class TestCaptureStateBefore:
    """Test capture_state_before in different modes."""

    def test_capture_state_replay_mode(self, mock_game_state, event_bus):
        """Test state capture in replay mode (no LiveStateProvider)."""
        tracker = StateTracker(mock_game_state, event_bus)

        state = tracker.capture_state_before()

        assert isinstance(state, PlayerState)
        assert state.cash == Decimal("0.150")
        assert state.position_qty == Decimal("0.05")
        assert state.avg_cost == Decimal("2.0")
        assert state.total_invested == Decimal("0.10")  # 0.05 * 2.0
        assert state.cumulative_pnl == Decimal("0.050")  # 0.150 - 0.100

    def test_capture_state_replay_mode_no_position(self, mock_game_state, event_bus):
        """Test state capture in replay mode with no position."""
        # Override position to None
        mock_game_state.get.side_effect = lambda key, default=None: {
            "balance": Decimal("0.100"),
            "position": None,
            "initial_balance": Decimal("0.100"),
        }.get(key, default)

        tracker = StateTracker(mock_game_state, event_bus)
        state = tracker.capture_state_before()

        assert state.cash == Decimal("0.100")
        assert state.position_qty == Decimal("0")
        assert state.avg_cost == Decimal("0")
        assert state.total_invested == Decimal("0")
        assert state.cumulative_pnl == Decimal("0")

    def test_capture_state_live_mode(self, mock_game_state, event_bus, mock_live_state_provider):
        """Test state capture in live mode (uses LiveStateProvider)."""
        tracker = StateTracker(mock_game_state, event_bus, mock_live_state_provider)

        state = tracker.capture_state_before()

        assert isinstance(state, PlayerState)
        # Should use LiveStateProvider values, not GameState
        assert state.cash == Decimal("0.180")
        assert state.position_qty == Decimal("0.06")
        assert state.avg_cost == Decimal("2.2")
        assert state.total_invested == Decimal("0.132")
        assert state.cumulative_pnl == Decimal("0.025")

    def test_capture_state_live_mode_not_connected(
        self, mock_game_state, event_bus, mock_live_state_provider
    ):
        """Test state capture when LiveStateProvider exists but is_live=False."""
        # Configure provider as not live
        type(mock_live_state_provider).is_live = PropertyMock(return_value=False)

        tracker = StateTracker(mock_game_state, event_bus, mock_live_state_provider)
        state = tracker.capture_state_before()

        # Should fall back to GameState
        assert state.cash == Decimal("0.150")
        assert state.position_qty == Decimal("0.05")


class TestCaptureGameContext:
    """Test capture_game_context."""

    def test_capture_game_context(self, mock_game_state, event_bus):
        """Test game context capture."""
        tracker = StateTracker(mock_game_state, event_bus)

        context = tracker.capture_game_context()

        assert isinstance(context, GameContext)
        assert context.game_id == "test_game_123"
        assert context.tick == 42
        assert context.price == Decimal("2.5")
        assert context.phase == "ACTIVE"
        assert context.is_active is True
        assert context.connected_players == 0

    def test_capture_game_context_with_live_provider(
        self, mock_game_state, event_bus, mock_live_state_provider
    ):
        """Test that game context uses GameState even in live mode."""
        tracker = StateTracker(mock_game_state, event_bus, mock_live_state_provider)

        context = tracker.capture_game_context()

        # Should still use GameState snapshot (same source in both modes)
        assert context.game_id == "test_game_123"
        assert context.tick == 42


class TestEmitPlayerAction:
    """Test emit_player_action event publishing."""

    def test_emit_player_action_basic(self, mock_game_state, event_bus):
        """Test emitting a basic PlayerAction event."""
        tracker = StateTracker(mock_game_state, event_bus)

        # Create action result
        state_before = PlayerState(
            cash=Decimal("0.100"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )

        state_after = PlayerState(
            cash=Decimal("0.050"),
            position_qty=Decimal("0.05"),
            avg_cost=Decimal("1.0"),
            total_invested=Decimal("0.05"),
            cumulative_pnl=Decimal("0"),
        )

        game_context = GameContext(
            game_id="test_game",
            tick=10,
            price=Decimal("1.0"),
            phase="ACTIVE",
            is_active=True,
            connected_players=5,
        )

        result = ActionResult(
            success=True,
            action_id=str(uuid.uuid4()),
            action_type=ActionType.BUY,
            client_ts=int(time.time() * 1000),
            server_ts=int(time.time() * 1000),
            confirmed_ts=int(time.time() * 1000),
            executed_price=Decimal("1.0"),
            executed_amount=Decimal("0.05"),
            state_before=state_before,
            state_after=state_after,
            game_context=game_context,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("0.05"))

        # Subscribe to event
        events_received = []

        def on_bot_action(event):
            events_received.append(event)

        event_bus.subscribe(Events.BOT_ACTION, on_bot_action, weak=False)

        # Emit action
        tracker.emit_player_action(result, params, session_id="test_session", player_id="player1")

        # Allow event to process
        time.sleep(0.1)

        # Verify event was published
        assert len(events_received) == 1
        event_data = events_received[0]["data"]

        assert event_data["action_id"] == result.action_id
        assert event_data["session_id"] == "test_session"
        assert event_data["player_id"] == "player1"
        assert event_data["action_type"] == "BUY"
        assert event_data["amount"] == Decimal("0.05")
        assert event_data["outcome"]["success"] is True

    def test_emit_player_action_with_error(self, mock_game_state, event_bus):
        """Test emitting a failed action."""
        tracker = StateTracker(mock_game_state, event_bus)

        result = ActionResult(
            success=False,
            action_id=str(uuid.uuid4()),
            action_type=ActionType.BUY,
            error="Insufficient balance",
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("1.0"))

        events_received = []

        def on_bot_action(event):
            events_received.append(event)

        event_bus.subscribe(Events.BOT_ACTION, on_bot_action, weak=False)

        tracker.emit_player_action(result, params)

        time.sleep(0.1)

        assert len(events_received) == 1
        event_data = events_received[0]["data"]

        assert event_data["outcome"]["success"] is False
        assert event_data["outcome"]["error"] == "Insufficient balance"

    def test_emit_player_action_generates_action_id(self, mock_game_state, event_bus):
        """Test that action_id is generated if not present."""
        tracker = StateTracker(mock_game_state, event_bus)

        result = ActionResult(
            success=True,
            action_id=None,  # No action_id
            action_type=ActionType.BUY,
        )

        params = ActionParams(action_type=ActionType.BUY)

        events_received = []

        def on_bot_action(event):
            events_received.append(event)

        event_bus.subscribe(Events.BOT_ACTION, on_bot_action, weak=False)

        tracker.emit_player_action(result, params)

        time.sleep(0.1)

        assert len(events_received) == 1
        event_data = events_received[0]["data"]

        # Should have generated a UUID
        assert event_data["action_id"] is not None
        assert len(event_data["action_id"]) == 36  # UUID format


class TestIntegration:
    """Integration tests with mock components."""

    def test_full_action_workflow_replay_mode(self, mock_game_state, event_bus):
        """Test complete action workflow in replay mode."""
        tracker = StateTracker(mock_game_state, event_bus)

        # Capture state and context
        state_before = tracker.capture_state_before()
        game_context = tracker.capture_game_context()

        assert state_before.cash == Decimal("0.150")
        assert game_context.tick == 42

        # Simulate action execution
        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("0.05"))

        result = ActionResult(
            success=True,
            action_id=str(uuid.uuid4()),
            action_type=ActionType.BUY,
            state_before=state_before,
            game_context=game_context,
        )

        # Emit event
        events_received = []

        def on_bot_action(event):
            events_received.append(event)

        event_bus.subscribe(Events.BOT_ACTION, on_bot_action, weak=False)

        tracker.emit_player_action(result, params)

        time.sleep(0.1)

        assert len(events_received) == 1

    def test_full_action_workflow_live_mode(
        self, mock_game_state, event_bus, mock_live_state_provider
    ):
        """Test complete action workflow in live mode."""
        tracker = StateTracker(mock_game_state, event_bus, mock_live_state_provider)

        # Capture state (should use LiveStateProvider)
        state_before = tracker.capture_state_before()
        game_context = tracker.capture_game_context()

        assert state_before.cash == Decimal("0.180")  # From LiveStateProvider
        assert game_context.tick == 42  # From GameState

        # Rest of workflow same as replay mode
        params = ActionParams(action_type=ActionType.SELL, percentage=Decimal("0.25"))

        result = ActionResult(
            success=True,
            action_id=str(uuid.uuid4()),
            action_type=ActionType.SELL,
            state_before=state_before,
            game_context=game_context,
        )

        events_received = []

        def on_bot_action(event):
            events_received.append(event)

        event_bus.subscribe(Events.BOT_ACTION, on_bot_action, weak=False)

        tracker.emit_player_action(result, params)

        time.sleep(0.1)

        assert len(events_received) == 1
        event_data = events_received[0]["data"]
        assert event_data["action_type"] == "SELL"
        assert event_data["percentage"] == Decimal("0.25")
