"""
Tests for EventStoreService - EventBus integration

Phase 12B, Issue #25
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


class TestEventStoreServiceInstantiation:
    """Tests for service initialization"""

    def test_instantiate_with_defaults(self, event_bus, paths):
        """Service can be instantiated with defaults"""
        service = EventStoreService(event_bus, paths)
        assert service is not None
        assert service.session_id is not None
        service.stop()

    def test_instantiate_with_custom_session_id(self, event_bus, paths):
        """Service accepts custom session ID"""
        custom_id = "test-session-123"
        service = EventStoreService(event_bus, paths, session_id=custom_id)
        assert service.session_id == custom_id
        service.stop()

    def test_initial_event_count_is_zero(self, service):
        """New service has zero buffered events"""
        service.start()
        assert service.event_count == 0


class TestEventStoreServiceLifecycle:
    """Tests for start/stop lifecycle"""

    def test_start_subscribes_to_events(self, event_bus, paths):
        """start() subscribes to EventBus events"""
        service = EventStoreService(event_bus, paths)
        service.start()

        # Verify subscription by publishing and checking buffer
        event_bus.publish(Events.WS_RAW_EVENT, {"event": "test", "data": {}})

        # Give EventBus time to process
        import time

        time.sleep(0.2)

        assert service.event_count == 1
        service.stop()

    def test_stop_unsubscribes_from_events(self, event_bus, paths):
        """stop() unsubscribes from EventBus"""
        service = EventStoreService(event_bus, paths)
        service.start()
        service.stop()

        # Publish event after stop - should not be received
        event_bus.publish(Events.WS_RAW_EVENT, {"event": "test", "data": {}})

        import time

        time.sleep(0.2)

        assert service.event_count == 0

    def test_context_manager(self, event_bus, paths):
        """Service works as context manager"""
        with EventStoreService(event_bus, paths) as service:
            assert service.session_id is not None

    def test_double_start_is_safe(self, service):
        """Calling start() twice is safe"""
        service.start()
        service.start()  # Should not raise

    def test_double_stop_is_safe(self, service):
        """Calling stop() twice is safe"""
        service.start()
        service.stop()
        service.stop()  # Should not raise


class TestWebSocketEventHandling:
    """Tests for WS_RAW_EVENT handling"""

    def test_ws_raw_event_stored(self, event_bus, paths, temp_data_dir):
        """WS_RAW_EVENT is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.WS_RAW_EVENT,
            {
                "event": "gameStateUpdate",
                "data": {"gameId": "game-123", "tick": 100},
                "source": "cdp",
            },
        )

        import time

        time.sleep(0.3)

        # Check file was created
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        service.stop()

    def test_ws_event_fields_preserved(self, event_bus, paths, temp_data_dir):
        """WS event fields are preserved in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.WS_RAW_EVENT,
            {
                "event": "playerUpdate",
                "data": {"playerId": "player-456"},
                "source": "public_ws",
                "game_id": "game-789",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        assert table.column("event_name")[0].as_py() == "playerUpdate"
        assert table.column("doc_type")[0].as_py() == "ws_event"
        service.stop()


class TestGameTickHandling:
    """Tests for GAME_TICK handling"""

    def test_game_tick_stored(self, event_bus, paths, temp_data_dir):
        """GAME_TICK is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 150,
                "price": 2.5,
                "gameId": "game-abc",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        service.stop()

    def test_game_tick_fields_preserved(self, event_bus, paths, temp_data_dir):
        """Game tick fields are preserved"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.GAME_TICK,
            {
                "tick": 200,
                "multiplier": 3.14159,
                "gameId": "game-xyz",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        assert table.column("tick")[0].as_py() == 200
        assert table.column("doc_type")[0].as_py() == "game_tick"
        service.stop()


class TestPlayerUpdateHandling:
    """Tests for PLAYER_UPDATE handling"""

    def test_player_update_stored(self, event_bus, paths, temp_data_dir):
        """PLAYER_UPDATE is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.PLAYER_UPDATE,
            {
                "gameId": "game-123",
                "playerId": "player-456",
                "cash": "100.50",
                "positionQty": "10.5",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        service.stop()


class TestTradeActionHandling:
    """Tests for trade action handling"""

    def test_buy_trade_stored(self, event_bus, paths, temp_data_dir):
        """TRADE_BUY is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.TRADE_BUY,
            {
                "gameId": "game-123",
                "amount": 50,
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()
        assert table.column("action_type")[0].as_py() == "buy"
        assert table.column("doc_type")[0].as_py() == "player_action"
        service.stop()

    def test_sell_trade_stored(self, event_bus, paths, temp_data_dir):
        """TRADE_SELL is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.TRADE_SELL,
            {
                "gameId": "game-123",
                "percentage": 50,
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()
        assert table.column("action_type")[0].as_py() == "sell"
        service.stop()

    def test_sidebet_stored(self, event_bus, paths, temp_data_dir):
        """TRADE_SIDEBET is stored in Parquet"""
        service = EventStoreService(event_bus, paths, buffer_size=1)
        service.start()

        event_bus.publish(
            Events.TRADE_SIDEBET,
            {
                "gameId": "game-123",
                "betType": "moon",
            },
        )

        import time

        time.sleep(0.3)

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()
        assert table.column("action_type")[0].as_py() == "sidebet"
        service.stop()


class TestSequenceNumbers:
    """Tests for sequence number generation"""

    def test_sequence_numbers_increment(self, event_bus, paths, temp_data_dir):
        """Events get incrementing sequence numbers"""
        service = EventStoreService(event_bus, paths, buffer_size=5)
        service.start()

        # Publish multiple events
        for i in range(3):
            event_bus.publish(
                Events.WS_RAW_EVENT,
                {"event": f"test-{i}", "data": {}},
            )

        import time

        time.sleep(0.3)

        # Flush to write
        service.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        seqs = [table.column("seq")[i].as_py() for i in range(len(table))]
        assert seqs == [1, 2, 3]
        service.stop()


class TestFlush:
    """Tests for manual flush"""

    def test_manual_flush(self, event_bus, paths, temp_data_dir):
        """Manual flush writes buffered events"""
        service = EventStoreService(event_bus, paths, buffer_size=100)
        service.start()

        event_bus.publish(Events.WS_RAW_EVENT, {"event": "test", "data": {}})

        import time

        time.sleep(0.2)

        assert service.event_count == 1

        service.flush()
        assert service.event_count == 0

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        service.stop()
