"""
Tests for ButtonEvent and ActionSequence models.

TDD: Tests written first, implementation follows.
Phase B: ButtonEvent Logging Implementation
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest


class TestButtonEvent:
    """Test ButtonEvent dataclass creation and validation."""

    def test_button_event_creation_buy(self):
        """Test creating a ButtonEvent for a BUY action."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=42,
            price=1.234,
            game_phase=2,  # ACTIVE
            game_id="20251226-abc123",
            balance=Decimal("1.5"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=0,
            sequence_id=str(uuid4()),
            sequence_position=0,
        )

        assert event.button_id == "BUY"
        assert event.button_category == ButtonCategory.ACTION
        assert event.tick == 42
        assert event.price == 1.234
        assert event.game_phase == 2
        assert event.balance == Decimal("1.5")
        assert event.position_qty == Decimal("0")
        assert event.bet_amount == Decimal("0.01")

    def test_button_event_creation_sell(self):
        """Test creating a ButtonEvent for a SELL action."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="SELL",
            button_category=ButtonCategory.ACTION,
            tick=100,
            price=2.5,
            game_phase=2,  # ACTIVE
            game_id="20251226-abc123",
            balance=Decimal("0.5"),
            position_qty=Decimal("0.02"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=58,
            sequence_id=str(uuid4()),
            sequence_position=0,
        )

        assert event.button_id == "SELL"
        assert event.position_qty == Decimal("0.02")
        assert event.ticks_since_last_action == 58

    def test_button_event_creation_bet_increment(self):
        """Test creating a ButtonEvent for a bet adjustment button."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="INC_01",  # +0.01 button
            button_category=ButtonCategory.BET_ADJUST,
            tick=10,
            price=1.0,
            game_phase=1,  # PRESALE
            game_id="20251226-abc123",
            balance=Decimal("2.0"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.001"),
            ticks_since_last_action=5,
            sequence_id=str(uuid4()),
            sequence_position=0,
        )

        assert event.button_id == "INC_01"
        assert event.button_category == ButtonCategory.BET_ADJUST
        assert event.game_phase == 1  # PRESALE

    def test_button_event_creation_percentage(self):
        """Test creating a ButtonEvent for a percentage sell button."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="SELL_25",  # 25% sell
            button_category=ButtonCategory.PERCENTAGE,
            tick=80,
            price=3.0,
            game_phase=2,  # ACTIVE
            game_id="20251226-abc123",
            balance=Decimal("0.8"),
            position_qty=Decimal("0.04"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=20,
            sequence_id=str(uuid4()),
            sequence_position=1,
        )

        assert event.button_id == "SELL_25"
        assert event.button_category == ButtonCategory.PERCENTAGE
        assert event.sequence_position == 1


class TestButtonCategory:
    """Test ButtonCategory enum."""

    def test_button_category_values(self):
        """Test ButtonCategory enum has expected values."""
        from models.events.button_event import ButtonCategory

        assert ButtonCategory.ACTION.value == "action"
        assert ButtonCategory.BET_ADJUST.value == "bet_adjust"
        assert ButtonCategory.PERCENTAGE.value == "percentage"

    def test_button_category_from_string(self):
        """Test creating ButtonCategory from string."""
        from models.events.button_event import ButtonCategory

        assert ButtonCategory("action") == ButtonCategory.ACTION
        assert ButtonCategory("bet_adjust") == ButtonCategory.BET_ADJUST
        assert ButtonCategory("percentage") == ButtonCategory.PERCENTAGE


class TestButtonIdMapping:
    """Test BUTTON_ID_MAP for mapping UI buttons to IDs."""

    def test_action_button_ids(self):
        """Test action button ID mapping."""
        from models.events.button_event import BUTTON_ID_MAP

        assert BUTTON_ID_MAP["BUY"] == ("BUY", "action")
        assert BUTTON_ID_MAP["SELL"] == ("SELL", "action")
        assert BUTTON_ID_MAP["SIDEBET"] == ("SIDEBET", "action")

    def test_bet_adjust_button_ids(self):
        """Test bet adjustment button ID mapping."""
        from models.events.button_event import BUTTON_ID_MAP

        assert BUTTON_ID_MAP["X"] == ("CLEAR", "bet_adjust")
        assert BUTTON_ID_MAP["+0.001"] == ("INC_001", "bet_adjust")
        assert BUTTON_ID_MAP["+0.01"] == ("INC_01", "bet_adjust")
        assert BUTTON_ID_MAP["+0.1"] == ("INC_10", "bet_adjust")
        assert BUTTON_ID_MAP["+1"] == ("INC_1", "bet_adjust")
        assert BUTTON_ID_MAP["1/2"] == ("HALF", "bet_adjust")
        assert BUTTON_ID_MAP["X2"] == ("DOUBLE", "bet_adjust")
        assert BUTTON_ID_MAP["MAX"] == ("MAX", "bet_adjust")

    def test_percentage_button_ids(self):
        """Test percentage button ID mapping."""
        from models.events.button_event import BUTTON_ID_MAP

        assert BUTTON_ID_MAP["10%"] == ("SELL_10", "percentage")
        assert BUTTON_ID_MAP["25%"] == ("SELL_25", "percentage")
        assert BUTTON_ID_MAP["50%"] == ("SELL_50", "percentage")
        assert BUTTON_ID_MAP["100%"] == ("SELL_100", "percentage")


class TestActionSequence:
    """Test ActionSequence dataclass."""

    def test_action_sequence_creation(self):
        """Test creating an ActionSequence."""
        from models.events.button_event import ActionSequence, ButtonCategory, ButtonEvent

        seq_id = str(uuid4())
        events = [
            ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,
                button_id="INC_01",
                button_category=ButtonCategory.BET_ADJUST,
                tick=10,
                price=1.0,
                game_phase=2,
                game_id="20251226-abc123",
                balance=Decimal("2.0"),
                position_qty=Decimal("0"),
                bet_amount=Decimal("0.001"),
                ticks_since_last_action=0,
                sequence_id=seq_id,
                sequence_position=0,
            ),
            ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,
                button_id="INC_01",
                button_category=ButtonCategory.BET_ADJUST,
                tick=10,
                price=1.0,
                game_phase=2,
                game_id="20251226-abc123",
                balance=Decimal("2.0"),
                position_qty=Decimal("0"),
                bet_amount=Decimal("0.011"),
                ticks_since_last_action=0,
                sequence_id=seq_id,
                sequence_position=1,
            ),
            ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,
                button_id="BUY",
                button_category=ButtonCategory.ACTION,
                tick=10,
                price=1.0,
                game_phase=2,
                game_id="20251226-abc123",
                balance=Decimal("2.0"),
                position_qty=Decimal("0"),
                bet_amount=Decimal("0.021"),
                ticks_since_last_action=0,
                sequence_id=seq_id,
                sequence_position=2,
            ),
        ]

        sequence = ActionSequence(
            sequence_id=seq_id,
            button_events=events,
            final_action="BUY",
            total_duration_ms=150,
            success=True,
            executed_price=1.0,
            latency_ms=45,
        )

        assert sequence.sequence_id == seq_id
        assert len(sequence.button_events) == 3
        assert sequence.final_action == "BUY"
        assert sequence.success is True
        assert sequence.executed_price == 1.0

    def test_action_sequence_incomplete(self):
        """Test ActionSequence with no final action button."""
        from models.events.button_event import ActionSequence, ButtonCategory, ButtonEvent

        seq_id = str(uuid4())
        events = [
            ButtonEvent(
                ts=datetime.now(timezone.utc),
                server_ts=None,
                button_id="INC_01",
                button_category=ButtonCategory.BET_ADJUST,
                tick=10,
                price=1.0,
                game_phase=2,
                game_id="20251226-abc123",
                balance=Decimal("2.0"),
                position_qty=Decimal("0"),
                bet_amount=Decimal("0.001"),
                ticks_since_last_action=0,
                sequence_id=seq_id,
                sequence_position=0,
            ),
        ]

        sequence = ActionSequence(
            sequence_id=seq_id,
            button_events=events,
            final_action="INCOMPLETE",
            total_duration_ms=0,
            success=False,
            executed_price=None,
            latency_ms=None,
        )

        assert sequence.final_action == "INCOMPLETE"
        assert sequence.success is False


class TestTradeOutcome:
    """Test TradeOutcome enum for tracking trade results."""

    def test_trade_outcome_values(self):
        """Test TradeOutcome enum has expected values."""
        from models.events.button_event import TradeOutcome

        assert TradeOutcome.PENDING.value == "pending"
        assert TradeOutcome.PROFIT.value == "profit"
        assert TradeOutcome.LOSS.value == "loss"
        assert TradeOutcome.LIQUIDATED.value == "liquidated"
        assert TradeOutcome.BREAK_EVEN.value == "break_even"


class TestSidebetOutcome:
    """Test SidebetOutcome enum for tracking sidebet results."""

    def test_sidebet_outcome_values(self):
        """Test SidebetOutcome enum has expected values."""
        from models.events.button_event import SidebetOutcome

        assert SidebetOutcome.PENDING.value == "pending"
        assert SidebetOutcome.WON.value == "won"
        assert SidebetOutcome.LOST.value == "lost"


class TestActionSequenceRugTracking:
    """Test ActionSequence rug event tracking - the CRITICAL functionality."""

    def test_mark_liquidated_on_rug(self):
        """
        Test that positions active during rug are marked LIQUIDATED.

        Rug = total loss. Position value goes to ~0.
        """
        from models.events.button_event import ActionSequence, TradeOutcome

        sequence = ActionSequence(
            sequence_id="seq-123",
            final_action="BUY",
            total_duration_ms=100,
            success=True,
            executed_price=1.5,
            latency_ms=50,
        )

        # Simulate rug event while holding position
        rug_tick = 150
        rug_price = 0.001  # Near zero
        entry_price = 1.5
        position_amount = Decimal("0.05")

        sequence.mark_liquidated(rug_tick, rug_price, entry_price, position_amount)

        assert sequence.trade_outcome == TradeOutcome.LIQUIDATED
        assert sequence.was_rugged is True
        assert sequence.rug_tick == 150
        assert sequence.rug_price == 0.001
        assert sequence.entry_price == 1.5
        assert sequence.exit_price == 0.001
        assert sequence.pnl_amount == Decimal("-0.05")  # Total loss
        assert sequence.pnl_percent == -100.0  # 100% loss

    def test_mark_sidebet_won_on_rug(self):
        """
        Test that sidebets active during rug are marked WON.

        Sidebet pays 5X on rug = 400% net profit.
        """
        from models.events.button_event import ActionSequence, SidebetOutcome

        sequence = ActionSequence(
            sequence_id="seq-456",
            final_action="SIDEBET",
            total_duration_ms=50,
            success=True,
            executed_price=1.2,
            latency_ms=30,
        )

        # Simulate rug event with active sidebet
        rug_tick = 200
        rug_price = 0.001
        bet_amount = Decimal("0.01")

        sequence.mark_sidebet_won(rug_tick, rug_price, bet_amount)

        assert sequence.sidebet_outcome == SidebetOutcome.WON
        assert sequence.was_rugged is True
        assert sequence.rug_tick == 200
        assert sequence.rug_price == 0.001
        # 5X payout - 1X original = 4X profit
        assert sequence.pnl_amount == Decimal("0.04")  # 0.01 * 4
        assert sequence.pnl_percent == 400.0  # 400% profit

    def test_mark_sidebet_lost_no_rug(self):
        """
        Test that sidebets when game doesn't rug are marked LOST.

        No rug = sidebet loses, player loses bet amount.
        """
        from models.events.button_event import ActionSequence, SidebetOutcome

        sequence = ActionSequence(
            sequence_id="seq-789",
            final_action="SIDEBET",
            total_duration_ms=50,
            success=True,
            executed_price=1.0,
            latency_ms=25,
        )

        bet_amount = Decimal("0.02")
        sequence.mark_sidebet_lost(bet_amount)

        assert sequence.sidebet_outcome == SidebetOutcome.LOST
        assert sequence.was_rugged is False
        assert sequence.pnl_amount == Decimal("-0.02")  # Lost bet
        assert sequence.pnl_percent == -100.0  # 100% loss


class TestButtonEventToDict:
    """Test ButtonEvent serialization."""

    def test_to_dict(self):
        """Test converting ButtonEvent to dict for storage."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime(2025, 12, 26, 12, 0, 0, tzinfo=timezone.utc),
            server_ts=1735214400000,
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=42,
            price=1.234,
            game_phase=2,
            game_id="20251226-abc123",
            balance=Decimal("1.5"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=0,
            sequence_id="seq-123",
            sequence_position=0,
        )

        d = event.to_dict()

        assert d["button_id"] == "BUY"
        assert d["button_category"] == "action"
        assert d["tick"] == 42
        assert d["price"] == 1.234
        assert d["game_phase"] == 2
        assert d["game_id"] == "20251226-abc123"
        assert d["balance"] == 1.5
        assert d["position_qty"] == 0.0
        assert d["bet_amount"] == 0.01
        assert d["sequence_id"] == "seq-123"
        assert d["sequence_position"] == 0


class TestButtonEventExecutionTracking:
    """Test ButtonEvent execution-time and latency tracking fields.

    Based on rugs-expert RAG validation:
    - execution_tick: from standard/newTrade.tickIndex (actual execution tick)
    - execution_price: from standard/newTrade.price (actual execution price)
    - trade_id: from standard/newTrade.id (links to broadcast)
    - client_timestamp: local timestamp when button pressed
    - server_timestamp: from success.timestamp (server ACK time)
    - latency_ms: calculated difference (server_ts - client_ts)
    - time_in_position: from LiveStateProvider at button press time
    """

    def test_button_event_with_execution_fields(self):
        """Test ButtonEvent includes execution tracking fields."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=1735214400050,  # Server ACK time
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=100,  # Request tick
            price=2.5,  # Request price
            game_phase=2,
            game_id="20251227-game123",
            balance=Decimal("1.0"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=10,
            sequence_id="seq-exec-001",
            sequence_position=0,
            # NEW: Execution tracking fields
            execution_tick=102,  # Actual execution tick (may differ from request)
            execution_price=2.52,  # Actual execution price
            trade_id="trade-abc123",  # Links to newTrade broadcast
            client_timestamp=1735214400000,  # When we sent request
            latency_ms=50,  # server_ts - client_ts
            time_in_position=0,  # No position yet
        )

        assert event.execution_tick == 102
        assert event.execution_price == 2.52
        assert event.trade_id == "trade-abc123"
        assert event.client_timestamp == 1735214400000
        assert event.latency_ms == 50
        assert event.time_in_position == 0

    def test_button_event_with_position_timing(self):
        """Test ButtonEvent with time_in_position from open position."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="SELL",
            button_category=ButtonCategory.ACTION,
            tick=150,
            price=3.0,
            game_phase=2,
            game_id="20251227-game456",
            balance=Decimal("0.5"),
            position_qty=Decimal("0.05"),
            bet_amount=Decimal("0.025"),
            ticks_since_last_action=50,
            sequence_id="seq-sell-001",
            sequence_position=0,
            time_in_position=75,  # Position opened at tick 75, current tick 150
        )

        assert event.time_in_position == 75

    def test_button_event_execution_fields_optional(self):
        """Test execution fields default to None when not available."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        # BET_ADJUST doesn't get server confirmation
        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="INC_01",
            button_category=ButtonCategory.BET_ADJUST,
            tick=50,
            price=1.5,
            game_phase=2,
            game_id="20251227-game789",
            balance=Decimal("2.0"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=5,
            sequence_id="seq-bet-001",
            sequence_position=0,
            # No execution fields for local-only actions
        )

        assert event.execution_tick is None
        assert event.execution_price is None
        assert event.trade_id is None
        assert event.latency_ms is None

    def test_button_event_to_dict_includes_execution_fields(self):
        """Test to_dict() includes execution tracking fields."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        event = ButtonEvent(
            ts=datetime(2025, 12, 27, 12, 0, 0, tzinfo=timezone.utc),
            server_ts=1735300850,
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=200,
            price=4.0,
            game_phase=2,
            game_id="20251227-exec",
            balance=Decimal("0.8"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.02"),
            ticks_since_last_action=20,
            sequence_id="seq-dict-001",
            sequence_position=0,
            execution_tick=202,
            execution_price=4.05,
            trade_id="trade-dict123",
            client_timestamp=1735300800,
            latency_ms=50,
            time_in_position=0,
        )

        d = event.to_dict()

        assert d["execution_tick"] == 202
        assert d["execution_price"] == 4.05
        assert d["trade_id"] == "trade-dict123"
        assert d["client_timestamp"] == 1735300800
        assert d["latency_ms"] == 50
        assert d["time_in_position"] == 0

    def test_button_event_from_dict_with_execution_fields(self):
        """Test from_dict() restores execution tracking fields."""
        from models.events.button_event import ButtonCategory, ButtonEvent

        data = {
            "ts": "2025-12-27T12:00:00+00:00",
            "server_ts": 1735300850,
            "button_id": "SELL",
            "button_category": "action",
            "tick": 300,
            "price": 5.0,
            "game_phase": 2,
            "game_id": "20251227-fromdict",
            "balance": 0.5,
            "position_qty": 0.03,
            "bet_amount": 0.015,
            "ticks_since_last_action": 100,
            "sequence_id": "seq-fromdict-001",
            "sequence_position": 0,
            "execution_tick": 302,
            "execution_price": 4.95,
            "trade_id": "trade-fromdict",
            "client_timestamp": 1735300800,
            "latency_ms": 50,
            "time_in_position": 150,
        }

        event = ButtonEvent.from_dict(data)

        assert event.execution_tick == 302
        assert event.execution_price == 4.95
        assert event.trade_id == "trade-fromdict"
        assert event.client_timestamp == 1735300800
        assert event.latency_ms == 50
        assert event.time_in_position == 150
