"""
Sidebet V4 Gymnasium Environment

Trains an RL agent to optimize sidebet timing in rugs.fun.
Uses real tick-by-tick price data from historical games.

Strategy: Sniper (single bet per game, ONLY in optimal zone tick 200+)

V4 Changes (from V3):
- LOSS penalty: -0.75 → -1.0 (aligns with 20% real breakeven)
- SKIP penalty: -1.0 → -0.5 (encourages selective betting)
- Extended SKIP: -1.5 → -0.75 (proportionally reduced)
- Removed near-miss bonus (clean economics)

V3 Base Features (unchanged):
- Betting only allowed at tick 200+ (optimal zone)
- No penalty for games that rug before reaching optimal zone
- 15-dimensional Bayesian observation space

Author: Human + Claude
Date: 2026-01-11
"""

from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces


class SidebetV1ObservationBuilder:
    """
    Build 15-dimensional observation vector for Sidebet v1.

    Features:
    - Game State (4): tick, price, active, connected_players
    - Bayesian Predictors (7): running_peak, peak_tick, distance_from_peak,
      ticks_since_peak, volatility_10, momentum_5, price_velocity
    - Sidebet State (3): sidebet_active, sidebet_ticks_remaining, can_place_bet
    - Game Context (1): game_in_optimal_zone

    Design principles:
    - No future information leakage
    - All features computable from current/past data
    - Aligned with Bayesian predictors
    """

    def __init__(self):
        self.price_history: list[float] = []

    def reset(self):
        """Reset for new game."""
        self.price_history = []

    def build(
        self,
        tick: int,
        price: float,
        active: bool,
        connected_players: int,
        sidebet_active: bool = False,
        sidebet_end_tick: int = 0,
    ) -> np.ndarray:
        """
        Build observation from current game state.

        Args:
            tick: Current tick count
            price: Current price/multiplier
            active: Whether game is active
            connected_players: Number of connected players
            sidebet_active: Whether we have an active sidebet
            sidebet_end_tick: Tick when sidebet window closes

        Returns:
            15-dimensional float32 array
        """
        obs = np.zeros(15, dtype=np.float32)

        # Update price history
        self.price_history.append(price)

        # === GAME STATE (0-3) ===
        obs[0] = float(tick)
        obs[1] = float(price)
        obs[2] = float(active)
        obs[3] = float(connected_players)

        # === BAYESIAN PREDICTORS (4-10) ===
        if len(self.price_history) > 0:
            running_peak = max(self.price_history)
            peak_tick = self.price_history.index(running_peak)

            obs[4] = float(running_peak)
            obs[5] = float(peak_tick)
            obs[6] = (running_peak - price) / running_peak if running_peak > 0 else 0.0
            obs[7] = float(tick - peak_tick)

        obs[8] = self._calc_volatility(10)
        obs[9] = self._calc_momentum(5)
        obs[10] = self._calc_velocity()

        # === SIDEBET STATE (11-13) ===
        if sidebet_active:
            obs[11] = 1.0
            obs[12] = float(max(0, sidebet_end_tick - tick))
        obs[13] = float(active and not sidebet_active)

        # === GAME CONTEXT (14) ===
        # V3: This now indicates if betting is ALLOWED (optimal zone reached)
        obs[14] = float(tick >= 200)  # can_bet_now

        return obs

    def _calc_volatility(self, window: int) -> float:
        """Standard deviation of price changes over window."""
        if len(self.price_history) < window + 1:
            return 0.0
        changes = np.diff(self.price_history[-window - 1 :])
        return float(np.std(changes))

    def _calc_momentum(self, window: int) -> float:
        """Average price change per tick over window."""
        if len(self.price_history) < window + 1:
            return 0.0
        return (self.price_history[-1] - self.price_history[-window - 1]) / window

    def _calc_velocity(self) -> float:
        """Instantaneous price change (last tick)."""
        if len(self.price_history) < 2:
            return 0.0
        return self.price_history[-1] - self.price_history[-2]


class SidebetV1Env(gym.Env):
    """
    Gymnasium environment for sidebet timing optimization.

    Replays historical games with real tick-by-tick prices.

    Episode: One complete game (tick 0 to rug)
    Action: 0=HOLD, 1=BET
    Observation: 15-dimensional Bayesian feature vector
    Reward: Terminal only (graduated by zone)

    See: Machine Learning/models/sidebet-v1/design/ for full documentation.
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    # Default data path
    DEFAULT_DATA_PATH = (
        Path(__file__).parent.parent.parent.parent
        / "Machine Learning"
        / "models"
        / "sidebet-v1"
        / "training_data"
        / "games_with_prices.parquet"
    )

    def __init__(
        self,
        data_path: str | None = None,
        render_mode: str | None = None,
        max_ticks: int = 2000,
        shuffle: bool = True,
    ):
        """
        Initialize environment.

        Args:
            data_path: Path to games_with_prices.parquet (optional)
            render_mode: "human" or "ansi" for visualization
            max_ticks: Safety limit for episode length
            shuffle: Randomize game order (default: True)
        """
        super().__init__()

        # Resolve data path
        if data_path is None:
            data_path = str(self.DEFAULT_DATA_PATH)

        # Load game data
        self.games_df = pd.read_parquet(data_path)
        self.num_games = len(self.games_df)
        self.shuffle = shuffle

        # Spaces
        self.action_space = spaces.Discrete(2)  # HOLD=0, BET=1
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)

        # Config
        self.max_ticks = max_ticks
        self.render_mode = render_mode

        # Episode state
        self.current_game_idx = -1
        self.current_game: dict | None = None
        self.current_tick = 0
        self.bet_placed = False
        self.bet_tick: int | None = None
        self.obs_builder = SidebetV1ObservationBuilder()

        # Stats tracking
        self.episode_count = 0
        self.total_reward = 0.0
        self.wins = 0
        self.losses = 0
        self.skips = 0

    def reset(
        self, seed: int | None = None, options: dict | None = None
    ) -> tuple[np.ndarray, dict]:
        """
        Reset to start of next game.

        Args:
            seed: Random seed for reproducibility
            options: Optional dict with 'game_idx' to select specific game

        Returns:
            observation, info
        """
        super().reset(seed=seed)

        # Select next game
        if options and options.get("game_idx") is not None:
            self.current_game_idx = options["game_idx"] % self.num_games
        elif self.shuffle:
            self.current_game_idx = self.np_random.integers(self.num_games)
        else:
            self.current_game_idx = (self.current_game_idx + 1) % self.num_games

        # Load game
        game_row = self.games_df.iloc[self.current_game_idx]
        prices = game_row["prices"]
        if isinstance(prices, np.ndarray):
            prices = prices.tolist()

        self.current_game = {
            "game_id": game_row["game_id"],
            "prices": prices,
            "duration": int(game_row["duration_ticks"]),
            "peak": float(game_row["peak_multiplier"]),
            "peak_tick": int(game_row["peak_tick"]),
            "is_unplayable": bool(game_row["is_unplayable"]),
        }

        # Reset episode state
        self.current_tick = 0
        self.bet_placed = False
        self.bet_tick = None
        self.obs_builder.reset()
        self.episode_count += 1

        # Build initial observation
        obs = self._get_observation()

        info = {
            "game_id": self.current_game["game_id"],
            "game_duration": self.current_game["duration"],
            "game_peak": self.current_game["peak"],
            "is_playable": not self.current_game["is_unplayable"],
        }

        return obs, info

    # Minimum tick to allow betting (optimal zone start)
    OPTIMAL_ZONE_START = 200

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        """
        Execute one tick.

        Args:
            action: 0=HOLD, 1=BET

        Returns:
            observation, reward, terminated, truncated, info
        """
        assert self.current_game is not None, "Must call reset() before step()"

        # V3: Enforce optimal zone requirement - BET only valid at tick 200+
        if action == 1 and self.current_tick < self.OPTIMAL_ZONE_START:
            action = 0  # Force HOLD if not in optimal zone

        # Enforce single bet rule (Sniper strategy)
        if action == 1 and self.bet_placed:
            action = 0

        # Record bet
        if action == 1 and not self.bet_placed:
            self.bet_placed = True
            self.bet_tick = self.current_tick

        # Advance tick
        self.current_tick += 1

        # Check termination
        game_duration = self.current_game["duration"]
        terminated = self.current_tick >= game_duration
        truncated = self.current_tick >= self.max_ticks

        # Calculate reward (terminal only)
        reward = 0.0
        bet_won: bool | None = None

        if terminated or truncated:
            reward, bet_won = self._calculate_episode_reward()
            self.total_reward += reward

            # Track stats
            if bet_won is None:
                self.skips += 1
            elif bet_won:
                self.wins += 1
            else:
                self.losses += 1

        # Build observation
        obs = self._get_observation()

        info = {
            "tick": self.current_tick,
            "price": self._get_current_price(),
            "bet_placed": self.bet_placed,
            "bet_tick": self.bet_tick,
            "game_duration": game_duration,
        }

        if terminated or truncated:
            info["bet_won"] = bet_won
            info["episode_reward"] = reward
            info["zone"] = self._categorize_tick(self.bet_tick) if self.bet_tick else "skip"

        return obs, reward, terminated, truncated, info

    def _get_current_price(self) -> float:
        """Get price at current tick."""
        assert self.current_game is not None
        idx = min(self.current_tick, len(self.current_game["prices"]) - 1)
        return self.current_game["prices"][idx]

    def _get_observation(self) -> np.ndarray:
        """Build observation for current state."""
        price = self._get_current_price()

        sidebet_active = False
        sidebet_end_tick = 0
        if self.bet_placed and self.bet_tick is not None:
            sidebet_end_tick = self.bet_tick + 40
            if self.current_tick < sidebet_end_tick:
                sidebet_active = True

        return self.obs_builder.build(
            tick=self.current_tick,
            price=price,
            active=True,
            connected_players=100,  # Placeholder for replay mode
            sidebet_active=sidebet_active,
            sidebet_end_tick=sidebet_end_tick,
        )

    def _calculate_episode_reward(self) -> tuple[float, bool | None]:
        """
        Calculate terminal reward.

        Returns:
            (reward, bet_won) where bet_won is None if no bet placed
        """
        assert self.current_game is not None
        game_duration = self.current_game["duration"]

        # No bet - skip penalty
        if not self.bet_placed or self.bet_tick is None:
            return self._skip_penalty(game_duration), None

        # Check win condition
        bet_window_end = self.bet_tick + 40
        bet_won = game_duration < bet_window_end
        ticks_to_rug = abs(game_duration - bet_window_end)

        reward = self._bet_reward(self.bet_tick, bet_won, ticks_to_rug)
        return reward, bet_won

    def _skip_penalty(self, duration: int) -> float:
        """
        Penalty for not betting.

        V4: Reduced skip penalties to encourage selective betting.
        Skip penalty only applies if game reached optimal zone.
        """
        if duration < 200:
            return 0.0  # Game didn't reach optimal zone - no penalty
        elif duration < 300:
            return -0.50  # Optimal zone reached but didn't bet (V4: was -1.0)
        else:
            return -0.75  # Extended game - missed opportunities (V4: was -1.5)

    def _bet_reward(self, entry_tick: int, won: bool, ticks_to_rug: int) -> float:
        """
        Simple reward for optimal zone betting.

        V4: Loss penalty aligned with 20% breakeven.
        No near-miss bonus (clean economics).
        """
        WIN_REWARD = 4.0  # Win in optimal zone
        LOSS_PENALTY = -1.0  # Loss (V4: was -0.75, now matches 20% breakeven)

        if won:
            return WIN_REWARD
        else:
            return LOSS_PENALTY  # V4: Removed near-miss bonus

    def _categorize_tick(self, tick: int) -> str:
        """Map tick to strategic zone."""
        if tick >= 200:
            return "optimal_zone"
        elif tick >= 150:
            return "marginal_late"
        elif tick >= 100:
            return "marginal_early"
        elif tick >= 50:
            return "dead_zone"
        else:
            return "very_early"

    def _near_miss_bonus(self, ticks_to_rug: int) -> float:
        """Bonus for close losses (reward shaping)."""
        if ticks_to_rug <= 10:
            return 0.15
        elif ticks_to_rug <= 20:
            return 0.08
        else:
            return 0.0

    def render(self) -> str | None:
        """Render current state."""
        if self.render_mode == "ansi" and self.current_game is not None:
            price = self._get_current_price()
            bet_status = f"BET@{self.bet_tick}" if self.bet_placed else "NO_BET"
            zone = self._categorize_tick(self.current_tick)
            return f"T:{self.current_tick:4d} P:{price:6.3f} [{zone:12s}] {bet_status}"
        return None

    def get_stats(self) -> dict[str, Any]:
        """Get training statistics."""
        total_bets = self.wins + self.losses
        return {
            "episodes": self.episode_count,
            "total_reward": self.total_reward,
            "avg_reward": self.total_reward / max(self.episode_count, 1),
            "wins": self.wins,
            "losses": self.losses,
            "skips": self.skips,
            "win_rate": self.wins / max(total_bets, 1),
            "bet_rate": total_bets / max(self.episode_count, 1),
        }

    def close(self):
        """Clean up resources."""
        pass


# === FACTORY FUNCTION ===
def make_sidebet_v1_env(**kwargs) -> SidebetV1Env:
    """Factory function for environment creation."""
    return SidebetV1Env(**kwargs)
