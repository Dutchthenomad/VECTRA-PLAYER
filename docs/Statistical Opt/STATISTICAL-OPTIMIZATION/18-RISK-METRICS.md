# 18 - Risk Metrics

## Purpose

Comprehensive risk measurement for sidebet strategies:
1. Value at Risk (VaR) - 95% and 99%
2. Conditional VaR (Expected Shortfall)
3. Sharpe, Sortino, Calmar ratios
4. Risk of Ruin calculation

## Dependencies

```python
import numpy as np
from dataclasses import dataclass
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Risk Metrics System                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  Monte Carlo Simulation Output                       │    │
│  │  final_bankrolls: [0.05, 0.12, 0.08, 0.23, ...]  (10k samples)     │    │
│  │  max_drawdowns: [0.12, 0.08, 0.15, ...]                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│           ┌────────────────────────┼────────────────────────┐               │
│           ▼                        ▼                        ▼               │
│  ┌─────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐   │
│  │     VaR/CVaR    │  │  Performance Ratios   │  │   Ruin Analysis     │   │
│  │                 │  │                       │  │                     │   │
│  │  VaR 95%: 5th   │  │  Sharpe: ret/std     │  │  P(ruin): bankrupt  │   │
│  │  percentile     │  │  Sortino: ret/down   │  │  games              │   │
│  │                 │  │  Calmar: ret/maxdd   │  │  E[games to ruin]   │   │
│  │  CVaR: mean of  │  │                       │  │                     │   │
│  │  worst 5%       │  │                       │  │                     │   │
│  └─────────────────┘  └───────────────────────┘  └─────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Risk Report                                    │    │
│  │  {var_95, var_99, cvar_95, sharpe, sortino, calmar, p_ruin, ...}   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Value at Risk (VaR)

```python
def calculate_var(final_bankrolls: np.ndarray, initial: float,
                  confidence: float = 0.95) -> float:
    """
    Calculate Value at Risk.

    VaR answers: "What is the maximum loss at X% confidence?"

    For 95% VaR: "95% of the time, losses won't exceed this amount"

    Args:
        final_bankrolls: Array of final portfolio values
        initial: Initial bankroll
        confidence: Confidence level (0.95 or 0.99)

    Returns:
        VaR as positive loss amount

    Example:
        >>> calculate_var(np.array([0.08, 0.12, 0.05, 0.15, 0.10]), 0.10, 0.95)
        0.05  # 5% chance of losing more than 0.05
    """
    percentile = (1 - confidence) * 100  # 5th percentile for 95% VaR
    var_value = np.percentile(final_bankrolls, percentile)

    # Return as positive loss (if var_value < initial, we have a loss)
    return max(0, initial - var_value)


def calculate_var_percentile(final_bankrolls: np.ndarray,
                             percentile: float) -> float:
    """
    Calculate VaR as raw percentile value.

    Args:
        final_bankrolls: Array of final portfolio values
        percentile: Percentile to calculate (5 for 95% VaR)

    Returns:
        Bankroll value at that percentile
    """
    return float(np.percentile(final_bankrolls, percentile))
```

### 2. Conditional VaR (Expected Shortfall)

```python
def calculate_cvar(final_bankrolls: np.ndarray, initial: float,
                   confidence: float = 0.95) -> float:
    """
    Calculate Conditional VaR (Expected Shortfall).

    CVaR answers: "If we're in the worst X%, what's the average loss?"

    More informative than VaR because it considers tail severity.

    Args:
        final_bankrolls: Array of final portfolio values
        initial: Initial bankroll
        confidence: Confidence level

    Returns:
        Average loss in worst (1-confidence) cases

    Example:
        >>> # If worst 5% of outcomes average 0.03 final value (from 0.10 start)
        >>> # CVaR = 0.10 - 0.03 = 0.07 average loss in bad scenarios
    """
    percentile = (1 - confidence) * 100
    var_threshold = np.percentile(final_bankrolls, percentile)

    # Mean of values below VaR threshold
    below_var = final_bankrolls[final_bankrolls <= var_threshold]

    if len(below_var) == 0:
        return calculate_var(final_bankrolls, initial, confidence)

    mean_below_var = np.mean(below_var)
    return max(0, initial - mean_below_var)


def calculate_cvar_value(final_bankrolls: np.ndarray,
                         percentile: float) -> float:
    """
    Calculate CVaR as mean of values below percentile.

    Args:
        final_bankrolls: Array of final portfolio values
        percentile: Percentile threshold

    Returns:
        Mean of values at or below percentile
    """
    var_threshold = np.percentile(final_bankrolls, percentile)
    below_var = final_bankrolls[final_bankrolls <= var_threshold]

    if len(below_var) == 0:
        return float(var_threshold)

    return float(np.mean(below_var))
```

### 3. Sharpe Ratio

```python
def calculate_sharpe(final_bankrolls: np.ndarray, initial: float,
                     risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe Ratio.

    Sharpe = (mean return - risk free) / std of returns

    Higher Sharpe = better risk-adjusted returns.

    Args:
        final_bankrolls: Array of final portfolio values
        initial: Initial bankroll
        risk_free_rate: Risk-free rate (usually 0 for short-term)

    Returns:
        Sharpe ratio (unitless)

    Interpretation:
        < 0: Negative returns
        0-1: Subpar risk-adjusted returns
        1-2: Good
        2-3: Very good
        > 3: Excellent (or likely data issue)
    """
    returns = (final_bankrolls - initial) / initial
    excess_return = np.mean(returns) - risk_free_rate
    std_return = np.std(returns)

    if std_return == 0:
        return 0.0 if excess_return == 0 else float('inf') * np.sign(excess_return)

    return float(excess_return / std_return)
```

### 4. Sortino Ratio

```python
def calculate_sortino(final_bankrolls: np.ndarray, initial: float,
                      target_return: float = 0.0) -> float:
    """
    Calculate Sortino Ratio.

    Sortino = (mean return - target) / downside deviation

    Like Sharpe but only penalizes downside volatility.
    Better for strategies with asymmetric returns.

    Args:
        final_bankrolls: Array of final portfolio values
        initial: Initial bankroll
        target_return: Minimum acceptable return (usually 0)

    Returns:
        Sortino ratio

    Interpretation:
        Similar to Sharpe but typically higher since it ignores
        upside volatility
    """
    returns = (final_bankrolls - initial) / initial
    excess_return = np.mean(returns) - target_return

    # Downside returns only
    downside_returns = returns[returns < target_return]

    if len(downside_returns) == 0:
        # No downside = excellent (return mean or inf)
        return float(excess_return) if excess_return != 0 else 0.0

    downside_std = np.std(downside_returns)

    if downside_std == 0:
        return float('inf') if excess_return > 0 else 0.0

    return float(excess_return / downside_std)
```

### 5. Calmar Ratio

```python
def calculate_calmar(final_bankrolls: np.ndarray,
                     max_drawdowns: np.ndarray,
                     initial: float) -> float:
    """
    Calculate Calmar Ratio.

    Calmar = annualized return / max drawdown

    Measures return per unit of drawdown risk.

    Args:
        final_bankrolls: Array of final portfolio values
        max_drawdowns: Array of max drawdown percentages per run
        initial: Initial bankroll

    Returns:
        Calmar ratio

    Note:
        For short-term sidebet strategies, we use mean return
        rather than annualized return.
    """
    mean_return = np.mean(final_bankrolls - initial) / initial
    mean_max_dd = np.mean(max_drawdowns)

    if mean_max_dd == 0:
        return float('inf') if mean_return > 0 else 0.0

    return float(mean_return / mean_max_dd)
```

### 6. Risk of Ruin

```python
def calculate_risk_of_ruin(simulation_results: dict) -> dict:
    """
    Calculate risk of ruin metrics.

    Risk of ruin = probability of going bankrupt before reaching goal.

    Args:
        simulation_results: Dict with 'ruined' flags and 'games_to_ruin'

    Returns:
        Dict with ruin metrics
    """
    num_ruined = simulation_results.get('num_ruined', 0)
    total_runs = simulation_results.get('iteration_count', 1)
    games_to_ruin = simulation_results.get('games_to_ruin', [])

    p_ruin = num_ruined / total_runs if total_runs > 0 else 0

    metrics = {
        'probability_of_ruin': p_ruin,
        'probability_of_survival': 1 - p_ruin,
        'num_ruined': num_ruined,
        'num_survived': total_runs - num_ruined,
    }

    if games_to_ruin:
        metrics['mean_games_to_ruin'] = float(np.mean(games_to_ruin))
        metrics['median_games_to_ruin'] = float(np.median(games_to_ruin))
        metrics['std_games_to_ruin'] = float(np.std(games_to_ruin))

    return metrics


def kelly_risk_of_ruin(kelly_fraction: float, win_rate: float,
                       target_multiple: float = 2.0) -> float:
    """
    Theoretical risk of ruin for Kelly betting.

    Formula: P(ruin before 2x) ≈ (1 - 2*edge) ^ (bankroll / bet_size)

    Args:
        kelly_fraction: Fraction of bankroll bet
        win_rate: Probability of winning
        target_multiple: Target bankroll multiple (default 2x)

    Returns:
        Probability of ruin before reaching target
    """
    # For 5:1 payout
    edge = win_rate * 4 - (1 - win_rate)

    if edge <= 0:
        return 1.0  # Guaranteed ruin with negative edge

    # Approximate risk of ruin
    # Using formula from "Beat the Dealer" by Ed Thorp
    q = 1 - win_rate
    p = win_rate

    if kelly_fraction >= 2 * edge:
        return 1.0  # Overbetting = guaranteed ruin

    # Risk of ruin decreases with lower Kelly fraction
    ror = (q / p) ** (1 / kelly_fraction) if kelly_fraction > 0 else 0

    return min(1.0, max(0.0, ror))
```

### 7. Comprehensive Risk Report

```python
def generate_risk_report(final_bankrolls: np.ndarray,
                         max_drawdowns: np.ndarray,
                         initial: float,
                         games_to_ruin: list = None) -> dict:
    """
    Generate comprehensive risk metrics report.

    Args:
        final_bankrolls: Array of final portfolio values
        max_drawdowns: Array of max drawdowns per simulation
        initial: Initial bankroll
        games_to_ruin: List of games until ruin (for ruined runs)

    Returns:
        Complete risk metrics dictionary
    """
    num_ruined = len(games_to_ruin) if games_to_ruin else 0
    total_runs = len(final_bankrolls) + num_ruined

    return {
        # VaR metrics
        'var': {
            'var_95': calculate_var(final_bankrolls, initial, 0.95),
            'var_99': calculate_var(final_bankrolls, initial, 0.99),
            'var_95_value': calculate_var_percentile(final_bankrolls, 5),
            'var_99_value': calculate_var_percentile(final_bankrolls, 1),
        },
        # CVaR metrics
        'cvar': {
            'cvar_95': calculate_cvar(final_bankrolls, initial, 0.95),
            'cvar_99': calculate_cvar(final_bankrolls, initial, 0.99),
            'cvar_95_value': calculate_cvar_value(final_bankrolls, 5),
            'cvar_99_value': calculate_cvar_value(final_bankrolls, 1),
        },
        # Performance ratios
        'ratios': {
            'sharpe': calculate_sharpe(final_bankrolls, initial),
            'sortino': calculate_sortino(final_bankrolls, initial),
            'calmar': calculate_calmar(final_bankrolls, max_drawdowns, initial),
        },
        # Drawdown metrics
        'drawdown': {
            'mean_max_drawdown': float(np.mean(max_drawdowns)),
            'median_max_drawdown': float(np.median(max_drawdowns)),
            'max_max_drawdown': float(np.max(max_drawdowns)),
            'std_max_drawdown': float(np.std(max_drawdowns)),
        },
        # Ruin metrics
        'ruin': {
            'probability_of_ruin': num_ruined / total_runs,
            'num_ruined': num_ruined,
            'mean_games_to_ruin': float(np.mean(games_to_ruin)) if games_to_ruin else None,
        },
        # Return distribution
        'returns': {
            'mean_return': float(np.mean((final_bankrolls - initial) / initial)),
            'median_return': float(np.median((final_bankrolls - initial) / initial)),
            'std_return': float(np.std((final_bankrolls - initial) / initial)),
            'skewness': float(stats.skew((final_bankrolls - initial) / initial)) if len(final_bankrolls) > 2 else 0,
        },
    }
```

## Risk Metric Interpretation

| Metric | Good | Acceptable | Poor |
|--------|------|------------|------|
| Sharpe Ratio | > 2.0 | 1.0 - 2.0 | < 1.0 |
| Sortino Ratio | > 3.0 | 1.5 - 3.0 | < 1.5 |
| Calmar Ratio | > 1.0 | 0.5 - 1.0 | < 0.5 |
| P(Ruin) | < 1% | 1% - 5% | > 5% |
| Max Drawdown | < 15% | 15% - 30% | > 30% |
| VaR 95% | < 20% | 20% - 40% | > 40% |

## Strategy Comparison Example

| Strategy | Sharpe | Sortino | VaR 95% | P(Ruin) |
|----------|--------|---------|---------|---------|
| Fixed Kelly 0.25 | 1.8 | 2.5 | 18% | 2% |
| Theta-Bayesian | 2.1 | 3.2 | 15% | 1% |
| Anti-Martingale | 1.2 | 1.8 | 35% | 8% |
| Progressive 2x | 0.8 | 1.1 | 55% | 22% |

## Gotchas

1. **Sample Size**: Need 1000+ simulations for stable VaR/CVaR estimates.

2. **VaR vs CVaR**: VaR tells you the threshold; CVaR tells you expected loss beyond it.

3. **Sortino Denominator**: Uses downside std, so can be undefined if no losses.

4. **Drawdown Timing**: Max drawdown might occur early or late in simulation.

5. **Return Horizon**: These metrics assume single simulation period. Annualize for comparison.

6. **Kelly and Ruin**: Full Kelly has ~33% chance of 50% drawdown. Use fractional.

7. **Fat Tails**: Sidebet returns have positive skew (many small losses, few big wins).
