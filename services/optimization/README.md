# Optimization Service

**Version:** 1.0.0 | **Port:** 9020 | **Status:** Complete

Statistical optimization service for rugs.fun trading strategy development. Provides survival analysis, Bayesian rug detection, Kelly criterion position sizing, and Monte Carlo risk simulation.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Modules](#modules)
  - [Survival Analysis](#survival-analysis)
  - [Bayesian Rug Signal](#bayesian-rug-signal)
  - [Kelly Criterion](#kelly-criterion)
  - [Monte Carlo Simulator](#monte-carlo-simulator)
  - [Strategy Profiles](#strategy-profiles)
  - [Optimization Subscriber](#optimization-subscriber)
- [REST API](#rest-api)
- [Configuration](#configuration)
- [Testing](#testing)
- [File Structure](#file-structure)

---

## Quick Start

```bash
cd services/optimization

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start service
python -m src.main
```

Service runs at `http://localhost:9020`. Health check: `GET /health`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Optimization Service (9020)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   Survival   │    │   Bayesian   │    │    Kelly     │       │
│  │   Analysis   │    │  Rug Signal  │    │  Criterion   │       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             │                                    │
│                    ┌────────▼────────┐                           │
│                    │   Monte Carlo   │                           │
│                    │   Simulator     │                           │
│                    └────────┬────────┘                           │
│                             │                                    │
│                    ┌────────▼────────┐                           │
│                    │    Profile      │                           │
│                    │   Producer      │                           │
│                    └────────┬────────┘                           │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐                │
│         │                   │                   │                │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐       │
│  │  Subscriber  │    │   REST API   │    │   Storage    │       │
│  │ (Foundation) │    │   (FastAPI)  │    │  (Parquet)   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
         │                      │
         ▼                      ▼
   Foundation Service      HTTP Clients
   (ws://localhost:9000)   (Artifacts, UI)
```

---

## Modules

### Survival Analysis

**File:** `src/analyzers/survival.py`

Kaplan-Meier survival curves for game duration analysis. Determines optimal sidebet entry timing based on conditional rug probability.

#### Functions

| Function | Description |
|----------|-------------|
| `compute_survival_curve(durations)` | Kaplan-Meier survival function |
| `compute_hazard_rate(durations)` | Instantaneous rug probability |
| `compute_conditional_probability(durations, window_size)` | P(rug within window \| survived to tick) |
| `find_optimal_entry_window(durations, window_size, min_edge)` | Find tick with best edge over breakeven |

#### Example

```python
from src.analyzers.survival import (
    compute_survival_curve,
    compute_conditional_probability,
    find_optimal_entry_window,
)
import numpy as np

# Sample game durations (ticks)
durations = np.array([100, 150, 200, 180, 250, 300, 120, 175, 220, 280])

# Compute survival curve
survival = compute_survival_curve(durations)
print(f"Times: {survival['times'][:5]}")
print(f"Survival: {survival['survival'][:5]}")

# Find optimal entry for 40-tick sidebet window
optimal = find_optimal_entry_window(durations, window_size=40, min_edge=0.02)
print(f"Optimal entry tick: {optimal['optimal_entry_tick']}")
print(f"Win rate at optimal: {optimal['win_rate_at_optimal']:.1%}")
print(f"Edge over breakeven: {optimal['edge_at_optimal']:.1%}")
```

#### Output Schema

```python
# compute_survival_curve returns:
{
    "times": np.ndarray,      # Unique event times
    "survival": np.ndarray,   # S(t) at each time
    "n_at_risk": np.ndarray,  # Number at risk
}

# find_optimal_entry_window returns:
{
    "optimal_entry_tick": int,      # Best tick to enter
    "win_rate_at_optimal": float,   # P(rug within window)
    "edge_at_optimal": float,       # Win rate - breakeven
    "breakeven_rate": float,        # 1/6 for 5:1 payout
}
```

---

### Bayesian Rug Signal

**File:** `src/analyzers/bayesian.py`

Real-time gap detection for pre-rug warning signals. Monitors WebSocket event timing to detect unusual gaps that precede rugs.

#### Classes & Functions

| Component | Description |
|-----------|-------------|
| `RugGapSignalDetector` | Stateful detector tracking event timing |
| `GapSignalResult` | Dataclass with detection result |
| `get_base_rug_probability(tick)` | Base P(rug) from empirical curve |
| `compute_bayesian_rug_probability(tick, signal)` | Bayesian update with signal |
| `BayesianSidebetAdvisor` | Full advisory combining all signals |

#### Gap Thresholds

| Threshold | Gap Duration | Likelihood Ratio |
|-----------|--------------|------------------|
| Normal | ≤350ms | 1.0 |
| Warning | 350-450ms | 2.0 |
| High Alert | 450-500ms | 4.0 |
| Detected | ≥500ms | 8.0 |

#### Example

```python
from src.analyzers.bayesian import (
    RugGapSignalDetector,
    get_base_rug_probability,
    compute_bayesian_rug_probability,
)

# Create detector
detector = RugGapSignalDetector()

# Simulate events
detector.on_event("gameStateUpdate", timestamp=0.0)
detector.on_event("gameStateUpdate", timestamp=0.25)  # Normal 250ms
result = detector.on_event("gameStateUpdate", timestamp=0.75)  # 500ms gap!

print(f"Gap detected: {result.gap_detected}")
print(f"Likelihood ratio: {result.likelihood_ratio}")
print(f"Consecutive gaps: {result.consecutive_gaps}")

# Bayesian probability update
tick = 200
base_prob = get_base_rug_probability(tick)
updated_prob = compute_bayesian_rug_probability(tick, result)
print(f"Base P(rug): {base_prob:.1%}")
print(f"Updated P(rug): {updated_prob:.1%}")
```

#### Output Schema

```python
@dataclass
class GapSignalResult:
    gap_detected: bool          # True if gap >= 500ms
    gap_duration_ms: float      # Actual gap in ms
    likelihood_ratio: float     # 1.0, 2.0, 4.0, or 8.0
    consecutive_gaps: int       # Count of consecutive large gaps
    signal_strength: str        # "none", "warning", "high", "detected"
```

---

### Kelly Criterion

**File:** `src/analyzers/kelly.py`

Position sizing using Kelly criterion with fractional variants for risk management.

#### Functions

| Function | Description |
|----------|-------------|
| `kelly_criterion(win_rate, payout)` | Full Kelly fraction |
| `fractional_kelly(win_rate, fraction, payout)` | Fractional Kelly (e.g., quarter) |
| `calculate_edge(win_rate, payout)` | Edge metrics dictionary |
| `recommend_bet_size(win_rate, bankroll, payout, risk_tolerance)` | Capped recommendation |
| `calculate_all_variants(win_rate, payout)` | All 8 Kelly variants |

#### Kelly Variants

| Variant | Fraction | Risk Level |
|---------|----------|------------|
| Micro | 0.0625 | Ultra-conservative |
| Eighth | 0.125 | Very conservative |
| Quarter | 0.25 | Conservative (recommended) |
| Third | 0.333 | Moderate |
| Half | 0.5 | Aggressive |
| Two-thirds | 0.667 | Very aggressive |
| Three-quarter | 0.75 | High risk |
| Full | 1.0 | Maximum growth (not recommended) |

#### Example

```python
from src.analyzers.kelly import (
    kelly_criterion,
    fractional_kelly,
    calculate_edge,
    recommend_bet_size,
)

# Sidebet: 5:1 payout, estimated 20% win rate
win_rate = 0.20
payout = 5.0

# Full Kelly
full_kelly = kelly_criterion(win_rate, payout)
print(f"Full Kelly: {full_kelly:.1%} of bankroll")

# Quarter Kelly (recommended)
quarter_kelly = fractional_kelly(win_rate, fraction=0.25, payout=payout)
print(f"Quarter Kelly: {quarter_kelly:.1%} of bankroll")

# Edge analysis
edge = calculate_edge(win_rate, payout)
print(f"Expected value: {edge['expected_value']:.1%}")
print(f"Edge exists: {edge['edge_exists']}")
print(f"Breakeven win rate: {edge['breakeven_win_rate']:.1%}")

# Bet recommendation with caps
rec = recommend_bet_size(
    win_rate=win_rate,
    bankroll=0.1,  # 0.1 SOL
    payout=payout,
    risk_tolerance="moderate"
)
print(f"Recommended bet: {rec['recommended_bet_size']:.4f} SOL")
print(f"Capped: {rec['capped']}")
```

#### Output Schema

```python
# calculate_edge returns:
{
    "expected_value": float,       # EV per unit bet
    "breakeven_win_rate": float,   # Win rate for EV=0
    "edge_exists": bool,           # True if EV > 0
    "edge_amount": float,          # win_rate - breakeven
}

# recommend_bet_size returns:
{
    "recommended_bet_size": float,  # In bankroll units
    "kelly_fraction": float,        # Raw Kelly result
    "risk_tolerance": str,          # Input tolerance
    "capped": bool,                 # True if hit max cap
    "max_cap": float,               # 5% of bankroll
}
```

---

### Monte Carlo Simulator

**File:** `src/analyzers/monte_carlo.py`

Risk metrics via 10,000 iteration simulations. Provides probability of ruin, profit, VaR, and Sharpe ratio.

#### Classes

| Class | Description |
|-------|-------------|
| `MonteCarloConfig` | Simulation configuration |
| `MonteCarloSimulator` | Main simulator class |
| `ScalingMode` | Enum: FIXED, KELLY, FRACTIONAL_KELLY |

#### Configuration Options

```python
@dataclass
class MonteCarloConfig:
    initial_bankroll: float = 0.1        # Starting balance
    base_bet_size: float = 0.001         # Base bet amount
    kelly_fraction: float = 0.25         # For FRACTIONAL_KELLY mode
    assumed_win_rate: float = 0.185      # Expected win rate
    payout_multiplier: float = 5.0       # 5:1 sidebet payout
    drawdown_halt: float = 0.15          # Stop at 15% drawdown
    scaling_mode: ScalingMode = ScalingMode.FRACTIONAL_KELLY
```

#### Example

```python
from src.analyzers.monte_carlo import MonteCarloSimulator, MonteCarloConfig

# Configure simulation
config = MonteCarloConfig(
    initial_bankroll=0.1,
    kelly_fraction=0.25,
    assumed_win_rate=0.185,
)

# Run 10k iterations, 500 games each
sim = MonteCarloSimulator(config, seed=42)
results = sim.run(
    num_iterations=10000,
    num_games=500,
    win_rate=0.185,
)

# Summary statistics
print(f"Mean final bankroll: {results['summary']['mean_final_bankroll']:.4f}")
print(f"Median final bankroll: {results['summary']['median_final_bankroll']:.4f}")
print(f"Std dev: {results['summary']['std_final_bankroll']:.4f}")

# Risk metrics
print(f"P(profit): {results['risk_metrics']['probability_profit']:.1%}")
print(f"P(ruin): {results['risk_metrics']['probability_ruin']:.1%}")
print(f"Max drawdown (median): {results['risk_metrics']['median_max_drawdown']:.1%}")

# VaR metrics
print(f"VaR 95%: {results['var_metrics']['var_95']:.4f}")
print(f"VaR 99%: {results['var_metrics']['var_99']:.4f}")
print(f"CVaR 95%: {results['var_metrics']['cvar_95']:.4f}")

# Performance
print(f"Sharpe ratio: {results['performance']['sharpe_ratio']:.2f}")
print(f"Sortino ratio: {results['performance']['sortino_ratio']:.2f}")
```

#### Output Schema

```python
{
    "summary": {
        "mean_final_bankroll": float,
        "median_final_bankroll": float,
        "std_final_bankroll": float,
        "min_final_bankroll": float,
        "max_final_bankroll": float,
        "percentile_5": float,
        "percentile_95": float,
    },
    "risk_metrics": {
        "probability_profit": float,    # P(final > initial)
        "probability_ruin": float,      # P(hit drawdown halt)
        "probability_double": float,    # P(final >= 2*initial)
        "median_max_drawdown": float,
        "worst_drawdown": float,
    },
    "var_metrics": {
        "var_95": float,                # 5th percentile loss
        "var_99": float,                # 1st percentile loss
        "cvar_95": float,               # Expected loss in worst 5%
        "cvar_99": float,
    },
    "performance": {
        "sharpe_ratio": float,          # Return / volatility
        "sortino_ratio": float,         # Return / downside volatility
        "calmar_ratio": float,          # Return / max drawdown
    },
    "config": {...},                    # Input configuration
}
```

---

### Strategy Profiles

**Files:** `src/profiles/models.py`, `src/profiles/producer.py`

Combines all analyzers to produce comprehensive trading profiles.

#### StrategyProfile Dataclass

```python
@dataclass
class StrategyProfile:
    # Identity
    profile_id: str
    created_at: datetime

    # Configuration
    kelly_variant: str              # "quarter", "half", "full"
    min_edge_threshold: float       # 0.02 (2% edge required)
    optimal_entry_tick: int         # From survival analysis

    # Monte Carlo Results
    expected_return: float
    probability_profit: float
    probability_ruin: float
    var_95: float
    sharpe_ratio: float

    # Bayesian Parameters
    base_probability_curve: list | None = None
    gap_signal_thresholds: dict | None = None

    # Live Testing State
    games_played: int = 0
    actual_return: float = 0.0
    predictions_correct: int = 0
```

#### ProfileProducer

```python
from src.profiles.producer import ProfileProducer

# Create producer
producer = ProfileProducer(
    kelly_fraction=0.25,           # Quarter Kelly
    min_edge_threshold=0.02,       # 2% minimum edge
    monte_carlo_iterations=10000,  # 10k MC iterations
)

# Generate profile from game data
games = [
    {"game_id": "abc123", "duration": 200},
    {"game_id": "def456", "duration": 150},
    # ... 100+ games recommended
]

profile = producer.generate_profile(games)

print(f"Profile ID: {profile.profile_id}")
print(f"Kelly variant: {profile.kelly_variant}")
print(f"Optimal entry: tick {profile.optimal_entry_tick}")
print(f"P(profit): {profile.probability_profit:.1%}")
print(f"P(ruin): {profile.probability_ruin:.1%}")
print(f"Sharpe ratio: {profile.sharpe_ratio:.2f}")

# Serialize
data = profile.to_dict()

# Deserialize
restored = StrategyProfile.from_dict(data)
```

---

### Optimization Subscriber

**File:** `src/subscriber.py`

Event subscriber that collects game data and generates profiles automatically.

#### Features

- Listens for `game.tick` events with `rugged=True`
- Collects completed games from `gameHistory`
- Auto-generates profiles after collecting threshold games
- Tracks connection state and statistics

#### Example

```python
from src.subscriber import OptimizationSubscriber
from src.profiles.producer import ProfileProducer

# Create subscriber
subscriber = OptimizationSubscriber(
    client=foundation_client,      # FoundationClient instance
    producer=ProfileProducer(),
    min_games_for_profile=50,      # Generate after 50 games
)

# Statistics
print(f"Games collected: {subscriber.stats.games_collected}")
print(f"Profiles generated: {subscriber.stats.profiles_generated}")

# Current profile
if subscriber.current_profile:
    print(f"Active profile: {subscriber.current_profile.profile_id}")

# Force generation
profile = subscriber.force_generate_profile()

# Get collected games
games = subscriber.get_collected_games()
```

#### OptimizationStats

```python
@dataclass
class OptimizationStats:
    games_collected: int = 0
    profiles_generated: int = 0
    last_profile_time: datetime | None = None
    session_start: datetime = field(default_factory=datetime.utcnow)
```

---

## REST API

**Base URL:** `http://localhost:9020`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/stats` | Service statistics |
| GET | `/profiles` | List all profiles |
| GET | `/profiles/current` | Get active profile |
| POST | `/profiles/generate` | Force profile generation |
| GET | `/games` | List collected games |
| GET | `/analysis/survival` | Survival analysis results |

### Examples

```bash
# Health check
curl http://localhost:9020/health
# {"status":"healthy","service":"optimization-service","uptime_seconds":123.45}

# Get statistics
curl http://localhost:9020/stats
# {"games_collected":150,"profiles_generated":3,...}

# Get current profile
curl http://localhost:9020/profiles/current
# {"profile_id":"profile-abc123","kelly_variant":"quarter",...}

# Force profile generation
curl -X POST http://localhost:9020/profiles/generate
# {"profile_id":"profile-def456",...}

# Get survival analysis
curl http://localhost:9020/analysis/survival
# {"survival_curve":{...},"optimal_entry":{...}}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FOUNDATION_WS_URL` | `ws://localhost:9000/feed` | Foundation WebSocket URL |
| `OPTIMIZATION_SERVICE_PORT` | `9020` | API port |
| `MONTE_CARLO_ITERATIONS` | `10000` | MC simulation iterations |
| `KELLY_FRACTION` | `0.25` | Kelly fraction (quarter) |
| `STORAGE_PATH` | `~/rugs_data/strategy_profiles` | Profile storage |

### Config File

**Location:** `config/config.yaml`

```yaml
foundation_ws_url: ws://localhost:9000/feed
storage_path: ~/rugs_data/strategy_profiles
port: 9020
host: 0.0.0.0

# Analysis parameters
monte_carlo_iterations: 10000
kelly_fraction: 0.25
min_edge_threshold: 0.02
min_games_for_profile: 50

# Bayesian thresholds
gap_warning_threshold_ms: 350
gap_high_alert_threshold_ms: 450
gap_detected_threshold_ms: 500
```

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/test_survival.py -v
python -m pytest tests/test_bayesian.py -v
python -m pytest tests/test_kelly.py -v
python -m pytest tests/test_monte_carlo.py -v
python -m pytest tests/test_profile.py -v
python -m pytest tests/test_subscriber.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

### Test Summary

| Module | Tests | Status |
|--------|-------|--------|
| Survival Analysis | 4 | ✅ |
| Bayesian Rug Signal | 5 | ✅ |
| Kelly Criterion | 5 | ✅ |
| Monte Carlo | 4 | ✅ |
| Strategy Profiles | 3 | ✅ |
| Subscriber | 4 | ✅ |
| **Total** | **25** | ✅ |

---

## File Structure

```
services/optimization/
├── manifest.json               # Service manifest
├── requirements.txt            # Python dependencies
├── start.sh                    # Startup script
├── README.md                   # This file
│
├── config/
│   └── config.yaml             # Service configuration
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── subscriber.py           # Event subscriber
│   │
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── survival.py         # Kaplan-Meier survival analysis
│   │   ├── bayesian.py         # Gap-based rug detection
│   │   ├── kelly.py            # Kelly criterion sizing
│   │   └── monte_carlo.py      # Risk simulation
│   │
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── models.py           # StrategyProfile dataclass
│   │   └── producer.py         # Profile generator
│   │
│   └── api/
│       ├── __init__.py
│       └── endpoints.py        # FastAPI routes
│
└── tests/
    ├── __init__.py
    ├── test_survival.py
    ├── test_bayesian.py
    ├── test_kelly.py
    ├── test_monte_carlo.py
    ├── test_profile.py
    └── test_subscriber.py
```

---

## Canonical Constants

### Sidebet Mechanics

| Constant | Value | Source |
|----------|-------|--------|
| Payout | 5:1 (400% net) | Protocol |
| Window | 40 ticks | Protocol |
| Breakeven | 16.67% | Math: 1/6 |
| Tick duration | 250ms (theoretical) | Protocol |

### Game Statistics (10,810 games)

| Metric | Value |
|--------|-------|
| Mean duration | 200.9 ticks |
| Median duration | 145 ticks |
| Std deviation | 193.5 ticks |
| 25th percentile | 57 ticks |
| 75th percentile | 292 ticks |
| 95th percentile | 571 ticks |

---

*Generated: January 29, 2026 | Optimization Service v1.0.0*
