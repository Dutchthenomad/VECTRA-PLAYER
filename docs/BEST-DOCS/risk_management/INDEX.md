# Risk Management Suite - File Index

## Quick Navigation

| File | Type | Purpose | Lines |
|------|------|---------|-------|
| **00_run_all_analyses.py** | Script | Master runner for all analyses | ~150 |
| **01_position_sizing.py** | Analysis | Kelly Criterion & sizing strategies | ~550 |
| **02_drawdown_analysis.py** | Analysis | Drawdown control & Monte Carlo | ~600 |
| **03_risk_metrics_dashboard.py** | Analysis | Comprehensive risk metrics | ~550 |
| **04_comprehensive_risk_system.py** | System | Production RiskManager class | ~650 |
| **README.md** | Docs | User guide & quick reference | ~400 |
| **IMPLEMENTATION_GUIDE.md** | Docs | Production deployment guide | ~600 |
| **SUMMARY.md** | Docs | Formulas & key concepts | ~500 |
| **INDEX.md** | Docs | This file | ~100 |

**Total**: ~4,000 lines of production-ready code and documentation

---

## Read First

1. **SUMMARY.md** - Understand the math and key concepts
2. **README.md** - Learn what each module does
3. Run **00_run_all_analyses.py** - Generate all plots
4. **IMPLEMENTATION_GUIDE.md** - Deploy to production

---

## Code Modules

### 01_position_sizing.py

**Purpose**: Compare position sizing strategies

**Functions**:
- `kelly_criterion()` - Full/half/quarter Kelly calculation
- `fixed_fractional()` - Simple constant % betting
- `anti_martingale()` - Increase after wins
- `optimal_f()` - Ralph Vince's optimal fraction
- `volatility_adjusted_kelly()` - Risk-scaled Kelly
- `compare_strategies()` - Backtest all strategies
- `plot_strategy_comparison()` - Visualize results

**Run**: `python3 01_position_sizing.py`
**Output**: `position_sizing_comparison.png`

---

### 02_drawdown_analysis.py

**Purpose**: Analyze and control drawdowns

**Functions**:
- `calculate_drawdowns()` - Identify all DD events
- `maximum_drawdown()` - Find MDD
- `ulcer_index()` - DD pain metric
- `calmar_ratio()` - Return / MDD
- `monte_carlo_simulation()` - 5000-run risk analysis
- `ruin_probability_analytic()` - Bankruptcy risk
- `plot_drawdown_analysis()` - Equity + DD charts
- `plot_monte_carlo_results()` - Distribution plots

**Run**: `python3 02_drawdown_analysis.py`
**Output**: `mc_*.png` (4 files, one per strategy)

---

### 03_risk_metrics_dashboard.py

**Purpose**: Comprehensive performance metrics

**Functions**:
- `sharpe_ratio()` - Risk-adjusted returns
- `sortino_ratio()` - Downside-only risk
- `calmar_ratio()` - Return per DD
- `value_at_risk()` - 95th/99th percentile loss
- `expected_shortfall()` - CVaR (tail risk)
- `profit_factor()` - Gross profit / loss
- `expectancy()` - Avg P&L per trade
- `analyze_streaks()` - Win/loss streaks
- `calculate_risk_dashboard()` - All metrics
- `print_risk_dashboard()` - Formatted output
- `plot_risk_dashboard()` - 6-panel visualization

**Run**: `python3 03_risk_metrics_dashboard.py`
**Output**: `risk_metrics_dashboard.png`

---

### 04_comprehensive_risk_system.py

**Purpose**: Production-ready risk management system

**Classes**:
- `TradingState` - Enum (ACTIVE/REDUCED/PAUSED/RECOVERY)
- `AccountState` - Current account state
- `RiskConfig` - Configuration dataclass
- `RiskManager` - Main risk management class

**RiskManager Methods**:
- `calculate_position_size(p_win)` - Kelly-based sizing
- `should_place_bet(p_win)` - Pre-trade checks
- `record_trade(bet, outcome, p_win)` - Update state
- `resume_trading()` - Manual restart after pause
- `get_summary()` - Performance metrics

**Functions**:
- `backtest_risk_system()` - Historical backtest
- `plot_backtest_results()` - 6-panel results

**Run**: `python3 04_comprehensive_risk_system.py`
**Output**: `comprehensive_risk_system.png`

---

## Documentation Files

### README.md

**Sections**:
1. Overview & key findings
2. Module descriptions
3. Event category taxonomy
4. Key events reference
5. Game cycle phases
6. Integration guide
7. Example workflow

**Audience**: Developers integrating risk management

---

### IMPLEMENTATION_GUIDE.md

**Sections**:
1. Executive summary
2. Module overview
3. The math (breakeven analysis)
4. Position sizing formulas
5. Risk controls (state machine)
6. Risk metrics explanations
7. Production integration code
8. Monitoring & alerts
9. Expected performance
10. Common pitfalls
11. Validation checklist

**Audience**: Production deployment engineers

---

### SUMMARY.md

**Sections**:
1. What was built
2. Key formulas with explanations (10 formulas)
3. Practical thresholds
4. How to combine into system
5. RL integration example
6. Visualization guide
7. Quick start
8. Deliverables checklist

**Audience**: Quick reference for all users

---

## Data Flow

```
Bayesian Analysis (existing)
    ↓
    Predicts P(win) for current tick
    ↓
RiskManager.should_place_bet(p_win)
    ↓
    Checks: min P(win), positive EV, trading state
    ↓ (if approved)
RiskManager.calculate_position_size(p_win)
    ↓
    Kelly calculation + state adjustments
    ↓
Place bet (your trading logic)
    ↓
Observe outcome
    ↓
RiskManager.record_trade(bet, outcome, p_win)
    ↓
    Updates: bankroll, DD, streaks, trading state
    ↓
Repeat
```

---

## Key Classes & Dataclasses

```python
# Trading State Enum
class TradingState(Enum):
    ACTIVE = "active"
    REDUCED = "reduced"
    PAUSED = "paused"
    RECOVERY = "recovery"

# Risk Configuration
@dataclass
class RiskConfig:
    kelly_fraction: float = 0.25
    max_drawdown_pct: float = 25.0
    reduce_size_dd_pct: float = 15.0
    max_consecutive_losses: int = 8
    min_win_probability: float = 0.18
    payout_multiplier: int = 5
    # ... more fields

# Account State
@dataclass
class AccountState:
    bankroll: float
    peak_bankroll: float
    current_drawdown_pct: float
    consecutive_wins: int
    consecutive_losses: int
    total_trades: int
    trading_state: TradingState
    equity_curve: List[float]
    # ... more fields

# Risk Metrics
@dataclass
class RiskMetricsDashboard:
    total_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    # ... 15+ metrics
```

---

## Dependencies

All modules require:
```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import minimize_scalar
```

Plus from existing code:
```python
from bayesian_sidebet_analysis import (
    load_game_data,
    BayesianSurvivalModel,
    extract_features
)
```

---

## Testing

Run full test suite:
```bash
cd /home/devops/Desktop/VECTRA-PLAYER/notebooks/risk_management
python3 00_run_all_analyses.py
```

Expected output:
- 7-10 PNG plots in `/home/devops/rugs_data/analysis/`
- Console summary with performance metrics
- Deployment readiness checklist
- Runtime: ~3 minutes

---

## Integration Points

### 1. Import RiskManager

```python
from risk_management.comprehensive_risk_system import RiskManager, RiskConfig

config = RiskConfig(kelly_fraction=0.25)
risk_mgr = RiskManager(initial_bankroll=1.0, config=config)
```

### 2. Use in Trading Loop

```python
for game in games:
    # Get prediction
    p_win = bayesian_model.predict(tick, features)

    # Check if should bet
    should_bet, reason = risk_mgr.should_place_bet(p_win)

    if should_bet:
        # Calculate bet size
        bet = risk_mgr.calculate_position_size(p_win)

        # Place bet (your code)
        outcome = place_sidebet(bet)

        # Record trade
        risk_mgr.record_trade(bet, outcome, p_win)
```

### 3. Monitor State

```python
# Check current state
print(f"State: {risk_mgr.state.trading_state}")
print(f"Bankroll: {risk_mgr.state.bankroll:.4f}")
print(f"Drawdown: {risk_mgr.state.current_drawdown_pct:.1f}%")

# Get full summary
summary = risk_mgr.get_summary()
print(summary)
```

---

## Output Files

After running `00_run_all_analyses.py`:

```
/home/devops/rugs_data/analysis/
├── position_sizing_comparison.png       # Strategy comparison
├── mc_full_kelly.png                    # Full Kelly MC
├── mc_half_kelly.png                    # Half Kelly MC
├── mc_quarter_kelly.png                 # Quarter Kelly MC
├── mc_fixed_2%.png                      # Fixed 2% MC
├── risk_metrics_dashboard.png           # All metrics
└── comprehensive_risk_system.png        # Full backtest
```

---

## Recommended Reading Order

1. **SUMMARY.md** - Get oriented with formulas
2. **README.md** - Understand each module
3. Run **00_run_all_analyses.py** - See it work
4. Review plots in `/home/devops/rugs_data/analysis/`
5. **IMPLEMENTATION_GUIDE.md** - Deploy to production
6. Study code in modules 01-04
7. Integrate **RiskManager** into RL bot

---

## Support & Troubleshooting

**Issue**: Import error for `bayesian_sidebet_analysis`
**Fix**: Ensure path is in sys.path:
```python
sys.path.insert(0, '/home/devops/Desktop/VECTRA-PLAYER/notebooks')
```

**Issue**: No data found
**Fix**: Check data exists:
```bash
ls ~/rugs_data/events_parquet/doc_type=complete_game/
```

**Issue**: Plots not saving
**Fix**: Create directory:
```bash
mkdir -p /home/devops/rugs_data/analysis
```

---

## Version History

- **v1.0** (Jan 7, 2026): Initial release
  - 4 analysis modules
  - 3 documentation files
  - Production-ready RiskManager class
  - Complete RL integration guide

---

**Last Updated**: January 7, 2026
**Status**: Production-ready
**Next**: Run `00_run_all_analyses.py`

---
