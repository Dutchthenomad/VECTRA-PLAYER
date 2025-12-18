"""
TDD Tests for ParquetWriter

Phase 12B, Issue #25: Buffered Parquet Writer with Atomic Writes

Tests written FIRST per TDD Iron Law.
"""

import json
import time
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from services.event_store.paths import EventStorePaths
from services.event_store.schema import (
    DocType,
    EventEnvelope,
    EventSource,
)
from services.event_store.writer import ParquetWriter

# =============================================================================
# Fixtures
# =============================================================================


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
def writer(paths):
    """Create ParquetWriter instance"""
    w = ParquetWriter(paths)
    yield w
    w.close()


@pytest.fixture
def sample_ws_event() -> EventEnvelope:
    """Create sample WebSocket event envelope"""
    return EventEnvelope.from_ws_event(
        event_name="gameStateUpdate",
        data={"gameId": "test-game-123", "tick": 100},
        source=EventSource.CDP,
        session_id=str(uuid.uuid4()),
        seq=1,
        game_id="test-game-123",
    )


@pytest.fixture
def sample_game_tick() -> EventEnvelope:
    """Create sample game tick envelope"""
    return EventEnvelope.from_game_tick(
        tick=100,
        price=Decimal("1.5"),
        data={"tick": 100, "price": 1.5, "gameId": "test-game-123"},
        source=EventSource.PUBLIC_WS,
        session_id=str(uuid.uuid4()),
        seq=2,
        game_id="test-game-123",
    )


@pytest.fixture
def sample_player_action() -> EventEnvelope:
    """Create sample player action envelope"""
    return EventEnvelope.from_player_action(
        action_type="buy",
        data={"amount": 100, "shitcoinAddress": "0x123"},
        source=EventSource.UI,
        session_id=str(uuid.uuid4()),
        seq=3,
        game_id="test-game-123",
        player_id="player-456",
    )


def make_event(
    doc_type: DocType, session_id: str, seq: int, game_id: str = "game-1"
) -> EventEnvelope:
    """Helper to create events of specific doc_type"""
    if doc_type == DocType.WS_EVENT:
        return EventEnvelope.from_ws_event(
            event_name="testEvent",
            data={"seq": seq},
            source=EventSource.CDP,
            session_id=session_id,
            seq=seq,
            game_id=game_id,
        )
    elif doc_type == DocType.GAME_TICK:
        return EventEnvelope.from_game_tick(
            tick=seq,
            price=Decimal(str(seq * 0.1)),
            data={"tick": seq},
            source=EventSource.CDP,
            session_id=session_id,
            seq=seq,
            game_id=game_id,
        )
    elif doc_type == DocType.PLAYER_ACTION:
        return EventEnvelope.from_player_action(
            action_type="test",
            data={"seq": seq},
            source=EventSource.UI,
            session_id=session_id,
            seq=seq,
            game_id=game_id,
        )
    elif doc_type == DocType.SERVER_STATE:
        return EventEnvelope.from_server_state(
            data={"seq": seq},
            source=EventSource.CDP,
            session_id=session_id,
            seq=seq,
            game_id=game_id,
            player_id="player-1",
            cash=Decimal("100.00"),
        )
    else:  # SYSTEM_EVENT
        return EventEnvelope.from_system_event(
            event_type="test",
            data={"seq": seq},
            source=EventSource.CDP,
            session_id=session_id,
            seq=seq,
        )


# =============================================================================
# Instantiation Tests
# =============================================================================


class TestParquetWriterInstantiation:
    """Tests for ParquetWriter initialization"""

    def test_instantiate_with_defaults(self, paths):
        """ParquetWriter can be instantiated with default parameters"""
        writer = ParquetWriter(paths)
        assert writer is not None
        assert writer.buffer_size == 100  # Default
        assert writer.flush_interval == 5.0  # Default
        writer.close()

    def test_instantiate_with_custom_params(self, paths):
        """ParquetWriter accepts custom buffer_size and flush_interval"""
        writer = ParquetWriter(paths, buffer_size=50, flush_interval=10.0)
        assert writer.buffer_size == 50
        assert writer.flush_interval == 10.0
        writer.close()

    def test_instantiate_creates_directories(self, paths):
        """ParquetWriter ensures required directories exist on init"""
        writer = ParquetWriter(paths)
        assert paths.events_parquet_dir.exists()
        writer.close()

    def test_initial_buffer_count_is_zero(self, writer):
        """New writer has empty buffer"""
        assert writer.buffer_count == 0


# =============================================================================
# Buffer Management Tests
# =============================================================================


class TestBufferManagement:
    """Tests for buffer accumulation"""

    def test_write_adds_event_to_buffer(self, writer, sample_ws_event):
        """write() adds event to internal buffer"""
        writer.write(sample_ws_event)
        assert writer.buffer_count == 1

    def test_buffer_accumulates_multiple_events(self, writer, sample_ws_event):
        """Buffer accumulates multiple events"""
        session_id = str(uuid.uuid4())
        for i in range(10):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)
        assert writer.buffer_count == 10

    def test_buffer_count_property(self, writer):
        """buffer_count returns current buffer size"""
        session_id = str(uuid.uuid4())
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)
        assert writer.buffer_count == 5


# =============================================================================
# Manual Flush Tests
# =============================================================================


class TestManualFlush:
    """Tests for manual flush behavior"""

    def test_flush_writes_parquet_file(self, writer, temp_data_dir):
        """flush() writes buffered events to Parquet file"""
        session_id = str(uuid.uuid4())
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        paths_written = writer.flush()
        assert paths_written is not None
        assert len(paths_written) > 0

        # Verify file exists
        for path in paths_written:
            assert path.exists()
            assert path.suffix == ".parquet"

    def test_flush_clears_buffer(self, writer):
        """Buffer is cleared after flush"""
        session_id = str(uuid.uuid4())
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        writer.flush()
        assert writer.buffer_count == 0

    def test_flush_empty_buffer_returns_none(self, writer):
        """Flushing empty buffer returns None"""
        result = writer.flush()
        assert result is None

    def test_flush_returns_list_of_paths(self, writer):
        """flush() returns list of written file paths"""
        session_id = str(uuid.uuid4())
        for i in range(3):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        paths = writer.flush()
        assert isinstance(paths, list)
        assert all(isinstance(p, Path) for p in paths)


# =============================================================================
# Auto-Flush on Buffer Size Tests
# =============================================================================


class TestAutoFlushOnBufferSize:
    """Tests for automatic flush when buffer reaches threshold"""

    def test_auto_flush_at_buffer_size(self, paths):
        """Flush triggered when buffer reaches buffer_size"""
        writer = ParquetWriter(paths, buffer_size=10, flush_interval=3600)  # Long interval
        session_id = str(uuid.uuid4())

        for i in range(10):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        # Buffer should have been flushed
        assert writer.buffer_count == 0
        writer.close()

    def test_auto_flush_creates_file(self, paths, temp_data_dir):
        """Auto-flush creates Parquet file"""
        writer = ParquetWriter(paths, buffer_size=5, flush_interval=3600)
        session_id = str(uuid.uuid4())

        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        # Check file was created
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1
        writer.close()

    def test_multiple_auto_flushes(self, paths):
        """Multiple auto-flushes work correctly"""
        writer = ParquetWriter(paths, buffer_size=5, flush_interval=3600)
        session_id = str(uuid.uuid4())

        # First batch
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)
        assert writer.buffer_count == 0

        # Second batch
        for i in range(5, 10):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)
        assert writer.buffer_count == 0

        writer.close()


# =============================================================================
# Auto-Flush on Time Interval Tests
# =============================================================================


class TestAutoFlushOnTimeInterval:
    """Tests for time-based automatic flush"""

    def test_time_based_flush_on_write(self, paths):
        """Events older than flush_interval trigger flush on next write"""
        writer = ParquetWriter(paths, buffer_size=1000, flush_interval=0.1)  # 100ms
        session_id = str(uuid.uuid4())

        # Write one event
        event = make_event(DocType.WS_EVENT, session_id, 1)
        writer.write(event)
        assert writer.buffer_count == 1

        # Wait for interval to pass
        time.sleep(0.15)

        # Next write should trigger flush
        event2 = make_event(DocType.WS_EVENT, session_id, 2)
        writer.write(event2)

        # Previous events should be flushed, only new event in buffer
        assert writer.buffer_count == 1
        writer.close()


# =============================================================================
# Partitioning Tests
# =============================================================================


class TestPartitioning:
    """Tests for Parquet partitioning by doc_type and date"""

    def test_partition_by_doc_type(self, paths, temp_data_dir):
        """Events partitioned into correct doc_type directories"""
        writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
        session_id = str(uuid.uuid4())

        # Write events of different types
        writer.write(make_event(DocType.WS_EVENT, session_id, 1))
        writer.write(make_event(DocType.GAME_TICK, session_id, 2))
        writer.write(make_event(DocType.PLAYER_ACTION, session_id, 3))

        writer.flush()

        # Check partition directories exist
        parquet_dir = temp_data_dir / "events_parquet"
        assert (parquet_dir / "doc_type=ws_event").exists()
        assert (parquet_dir / "doc_type=game_tick").exists()
        assert (parquet_dir / "doc_type=player_action").exists()
        writer.close()

    def test_partition_by_date(self, paths, temp_data_dir):
        """Events partitioned into date subdirectories"""
        writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
        session_id = str(uuid.uuid4())

        writer.write(make_event(DocType.WS_EVENT, session_id, 1))
        writer.flush()

        # Check date partition exists
        today = datetime.utcnow().strftime("%Y-%m-%d")
        parquet_dir = temp_data_dir / "events_parquet"
        doc_type_dir = parquet_dir / "doc_type=ws_event"
        date_dirs = list(doc_type_dir.glob("date=*"))
        assert len(date_dirs) >= 1
        assert any(today in str(d) for d in date_dirs)
        writer.close()

    def test_multiple_doc_types_create_separate_files(self, paths, temp_data_dir):
        """Different doc_types create files in separate partition directories"""
        writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
        session_id = str(uuid.uuid4())

        # Add multiple events of each type
        for i in range(3):
            writer.write(make_event(DocType.WS_EVENT, session_id, i))
            writer.write(make_event(DocType.GAME_TICK, session_id, i + 10))

        paths_written = writer.flush()

        # Should have files in both partitions
        ws_files = [p for p in paths_written if "ws_event" in str(p)]
        tick_files = [p for p in paths_written if "game_tick" in str(p)]
        assert len(ws_files) >= 1
        assert len(tick_files) >= 1
        writer.close()


# =============================================================================
# Parquet File Format Tests
# =============================================================================


class TestParquetFileFormat:
    """Tests for Parquet file validity and data integrity"""

    def test_written_file_is_valid_parquet(self, writer, temp_data_dir):
        """Written files are valid Parquet format"""
        session_id = str(uuid.uuid4())
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        writer.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

        # Read with pyarrow ParquetFile to verify validity (not dataset API)
        for pf in parquet_files:
            pf_reader = pq.ParquetFile(pf)
            table = pf_reader.read()
            assert table is not None
            assert len(table) > 0

    def test_all_fields_preserved_in_parquet(self, writer, temp_data_dir):
        """All EventEnvelope fields are preserved in Parquet"""
        session_id = str(uuid.uuid4())
        event = make_event(DocType.WS_EVENT, session_id, 1, game_id="test-game-xyz")
        writer.write(event)
        writer.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        # Check required fields exist
        required_fields = ["ts", "source", "doc_type", "session_id", "seq", "direction", "raw_json"]
        column_names = [field.name for field in table.schema]
        for field in required_fields:
            assert field in column_names, f"Missing field: {field}"

        # Verify values using PyArrow directly
        assert table.column("session_id")[0].as_py() == session_id
        assert table.column("seq")[0].as_py() == 1
        assert table.column("doc_type")[0].as_py() == "ws_event"

    def test_decimal_fields_serialized_correctly(self, writer, temp_data_dir):
        """Decimal fields are serialized and can be restored"""
        session_id = str(uuid.uuid4())
        event = EventEnvelope.from_game_tick(
            tick=100,
            price=Decimal("1.23456789"),
            data={"tick": 100},
            source=EventSource.CDP,
            session_id=session_id,
            seq=1,
            game_id="test-game",
        )
        writer.write(event)
        writer.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        # Price should be stored as string and restorable
        price_str = table.column("price")[0].as_py()
        restored_price = Decimal(price_str)
        assert restored_price == Decimal("1.23456789")

    def test_raw_json_is_valid_json(self, writer, temp_data_dir):
        """raw_json field contains valid JSON"""
        session_id = str(uuid.uuid4())
        event = make_event(DocType.WS_EVENT, session_id, 1)
        writer.write(event)
        writer.flush()

        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        pf_reader = pq.ParquetFile(parquet_files[0])
        table = pf_reader.read()

        raw_json_str = table.column("raw_json")[0].as_py()
        parsed = json.loads(raw_json_str)
        assert isinstance(parsed, dict)


# =============================================================================
# Atomic Write Tests
# =============================================================================


class TestAtomicWrites:
    """Tests for atomic file write operations"""

    def test_no_partial_files_on_success(self, writer, temp_data_dir):
        """Successful write leaves only complete files, no temp files"""
        session_id = str(uuid.uuid4())
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        writer.flush()

        # Check no temp files remain
        temp_files = list(temp_data_dir.rglob("*.tmp"))
        partial_files = list(temp_data_dir.rglob("*.partial"))
        assert len(temp_files) == 0
        assert len(partial_files) == 0

    def test_unique_filenames_prevent_overwrites(self, paths, temp_data_dir):
        """Each flush creates uniquely named file to prevent overwrites"""
        writer = ParquetWriter(paths, buffer_size=5, flush_interval=3600)
        session_id = str(uuid.uuid4())

        # First flush
        for i in range(5):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        # Second flush
        for i in range(5, 10):
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        # Flush remaining
        writer.close()

        # Should have 2 separate files
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 2


# =============================================================================
# Close/Cleanup Tests
# =============================================================================


class TestCloseAndCleanup:
    """Tests for proper resource cleanup"""

    def test_close_flushes_remaining_buffer(self, paths, temp_data_dir):
        """close() flushes any remaining buffered events"""
        writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
        session_id = str(uuid.uuid4())

        for i in range(3):  # Less than buffer_size
            event = make_event(DocType.WS_EVENT, session_id, i)
            writer.write(event)

        assert writer.buffer_count == 3
        writer.close()

        # File should exist with our events
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

    def test_context_manager(self, paths, temp_data_dir):
        """Writer works as context manager"""
        session_id = str(uuid.uuid4())

        with ParquetWriter(paths) as writer:
            for i in range(3):
                event = make_event(DocType.WS_EVENT, session_id, i)
                writer.write(event)

        # Events should be flushed after context exit
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1

    def test_double_close_is_safe(self, paths):
        """Calling close() multiple times is safe"""
        writer = ParquetWriter(paths)
        writer.close()
        writer.close()  # Should not raise


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for thread-safe operations"""

    def test_concurrent_writes(self, paths, temp_data_dir):
        """Multiple threads can write concurrently"""
        import threading

        writer = ParquetWriter(paths, buffer_size=50, flush_interval=3600)
        session_id = str(uuid.uuid4())
        errors = []

        def write_events(start_seq: int):
            try:
                for i in range(20):
                    event = make_event(DocType.WS_EVENT, session_id, start_seq + i)
                    writer.write(event)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_events, args=(i * 100,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        writer.close()

        assert len(errors) == 0, f"Thread errors: {errors}"

        # Verify data was written
        parquet_files = list(temp_data_dir.rglob("*.parquet"))
        assert len(parquet_files) >= 1


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_write_after_close_raises(self, paths):
        """Writing after close raises exception"""
        writer = ParquetWriter(paths)
        writer.close()

        session_id = str(uuid.uuid4())
        event = make_event(DocType.WS_EVENT, session_id, 1)

        with pytest.raises(RuntimeError):
            writer.write(event)

    def test_flush_after_close_is_safe(self, paths):
        """flush() after close() is safe and returns None"""
        writer = ParquetWriter(paths)
        writer.close()

        result = writer.flush()
        assert result is None

    def test_handles_all_doc_types(self, paths, temp_data_dir):
        """Writer handles all DocType enum values"""
        writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
        session_id = str(uuid.uuid4())

        for i, doc_type in enumerate(DocType):
            event = make_event(doc_type, session_id, i)
            writer.write(event)

        writer.close()

        # Should have partitions for each doc_type
        parquet_dir = temp_data_dir / "events_parquet"
        for doc_type in DocType:
            partition_dir = parquet_dir / f"doc_type={doc_type.value}"
            assert partition_dir.exists(), f"Missing partition for {doc_type}"
