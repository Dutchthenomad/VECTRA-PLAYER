# Statistical Optimization Integration Guide

> Companion addendum for integrating statistical optimization from VECTRA-PLAYER into VECTRA-BOILERPLATE.

**Version:** 1.0.0 | **Date:** 2026-01-29

---

## Overview

This guide documents how the statistical optimization systems from VECTRA-PLAYER have been integrated into VECTRA-BOILERPLATE as the Optimization Service (port 9020).

## Architecture

```
Foundation Service (9000/9001)
         │
         ▼ game.tick events
┌────────────────────────┐
│  Optimization Service  │
│      (port 9020)       │
├────────────────────────┤
│ - Survival Analysis    │
│ - Bayesian Rug Signal  │
│ - Kelly Criterion      │
│ - Monte Carlo Sim      │
│ - Profile Producer     │
└────────────────────────┘
         │
         ▼ REST API
   Strategy Profiles
```

## Modules

### Survival Analysis (`src/analyzers/survival.py`)

Kaplan-Meier survival curves for game duration analysis.

```python
from src.analyzers.survival import (
    compute_survival_curve,
    compute_conditional_probability,
    find_optimal_entry_window,
)

# Find optimal sidebet entry point
optimal = find_optimal_entry_window(durations, window_size=40, min_edge=0.02)
print(f"Optimal entry: tick {optimal['optimal_entry_tick']}")
```

### Bayesian Rug Signal (`src/analyzers/bayesian.py`)

Gap-based rug detection with likelihood ratio updates.

```python
from src.analyzers.bayesian import RugGapSignalDetector

detector = RugGapSignalDetector()
detector.on_event("gameStateUpdate", timestamp=0.0)
result = detector.on_event("gameStateUpdate", timestamp=0.5)  # 500ms gap
# result.gap_detected = True, result.likelihood_ratio = 8.0
```

### Kelly Criterion (`src/analyzers/kelly.py`)

Position sizing with 8 Kelly variants.

```python
from src.analyzers.kelly import fractional_kelly, calculate_edge

# Quarter Kelly for 20% win rate, 5:1 payout
bet_fraction = fractional_kelly(win_rate=0.20, fraction=0.25, payout=5.0)
edge = calculate_edge(win_rate=0.20, payout=5.0)
```

### Monte Carlo Simulator (`src/analyzers/monte_carlo.py`)

Risk metrics via 10k iteration simulations.

```python
from src.analyzers.monte_carlo import MonteCarloSimulator, MonteCarloConfig

config = MonteCarloConfig(kelly_fraction=0.25, assumed_win_rate=0.185)
sim = MonteCarloSimulator(config, seed=42)
results = sim.run(num_iterations=10000, num_games=500, win_rate=0.185)
# results["risk_metrics"]["probability_ruin"]
# results["performance"]["sharpe_ratio"]
```

### Profile Producer (`src/profiles/producer.py`)

Generates Strategy Profiles from game data.

```python
from src.profiles.producer import ProfileProducer

producer = ProfileProducer(kelly_fraction=0.25, monte_carlo_iterations=10000)
profile = producer.generate_profile(games)
# profile.optimal_entry_tick, profile.probability_profit, etc.
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/stats` | GET | Service statistics |
| `/profiles` | GET | List profiles |
| `/profiles/current` | GET | Current profile |
| `/profiles/generate` | POST | Force generation |
| `/games` | GET | Collected games |
| `/analysis/survival` | GET | Survival analysis |

## Configuration

### Environment Variables

```bash
FOUNDATION_WS_URL=ws://localhost:9000/feed
OPTIMIZATION_SERVICE_PORT=9020
MONTE_CARLO_ITERATIONS=10000
KELLY_FRACTION=0.25
```

### Config File (`config/config.yaml`)

```yaml
foundation_ws_url: ws://localhost:9000/feed
port: 9020
monte_carlo_iterations: 10000
kelly_fraction: 0.25
min_games_for_profile: 50
```

## Running the Service

```bash
cd services/optimization

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start service
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --host 0.0.0.0 --port 9020
```

## Testing

```bash
cd services/optimization
source .venv/bin/activate
python -m pytest tests/ -v
```

## Canonical Constants

### Sidebet Mechanics

| Constant | Value |
|----------|-------|
| Sidebet payout | 5:1 (400% net profit) |
| Sidebet window | 40 ticks |
| Breakeven win rate | 16.67% (1/6) |
| Tick duration | 250ms theoretical |

### Gap Signal Thresholds

| Threshold | Value |
|-----------|-------|
| Warning | 350ms |
| High Alert | 450ms |
| Detected | 500ms |

## Source Origins

Algorithms ported from VECTRA-PLAYER documentation:

- `survival_analysis.py` → Kaplan-Meier curves
- `bayesian_updater.py` → Gap detection
- `kelly_sizing.py` → Position sizing
- `monte_carlo_sim.py` → Risk simulation

---

*January 29, 2026 | Optimization Service v1.0.0*
