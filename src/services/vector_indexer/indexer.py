"""Vector indexer: Parquet -> ChromaDB.

This module reads the canonical Parquet dataset and builds a derived
vector index for semantic search. The index is rebuildable from Parquet
at any time.

Architecture:
    EventStore -> Parquet (canonical truth)
                      |
               VectorIndexer
                      |
                  ChromaDB (derived, rebuildable)
"""

import json
import logging
import os
import sys
from pathlib import Path

# Lazy import claude-flow modules to avoid import errors in tests
store = None
embed_batch = None

logger = logging.getLogger(__name__)


def _ensure_claude_flow_imports():
    """Lazy load claude-flow imports.

    AUDIT FIX: sys.path mutation moved here (deferred until actually needed)
    instead of at module import time.
    """
    global store, embed_batch
    if store is None:
        # Add claude-flow RAG pipeline to path (configurable via env var)
        # CRITICAL: This is a development-time dependency on claude-flow
        # Production deployments should package RAG pipeline as a proper dependency
        _CLAUDE_FLOW_RAG = Path(
            os.environ.get("CLAUDE_FLOW_RAG_PATH", str(Path.home() / "Desktop/claude-flow/rag-pipeline"))
        )

        if not _CLAUDE_FLOW_RAG.exists():
            logger.warning(
                f"claude-flow RAG pipeline not found at {_CLAUDE_FLOW_RAG}. "
                f"Set CLAUDE_FLOW_RAG_PATH env var or ensure claude-flow is installed."
            )
            raise ImportError(f"claude-flow RAG pipeline not found at {_CLAUDE_FLOW_RAG}")

        if str(_CLAUDE_FLOW_RAG) not in sys.path:
            sys.path.insert(0, str(_CLAUDE_FLOW_RAG))
            logger.debug(f"Added claude-flow RAG to sys.path: {_CLAUDE_FLOW_RAG}")

        from embeddings.embedder import embed_batch as _embed_batch
        from storage import store as _store

        store = _store
        embed_batch = _embed_batch


class VectorIndexer:
    """Indexes events from Parquet into ChromaDB.

    This reads the canonical Parquet dataset and builds a derived
    vector index for semantic search.

    Attributes:
        data_dir: Path to data directory (contains events_parquet/)
        collection_name: ChromaDB collection name
    """

    def __init__(
        self,
        data_dir: Path,
        collection_name: str = "rugs_events",
    ):
        """Initialize indexer.

        Args:
            data_dir: Path to data directory containing events_parquet/
            collection_name: ChromaDB collection name
        """
        self.data_dir = Path(data_dir)
        self.collection_name = collection_name
        self.checkpoint_file = self.data_dir / "manifests" / "vector_index_checkpoint.json"

    def read_checkpoint(self) -> dict:
        """Read indexer checkpoint.

        Returns:
            Checkpoint dict with last_indexed_ts, embedding_model, schema_version
        """
        if not self.checkpoint_file.exists():
            return {
                "last_indexed_ts": "1970-01-01T00:00:00Z",
                "embedding_model": "all-MiniLM-L6-v2",
                "schema_version": "1.0.0",
            }

        return json.loads(self.checkpoint_file.read_text())

    def write_checkpoint(self, checkpoint: dict):
        """Write indexer checkpoint.

        Args:
            checkpoint: Checkpoint dict to persist
        """
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file.write_text(json.dumps(checkpoint, indent=2))

    def read_new_events(self, since: str) -> list[dict]:
        """Read events from Parquet since checkpoint.

        Args:
            since: ISO timestamp to read from

        Returns:
            List of event records
        """
        try:
            import duckdb
        except ImportError:
            logger.warning("duckdb not installed, returning empty events")
            return []

        parquet_dir = self.data_dir / "events_parquet"
        if not parquet_dir.exists():
            return []

        # Query all parquet files with DuckDB
        parquet_pattern = str(parquet_dir / "**" / "*.parquet")

        # Check if any parquet files exist
        parquet_files = list(parquet_dir.rglob("*.parquet"))
        if not parquet_files:
            return []

        query = f"""
            SELECT * FROM read_parquet('{parquet_pattern}')
            WHERE ts > '{since}'
            ORDER BY ts ASC
        """

        try:
            conn = duckdb.connect()
            df = conn.execute(query).df()
            return df.to_dict("records")
        except Exception as e:
            logger.warning(f"DuckDB query failed: {e}")
            return []

    def build_incremental(self, batch_size: int = 1000) -> dict:
        """Incrementally index new events.

        Args:
            batch_size: Number of events to process per batch

        Returns:
            Stats dict with new_events, chunks_added, latest_ts
        """
        from services.vector_indexer.chunker import chunk_event

        _ensure_claude_flow_imports()

        # Read checkpoint
        checkpoint = self.read_checkpoint()
        since = checkpoint["last_indexed_ts"]

        logger.info(f"Reading events since {since}...")
        events = self.read_new_events(since=since)

        if not events:
            logger.info("No new events to index")
            return {"new_events": 0, "chunks_added": 0}

        logger.info(f"Found {len(events)} new events")

        # Process in batches
        total_chunks = 0
        latest_ts = since

        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]

            # Chunk events
            chunks = [chunk_event(event) for event in batch]

            # Generate embeddings
            texts = [c["text"] for c in chunks]
            embeddings = embed_batch(texts, show_progress=False)

            # Add to ChromaDB
            added = store.add_documents(chunks, embeddings)
            total_chunks += added

            # Track latest timestamp
            latest_ts = max(latest_ts, str(batch[-1].get("ts", since)))

            logger.info(f"  Processed batch {i // batch_size + 1}: {added} chunks")

        # Update checkpoint
        checkpoint["last_indexed_ts"] = latest_ts
        self.write_checkpoint(checkpoint)

        return {
            "new_events": len(events),
            "chunks_added": total_chunks,
            "latest_ts": latest_ts,
        }

    def build_full(self, batch_size: int = 1000) -> dict:
        """Rebuild entire index from scratch.

        Args:
            batch_size: Number of events to process per batch

        Returns:
            Stats dict with new_events, chunks_added, latest_ts
        """
        _ensure_claude_flow_imports()

        logger.info("Clearing existing index...")
        store.clear()

        # Reset checkpoint to epoch
        checkpoint = self.read_checkpoint()
        checkpoint["last_indexed_ts"] = "1970-01-01T00:00:00Z"
        self.write_checkpoint(checkpoint)

        # Run incremental (which will now process everything)
        return self.build_incremental(batch_size=batch_size)


def get_indexer(data_dir: Path = None) -> VectorIndexer:
    """Get default indexer instance.

    Args:
        data_dir: Optional data directory override

    Returns:
        VectorIndexer instance
    """
    if data_dir is None:
        import os

        data_dir = Path(os.getenv("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))

    return VectorIndexer(data_dir=data_dir)
