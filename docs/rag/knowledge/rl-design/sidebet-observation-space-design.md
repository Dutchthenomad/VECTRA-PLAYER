# Sidebet Timing Optimization - RL Observation Space Design

**Date:** 2026-01-07
**Status:** DESIGN SPECIFICATION
**Target Framework:** Gymnasium + Stable-Baselines3
**Based on:** Bayesian Analysis (568 games), rugs.fun Protocol v3.0

---

## Executive Summary

This document defines the RL observation space for sidebet timing optimization in rugs.fun. Based on empirical analysis of 568 games:

- **Win Rate**: 17.4% overall, 19.9% for tick 200-500
- **Breakeven**: 20% (5x payout requires 1/6 win rate)
- **Key Features** (Bayesian): `age`, `ticks_since_peak`, `distance_from_peak`, `volatility_10`, `momentum_5`
- **Optimal Window**: 40 ticks (sidebet duration)

**Design Philosophy**: Server-authoritative state from `gameStateUpdate` + derived features, aligned with Bayesian predictors.

---

## 1. Action Space

### Discrete(2) - Binary Decision

```python
from gymnasium import spaces

action_space = spaces.Discrete(2)

# Action encoding
ACTIONS = {
    0: "HOLD",       # Do not place sidebet this tick
    1: "PLACE_5X",   # Place 5x sidebet now
}
```

### Future Extension (Multi-Discrete)

```python
# For future 10x sidebet support
action_space = spaces.MultiDiscrete([2, 2])  # [place_5x, place_10x]

# Or explicit choice
action_space = spaces.Discrete(3)
ACTIONS = {
    0: "HOLD",
    1: "PLACE_5X",
    2: "PLACE_10X",
}
```

---

## 2. Observation Space Design

### 2.1 Space Definition

```python
from gymnasium import spaces
import numpy as np

observation_space = spaces.Box(
    low=-np.inf,
    high=np.inf,
    shape=(28,),  # 28-dimensional feature vector
    dtype=np.float32
)
```

### 2.2 Feature Taxonomy

| Category | Count | Purpose |
|----------|-------|---------|
| Game State (Raw) | 6 | Direct from `gameStateUpdate` |
| Price Features | 7 | Bayesian predictors |
| Position Context | 3 | Player state |
| Market Context | 4 | Multi-player dynamics |
| Session Context | 5 | Meta-game statistics |
| Sidebet State | 3 | Current sidebet status |
| **TOTAL** | **28** | |

---

## 3. Feature Definitions

### 3.1 Game State (Raw) - 6 features

Direct extraction from `gameStateUpdate` event.

| Index | Feature | Type | Range | Source Field |
|-------|---------|------|-------|--------------|
| 0 | `tick` | int | [0, 2000] | `tickCount` |
| 1 | `price` | float | [0.02, 1000+] | `price` |
| 2 | `active` | bool | {0, 1} | `active` |
| 3 | `cooldown_timer_ms` | int | [0, 30000] | `cooldownTimer` |
| 4 | `allow_pre_round_buys` | bool | {0, 1} | `allowPreRoundBuys` |
| 5 | `connected_players` | int | [0, 500] | `connectedPlayers` |

**Normalization**: Tick, price, timer scaled to [0, 1] via running statistics.

---

### 3.2 Price Features (Bayesian Predictors) - 7 features

Derived from `partialPrices` history and current state. These features are the **top predictors** from Bayesian analysis.

| Index | Feature | Formula | Range | Notes |
|-------|---------|---------|-------|-------|
| 6 | `age` | Current tick count | [0, 2000] | Normalized by max observed |
| 7 | `distance_from_peak` | `(peak - current) / peak` | [0, 1] | Relative distance |
| 8 | `ticks_since_peak` | `tick - tick_at_peak` | [0, 2000] | Critical predictor |
| 9 | `volatility_5` | `std(price_changes[-5:])` | [0, ∞] | 5-tick rolling std |
| 10 | `volatility_10` | `std(price_changes[-10:])` | [0, ∞] | 10-tick rolling std |
| 11 | `momentum_3` | `(price - price[-3]) / 3` | [-∞, ∞] | 3-tick momentum |
| 12 | `momentum_5` | `(price - price[-5]) / 5` | [-∞, ∞] | 5-tick momentum |

**Peak Tracking**:
```python
peak_price = max(price_history)
peak_tick = price_history.index(peak_price)
distance_from_peak = (peak_price - current_price) / peak_price
ticks_since_peak = current_tick - peak_tick
```

**Volatility Calculation**:
```python
def calc_volatility(window: int) -> float:
    if tick < window:
        return 0.0
    returns = np.diff(prices[-window:])
    return np.std(returns)
```

---

### 3.3 Position Context - 3 features

Player's trading state from `playerUpdate` (auth required).

| Index | Feature | Type | Range | Source Field |
|-------|---------|------|-------|--------------|
| 13 | `position_qty` | float | [0, ∞] | `playerUpdate.positionQty` |
| 14 | `avg_cost` | float | [0, ∞] | `playerUpdate.avgCost` |
| 15 | `unrealized_pnl_pct` | float | [-100, ∞] | Calculated: `(price/avgCost - 1) * 100` |

**Note**: If no position, all three are 0.0.

---

### 3.4 Market Context - 4 features

Multi-player activity from `gameStateUpdate.leaderboard[]`.

| Index | Feature | Formula | Range | Notes |
|-------|---------|---------|-------|-------|
| 16 | `players_with_positions` | Count `hasActiveTrades=true` | [0, 500] | Active traders |
| 17 | `total_market_capital` | Sum `totalInvested` | [0, ∞] | Total SOL at risk |
| 18 | `recent_trade_count` | Trades in last 10 ticks | [0, 100+] | From `standard/newTrade` |
| 19 | `rugpool_ratio` | `rugpoolAmount / threshold` | [0, 1+] | Instarug risk |

**Trade Counting**: Subscribe to `standard/newTrade` events, maintain rolling 10-tick window.

---

### 3.5 Session Context (Meta-Game) - 5 features

Statistical patterns from `gameStateUpdate` session data.

| Index | Feature | Type | Range | Source Field |
|-------|---------|------|-------|--------------|
| 20 | `average_multiplier` | float | [0, 100+] | `averageMultiplier` |
| 21 | `count_2x` | int | [0, ∞] | `count2x` |
| 22 | `count_10x` | int | [0, ∞] | `count10x` |
| 23 | `count_50x` | int | [0, ∞] | `count50x` |
| 24 | `highest_today` | float | [0, 1000+] | `highestToday` |

**Hypothesis**: Games during high `averageMultiplier` sessions may have different rug timing distributions.

---

### 3.6 Sidebet State - 3 features

Current sidebet status (if any).

| Index | Feature | Type | Range | Notes |
|-------|---------|------|-------|-------|
| 25 | `sidebet_active` | bool | {0, 1} | From `currentSidebet` |
| 26 | `sidebet_start_tick` | int | [0, 2000] | `currentSidebet.startTick` |
| 27 | `sidebet_end_tick` | int | [0, 2000] | `currentSidebet.endTick` |

**If no active sidebet**: All three are 0.

---

## 4. Observation Builder Implementation

```python
import numpy as np
from typing import Dict, List

class SidebetObservationBuilder:
    """Build 28-dimensional observation vector from game state."""
    
    def __init__(self):
        self.price_history: List[float] = []
        self.trade_timestamps: List[int] = []
        
    def reset(self):
        """Reset for new game."""
        self.price_history = []
        self.trade_timestamps = []
        
    def build(self, 
              game_state: Dict,
              player_state: Dict,
              sidebet_state: Dict) -> np.ndarray:
        """
        Build observation vector.
        
        Args:
            game_state: From gameStateUpdate event
            player_state: From playerUpdate event (or None)
            sidebet_state: From currentSidebet event (or None)
            
        Returns:
            28-dimensional float32 array
        """
        obs = np.zeros(28, dtype=np.float32)
        
        # === GAME STATE (0-5) ===
        obs[0] = float(game_state['tickCount'])
        obs[1] = float(game_state['price'])
        obs[2] = float(game_state['active'])
        obs[3] = float(game_state['cooldownTimer'])
        obs[4] = float(game_state['allowPreRoundBuys'])
        obs[5] = float(game_state['connectedPlayers'])
        
        # Update price history
        self.price_history.append(obs[1])
        
        # === PRICE FEATURES (6-12) ===
        obs[6] = obs[0]  # age = tick
        
        if len(self.price_history) > 0:
            peak = max(self.price_history)
            peak_idx = self.price_history.index(peak)
            obs[7] = (peak - obs[1]) / peak if peak > 0 else 0  # distance_from_peak
            obs[8] = float(obs[0] - peak_idx)  # ticks_since_peak
        
        obs[9] = self._calc_volatility(5)   # volatility_5
        obs[10] = self._calc_volatility(10)  # volatility_10
        obs[11] = self._calc_momentum(3)     # momentum_3
        obs[12] = self._calc_momentum(5)     # momentum_5
        
        # === POSITION CONTEXT (13-15) ===
        if player_state:
            obs[13] = float(player_state.get('positionQty', 0))
            obs[14] = float(player_state.get('avgCost', 0))
            if obs[14] > 0:
                obs[15] = (obs[1] / obs[14] - 1) * 100  # unrealized_pnl_pct
        
        # === MARKET CONTEXT (16-19) ===
        leaderboard = game_state.get('leaderboard', [])
        obs[16] = float(sum(1 for p in leaderboard if p.get('hasActiveTrades')))
        obs[17] = float(sum(p.get('totalInvested', 0) for p in leaderboard))
        obs[18] = float(self._count_recent_trades(obs[0]))
        
        rugpool = game_state.get('rugpool', {})
        threshold = rugpool.get('threshold', 10)
        obs[19] = rugpool.get('rugpoolAmount', 0) / threshold if threshold > 0 else 0
        
        # === SESSION CONTEXT (20-24) ===
        obs[20] = float(game_state.get('averageMultiplier', 0))
        obs[21] = float(game_state.get('count2x', 0))
        obs[22] = float(game_state.get('count10x', 0))
        obs[23] = float(game_state.get('count50x', 0))
        obs[24] = float(game_state.get('highestToday', 0))
        
        # === SIDEBET STATE (25-27) ===
        if sidebet_state:
            obs[25] = 1.0  # active
            obs[26] = float(sidebet_state.get('startTick', 0))
            obs[27] = float(sidebet_state.get('endTick', 0))
        
        return obs
    
    def _calc_volatility(self, window: int) -> float:
        if len(self.price_history) < window:
            return 0.0
        returns = np.diff(self.price_history[-window:])
        return float(np.std(returns))
    
    def _calc_momentum(self, window: int) -> float:
        if len(self.price_history) < window:
            return 0.0
        return (self.price_history[-1] - self.price_history[-window]) / window
    
    def _count_recent_trades(self, current_tick: int, window: int = 10) -> int:
        """Count trades in last `window` ticks."""
        cutoff = current_tick - window
        return sum(1 for ts in self.trade_timestamps if ts > cutoff)
```

---

## 5. Reward Function Design

### 5.1 Reward Structure

```python
def calculate_reward(
    action: int,
    state_before: np.ndarray,
    state_after: np.ndarray,
    game_outcome: str,  # "active", "rugged", "won", "lost"
) -> float:
    """
    Calculate step reward for sidebet timing.
    
    Reward components:
    1. Win: +payout (5x bet = +0.004 SOL for 0.001 bet)
    2. Loss: -bet amount (-0.001 SOL)
    3. Timing penalty: Small negative for holding too long
    4. Opportunity cost: Penalty for missing optimal windows
    """
    
    BET_AMOUNT = 0.001  # Standard sidebet size
    PAYOUT_MULTIPLIER = 5
    
    reward = 0.0
    
    if action == 1:  # PLACE_5X
        if game_outcome == "won":
            # Sidebet won (rug in 40 ticks)
            profit = BET_AMOUNT * (PAYOUT_MULTIPLIER - 1)
            reward = profit * 100  # Scale for learning (0.4)
            
            # Bonus for optimal timing (tick 200-500 has higher win rate)
            tick = int(state_before[0])
            if 200 <= tick <= 500:
                reward += 0.1
                
        elif game_outcome == "lost":
            # Sidebet lost (no rug in 40 ticks)
            reward = -BET_AMOUNT * 100  # (-0.1)
            
    else:  # HOLD
        # Small time penalty to encourage action
        tick = int(state_before[0])
        if tick > 138:  # Past median rug point
            reward = -0.01 * (tick - 138) / 100  # Escalating penalty
            
    return reward
```

### 5.2 Reward Shaping (Optional)

```python
def shaped_reward(base_reward: float, features: np.ndarray) -> float:
    """
    Apply potential-based reward shaping to guide exploration.
    
    Potential function: Φ(s) based on Bayesian rug probability.
    """
    # Extract Bayesian features
    age = features[6]
    ticks_since_peak = features[8]
    distance_from_peak = features[7]
    volatility_10 = features[10]
    
    # Simplified Bayesian potential (higher = more likely to rug soon)
    potential = 0.0
    
    if ticks_since_peak > 20:
        potential += 0.3
    if distance_from_peak > 0.3:
        potential += 0.2
    if volatility_10 > 0.1:
        potential += 0.2
    if age > 138:  # Past median
        potential += 0.3
        
    # Potential-based shaping: R' = R + γΦ(s') - Φ(s)
    # For simplicity, use potential directly as bonus
    shaped = base_reward + potential * 0.1
    
    return shaped
```

---

## 6. Episode Structure

### 6.1 Episode Definition

**Episode Boundary**: One complete game cycle (COOLDOWN → PRESALE → ACTIVE → RUGGED).

```python
class SidebetTimingEnv(gym.Env):
    def __init__(self):
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(28,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(2)
        
        self.max_steps_per_episode = 2000  # Max ticks per game
        
    def reset(self, seed=None, options=None):
        """
        Reset at game start (PRESALE phase).
        
        Returns:
            observation: Initial state (all zeros except session stats)
            info: Metadata
        """
        super().reset(seed=seed)
        self.step_count = 0
        self.obs_builder.reset()
        
        # Wait for game to start (active=True)
        obs = self._wait_for_game_start()
        
        info = {
            "game_id": self.current_game_id,
            "phase": "PRESALE",
        }
        
        return obs, info
    
    def step(self, action: int):
        """
        Execute one step (one tick).
        
        Returns:
            observation: Next state
            reward: Step reward
            terminated: Game rugged
            truncated: Max steps exceeded
            info: Metadata
        """
        self.step_count += 1
        
        # Execute action (if PLACE_5X, send requestSidebet)
        if action == 1:
            self._place_sidebet()
        
        # Wait for next tick
        obs_next = self._wait_for_next_tick()
        
        # Check termination
        terminated = self._is_rugged()
        truncated = self.step_count >= self.max_steps_per_episode
        
        # Calculate reward
        game_outcome = self._determine_outcome()
        reward = calculate_reward(action, self.obs_prev, obs_next, game_outcome)
        
        info = {
            "tick": int(obs_next[0]),
            "price": float(obs_next[1]),
            "sidebet_active": bool(obs_next[25]),
            "outcome": game_outcome,
        }
        
        self.obs_prev = obs_next
        
        return obs_next, reward, terminated, truncated, info
```

### 6.2 Termination Conditions

| Condition | Type | Reason |
|-----------|------|--------|
| `rugged=True` | Terminated | Game ended |
| `tick >= 2000` | Truncated | Safety limit |
| `connection_lost` | Truncated | Network error |

### 6.3 Episode Length Statistics

From analysis of 568 games:
- **Median**: 150 ticks
- **Mean**: 267 ticks
- **Range**: 2-1815 ticks
- **50th percentile**: Rug by tick 138

---

## 7. Temporal Context (Lookback Windows)

### 7.1 Implemented Lookbacks

| Feature | Window | Purpose |
|---------|--------|---------|
| `volatility_5` | 5 ticks | Short-term instability |
| `volatility_10` | 10 ticks | Medium-term instability |
| `momentum_3` | 3 ticks | Recent trend |
| `momentum_5` | 5 ticks | Broader trend |
| `recent_trade_count` | 10 ticks | Market activity |

### 7.2 Price History Buffer

```python
class PriceHistoryBuffer:
    """Rolling buffer for price history."""
    
    def __init__(self, max_len: int = 100):
        self.max_len = max_len
        self.prices = []
        
    def append(self, price: float):
        self.prices.append(price)
        if len(self.prices) > self.max_len:
            self.prices.pop(0)
            
    def get_window(self, window: int) -> List[float]:
        """Get last N prices."""
        return self.prices[-window:] if len(self.prices) >= window else self.prices
```

---

## 8. Normalization Strategy

### 8.1 Feature Scaling

| Feature Type | Method | Range |
|--------------|--------|-------|
| Tick counts | Min-max | [0, 1] |
| Prices | Log-scale + standardize | ℝ |
| Volatility | Standardize (running) | ℝ |
| Momentum | Clip + standardize | [-3, 3] |
| Counts | Log(1+x) | [0, ∞) |
| Ratios | Identity | [0, 1] |
| Booleans | Identity | {0, 1} |

### 8.2 Running Statistics

```python
class RunningNormalizer:
    """Online normalization with running mean/std."""
    
    def __init__(self, shape: tuple):
        self.mean = np.zeros(shape)
        self.var = np.ones(shape)
        self.count = 0
        
    def update(self, x: np.ndarray):
        """Update running statistics."""
        batch_mean = np.mean(x, axis=0)
        batch_var = np.var(x, axis=0)
        batch_count = x.shape[0]
        
        delta = batch_mean - self.mean
        total_count = self.count + batch_count
        
        self.mean = self.mean + delta * batch_count / total_count
        self.var = (
            self.var * self.count +
            batch_var * batch_count +
            delta ** 2 * self.count * batch_count / total_count
        ) / total_count
        self.count = total_count
        
    def normalize(self, x: np.ndarray) -> np.ndarray:
        """Normalize observation."""
        return (x - self.mean) / (np.sqrt(self.var) + 1e-8)
```

---

## 9. Training Configuration

### 9.1 Stable-Baselines3 Setup

```python
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

# Create environment
env = SidebetTimingEnv()
env = DummyVecEnv([lambda: env])
env = VecNormalize(env, norm_obs=True, norm_reward=True)

# PPO hyperparameters (based on best practices)
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
    ent_coef=0.01,  # Encourage exploration
    verbose=1,
    tensorboard_log="./tensorboard/",
)

# Train
model.learn(total_timesteps=1_000_000)
```

### 9.2 Network Architecture

```python
policy_kwargs = dict(
    net_arch=dict(
        pi=[128, 128, 64],  # Actor (policy) network
        vf=[128, 128, 64],  # Critic (value) network
    ),
    activation_fn=torch.nn.ReLU,
)

model = PPO(
    "MlpPolicy",
    env,
    policy_kwargs=policy_kwargs,
    # ... other params
)
```

---

## 10. Evaluation Metrics

### 10.1 Performance Metrics

| Metric | Target | Formula |
|--------|--------|---------|
| Win Rate | >20% | Wins / Total Bets |
| Expected Value | >0 | Avg(profit per bet) |
| Kelly Criterion | Aligned | `(p*b - q) / b` |
| Sharpe Ratio | >1.0 | `mean(returns) / std(returns)` |
| Max Drawdown | <20% | Max cumulative loss |

### 10.2 Timing Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Avg placement tick | 200-500 | Optimal window |
| Early placement rate | <10% | Before tick 100 |
| Late placement rate | <5% | After tick 600 |
| Placement frequency | 30-50% | Games with bet |

### 10.3 Bayesian Alignment

Compare RL agent's decisions with Bayesian model predictions:

```python
def evaluate_bayesian_alignment(
    rl_actions: List[int],
    bayesian_probs: List[float],
    threshold: float = 0.20
):
    """
    Measure how well RL agent aligns with Bayesian predictions.
    
    Args:
        rl_actions: 1 if agent placed bet, 0 otherwise
        bayesian_probs: P(rug in 40 ticks) from Bayesian model
        threshold: Breakeven probability (20% for 5x)
    
    Returns:
        Alignment score (0-1)
    """
    bayesian_actions = [1 if p > threshold else 0 for p in bayesian_probs]
    agreement = sum(a == b for a, b in zip(rl_actions, bayesian_actions))
    return agreement / len(rl_actions)
```

---

## 11. Data Pipeline

### 11.1 Training Data Sources

| Source | Format | Usage |
|--------|--------|-------|
| Live captures | Parquet (EventStore) | Online learning |
| Historical games | `complete_game` doc_type | Replay |
| Bayesian features | Precomputed | Feature validation |

### 11.2 Replay Buffer

```python
from collections import deque

class SidebetReplayBuffer:
    """Store (s, a, r, s', done) tuples for off-policy learning."""
    
    def __init__(self, capacity: int = 100_000):
        self.buffer = deque(maxlen=capacity)
        
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
        
    def sample(self, batch_size: int):
        indices = np.random.choice(len(self.buffer), batch_size)
        batch = [self.buffer[i] for i in indices]
        
        states = np.array([b[0] for b in batch])
        actions = np.array([b[1] for b in batch])
        rewards = np.array([b[2] for b in batch])
        next_states = np.array([b[3] for b in batch])
        dones = np.array([b[4] for b in batch])
        
        return states, actions, rewards, next_states, dones
```

---

## 12. Implementation Checklist

- [ ] Implement `SidebetObservationBuilder` class
- [ ] Add `PriceHistoryBuffer` for lookback windows
- [ ] Implement `SidebetTimingEnv(gym.Env)`
- [ ] Add `RunningNormalizer` for online standardization
- [ ] Create `calculate_reward()` function
- [ ] Implement Bayesian potential shaping (optional)
- [ ] Write unit tests for observation builder
- [ ] Integration test with live `gameStateUpdate` stream
- [ ] Validate feature ranges on historical data
- [ ] Train baseline PPO model
- [ ] Evaluate vs. Bayesian model
- [ ] Hyperparameter tuning
- [ ] Deployment to live environment

---

## 13. File Locations

| Component | File Path |
|-----------|-----------|
| Environment | `src/rl/envs/sidebet_timing_env.py` |
| Observation Builder | `src/rl/observation/sidebet_builder.py` |
| Reward Function | `src/rl/rewards/sidebet_reward.py` |
| Training Script | `scripts/train_sidebet_rl.py` |
| Evaluation Script | `scripts/evaluate_sidebet_model.py` |
| Bayesian Baseline | `/home/devops/Desktop/JUPYTER-CENTRAL-FOLDER/bayesian_sidebet_analysis.py` |

---

## 14. Related Documents

- `/home/devops/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md` - Protocol reference
- `/home/devops/Desktop/VECTRA-PLAYER/docs/rag/knowledge/rl-design/action-space-design.md` - General action space
- `/home/devops/Desktop/VECTRA-PLAYER/docs/rag/knowledge/rl-design/implementation-plan.md` - Pipeline design
- `/home/devops/Desktop/JUPYTER-CENTRAL-FOLDER/bayesian_sidebet_analysis.py` - Bayesian baseline

---

## 15. Success Criteria

| Metric | Threshold | Status |
|--------|-----------|--------|
| Win rate (validation) | >20% | TBD |
| Positive EV | >0 SOL/bet | TBD |
| Bayesian alignment | >70% | TBD |
| Training convergence | <100k steps | TBD |
| Live performance (100 bets) | Profit | TBD |

---

**Author**: Claude Code (Sonnet 4.5)
**Date**: 2026-01-07
**Version**: 1.0
**Status**: Ready for Implementation
