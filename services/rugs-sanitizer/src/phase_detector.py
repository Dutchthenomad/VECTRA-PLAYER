"""
Game phase detection state machine.

Implements the Rosetta Stone v0.2.0 phase detection priority order.
Tracks game transitions to detect the two-broadcast rug mechanism
and seed reveals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .models import Phase

logger = logging.getLogger(__name__)


@dataclass
class GameTransition:
    """Describes a phase transition between two events."""

    previous_phase: Phase
    new_phase: Phase
    previous_game_id: str
    new_game_id: str
    is_new_game: bool = False
    is_seed_reveal: bool = False


@dataclass
class PhaseDetectorState:
    """Internal state tracked across events."""

    current_phase: Phase = Phase.UNKNOWN
    current_game_id: str = ""
    previous_phase: Phase = Phase.UNKNOWN
    previous_game_id: str = ""
    rug_count: int = 0
    games_seen: int = 0


class PhaseDetector:
    """Stateful game phase detector.

    Detects phase from gameStateUpdate fields using the Rosetta Stone
    priority order, and tracks game-to-game transitions including
    the two-broadcast rug mechanism.
    """

    def __init__(self) -> None:
        self._state = PhaseDetectorState()

    @property
    def current_phase(self) -> Phase:
        return self._state.current_phase

    @property
    def current_game_id(self) -> str:
        return self._state.current_game_id

    @property
    def rug_count(self) -> int:
        return self._state.rug_count

    @property
    def games_seen(self) -> int:
        return self._state.games_seen

    def detect(self, data: dict) -> Phase:
        """Detect phase from a gameStateUpdate event's data payload.

        Priority order (Rosetta Stone Section 1.2):
        1. active=True AND rugged=False -> ACTIVE
        2. rugged=True -> RUGGED
        3. cooldownTimer > 0 + allowPreRoundBuys -> PRESALE
        4. cooldownTimer > 0 -> COOLDOWN
        5. allowPreRoundBuys=True (near-zero timer) -> PRESALE
        6. Otherwise -> UNKNOWN
        """
        active = data.get("active", False)
        rugged = data.get("rugged", False)
        timer = data.get("cooldownTimer", 0)
        allow_buys = data.get("allowPreRoundBuys", False)

        if active and not rugged:
            return Phase.ACTIVE
        if rugged:
            return Phase.RUGGED
        if timer > 0:
            if allow_buys:
                return Phase.PRESALE
            return Phase.COOLDOWN
        if allow_buys:
            return Phase.PRESALE
        return Phase.UNKNOWN

    def process(self, data: dict) -> GameTransition | None:
        """Process a gameStateUpdate event, returning transition info if phase changed.

        Returns None if phase and game did not change.
        Returns GameTransition when:
        - Phase changed (e.g., ACTIVE -> RUGGED)
        - Game ID changed (new game started)
        """
        new_phase = self.detect(data)
        new_game_id = data.get("gameId", "")

        # Check if anything changed
        phase_changed = new_phase != self._state.current_phase
        game_changed = (
            new_game_id != self._state.current_game_id
            and self._state.current_game_id != ""
            and new_game_id != ""
        )

        transition = None

        if phase_changed or game_changed:
            is_seed_reveal = False
            is_new_game = False

            # Detect the two-broadcast rug mechanism:
            # First broadcast: same game, phase -> RUGGED, serverSeed revealed
            # Second broadcast: NEW game ID, phase -> COOLDOWN, new serverSeedHash
            if new_phase == Phase.RUGGED and not game_changed:
                self._state.rug_count += 1
                provably_fair = data.get("provablyFair", {})
                if provably_fair.get("serverSeed"):
                    is_seed_reveal = True

            if game_changed:
                is_new_game = True
                self._state.games_seen += 1

            transition = GameTransition(
                previous_phase=self._state.current_phase,
                new_phase=new_phase,
                previous_game_id=self._state.current_game_id,
                new_game_id=new_game_id,
                is_new_game=is_new_game,
                is_seed_reveal=is_seed_reveal,
            )

            if is_seed_reveal:
                logger.info(f"Seed reveal: game={self._state.current_game_id}")
            if is_new_game:
                logger.info(f"New game: {new_game_id} (prev={self._state.current_game_id})")

        # Update state
        self._state.previous_phase = self._state.current_phase
        self._state.previous_game_id = self._state.current_game_id
        self._state.current_phase = new_phase
        self._state.current_game_id = new_game_id

        return transition

    def get_stats(self) -> dict:
        """Return detector statistics."""
        return {
            "current_phase": self._state.current_phase.value,
            "current_game_id": self._state.current_game_id,
            "rug_count": self._state.rug_count,
            "games_seen": self._state.games_seen,
        }
