# Sidebet v1 Observation Space (15 Features)

**Date:** January 10, 2026
**Status:** APPROVED - Ready for Implementation
**Complexity:** Bayesian (Option B)

---

## Design Principles

1. **No future information leakage** - All features from current/past data only
2. **Aligned with Bayesian predictors** - Top empirical predictors included
3. **Minimal for v1** - 15 features vs 28 in full design
4. **Real-world replication** - Model sees exactly what human player sees

---

## Feature Specification

| Index | Feature | Type | Range | Source | Computation |
|-------|---------|------|-------|--------|-------------|
| **Game State (4)** |||||
| 0 | `tick` | int | [0, 2000] | `tickCount` | Direct |
| 1 | `price` | float | [0.02, 100+] | `price` | Direct |
| 2 | `active` | bool | {0, 1} | `active` | Direct |
| 3 | `connected_players` | int | [0, 500] | `connectedPlayers` | Direct |
| **Bayesian Predictors (7)** |||||
| 4 | `running_peak` | float | [1.0, 100+] | Derived | `max(price_history)` |
| 5 | `peak_tick` | int | [0, 2000] | Derived | `argmax(price_history)` |
| 6 | `distance_from_peak` | float | [0, 1] | Derived | `(peak - price) / peak` |
| 7 | `ticks_since_peak` | int | [0, 2000] | Derived | `tick - peak_tick` |
| 8 | `volatility_10` | float | [0, inf] | Derived | `std(price_changes[-10:])` |
| 9 | `momentum_5` | float | [-inf, inf] | Derived | `(price - price[-5]) / 5` |
| 10 | `price_velocity` | float | [-inf, inf] | Derived | `price - price[-1]` |
| **Sidebet State (3)** |||||
| 11 | `sidebet_active` | bool | {0, 1} | `currentSidebet` | Direct |
| 12 | `sidebet_ticks_remaining` | int | [0, 40] | Derived | `end_tick - tick` if active |
| 13 | `can_place_bet` | bool | {0, 1} | Derived | `active AND NOT sidebet_active` |
| **Game Context (1)** |||||
| 14 | `game_in_optimal_zone` | bool | {0, 1} | Derived | `tick >= 200` |

---

## Peak Calculation (No Future Leakage)

The "peak" is the **running maximum** of prices seen so far, NOT the true game peak.

```python
# During live game at tick N:
running_peak = max(prices[0:N])  # Max of all prices seen so far
peak_tick = prices.index(running_peak)  # When it occurred

# Derived features:
distance_from_peak = (running_peak - current_price) / running_peak
ticks_since_peak = current_tick - peak_tick
```

### Example Progression

| Tick | Price | Running Peak | Peak Tick | Distance | Ticks Since |
|------|-------|--------------|-----------|----------|-------------|
| 0 | 1.00 | 1.00 | 0 | 0.0% | 0 |
| 10 | 1.50 | 1.50 | 10 | 0.0% | 0 |
| 20 | 2.00 | 2.00 | 20 | 0.0% | 0 |
| 30 | 1.80 | 2.00 | 20 | 10.0% | 10 |
| 40 | 1.50 | 2.00 | 20 | 25.0% | 20 |
| 50 | 2.50 | 2.50 | 50 | 0.0% | 0 |
| 60 | 2.00 | 2.50 | 50 | 20.0% | 10 |

**Key insight:** When `ticks_since_peak` > 20 and `distance_from_peak` > 0.2, rug probability increases.

---

## Implementation

```python
import numpy as np
from typing import List, Dict, Optional
from gymnasium import spaces

class SidebetV1ObservationBuilder:
    """
    Build 15-dimensional observation vector for Sidebet v1.

    Design principles:
    - No future information leakage
    - All features computable from current/past data
    - Aligned with Bayesian predictors
    """

    def __init__(self):
        self.price_history: List[float] = []
        self.reset()

    @property
    def observation_space(self) -> spaces.Box:
        return spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(15,),
            dtype=np.float32
        )

    def reset(self):
        """Reset for new game."""
        self.price_history = []

    def build(
        self,
        game_state: Dict,
        sidebet_state: Optional[Dict] = None
    ) -> np.ndarray:
        """
        Build observation from current game state.

        Args:
            game_state: From gameStateUpdate event
            sidebet_state: From currentSidebet (if any)

        Returns:
            15-dimensional float32 array
        """
        obs = np.zeros(15, dtype=np.float32)

        # === GAME STATE (0-3) ===
        tick = game_state.get('tickCount', 0)
        price = game_state.get('price', 1.0)
        active = game_state.get('active', False)

        obs[0] = float(tick)
        obs[1] = float(price)
        obs[2] = float(active)
        obs[3] = float(game_state.get('connectedPlayers', 0))

        # Update price history
        self.price_history.append(price)

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
        if sidebet_state and sidebet_state.get('active'):
            obs[11] = 1.0
            end_tick = sidebet_state.get('endTick', tick + 40)
            obs[12] = float(max(0, end_tick - tick))

        obs[13] = float(active and obs[11] == 0)  # can_place_bet

        # === GAME CONTEXT (14) ===
        obs[14] = float(tick >= 200)  # in optimal zone

        return obs

    def _calc_volatility(self, window: int) -> float:
        """Standard deviation of price changes over window."""
        if len(self.price_history) < window + 1:
            return 0.0
        changes = np.diff(self.price_history[-window-1:])
        return float(np.std(changes))

    def _calc_momentum(self, window: int) -> float:
        """Average price change per tick over window."""
        if len(self.price_history) < window + 1:
            return 0.0
        return (self.price_history[-1] - self.price_history[-window-1]) / window

    def _calc_velocity(self) -> float:
        """Instantaneous price change (last tick)."""
        if len(self.price_history) < 2:
            return 0.0
        return self.price_history[-1] - self.price_history[-2]
```

---

## Normalization Strategy

| Feature | Method | Target Range | Notes |
|---------|--------|--------------|-------|
| `tick` | Divide by 500 | [0, 4] | Most games < 500 |
| `price` | Log scale | [-4, 5] | Handles wide range |
| `connected_players` | Divide by 200 | [0, 2.5] | Typical 50-200 |
| `running_peak` | Log scale | [-4, 5] | Same as price |
| `peak_tick` | Divide by 500 | [0, 4] | Same as tick |
| `distance_from_peak` | Identity | [0, 1] | Already normalized |
| `ticks_since_peak` | Divide by 100 | [0, 20] | Meaningful range |
| `volatility_10` | Clip [0, 1] | [0, 1] | Rare > 1 |
| `momentum_5` | Clip [-0.5, 0.5] | [-0.5, 0.5] | Typical range |
| `price_velocity` | Clip [-0.5, 0.5] | [-0.5, 0.5] | Typical range |
| Booleans | Identity | {0, 1} | Already binary |

**Recommendation:** Use `VecNormalize` from Stable-Baselines3 for automatic running normalization.

---

## Gymnasium Space Definition

```python
from gymnasium import spaces
import numpy as np

observation_space = spaces.Box(
    low=np.array([
        0,      # tick
        0.02,   # price (min)
        0,      # active
        0,      # connected_players
        1.0,    # running_peak (min)
        0,      # peak_tick
        0,      # distance_from_peak
        0,      # ticks_since_peak
        0,      # volatility_10
        -np.inf, # momentum_5
        -np.inf, # price_velocity
        0,      # sidebet_active
        0,      # sidebet_ticks_remaining
        0,      # can_place_bet
        0,      # game_in_optimal_zone
    ], dtype=np.float32),
    high=np.array([
        2000,   # tick
        np.inf, # price
        1,      # active
        500,    # connected_players
        np.inf, # running_peak
        2000,   # peak_tick
        1,      # distance_from_peak
        2000,   # ticks_since_peak
        np.inf, # volatility_10
        np.inf, # momentum_5
        np.inf, # price_velocity
        1,      # sidebet_active
        40,     # sidebet_ticks_remaining
        1,      # can_place_bet
        1,      # game_in_optimal_zone
    ], dtype=np.float32),
    shape=(15,),
    dtype=np.float32
)
```

---

## Validation Checklist

| Check | Status | Notes |
|-------|--------|-------|
| No future information | PASS | `running_peak` uses past prices only |
| All features observable | PASS | Direct from `gameStateUpdate` or derived |
| Bayesian predictors | PASS | Top 5 predictors included |
| Sidebet state tracked | PASS | Active, remaining, can_place |
| Optimal zone flagged | PASS | Aligns with reward function |
| Dimensionality | PASS | 15 features (manageable for v1) |

---

## Comparison to Full Design (28 Features)

| Category | v1 (15) | Full (28) | Excluded in v1 |
|----------|---------|-----------|----------------|
| Game State | 4 | 6 | cooldown_timer, allow_pre_round_buys |
| Price Features | 7 | 7 | None |
| Position Context | 0 | 3 | All (not needed for sidebets) |
| Market Context | 0 | 4 | All (complexity reduction) |
| Session Context | 0 | 5 | All (complexity reduction) |
| Sidebet State | 3 | 3 | None |
| Game Context | 1 | 0 | Added optimal_zone flag |

**Rationale:** Position and market context are more relevant for trading RL. Sidebet timing primarily depends on game age and price dynamics.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-10 | Initial 15-feature Bayesian design |

---

*Collaboratively designed: Human + Claude*
*Session: 2026-01-10*
