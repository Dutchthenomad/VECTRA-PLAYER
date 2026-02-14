# 19 - Sidebet RL Environment

## Purpose

Gymnasium environment for reinforcement learning-based sidebet timing optimization:
1. Real tick-by-tick price replay
2. 15-dimensional Bayesian observation space
3. Sniper strategy (single bet per game)
4. Reward shaping for optimal zone entry

## Dependencies

```python
import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces
from pathlib import Path
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Sidebet V1 Gymnasium Environment                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Historical Game Data                              │    │
│  │  games_with_prices.parquet:                                          │    │
│  │  - game_id, prices[], duration_ticks, peak_multiplier               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Episode Loop                                    │    │
│  │                                                                      │    │
│  │  reset() → Load random game                                         │    │
│  │     │                                                                │    │
│  │     ▼                                                                │    │
│  │  step(action) →  0=HOLD: advance tick                               │    │
│  │     │            1=BET:  place sidebet (if tick >= 200)             │    │
│  │     │                                                                │    │
│  │     ▼                                                                │    │
│  │  observation (15-dim) + reward (terminal only)                      │    │
│  │     │                                                                │    │
│  │     ▼                                                                │    │
│  │  terminated = (tick >= game_duration)                               │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Observation Space (15-dim)                        │    │
│  │                                                                      │    │
│  │  [0-3]  Game State:    tick, price, active, players                 │    │
│  │  [4-10] Bayesian:      peak, peak_tick, dist_from_peak,             │    │
│  │                        ticks_since_peak, vol_10, mom_5, velocity    │    │
│  │  [11-13] Sidebet:      active, ticks_remaining, can_bet             │    │
│  │  [14]   Context:       in_optimal_zone (tick >= 200)                │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Reward Structure (V4)                             │    │
│  │                                                                      │    │
│  │  WIN (rug in 40-tick window):     +4.0                              │    │
│  │  LOSS (no rug in window):         -1.0                              │    │
│  │  SKIP (game reached 200+):        -0.50                             │    │
│  │  SKIP (game reached 300+):        -0.75                             │    │
│  │  SKIP (game rugged < 200):         0.0 (no penalty)                 │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Environment Class

```python
# src/rl/envs/sidebet_v1_env.py

class SidebetV1Env(gym.Env):
    """
    Gymnasium environment for sidebet timing optimization.

    Replays historical games with real tick-by-tick prices.

    Episode: One complete game (tick 0 to rug)
    Action: 0=HOLD, 1=BET
    Observation: 15-dimensional Bayesian feature vector
    Reward: Terminal only (graduated by zone)
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    # Minimum tick to allow betting (optimal zone start)
    OPTIMAL_ZONE_START = 200

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
            data_path: Path to games_with_prices.parquet
            render_mode: "human" or "ansi" for visualization
            max_ticks: Safety limit for episode length
            shuffle: Randomize game order (default: True)
        """
        super().__init__()

        # Load game data
        self.games_df = pd.read_parquet(data_path or self.DEFAULT_DATA_PATH)
        self.num_games = len(self.games_df)
        self.shuffle = shuffle

        # Spaces
        self.action_space = spaces.Discrete(2)  # HOLD=0, BET=1
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32
        )

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
```

### 2. Observation Builder

```python
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
        """Build observation from current game state."""
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
        obs[14] = float(tick >= 200)  # can_bet_now

        return obs

    def _calc_volatility(self, window: int) -> float:
        """Standard deviation of price changes over window."""
        if len(self.price_history) < window + 1:
            return 0.0
        changes = np.diff(self.price_history[-window - 1:])
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
```

### 3. Reset Method

```python
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

    obs = self._get_observation()

    info = {
        "game_id": self.current_game["game_id"],
        "game_duration": self.current_game["duration"],
        "game_peak": self.current_game["peak"],
        "is_playable": not self.current_game["is_unplayable"],
    }

    return obs, info
```

### 4. Step Method

```python
def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
    """
    Execute one tick.

    Args:
        action: 0=HOLD, 1=BET

    Returns:
        observation, reward, terminated, truncated, info
    """
    assert self.current_game is not None, "Must call reset() before step()"

    # Enforce optimal zone requirement - BET only valid at tick 200+
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
```

### 5. Reward Calculation

```python
def _calculate_episode_reward(self) -> tuple[float, bool | None]:
    """
    Calculate terminal reward.

    V4 Economics:
    - WIN: +4.0 (matches 5:1 payout minus stake)
    - LOSS: -1.0 (matches 20% breakeven requirement)
    - SKIP: -0.50 to -0.75 (encourages selective betting)

    Returns:
        (reward, bet_won) where bet_won is None if no bet placed
    """
    game_duration = self.current_game["duration"]

    # No bet - skip penalty
    if not self.bet_placed or self.bet_tick is None:
        return self._skip_penalty(game_duration), None

    # Check win condition: rug happens within 40-tick window
    bet_window_end = self.bet_tick + 40
    bet_won = game_duration < bet_window_end

    if bet_won:
        return 4.0, True  # WIN_REWARD
    else:
        return -1.0, False  # LOSS_PENALTY

def _skip_penalty(self, duration: int) -> float:
    """
    Penalty for not betting.

    No penalty if game rugged before optimal zone.
    """
    if duration < 200:
        return 0.0  # Game didn't reach optimal zone - no penalty
    elif duration < 300:
        return -0.50  # Optimal zone reached but didn't bet
    else:
        return -0.75  # Extended game - missed opportunities

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
```

### 6. Training Example

```python
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# Create environment
def make_env():
    return SidebetV1Env(shuffle=True)

env = DummyVecEnv([make_env])

# Train with PPO
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    verbose=1,
)

model.learn(total_timesteps=100_000)

# Evaluate
env_eval = SidebetV1Env(shuffle=False)
obs, info = env_eval.reset()
total_reward = 0

for _ in range(1000):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env_eval.step(action)
    total_reward += reward

    if terminated or truncated:
        obs, info = env_eval.reset()

print(f"Eval stats: {env_eval.get_stats()}")
```

## Observation Space Details

| Index | Feature | Range | Description |
|-------|---------|-------|-------------|
| 0 | tick | [0, 2000] | Current game tick |
| 1 | price | [1.0, 50.0] | Current multiplier |
| 2 | active | {0, 1} | Game active flag |
| 3 | players | [0, 500] | Connected players |
| 4 | running_peak | [1.0, 50.0] | Max price so far |
| 5 | peak_tick | [0, 2000] | Tick of peak |
| 6 | dist_from_peak | [0.0, 1.0] | (peak - price) / peak |
| 7 | ticks_since_peak | [0, 2000] | tick - peak_tick |
| 8 | volatility_10 | [0.0, 1.0] | Std of last 10 changes |
| 9 | momentum_5 | [-1.0, 1.0] | Avg change over 5 ticks |
| 10 | velocity | [-0.5, 0.5] | Last tick change |
| 11 | sidebet_active | {0, 1} | Have active bet |
| 12 | ticks_remaining | [0, 40] | Ticks left in window |
| 13 | can_bet | {0, 1} | Can place new bet |
| 14 | in_optimal_zone | {0, 1} | tick >= 200 |

## Reward Structure Comparison

| Version | WIN | LOSS | SKIP (200+) | SKIP (300+) |
|---------|-----|------|-------------|-------------|
| V1 | +4.0 | -0.50 | -1.0 | -1.5 |
| V2 | +4.0 | -0.65 | -1.0 | -1.5 |
| V3 | +4.0 | -0.75 | -1.0 | -1.5 |
| V4 | +4.0 | -1.0 | -0.50 | -0.75 |

V4 aligns loss penalty with 20% breakeven and reduces skip penalty.

## Gotchas

1. **Optimal Zone Enforcement**: BET action is forced to HOLD if tick < 200.

2. **Single Bet**: Only one bet per game (Sniper strategy). Subsequent BET actions become HOLD.

3. **Terminal Reward**: All reward is given at episode end, not per-step.

4. **Game Selection**: Use `shuffle=False` for deterministic evaluation.

5. **Price History**: ObservationBuilder maintains price history; call `reset()` on new game.

6. **Unplayable Games**: Some games rug before tick 200. These have `is_unplayable=True`.

7. **Data Path**: Default looks for `games_with_prices.parquet` in standard location.
