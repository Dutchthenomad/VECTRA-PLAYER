"""
OptimizationSubscriber - Processes game events for statistical analysis.

This module follows VECTRA-BOILERPLATE MODULE-EXTENSION-SPEC v1.0.0

Strategy:
- Listen for game.tick events with rugged=True
- Collect completed games from gameHistory
- Run statistical analysis and generate strategy profiles
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .profiles.models import StrategyProfile
from .profiles.producer import ProfileProducer

logger = logging.getLogger(__name__)


@dataclass
class OptimizationStats:
    """Statistics for optimization service."""

    games_collected: int = 0
    profiles_generated: int = 0
    last_profile_time: datetime | None = None
    session_start: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "games_collected": self.games_collected,
            "profiles_generated": self.profiles_generated,
            "last_profile_time": (
                self.last_profile_time.isoformat() if self.last_profile_time else None
            ),
            "session_start": self.session_start.isoformat(),
        }


class OptimizationSubscriber:
    """
    Subscriber that processes game events for statistical optimization.

    On each RUG event (rugged=True), collects game data and periodically
    generates strategy profiles using survival analysis, Bayesian signals,
    Kelly criterion, and Monte Carlo simulation.

    Consumed events:
        - game.tick: Watches for rugged=True to collect games
        - player.state: Tracks balance for position sizing
    """

    def __init__(
        self,
        client: Any,
        producer: ProfileProducer | None = None,
        min_games_for_profile: int = 50,
    ):
        """
        Initialize optimization subscriber.

        Args:
            client: Client instance for receiving events
            producer: ProfileProducer instance (created if None)
            min_games_for_profile: Minimum games before generating profile
        """
        self._client = client
        self._producer = producer or ProfileProducer()
        self._min_games = min_games_for_profile
        self._collected_games: list[dict] = []
        self._current_profile: StrategyProfile | None = None
        self._stats = OptimizationStats()
        self._connected = False
        self._current_balance = 0.0

        # Register event handlers with client
        if hasattr(client, "on"):
            client.on("game.tick", self.on_game_tick)
            client.on("player.state", self.on_player_state)
            client.on("connection", self.on_connection_change)

        logger.info("OptimizationSubscriber initialized")

    @property
    def stats(self) -> OptimizationStats:
        """Get current statistics."""
        return self._stats

    @property
    def current_profile(self) -> StrategyProfile | None:
        """Get current active profile."""
        return self._current_profile

    def on_game_tick(self, event: Any) -> None:
        """
        Handle game.tick event.

        Collects completed games from gameHistory when rugged=True.
        """
        if getattr(event, "rugged", False) and getattr(event, "game_history", None):
            self._collect_games(event.game_history)

    def on_player_state(self, event: Any) -> None:
        """
        Handle player.state event.

        Tracks current balance for position sizing calculations.
        """
        self._current_balance = getattr(event, "cash", 0.0)

    def on_connection_change(self, connected: bool) -> None:
        """
        Handle connection state change.
        """
        self._connected = connected
        if connected:
            logger.info("Connected to Foundation Service")
        else:
            logger.warning("Disconnected from Foundation Service")

    def _collect_games(self, game_history: list) -> None:
        """
        Collect games from gameHistory array.

        Args:
            game_history: List of game dicts from server
        """
        for game in game_history:
            game_id = game.get("id") or game.get("gameId") or game.get("game_id")
            if not game_id:
                continue

            # Check for duplicate
            if any(g.get("id") == game_id for g in self._collected_games):
                continue

            # Normalize and store
            normalized = {
                "id": game_id,
                "duration": (game.get("duration") or game.get("ticks") or game.get("length")),
                "peak": game.get("peak") or game.get("peakMultiplier"),
                "collected_at": datetime.utcnow().isoformat(),
            }
            self._collected_games.append(normalized)
            self._stats.games_collected += 1

        # Check if we should generate a new profile
        if len(self._collected_games) >= self._min_games:
            self._maybe_generate_profile()

    def _maybe_generate_profile(self) -> None:
        """Generate new profile if enough games collected."""
        logger.info(f"Generating profile from {len(self._collected_games)} games")

        try:
            self._current_profile = self._producer.generate_profile(self._collected_games)
            self._stats.profiles_generated += 1
            self._stats.last_profile_time = datetime.utcnow()

            logger.info(f"Generated profile: {self._current_profile.profile_id}")
        except Exception as e:
            logger.error(f"Failed to generate profile: {e}")

    def force_generate_profile(self) -> StrategyProfile | None:
        """Force profile generation with current games."""
        if not self._collected_games:
            logger.warning("No games collected, cannot generate profile")
            return None

        self._maybe_generate_profile()
        return self._current_profile

    def get_collected_games(self) -> list[dict]:
        """Get list of collected games."""
        return self._collected_games.copy()
