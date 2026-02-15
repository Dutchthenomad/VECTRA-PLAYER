"""Tests for Optimization Subscriber."""

from unittest.mock import Mock


class TestOptimizationSubscriber:
    """Tests for the optimization subscriber."""

    def test_subscriber_initializes(self):
        """Subscriber should initialize with client and producer."""
        from src.profiles.producer import ProfileProducer
        from src.subscriber import OptimizationSubscriber

        mock_client = Mock()
        mock_client.on = Mock(return_value=Mock())  # Returns unsubscribe func
        mock_producer = Mock(spec=ProfileProducer)

        subscriber = OptimizationSubscriber(
            client=mock_client,
            producer=mock_producer,
        )

        assert subscriber is not None
        assert subscriber._producer == mock_producer

    def test_on_game_tick_collects_rugged_games(self):
        """on_game_tick should collect games when rugged=True."""
        from src.subscriber import OptimizationSubscriber

        mock_client = Mock()
        mock_client.on = Mock(return_value=Mock())

        subscriber = OptimizationSubscriber(
            client=mock_client,
            producer=Mock(),
        )

        # Create mock event with rugged=True and game_history
        mock_event = Mock()
        mock_event.rugged = True
        mock_event.game_history = [{"id": "game-1", "duration": 200}]

        subscriber.on_game_tick(mock_event)

        # Should have collected the game
        assert len(subscriber._collected_games) > 0

    def test_on_connection_change_logs_status(self):
        """on_connection_change should update connection state."""
        from src.subscriber import OptimizationSubscriber

        mock_client = Mock()
        mock_client.on = Mock(return_value=Mock())

        subscriber = OptimizationSubscriber(
            client=mock_client,
            producer=Mock(),
        )

        subscriber.on_connection_change(True)
        assert subscriber._connected is True

        subscriber.on_connection_change(False)
        assert subscriber._connected is False

    def test_stats_tracking(self):
        """Subscriber should track statistics."""
        from src.subscriber import OptimizationSubscriber

        mock_client = Mock()
        mock_client.on = Mock(return_value=Mock())

        subscriber = OptimizationSubscriber(
            client=mock_client,
            producer=Mock(),
        )

        assert subscriber.stats is not None
        assert subscriber.stats.games_collected == 0
