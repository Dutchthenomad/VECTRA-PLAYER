"""Tests for WebSocket broadcaster."""

import sys
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, "services/rugs-feed")

from src.broadcaster import RawEventBroadcaster, get_broadcaster
from src.client import CapturedEvent


class TestRawEventBroadcaster:
    """Test RawEventBroadcaster class."""

    def test_initialization(self):
        """Test broadcaster initialization."""
        broadcaster = RawEventBroadcaster()
        assert broadcaster.client_count == 0
        assert not broadcaster.is_running

    def test_start_stop(self):
        """Test broadcaster start/stop."""
        broadcaster = RawEventBroadcaster()

        broadcaster.start()
        assert broadcaster.is_running

        broadcaster.stop()
        assert not broadcaster.is_running

    @pytest.mark.asyncio
    async def test_register_unregister(self):
        """Test client registration."""
        broadcaster = RawEventBroadcaster()
        broadcaster.start()

        # Mock websocket
        ws = AsyncMock()

        await broadcaster.register(ws)
        assert broadcaster.client_count == 1

        await broadcaster.unregister(ws)
        assert broadcaster.client_count == 0

        broadcaster.stop()

    def test_broadcast_before_start(self):
        """Test broadcasting before start logs warning."""
        broadcaster = RawEventBroadcaster()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={"test": True},
            game_id="test-123",
        )

        # Should not raise, just log warning
        broadcaster.broadcast(event)

    def test_broadcast_queues_event(self):
        """Test broadcasting queues event."""
        broadcaster = RawEventBroadcaster()
        broadcaster.start()

        event = CapturedEvent(
            event_type="gameStateUpdate",
            data={"test": True},
            game_id="test-123",
        )

        broadcaster.broadcast(event)

        stats = broadcaster.get_stats()
        assert stats["queue_size"] == 1

        broadcaster.stop()

    def test_get_stats(self):
        """Test stats reporting."""
        broadcaster = RawEventBroadcaster()

        stats = broadcaster.get_stats()
        assert "client_count" in stats
        assert "is_running" in stats
        assert "events_broadcast" in stats
        assert "events_dropped" in stats
        assert "queue_size" in stats


class TestGetBroadcaster:
    """Test global broadcaster instance."""

    def test_singleton(self):
        """Test get_broadcaster returns singleton."""
        b1 = get_broadcaster()
        b2 = get_broadcaster()
        assert b1 is b2
