# Sidebet RL - Feature Quick Reference

**Companion to:** `sidebet-observation-space-design.md`

---

## Feature Vector Layout (28 dimensions)

```
┌─────────────────────────────────────────────────────────────────┐
│  INDEX │ FEATURE                │ CATEGORY       │ SOURCE       │
├─────────────────────────────────────────────────────────────────┤
│  0-5   │ Game State (Raw)       │ Direct         │ gameStateUpdate
│  6-12  │ Price Features         │ Derived        │ partialPrices
│  13-15 │ Position Context       │ Direct         │ playerUpdate
│  16-19 │ Market Context         │ Derived        │ leaderboard
│  20-24 │ Session Context        │ Direct         │ gameStateUpdate
│  25-27 │ Sidebet State          │ Direct         │ currentSidebet
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Details Table

| Index | Name | Type | Range | Derivation | Priority |
|-------|------|------|-------|------------|----------|
| **0** | tick | int | [0, 2000] | `tickCount` | P0 |
| **1** | price | float | [0.02, 1000+] | `price` | P0 |
| **2** | active | bool | {0, 1} | `active` | P0 |
| **3** | cooldown_timer_ms | int | [0, 30000] | `cooldownTimer` | P1 |
| **4** | allow_pre_round_buys | bool | {0, 1} | `allowPreRoundBuys` | P1 |
| **5** | connected_players | int | [0, 500] | `connectedPlayers` | P2 |
| **6** | age | int | [0, 2000] | tick | P0 |
| **7** | distance_from_peak | float | [0, 1] | `(peak-curr)/peak` | P0 |
| **8** | ticks_since_peak | int | [0, 2000] | `tick - peak_tick` | P0 |
| **9** | volatility_5 | float | [0, ∞] | `std(Δprice[-5:])` | P0 |
| **10** | volatility_10 | float | [0, ∞] | `std(Δprice[-10:])` | P0 |
| **11** | momentum_3 | float | [-∞, ∞] | `(p-p[-3])/3` | P0 |
| **12** | momentum_5 | float | [-∞, ∞] | `(p-p[-5])/5` | P0 |
| **13** | position_qty | float | [0, ∞] | `positionQty` | P1 |
| **14** | avg_cost | float | [0, ∞] | `avgCost` | P1 |
| **15** | unrealized_pnl_pct | float | [-100, ∞] | `(p/avg-1)*100` | P1 |
| **16** | players_with_positions | int | [0, 500] | Count active | P1 |
| **17** | total_market_capital | float | [0, ∞] | Sum invested | P2 |
| **18** | recent_trade_count | int | [0, 100+] | Trades in 10 ticks | P1 |
| **19** | rugpool_ratio | float | [0, 1+] | `amount/threshold` | P1 |
| **20** | average_multiplier | float | [0, 100+] | `averageMultiplier` | P2 |
| **21** | count_2x | int | [0, ∞] | `count2x` | P2 |
| **22** | count_10x | int | [0, ∞] | `count10x` | P2 |
| **23** | count_50x | int | [0, ∞] | `count50x` | P2 |
| **24** | highest_today | float | [0, 1000+] | `highestToday` | P2 |
| **25** | sidebet_active | bool | {0, 1} | Active flag | P0 |
| **26** | sidebet_start_tick | int | [0, 2000] | `startTick` | P0 |
| **27** | sidebet_end_tick | int | [0, 2000] | `endTick` | P0 |

---

## Priority Legend

- **P0**: Critical for Bayesian predictions (top 5 features)
- **P1**: Important for game context
- **P2**: Auxiliary / meta-game features

---

## Bayesian Feature Importance (Empirical)

From analysis of 568 games, ranked by information gain:

| Rank | Feature | Info Gain | Description |
|------|---------|-----------|-------------|
| 1 | `ticks_since_peak` [8] | HIGH | Time since max price |
| 2 | `distance_from_peak` [7] | HIGH | % below peak |
| 3 | `volatility_10` [10] | MEDIUM | Medium-term instability |
| 4 | `age` [6] | MEDIUM | Game duration |
| 5 | `momentum_5` [12] | MEDIUM | Price trend |

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────┐
│               WebSocket Events (Socket.IO)                │
└──────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ gameState    │  │ playerUpdate │  │ currentSide  │
│ Update       │  │              │  │ bet          │
└──────────────┘  └──────────────┘  └──────────────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
        ┌─────────────────────────────────────┐
        │  SidebetObservationBuilder          │
        │  - Extract raw features             │
        │  - Calculate derived features       │
        │  - Maintain price history           │
        └─────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │  28-Dimensional Observation Vector  │
        │  [tick, price, ..., sidebet_end]    │
        └─────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │  RunningNormalizer                  │
        │  - Online standardization           │
        │  - Clip outliers                    │
        └─────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │  RL Agent (PPO/DQN/etc.)            │
        │  - Policy network: π(a|s)           │
        │  - Value network: V(s)              │
        └─────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────┐
        │  Action: HOLD [0] or PLACE_5X [1]   │
        └─────────────────────────────────────┘
```

---

## Observation Space Code

```python
# Minimal working example
from gymnasium import spaces
import numpy as np

observation_space = spaces.Box(
    low=-np.inf,
    high=np.inf,
    shape=(28,),
    dtype=np.float32
)

# Example observation
obs = np.array([
    # Game state (0-5)
    250.0,      # tick
    1.523,      # price
    1.0,        # active
    0.0,        # cooldown_timer_ms
    0.0,        # allow_pre_round_buys
    145.0,      # connected_players

    # Price features (6-12)
    250.0,      # age
    0.23,       # distance_from_peak
    45.0,       # ticks_since_peak
    0.087,      # volatility_5
    0.112,      # volatility_10
    -0.012,     # momentum_3
    -0.008,     # momentum_5

    # Position (13-15)
    0.0,        # position_qty (none)
    0.0,        # avg_cost
    0.0,        # unrealized_pnl_pct

    # Market (16-19)
    67.0,       # players_with_positions
    12.456,     # total_market_capital
    8.0,        # recent_trade_count
    0.65,       # rugpool_ratio

    # Session (20-24)
    6.45,       # average_multiplier
    1245.0,     # count_2x
    87.0,       # count_10x
    12.0,       # count_50x
    124.5,      # highest_today

    # Sidebet (25-27)
    0.0,        # sidebet_active (none)
    0.0,        # sidebet_start_tick
    0.0,        # sidebet_end_tick
], dtype=np.float32)

assert obs.shape == (28,)
```

---

## Action Space Code

```python
from gymnasium import spaces

action_space = spaces.Discrete(2)

# Action mapping
ACTIONS = {
    0: "HOLD",       # Do nothing
    1: "PLACE_5X",   # Place 5x sidebet
}

# Example usage
action = 1  # Agent decides to place bet
action_name = ACTIONS[action]  # "PLACE_5X"
```

---

## Feature Extraction Examples

### Example 1: Peak Tracking

```python
# Price history
prices = [1.0, 1.2, 1.5, 1.8, 1.6, 1.4, 1.3]
current_tick = 6
current_price = 1.3

# Find peak
peak_price = max(prices)  # 1.8
peak_tick = prices.index(peak_price)  # 3

# Calculate features
distance_from_peak = (peak_price - current_price) / peak_price  # 0.278
ticks_since_peak = current_tick - peak_tick  # 3

# obs[7] = 0.278
# obs[8] = 3.0
```

### Example 2: Volatility

```python
import numpy as np

# Last 10 prices
prices = [1.0, 1.1, 1.05, 1.2, 1.15, 1.3, 1.25, 1.4, 1.35, 1.5]

# Price changes (returns)
returns = np.diff(prices)  # [0.1, -0.05, 0.15, -0.05, 0.15, -0.05, 0.15, -0.05, 0.15]

# Volatility (std dev)
volatility_10 = np.std(returns)  # 0.0943

# obs[10] = 0.0943
```

### Example 3: Momentum

```python
# Current price: 1.5
# Price 5 ticks ago: 1.3

momentum_5 = (1.5 - 1.3) / 5  # 0.04

# obs[12] = 0.04
```

---

## Normalization Examples

### Min-Max Scaling (Tick)

```python
# Observed range: [0, 2000]
tick = 250

tick_normalized = tick / 2000  # 0.125
```

### Standardization (Volatility)

```python
# Running statistics
mean_vol = 0.08
std_vol = 0.03

# Current observation
vol = 0.12

vol_normalized = (vol - mean_vol) / std_vol  # 1.333
```

---

## References

- Main Design: `/home/devops/Desktop/VECTRA-PLAYER/docs/rag/knowledge/rl-design/sidebet-observation-space-design.md`
- Protocol Spec: `/home/devops/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`
- Bayesian Analysis: `/home/devops/Desktop/JUPYTER-CENTRAL-FOLDER/bayesian_sidebet_analysis.py`

---

**Last Updated**: 2026-01-07
