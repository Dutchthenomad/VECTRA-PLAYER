"""
Tests for ActionExecutor ABC and SimulatedExecutor.

TDD RED phase - these tests define the expected behavior.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from bot.action_interface.executors.base import ActionExecutor
from bot.action_interface.executors.simulated import SimulatedExecutor
from bot.action_interface.types import ActionParams, ActionResult
from models.events.player_action import ActionType


class TestActionExecutorABC:
    """Test ActionExecutor abstract base class."""

    def test_executor_is_abstract(self):
        """ActionExecutor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ActionExecutor()

    def test_executor_requires_execute_method(self):
        """Subclass must implement execute() method."""
        assert hasattr(ActionExecutor, "execute")

    def test_executor_requires_is_available_method(self):
        """Subclass must implement is_available() method."""
        assert hasattr(ActionExecutor, "is_available")

    def test_executor_requires_get_mode_name_method(self):
        """Subclass must implement get_mode_name() method."""
        assert hasattr(ActionExecutor, "get_mode_name")


class TestSimulatedExecutor:
    """Test SimulatedExecutor for training mode."""

    @pytest.fixture
    def mock_game_state(self):
        """Create a mock GameState."""
        state = MagicMock()
        state.get.side_effect = lambda key, default=None: {
            "balance": Decimal("1.0"),
            "position": None,
            "sidebet": None,
        }.get(key, default)
        state.get_sell_percentage.return_value = Decimal("1.0")
        return state

    @pytest.fixture
    def mock_trade_manager(self, mock_game_state):
        """Create a mock TradeManager."""
        manager = MagicMock()

        # Mock execute_buy to return success
        manager.execute_buy.return_value = {
            "success": True,
            "action": "BUY",
            "amount": 0.01,
            "price": 1.5,
            "tick": 100,
            "reason": "BUY executed successfully",
        }

        # Mock execute_sell to return success
        manager.execute_sell.return_value = {
            "success": True,
            "action": "SELL",
            "amount": 0.01,
            "price": 2.0,
            "pnl_sol": 0.005,
            "reason": "SELL executed successfully",
        }

        # Mock execute_sidebet to return success
        manager.execute_sidebet.return_value = {
            "success": True,
            "action": "SIDE",
            "amount": 0.005,
            "potential_win": 0.05,
            "reason": "SIDEBET executed successfully",
        }

        return manager

    @pytest.fixture
    def executor(self, mock_game_state, mock_trade_manager):
        """Create SimulatedExecutor with mocks."""
        return SimulatedExecutor(
            game_state=mock_game_state,
            trade_manager=mock_trade_manager,
        )

    def test_is_action_executor_subclass(self, executor):
        """SimulatedExecutor is a subclass of ActionExecutor."""
        assert isinstance(executor, ActionExecutor)

    def test_is_always_available(self, executor):
        """SimulatedExecutor is always available."""
        assert executor.is_available() is True

    def test_get_mode_name_returns_simulated(self, executor):
        """Mode name is 'simulated'."""
        assert executor.get_mode_name() == "simulated"

    @pytest.mark.asyncio
    async def test_execute_buy_calls_trade_manager(self, executor, mock_trade_manager):
        """BUY action calls TradeManager.execute_buy()."""
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        mock_trade_manager.execute_buy.assert_called_once_with(Decimal("0.01"))
        assert result.success is True
        assert result.action_type == ActionType.BUY

    @pytest.mark.asyncio
    async def test_execute_sell_calls_trade_manager(self, executor, mock_trade_manager):
        """SELL action calls TradeManager.execute_sell()."""
        params = ActionParams(
            action_type=ActionType.SELL,
            percentage=Decimal("1.0"),
        )

        result = await executor.execute(params)

        mock_trade_manager.execute_sell.assert_called_once()
        assert result.success is True
        assert result.action_type == ActionType.SELL

    @pytest.mark.asyncio
    async def test_execute_sidebet_calls_trade_manager(self, executor, mock_trade_manager):
        """SIDEBET action calls TradeManager.execute_sidebet()."""
        params = ActionParams(
            action_type=ActionType.SIDEBET,
            amount=Decimal("0.005"),
        )

        result = await executor.execute(params)

        mock_trade_manager.execute_sidebet.assert_called_once_with(Decimal("0.005"))
        assert result.success is True
        assert result.action_type == ActionType.SIDEBET

    @pytest.mark.asyncio
    async def test_execute_wait_returns_success(self, executor, mock_trade_manager):
        """WAIT action returns success without calling TradeManager."""
        # Need to create a WAIT action type for testing
        # Use BET_INCREMENT as a stand-in for no-op action
        params = ActionParams(
            action_type=ActionType.BET_INCREMENT,
            button="WAIT",
        )

        result = await executor.execute(params)

        # Should not call any trade methods for increment
        mock_trade_manager.execute_buy.assert_not_called()
        mock_trade_manager.execute_sell.assert_not_called()
        mock_trade_manager.execute_sidebet.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_returns_action_result(self, executor):
        """Execute returns ActionResult instance."""
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert isinstance(result, ActionResult)

    @pytest.mark.asyncio
    async def test_execute_includes_timestamps(self, executor):
        """Result includes client timestamp."""
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.client_ts > 0

    @pytest.mark.asyncio
    async def test_execute_includes_action_id(self, executor):
        """Result includes unique action ID."""
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.action_id is not None
        assert len(result.action_id) > 0

    @pytest.mark.asyncio
    async def test_execute_handles_trade_failure(self, executor, mock_trade_manager):
        """Failed trade is reflected in result."""
        mock_trade_manager.execute_buy.return_value = {
            "success": False,
            "action": "BUY",
            "reason": "Insufficient balance",
        }

        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("100.0"),  # Too much
        )

        result = await executor.execute(params)

        assert result.success is False
        assert result.error == "Insufficient balance"

    @pytest.mark.asyncio
    async def test_execute_handles_exception(self, executor, mock_trade_manager):
        """Exception during trade is handled gracefully."""
        mock_trade_manager.execute_buy.side_effect = RuntimeError("Test error")

        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.success is False
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_execute_sell_with_percentage(self, executor, mock_game_state):
        """SELL with percentage sets GameState.sell_percentage."""
        params = ActionParams(
            action_type=ActionType.SELL,
            percentage=Decimal("0.5"),
        )

        await executor.execute(params)

        mock_game_state.set_sell_percentage.assert_called_with(Decimal("0.5"))

    @pytest.mark.asyncio
    async def test_simulated_latency_zero_by_default(self, executor):
        """Default simulated latency is 0ms."""
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        # When simulated_latency_ms=0, server_ts and confirmed_ts equal client_ts
        assert result.server_ts == result.client_ts
        assert result.confirmed_ts == result.client_ts

    @pytest.mark.asyncio
    async def test_simulated_latency_custom(self, mock_game_state, mock_trade_manager):
        """Custom simulated latency is reflected in timestamps."""
        executor = SimulatedExecutor(
            game_state=mock_game_state,
            trade_manager=mock_trade_manager,
            simulated_latency_ms=100,
        )

        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.server_ts == result.client_ts + 50  # Half of latency
        assert result.confirmed_ts == result.client_ts + 100

    @pytest.mark.asyncio
    async def test_execute_extracts_price_from_result(self, executor, mock_trade_manager):
        """Executed price is extracted from TradeManager result."""
        mock_trade_manager.execute_buy.return_value = {
            "success": True,
            "action": "BUY",
            "price": 1.75,
            "amount": 0.01,
        }

        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.executed_price == Decimal("1.75")

    @pytest.mark.asyncio
    async def test_execute_extracts_amount_from_result(self, executor, mock_trade_manager):
        """Executed amount is extracted from TradeManager result."""
        mock_trade_manager.execute_buy.return_value = {
            "success": True,
            "action": "BUY",
            "price": 1.5,
            "amount": 0.01,
        }

        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )

        result = await executor.execute(params)

        assert result.executed_amount == Decimal("0.01")
