"""
Deduplication Tracker - Tracks seen gameIds to prevent duplicate storage.

Uses an in-memory set backed by periodic persistence to disk.
"""

import json
import logging
import threading
from collections import OrderedDict
from pathlib import Path

logger = logging.getLogger(__name__)


class DeduplicationTracker:
    """
    Tracks seen gameIds to prevent duplicate game storage.

    Uses an LRU cache to limit memory usage while maintaining
    deduplication accuracy for recent games.

    Persistence:
        - Writes seen IDs to disk periodically
        - Loads on startup to survive restarts
    """

    def __init__(
        self,
        persist_path: Path | str | None = None,
        max_cache_size: int = 10000,
    ):
        """
        Initialize deduplication tracker.

        Args:
            persist_path: Path to JSON file for persistence (optional)
            max_cache_size: Maximum number of gameIds to track in memory
        """
        self._persist_path = Path(persist_path) if persist_path else None
        self._max_cache_size = max_cache_size
        self._lock = threading.Lock()

        # OrderedDict for LRU behavior
        self._seen: OrderedDict[str, bool] = OrderedDict()
        self._dirty = False

        # Load persisted state
        if self._persist_path and self._persist_path.exists():
            self._load()

    def is_duplicate(self, game_id: str) -> bool:
        """
        Check if a gameId has already been seen.

        Args:
            game_id: The game ID to check

        Returns:
            True if the game has been seen before
        """
        with self._lock:
            return game_id in self._seen

    def mark_seen(self, game_id: str) -> None:
        """
        Mark a gameId as seen.

        Args:
            game_id: The game ID to mark
        """
        with self._lock:
            # Move to end if exists (LRU refresh)
            if game_id in self._seen:
                self._seen.move_to_end(game_id)
            else:
                self._seen[game_id] = True

                # Enforce max cache size (LRU eviction)
                while len(self._seen) > self._max_cache_size:
                    self._seen.popitem(last=False)

            self._dirty = True

    def get_seen_count(self) -> int:
        """Get the number of tracked gameIds."""
        with self._lock:
            return len(self._seen)

    def persist(self) -> bool:
        """
        Persist seen gameIds to disk.

        Returns:
            True if persistence succeeded
        """
        if not self._persist_path:
            return False

        with self._lock:
            if not self._dirty:
                return True

            try:
                # Ensure directory exists
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)

                # Write atomically via temp file
                temp_path = self._persist_path.with_suffix(".tmp")
                with open(temp_path, "w") as f:
                    json.dump(list(self._seen.keys()), f)

                temp_path.replace(self._persist_path)
                self._dirty = False

                logger.debug(f"Persisted {len(self._seen)} gameIds to {self._persist_path}")
                return True

            except Exception as e:
                logger.error(f"Failed to persist dedup state: {e}")
                return False

    def _load(self) -> None:
        """Load persisted state from disk."""
        try:
            with open(self._persist_path) as f:
                game_ids = json.load(f)

            # Rebuild OrderedDict (respecting max size)
            for game_id in game_ids[-self._max_cache_size :]:
                self._seen[game_id] = True

            logger.info(f"Loaded {len(self._seen)} gameIds from persistence")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse dedup file: {e}")
        except Exception as e:
            logger.error(f"Failed to load dedup state: {e}")

    def clear(self) -> None:
        """Clear all tracked gameIds."""
        with self._lock:
            self._seen.clear()
            self._dirty = True
