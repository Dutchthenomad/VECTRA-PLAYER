"""
Parquet Writer Pattern

Demonstrates the event persistence pattern using PyArrow Parquet
for VECTRA-PLAYER's canonical data store.

Usage:
    from parquet_writer import ParquetEventWriter

    writer = ParquetEventWriter(base_path="~/rugs_data/events_parquet")
    writer.write_event({
        "doc_type": "game_tick",
        "game_id": "abc123",
        "tick": 100,
        "price": 2.5,
    })
    writer.flush()
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


@dataclass
class EventEnvelope:
    """
    Standard envelope for all persisted events.

    Design principles:
    - Consistent schema across all event types
    - JSON payload for flexibility
    - Timestamps for ordering and analysis
    """

    doc_type: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    game_id: str = ""
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "doc_type": self.doc_type,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "game_id": self.game_id,
            "payload": json.dumps(self.payload),
        }


class ParquetEventWriter:
    """
    Buffered Parquet writer for event persistence.

    Features:
    - Partitioned by doc_type for efficient queries
    - Buffered writes with configurable flush interval
    - Atomic file operations
    - Schema validation

    Usage:
        writer = ParquetEventWriter("~/rugs_data/events_parquet")

        # Write events
        writer.write_event({"doc_type": "game_tick", "tick": 1, "price": 1.0})
        writer.write_event({"doc_type": "game_tick", "tick": 2, "price": 1.2})

        # Flush to disk
        writer.flush()

        # Or auto-flush when buffer is full
        writer = ParquetEventWriter(path, buffer_size=1000)
    """

    # Schema definition
    SCHEMA = pa.schema(
        [
            ("doc_type", pa.string()),
            ("event_id", pa.string()),
            ("timestamp", pa.float64()),
            ("session_id", pa.string()),
            ("game_id", pa.string()),
            ("payload", pa.string()),  # JSON string
        ]
    )

    def __init__(
        self,
        base_path: str | Path,
        buffer_size: int = 100,
        auto_flush_seconds: float = 30.0,
    ):
        """
        Initialize writer.

        Args:
            base_path: Base directory for Parquet files
            buffer_size: Number of events to buffer before auto-flush
            auto_flush_seconds: Time interval for periodic flush
        """
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.buffer_size = buffer_size
        self.auto_flush_seconds = auto_flush_seconds

        self._buffers: dict[str, list[dict]] = {}
        self._last_flush = time.time()
        self._session_id = str(uuid.uuid4())[:8]

    def write_event(self, event: dict):
        """
        Write an event to the buffer.

        Args:
            event: Event dict with at least 'doc_type' key

        Automatically flushes if buffer exceeds size limit.
        """
        doc_type = event.get("doc_type", "unknown")

        # Create envelope
        envelope = EventEnvelope(
            doc_type=doc_type,
            session_id=self._session_id,
            game_id=event.get("game_id", ""),
            payload=event,
        )

        # Add to buffer
        if doc_type not in self._buffers:
            self._buffers[doc_type] = []
        self._buffers[doc_type].append(envelope.to_dict())

        # Auto-flush if buffer full
        if len(self._buffers[doc_type]) >= self.buffer_size:
            self._flush_buffer(doc_type)

        # Time-based auto-flush
        if time.time() - self._last_flush > self.auto_flush_seconds:
            self.flush()

    def flush(self):
        """Flush all buffers to disk."""
        for doc_type in list(self._buffers.keys()):
            self._flush_buffer(doc_type)
        self._last_flush = time.time()

    def _flush_buffer(self, doc_type: str):
        """Flush a single doc_type buffer."""
        buffer = self._buffers.get(doc_type, [])
        if not buffer:
            return

        # Create partition directory
        partition_path = self.base_path / f"doc_type={doc_type}"
        partition_path.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self._session_id}_{len(buffer)}.parquet"
        filepath = partition_path / filename

        # Convert to Arrow table
        table = pa.Table.from_pylist(buffer, schema=self.SCHEMA)

        # Write atomically (write to temp, then rename)
        temp_path = filepath.with_suffix(".tmp")
        pq.write_table(table, temp_path, compression="snappy")
        temp_path.rename(filepath)

        # Clear buffer
        self._buffers[doc_type] = []

    def close(self):
        """Flush and close writer."""
        self.flush()


class ParquetEventReader:
    """
    Reader for Parquet event store.

    Uses DuckDB for efficient querying.
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path).expanduser()

    def read_all(self, doc_type: str | None = None) -> list[dict]:
        """
        Read all events, optionally filtered by doc_type.

        Args:
            doc_type: Filter by document type

        Returns:
            List of event dicts
        """
        import duckdb

        if doc_type:
            pattern = self.base_path / f"doc_type={doc_type}" / "*.parquet"
        else:
            pattern = self.base_path / "**/*.parquet"

        query = f"SELECT * FROM read_parquet('{pattern}')"
        df = duckdb.execute(query).fetchdf()

        # Parse JSON payloads
        events = []
        for _, row in df.iterrows():
            event = row.to_dict()
            event["payload"] = json.loads(event["payload"])
            events.append(event)

        return events

    def query(self, sql: str) -> Any:
        """
        Execute SQL query on event store.

        Args:
            sql: DuckDB SQL query

        Returns:
            Query results

        Example:
            reader.query('''
                SELECT payload->>'tick' as tick, payload->>'price' as price
                FROM read_parquet('~/rugs_data/events_parquet/**/*.parquet')
                WHERE doc_type = 'game_tick'
                ORDER BY timestamp
                LIMIT 100
            ''')
        """
        import duckdb

        return duckdb.execute(sql).fetchall()


# Example usage
if __name__ == "__main__":
    import tempfile

    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = ParquetEventWriter(tmpdir, buffer_size=5)

        # Write some events
        for i in range(10):
            writer.write_event(
                {
                    "doc_type": "game_tick",
                    "game_id": "test_game",
                    "tick": i,
                    "price": 1.0 + i * 0.1,
                }
            )

        writer.write_event(
            {
                "doc_type": "player_action",
                "game_id": "test_game",
                "action": "sidebet",
                "amount": 0.01,
            }
        )

        writer.flush()

        # Read back
        reader = ParquetEventReader(tmpdir)
        ticks = reader.read_all("game_tick")
        print(f"Read {len(ticks)} game_tick events")

        actions = reader.read_all("player_action")
        print(f"Read {len(actions)} player_action events")
