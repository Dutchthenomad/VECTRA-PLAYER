# Sidebet Optimization - Quick Reference

## TL;DR: The Strategy

**PLACE SIDEBET when**:
- Game age > 200 ticks
- P(rug in 40 ticks) > 20%
- High volatility OR distance from peak > 30%

**BET SIZE**: 1-2% of bankroll (conservative Kelly)

**EXPECTED PERFORMANCE**: ~Break-even at current skill level, positive EV with refinement

---

## Code Snippets

### Quick Analysis

```python
from bayesian_sidebet_analysis import *

# Load data
games_df = load_game_data()
training_df = create_training_dataset(games_df)

# Fit model
model = BayesianSurvivalModel(games_df)

# Predict at tick 250
p_win = model.predict_rug_probability(tick=250, window=40)
ev = expected_value(p_win, payout_multiplier=5)

print(f"P(win): {p_win:.1%}, EV: {ev:.6f} SOL")
```

### Live Decision Logic

```python
def should_place_sidebet(current_tick, prices, model):
    """Decision logic for live trading."""
    # Extract features
    features = extract_features(prices, current_tick)
    
    # Predict probability
    p_win = model.predict_rug_probability(
        current_tick, 
        window=40, 
        features=features
    )
    
    # Decision rules
    if current_tick < 200:
        return False, 0.0  # Too early
    
    if p_win < breakeven_probability(5):
        return False, 0.0  # Negative EV
    
    # Calculate bet size (1/4 Kelly)
    kelly_frac = kelly_criterion(p_win, 5) / 4
    
    return True, kelly_frac
```

### Feature Extraction

```python
features = extract_features(prices, tick=250)

# Key features:
# - age: Ticks since start
# - volatility_10: 10-tick rolling volatility
# - ticks_since_peak: Time since peak price
# - distance_from_peak: % below peak
# - rapid_fall: Price dropped >20% in last 3 ticks
```

### Conditional Probability

```python
# P(rug | game age 200-300)
p_rug = conditional_rug_probability(
    training_df,
    {'age': (200, 300)}
)

# P(rug | high volatility)
p_rug = conditional_rug_probability(
    training_df,
    {'volatility_10': (0.1, 1.0)}
)
```

---

## Key Formulas

### Expected Value

```
EV = Bet × [P(win) × (Multiplier + 1) - 1]

For 5x payout:
  EV = 0.001 × [P(win) × 6 - 1]
  
Positive EV when P(win) > 16.67%
```

### Kelly Criterion

```
f* = (p × b - q) / b

where:
  p = P(win)
  q = 1 - p
  b = Multiplier - 1

Example (P(win) = 25%, 5x payout):
  f* = (0.25 × 4 - 0.75) / 4 = 0.0625 (6.25%)
```

### Survival Function

```
S(t) = P(game survives past tick t)
     = exp(-∫[0,t] h(u) du)

where h(t) = hazard rate at tick t
```

### Information Gain

```
IG(Y, X) = H(Y) - H(Y | X)
         = Entropy(target) - Conditional_Entropy(target | feature)
```

---

## Breakeven Thresholds

| Payout Multiplier | Breakeven P(win) | Current Win Rate | Status |
|-------------------|------------------|------------------|--------|
| 5x | 16.67% | 17.4% overall | Slightly positive |
| 5x | 16.67% | 19.9% (late) | Nearly optimal |
| 10x | 9.09% | TBD | Higher variance |
| 20x | 4.76% | TBD | Very high variance |

---

## Feature Importance (Top 5)

1. **age**: Game age in ticks (strong predictor)
2. **ticks_since_peak**: Time since peak price
3. **distance_from_peak**: % below peak
4. **volatility_10**: 10-tick rolling volatility
5. **momentum_5**: 5-tick price momentum

---

## Bayesian Adjustment Factors

| Condition | Multiplier | Reasoning |
|-----------|------------|-----------|
| rapid_fall = True | 2.0x | Strong rug signal |
| volatility_10 > 0.1 | 1.5x | Instability |
| ticks_since_peak > 20 | 1.3x | Mean reversion |
| distance_from_peak > 0.3 | 1.2x | Far from peak |
| rapid_rise = True | 0.7x | Momentum (reduces rug risk) |

---

## Historical Performance

### Win Rates by Game Age

```
Ticks   0-100:  14.2% (negative EV)
Ticks 100-200:  16.1% (slightly negative)
Ticks 200-300:  19.8% (near break-even)
Ticks 300-500:  20.3% (positive EV)
```

**Takeaway**: Wait until tick 200+ for best results

---

## Common Pitfalls

1. **Betting too early**: Win rate < 15% for ticks < 100
2. **Ignoring volatility**: High volatility increases rug probability
3. **Chasing momentum**: Rapid rise suggests continued pump (lower rug risk)
4. **Over-betting**: Use conservative Kelly (1/4 or 1/2)
5. **Ignoring bankroll**: Always bet a fixed % of current balance

---

## Visualization Guide

| File | Shows |
|------|-------|
| `survival_functions.png` | Hazard rate and survival function |
| `ev_by_tick.png` | Expected value evolution by game age |
| `conditional_probability_heatmap.png` | P(rug) by age and price |
| `feature_importance.png` | Which features matter most |
| `optimal_sidebet_timing.png` | Example of optimal entry point |
| `kelly_criterion.png` | Bet sizing by win probability |

---

## Next Steps

### For Analysis

1. Run `python bayesian_sidebet_analysis.py` for quick test
2. Open Jupyter notebook for full analysis
3. Review visualizations in `~/rugs_data/analysis/`

### For RL Integration

1. Use features from `extract_features()` as observation space
2. Actions: HOLD, PLACE_5X, PLACE_10X
3. Reward: Actual payout - bet amount
4. Train with PPO or DQN on historical games
5. Fine-tune with live data

### For Live Trading

1. Capture real-time price data via WebSocket
2. Extract features at each tick
3. Query survival model for P(rug in 40 ticks)
4. Apply decision logic (see code above)
5. Place sidebet if EV > 0 and age > 200

---

## Files Overview

```
notebooks/
├── bayesian_sidebet_analysis.py    # Core analysis functions
├── sidebet_optimization.ipynb      # Interactive Jupyter notebook
├── README.md                        # Full documentation
├── PROBABILISTIC_REASONING.md      # Mathematical details
└── QUICK_REFERENCE.md              # This file
```

---

## WebSocket Integration

### Key Events

From `WEBSOCKET_EVENTS_SPEC.md`:

**gameStateUpdate** (P0):
- `price`: Current multiplier
- `tickCount`: Game age
- `active`: Is game running?
- `rugged`: Has game ended?

**gameHistory[]** (P0):
- `prices[]`: Tick-by-tick price data (CRITICAL)
- `globalSidebets[]`: All sidebets in game
- `peakMultiplier`: Peak price

### Real-Time Feature Extraction

```python
# From live WebSocket stream
current_tick = event['tickCount']
prices = []  # Accumulated price history

# Update each tick
if event['event'] == 'gameStateUpdate':
    prices.append(event['price'])
    
    # Extract features
    features = extract_features(prices, current_tick)
    
    # Predict
    p_win = model.predict_rug_probability(current_tick, 40, features)
    
    # Decide
    should_bet, bet_size = should_place_sidebet(current_tick, prices, model)
```

---

**Last Updated**: January 7, 2026  
**Version**: 1.0.0  
**Author**: rugs-expert (Claude Code Agent)
