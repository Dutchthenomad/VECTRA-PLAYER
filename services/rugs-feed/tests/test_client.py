"""Tests for RugsFeedClient."""

import sys

sys.path.insert(0, "services/rugs-feed")

from src.client import ConnectionState, RugsFeedClient


class TestRugsFeedClient:
    """Test RugsFeedClient initialization and state."""

    def test_initial_state_is_disconnected(self):
        """Client should start in DISCONNECTED state."""
        client = RugsFeedClient()
        assert client.state == ConnectionState.DISCONNECTED

    def test_url_default(self):
        """Client should use correct default URL."""
        client = RugsFeedClient()
        assert "backend.rugs.fun" in client.url

    def test_url_custom(self):
        """Client should accept custom URL."""
        client = RugsFeedClient(url="wss://custom.example.com")
        assert client.url == "wss://custom.example.com"

    def test_event_handlers_registered(self):
        """Client should have handlers for key events."""
        client = RugsFeedClient()
        assert client._handlers is not None
        assert "gameStateUpdate" in client._handlers
        assert "standard/newTrade" in client._handlers
