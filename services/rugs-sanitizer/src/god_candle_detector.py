"""
God candle change-detection.

The rugs.fun platform re-reports stale god candle data on every transition tick
for the rest of the UTC day after a god candle occurs. This detector tracks
previously seen god candle game IDs and only flags a NEW god candle when an
unseen game ID appears in the daily records.

See: Root Cause Analysis in the god candle false-positive investigation.
"""

from __future__ import annotations

import logging

from .models import DailyRecords

logger = logging.getLogger(__name__)


class GodCandleDetector:
    """Stateful god candle change-detection.

    Tracks the set of god candle game IDs seen so far. Returns True from
    ``check()`` only when a new god candle game ID appears that was not
    previously reported.
    """

    def __init__(self) -> None:
        self._seen_game_ids: set[str] = set()
        self._new_detections: int = 0

    def check(self, daily: DailyRecords | None) -> bool:
        """Check if the daily records contain a NEW god candle.

        Args:
            daily: Parsed DailyRecords from a transition tick, or None.

        Returns:
            True only if a god candle game ID is present that has not been
            seen before. False for stale/repeated data or None input.
        """
        if daily is None or not daily.has_god_candle:
            return False

        current_ids = daily.god_candle_game_ids
        new_ids = current_ids - self._seen_game_ids

        if not new_ids:
            return False

        # New god candle(s) detected — record and flag
        self._seen_game_ids |= new_ids
        self._new_detections += 1
        for gid in new_ids:
            logger.info(f"NEW god candle detected: game_id={gid}")
        return True

    def get_stats(self) -> dict:
        """Return detector statistics."""
        return {
            "new_detections": self._new_detections,
            "tracked_game_ids": len(self._seen_game_ids),
        }
