"""
Tests for EventStoreService recording toggle functionality.

Part of 1-click recording toggle feature - Task 1.
"""

import pytest

from services.event_bus import EventBus
from services.event_store.paths import EventStorePaths
from services.event_store.service import EventStoreService


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests."""
    data_dir = tmp_path / "rugs_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def paths(temp_data_dir):
    """Create EventStorePaths with temp directory."""
    return EventStorePaths(data_dir=temp_data_dir)


@pytest.fixture
def event_bus():
    """Create and start EventBus."""
    bus = EventBus()
    bus.start()
    yield bus
    bus.stop()
    bus.clear_all()


@pytest.fixture
def event_store(event_bus, paths):
    """Create EventStoreService instance."""
    service = EventStoreService(event_bus, paths, buffer_size=10, flush_interval=60.0)
    yield service
    if service._started:
        service.stop()


class TestEventStoreRecordingToggle:
    """Test EventStoreService pause/resume functionality."""

    def test_starts_paused_by_default(self, event_store):
        """EventStore should start in paused state."""
        event_store.start()
        assert event_store.is_paused is True
        assert event_store.is_recording is False

    def test_resume_enables_recording(self, event_store):
        """resume() should enable event recording."""
        event_store.start()
        event_store.resume()
        assert event_store.is_paused is False
        assert event_store.is_recording is True

    def test_pause_disables_recording(self, event_store):
        """pause() should disable event recording."""
        event_store.start()
        event_store.resume()
        event_store.pause()
        assert event_store.is_paused is True
        assert event_store.is_recording is False

    def test_toggle_recording(self, event_store):
        """toggle_recording() should flip recording state."""
        event_store.start()
        assert event_store.is_recording is False

        result = event_store.toggle_recording()
        assert result is True
        assert event_store.is_recording is True

        result = event_store.toggle_recording()
        assert result is False
        assert event_store.is_recording is False

    def test_recorded_game_ids_tracked(self, event_store):
        """Service should track unique game_ids recorded."""
        event_store.start()
        event_store.resume()
        assert len(event_store.recorded_game_ids) == 0
        # recorded_game_ids should be a set
        assert isinstance(event_store.recorded_game_ids, set)

    def test_total_events_recorded_property(self, event_store):
        """total_events_recorded property should track total persisted events."""
        event_store.start()
        assert event_store.total_events_recorded == 0


class TestRecordingPausedBehavior:
    """Test that events are dropped when recording is paused."""

    def test_ws_event_dropped_when_paused(self, event_bus, paths, temp_data_dir):
        """WS_RAW_EVENT should not be stored when recording is paused."""
        import time

        from services.event_bus import Events

        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        # Should be paused by default
        assert service.is_paused is True

        # Publish event while paused
        event_bus.publish(
            Events.WS_RAW_EVENT,
            {"event": "test", "data": {}},
        )
        time.sleep(0.2)

        # No files should be created
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) == 0

        service.stop()

    def test_ws_event_stored_when_resumed(self, event_bus, paths, temp_data_dir):
        """WS_RAW_EVENT should be stored after resume() is called."""
        import time

        from services.event_bus import Events

        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()
        service.resume()  # Enable recording

        assert service.is_recording is True

        # Publish event while recording
        event_bus.publish(
            Events.WS_RAW_EVENT,
            {"event": "test", "data": {}},
        )
        time.sleep(0.3)

        # File should be created
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

        service.stop()

    def test_game_tick_dropped_when_paused(self, event_bus, paths):
        """GAME_TICK should not be stored when recording is paused."""
        import time

        from services.event_bus import Events

        service = EventStoreService(event_bus, paths, buffer_size=100)
        service.start()

        assert service.is_paused is True

        event_bus.publish(
            Events.GAME_TICK,
            {"tick": 100, "price": 2.5, "gameId": "game-123"},
        )
        time.sleep(0.2)

        # Buffer should remain empty
        assert service.event_count == 0

        service.stop()


class TestGameIdDeduplication:
    """Test that duplicate complete_game writes are prevented."""

    def test_complete_game_deduplication(self, event_bus, paths, temp_data_dir):
        """Duplicate game_ids in gameHistory should only be written once."""
        import time

        from services.event_bus import Events

        service = EventStoreService(event_bus, paths, buffer_size=10)
        service.start()
        service.resume()

        # Publish gameStateUpdate with gameHistory containing games
        # Note: gameHistory games use "id" field, not "gameId"
        game_history = [
            {"id": "game-001", "prices": [1.0, 1.5], "globalSidebets": []},
            {"id": "game-002", "prices": [1.0, 2.0], "globalSidebets": []},
        ]

        event_bus.publish(
            Events.WS_RAW_EVENT,
            {
                "event": "gameStateUpdate",
                "data": {"gameHistory": game_history},
            },
        )
        time.sleep(0.3)

        # Both games should be tracked
        assert "game-001" in service.recorded_game_ids
        assert "game-002" in service.recorded_game_ids

        # Publish again with same games (simulating rug event with same history)
        event_bus.publish(
            Events.WS_RAW_EVENT,
            {
                "event": "gameStateUpdate",
                "data": {"gameHistory": game_history},
            },
        )
        time.sleep(0.3)

        service.flush()
        service.stop()

        # Verify deduplication by checking recorded_game_ids size
        # (should still only have 2 unique games)
        assert len(service.recorded_game_ids) == 2
