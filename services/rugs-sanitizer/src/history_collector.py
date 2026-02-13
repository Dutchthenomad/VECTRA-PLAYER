"""
Smart gameHistory collection strategy.

Rosetta Stone Section 1.10: The rolling window contains exactly 10 games
and shifts by 1 on each completion. Capturing every 10th rug yields zero
overlap. God candle events trigger immediate capture regardless of counter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .models import GameHistoryRecord

logger = logging.getLogger(__name__)


@dataclass
class CollectorStats:
    """Statistics for the history collector."""

    rugs_seen: int = 0
    collections_triggered: int = 0
    records_collected: int = 0
    god_candle_captures: int = 0
    duplicates_skipped: int = 0


class HistoryCollector:
    """Smart gameHistory collection.

    Strategy:
    - Count rugged games
    - Capture gameHistory every N-th rug (default: 10) for zero overlap
    - God candle events trigger immediate capture regardless of counter
    - Dedup by gameId as redundant safety net
    """

    def __init__(self, collection_interval: int = 10) -> None:
        self._interval = collection_interval
        self._stats = CollectorStats()
        self._captured_ids: set[str] = set()
        self._max_tracked_ids = 1000

    @property
    def rug_count(self) -> int:
        return self._stats.rugs_seen

    @property
    def next_collection_in(self) -> int:
        """Number of rugs until next scheduled collection."""
        return self._interval - (self._stats.rugs_seen % self._interval)

    def on_rug(
        self,
        game_history_raw: list[dict] | None,
        has_god_candle: bool = False,
    ) -> list[GameHistoryRecord]:
        """Called when a rug is detected. Returns collected records (may be empty).

        Args:
            game_history_raw: Raw gameHistory array from the event, or None if not present.
            has_god_candle: Whether a god candle was detected in this event.

        Returns:
            List of GameHistoryRecord if collection was triggered, empty list otherwise.
        """
        self._stats.rugs_seen += 1

        should_collect = False

        # Regular interval collection
        if self._stats.rugs_seen % self._interval == 0:
            should_collect = True

        # God candle override: ALWAYS collect
        if has_god_candle:
            should_collect = True
            self._stats.god_candle_captures += 1
            logger.info("HIGH PRIORITY: God candle detected — forcing collection")

        if not should_collect:
            return []

        if not game_history_raw:
            logger.warning("Collection triggered but no gameHistory data present")
            return []

        return self._collect(game_history_raw)

    def _collect(self, game_history_raw: list[dict]) -> list[GameHistoryRecord]:
        """Parse and deduplicate game history entries."""
        self._stats.collections_triggered += 1
        records: list[GameHistoryRecord] = []

        for entry_raw in game_history_raw:
            game_id = entry_raw.get("id", "")
            if not game_id:
                continue

            # Dedup safety net
            if game_id in self._captured_ids:
                self._stats.duplicates_skipped += 1
                continue

            self._captured_ids.add(game_id)

            # Memory management
            if len(self._captured_ids) > self._max_tracked_ids:
                # Remove oldest
                oldest = next(iter(self._captured_ids))
                self._captured_ids.discard(oldest)

            record = GameHistoryRecord.from_raw(entry_raw)
            records.append(record)
            self._stats.records_collected += 1

        if records:
            logger.info(
                f"Collected {len(records)} records "
                f"(rug #{self._stats.rugs_seen}, "
                f"total: {self._stats.records_collected})"
            )

        return records

    def get_stats(self) -> dict:
        """Return collector statistics."""
        return {
            "rugs_seen": self._stats.rugs_seen,
            "collections_triggered": self._stats.collections_triggered,
            "records_collected": self._stats.records_collected,
            "god_candle_captures": self._stats.god_candle_captures,
            "duplicates_skipped": self._stats.duplicates_skipped,
            "next_collection_in": self.next_collection_in,
            "collection_interval": self._interval,
            "tracked_ids": len(self._captured_ids),
        }
