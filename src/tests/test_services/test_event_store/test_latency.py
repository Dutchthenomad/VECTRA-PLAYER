"""
Tests for Trade Latency Capture in EventStoreService

Phase 12D, Task 4
"""

import pyarrow.parquet as pq
import pytest

from services.event_bus import EventBus, Events
from services.event_store.paths import EventStorePaths
from services.event_store.service import EventStoreService


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests"""
    data_dir = tmp_path / "rugs_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def paths(temp_data_dir):
    """Create EventStorePaths with temp directory"""
    return EventStorePaths(data_dir=temp_data_dir)


@pytest.fixture
def event_bus():
    """Create and start EventBus"""
    bus = EventBus()
    bus.start()
    yield bus
    bus.stop()
    bus.clear_all()


@pytest.fixture
def service(event_bus, paths):
    """Create EventStoreService instance"""
    svc = EventStoreService(event_bus, paths, buffer_size=10, flush_interval=60.0)
    yield svc
    svc.stop()


class TestTradeConfirmedEvent:
    """Tests for TRADE_CONFIRMED event handling"""

    def test_trade_confirmed_stored(self, event_bus, paths, temp_data_dir):
        """TRADE_CONFIRMED is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        event_bus.publish(
            Events.TRADE_CONFIRMED,
            {
                "gameId": "game-123",
                "playerId": "player-456",
                "username": "testuser",
                "timestamp_submitted": "2025-12-21T12:00:00.000Z",
                "timestamp_confirmed": "2025-12-21T12:00:00.150Z",
                "latency_ms": 150,
                "action_id": "action-789",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        service.stop()

    def test_trade_confirmed_fields_preserved(self, event_bus, paths, temp_data_dir):
        """Trade confirmed fields are preserved in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        event_bus.publish(
            Events.TRADE_CONFIRMED,
            {
                "gameId": "game-abc",
                "playerId": "player-xyz",
                "username": "testplayer",
                "timestamp_submitted": "2025-12-21T12:00:00.000Z",
                "timestamp_confirmed": "2025-12-21T12:00:00.200Z",
                "latency_ms": 200,
                "action_id": "action-123",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        assert table.column("action_type")[0].as_py() == "trade_confirmed"
        assert table.column("doc_type")[0].as_py() == "player_action"
        assert table.column("game_id")[0].as_py() == "game-abc"
        assert table.column("player_id")[0].as_py() == "player-xyz"
        assert table.column("username")[0].as_py() == "testplayer"
        service.stop()

    def test_trade_confirmed_raw_json_contains_latency(self, event_bus, paths, temp_data_dir):
        """Trade confirmed raw_json contains latency data"""
        import json

        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        event_data = {
            "gameId": "game-123",
            "playerId": "player-456",
            "timestamp_submitted": "2025-12-21T12:00:00.000Z",
            "timestamp_confirmed": "2025-12-21T12:00:00.150Z",
            "latency_ms": 150,
            "action_id": "action-789",
        }

        event_bus.publish(Events.TRADE_CONFIRMED, event_data)

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        raw_json = table.column("raw_json")[0].as_py()
        parsed = json.loads(raw_json)

        assert "latency_ms" in parsed
        assert parsed["latency_ms"] == 150
        assert parsed["timestamp_submitted"] == "2025-12-21T12:00:00.000Z"
        assert parsed["timestamp_confirmed"] == "2025-12-21T12:00:00.150Z"
        assert parsed["action_id"] == "action-789"
        service.stop()

    def test_multiple_trade_confirmed_events(self, event_bus, paths, temp_data_dir):
        """Multiple TRADE_CONFIRMED events are stored correctly"""
        service = EventStoreService(event_bus, paths, buffer_size=5)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # Publish multiple trade confirmations with different latencies
        latencies = [100, 150, 200]
        for i, latency in enumerate(latencies):
            event_bus.publish(
                Events.TRADE_CONFIRMED,
                {
                    "gameId": f"game-{i}",
                    "playerId": "player-456",
                    "latency_ms": latency,
                    "action_id": f"action-{i}",
                },
            )

        import time

        time.sleep(0.3)

        # Flush to write
        service.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        # Check we have 3 events
        assert len(table) == 3

        # All should be trade_confirmed
        action_types = [table.column("action_type")[i].as_py() for i in range(len(table))]
        assert all(at == "trade_confirmed" for at in action_types)

        service.stop()

    def test_trade_confirmed_optional_fields(self, event_bus, paths, temp_data_dir):
        """Trade confirmed works with minimal required fields"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # Minimal data - only latency and action_id
        event_bus.publish(
            Events.TRADE_CONFIRMED,
            {
                "latency_ms": 100,
                "action_id": "action-minimal",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        assert table.column("action_type")[0].as_py() == "trade_confirmed"
        service.stop()


class TestTradeConfirmedSubscription:
    """Tests for TRADE_CONFIRMED subscription lifecycle"""

    def test_start_subscribes_to_trade_confirmed(self, event_bus, paths):
        """start() subscribes to TRADE_CONFIRMED event"""
        service = EventStoreService(event_bus, paths, buffer_size=10)
        service.start()
        service.resume()  # Enable recording (starts paused by default)

        # Verify subscription by publishing and checking buffer
        event_bus.publish(
            Events.TRADE_CONFIRMED,
            {"latency_ms": 100, "action_id": "test"},
        )

        import time

        time.sleep(0.2)

        assert service.event_count == 1
        service.stop()

    def test_stop_unsubscribes_from_trade_confirmed(self, event_bus, paths):
        """stop() unsubscribes from TRADE_CONFIRMED"""
        service = EventStoreService(event_bus, paths, buffer_size=10)
        service.start()
        service.resume()  # Enable recording first (starts paused by default)
        service.stop()

        # Publish event after stop - should not be received
        event_bus.publish(
            Events.TRADE_CONFIRMED,
            {"latency_ms": 100, "action_id": "test"},
        )

        import time

        time.sleep(0.2)

        assert service.event_count == 0
