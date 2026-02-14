# 17 - Survival Analysis

## Purpose

Statistical analysis of game duration and rug timing:
1. Hazard rate functions
2. Kaplan-Meier survival curves
3. Conditional probability matrices
4. Time-to-event modeling

## Dependencies

```python
import numpy as np
import pandas as pd
from scipy import stats
from lifelines import KaplanMeierFitter, CoxPHFitter
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Survival Analysis System                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Historical Game Data                             │    │
│  │  - Duration (ticks)                                                  │    │
│  │  - Peak multiplier                                                   │    │
│  │  - Event: rug (all games end in rug)                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                   ┌────────────────┼────────────────┐                       │
│                   ▼                ▼                ▼                       │
│  ┌────────────────────┐  ┌────────────────┐  ┌──────────────────┐          │
│  │    Hazard Rate     │  │ Survival Curve │  │   Conditional    │          │
│  │    h(t) = f(t)/S(t)│  │  S(t) = 1-F(t) │  │   Probability    │          │
│  │                    │  │                │  │  P(T≤t+w|T>t)    │          │
│  └────────────────────┘  └────────────────┘  └──────────────────┘          │
│           │                      │                    │                     │
│           └──────────────────────┼────────────────────┘                     │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Sidebet Timing Optimization                       │    │
│  │  P(rug in window | survived to tick t) → Bet/Skip decision          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Survival Function

```python
def compute_survival_curve(durations: np.ndarray) -> dict:
    """
    Compute Kaplan-Meier survival curve.

    S(t) = P(T > t) = probability of surviving past time t

    For rugs.fun: S(t) = probability game lasts beyond tick t

    Args:
        durations: Array of game durations in ticks

    Returns:
        Dict with time points and survival probabilities
    """
    # Sort durations
    sorted_durations = np.sort(durations)
    n = len(sorted_durations)

    # Get unique times and counts
    unique_times, counts = np.unique(sorted_durations, return_counts=True)

    # Kaplan-Meier estimator
    survival_probs = []
    at_risk = n

    for t, d in zip(unique_times, counts):
        # P(survive past t) = P(survive to t) * (1 - d/at_risk)
        survival_prob = (at_risk - d) / at_risk if at_risk > 0 else 0
        survival_probs.append(survival_prob)
        at_risk -= d

    # Cumulative survival
    cumulative_survival = np.cumprod(
        [(at_risk - d) / at_risk if at_risk > 0 else 1
         for at_risk, d in zip(range(n, 0, -1), counts)]
    )

    return {
        'times': unique_times,
        'survival': cumulative_survival,
        'n_at_risk': list(range(n, n - len(unique_times), -1)),
    }
```

### 2. Hazard Rate Function

```python
def compute_hazard_rate(durations: np.ndarray, bandwidth: int = 10) -> dict:
    """
    Compute hazard rate h(t) = f(t) / S(t).

    Hazard rate is the instantaneous risk of rugging given survival to time t.

    For rugs.fun: h(t) = P(rug at tick t | game reached tick t)

    Args:
        durations: Array of game durations
        bandwidth: Smoothing window size

    Returns:
        Dict with time points and hazard rates
    """
    sorted_durations = np.sort(durations)
    n = len(sorted_durations)

    # Create time grid
    max_time = int(np.max(durations))
    time_grid = np.arange(0, max_time + 1)

    # Count events at each time
    event_counts = np.zeros(max_time + 1)
    for d in sorted_durations:
        event_counts[int(d)] += 1

    # Count at risk at each time
    at_risk = np.zeros(max_time + 1)
    for t in range(max_time + 1):
        at_risk[t] = np.sum(sorted_durations >= t)

    # Hazard rate: h(t) = events at t / at risk at t
    hazard = np.zeros(max_time + 1)
    for t in range(max_time + 1):
        if at_risk[t] > 0:
            hazard[t] = event_counts[t] / at_risk[t]

    # Smooth with rolling average
    if bandwidth > 1:
        kernel = np.ones(bandwidth) / bandwidth
        hazard_smooth = np.convolve(hazard, kernel, mode='same')
    else:
        hazard_smooth = hazard

    return {
        'times': time_grid,
        'hazard': hazard,
        'hazard_smooth': hazard_smooth,
        'at_risk': at_risk,
        'events': event_counts,
    }
```

### 3. Conditional Probability Matrix

```python
def compute_conditional_probability(
    durations: np.ndarray,
    window_size: int = 40,
    max_tick: int = 500
) -> np.ndarray:
    """
    Compute P(rug in next w ticks | survived to tick t).

    This is the key metric for sidebet timing decisions.

    Args:
        durations: Array of game durations
        window_size: Sidebet window (40 ticks default)
        max_tick: Maximum tick to compute

    Returns:
        2D array where [t] = P(rug in [t, t+window] | survived to t)
    """
    n = len(durations)
    conditional_probs = np.zeros(max_tick + 1)

    for t in range(max_tick + 1):
        # Games that survived to tick t
        survived_to_t = durations[durations >= t]
        n_survived = len(survived_to_t)

        if n_survived == 0:
            conditional_probs[t] = 1.0  # All games ended before t
            continue

        # Games that rugged within window [t, t + window_size)
        rugged_in_window = np.sum(
            (survived_to_t >= t) & (survived_to_t < t + window_size)
        )

        # P(rug in window | survived to t)
        conditional_probs[t] = rugged_in_window / n_survived

    return conditional_probs
```

### 4. Survival Analysis Report

```python
def survival_analysis_report(durations: np.ndarray) -> dict:
    """
    Generate comprehensive survival analysis report.

    Args:
        durations: Array of game durations

    Returns:
        Dict with all survival metrics
    """
    # Basic statistics
    stats_dict = {
        'count': len(durations),
        'mean': np.mean(durations),
        'median': np.median(durations),
        'std': np.std(durations),
        'min': np.min(durations),
        'max': np.max(durations),
    }

    # Percentiles
    percentiles = {
        'p10': np.percentile(durations, 10),
        'p25': np.percentile(durations, 25),
        'p50': np.percentile(durations, 50),
        'p75': np.percentile(durations, 75),
        'p90': np.percentile(durations, 90),
        'p95': np.percentile(durations, 95),
    }

    # Survival at key ticks
    survival_curve = compute_survival_curve(durations)
    survival_at_ticks = {}
    for tick in [50, 100, 150, 200, 250, 300, 400, 500]:
        idx = np.searchsorted(survival_curve['times'], tick)
        if idx < len(survival_curve['survival']):
            survival_at_ticks[f'S({tick})'] = survival_curve['survival'][idx]
        else:
            survival_at_ticks[f'S({tick})'] = 0.0

    # Conditional probabilities at key ticks
    cond_probs = compute_conditional_probability(durations)
    conditional_at_ticks = {}
    for tick in [50, 100, 150, 200, 250, 300]:
        conditional_at_ticks[f'P(rug|t>{tick})'] = cond_probs[tick]

    return {
        'statistics': stats_dict,
        'percentiles': percentiles,
        'survival_at_ticks': survival_at_ticks,
        'conditional_probabilities': conditional_at_ticks,
    }
```

### 5. Optimal Entry Analysis

```python
def find_optimal_entry_window(
    durations: np.ndarray,
    window_size: int = 40,
    min_edge: float = 0.0167,  # 16.67% breakeven for 5:1
    kelly_fraction: float = 0.25
) -> dict:
    """
    Find optimal tick range for sidebet entry.

    Optimal = where conditional probability exceeds breakeven
    and expected value is maximized.

    Args:
        durations: Game durations
        window_size: Sidebet window (40 ticks)
        min_edge: Minimum edge required (above breakeven)
        kelly_fraction: Kelly fraction for sizing

    Returns:
        Dict with optimal entry recommendations
    """
    cond_probs = compute_conditional_probability(durations, window_size)
    breakeven = 1 / 6  # 16.67% for 5:1 payout

    # Find ticks with positive edge
    edge = cond_probs - breakeven
    positive_edge_ticks = np.where(edge > min_edge)[0]

    if len(positive_edge_ticks) == 0:
        return {
            'optimal_entry': None,
            'message': 'No ticks with positive edge found',
        }

    # Find maximum edge tick
    max_edge_tick = np.argmax(edge)
    max_edge = edge[max_edge_tick]

    # Kelly calculation
    kelly = (cond_probs[max_edge_tick] * 4 - (1 - cond_probs[max_edge_tick])) / 4
    recommended_bet = kelly * kelly_fraction

    return {
        'optimal_entry_tick': int(max_edge_tick),
        'win_rate_at_optimal': float(cond_probs[max_edge_tick]),
        'edge_at_optimal': float(max_edge),
        'kelly_fraction': float(kelly),
        'recommended_bet_pct': float(recommended_bet * 100),
        'positive_edge_range': (
            int(positive_edge_ticks[0]),
            int(positive_edge_ticks[-1])
        ),
        'ev_per_bet': float(max_edge * 4),  # Expected value per unit bet
    }
```

## Key Formulas

| Metric | Formula | Description |
|--------|---------|-------------|
| Survival | S(t) = P(T > t) | Probability of lasting beyond t |
| Hazard | h(t) = f(t) / S(t) | Instantaneous rug risk |
| Conditional | P(t < T ≤ t+w \| T > t) | Rug in window given survival |
| Cumulative Hazard | H(t) = -ln(S(t)) | Accumulated risk |

## Empirical Results (568-game study)

| Tick | S(t) | P(rug in 40 | T > t) | Hazard |
|------|------|----------------------|--------|
| 50 | 0.92 | 12% | 0.008 |
| 100 | 0.78 | 18% | 0.012 |
| 150 | 0.58 | 25% | 0.018 |
| 200 | 0.38 | 35% | 0.025 |
| 250 | 0.22 | 48% | 0.035 |
| 300 | 0.12 | 62% | 0.048 |
| 400 | 0.04 | 78% | 0.065 |

## Integration with Sidebet Strategy

```python
# Example: Using survival analysis for entry timing
def should_place_sidebet(
    current_tick: int,
    durations: np.ndarray,
    window_size: int = 40
) -> dict:
    """
    Decide whether to place sidebet based on survival analysis.

    Args:
        current_tick: Current game tick
        durations: Historical game durations
        window_size: Sidebet window (40 ticks)

    Returns:
        Decision dict
    """
    cond_probs = compute_conditional_probability(durations, window_size)
    breakeven = 1 / 6  # 16.67%

    win_rate = cond_probs[current_tick] if current_tick < len(cond_probs) else 1.0
    edge = win_rate - breakeven

    return {
        'tick': current_tick,
        'win_rate': win_rate,
        'edge': edge,
        'should_bet': edge > 0.02,  # 2% edge threshold
        'confidence': 'high' if edge > 0.10 else 'medium' if edge > 0.05 else 'low',
    }
```

## Gotchas

1. **All Events Are Rugs**: In rugs.fun, every game ends in a rug. No censoring needed.

2. **Window Overlap**: Conditional probabilities for adjacent ticks overlap significantly.

3. **Sample Size**: Need 500+ games for reliable hazard estimates at high ticks.

4. **Non-Stationarity**: Game parameters may change over time. Use recent data.

5. **Tick Resolution**: 250ms per tick. Convert to time with `time_ms = tick * 250`.

6. **Boundary Effects**: Hazard rate unstable at tail (few games survive to high ticks).

7. **Independence Assumption**: Each game is assumed independent. Not strictly true if player behavior affects rug timing.
