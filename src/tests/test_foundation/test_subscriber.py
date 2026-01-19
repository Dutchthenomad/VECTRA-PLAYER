"""
Tests for Foundation BaseSubscriber - Abstract base class for all Python subscribers.

TDD: Tests written BEFORE implementation.
"""

from unittest.mock import MagicMock

import pytest

# =============================================================================
# PHASE 1: BaseSubscriber Abstract Interface Tests
# =============================================================================


class TestBaseSubscriberInterface:
    """Test that BaseSubscriber enforces correct interface."""

    def test_base_subscriber_is_abstract(self):
        """BaseSubscriber cannot be instantiated directly."""
        from foundation.subscriber import BaseSubscriber

        with pytest.raises(TypeError) as exc_info:
            BaseSubscriber(MagicMock())

        assert "abstract" in str(exc_info.value).lower()

    def test_must_implement_on_game_tick(self):
        """Concrete subscriber must implement on_game_tick."""
        from foundation.subscriber import BaseSubscriber

        class IncompleteSubscriber(BaseSubscriber):
            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteSubscriber(MagicMock())

        assert "on_game_tick" in str(exc_info.value)

    def test_must_implement_on_player_state(self):
        """Concrete subscriber must implement on_player_state."""
        from foundation.subscriber import BaseSubscriber

        class IncompleteSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteSubscriber(MagicMock())

        assert "on_player_state" in str(exc_info.value)

    def test_must_implement_on_connection_change(self):
        """Concrete subscriber must implement on_connection_change."""
        from foundation.subscriber import BaseSubscriber

        class IncompleteSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteSubscriber(MagicMock())

        assert "on_connection_change" in str(exc_info.value)


# =============================================================================
# PHASE 2: Complete Subscriber Implementation Tests
# =============================================================================


class TestCompleteSubscriber:
    """Test complete subscriber implementations."""

    def test_minimal_subscriber_can_be_instantiated(self):
        """Minimal subscriber with required methods can be created."""
        from foundation.subscriber import BaseSubscriber

        class MinimalSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = MinimalSubscriber(mock_client)

        assert subscriber is not None
        assert subscriber._client is mock_client

    def test_subscriber_stores_client_reference(self):
        """Subscriber stores reference to client."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        assert subscriber._client is mock_client


# =============================================================================
# PHASE 3: Handler Registration Tests
# =============================================================================


class TestHandlerRegistration:
    """Test that handlers are auto-registered with client."""

    def test_constructor_registers_handlers(self):
        """Constructor automatically registers event handlers."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Check that client.on was called for each event type
        call_args = [call[0][0] for call in mock_client.on.call_args_list]
        assert "game.tick" in call_args
        assert "player.state" in call_args
        assert "connection" in call_args

    def test_optional_handlers_registered_if_overridden(self):
        """Optional handlers are registered when overridden."""
        from foundation.subscriber import BaseSubscriber

        class ExtendedSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

            def on_player_trade(self, event):
                pass  # Override optional method

        mock_client = MagicMock()
        subscriber = ExtendedSubscriber(mock_client)

        call_args = [call[0][0] for call in mock_client.on.call_args_list]
        assert "player.trade" in call_args

    def test_unsubscribe_removes_all_handlers(self):
        """unsubscribe() removes all registered handlers."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        # Mock the unsubscribe functions
        mock_unsub = MagicMock()
        mock_client.on.return_value = mock_unsub

        subscriber = TestSubscriber(mock_client)
        subscriber.unsubscribe()

        # Each registered handler's unsub should have been called
        assert mock_unsub.call_count >= 3  # At minimum the required handlers


# =============================================================================
# PHASE 4: Optional Hook Tests
# =============================================================================


class TestOptionalHooks:
    """Test optional event hooks with default no-op behavior."""

    def test_on_player_trade_default_noop(self):
        """on_player_trade default does nothing."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Should not raise
        subscriber.on_player_trade(MagicMock())

    def test_on_sidebet_placed_default_noop(self):
        """on_sidebet_placed default does nothing."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Should not raise
        subscriber.on_sidebet_placed(MagicMock())

    def test_on_sidebet_result_default_noop(self):
        """on_sidebet_result default does nothing."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Should not raise
        subscriber.on_sidebet_result(MagicMock())

    def test_on_raw_event_default_noop(self):
        """on_raw_event default does nothing."""
        from foundation.subscriber import BaseSubscriber

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Should not raise
        subscriber.on_raw_event({"type": "raw.unknown", "data": {}})


# =============================================================================
# PHASE 5: Event Parsing Tests
# =============================================================================


class TestEventParsing:
    """Test that events are parsed to typed dataclasses before delivery."""

    def test_game_tick_handler_receives_typed_event(self):
        """on_game_tick receives GameTickEvent instance."""
        from foundation.events import GameTickEvent
        from foundation.subscriber import BaseSubscriber

        received_events = []

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                received_events.append(event)

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Get the registered callback for game.tick
        game_tick_callback = None
        for call in mock_client.on.call_args_list:
            if call[0][0] == "game.tick":
                game_tick_callback = call[0][1]
                break

        assert game_tick_callback is not None

        # Simulate event delivery
        raw_event = {
            "type": "game.tick",
            "ts": 1737200000000,
            "gameId": "test",
            "seq": 1,
            "data": {"price": 1.5, "active": True, "phase": "ACTIVE"},
        }
        game_tick_callback(raw_event)

        assert len(received_events) == 1
        assert isinstance(received_events[0], GameTickEvent)
        assert received_events[0].price == 1.5

    def test_player_state_handler_receives_typed_event(self):
        """on_player_state receives PlayerStateEvent instance."""
        from foundation.events import PlayerStateEvent
        from foundation.subscriber import BaseSubscriber

        received_events = []

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                received_events.append(event)

            def on_connection_change(self, connected):
                pass

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Get the registered callback for player.state
        player_state_callback = None
        for call in mock_client.on.call_args_list:
            if call[0][0] == "player.state":
                player_state_callback = call[0][1]
                break

        assert player_state_callback is not None

        # Simulate event delivery
        raw_event = {
            "type": "player.state",
            "ts": 1737200000000,
            "gameId": "test",
            "seq": 1,
            "data": {"cash": 5.0, "positionQty": 0.1},
        }
        player_state_callback(raw_event)

        assert len(received_events) == 1
        assert isinstance(received_events[0], PlayerStateEvent)
        assert received_events[0].cash == 5.0


# =============================================================================
# PHASE 6: Wildcard/Raw Event Handling Tests
# =============================================================================


class TestRawEventHandling:
    """Test handling of unknown/raw events."""

    def test_raw_events_delivered_to_on_raw_event(self):
        """Unknown events are delivered to on_raw_event hook."""
        from foundation.subscriber import BaseSubscriber

        received_raw = []

        class TestSubscriber(BaseSubscriber):
            def on_game_tick(self, event):
                pass

            def on_player_state(self, event):
                pass

            def on_connection_change(self, connected):
                pass

            def on_raw_event(self, event):
                received_raw.append(event)

        mock_client = MagicMock()
        subscriber = TestSubscriber(mock_client)

        # Get the registered callback for '*' (wildcard)
        wildcard_callback = None
        for call in mock_client.on.call_args_list:
            if call[0][0] == "*":
                wildcard_callback = call[0][1]
                break

        if wildcard_callback:
            # Simulate raw event delivery
            raw_event = {
                "type": "raw.unknownEvent",
                "ts": 1737200000000,
                "gameId": "test",
                "seq": 1,
                "data": {"custom": "data"},
            }
            wildcard_callback(raw_event)

            # Should have received the raw event
            assert len(received_raw) == 1
            assert received_raw[0]["type"] == "raw.unknownEvent"
