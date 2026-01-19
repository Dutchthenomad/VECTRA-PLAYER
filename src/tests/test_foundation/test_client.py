"""
Tests for Foundation Python Client - Async WebSocket client equivalent to JS FoundationWSClient.

TDD: Tests written BEFORE implementation.
"""

import asyncio

import pytest

# =============================================================================
# PHASE 1: ClientMetrics Tests
# =============================================================================


class TestClientMetrics:
    """Test ClientMetrics dataclass."""

    def test_initial_metrics_are_zeroed(self):
        """Fresh ClientMetrics has zero values."""
        from foundation.client import ClientMetrics

        metrics = ClientMetrics()

        assert metrics.connected is False
        assert metrics.message_count == 0
        assert metrics.last_message_time is None
        assert metrics.connection_attempts == 0
        assert metrics.last_connected_time is None
        assert metrics.average_latency == 0.0

    def test_metrics_to_dict_returns_all_fields(self):
        """to_dict returns dictionary with all fields."""
        from foundation.client import ClientMetrics

        metrics = ClientMetrics(
            connected=True,
            message_count=100,
            last_message_time=1737200000000,
            connection_attempts=3,
            last_connected_time=1737199000000,
            average_latency=25.5,
        )

        result = metrics.to_dict()

        assert result == {
            "connected": True,
            "message_count": 100,
            "last_message_time": 1737200000000,
            "connection_attempts": 3,
            "last_connected_time": 1737199000000,
            "average_latency": 25.5,
        }


# =============================================================================
# PHASE 2: FoundationClient Configuration Tests
# =============================================================================


class TestFoundationClientConfig:
    """Test FoundationClient initialization and configuration."""

    def test_default_url_is_localhost_9000(self):
        """Default URL is ws://localhost:9000/feed."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        assert client.url == "ws://localhost:9000/feed"

    def test_custom_url_is_respected(self):
        """Custom URL is used when provided."""
        from foundation.client import FoundationClient

        client = FoundationClient(url="ws://example.com:8080/ws")

        assert client.url == "ws://example.com:8080/ws"

    def test_default_reconnect_settings(self):
        """Default reconnection settings are sensible."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        assert client.reconnect_delay == 1.0
        assert client.max_reconnect_delay == 30.0
        assert client.reconnect_multiplier == 1.5

    def test_custom_reconnect_settings(self):
        """Custom reconnection settings are used."""
        from foundation.client import FoundationClient

        client = FoundationClient(
            reconnect_delay=0.5,
            max_reconnect_delay=10.0,
            reconnect_multiplier=2.0,
        )

        assert client.reconnect_delay == 0.5
        assert client.max_reconnect_delay == 10.0
        assert client.reconnect_multiplier == 2.0

    def test_is_connected_initially_false(self):
        """is_connected() returns False before connection."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        assert client.is_connected() is False

    def test_get_metrics_returns_client_metrics(self):
        """get_metrics() returns ClientMetrics instance."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        metrics = client.get_metrics()

        assert hasattr(metrics, "connected")
        assert hasattr(metrics, "message_count")
        assert hasattr(metrics, "average_latency")


# =============================================================================
# PHASE 3: Event Listener Tests
# =============================================================================


class TestEventListeners:
    """Test event subscription system."""

    def test_on_returns_unsubscribe_function(self):
        """on() returns a callable unsubscribe function."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        unsubscribe = client.on("game.tick", lambda e: received.append(e))

        assert callable(unsubscribe)

    def test_on_registers_callback_for_event_type(self):
        """on() registers callback and receives events."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        client.on("game.tick", lambda e: received.append(e))

        # Simulate event emission (internal method)
        client._emit("game.tick", {"price": 1.5})

        assert len(received) == 1
        assert received[0]["price"] == 1.5

    def test_unsubscribe_removes_callback(self):
        """Unsubscribe function removes callback."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        unsubscribe = client.on("game.tick", lambda e: received.append(e))
        unsubscribe()

        # Emit after unsubscribe
        client._emit("game.tick", {"price": 1.5})

        assert len(received) == 0

    def test_wildcard_listener_receives_all_events(self):
        """'*' listener receives all event types."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        client.on("*", lambda e: received.append(e))

        client._emit("game.tick", {"price": 1.5})
        client._emit("player.state", {"cash": 10.0})
        client._emit("connection.authenticated", {"username": "Test"})

        assert len(received) == 3

    def test_multiple_listeners_same_event(self):
        """Multiple listeners for same event all receive it."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received_a = []
        received_b = []

        client.on("game.tick", lambda e: received_a.append(e))
        client.on("game.tick", lambda e: received_b.append(e))

        client._emit("game.tick", {"price": 2.0})

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_listener_error_does_not_break_other_listeners(self):
        """Error in one listener doesn't affect others."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        def bad_callback(e):
            raise ValueError("Intentional error")

        client.on("game.tick", bad_callback)
        client.on("game.tick", lambda e: received.append(e))

        # Should not raise - error is caught
        client._emit("game.tick", {"price": 1.5})

        assert len(received) == 1


# =============================================================================
# PHASE 4: Event Buffering Tests
# =============================================================================


class TestEventBuffering:
    """Test recent event buffering for late subscribers."""

    def test_get_recent_events_returns_empty_list_initially(self):
        """get_recent_events returns empty list before events."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        events = client.get_recent_events("game.tick")

        assert events == []

    def test_recent_events_are_buffered(self):
        """Events are stored in buffer."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        # Simulate receiving events
        client._handle_message({"type": "game.tick", "ts": 1000, "seq": 1, "data": {"price": 1.0}})
        client._handle_message({"type": "game.tick", "ts": 2000, "seq": 2, "data": {"price": 1.5}})

        events = client.get_recent_events("game.tick")

        assert len(events) == 2
        assert events[0]["data"]["price"] == 1.0
        assert events[1]["data"]["price"] == 1.5

    def test_buffer_size_is_limited(self):
        """Buffer doesn't grow unbounded."""
        from foundation.client import FoundationClient

        client = FoundationClient(max_buffer_size=5)

        # Simulate receiving many events
        for i in range(10):
            client._handle_message(
                {"type": "game.tick", "ts": i * 1000, "seq": i, "data": {"price": i}}
            )

        events = client.get_recent_events("game.tick")

        assert len(events) == 5
        # Should have the most recent 5
        assert events[0]["data"]["price"] == 5
        assert events[4]["data"]["price"] == 9


# =============================================================================
# PHASE 5: Connection Tests (Async with Mocking)
# =============================================================================


class TestConnection:
    """Test WebSocket connection handling."""

    @pytest.mark.asyncio
    async def test_connect_updates_metrics(self):
        """connect() updates connection metrics."""
        from unittest.mock import AsyncMock, patch

        from foundation.client import FoundationClient

        client = FoundationClient()

        # Mock websockets.connect
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=asyncio.CancelledError)
        mock_ws.close = AsyncMock()

        with patch("websockets.connect", return_value=mock_ws):
            # Start connection task but cancel quickly
            task = asyncio.create_task(client.connect())
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        assert client.get_metrics().connection_attempts >= 1

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self):
        """disconnect() closes the WebSocket."""
        from unittest.mock import AsyncMock

        from foundation.client import FoundationClient

        client = FoundationClient()

        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()
        client._ws = mock_ws
        client._is_connected = True

        await client.disconnect()

        mock_ws.close.assert_called_once()
        assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_reconnect_uses_exponential_backoff(self):
        """Reconnection uses exponential backoff."""
        from foundation.client import FoundationClient

        client = FoundationClient(
            reconnect_delay=1.0,
            max_reconnect_delay=10.0,
            reconnect_multiplier=2.0,
        )

        # Simulate backoff calculation
        delays = []
        current_delay = client.reconnect_delay

        for _ in range(5):
            delays.append(current_delay)
            current_delay = min(
                current_delay * client.reconnect_multiplier, client.max_reconnect_delay
            )

        # Exponential growth with cap
        assert delays == [1.0, 2.0, 4.0, 8.0, 10.0]


# =============================================================================
# PHASE 6: Message Handling Tests
# =============================================================================


class TestMessageHandling:
    """Test incoming message processing."""

    def test_handle_message_emits_typed_event(self):
        """_handle_message emits event to typed listeners."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        client.on("game.tick", lambda e: received.append(e))

        message = {
            "type": "game.tick",
            "ts": 1737200000000,
            "gameId": "test-game",
            "seq": 1,
            "data": {"price": 1.5, "tickCount": 10},
        }

        client._handle_message(message)

        assert len(received) == 1
        assert received[0]["data"]["price"] == 1.5

    def test_handle_message_updates_metrics(self):
        """_handle_message updates message count and latency."""
        from foundation.client import FoundationClient

        client = FoundationClient()

        message = {
            "type": "game.tick",
            "ts": 1737200000000,
            "seq": 1,
            "data": {"price": 1.5},
        }

        client._handle_message(message)

        metrics = client.get_metrics()
        assert metrics.message_count == 1
        assert metrics.last_message_time is not None

    def test_handle_message_calculates_latency(self):
        """_handle_message calculates and tracks latency."""
        import time

        from foundation.client import FoundationClient

        client = FoundationClient()

        # Use recent timestamp
        now_ms = int(time.time() * 1000)
        message = {
            "type": "game.tick",
            "ts": now_ms - 50,  # 50ms ago
            "seq": 1,
            "data": {"price": 1.5},
        }

        client._handle_message(message)

        metrics = client.get_metrics()
        # Latency should be roughly 50ms (allow for test execution time)
        assert metrics.average_latency >= 40
        assert metrics.average_latency < 200


# =============================================================================
# PHASE 7: Connection Callback Tests
# =============================================================================


class TestConnectionCallbacks:
    """Test connection state change callbacks."""

    def test_connection_event_emitted_on_connect(self):
        """'connection' event emitted when connected."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        client.on("connection", lambda e: received.append(e))

        # Simulate connection established
        client._on_connected()

        assert len(received) == 1
        assert received[0]["connected"] is True

    def test_connection_event_emitted_on_disconnect(self):
        """'connection' event emitted when disconnected."""
        from foundation.client import FoundationClient

        client = FoundationClient()
        received = []

        client.on("connection", lambda e: received.append(e))

        # Simulate disconnection
        client._on_disconnected(code=1000, reason="Normal closure")

        assert len(received) == 1
        assert received[0]["connected"] is False
        assert received[0]["code"] == 1000
