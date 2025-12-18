"""
Parquet Writer - Buffered atomic writes with partitioning

Phase 12B, Issue #25

Features:
- Buffered writes (configurable buffer_size, default 100)
- Time-based auto-flush (configurable flush_interval, default 5s)
- Partition by doc_type and date
- Atomic writes (write to temp, rename)
- Thread-safe operations
"""

import logging
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from services.event_store.paths import EventStorePaths
from services.event_store.schema import EventEnvelope

logger = logging.getLogger(__name__)


class ParquetWriter:
    """
    Buffered Parquet writer with automatic flushing and partitioning.

    Events are accumulated in memory and written to Parquet files when:
    - Buffer reaches buffer_size threshold
    - flush_interval seconds have passed since last flush
    - flush() is called manually
    - close() is called

    Files are partitioned by:
    - doc_type (first level): doc_type=ws_event, doc_type=game_tick, etc.
    - date (second level): date=2025-12-17

    Thread-safe for concurrent writes.
    """

    def __init__(
        self,
        paths: EventStorePaths,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
    ):
        """
        Initialize ParquetWriter.

        Args:
            paths: EventStorePaths instance for directory management
            buffer_size: Number of events to buffer before auto-flush
            flush_interval: Seconds between time-based auto-flushes
        """
        self._paths = paths
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval

        # Buffer organized by (doc_type, date) for partitioning
        self._buffers: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self._buffer_count = 0

        # Timing for interval-based flush
        self._last_flush_time = time.time()

        # Thread safety
        self._lock = threading.RLock()
        self._closed = False

        # Ensure directories exist
        paths.ensure_directories()

        logger.debug(
            f"ParquetWriter initialized: buffer_size={buffer_size}, "
            f"flush_interval={flush_interval}s"
        )

    @property
    def buffer_size(self) -> int:
        """Configured buffer size threshold"""
        return self._buffer_size

    @property
    def flush_interval(self) -> float:
        """Configured flush interval in seconds"""
        return self._flush_interval

    @property
    def buffer_count(self) -> int:
        """Current number of buffered events"""
        with self._lock:
            return self._buffer_count

    def write(self, event: EventEnvelope) -> None:
        """
        Write event to buffer.

        Event is buffered and will be written to Parquet when:
        - Buffer reaches buffer_size
        - flush_interval has passed
        - flush() or close() is called

        Args:
            event: EventEnvelope to write

        Raises:
            RuntimeError: If writer has been closed
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("Cannot write to closed ParquetWriter")

            # Check if time-based flush needed before adding event
            if self._should_time_flush():
                self._do_flush()

            # Get partition key
            doc_type = event.doc_type.value
            date_str = event.ts.strftime("%Y-%m-%d")
            partition_key = (doc_type, date_str)

            # Add to buffer
            self._buffers[partition_key].append(event.to_dict())
            self._buffer_count += 1

            logger.debug(
                f"Buffered event: doc_type={doc_type}, seq={event.seq}, "
                f"buffer_count={self._buffer_count}"
            )

            # Check if size-based flush needed
            if self._buffer_count >= self._buffer_size:
                self._do_flush()

    def flush(self) -> list[Path] | None:
        """
        Flush all buffered events to Parquet files.

        Returns:
            List of written file paths, or None if buffer was empty
        """
        with self._lock:
            if self._closed:
                return None
            return self._do_flush()

    def _should_time_flush(self) -> bool:
        """Check if time-based flush is needed"""
        if self._buffer_count == 0:
            return False
        elapsed = time.time() - self._last_flush_time
        return elapsed >= self._flush_interval

    def _do_flush(self) -> list[Path] | None:
        """
        Internal flush implementation (must be called with lock held).

        Returns:
            List of written file paths, or None if buffer was empty
        """
        if self._buffer_count == 0:
            return None

        written_paths: list[Path] = []

        for (doc_type, date_str), events in self._buffers.items():
            if not events:
                continue

            path = self._write_partition(doc_type, date_str, events)
            if path:
                written_paths.append(path)
                logger.info(f"Wrote {len(events)} events to {path}")

        # Clear buffers
        self._buffers.clear()
        self._buffer_count = 0
        self._last_flush_time = time.time()

        return written_paths if written_paths else None

    def _write_partition(
        self, doc_type: str, date_str: str, events: list[dict[str, Any]]
    ) -> Path | None:
        """
        Write events to a partition directory.

        Uses atomic write pattern: write to temp file, then rename.

        Args:
            doc_type: Document type (partition key)
            date_str: Date string (partition key)
            events: List of event dicts to write

        Returns:
            Path to written file, or None on failure
        """
        if not events:
            return None

        # Get partition directory
        partition_dir = self._paths.parquet_partition_dir(doc_type, date_str)
        partition_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}.parquet"
        final_path = partition_dir / filename

        # Write to temp file first (atomic write pattern)
        temp_path = partition_dir / f".{filename}.tmp"

        try:
            # Create PyArrow table from events
            table = self._events_to_table(events)

            # Write to temp file
            pq.write_table(table, temp_path)

            # Atomic rename
            temp_path.rename(final_path)

            return final_path

        except Exception as e:
            logger.error(f"Failed to write Parquet: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise

    def _events_to_table(self, events: list[dict[str, Any]]) -> pa.Table:
        """
        Convert list of event dicts to PyArrow Table.

        Args:
            events: List of event dicts (from EventEnvelope.to_dict())

        Returns:
            PyArrow Table
        """
        # Define schema with all fields
        schema = pa.schema(
            [
                ("ts", pa.string()),
                ("source", pa.string()),
                ("doc_type", pa.string()),
                ("session_id", pa.string()),
                ("seq", pa.int64()),
                ("direction", pa.string()),
                ("raw_json", pa.string()),
                ("game_id", pa.string()),
                ("player_id", pa.string()),
                ("username", pa.string()),
                ("event_name", pa.string()),
                ("price", pa.string()),  # Decimal stored as string
                ("tick", pa.int64()),
                ("action_type", pa.string()),
                ("cash", pa.string()),  # Decimal stored as string
                ("position_qty", pa.string()),  # Decimal stored as string
            ]
        )

        # Build arrays for each column
        arrays = {}
        for field in schema:
            field_name = field.name
            values = [e.get(field_name) for e in events]

            if field.type == pa.int64():
                # Handle nullable integers
                arrays[field_name] = pa.array(values, type=pa.int64())
            else:
                arrays[field_name] = pa.array(values, type=pa.string())

        return pa.Table.from_pydict(arrays, schema=schema)

    def close(self) -> None:
        """
        Close the writer, flushing any remaining buffered events.

        Safe to call multiple times.
        """
        with self._lock:
            if self._closed:
                return

            # Flush remaining events
            if self._buffer_count > 0:
                try:
                    self._do_flush()
                except Exception as e:
                    logger.error(f"Error flushing on close: {e}")

            self._closed = True
            logger.debug("ParquetWriter closed")

    def __enter__(self) -> "ParquetWriter":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures flush on exit"""
        self.close()
