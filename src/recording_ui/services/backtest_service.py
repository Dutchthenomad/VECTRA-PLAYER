"""
Backtest Service - Strategy playback engine for visual backtesting.

Provides:
- Strategy save/load from JSON files
- Game data loading with train/validation split
- Tick-by-tick playback simulation
- Bet placement and resolution logic
"""

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

# Constants
SIDEBET_WINDOW = 40
SIDEBET_COOLDOWN = 5
SIDEBET_PAYOUT = 5  # 5:1
VALIDATION_SPLIT = 0.30  # 30% for validation

# Machine Learning directory for strategies
ML_DIR = Path("/home/devops/Desktop/VECTRA-PLAYER/Machine Learning")
DEFAULT_STRATEGIES_DIR = ML_DIR / "strategies"


@dataclass
class ActiveBet:
    """A bet that has been placed and is waiting for resolution."""

    bet_num: int  # 1-4
    tick_placed: int
    size: float
    entry_price: float  # Price when bet was placed
    window_end: int  # tick_placed + 40
    resolved: bool = False
    won: bool = False


@dataclass
class GameState:
    """State of a single game during playback."""

    game_id: str
    prices: list[float]
    duration: int
    current_tick: int = 0
    phase: str = "waiting"  # waiting, active, rugged


@dataclass
class PlaybackState:
    """Complete state of a playback session."""

    session_id: str
    strategy: dict

    # Game progress
    current_game_idx: int = 0
    total_games: int = 0
    game: GameState | None = None

    # Wallet
    initial_balance: float = 0.1
    wallet: float = 0.1
    peak_balance: float = 0.1

    # Active bets
    active_bets: list[ActiveBet] = field(default_factory=list)

    # Cumulative stats
    wins: int = 0
    losses: int = 0
    early_rugs: int = 0
    games_played: int = 0
    total_wagered: float = 0.0
    max_drawdown: float = 0.0

    # Equity curve
    equity_curve: list[float] = field(default_factory=list)

    # Control
    paused: bool = True
    speed: float = 1.0  # 1x = real-time
    finished: bool = False

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "session_id": self.session_id,
            "strategy_name": self.strategy.get("name", "unnamed"),
            "current_game_idx": self.current_game_idx,
            "total_games": self.total_games,
            "game": {
                "game_id": self.game.game_id if self.game else None,
                "current_tick": self.game.current_tick if self.game else 0,
                "duration": self.game.duration if self.game else 0,
                "price": self.game.prices[self.game.current_tick]
                if self.game and self.game.current_tick < len(self.game.prices)
                else 1.0,
                "current_price": self.game.prices[self.game.current_tick]
                if self.game and self.game.current_tick < len(self.game.prices)
                else 1.0,
                "phase": self.game.phase if self.game else "waiting",
            }
            if self.game
            else None,
            "wallet": round(self.wallet, 6),
            "initial_balance": self.initial_balance,
            "pnl": round(self.wallet - self.initial_balance, 6),
            "pnl_pct": round((self.wallet - self.initial_balance) / self.initial_balance * 100, 2),
            "active_bets": [
                {
                    "bet_num": b.bet_num,
                    "tick_placed": b.tick_placed,
                    "entry_tick": b.tick_placed,  # Alias
                    "entry_price": b.entry_price,
                    "amount": b.size,
                    "size": b.size,  # Alias
                    "window_end": b.window_end,
                    "resolved": b.resolved,
                    "won": b.won,
                }
                for b in self.active_bets
            ],
            "stats": {
                "wins": self.wins,
                "losses": self.losses,
                "early_rugs": self.early_rugs,
                "games_played": self.games_played,
                "win_rate": round(self.wins / self.games_played * 100, 1)
                if self.games_played > 0
                else 0,
                "total_wagered": round(self.total_wagered, 6),
                "max_drawdown": round(self.max_drawdown * 100, 2),
            },
            "equity_curve": [round(e, 6) for e in self.equity_curve[-100:]],  # Last 100 points
            "paused": self.paused,
            "speed": self.speed,
            "finished": self.finished,
        }


class BacktestService:
    """Service for managing backtest playback sessions."""

    def __init__(self, data_dir: str = None, strategies_dir: str = None):
        self.data_dir = Path(
            data_dir or os.environ.get("RUGS_DATA_DIR", os.path.expanduser("~/rugs_data"))
        )
        self.strategies_dir = Path(strategies_dir) if strategies_dir else DEFAULT_STRATEGIES_DIR
        self.strategies_dir.mkdir(parents=True, exist_ok=True)

        # Active sessions
        self.sessions: dict[str, PlaybackState] = {}

        # Cached game data
        self._games_cache: pd.DataFrame | None = None
        self._validation_games: list[dict] | None = None

    # =========================================================================
    # STRATEGY MANAGEMENT
    # =========================================================================

    def list_strategies(self) -> list[dict]:
        """List all saved strategies."""
        strategies = []
        for f in self.strategies_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    strategies.append(
                        {
                            "name": data.get("name", f.stem),
                            "created": data.get("created"),
                            "file": f.name,
                        }
                    )
            except Exception:
                continue
        return sorted(strategies, key=lambda x: x.get("created", ""), reverse=True)

    def load_strategy(self, name: str) -> dict | None:
        """Load a strategy by name."""
        path = self.strategies_dir / f"{name}.json"
        if not path.exists():
            return None
        with open(path) as fp:
            return json.load(fp)

    def save_strategy(self, strategy: dict) -> str:
        """Save a strategy. Returns the filename."""
        name = strategy.get("name", f"strategy_{int(time.time())}")
        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_").strip()
        if not safe_name:
            safe_name = f"strategy_{int(time.time())}"

        strategy["name"] = safe_name
        if "created" not in strategy:
            strategy["created"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        path = self.strategies_dir / f"{safe_name}.json"
        with open(path, "w") as fp:
            json.dump(strategy, fp, indent=2)

        return safe_name

    def delete_strategy(self, name: str) -> bool:
        """Delete a strategy by name."""
        path = self.strategies_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # =========================================================================
    # GAME DATA
    # =========================================================================

    def _load_games(self) -> pd.DataFrame:
        """Load all games from parquet."""
        if self._games_cache is not None:
            return self._games_cache

        parquet_path = self.data_dir / "events_parquet" / "doc_type=complete_game"
        if not parquet_path.exists():
            raise FileNotFoundError(f"No game data at {parquet_path}")

        conn = duckdb.connect()
        df = conn.execute(f"""
            SELECT DISTINCT game_id, raw_json
            FROM '{parquet_path}/**/*.parquet'
            WHERE raw_json IS NOT NULL
        """).df()

        # Parse raw_json to extract prices
        games = []
        for _, row in df.iterrows():
            try:
                data = json.loads(row["raw_json"])
                if "prices" in data and len(data["prices"]) > 50:  # Skip very short games
                    games.append(
                        {
                            "game_id": row["game_id"],
                            "prices": data["prices"],
                            "duration": len(data["prices"]),
                        }
                    )
            except Exception:
                continue

        self._games_cache = pd.DataFrame(games)
        return self._games_cache

    def _is_validation_game(self, game_id: str) -> bool:
        """Deterministic split: hash game_id to determine if validation."""
        h = hashlib.md5(game_id.encode()).hexdigest()
        return int(h[:8], 16) / 0xFFFFFFFF < VALIDATION_SPLIT

    def get_validation_games(self) -> list[dict]:
        """Get games in the validation set."""
        if self._validation_games is not None:
            return self._validation_games

        df = self._load_games()
        validation = []
        for _, row in df.iterrows():
            if self._is_validation_game(row["game_id"]):
                validation.append(
                    {
                        "game_id": row["game_id"],
                        "prices": row["prices"],
                        "duration": row["duration"],
                    }
                )

        self._validation_games = validation
        return self._validation_games

    # =========================================================================
    # PLAYBACK SESSION
    # =========================================================================

    def start_playback(self, strategy: dict) -> str:
        """Start a new playback session. Returns session_id."""
        session_id = str(uuid.uuid4())[:8]

        games = self.get_validation_games()
        if not games:
            raise ValueError("No validation games available")

        initial_balance = strategy.get("initial_balance", 0.1)

        state = PlaybackState(
            session_id=session_id,
            strategy=strategy,
            total_games=len(games),
            initial_balance=initial_balance,
            wallet=initial_balance,
            peak_balance=initial_balance,
            equity_curve=[initial_balance],
        )

        # Load first game
        state.game = GameState(
            game_id=games[0]["game_id"],
            prices=games[0]["prices"],
            duration=games[0]["duration"],
            current_tick=0,
            phase="active",
        )

        self.sessions[session_id] = state
        return session_id

    def get_state(self, session_id: str) -> PlaybackState | None:
        """Get current state of a session."""
        return self.sessions.get(session_id)

    def pause(self, session_id: str):
        """Pause playback."""
        if session_id in self.sessions:
            self.sessions[session_id].paused = True

    def resume(self, session_id: str):
        """Resume playback."""
        if session_id in self.sessions:
            self.sessions[session_id].paused = False

    def set_speed(self, session_id: str, speed: float):
        """Set playback speed (1.0 = real-time)."""
        if session_id in self.sessions:
            self.sessions[session_id].speed = max(0.1, min(speed, 100.0))

    def next_game(self, session_id: str):
        """Skip to next game."""
        state = self.sessions.get(session_id)
        if not state:
            return

        # Resolve any active bets as losses
        for bet in state.active_bets:
            if not bet.resolved:
                bet.resolved = True
                bet.won = False
                state.losses += 1

        state.active_bets = []
        self._advance_to_next_game(state)

    def tick(self, session_id: str) -> dict | None:
        """
        Advance one tick. Returns the new state.
        This is the core simulation loop.
        """
        state = self.sessions.get(session_id)
        if not state or not state.game or state.finished:
            return state.to_dict() if state else None

        game = state.game
        strategy = state.strategy.get("params", state.strategy)

        # Get current price
        if game.current_tick >= game.duration:
            # Game is over (rugged)
            self._handle_rug(state)
            return state.to_dict()

        current_price = game.prices[game.current_tick]

        # Check if we should place bets
        entry_tick = strategy.get("entry_tick", 200)
        num_bets = strategy.get("num_bets", 4)

        if game.current_tick >= entry_tick and game.phase == "active":
            self._check_bet_placement(state, strategy)

        # Check for bet resolutions (game rug = win for active bets in window)
        # This happens when we reach the end of prices array

        # Advance tick
        game.current_tick += 1

        # Check if game rugged (reached end of prices)
        if game.current_tick >= game.duration:
            self._handle_rug(state)

        return state.to_dict()

    def _check_bet_placement(self, state: PlaybackState, strategy: dict):
        """Check if we should place a new bet this tick."""
        game = state.game
        if not game:
            return

        entry_tick = strategy.get("entry_tick", 200)
        num_bets = strategy.get("num_bets", 4)

        # Calculate bet windows
        current_tick = game.current_tick

        # Determine which bet number we're on
        for bet_num in range(1, num_bets + 1):
            bet_start = entry_tick + (bet_num - 1) * (SIDEBET_WINDOW + SIDEBET_COOLDOWN)

            # Check if this is the exact tick to place this bet
            if current_tick == bet_start:
                # Check if we already placed this bet
                already_placed = any(b.bet_num == bet_num for b in state.active_bets)
                if already_placed:
                    continue

                # Calculate bet size
                bet_size = self._calculate_bet_size(state, strategy, bet_num)

                # Check if we can afford it
                if bet_size > state.wallet:
                    continue

                # Place the bet
                current_price = (
                    game.prices[current_tick] if current_tick < len(game.prices) else 1.0
                )
                state.wallet -= bet_size
                state.total_wagered += bet_size

                state.active_bets.append(
                    ActiveBet(
                        bet_num=bet_num,
                        tick_placed=current_tick,
                        size=bet_size,
                        entry_price=current_price,
                        window_end=current_tick + SIDEBET_WINDOW,
                    )
                )

    def _calculate_bet_size(self, state: PlaybackState, strategy: dict, bet_num: int) -> float:
        """Calculate the bet size based on strategy."""
        bet_sizes = strategy.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])

        if bet_num <= len(bet_sizes):
            base_size = bet_sizes[bet_num - 1]
        else:
            base_size = 0.001

        # Kelly sizing
        if strategy.get("use_kelly_sizing", False):
            kelly_fraction = strategy.get("kelly_fraction", 0.25)
            # Simplified Kelly - use ~60% win rate assumption
            kelly_full = 0.60 - (1 - 0.60) / SIDEBET_PAYOUT
            kelly_adjusted = kelly_full * kelly_fraction
            base_size = max(0.0001, state.wallet * kelly_adjusted / 4)

        # Dynamic sizing adjustments
        if strategy.get("use_dynamic_sizing", False):
            # Apply multiplier if above threshold
            threshold = strategy.get("high_confidence_threshold", 60) / 100
            multiplier = strategy.get("high_confidence_multiplier", 2.0)
            # For now, assume we're always above threshold in backtest
            base_size *= multiplier

        # Reduce on drawdown
        if strategy.get("reduce_on_drawdown", False):
            current_dd = (
                (state.peak_balance - state.wallet) / state.peak_balance
                if state.peak_balance > 0
                else 0
            )
            if current_dd > 0.05:
                reduction = min(0.9, current_dd)
                base_size *= 1 - reduction

        # Round to 3 decimal places (thousandths) - rugs.fun UI precision
        return round(max(0.001, base_size), 3)

    def _handle_rug(self, state: PlaybackState):
        """Handle end of game (rug event)."""
        game = state.game
        if not game:
            return

        game.phase = "rugged"
        rug_tick = game.duration  # The tick when it rugged

        # Check early rug (before entry)
        entry_tick = state.strategy.get("params", state.strategy).get("entry_tick", 200)
        if rug_tick < entry_tick:
            state.early_rugs += 1
        else:
            state.games_played += 1

        # Resolve all active bets
        any_won = False
        for bet in state.active_bets:
            if bet.resolved:
                continue

            bet.resolved = True

            # Win if game rugged within bet window
            if bet.tick_placed <= rug_tick <= bet.window_end:
                bet.won = True
                payout = bet.size * SIDEBET_PAYOUT
                state.wallet += payout
                state.wins += 1
                any_won = True
            else:
                bet.won = False
                if rug_tick > bet.window_end:
                    state.losses += 1

        # Clear active bets
        state.active_bets = []

        # Update peak and drawdown
        if state.wallet > state.peak_balance:
            state.peak_balance = state.wallet

        current_dd = (
            (state.peak_balance - state.wallet) / state.peak_balance
            if state.peak_balance > 0
            else 0
        )
        state.max_drawdown = max(state.max_drawdown, current_dd)

        # Update equity curve
        state.equity_curve.append(state.wallet)

        # Check take-profit
        take_profit = state.strategy.get("params", state.strategy).get("take_profit_target")
        if take_profit and state.wallet >= state.initial_balance * take_profit:
            state.finished = True
            state.paused = True
            return

        # Check max drawdown
        max_dd = state.strategy.get("params", state.strategy).get("max_drawdown_pct", 0.50)
        if current_dd >= max_dd:
            state.finished = True
            state.paused = True
            return

        # Advance to next game
        self._advance_to_next_game(state)

    def _advance_to_next_game(self, state: PlaybackState):
        """Move to the next game in the validation set."""
        games = self.get_validation_games()

        state.current_game_idx += 1

        if state.current_game_idx >= len(games):
            state.finished = True
            state.paused = True
            state.game = None
            return

        next_game = games[state.current_game_idx]
        state.game = GameState(
            game_id=next_game["game_id"],
            prices=next_game["prices"],
            duration=next_game["duration"],
            current_tick=0,
            phase="active",
        )

    def stop_session(self, session_id: str):
        """Stop and remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


# Singleton instance
_service: BacktestService | None = None


def get_backtest_service() -> BacktestService:
    """Get the singleton backtest service instance."""
    global _service
    if _service is None:
        _service = BacktestService()
    return _service
