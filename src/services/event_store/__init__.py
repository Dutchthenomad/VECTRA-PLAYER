"""
Event Store Module - Phase 12 Unified Data Architecture

Single writer for all persistence:
- Parquet dataset (DuckDB query layer)
- VectorDB (ChromaDB) index (derived, external)

All producers publish to EventBus; EventStore subscribes and persists.
"""

from .duckdb import EventStoreQuery
from .paths import (
    EventStorePaths,
    get_data_dir,
    get_legacy_recordings_dir,
    get_raw_captures_dir,
)
from .schema import Direction, DocType, EventEnvelope, EventSource
from .service import EventStoreService
from .writer import ParquetWriter

__all__ = [
    "Direction",
    "DocType",
    "EventEnvelope",
    "EventSource",
    "EventStorePaths",
    "EventStoreQuery",
    "EventStoreService",
    "ParquetWriter",
    # Convenience path functions
    "get_data_dir",
    "get_legacy_recordings_dir",
    "get_raw_captures_dir",
]
