# Bayesian Sidebet Optimization Analysis

## Overview

This analysis suite provides probabilistic methods for optimizing sidebet placement timing in rugs.fun.

**Key Question**: WHEN should we place a sidebet to maximize expected value?

**Data**: 568 deduplicated games with complete tick-by-tick price histories

**Current Performance**:
- Overall win rate: 17.4% (below 20% breakeven for 5x payout)
- Late-game bets (tick 200-500): 19.9% win rate (nearly break-even)

## Files

| File | Purpose |
|------|---------|
| `bayesian_sidebet_analysis.py` | Core analysis functions and models |
| `sidebet_optimization.ipynb` | Interactive Jupyter notebook with full analysis |
| `README.md` | This file |

## Quick Start

### Option 1: Python Script (Quick Test)

```bash
cd /home/devops/Desktop/VECTRA-PLAYER
source .venv/bin/activate
python notebooks/bayesian_sidebet_analysis.py
```

This runs a quick analysis and prints summary statistics.

### Option 2: Jupyter Notebook (Full Analysis)

```bash
cd /home/devops/Desktop/VECTRA-PLAYER
source .venv/bin/activate
jupyter notebook notebooks/sidebet_optimization.ipynb
```

Then run all cells to generate visualizations and analysis.

## Analysis Components

### 1. Bayesian Survival Analysis

**Goal**: Model P(rug in next N ticks | game_age, features)

**Key Functions**:
```python
from bayesian_sidebet_analysis import BayesianSurvivalModel

model = BayesianSurvivalModel(games_df)
p_win = model.predict_rug_probability(current_tick=250, window=40)
```

**Outputs**:
- Hazard function h(t): Instantaneous rug risk at each tick
- Survival function S(t): P(game survives past tick t)
- Conditional predictions with feature adjustments

**Visualizations**:
- `survival_functions.png`: Hazard and survival curves
- `ev_by_tick.png`: Expected value evolution by game age

### 2. Feature Engineering

**Goal**: Extract predictive features from game state

**Key Features** (ranked by information gain):
1. `age`: Ticks since game start
2. `ticks_since_peak`: Time since peak price
3. `distance_from_peak`: % below peak
4. `volatility_10`: 10-tick rolling volatility
5. `momentum_5`: 5-tick price momentum

**Function**:
```python
features = extract_features(prices, tick=250)
# Returns GameFeatures dataclass with 16+ fields
```

### 3. Conditional Probability Analysis

**Goal**: P(rug | age, price, volatility, etc.)

**Key Functions**:
```python
# Single condition
p_rug = conditional_rug_probability(
    training_df,
    {'age': (200, 300), 'volatility_10': (0.1, 0.2)}
)

# Full matrix
prob_matrix = build_conditional_probability_matrix(training_df)
```

**Visualization**:
- `conditional_probability_heatmap.png`: P(rug | age, price) heatmap

### 4. Expected Value Optimization

**Goal**: Find optimal tick to maximize EV

**Key Functions**:
```python
# Calculate EV
ev = expected_value(p_win=0.25, payout_multiplier=5, bet_amount=0.001)

# Breakeven probability
breakeven = breakeven_probability(payout_multiplier=5)  # 16.67% for 5x

# Find optimal placement
optimal_tick, max_ev = find_optimal_tick(
    survival_model,
    prices,
    payout_multiplier=5
)
```

**Formula**:
```
EV = bet × [P(win) × (multiplier + 1) - 1]

For 5x payout:
  EV > 0 when P(win) > 1/6 = 16.67%
```

### 5. Kelly Criterion for Bet Sizing

**Goal**: Optimal fraction of bankroll to bet

**Function**:
```python
kelly_frac = kelly_criterion(p_win=0.25, payout_multiplier=5)
# Returns: 0.0625 (6.25% of bankroll)
```

**Practical Tip**: Use 1/4 Kelly for conservative sizing (reduces variance)

**Visualization**:
- `kelly_criterion.png`: Kelly fraction vs win probability

### 6. Feature Importance Analysis

**Goal**: Which features best predict rug timing?

**Method**: Information gain (entropy reduction)

**Function**:
```python
importance_df = rank_features_by_importance(training_df)
```

**Visualization**:
- `feature_importance.png`: Ranked bar chart

## Key Findings

### 1. Timing Matters

**Historical Win Rates by Age**:
- Ticks 0-100: ~14% (negative EV)
- Ticks 100-200: ~16% (slightly negative)
- Ticks 200-500: ~20% (break-even)

**Conclusion**: Wait until tick 200+ for positive EV

### 2. Breakeven Thresholds

| Payout | Breakeven P(win) | Current Win Rate | EV |
|--------|------------------|------------------|-----|
| 5x | 16.67% | 17.4% | Slightly positive |
| 10x | 9.09% | N/A | TBD |
| 20x | 4.76% | N/A | TBD |

### 3. High-Risk Indicators (Bayesian Adjustments)

**Features that increase rug probability**:
- `rapid_fall = True`: 2.0x multiplier
- `volatility_10 > 0.1`: 1.5x multiplier
- `ticks_since_peak > 20`: 1.3x multiplier
- `distance_from_peak > 0.3`: 1.2x multiplier

**Features that decrease rug probability**:
- `rapid_rise = True`: 0.7x multiplier (momentum)

### 4. Optimal Strategy

**PLACE SIDEBET when**:
- ✅ Game age > 200 ticks
- ✅ P(win) > 20% (from survival model)
- ✅ High volatility OR long time since peak

**AVOID SIDEBET when**:
- ❌ Game age < 100 ticks
- ❌ Rapid price rise (momentum)
- ❌ P(win) < 16%

**BET SIZING**:
- Use 1/4 Kelly criterion
- If P(win) = 25%, Kelly = 6.25% → Bet 1.5-2% of bankroll
- Conservative default: 0.001-0.002 SOL per bet

## RL Integration

### Observation Space

```python
obs = np.array([
    game_age,              # Ticks since start
    current_price,         # Current multiplier
    distance_from_peak,    # % below peak
    volatility_10,         # 10-tick volatility
    ticks_since_peak,      # Time since peak
    p_rug_40_ticks,        # From survival model
])
```

### Action Space

```python
actions = {
    0: HOLD,        # Don't place sidebet
    1: PLACE_5X,    # Place 5x sidebet
    2: PLACE_10X,   # Place 10x sidebet
}
```

### Reward Function

```python
if action == PLACE_5X:
    if rug_in_next_40_ticks:
        reward = +4 * bet_amount  # Won 5x payout
    else:
        reward = -1 * bet_amount  # Lost bet
else:
    reward = 0  # No action
```

### Training Approach

1. **Offline RL**: Train on 568 historical games using PPO/DQN
2. **Initialize Q-values**: Use expected values from this analysis
3. **Exploration**: ε-greedy or UCB for tick selection
4. **Position sizing**: Kelly criterion for bet amounts
5. **Live fine-tuning**: Update policy with real-time data

## WebSocket Fields Used

From `/home/devops/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`:

### gameStateUpdate (P0)

| Field | Usage |
|-------|-------|
| `price` | Current multiplier for features |
| `tickCount` | Game age calculation |
| `active` | Phase detection |
| `rugged` | Rug event detection |
| `gameHistory[]` | Historical game data source |

### gameHistory Entry

| Field | Usage |
|-------|-------|
| `prices[]` | Tick-by-tick price history (CRITICAL) |
| `globalSidebets[]` | Sidebet placement/payout data |
| `peakMultiplier` | Peak price for distance calculation |
| `rugged` | Confirm game completion |

### globalSidebets Entry

| Field | Usage |
|-------|-------|
| `startedAtTick` | Entry tick |
| `end` | Exit tick (startedAtTick + 40) |
| `betAmount` | Bet size |
| `xPayout` | Target multiplier (5x, 10x, etc.) |

## Output Files

All visualizations saved to `~/rugs_data/analysis/`:

```
~/rugs_data/analysis/
├── survival_functions.png           # Hazard and survival curves
├── ev_by_tick.png                   # EV evolution by game age
├── conditional_probability_heatmap.png  # P(rug | age, price)
├── feature_importance.png           # Information gain ranking
├── optimal_sidebet_timing.png       # Example game analysis
└── kelly_criterion.png              # Optimal bet sizing
```

## Dependencies

```
duckdb
pandas
numpy
scipy
matplotlib
seaborn
```

Install with:
```bash
pip install duckdb pandas numpy scipy matplotlib seaborn
```

## References

**Canonical Protocol Spec**:
- `/home/devops/Desktop/claude-flow/knowledge/rugs-events/WEBSOCKET_EVENTS_SPEC.md`

**Related Scripts**:
- `/home/devops/Desktop/VECTRA-PLAYER/scripts/export_for_julius.py`
- `/home/devops/Desktop/VECTRA-PLAYER/scripts/analyze_rug_mechanism.py`

**Data Source**:
- `~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet`

---

**Last Updated**: January 7, 2026
**Author**: rugs-expert (Claude Code Agent)
**Version**: 1.0.0
