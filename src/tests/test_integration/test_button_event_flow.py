"""
Integration tests for ButtonEvent logging flow.

Phase B: Validates the complete pipeline:
1. HumanActionInterceptor creates ButtonEvents
2. ButtonEvents are published via EventBus (BUTTON_PRESS)
3. Events can be persisted via EventStore (BUTTON_EVENT doc_type)
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from models.events.button_event import (
    ActionSequence,
    ButtonCategory,
    ButtonEvent,
    SidebetOutcome,
    TradeOutcome,
    get_button_info,
)
from services.event_bus import EventBus, Events
from services.event_store.schema import DocType, EventEnvelope, EventSource


class TestButtonEventCreation:
    """Test ButtonEvent creation with full game context."""

    def test_button_event_has_all_required_fields(self):
        """ButtonEvent captures all fields needed for RL training."""
        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=42,
            price=1.5,
            game_phase=2,  # ACTIVE
            game_id="game-123",
            balance=Decimal("1.0"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=10,
            sequence_id="seq-123",
            sequence_position=0,
        )

        # Verify all critical fields are present
        assert event.button_id == "BUY"
        assert event.button_category == ButtonCategory.ACTION
        assert event.tick == 42
        assert event.price == 1.5
        assert event.game_phase == 2
        assert event.game_id == "game-123"
        assert event.balance == Decimal("1.0")
        assert event.bet_amount == Decimal("0.01")
        assert event.sequence_id == "seq-123"

    def test_button_event_to_dict_serialization(self):
        """ButtonEvent.to_dict() produces serializable output."""
        event = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="INC_01",
            button_category=ButtonCategory.BET_ADJUST,
            tick=100,
            price=2.5,
            game_phase=2,
            game_id="game-456",
            balance=Decimal("0.5"),
            position_qty=Decimal("0.02"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=5,
            sequence_id="seq-456",
            sequence_position=1,
        )

        data = event.to_dict()

        # Check serialization format
        assert data["button_id"] == "INC_01"
        assert data["button_category"] == "bet_adjust"
        assert data["tick"] == 100
        assert data["price"] == 2.5
        assert data["game_phase"] == 2
        assert isinstance(data["balance"], float)  # Decimal converted to float


class TestButtonIdMapping:
    """Test button text to ID mapping."""

    @pytest.mark.parametrize(
        "button_text,expected_id,expected_category",
        [
            ("BUY", "BUY", ButtonCategory.ACTION),
            ("SELL", "SELL", ButtonCategory.ACTION),
            ("SIDEBET", "SIDEBET", ButtonCategory.ACTION),
            ("+0.01", "INC_01", ButtonCategory.BET_ADJUST),
            ("+0.001", "INC_001", ButtonCategory.BET_ADJUST),
            ("X2", "DOUBLE", ButtonCategory.BET_ADJUST),
            ("25%", "SELL_25", ButtonCategory.PERCENTAGE),
            ("100%", "SELL_100", ButtonCategory.PERCENTAGE),
        ],
    )
    def test_get_button_info(self, button_text, expected_id, expected_category):
        """get_button_info correctly maps UI button text to IDs."""
        button_id, category = get_button_info(button_text)
        assert button_id == expected_id
        assert category == expected_category


class TestEventBusButtonPress:
    """Test BUTTON_PRESS event publishing via EventBus."""

    def test_button_press_event_exists(self):
        """BUTTON_PRESS event type exists in EventBus."""
        assert hasattr(Events, "BUTTON_PRESS")
        assert Events.BUTTON_PRESS.value == "button.press"

    def test_button_event_can_be_published(self):
        """ButtonEvent can be published to EventBus."""
        bus = EventBus()
        bus.start()

        received_events = []

        def handler(event):
            received_events.append(event)

        bus.subscribe(Events.BUTTON_PRESS, handler, weak=False)

        # Publish button event
        event_data = ButtonEvent(
            ts=datetime.now(timezone.utc),
            server_ts=None,
            button_id="BUY",
            button_category=ButtonCategory.ACTION,
            tick=42,
            price=1.5,
            game_phase=2,
            game_id="game-123",
            balance=Decimal("1.0"),
            position_qty=Decimal("0"),
            bet_amount=Decimal("0.01"),
            ticks_since_last_action=10,
            sequence_id="seq-123",
            sequence_position=0,
        ).to_dict()

        bus.publish(Events.BUTTON_PRESS, event_data)

        # Wait for processing
        import time

        time.sleep(0.2)

        bus.stop()

        assert len(received_events) == 1
        assert received_events[0]["data"]["button_id"] == "BUY"


class TestEventStoreButtonEvent:
    """Test BUTTON_EVENT doc_type in EventStore schema."""

    def test_button_event_doc_type_exists(self):
        """BUTTON_EVENT exists in DocType enum."""
        assert hasattr(DocType, "BUTTON_EVENT")
        assert DocType.BUTTON_EVENT.value == "button_event"

    def test_event_envelope_from_button_event(self):
        """EventEnvelope.from_button_event creates valid envelope."""
        envelope = EventEnvelope.from_button_event(
            button_id="BUY",
            button_category="action",
            data={"button_id": "BUY", "tick": 42},
            source=EventSource.UI,
            session_id="session-123",
            seq=1,
            game_id="game-123",
            player_id="player-456",
            tick=42,
            price=Decimal("1.5"),
            sequence_id="seq-789",
            sequence_position=0,
        )

        assert envelope.doc_type == DocType.BUTTON_EVENT
        assert envelope.button_id == "BUY"
        assert envelope.button_category == "action"
        assert envelope.tick == 42
        assert envelope.sequence_id == "seq-789"
        assert envelope.sequence_position == 0

    def test_envelope_to_dict_includes_button_fields(self):
        """EventEnvelope.to_dict() includes button event fields."""
        envelope = EventEnvelope.from_button_event(
            button_id="SELL",
            button_category="action",
            data={"button_id": "SELL"},
            source=EventSource.UI,
            session_id="session-123",
            seq=1,
            sequence_id="seq-abc",
            sequence_position=2,
        )

        data = envelope.to_dict()

        assert data["button_id"] == "SELL"
        assert data["button_category"] == "action"
        assert data["sequence_id"] == "seq-abc"
        assert data["sequence_position"] == 2


class TestActionSequenceRugTracking:
    """Test ActionSequence rug outcome tracking."""

    def test_liquidation_tracking(self):
        """ActionSequence correctly tracks liquidated positions."""
        sequence = ActionSequence(
            sequence_id="seq-123",
            final_action="BUY",
            total_duration_ms=100,
            success=True,
            executed_price=1.5,
            latency_ms=50,
        )

        sequence.mark_liquidated(
            rug_tick=150,
            rug_price=0.001,
            entry_price=1.5,
            amount=Decimal("0.05"),
        )

        assert sequence.trade_outcome == TradeOutcome.LIQUIDATED
        assert sequence.was_rugged is True
        assert sequence.rug_tick == 150
        assert sequence.pnl_amount == Decimal("-0.05")
        assert sequence.pnl_percent == -100.0

    def test_sidebet_win_tracking(self):
        """ActionSequence correctly tracks winning sidebets (5X, 400% net)."""
        sequence = ActionSequence(
            sequence_id="seq-456",
            final_action="SIDEBET",
            total_duration_ms=50,
            success=True,
            executed_price=1.2,
            latency_ms=30,
        )

        sequence.mark_sidebet_won(
            rug_tick=200,
            rug_price=0.001,
            bet_amount=Decimal("0.01"),
        )

        assert sequence.sidebet_outcome == SidebetOutcome.WON
        assert sequence.was_rugged is True
        # 5X payout means 4X net profit (5X - 1X original)
        assert sequence.pnl_amount == Decimal("0.04")
        assert sequence.pnl_percent == 400.0

    def test_sidebet_loss_tracking(self):
        """ActionSequence correctly tracks losing sidebets."""
        sequence = ActionSequence(
            sequence_id="seq-789",
            final_action="SIDEBET",
            total_duration_ms=50,
            success=True,
            executed_price=1.0,
            latency_ms=25,
        )

        sequence.mark_sidebet_lost(bet_amount=Decimal("0.02"))

        assert sequence.sidebet_outcome == SidebetOutcome.LOST
        assert sequence.was_rugged is False
        assert sequence.pnl_amount == Decimal("-0.02")
        assert sequence.pnl_percent == -100.0


class TestHumanActionInterceptorButtonEvents:
    """Test HumanActionInterceptor emits ButtonEvents."""

    def test_interceptor_emits_button_event_on_buy(self):
        """HumanActionInterceptor emits BUTTON_PRESS on BUY click."""
        import time

        from bot.action_interface.recording.human_interceptor import HumanActionInterceptor

        # Mock dependencies
        mock_interface = MagicMock()
        mock_game_state = MagicMock()
        mock_event_bus = MagicMock()

        # Configure game state mock
        mock_game_state.get.side_effect = lambda key, default=None: {
            "current_tick": 42,
            "current_price": Decimal("1.5"),
            "game_id": "game-123",
            "current_phase": "ACTIVE",
            "balance": Decimal("1.0"),
            "position": None,
        }.get(key, default)

        interceptor = HumanActionInterceptor(
            action_interface=mock_interface,
            game_state=mock_game_state,
            event_bus=mock_event_bus,
        )

        try:
            # Wrap a BUY handler
            original_called = []

            def original_handler():
                original_called.append(True)

            def get_amount():
                return Decimal("0.01")

            wrapped = interceptor.wrap_buy(original_handler, get_amount)
            wrapped()

            # Verify ButtonEvent was published
            mock_event_bus.publish.assert_called_once()
            call_args = mock_event_bus.publish.call_args
            assert call_args[0][0] == Events.BUTTON_PRESS

            # Verify original handler was called
            assert len(original_called) == 1
        finally:
            # Cleanup: ensure async manager is stopped properly
            if interceptor._owns_async_manager and interceptor._async_manager:
                interceptor._async_manager.stop(timeout=2.0)
            # Give any pending tasks time to complete
            time.sleep(0.05)
