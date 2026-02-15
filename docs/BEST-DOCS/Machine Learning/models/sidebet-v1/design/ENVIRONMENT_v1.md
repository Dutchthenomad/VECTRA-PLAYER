# Sidebet v1 Gymnasium Environment

**Date:** January 10, 2026
**Status:** DESIGN COMPLETE - Ready for Implementation
**Framework:** Gymnasium + Stable-Baselines3
**Data:** Real tick-by-tick prices from 943 games

---

## Overview

The environment replays historical games for offline RL training. Each episode is one complete game from tick 0 to rug.

| Property | Value |
|----------|-------|
| Observation Space | Box(15,) - Bayesian features |
| Action Space | Discrete(2) - HOLD=0, BET=1 |
| Episode Length | 2-1815 ticks (median: 144) |
| Data Source | `games_with_prices.parquet` (943 games) |

---

## Training Data

### games_with_prices.parquet

| Column | Type | Description |
|--------|------|-------------|
| `game_id` | string | Unique identifier |
| `timestamp` | int | Unix timestamp (ms) |
| `duration_ticks` | int | Total game length |
| `prices` | list[float] | **Real tick-by-tick prices** |
| `peak_multiplier` | float | Max price reached |
| `peak_tick` | int | Tick of peak |
| `ticks_after_peak` | int | Ticks from peak to rug |
| `final_price` | float | Price at rug |
| `is_unplayable` | bool | True if < 40 ticks |
| `game_version` | string | Protocol version |

**Key:** The `prices` array contains the REAL multiplier at each tick, extracted from `complete_game` Parquet files.

---

## Environment Implementation

```python
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, Any, List


class SidebetV1ObservationBuilder:
    """Build 15-dimensional observation vector."""

    def __init__(self):
        self.price_history: List[float] = []

    def reset(self):
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
        obs[14] = float(tick >= 200)

        return obs

    def _calc_volatility(self, window: int) -> float:
        if len(self.price_history) < window + 1:
            return 0.0
        changes = np.diff(self.price_history[-window-1:])
        return float(np.std(changes))

    def _calc_momentum(self, window: int) -> float:
        if len(self.price_history) < window + 1:
            return 0.0
        return (self.price_history[-1] - self.price_history[-window-1]) / window

    def _calc_velocity(self) -> float:
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
    Reward: Terminal only (see REWARD_FUNCTION_v1.md)
    """

    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    def __init__(
        self,
        data_path: str = None,
        render_mode: Optional[str] = None,
        max_ticks: int = 2000,
        shuffle: bool = True,
    ):
        """
        Initialize environment.

        Args:
            data_path: Path to games_with_prices.parquet
            render_mode: "human" or "ansi" for visualization
            max_ticks: Safety limit for episode length
            shuffle: Randomize game order each epoch
        """
        super().__init__()

        # Default path
        if data_path is None:
            data_path = "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/training_data/games_with_prices.parquet"

        # Load game data
        self.games_df = pd.read_parquet(data_path)
        self.game_ids = self.games_df['game_id'].tolist()
        self.shuffle = shuffle

        # Spaces
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32
        )

        # Config
        self.max_ticks = max_ticks
        self.render_mode = render_mode

        # Episode state
        self.current_game_idx = -1
        self.current_game = None
        self.current_tick = 0
        self.bet_placed = False
        self.bet_tick = None
        self.obs_builder = SidebetV1ObservationBuilder()

        # Stats tracking
        self.episode_count = 0
        self.total_reward = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """Reset to start of next game."""
        super().reset(seed=seed)

        # Select next game
        if options and options.get('game_idx') is not None:
            self.current_game_idx = options['game_idx']
        elif self.shuffle:
            self.current_game_idx = self.np_random.integers(len(self.game_ids))
        else:
            self.current_game_idx = (self.current_game_idx + 1) % len(self.game_ids)

        # Load game
        game_row = self.games_df.iloc[self.current_game_idx]
        self.current_game = {
            'game_id': game_row['game_id'],
            'prices': game_row['prices'],
            'duration': game_row['duration_ticks'],
            'peak': game_row['peak_multiplier'],
            'peak_tick': game_row['peak_tick'],
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
            "game_id": self.current_game['game_id'],
            "game_duration": self.current_game['duration'],
            "game_peak": self.current_game['peak'],
            "is_playable": self.current_game['duration'] >= 40,
        }

        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one tick.

        Args:
            action: 0=HOLD, 1=BET

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Enforce single bet rule
        if action == 1 and self.bet_placed:
            action = 0

        # Record bet
        if action == 1 and not self.bet_placed:
            self.bet_placed = True
            self.bet_tick = self.current_tick

        # Advance tick
        self.current_tick += 1

        # Check termination
        game_duration = self.current_game['duration']
        terminated = self.current_tick >= game_duration
        truncated = self.current_tick >= self.max_ticks

        # Calculate reward (terminal only)
        reward = 0.0
        bet_won = None

        if terminated or truncated:
            reward, bet_won = self._calculate_episode_reward()
            self.total_reward += reward

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

        return obs, reward, terminated, truncated, info

    def _get_current_price(self) -> float:
        """Get price at current tick."""
        idx = min(self.current_tick, len(self.current_game['prices']) - 1)
        return self.current_game['prices'][idx]

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
            connected_players=100,  # Placeholder for replay
            sidebet_active=sidebet_active,
            sidebet_end_tick=sidebet_end_tick,
        )

    def _calculate_episode_reward(self) -> Tuple[float, Optional[bool]]:
        """Calculate terminal reward."""
        game_duration = self.current_game['duration']

        # No bet - skip penalty
        if not self.bet_placed:
            return self._skip_penalty(game_duration), None

        # Check win condition
        bet_window_end = self.bet_tick + 40
        bet_won = game_duration < bet_window_end
        ticks_to_rug = abs(game_duration - bet_window_end)

        reward = self._bet_reward(self.bet_tick, bet_won, ticks_to_rug)
        return reward, bet_won

    def _skip_penalty(self, duration: int) -> float:
        """Penalty for not betting (from REWARD_FUNCTION_v1.md)."""
        if duration < 40:
            return 0.0
        elif duration < 90:
            return -0.30
        elif duration < 200:
            return -0.60
        elif duration < 300:
            return -1.20
        else:
            return -1.75

    def _bet_reward(self, entry_tick: int, won: bool, ticks_to_rug: int) -> float:
        """Zone-based reward (from REWARD_FUNCTION_v1.md)."""
        zone = self._categorize_tick(entry_tick)

        WIN = {"optimal_zone": 4.0, "marginal_late": 3.0, "marginal_early": 2.5,
               "dead_zone": 2.0, "very_early": 1.5}
        LOSS = {"optimal_zone": -0.75, "marginal_late": -0.85, "marginal_early": -0.90,
                "dead_zone": -1.00, "very_early": -0.50}

        if won:
            return WIN[zone]
        else:
            near_miss = 0.15 if ticks_to_rug <= 10 else (0.08 if ticks_to_rug <= 20 else 0.0)
            return LOSS[zone] + near_miss

    def _categorize_tick(self, tick: int) -> str:
        """Map tick to strategic zone."""
        if tick >= 200: return "optimal_zone"
        if tick >= 150: return "marginal_late"
        if tick >= 100: return "marginal_early"
        if tick >= 50: return "dead_zone"
        return "very_early"

    def render(self):
        """Render current state."""
        if self.render_mode == "ansi":
            price = self._get_current_price()
            bet_status = f"BET@{self.bet_tick}" if self.bet_placed else "NO_BET"
            zone = self._categorize_tick(self.current_tick)
            return f"T:{self.current_tick:4d} P:{price:6.3f} [{zone:12s}] {bet_status}"
        return None

    def get_episode_stats(self) -> Dict:
        """Get training statistics."""
        return {
            "episodes": self.episode_count,
            "total_reward": self.total_reward,
            "avg_reward": self.total_reward / max(self.episode_count, 1),
        }


# === ENVIRONMENT REGISTRATION ===
def make_sidebet_v1_env(**kwargs):
    """Factory function for environment creation."""
    return SidebetV1Env(**kwargs)


# Register with Gymnasium (optional)
# gym.register(
#     id="SidebetV1-v0",
#     entry_point="sidebet_v1_env:SidebetV1Env",
# )
```

---

## Training Script

```python
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.callbacks import EvalCallback
import os

# Create environment
def make_env():
    return SidebetV1Env(shuffle=True)

env = DummyVecEnv([make_env])
env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=10.0)

# Create model
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01,
    verbose=1,
    tensorboard_log="./logs/sidebet_v1/",
)

# Evaluation callback
eval_env = DummyVecEnv([make_env])
eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, training=False)
eval_callback = EvalCallback(
    eval_env,
    best_model_save_path="./checkpoints/",
    log_path="./logs/",
    eval_freq=10000,
    n_eval_episodes=50,
)

# Train
model.learn(
    total_timesteps=500_000,
    callback=eval_callback,
    progress_bar=True,
)

# Save
model.save("sidebet_v1_final")
env.save("vecnorm_sidebet_v1.pkl")
```

---

## Validation Tests

```python
def test_environment():
    """Validate environment behavior."""
    env = SidebetV1Env(shuffle=False)

    # Test reset
    obs, info = env.reset()
    assert obs.shape == (15,), f"Obs shape: {obs.shape}"
    assert "game_id" in info

    # Test step without bet
    obs, reward, term, trunc, info = env.step(0)
    assert reward == 0.0, "Mid-episode reward should be 0"

    # Test full episode
    env.reset()
    total_reward = 0
    while True:
        obs, reward, term, trunc, info = env.step(0)  # Always HOLD
        total_reward += reward
        if term or trunc:
            break

    # Should get skip penalty for playable game
    if info["game_duration"] >= 40:
        assert total_reward < 0, "Should have skip penalty"

    # Test betting
    env.reset()
    for _ in range(200):  # Wait for optimal zone
        obs, reward, term, trunc, info = env.step(0)
        if term or trunc:
            break

    if not (term or trunc):
        obs, reward, term, trunc, info = env.step(1)  # Place bet
        assert info["bet_placed"] == True
        assert info["bet_tick"] == 200

    print("All tests passed!")

test_environment()
```

---

## Episode Flow

```
reset()
  ├── Select next game (random or sequential)
  ├── Load prices array from Parquet
  ├── Reset: tick=0, bet_placed=False
  └── Return: obs[15], info{game_id, duration, ...}
       │
       ▼
step(action) ────────────────────────────────┐
  ├── If action=1 and !bet_placed:           │
  │     bet_placed=True, bet_tick=current    │
  ├── current_tick += 1                      │
  ├── Check: terminated = tick >= duration   │
  │                                          │
  ├── If terminated:                         │
  │     reward = calculate_terminal_reward() │
  │     └── Skip penalty OR bet reward       │
  │                                          │
  └── Return: obs, reward, term, trunc, info │
       │                                     │
       └── If not terminated ────────────────┘
              (loop back to step)
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Replay (Parquet) | 943 games sufficient for v1 |
| Reward timing | Terminal only | Prevents mid-episode hacking |
| Action masking | Single bet enforced | Sniper strategy |
| Price data | Real tick-by-tick | No synthetic approximations |
| Shuffle | Random by default | Better generalization |

---

## File Locations

| Component | Path |
|-----------|------|
| Environment | `src/rl/envs/sidebet_v1_env.py` |
| Training script | `scripts/train_sidebet_v1.py` |
| Training data | `Machine Learning/models/sidebet-v1/training_data/` |
| Checkpoints | `Machine Learning/models/sidebet-v1/checkpoints/` |
| Logs | `Machine Learning/models/sidebet-v1/logs/` |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-10 | Initial design with real price data |

---

*Collaboratively designed: Human + Claude*
*Session: 2026-01-10*
