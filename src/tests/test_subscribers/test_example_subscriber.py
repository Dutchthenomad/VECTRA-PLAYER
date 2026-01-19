"""
Tests for ExampleSubscriber - Validates correct BaseSubscriber usage.
"""

from unittest.mock import MagicMock

from foundation.events import GameTickEvent, PlayerStateEvent, PlayerTradeEvent


class TestExampleSubscriberCreation:
    """Test ExampleSubscriber instantiation."""

    def test_can_create_example_subscriber(self):
        """ExampleSubscriber can be instantiated."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        assert subscriber is not None

    def test_subscriber_initializes_state(self):
        """ExampleSubscriber initializes with default state."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        state = subscriber.get_state()
        assert state.last_price == 1.0
        assert state.last_tick == 0
        assert state.last_phase == "UNKNOWN"
        assert state.cash == 0.0
        assert state.position_qty == 0.0
        assert state.connected is False

    def test_subscriber_registers_handlers(self):
        """ExampleSubscriber registers handlers with client."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        # Verify handlers were registered
        call_args = [call[0][0] for call in mock_client.on.call_args_list]
        assert "game.tick" in call_args
        assert "player.state" in call_args
        assert "connection" in call_args


class TestGameTickHandling:
    """Test game.tick event handling."""

    def test_on_game_tick_updates_price(self):
        """on_game_tick updates state price."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        event = GameTickEvent(
            type="game.tick",
            ts=1737200000000,
            game_id="test",
            seq=1,
            price=2.5,
            tick_count=10,
            phase="ACTIVE",
        )

        subscriber.on_game_tick(event)

        state = subscriber.get_state()
        assert state.last_price == 2.5
        assert state.last_tick == 10
        assert state.last_phase == "ACTIVE"


class TestPlayerStateHandling:
    """Test player.state event handling."""

    def test_on_player_state_updates_balance(self):
        """on_player_state updates cash and position."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        event = PlayerStateEvent(
            type="player.state",
            ts=1737200000000,
            game_id="test",
            seq=1,
            cash=5.0,
            position_qty=0.25,
        )

        subscriber.on_player_state(event)

        state = subscriber.get_state()
        assert state.cash == 5.0
        assert state.position_qty == 0.25


class TestConnectionHandling:
    """Test connection state change handling."""

    def test_on_connection_change_updates_state(self):
        """on_connection_change updates connected flag."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        subscriber.on_connection_change(True)
        assert subscriber.get_state().connected is True

        subscriber.on_connection_change(False)
        assert subscriber.get_state().connected is False


class TestTradeTracking:
    """Test optional trade tracking."""

    def test_trade_tracking_disabled_by_default(self):
        """Trade tracking is disabled by default."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client)

        event = PlayerTradeEvent(
            type="player.trade",
            ts=1737200000000,
            game_id="test",
            seq=1,
            username="Trader",
            trade_type="buy",
            qty=1.0,
            price=2.0,
        )

        subscriber.on_player_trade(event)

        # Should not track
        assert len(subscriber.get_state().trades_seen) == 0

    def test_trade_tracking_when_enabled(self):
        """Trades are tracked when track_trades=True."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client, track_trades=True)

        event = PlayerTradeEvent(
            type="player.trade",
            ts=1737200000000,
            game_id="test",
            seq=1,
            username="Trader",
            trade_type="buy",
            qty=1.0,
            price=2.0,
        )

        subscriber.on_player_trade(event)

        trades = subscriber.get_state().trades_seen
        assert len(trades) == 1
        assert trades[0]["username"] == "Trader"
        assert trades[0]["type"] == "buy"
        assert trades[0]["qty"] == 1.0

    def test_reset_trades_clears_list(self):
        """reset_trades clears the trades list."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        subscriber = ExampleSubscriber(mock_client, track_trades=True)

        event = PlayerTradeEvent(
            type="player.trade",
            ts=1737200000000,
            game_id="test",
            seq=1,
            username="Trader",
            trade_type="sell",
            qty=0.5,
            price=3.0,
        )

        subscriber.on_player_trade(event)
        assert len(subscriber.get_state().trades_seen) == 1

        subscriber.reset_trades()
        assert len(subscriber.get_state().trades_seen) == 0


class TestUnsubscribe:
    """Test unsubscribe functionality."""

    def test_unsubscribe_removes_handlers(self):
        """unsubscribe removes all registered handlers."""
        from subscribers.example import ExampleSubscriber

        mock_client = MagicMock()
        mock_unsub = MagicMock()
        mock_client.on.return_value = mock_unsub

        subscriber = ExampleSubscriber(mock_client)
        subscriber.unsubscribe()

        # Each handler's unsub should have been called
        assert mock_unsub.call_count >= 3
