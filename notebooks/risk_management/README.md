# Risk Management & Position Sizing for Sidebet Optimization

Comprehensive risk management analysis suite for rugs.fun sidebet trading strategy.

## Overview

This suite provides production-ready risk management tools for the RL sidebet bot, based on:
- **568 games** of historical data
- **~12K sidebet outcomes** analyzed
- **5:1 payout structure** (need 20% win rate for breakeven)
- **Bayesian probability estimation** from `bayesian_sidebet_analysis.py`

## Key Findings

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Overall Win Rate | 17.4% | Below breakeven (need 20%) |
| Late-game (tick 200-500) | 19.9% | Nearly breakeven |
| Breakeven P(win) for 5x | 20.0% | Target threshold |
| Expected Value at 20% | 0.0 SOL | Neutral |
| Expected Value at 25% | +0.25 SOL | Positive edge |

**Math**: With 5x payout, bet 1 SOL:
- Win: Get 5 SOL back (+4 profit)
- Lose: Lose 1 SOL
- Breakeven: Win 1 in 5 bets = 20%

## Modules

### 1. Position Sizing (`01_position_sizing.py`)

**Purpose**: Determine optimal bet size for each opportunity.

**Strategies Implemented**:
- **Full Kelly**: Maximum growth rate (aggressive)
- **Half Kelly**: Reduced variance (balanced)
- **Quarter Kelly**: Conservative growth (recommended)
- **Fixed Fractional**: Simple constant % (2%, 5%)
- **Volatility-Adjusted Kelly**: Adapts to changing conditions

**Key Formulas**:

```python
# Kelly Criterion
f* = (p × b - q) / b
where:
    p = win probability
    q = 1 - p
    b = net payout odds (4 for 5x payout)

# Example: 25% win rate, 5x payout
f* = (0.25 × 4 - 0.75) / 4 = 0.0625  # 6.25% of bankroll

# Quarter Kelly (recommended)
f_quarter = f* × 0.25 = 0.015625  # ~1.5% of bankroll
```

**Output**:
- Comparison table of all strategies
- Growth rate vs variance tradeoff
- Recommended sizing for different risk profiles
- Plot: `/home/devops/rugs_data/analysis/position_sizing_comparison.png`

**Run**:
```bash
cd /home/devops/Desktop/VECTRA-PLAYER/notebooks/risk_management
python3 01_position_sizing.py
```

---

### 2. Drawdown Analysis (`02_drawdown_analysis.py`)

**Purpose**: Analyze and control drawdowns (losing streaks).

**Features**:
- Maximum Drawdown (MDD) calculation
- Drawdown duration and recovery time
- Monte Carlo simulation of worst-case scenarios
- Ruin probability estimation
- Stop-loss trigger analysis

**Key Metrics**:

```python
# Maximum Drawdown
MDD = max((Peak - Trough) / Peak) × 100%

# Ulcer Index (pain of drawdowns)
UI = sqrt(mean(squared drawdown %))

# Calmar Ratio (return per unit of drawdown risk)
Calmar = Annual Return / MDD
# > 1.0 = good, > 3.0 = excellent

# Value at Risk (95th percentile worst loss)
VaR_95 = 95th percentile of loss distribution

# Expected Shortfall (average loss beyond VaR)
CVaR_95 = mean(losses worse than VaR_95)
```

**Monte Carlo Results** (5000 simulations, 100 bets each):

| Strategy | Mean Final | Mean MDD | P95 MDD | Ruin Prob |
|----------|------------|----------|---------|-----------|
| Quarter Kelly | 1.15 | 12% | 25% | <5% |
| Half Kelly | 1.35 | 18% | 38% | 8% |
| Full Kelly | 1.65 | 28% | 55% | 15% |

**Recommended Stop-Loss Levels**:
- **Conservative**: Stop at 15% drawdown
- **Moderate**: Stop at 25% drawdown
- **Aggressive**: Stop at 40% drawdown

**Output**:
- Monte Carlo simulation plots for each strategy
- Drawdown distribution histograms
- Recovery time analysis
- Plots: `/home/devops/rugs_data/analysis/mc_*.png`

**Run**:
```bash
python3 02_drawdown_analysis.py
```

---

### 3. Risk Metrics Dashboard (`03_risk_metrics_dashboard.py`)

**Purpose**: Comprehensive risk-adjusted performance tracking.

**Metrics Calculated**:

| Category | Metrics |
|----------|---------|
| **Risk-Adjusted Returns** | Sharpe Ratio, Sortino Ratio, Calmar Ratio |
| **Risk Measures** | Max Drawdown, VaR (95%, 99%), CVaR (95%, 99%) |
| **Trade Quality** | Profit Factor, Expectancy, Avg Win/Loss |
| **Streaks** | Longest win/loss streaks, avg streak length |

**Key Formulas**:

```python
# Sharpe Ratio (risk-adjusted returns)
Sharpe = mean(returns) / std(returns)
# > 1.0 = good, > 2.0 = excellent

# Sortino Ratio (downside-only risk)
Sortino = mean(returns) / std(downside_returns)
# Only penalizes losses, not upside volatility

# Profit Factor
PF = gross_profit / gross_loss
# > 1.5 = good, > 2.0 = excellent

# Expectancy (average P&L per trade)
E = (win_rate × avg_win) - (loss_rate × avg_loss)
# Must be > 0 for profitable system
```

**Interpretation Guide**:

| Metric | Poor | Good | Excellent |
|--------|------|------|-----------|
| Sharpe Ratio | < 1.0 | 1.0-2.0 | > 2.0 |
| Sortino Ratio | < 1.5 | 1.5-2.5 | > 2.5 |
| Calmar Ratio | < 1.0 | 1.0-3.0 | > 3.0 |
| Profit Factor | < 1.5 | 1.5-2.0 | > 2.0 |
| Max Drawdown | > 30% | 15-30% | < 15% |

**Output**:
- Complete risk metrics dashboard (6-panel visualization)
- Trade quality scorecard
- Win/loss streak analysis
- Plot: `/home/devops/rugs_data/analysis/risk_metrics_dashboard.png`

**Run**:
```bash
python3 03_risk_metrics_dashboard.py
```

---

### 4. Comprehensive Risk System (`04_comprehensive_risk_system.py`)

**Purpose**: Production-ready integrated risk management system.

**Features**:
- Dynamic position sizing (Kelly-based)
- Real-time drawdown monitoring
- Trading state management (ACTIVE / REDUCED / PAUSED / RECOVERY)
- Automatic stop-loss triggers
- Recovery protocols

**Trading States**:

```
ACTIVE (Normal Trading)
  ↓ (DD > 15% OR 5 consecutive losses)
REDUCED (75% of normal size)
  ↓ (DD > 25% OR 8 consecutive losses OR no win in 20 trades)
PAUSED (No trading)
  ↓ (Manual resume)
RECOVERY (50% of normal size)
  ↓ (50% win rate over 10 trades)
ACTIVE
```

**Risk Configuration** (default):

```python
RiskConfig(
    kelly_fraction=0.25,              # Quarter Kelly
    max_drawdown_pct=25.0,            # Stop at 25% DD
    reduce_size_dd_pct=15.0,          # Reduce at 15% DD
    max_consecutive_losses=8,         # Stop after 8 losses
    reduce_after_losses=5,            # Reduce after 5 losses
    max_trades_without_win=20,        # Stop if no win in 20
    min_win_probability=0.18,         # Don't bet if P(win) < 18%
    recovery_multiplier=0.5           # 50% size in recovery
)
```

**Usage**:

```python
from risk_management.comprehensive_risk_system import RiskManager, RiskConfig

# Initialize
config = RiskConfig(kelly_fraction=0.25)
risk_mgr = RiskManager(initial_bankroll=1.0, config=config)

# For each betting opportunity
p_win = bayesian_model.predict_rug_probability(tick, window=40)

# Check if should bet
should_bet, reason = risk_mgr.should_place_bet(p_win)

if should_bet:
    # Calculate position size
    bet_size = risk_mgr.calculate_position_size(p_win)
    
    # Place bet (in your trading logic)
    # ...
    
    # Record outcome
    outcome = (rug occurred within 40 ticks)
    risk_mgr.record_trade(bet_size, outcome, p_win)
    
    # Check state
    print(f"Trading State: {risk_mgr.state.trading_state}")
    print(f"Current DD: {risk_mgr.state.current_drawdown_pct:.1f}%")
```

**Output**:
- Backtest results with full risk metrics
- State transition timeline
- Equity curve with drawdown overlay
- Position sizing evolution
- Plot: `/home/devops/rugs_data/analysis/comprehensive_risk_system.png`

**Run**:
```bash
python3 04_comprehensive_risk_system.py
```

---

## Integration with RL Bot

### Observation Space

```python
obs = np.array([
    # Game state
    game_age,                  # Ticks since start
    current_price,             # Current multiplier
    distance_from_peak,        # % below peak price
    volatility_10,             # 10-tick volatility
    ticks_since_peak,          # Time since peak
    
    # Bayesian prediction
    p_win_40_ticks,            # From survival model
    expected_value,            # EV of bet
    
    # Risk state
    current_bankroll,
    current_drawdown_pct,
    consecutive_wins,
    consecutive_losses,
    trading_state_encoded,     # 0=ACTIVE, 1=REDUCED, 2=RECOVERY
    
    # Position sizing
    recommended_bet_size,      # From Kelly
])
```

### Action Space

```python
actions = {
    0: HOLD,           # Don't place sidebet
    1: PLACE_BET,      # Place sidebet (size from RiskManager)
}
```

### Reward Function

```python
def calculate_reward(outcome, bet_size, bankroll, state):
    """
    Risk-adjusted reward function.
    """
    if action == HOLD:
        # Small negative for not betting when should
        if p_win > 0.22:
            return -0.01
        return 0.0
    
    elif action == PLACE_BET:
        if outcome:
            # Win: Positive reward
            pnl = bet_size * 4
            base_reward = pnl / bankroll
        else:
            # Loss: Negative reward
            pnl = -bet_size
            base_reward = pnl / bankroll
        
        # Risk adjustment penalties
        penalty = 0.0
        
        # Penalize drawdowns
        if drawdown_pct > 20:
            penalty += 0.1 * (drawdown_pct - 20)
        
        # Penalize consecutive losses
        if consecutive_losses > 5:
            penalty += 0.05 * (consecutive_losses - 5)
        
        # Bonus for good Sharpe ratio
        if sharpe_ratio > 1.5:
            bonus = 0.05
        else:
            bonus = 0.0
        
        return base_reward - penalty + bonus
```

### Training Protocol

1. **Offline RL**: Train on historical games first
   - Initialize Q-values using Bayesian EV estimates
   - Learn state→action mapping for 10K episodes

2. **Safety Constraints**: Hard limits from RiskManager
   - Never override `should_place_bet()` = False
   - Always respect trading state (PAUSED = no action)

3. **Live Deployment**: Gradual rollout
   - Start with 1% of bankroll (micro-stakes)
   - Monitor for 100 trades before increasing
   - Require Sharpe > 1.0 before scaling up

4. **Continuous Monitoring**:
   - Track all RiskMetricsDashboard metrics
   - Alert if Sharpe < 0.8 or MDD > 30%
   - Auto-pause if Calmar < 0.5 (not compensated for risk)

---

## Example Workflow

```bash
# 1. Position Sizing Analysis
cd /home/devops/Desktop/VECTRA-PLAYER/notebooks/risk_management
python3 01_position_sizing.py

# Output: Quarter Kelly recommended (1.5-2% of bankroll per bet)

# 2. Drawdown Analysis
python3 02_drawdown_analysis.py

# Output: 95th percentile MDD = 25%, plan for 2-3 major drawdowns per 100 bets

# 3. Risk Metrics Baseline
python3 03_risk_metrics_dashboard.py

# Output: Target Sharpe > 1.0, Profit Factor > 1.5

# 4. Full System Backtest
python3 04_comprehensive_risk_system.py

# Output: 200-trade backtest, verify positive expectancy

# 5. Deploy to RL Bot
# Copy RiskManager to production environment
# Wrap in RL environment
# Train with safety constraints
```

---

## Files Generated

All analysis outputs saved to: `/home/devops/rugs_data/analysis/`

| File | Description |
|------|-------------|
| `position_sizing_comparison.png` | Strategy comparison (Kelly variants) |
| `mc_full_kelly.png` | Monte Carlo results (Full Kelly) |
| `mc_half_kelly.png` | Monte Carlo results (Half Kelly) |
| `mc_quarter_kelly.png` | Monte Carlo results (Quarter Kelly) |
| `mc_fixed_2%.png` | Monte Carlo results (Fixed 2%) |
| `risk_metrics_dashboard.png` | Comprehensive metrics dashboard |
| `comprehensive_risk_system.png` | Full system backtest results |

---

## Dependencies

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import minimize_scalar
```

All scripts import from:
```python
sys.path.insert(0, '/home/devops/Desktop/VECTRA-PLAYER/notebooks')
from bayesian_sidebet_analysis import (
    load_game_data,
    BayesianSurvivalModel,
    extract_features
)
```

---

## Quick Reference: Key Thresholds

| Metric | Conservative | Moderate | Aggressive |
|--------|--------------|----------|------------|
| **Kelly Fraction** | 0.25 | 0.5 | 1.0 |
| **Max Drawdown Stop** | 15% | 25% | 40% |
| **Consecutive Loss Stop** | 5 | 8 | 12 |
| **Min P(win)** | 20% | 18% | 16% |
| **Target Sharpe** | > 1.5 | > 1.0 | > 0.8 |
| **Target Profit Factor** | > 2.0 | > 1.5 | > 1.2 |

**Recommended for Production**: Start Conservative, increase to Moderate after 100 profitable trades.

---

## Support

For questions or issues:
1. Check Bayesian analysis: `notebooks/bayesian_sidebet_analysis.py`
2. Review risk config: `RiskConfig` dataclass in `04_comprehensive_risk_system.py`
3. Adjust thresholds based on live performance monitoring

---

**Last Updated**: January 7, 2026
**Data Source**: `~/rugs_data/events_parquet/doc_type=complete_game/`
**Author**: Claude (rugs-expert)
