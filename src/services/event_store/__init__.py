"""
Event Store Module - Phase 12 Unified Data Architecture

Single writer for all persistence:
- Parquet dataset (DuckDB query layer)
- LanceDB vector index (derived)

All producers publish to EventBus; EventStore subscribes and persists.
"""

from .paths import EventStorePaths
from .schema import DocType, EventEnvelope

__all__ = [
    "DocType",
    "EventEnvelope",
    "EventStorePaths",
]
