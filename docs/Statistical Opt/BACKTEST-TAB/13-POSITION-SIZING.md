# 13 - Position Sizing (Backtest Tab)

## Purpose

Calculate optimal bet sizes using various methodologies:
1. Kelly Criterion (8 variants)
2. Progressive sizing
3. Dynamic confidence-based
4. Volatility-adjusted

## Dependencies

```python
# Internal module
from recording_ui.services.position_sizing import (
    kelly_criterion,
    fractional_kelly,
    suggest_kelly_sizing,
    calculate_progressive_sizes,
    WalletConfig,
)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Position Sizing System                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Kelly Criterion Family                          │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │                                                                      │    │
│  │  Full Kelly:     f* = (p*b - q) / b                                 │    │
│  │  Half Kelly:     f  = 0.50 * f*                                     │    │
│  │  Quarter Kelly:  f  = 0.25 * f*     (Recommended for sidebets)     │    │
│  │  Aggressive:     f  = 0.75 * f*                                     │    │
│  │                                                                      │    │
│  │  Where: p = win rate, q = 1-p, b = net odds (4 for 5:1 payout)     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Dynamic Sizing Modes                            │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │                                                                      │    │
│  │  Fixed:            bet = base_size                                  │    │
│  │  Progressive:      bet[i] = base_size * multiplier^(i-1)            │    │
│  │  Confidence-based: bet = base * (1 + confidence_bonus)              │    │
│  │  Drawdown-adjusted: bet = base * (1 - drawdown_factor)              │    │
│  │  Anti-Martingale:  bet = base * win_streak_multiplier               │    │
│  │  Theta-Bayesian:   bet = base * theta(experience)                   │    │
│  │  Volatility:       bet = base * (baseline_vol / current_vol)        │    │
│  │                                                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Kelly Criterion

```python
# src/recording_ui/services/position_sizing.py

def kelly_criterion(win_rate: float, payout: float = 5.0) -> float:
    """
    Calculate full Kelly fraction.

    The Kelly Criterion maximizes long-term growth rate.

    Formula:
        f* = (p * b - q) / b

    Where:
        p = probability of winning
        q = probability of losing (1 - p)
        b = net odds (payout - 1)

    For 5:1 sidebet payout:
        b = 4 (you win 4x your bet, plus return of original)
        Breakeven: p = 1/6 = 16.67%

    Args:
        win_rate: Probability of winning (0 to 1)
        payout: Total payout multiplier (5.0 for 5:1)

    Returns:
        Kelly fraction (fraction of bankroll to bet)
        Returns 0 if no edge (negative Kelly)

    Example:
        >>> kelly_criterion(0.20, 5.0)  # 20% win rate, 5:1 payout
        0.05  # Bet 5% of bankroll
    """
    p = win_rate
    q = 1 - p
    b = payout - 1  # Net odds

    kelly = (p * b - q) / b

    # Don't bet with negative edge
    return max(0, kelly)


def fractional_kelly(win_rate: float, fraction: float = 0.25,
                     payout: float = 5.0) -> float:
    """
    Calculate fractional Kelly for reduced variance.

    Full Kelly is theoretically optimal but has high variance.
    Fractional Kelly trades some growth for stability.

    Recommended fractions:
        - 0.25 (Quarter Kelly): Conservative, recommended for sidebets
        - 0.50 (Half Kelly): Moderate risk
        - 0.75: Aggressive

    Args:
        win_rate: Probability of winning
        fraction: Kelly fraction (0.25 = quarter Kelly)
        payout: Total payout multiplier

    Returns:
        Bet size as fraction of bankroll
    """
    full_kelly = kelly_criterion(win_rate, payout)
    return full_kelly * fraction
```

### 2. Kelly Variants

```python
def calculate_all_kelly_variants(win_rate: float, bankroll: float,
                                  payout: float = 5.0) -> dict:
    """
    Calculate all Kelly variants for comparison.

    Returns dict with bet sizes for each variant.
    """
    full = kelly_criterion(win_rate, payout)

    return {
        "full_kelly": {
            "fraction": full,
            "bet_size": bankroll * full,
            "risk_level": "Extreme",
        },
        "three_quarter_kelly": {
            "fraction": full * 0.75,
            "bet_size": bankroll * full * 0.75,
            "risk_level": "High",
        },
        "half_kelly": {
            "fraction": full * 0.50,
            "bet_size": bankroll * full * 0.50,
            "risk_level": "Medium",
        },
        "quarter_kelly": {
            "fraction": full * 0.25,
            "bet_size": bankroll * full * 0.25,
            "risk_level": "Low (Recommended)",
        },
        "eighth_kelly": {
            "fraction": full * 0.125,
            "bet_size": bankroll * full * 0.125,
            "risk_level": "Very Low",
        },
    }
```

### 3. Progressive Sizing

```python
def calculate_progressive_sizes(base_size: float, num_bets: int,
                                 multiplier: float = 2.0) -> list[float]:
    """
    Calculate progressive bet sizes (Martingale-style).

    Each subsequent bet is multiplier times the previous.
    Common for "chase" strategies.

    Args:
        base_size: First bet size
        num_bets: Number of bets in sequence
        multiplier: Multiplier between bets (2.0 = double each time)

    Returns:
        List of bet sizes

    Example:
        >>> calculate_progressive_sizes(0.001, 4, 2.0)
        [0.001, 0.002, 0.004, 0.008]

    Warning:
        Progressive sizing is high risk. Total exposure grows exponentially.
        Total risk for above: 0.015 SOL (15x base bet)
    """
    sizes = []
    current = base_size
    for _ in range(num_bets):
        sizes.append(current)
        current *= multiplier
    return sizes


def calculate_reverse_progressive(base_size: float, num_bets: int,
                                   multiplier: float = 2.0) -> list[float]:
    """
    Reverse progressive (large first, decreasing).

    Useful when early bets have higher expected value.

    Example:
        >>> calculate_reverse_progressive(0.008, 4, 2.0)
        [0.008, 0.004, 0.002, 0.001]
    """
    forward = calculate_progressive_sizes(base_size, num_bets, multiplier)
    return list(reversed(forward))
```

### 4. Dynamic Sizing Functions

```python
def confidence_based_size(base_size: float, confidence: float,
                          threshold: float = 0.60,
                          multiplier: float = 2.0) -> float:
    """
    Adjust bet size based on confidence level.

    Higher confidence = larger bet (up to multiplier).

    Args:
        base_size: Base bet size
        confidence: Confidence level (0 to 1)
        threshold: Confidence level to trigger multiplier
        multiplier: Maximum bet multiplier

    Returns:
        Adjusted bet size
    """
    if confidence >= threshold:
        # Linear scale from 1x at threshold to multiplier at 100%
        scale = 1 + (multiplier - 1) * (confidence - threshold) / (1 - threshold)
        return base_size * scale
    return base_size


def drawdown_adjusted_size(base_size: float, current_balance: float,
                           initial_balance: float,
                           reduction_factor: float = 0.5) -> float:
    """
    Reduce bet size during drawdown.

    Preserves capital when strategy is underperforming.

    Args:
        base_size: Base bet size
        current_balance: Current wallet balance
        initial_balance: Starting balance
        reduction_factor: How aggressively to reduce (0.5 = halve bet at 50% drawdown)

    Returns:
        Adjusted bet size
    """
    drawdown_pct = (initial_balance - current_balance) / initial_balance
    if drawdown_pct > 0:
        adjustment = 1 - (drawdown_pct * reduction_factor)
        return base_size * max(0.25, adjustment)  # Floor at 25%
    return base_size


def theta_bayesian_size(base_size: float, games_played: int,
                        theta_base: float = 0.5,
                        theta_max: float = 2.0,
                        theta_scale: int = 100) -> float:
    """
    Theta-accelerated Bayesian sizing.

    Bet size increases with experience (games played).
    Based on idea that strategy confidence grows with data.

    Formula:
        theta = base + (max - base) * (1 - 1/(1 + n/scale))

    Where n = games played, scale = games for theta to reach midpoint.

    Args:
        base_size: Base bet size
        games_played: Number of games completed
        theta_base: Starting theta multiplier
        theta_max: Maximum theta multiplier
        theta_scale: Games for theta to reach midpoint

    Returns:
        Adjusted bet size

    Example:
        At 0 games:   theta = 0.5 (half base)
        At 100 games: theta = 1.25 (midpoint)
        At 1000 games: theta ≈ 1.95 (approaching max)
    """
    theta = theta_base + (theta_max - theta_base) * (1 - 1 / (1 + games_played / theta_scale))
    return base_size * theta


def volatility_adjusted_size(base_size: float, current_volatility: float,
                              baseline_volatility: float = 0.102917) -> float:
    """
    Adjust bet size based on game volatility.

    Reduce bets in high volatility, increase in low volatility.

    Args:
        base_size: Base bet size
        current_volatility: Current game's volatility metric
        baseline_volatility: Historical average volatility

    Returns:
        Adjusted bet size (clamped to 0.5x - 2x)
    """
    if current_volatility <= 0:
        return base_size

    ratio = baseline_volatility / current_volatility
    adjustment = max(0.5, min(2.0, ratio))
    return base_size * adjustment
```

### 5. Suggested Sizing Function

```python
def suggest_kelly_sizing(win_rate: float, initial_balance: float,
                         num_bets: int, kelly_fraction: float = 0.25) -> list[float]:
    """
    Suggest Kelly-based bet sizes for a multi-bet strategy.

    Calculates fractional Kelly and divides across bet windows.

    Args:
        win_rate: Win rate percentage (e.g., 20 for 20%)
        initial_balance: Starting bankroll in SOL
        num_bets: Number of bets in sequence
        kelly_fraction: Kelly fraction to use (0.25 = quarter)

    Returns:
        List of suggested bet sizes

    Example:
        >>> suggest_kelly_sizing(20, 0.1, 4, 0.25)
        [0.00125, 0.00125, 0.00125, 0.00125]
    """
    kelly = fractional_kelly(win_rate / 100, fraction=kelly_fraction)

    if kelly <= 0:
        return [0.0] * num_bets

    # Divide Kelly fraction across bets
    per_bet_fraction = kelly / num_bets
    per_bet_size = initial_balance * per_bet_fraction

    return [per_bet_size] * num_bets
```

### 6. API Endpoint

```python
@app.route("/api/explorer/kelly")
def api_explorer_kelly():
    """Get Kelly Criterion bet size suggestions."""
    win_rate = request.args.get("win_rate", 20.0, type=float)
    initial_balance = request.args.get("initial_balance", 0.1, type=float)
    num_bets = request.args.get("num_bets", 4, type=int)

    # Calculate Kelly
    kelly_full = kelly_criterion(win_rate / 100)
    kelly_quarter = fractional_kelly(win_rate / 100, fraction=0.25)
    kelly_half = fractional_kelly(win_rate / 100, fraction=0.5)

    # Suggested sizes
    suggested = suggest_kelly_sizing(win_rate, initial_balance, num_bets, 0.25)
    progressive = calculate_progressive_sizes(0.001, num_bets, 2.0)

    return jsonify({
        "win_rate": win_rate,
        "initial_balance": initial_balance,
        "kelly": {
            "full": round(kelly_full, 4),
            "half": round(kelly_half, 4),
            "quarter": round(kelly_quarter, 4),
        },
        "suggested_sizes": {
            "kelly_quarter": suggested,
            "fixed_small": [0.001] * num_bets,
            "progressive_2x": progressive,
        },
        "analysis": {
            "edge_exists": kelly_full > 0,
            "recommended_strategy": "kelly_quarter" if kelly_full > 0 else "skip",
            "total_risk_kelly": sum(suggested),
            "total_risk_progressive": sum(progressive),
        },
    })
```

## Sizing Mode Comparison

| Mode | Formula | Best For | Risk Level |
|------|---------|----------|------------|
| Fixed | `bet = constant` | Consistency | Low |
| Kelly | `bet = bankroll * f*` | Growth | High |
| Fractional Kelly | `bet = bankroll * f* * fraction` | Balanced | Medium |
| Progressive | `bet[i] = base * mult^i` | Loss recovery | Very High |
| Confidence | `bet = base * confidence_multiplier` | Variable conditions | Medium |
| Drawdown-adjusted | `bet = base * (1 - dd_factor)` | Capital preservation | Low |
| Theta-Bayesian | `bet = base * theta(experience)` | Learning | Medium |
| Volatility | `bet = base * (baseline/current)` | Stability | Medium |

## Critical Constants

| Constant | Value | Formula |
|----------|-------|---------|
| Breakeven win rate | 16.67% | 1 / payout |
| Full Kelly at 18.5% | 4.63% | (0.185*4 - 0.815) / 4 |
| Quarter Kelly at 18.5% | 1.16% | full * 0.25 |
| Historical volatility | 0.102917 | From 568-game study |

## Gotchas

1. **Negative Kelly**: If win rate < 16.67%, Kelly is negative. Don't bet.

2. **Progressive Explosion**: Progressive sizing total exposure is `base * (mult^n - 1) / (mult - 1)`.

3. **Kelly Variance**: Full Kelly has ~33% chance of 50%+ drawdown. Use fractional.

4. **Win Rate Estimation**: Use rolling window, not lifetime average.

5. **Bet > Balance**: Always clamp: `bet = min(bet, balance)`.

6. **Theta Start**: Theta-Bayesian starts conservative (0.5x) and grows.

7. **Volatility Extremes**: Clamp volatility adjustment to prevent extreme bets.
