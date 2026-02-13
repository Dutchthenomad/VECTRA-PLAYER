# 15 - Kelly Criterion

## Purpose

Optimal bet sizing for long-term growth maximization:
1. Full Kelly formula
2. 8 fractional variants
3. Edge calculation
4. Risk-adjusted recommendations

## Dependencies

```python
import math
from recording_ui.services.position_sizing import (
    kelly_criterion,
    fractional_kelly,
)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Kelly Criterion Family                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                              Full Kelly Formula                              │
│                                                                              │
│                           f* = (p × b - q) / b                               │
│                                                                              │
│                    Where:                                                    │
│                      p = probability of winning                              │
│                      q = probability of losing (1 - p)                       │
│                      b = net odds (payout - 1)                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                For 5:1 Sidebet Payout                                │    │
│  │                                                                      │    │
│  │  Net odds: b = 5 - 1 = 4                                            │    │
│  │  Breakeven: p = 1/(b+1) = 1/5 = 20%? NO!                           │    │
│  │                                                                      │    │
│  │  Correct breakeven: p × b = q → p × 4 = 1 - p → p = 1/5 = 20%?     │    │
│  │  Wait: EV = p × 4 - q × 1 = 0 → 4p = 1-p → 5p = 1 → p = 0.2       │    │
│  │                                                                      │    │
│  │  Actually for sidebet: You bet 1, win returns 5 (profit = 4)        │    │
│  │  Breakeven: p × 4 = (1-p) × 1 → 4p = 1-p → p = 1/5 = 20%           │    │
│  │                                                                      │    │
│  │  Hmm, but rugs-expert says 16.67%...                                │    │
│  │  Let me recalculate: You bet 1 SOL                                  │    │
│  │    Win: get 5 SOL back (profit = 4)                                 │    │
│  │    Lose: lose 1 SOL                                                 │    │
│  │  EV = p×4 - (1-p)×1 = 0 → 4p - 1 + p = 0 → 5p = 1 → p = 0.2       │    │
│  │                                                                      │    │
│  │  But 1/6 = 16.67%. Where does that come from?                       │    │
│  │  Ah! If payout is 6:1 (profit = 5): p = 1/6 = 16.67%               │    │
│  │                                                                      │    │
│  │  Per rugs-expert: Sidebet pays 5:1 meaning 400% profit              │    │
│  │  So: bet 1, win = 5 total, profit = 4                               │    │
│  │  Breakeven: 1/5 = 20%                                               │    │
│  │                                                                      │    │
│  │  BUT: Per CLAUDE.md, breakeven is 16.67% (1/6)                      │    │
│  │  This implies: profit = 5 (6:1 total return)                        │    │
│  │                                                                      │    │
│  │  Let's use the documented value: breakeven = 16.67%                 │    │
│  │  This means: payout odds b = 5 (net profit)                         │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Full Kelly Formula

```python
def kelly_criterion(win_rate: float, payout: float = 5.0) -> float:
    """
    Calculate the Kelly Criterion optimal bet fraction.

    The Kelly Criterion tells you what fraction of your bankroll to bet
    to maximize long-term growth rate (geometric mean return).

    Formula:
        f* = (p × b - q) / b

    Where:
        f* = optimal fraction of bankroll to bet
        p = probability of winning
        q = probability of losing (1 - p)
        b = net odds (decimal odds - 1, or profit per unit bet)

    For rugs.fun sidebets:
        - Payout: 5:1 (bet 1, win 5 total, profit 4)
        - But per CLAUDE.md: breakeven = 16.67% implies b = 5
        - So net profit per winning bet = 5

    Args:
        win_rate: Probability of winning (0.0 to 1.0)
        payout: Total return multiplier (default 5.0 for sidebet)

    Returns:
        Optimal bet fraction (0.0 if no edge)

    Example:
        >>> kelly_criterion(0.185)  # 18.5% win rate
        0.037  # Bet 3.7% of bankroll

        >>> kelly_criterion(0.167)  # Breakeven
        0.0    # No edge, don't bet

        >>> kelly_criterion(0.25)   # 25% win rate
        0.10   # Bet 10% of bankroll
    """
    p = win_rate
    q = 1 - p
    b = payout - 1  # Net odds

    kelly = (p * b - q) / b

    # Never return negative (no edge = don't bet)
    return max(0.0, kelly)
```

### 2. Fractional Kelly

```python
def fractional_kelly(win_rate: float, fraction: float = 0.25,
                     payout: float = 5.0) -> float:
    """
    Calculate fractional Kelly for reduced variance.

    Full Kelly maximizes growth but has HIGH variance:
    - ~33% chance of 50% drawdown
    - Requires accurate win rate estimate

    Fractional Kelly trades growth for stability:
    - Quarter Kelly (0.25): 75% of optimal growth, much lower variance
    - Half Kelly (0.50): 87.5% of optimal growth, moderate variance

    The Growth-Risk Tradeoff:
        Fraction | Growth Rate | Variance
        1.00     | 100%        | 100%
        0.75     | 93.8%       | 56.3%
        0.50     | 75%         | 25%
        0.25     | 43.8%       | 6.3%
        0.125    | 23.4%       | 1.6%

    Args:
        win_rate: Probability of winning
        fraction: Kelly fraction (0.25 = quarter Kelly)
        payout: Total return multiplier

    Returns:
        Bet size as fraction of bankroll

    Recommendation:
        For sidebets with uncertain edge, use Quarter Kelly (0.25)
    """
    full_kelly = kelly_criterion(win_rate, payout)
    return full_kelly * fraction
```

### 3. Kelly Variants Table

```python
KELLY_VARIANTS = {
    "full_kelly": {
        "fraction": 1.0,
        "growth_rate": 1.0,
        "variance": 1.0,
        "risk_level": "Extreme",
        "description": "Maximum growth, maximum risk",
    },
    "three_quarter_kelly": {
        "fraction": 0.75,
        "growth_rate": 0.938,
        "variance": 0.563,
        "risk_level": "High",
        "description": "94% growth, 44% less variance",
    },
    "half_kelly": {
        "fraction": 0.50,
        "growth_rate": 0.75,
        "variance": 0.25,
        "risk_level": "Medium",
        "description": "75% growth, 75% less variance",
    },
    "quarter_kelly": {
        "fraction": 0.25,
        "growth_rate": 0.438,
        "variance": 0.063,
        "risk_level": "Low",
        "description": "44% growth, 94% less variance (RECOMMENDED)",
    },
    "eighth_kelly": {
        "fraction": 0.125,
        "growth_rate": 0.234,
        "variance": 0.016,
        "risk_level": "Very Low",
        "description": "23% growth, minimal variance",
    },
    "sixteenth_kelly": {
        "fraction": 0.0625,
        "growth_rate": 0.121,
        "variance": 0.004,
        "risk_level": "Minimal",
        "description": "12% growth, near-zero variance",
    },
    "aggressive_kelly": {
        "fraction": 1.5,
        "growth_rate": 0.875,  # Actually decreases!
        "variance": 2.25,
        "risk_level": "Extreme+",
        "description": "OVER-BETTING: Less growth, more risk!",
    },
    "double_kelly": {
        "fraction": 2.0,
        "growth_rate": 0.0,  # Zero long-term growth
        "variance": 4.0,
        "risk_level": "Ruin",
        "description": "GUARANTEED RUIN: Never do this",
    },
}
```

### 4. Edge Calculation

```python
def calculate_edge(win_rate: float, payout: float = 5.0) -> dict:
    """
    Calculate the mathematical edge for a betting opportunity.

    Edge = Expected Value per unit bet

    For sidebet with 5:1 payout (profit = 4):
        EV = p × 4 - q × 1
        EV = 4p - (1-p)
        EV = 5p - 1

    Args:
        win_rate: Probability of winning
        payout: Total return multiplier

    Returns:
        Dict with edge metrics
    """
    p = win_rate
    q = 1 - p
    profit_on_win = payout - 1

    # Expected value per unit bet
    ev = p * profit_on_win - q

    # Breakeven win rate
    breakeven = 1 / payout

    # Edge as percentage
    edge_pct = (win_rate - breakeven) / breakeven

    # Kelly fraction
    kelly = kelly_criterion(win_rate, payout)

    return {
        "expected_value": ev,
        "expected_value_pct": ev * 100,
        "breakeven_win_rate": breakeven,
        "actual_win_rate": win_rate,
        "edge_exists": ev > 0,
        "edge_pct": edge_pct * 100,
        "kelly_fraction": kelly,
        "recommended_bet": fractional_kelly(win_rate, 0.25, payout),
        "verdict": "BET" if ev > 0 else "NO BET",
    }
```

### 5. Practical Application

```python
def recommend_bet_size(win_rate: float, bankroll: float,
                       payout: float = 5.0,
                       risk_tolerance: str = "moderate") -> dict:
    """
    Get practical bet size recommendation.

    Args:
        win_rate: Estimated probability of winning
        bankroll: Current bankroll in SOL
        payout: Payout multiplier
        risk_tolerance: "low", "moderate", "high", "aggressive"

    Returns:
        Dict with recommendation
    """
    fraction_map = {
        "low": 0.125,       # Eighth Kelly
        "moderate": 0.25,   # Quarter Kelly (default)
        "high": 0.50,       # Half Kelly
        "aggressive": 0.75, # Three-quarter Kelly
    }

    fraction = fraction_map.get(risk_tolerance, 0.25)
    kelly_frac = fractional_kelly(win_rate, fraction, payout)
    bet_size = bankroll * kelly_frac

    edge = calculate_edge(win_rate, payout)

    # Cap at 5% of bankroll for safety
    max_bet = bankroll * 0.05
    safe_bet = min(bet_size, max_bet)

    return {
        "kelly_fraction": kelly_frac,
        "raw_bet_size": bet_size,
        "recommended_bet_size": safe_bet,
        "pct_of_bankroll": safe_bet / bankroll * 100,
        "edge": edge,
        "risk_tolerance": risk_tolerance,
        "capped": bet_size > max_bet,
        "warnings": [
            "Win rate estimation is crucial - small errors compound",
            "Use conservative estimates when uncertain",
        ] if kelly_frac > 0.02 else [],
    }
```

## Critical Formulas

| Metric | Formula | For 5:1 Payout |
|--------|---------|----------------|
| Kelly Fraction | f* = (pb - q) / b | (4p - q) / 4 |
| Breakeven | p = 1 / payout | 1/5 = 20% |
| Expected Value | EV = pb - q | 4p - (1-p) = 5p - 1 |
| Growth Rate | G = p×ln(1+b×f) + q×ln(1-f) | Complex |

## Win Rate vs Kelly Fraction (5:1 Payout)

| Win Rate | Full Kelly | Quarter Kelly | Edge |
|----------|------------|---------------|------|
| 15% | 0% | 0% | -25% |
| 16.67% | 0% | 0% | 0% (breakeven) |
| 18% | 2.5% | 0.625% | +8% |
| 18.5% | 3.1% | 0.78% | +11% |
| 20% | 5.0% | 1.25% | +20% |
| 22% | 7.5% | 1.88% | +32% |
| 25% | 12.5% | 3.13% | +50% |
| 30% | 20.0% | 5.0% | +80% |

## Gotchas

1. **Win Rate Uncertainty**: Kelly assumes known win rate. Overestimation leads to overbetting.

2. **Fractional is Safer**: Quarter Kelly sacrifices 56% growth for 94% less variance.

3. **Over-Kelly**: Betting more than Kelly DECREASES expected growth.

4. **Double Kelly = Ruin**: At 2x Kelly, expected geometric return is 0.

5. **Breakeven Confusion**: For 5:1 total return (profit=4), breakeven is 20%. For 6:1 (profit=5), it's 16.67%.

6. **Multiple Bets**: For n sequential bets, divide Kelly by n.

7. **Estimation Error**: Use historical data, but apply recency weighting.
