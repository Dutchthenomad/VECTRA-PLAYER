"""
Tests for Player Action Event Models - Schema v2.0.0

Tests the enhancements for RL training data capture:
- PRESALE phase in GamePhase enum
- Rugpool fields in GameContext
- Session stats in GameContext
"""

import pytest
from decimal import Decimal

from models.events.player_action import (
    ActionType,
    GamePhase,
    GameContext,
    PlayerState,
    ActionTimestamps,
    ActionOutcome,
    PlayerAction,
)


class TestGamePhase:
    """Tests for GamePhase enum including PRESALE."""

    def test_all_phases_exist(self):
        """Verify all 4 game phases are defined."""
        assert GamePhase.COOLDOWN == "COOLDOWN"
        assert GamePhase.PRESALE == "PRESALE"
        assert GamePhase.ACTIVE == "ACTIVE"
        assert GamePhase.RUGGED == "RUGGED"

    def test_phase_count(self):
        """Verify exactly 4 phases exist."""
        assert len(GamePhase) == 4

    def test_presale_is_string_enum(self):
        """PRESALE should be usable as string."""
        phase = GamePhase.PRESALE
        assert phase.value == "PRESALE"
        assert str(phase) == "GamePhase.PRESALE"


class TestGameContext:
    """Tests for GameContext with rugpool and session stats."""

    def test_basic_context(self):
        """Test basic GameContext creation."""
        ctx = GameContext(
            game_id="test-game-123",
            tick=42,
            price=Decimal("1.5"),
            phase=GamePhase.ACTIVE,
            is_pre_round=False,
            connected_players=15,
        )
        assert ctx.game_id == "test-game-123"
        assert ctx.tick == 42
        assert ctx.price == Decimal("1.5")
        assert ctx.phase == GamePhase.ACTIVE
        assert ctx.is_pre_round is False
        assert ctx.connected_players == 15

    def test_presale_phase_context(self):
        """Test GameContext with PRESALE phase."""
        ctx = GameContext(
            game_id="presale-game",
            tick=0,
            price=Decimal("1.0"),
            phase=GamePhase.PRESALE,
            is_pre_round=True,
            connected_players=10,
        )
        assert ctx.phase == GamePhase.PRESALE
        assert ctx.is_pre_round is True

    def test_rugpool_fields(self):
        """Test rugpool fields for instarug risk prediction."""
        ctx = GameContext(
            game_id="test-game",
            tick=100,
            price=Decimal("25.5"),
            phase=GamePhase.ACTIVE,
            is_pre_round=False,
            connected_players=20,
            # Rugpool fields
            rugpool_amount=Decimal("0.5"),
            rugpool_threshold=Decimal("1.0"),
            rugpool_ratio=Decimal("0.5"),
        )
        assert ctx.rugpool_amount == Decimal("0.5")
        assert ctx.rugpool_threshold == Decimal("1.0")
        assert ctx.rugpool_ratio == Decimal("0.5")

    def test_session_stats_fields(self):
        """Test session statistics fields for training context."""
        ctx = GameContext(
            game_id="test-game",
            tick=50,
            price=Decimal("10.0"),
            phase=GamePhase.ACTIVE,
            is_pre_round=False,
            connected_players=25,
            # Session stats
            average_multiplier=Decimal("15.5"),
            count_2x=100,
            count_10x=45,
            count_50x=12,
            count_100x=3,
            highest_today=Decimal("250.0"),
        )
        assert ctx.average_multiplier == Decimal("15.5")
        assert ctx.count_2x == 100
        assert ctx.count_10x == 45
        assert ctx.count_50x == 12
        assert ctx.count_100x == 3
        assert ctx.highest_today == Decimal("250.0")

    def test_full_context_for_training(self):
        """Test complete GameContext with all fields for RL training."""
        ctx = GameContext(
            game_id="full-context-game",
            tick=75,
            price=Decimal("35.2"),
            phase=GamePhase.ACTIVE,
            is_pre_round=False,
            connected_players=30,
            # Rugpool
            rugpool_amount=Decimal("0.8"),
            rugpool_threshold=Decimal("1.0"),
            rugpool_ratio=Decimal("0.8"),
            # Session stats
            average_multiplier=Decimal("20.0"),
            count_2x=150,
            count_10x=60,
            count_50x=15,
            count_100x=5,
            highest_today=Decimal("500.0"),
        )
        # Verify all fields accessible
        assert ctx.rugpool_ratio == Decimal("0.8")
        assert ctx.count_100x == 5
        assert ctx.highest_today == Decimal("500.0")


class TestPlayerState:
    """Tests for PlayerState model."""

    def test_basic_state(self):
        """Test basic PlayerState creation."""
        state = PlayerState(
            cash=Decimal("5.0"),
            position_qty=Decimal("0.1"),
            avg_cost=Decimal("10.0"),
            total_invested=Decimal("1.0"),
            cumulative_pnl=Decimal("0.5"),
        )
        assert state.cash == Decimal("5.0")
        assert state.position_qty == Decimal("0.1")

    def test_float_coercion(self):
        """Test that floats are coerced to Decimal."""
        state = PlayerState(
            cash=5.0,
            position_qty=0.1,
            avg_cost=10.0,
            total_invested=1.0,
            cumulative_pnl=0.5,
        )
        assert isinstance(state.cash, Decimal)
        assert state.cash == Decimal("5.0")

    def test_none_coercion(self):
        """Test that None values become Decimal(0)."""
        state = PlayerState(
            cash=None,
            position_qty=None,
            avg_cost=None,
            total_invested=None,
            cumulative_pnl=None,
        )
        assert state.cash == Decimal("0")
        assert state.position_qty == Decimal("0")


class TestActionTimestamps:
    """Tests for ActionTimestamps latency calculations."""

    def test_latency_calculations(self):
        """Test latency property calculations."""
        ts = ActionTimestamps(
            client_ts=1000,
            server_ts=1100,
            confirmed_ts=1350,
        )
        assert ts.send_latency_ms == 100
        assert ts.confirm_latency_ms == 250
        assert ts.total_latency_ms == 350


class TestPlayerAction:
    """Tests for complete PlayerAction model."""

    def test_full_action_with_presale(self):
        """Test PlayerAction with PRESALE phase context."""
        action = PlayerAction(
            action_id="action-123",
            session_id="session-456",
            game_id="game-789",
            player_id="player-abc",
            username="test_user",
            action_type=ActionType.BUY,
            button="BUY",
            amount=Decimal("0.01"),
            game_context=GameContext(
                game_id="game-789",
                tick=0,
                price=Decimal("1.0"),
                phase=GamePhase.PRESALE,
                is_pre_round=True,
                connected_players=10,
            ),
            state_before=PlayerState(
                cash=Decimal("5.0"),
                position_qty=Decimal("0"),
                avg_cost=Decimal("0"),
                total_invested=Decimal("0"),
                cumulative_pnl=Decimal("0"),
            ),
            timestamps=ActionTimestamps(
                client_ts=1000,
                server_ts=1100,
                confirmed_ts=1350,
            ),
            outcome=ActionOutcome(
                success=True,
                executed_price=Decimal("1.0"),
                executed_amount=Decimal("0.01"),
            ),
            state_after=PlayerState(
                cash=Decimal("4.99"),
                position_qty=Decimal("0.01"),
                avg_cost=Decimal("1.0"),
                total_invested=Decimal("0.01"),
                cumulative_pnl=Decimal("0"),
            ),
        )
        assert action.game_context.phase == GamePhase.PRESALE
        assert action.state_after.position_qty == Decimal("0.01")
