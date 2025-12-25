"""
Tests for BotActionInterface types.

TDD RED phase - these tests define the expected behavior.
"""

import time
from decimal import Decimal

from bot.action_interface.types import (
    ActionParams,
    ActionResult,
    ExecutionMode,
    GameContext,
)
from models.events.player_action import ActionType, PlayerState


class TestExecutionMode:
    """Test ExecutionMode enum."""

    def test_recording_mode_exists(self):
        assert ExecutionMode.RECORDING == "recording"

    def test_training_mode_exists(self):
        assert ExecutionMode.TRAINING == "training"

    def test_validation_mode_exists(self):
        assert ExecutionMode.VALIDATION == "validation"

    def test_live_mode_exists(self):
        assert ExecutionMode.LIVE == "live"

    def test_all_modes_are_strings(self):
        for mode in ExecutionMode:
            assert isinstance(mode.value, str)


class TestActionParams:
    """Test ActionParams dataclass."""

    def test_create_buy_params(self):
        params = ActionParams(
            action_type=ActionType.BUY,
            amount=Decimal("0.01"),
        )
        assert params.action_type == ActionType.BUY
        assert params.amount == Decimal("0.01")
        assert params.percentage is None
        assert params.button is None

    def test_create_sell_params_with_percentage(self):
        params = ActionParams(
            action_type=ActionType.SELL,
            percentage=Decimal("0.5"),
        )
        assert params.action_type == ActionType.SELL
        assert params.percentage == Decimal("0.5")
        assert params.amount is None

    def test_create_sidebet_params(self):
        params = ActionParams(
            action_type=ActionType.SIDEBET,
            amount=Decimal("0.005"),
        )
        assert params.action_type == ActionType.SIDEBET
        assert params.amount == Decimal("0.005")

    def test_create_bet_increment_params(self):
        params = ActionParams(
            action_type=ActionType.BET_INCREMENT,
            button="+0.01",
        )
        assert params.action_type == ActionType.BET_INCREMENT
        assert params.button == "+0.01"


class TestGameContext:
    """Test GameContext dataclass."""

    def test_create_game_context(self):
        ctx = GameContext(
            game_id="game_123",
            tick=42,
            price=Decimal("1.5"),
            phase="ACTIVE",
            is_active=True,
            connected_players=15,
        )
        assert ctx.game_id == "game_123"
        assert ctx.tick == 42
        assert ctx.price == Decimal("1.5")
        assert ctx.phase == "ACTIVE"
        assert ctx.is_active is True
        assert ctx.connected_players == 15

    def test_game_context_defaults(self):
        ctx = GameContext(
            game_id="game_456",
            tick=0,
            price=Decimal("1.0"),
            phase="COOLDOWN",
            is_active=False,
        )
        assert ctx.connected_players == 0


class TestActionResult:
    """Test ActionResult dataclass."""

    def test_create_successful_result(self):
        result = ActionResult(
            success=True,
            action_id="action_123",
            action_type=ActionType.BUY,
            executed_price=Decimal("1.5"),
            executed_amount=Decimal("0.01"),
        )
        assert result.success is True
        assert result.action_id == "action_123"
        assert result.action_type == ActionType.BUY
        assert result.executed_price == Decimal("1.5")
        assert result.executed_amount == Decimal("0.01")
        assert result.error is None

    def test_create_failed_result(self):
        result = ActionResult(
            success=False,
            action_id="action_456",
            action_type=ActionType.BUY,
            error="Insufficient balance",
        )
        assert result.success is False
        assert result.error == "Insufficient balance"

    def test_result_with_state_snapshots(self):
        state_before = PlayerState(
            cash=Decimal("1.0"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )
        state_after = PlayerState(
            cash=Decimal("0.99"),
            position_qty=Decimal("0.01"),
            avg_cost=Decimal("1.5"),
            total_invested=Decimal("0.01"),
            cumulative_pnl=Decimal("0"),
        )

        result = ActionResult(
            success=True,
            action_id="action_789",
            action_type=ActionType.BUY,
            state_before=state_before,
            state_after=state_after,
        )

        assert result.state_before.cash == Decimal("1.0")
        assert result.state_after.position_qty == Decimal("0.01")

    def test_result_with_game_context(self):
        ctx = GameContext(
            game_id="game_test",
            tick=100,
            price=Decimal("2.5"),
            phase="ACTIVE",
            is_active=True,
        )

        result = ActionResult(
            success=True,
            action_id="action_ctx",
            action_type=ActionType.SELL,
            game_context=ctx,
        )

        assert result.game_context.tick == 100
        assert result.game_context.price == Decimal("2.5")

    def test_result_timestamps_default(self):
        result = ActionResult(
            success=True,
            action_id="action_ts",
            action_type=ActionType.BUY,
        )
        # client_ts should be set automatically
        assert result.client_ts > 0
        # server_ts and confirmed_ts should be None by default
        assert result.server_ts is None
        assert result.confirmed_ts is None

    def test_result_latency_calculation(self):
        now = int(time.time() * 1000)
        result = ActionResult(
            success=True,
            action_id="action_latency",
            action_type=ActionType.BUY,
            client_ts=now,
            server_ts=now + 50,
            confirmed_ts=now + 100,
        )

        assert result.send_latency_ms == 50
        assert result.confirm_latency_ms == 50
        assert result.total_latency_ms == 100

    def test_result_latency_none_when_missing_timestamps(self):
        result = ActionResult(
            success=True,
            action_id="action_no_ts",
            action_type=ActionType.BUY,
        )
        # When server_ts is None, latency calculations should return None
        assert result.send_latency_ms is None
        assert result.confirm_latency_ms is None
        assert result.total_latency_ms is None

    def test_result_reward_calculation(self):
        state_before = PlayerState(
            cash=Decimal("1.0"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0"),
        )
        state_after = PlayerState(
            cash=Decimal("1.1"),
            position_qty=Decimal("0"),
            avg_cost=Decimal("0"),
            total_invested=Decimal("0"),
            cumulative_pnl=Decimal("0.1"),
        )

        result = ActionResult(
            success=True,
            action_id="action_reward",
            action_type=ActionType.SELL,
            state_before=state_before,
            state_after=state_after,
        )

        # Reward = state_after.cumulative_pnl - state_before.cumulative_pnl
        assert result.reward == Decimal("0.1")

    def test_result_reward_zero_without_state(self):
        result = ActionResult(
            success=True,
            action_id="action_no_state",
            action_type=ActionType.BUY,
        )
        assert result.reward == Decimal("0")
