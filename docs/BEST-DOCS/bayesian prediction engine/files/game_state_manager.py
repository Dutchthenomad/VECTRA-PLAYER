"""
Game State Manager - Tracks game lifecycle and triggers predictions.

Integrates with rugs.fun WebSocket feed to:
1. Detect game transitions (new game, rug, cooldown)
2. Track peak price during active phase
3. Extract final price and duration at rug
4. Trigger Bayesian predictions at game start
5. Record outcomes for training
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


class GamePhase(Enum):
    UNKNOWN = "unknown"
    COOLDOWN = "cooldown"
    PRESALE = "presale"
    ACTIVE = "active"
    RUGGED = "rugged"


@dataclass
class CompletedGame:
    """Record of a completed game"""

    game_id: str
    peak: float
    final_price: float
    duration: int  # ticks
    server_seed: str
    server_seed_hash: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ActiveGame:
    """State of the currently running game"""

    game_id: str
    server_seed_hash: str
    start_time: datetime
    current_tick: int = 0
    current_price: float = 1.0
    peak: float = 1.0
    phase: GamePhase = GamePhase.ACTIVE


class GameStateManager:
    """
    Manages game state from WebSocket events.

    Usage:
        manager = GameStateManager()
        manager.on_game_start = lambda game_id: print(f"New game: {game_id}")
        manager.on_game_end = lambda game: print(f"Game ended: {game.peak}x")

        # Feed WebSocket events
        manager.process_event(event_data)
    """

    def __init__(self):
        # Current state
        self.current_game: ActiveGame | None = None
        self.phase: GamePhase = GamePhase.UNKNOWN
        self.cooldown_timer: int = 0

        # History
        self.completed_games: list[CompletedGame] = []
        self.max_history = 100

        # Callbacks
        self.on_game_start: Callable[[str, str], None] | None = None  # (game_id, seed_hash)
        self.on_game_end: Callable[[CompletedGame], None] | None = None
        self.on_tick: Callable[[int, float, float], None] | None = None  # (tick, price, peak)
        self.on_phase_change: Callable[[GamePhase], None] | None = None
        self.on_history_bootstrap: Callable[[list[CompletedGame]], None] | None = (
            None  # Called with bootstrap games
        )

        # Track last seen game_id to detect transitions
        self._last_game_id: str | None = None
        self._pending_seed_extraction: bool = False
        self._bootstrapped: bool = False  # Track if we've already bootstrapped from history

    def process_event(self, event: dict) -> None:
        """
        Process a game.tick event from WebSocket.

        Expected event structure:
        {
            "type": "game.tick",
            "gameId": "20260117-abc123",
            "data": {
                "tick": 150,
                "price": 2.3456,
                "active": true,
                "rugged": false,
                "cooldownTimer": 0,
                "allowPreRoundBuys": false,
                "gameHistory": [...]
            }
        }
        """
        if event.get("type") != "game.tick":
            return

        game_id = event.get("gameId", "")
        data = event.get("data", {})

        tick = data.get("tick", data.get("tickCount", 0))
        price = data.get("price", 1.0)
        active = data.get("active", False)
        rugged = data.get("rugged", False)
        cooldown_timer = data.get("cooldownTimer", 0)
        allow_presale = data.get("allowPreRoundBuys", False)
        game_history = data.get("gameHistory", [])

        # Detect phase
        new_phase = self._detect_phase(active, rugged, cooldown_timer, allow_presale)

        # Phase change detection
        if new_phase != self.phase:
            old_phase = self.phase
            self.phase = new_phase
            logger.info(f"Phase: {old_phase.value} → {new_phase.value}")
            if self.on_phase_change:
                self.on_phase_change(new_phase)

        self.cooldown_timer = cooldown_timer

        # Bootstrap from gameHistory on first event (skip warmup)
        if not self._bootstrapped and game_history:
            self._bootstrap_from_history(game_history)

        # Handle game transitions
        if game_id and game_id != self._last_game_id:
            self._handle_game_transition(game_id, data, game_history)
            self._last_game_id = game_id

        # Handle active game updates
        if self.current_game and active and not rugged:
            self.current_game.current_tick = tick
            self.current_game.current_price = price
            if price > self.current_game.peak:
                self.current_game.peak = price

            if self.on_tick:
                self.on_tick(tick, price, self.current_game.peak)

        # Handle rug event
        if rugged and self.current_game and not self._pending_seed_extraction:
            self._pending_seed_extraction = True
            # Seed will be extracted from gameHistory on next event

        # Extract seed from gameHistory if pending
        if self._pending_seed_extraction and game_history:
            self._extract_completed_game(game_history, price)

    def _detect_phase(
        self, active: bool, rugged: bool, cooldown_timer: int, allow_presale: bool
    ) -> GamePhase:
        """Determine current game phase from event data"""
        if cooldown_timer > 0:
            if allow_presale:
                return GamePhase.PRESALE
            return GamePhase.COOLDOWN
        if rugged and not active:
            return GamePhase.COOLDOWN
        if allow_presale and not active:
            return GamePhase.PRESALE
        if active and not rugged:
            return GamePhase.ACTIVE
        if rugged:
            return GamePhase.RUGGED
        return GamePhase.UNKNOWN

    def _bootstrap_from_history(self, game_history: list[dict]) -> None:
        """
        Bootstrap from gameHistory in first WebSocket event.

        This allows skipping warmup by loading historical game outcomes.
        The gameHistory array contains recent completed games with their
        provably fair data revealed.
        """
        self._bootstrapped = True

        if not game_history:
            return

        bootstrapped_games: list[CompletedGame] = []

        # Process history in reverse (oldest first) for proper ordering
        for entry in reversed(game_history):
            game_id = entry.get("gameId", "")
            provably_fair = entry.get("provablyFair", {})
            server_seed = provably_fair.get("serverSeed", "")
            server_seed_hash = provably_fair.get("serverSeedHash", "")

            # Skip entries without revealed seeds (incomplete data)
            if not server_seed:
                continue

            # Extract game data
            peak = entry.get("peak", 1.0)
            prices = entry.get("prices", [])
            duration = len(prices) if prices else 0

            # Estimate final price from prices array if available
            final_price = prices[-1] if prices else 0.01

            # Create completed game record
            game_record = CompletedGame(
                game_id=game_id,
                peak=peak,
                final_price=final_price,
                duration=duration,
                server_seed=server_seed,
                server_seed_hash=server_seed_hash,
            )

            bootstrapped_games.append(game_record)
            self.completed_games.append(game_record)

        # Trim history if needed
        while len(self.completed_games) > self.max_history:
            self.completed_games.pop(0)

        if bootstrapped_games:
            logger.info(f"📚 Bootstrapped {len(bootstrapped_games)} games from history")

            # Trigger callback so prediction engine can update forecaster
            if self.on_history_bootstrap:
                self.on_history_bootstrap(bootstrapped_games)

    def _handle_game_transition(
        self, new_game_id: str, data: dict, game_history: list[dict]
    ) -> None:
        """Handle transition to a new game"""
        logger.info(f"New game detected: {new_game_id}")

        # Extract seed hash for new game
        seed_hash = data.get("serverSeedHash", "")

        # Create new active game
        self.current_game = ActiveGame(
            game_id=new_game_id,
            server_seed_hash=seed_hash,
            start_time=datetime.now(),
            current_tick=0,
            current_price=1.0,
            peak=1.0,
            phase=GamePhase.ACTIVE,
        )

        # Trigger callback
        if self.on_game_start:
            self.on_game_start(new_game_id, seed_hash)

    def _extract_completed_game(self, game_history: list[dict], final_price: float) -> None:
        """Extract completed game data from gameHistory"""
        if not game_history or not self.current_game:
            return

        # Find the just-completed game in history
        completed = None
        for entry in game_history:
            if entry.get("gameId") == self.current_game.game_id:
                completed = entry
                break

        if not completed:
            # Might be the first entry if it just completed
            completed = game_history[0] if game_history else None

        if not completed:
            logger.warning("Could not find completed game in history")
            self._pending_seed_extraction = False
            return

        # Extract provably fair data
        provably_fair = completed.get("provablyFair", {})
        server_seed = provably_fair.get("serverSeed", "")
        server_seed_hash = provably_fair.get("serverSeedHash", "")

        if not server_seed:
            # Seed not revealed yet, wait for next event
            return

        # Get peak from history or use tracked value
        peak = completed.get("peak", self.current_game.peak)

        # Get duration from prices array or current tick
        prices = completed.get("prices", [])
        duration = len(prices) if prices else self.current_game.current_tick

        # Create completed game record
        game_record = CompletedGame(
            game_id=self.current_game.game_id,
            peak=peak,
            final_price=final_price,
            duration=duration,
            server_seed=server_seed,
            server_seed_hash=server_seed_hash,
        )

        # Store in history
        self.completed_games.append(game_record)
        if len(self.completed_games) > self.max_history:
            self.completed_games.pop(0)

        logger.info(
            f"Game completed: {game_record.game_id} | "
            f"Peak: {game_record.peak:.4f}x | "
            f"Final: {game_record.final_price:.4f} | "
            f"Duration: {game_record.duration} ticks"
        )

        # Trigger callback
        if self.on_game_end:
            self.on_game_end(game_record)

        self._pending_seed_extraction = False
        self.current_game = None

    def get_previous_game(self) -> CompletedGame | None:
        """Get the most recently completed game"""
        return self.completed_games[-1] if self.completed_games else None

    def get_recent_games(self, n: int = 10) -> list[CompletedGame]:
        """Get the n most recently completed games"""
        return self.completed_games[-n:]

    def get_stats(self) -> dict:
        """Get summary statistics"""
        if not self.completed_games:
            return {"total_games": 0, "avg_peak": 0, "avg_duration": 0, "avg_final": 0}

        games = self.completed_games
        return {
            "total_games": len(games),
            "avg_peak": sum(g.peak for g in games) / len(games),
            "avg_duration": sum(g.duration for g in games) / len(games),
            "avg_final": sum(g.final_price for g in games) / len(games),
        }


if __name__ == "__main__":
    # Test with mock events
    manager = GameStateManager()

    def on_start(game_id, seed_hash):
        print(f"🎮 Game started: {game_id}")

    def on_end(game):
        print(f"💀 Game ended: Peak={game.peak:.2f}x, Duration={game.duration}")

    manager.on_game_start = on_start
    manager.on_game_end = on_end

    # Simulate events
    mock_events = [
        {
            "type": "game.tick",
            "gameId": "20260118-test001",
            "data": {
                "tick": 0,
                "price": 1.0,
                "active": True,
                "rugged": False,
                "cooldownTimer": 0,
                "gameHistory": [],
            },
        },
        {
            "type": "game.tick",
            "gameId": "20260118-test001",
            "data": {
                "tick": 50,
                "price": 1.85,
                "active": True,
                "rugged": False,
                "cooldownTimer": 0,
                "gameHistory": [],
            },
        },
        {
            "type": "game.tick",
            "gameId": "20260118-test001",
            "data": {
                "tick": 100,
                "price": 0.45,
                "active": True,
                "rugged": True,
                "cooldownTimer": 0,
                "gameHistory": [
                    {
                        "gameId": "20260118-test001",
                        "provablyFair": {"serverSeed": "abc123def456", "serverSeedHash": "hash123"},
                        "peak": 1.85,
                        "prices": [1.0] * 100,
                    }
                ],
            },
        },
    ]

    for event in mock_events:
        manager.process_event(event)

    print(f"\nStats: {manager.get_stats()}")
