"""
RecordingSubscriber - Captures game data via gameHistory extraction on RUG events.

This module follows VECTRA-BOILERPLATE MODULE-EXTENSION-SPEC v1.0.0

Strategy:
- Listen for game.tick events with rugged=True
- Extract gameHistory array (10 most recent complete games)
- Deduplicate by gameId to avoid storing duplicates
- Write new games to Parquet storage
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from foundation.client import FoundationClient

# Use relative imports when running as a service
try:
    from foundation.events import GameTickEvent, PlayerStateEvent
    from foundation.subscriber import BaseSubscriber
except ImportError:
    # When running standalone, import from src
    import sys

    sys.path.insert(0, "/home/devops/Desktop/VECTRA-BOILERPLATE/src")
    from foundation.events import GameTickEvent, PlayerStateEvent
    from foundation.subscriber import BaseSubscriber

from .dedup import DeduplicationTracker
from .storage import GameStorage

logger = logging.getLogger(__name__)


@dataclass
class RecordingStats:
    """Statistics for the current recording session."""

    session_games: int = 0
    today_games: int = 0
    total_games: int = 0
    deduped_count: int = 0
    last_rug_multiplier: float | None = None
    last_rug_time: datetime | None = None
    session_start: datetime = field(default_factory=datetime.utcnow)
    is_recording: bool = True

    def to_dict(self) -> dict:
        """Serialize stats to dict."""
        return {
            "session_games": self.session_games,
            "today_games": self.today_games,
            "total_games": self.total_games,
            "deduped_count": self.deduped_count,
            "last_rug_multiplier": self.last_rug_multiplier,
            "last_rug_time": self.last_rug_time.isoformat() if self.last_rug_time else None,
            "session_start": self.session_start.isoformat(),
            "is_recording": self.is_recording,
        }


class RecordingSubscriber(BaseSubscriber):
    """
    Subscriber that captures game data via gameHistory extraction.

    On each RUG event (rugged=True), extracts the gameHistory array and
    stores any new games (deduped by gameId) to Parquet storage.

    Consumed events:
        - game.tick: Watches for rugged=True to trigger extraction
        - player.state: Not used directly (required by BaseSubscriber)
    """

    def __init__(
        self,
        client: "FoundationClient",
        storage: GameStorage,
        dedup_tracker: DeduplicationTracker,
    ):
        """
        Initialize recording subscriber.

        Args:
            client: FoundationClient instance for receiving events
            storage: GameStorage instance for persisting games
            dedup_tracker: DeduplicationTracker for preventing duplicates
        """
        self._storage = storage
        self._dedup = dedup_tracker
        self._stats = RecordingStats()
        self._connected = False

        # Load initial stats from storage
        self._stats.total_games = storage.get_total_game_count()
        self._stats.today_games = storage.get_today_game_count()

        # Initialize base subscriber (registers handlers)
        super().__init__(client)

        logger.info(f"RecordingSubscriber initialized. Total games: {self._stats.total_games}")

    @property
    def stats(self) -> RecordingStats:
        """Get current recording statistics."""
        return self._stats

    @property
    def is_recording(self) -> bool:
        """Check if recording is currently enabled."""
        return self._stats.is_recording

    def start_recording(self) -> bool:
        """
        Start recording.

        Returns:
            True if recording was started, False if already recording
        """
        if self._stats.is_recording:
            return False

        self._stats.is_recording = True
        self._stats.session_start = datetime.utcnow()
        self._stats.session_games = 0
        logger.info("Recording started")
        return True

    def stop_recording(self) -> bool:
        """
        Stop recording.

        Returns:
            True if recording was stopped, False if already stopped
        """
        if not self._stats.is_recording:
            return False

        self._stats.is_recording = False
        logger.info(f"Recording stopped. Session captured {self._stats.session_games} games")
        return True

    def on_game_tick(self, event: GameTickEvent) -> None:
        """
        Handle game.tick event.

        Watches for rugged=True to trigger gameHistory extraction.
        """
        if not self._stats.is_recording:
            return

        # Only process RUG events with gameHistory
        if event.rugged and event.game_history:
            self._extract_new_games(event.game_history, event.price)

    def on_player_state(self, event: PlayerStateEvent) -> None:
        """
        Handle player.state event.

        Not used for recording - required by BaseSubscriber interface.
        """
        # Recording service doesn't need player state
        pass

    def on_connection_change(self, connected: bool) -> None:
        """
        Handle connection state change.

        Logs connection status changes.
        """
        self._connected = connected
        if connected:
            logger.info("Connected to Foundation Service")
        else:
            logger.warning("Disconnected from Foundation Service")

    def _extract_new_games(self, game_history: list, rug_price: float) -> None:
        """
        Extract and store new games from gameHistory array.

        Args:
            game_history: List of complete game data from server
            rug_price: Final price when RUG occurred
        """
        if not game_history:
            return

        new_games = []
        for game in game_history:
            game_id = game.get("id") or game.get("gameId") or game.get("game_id")
            if not game_id:
                logger.warning("Game in history missing gameId, skipping")
                continue

            # Check for duplicate
            if self._dedup.is_duplicate(game_id):
                self._stats.deduped_count += 1
                continue

            # Mark as seen and queue for storage
            self._dedup.mark_seen(game_id)
            new_games.append(game)

        if new_games:
            # Store new games
            stored_count = self._storage.store_games(new_games)

            # Update stats
            self._stats.session_games += stored_count
            self._stats.today_games += stored_count
            self._stats.total_games += stored_count
            self._stats.last_rug_multiplier = rug_price
            self._stats.last_rug_time = datetime.utcnow()

            logger.info(
                f"Stored {stored_count} new games from gameHistory "
                f"(deduped: {len(game_history) - len(new_games)})"
            )

    def get_recent_games(self, limit: int = 10) -> list[dict]:
        """
        Get most recently captured games.

        Args:
            limit: Maximum number of games to return

        Returns:
            List of recent game dicts
        """
        return self._storage.get_recent_games(limit)
