"""
Tests for BotActionInterface orchestrator.

Tests:
- Initialization with different executors/modes
- execute() lifecycle (state capture, execution, confirmation, events)
- Statistics tracking
- Availability checks
- Error handling
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.action_interface.interface import BotActionInterface
from bot.action_interface.types import (
    ActionParams,
    ActionResult,
    ActionType,
    ExecutionMode,
    GameContext,
)
from models.events.player_action import PlayerState


@pytest.fixture
def mock_executor():
    """Mock ActionExecutor."""
    executor = MagicMock()
    executor.get_mode_name.return_value = "MockExecutor"
    executor.is_available.return_value = True

    # Make execute async
    async def mock_execute(params):
        return ActionResult(
            success=True,
            action_id="test-action-123",
            action_type=params.action_type,
            executed_price=Decimal("2.5"),
            executed_amount=params.amount,
        )

    executor.execute = AsyncMock(side_effect=mock_execute)

    return executor


@pytest.fixture
def mock_state_tracker():
    """Mock StateTracker."""
    tracker = MagicMock()

    # Mock state capture methods
    tracker.capture_state_before.return_value = PlayerState(
        cash=Decimal("100.0"),
        position_qty=Decimal("0"),
        avg_cost=Decimal("0"),
        total_invested=Decimal("0"),
        cumulative_pnl=Decimal("0"),
    )

    tracker.capture_game_context.return_value = GameContext(
        game_id="game-123",
        tick=50,
        price=Decimal("2.5"),
        phase="active",
        is_active=True,
        connected_players=3,
    )

    # Mock event emission
    tracker.emit_player_action = MagicMock()

    return tracker


@pytest.fixture
def mock_confirmation_monitor():
    """Mock ConfirmationMonitor."""
    monitor = MagicMock()
    monitor.register_pending = MagicMock()
    monitor.get_latency_stats.return_value = {
        "avg_ms": 250.0,
        "min_ms": 200,
        "max_ms": 300,
        "count": 10,
    }
    return monitor


class TestBotActionInterfaceInit:
    """Test BotActionInterface initialization."""

    def test_init_minimal(self, mock_executor, mock_state_tracker):
        """Test initialization with minimal arguments."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        assert interface.mode == ExecutionMode.TRAINING
        assert interface.executor_name == "MockExecutor"
        assert interface.is_available() is True

    def test_init_with_confirmation_monitor(
        self, mock_executor, mock_state_tracker, mock_confirmation_monitor
    ):
        """Test initialization with confirmation monitor."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
            confirmation_monitor=mock_confirmation_monitor,
            mode=ExecutionMode.LIVE,
        )

        assert interface.mode == ExecutionMode.LIVE
        assert interface._confirmation_monitor is mock_confirmation_monitor

    def test_init_different_modes(self, mock_executor, mock_state_tracker):
        """Test initialization with different execution modes."""
        for mode in ExecutionMode:
            interface = BotActionInterface(
                executor=mock_executor,
                state_tracker=mock_state_tracker,
                mode=mode,
            )
            assert interface.mode == mode


class TestBotActionInterfaceAvailability:
    """Test availability checks."""

    def test_is_available_delegates_to_executor(self, mock_executor, mock_state_tracker):
        """Test is_available() delegates to executor."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        # Executor is available
        mock_executor.is_available.return_value = True
        assert interface.is_available() is True

        # Executor is not available
        mock_executor.is_available.return_value = False
        assert interface.is_available() is False

        # Verify delegation
        assert mock_executor.is_available.call_count == 2


class TestBotActionInterfaceExecute:
    """Test execute() lifecycle."""

    @pytest.mark.asyncio
    async def test_execute_captures_state_before(self, mock_executor, mock_state_tracker):
        """Test execute() captures state_before."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify state_before was captured (called twice: once for state_before, once for state_after)
        assert mock_state_tracker.capture_state_before.call_count >= 1
        assert result.state_before is not None
        assert result.state_before.cash == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_execute_captures_game_context(self, mock_executor, mock_state_tracker):
        """Test execute() captures game_context."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify game_context was captured
        mock_state_tracker.capture_game_context.assert_called_once()
        assert result.game_context is not None
        assert result.game_context.game_id == "game-123"
        assert result.game_context.tick == 50

    @pytest.mark.asyncio
    async def test_execute_calls_executor(self, mock_executor, mock_state_tracker):
        """Test execute() calls executor with params."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify executor was called
        mock_executor.execute.assert_called_once_with(params)
        assert result.success is True
        assert result.executed_amount == Decimal("10")

    @pytest.mark.asyncio
    async def test_execute_registers_with_confirmation_monitor(
        self, mock_executor, mock_state_tracker, mock_confirmation_monitor
    ):
        """Test execute() registers with confirmation monitor in live mode."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
            confirmation_monitor=mock_confirmation_monitor,
            mode=ExecutionMode.LIVE,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify confirmation monitor was called
        mock_confirmation_monitor.register_pending.assert_called_once()
        call_args = mock_confirmation_monitor.register_pending.call_args
        assert call_args.kwargs["action_id"] == result.action_id
        assert call_args.kwargs["action_type"] == ActionType.BUY

    @pytest.mark.asyncio
    async def test_execute_no_confirmation_monitor_in_training_mode(
        self, mock_executor, mock_state_tracker
    ):
        """Test execute() captures state_after immediately in training mode."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
            mode=ExecutionMode.TRAINING,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify state_after was captured immediately
        assert result.state_after is not None
        # capture_state_before called twice: once for state_before, once for state_after
        assert mock_state_tracker.capture_state_before.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_emits_player_action(self, mock_executor, mock_state_tracker):
        """Test execute() emits player_action event."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify event was emitted
        mock_state_tracker.emit_player_action.assert_called_once_with(result, params)

    @pytest.mark.asyncio
    async def test_execute_failure_still_emits_event(self, mock_executor, mock_state_tracker):
        """Test execute() emits event even on failure."""
        # Make executor raise exception
        mock_executor.execute = AsyncMock(side_effect=Exception("Executor failure"))

        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify failure result
        assert result.success is False
        assert result.error == "Executor failure"

        # Verify event was still emitted
        mock_state_tracker.emit_player_action.assert_called_once()
        emitted_result = mock_state_tracker.emit_player_action.call_args[0][0]
        assert emitted_result.success is False

    @pytest.mark.asyncio
    async def test_execute_sets_action_id_if_missing(self, mock_executor, mock_state_tracker):
        """Test execute() sets action_id if not provided by executor."""

        # Executor returns result without action_id
        async def mock_execute_no_id(params):
            return ActionResult(
                success=True,
                action_id="",  # Empty action_id
                action_type=params.action_type,
            )

        mock_executor.execute = AsyncMock(side_effect=mock_execute_no_id)

        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        result = await interface.execute(params)

        # Verify action_id was set
        assert result.action_id != ""
        assert len(result.action_id) > 0


class TestBotActionInterfaceStats:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_get_stats_tracks_actions(self, mock_executor, mock_state_tracker):
        """Test get_stats() tracks action counts."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        # Initially no actions
        stats = interface.get_stats()
        assert stats["total_actions"] == 0
        assert stats["successful_actions"] == 0
        assert stats["failed_actions"] == 0
        assert stats["success_rate"] == 0.0

        # Execute 2 successful actions
        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        await interface.execute(params)
        await interface.execute(params)

        stats = interface.get_stats()
        assert stats["total_actions"] == 2
        assert stats["successful_actions"] == 2
        assert stats["failed_actions"] == 0
        assert stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_get_stats_tracks_failures(self, mock_executor, mock_state_tracker):
        """Test get_stats() tracks failures."""
        # Make executor fail
        mock_executor.execute = AsyncMock(side_effect=Exception("Executor failure"))

        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        params = ActionParams(action_type=ActionType.BUY, amount=Decimal("10"))
        await interface.execute(params)

        stats = interface.get_stats()
        assert stats["total_actions"] == 1
        assert stats["successful_actions"] == 0
        assert stats["failed_actions"] == 1
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_stats_includes_latency(
        self, mock_executor, mock_state_tracker, mock_confirmation_monitor
    ):
        """Test get_stats() includes latency from confirmation monitor."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
            confirmation_monitor=mock_confirmation_monitor,
            mode=ExecutionMode.LIVE,
        )

        stats = interface.get_stats()

        # Verify latency stats are included
        assert "latency" in stats
        assert stats["latency"]["avg_ms"] == 250.0
        assert stats["latency"]["min_ms"] == 200
        assert stats["latency"]["max_ms"] == 300
        assert stats["latency"]["count"] == 10

    def test_get_stats_without_confirmation_monitor(self, mock_executor, mock_state_tracker):
        """Test get_stats() returns zero latency without confirmation monitor."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
        )

        stats = interface.get_stats()

        # Verify latency stats are zeroed
        assert "latency" in stats
        assert stats["latency"]["avg_ms"] == 0.0
        assert stats["latency"]["min_ms"] == 0
        assert stats["latency"]["max_ms"] == 0
        assert stats["latency"]["count"] == 0

    def test_get_stats_includes_mode_and_executor(self, mock_executor, mock_state_tracker):
        """Test get_stats() includes mode and executor name."""
        interface = BotActionInterface(
            executor=mock_executor,
            state_tracker=mock_state_tracker,
            mode=ExecutionMode.VALIDATION,
        )

        stats = interface.get_stats()

        assert stats["mode"] == "validation"
        assert stats["executor"] == "MockExecutor"
