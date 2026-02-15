# 10 - Monte Carlo Comparison (Explorer Tab)

## Purpose

Run Monte Carlo simulations to compare 8 position sizing strategies:
1. 10,000+ iteration statistical reliability
2. Risk-adjusted performance metrics
3. Strategy ranking and selection
4. Distribution analysis

## Dependencies

```python
# Monte Carlo modules
from recording_ui.services.monte_carlo import (
    MonteCarloSimulator,
    MonteCarloConfig,
    ScalingMode,
    run_single_simulation,
)
from recording_ui.services.monte_carlo_service import (
    run_strategy_comparison,
    create_strategy_configs,
    STRATEGY_DESCRIPTIONS,
)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     Monte Carlo Comparison Engine                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Strategy Configurations (8)                     │    │
│  ├─────────────────────────────────────────────────────────────────────┤    │
│  │  fixed_conservative   │ Fixed 0.001 SOL per bet                    │    │
│  │  fixed_aggressive     │ Fixed 0.005 SOL per bet                    │    │
│  │  kelly_conservative   │ 0.25 Kelly fraction                        │    │
│  │  kelly_aggressive     │ 0.50 Kelly fraction                        │    │
│  │  anti_martingale      │ Double on win streak                       │    │
│  │  theta_bayesian_cons  │ Adaptive theta (conservative)              │    │
│  │  theta_bayesian_aggr  │ Adaptive theta (aggressive)                │    │
│  │  volatility_adjusted  │ Scale by game volatility                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Monte Carlo Loop                                │    │
│  │  for iteration in 1..N:                                             │    │
│  │      for game in 1..500:                                            │    │
│  │          outcome = sample_outcome(win_rate, volatility)             │    │
│  │          bet_size = strategy.calculate_bet(state)                   │    │
│  │          update_bankroll(outcome, bet_size)                         │    │
│  │          check_circuit_breakers()                                   │    │
│  │      record_final_bankroll()                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Results Aggregation                             │    │
│  │  - Final bankroll distribution                                      │    │
│  │  - Risk metrics (VaR, Sharpe, Sortino)                             │    │
│  │  - Probability of profit/2x/ruin                                   │    │
│  │  - Strategy ranking                                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Strategy Configuration

```python
# src/recording_ui/services/monte_carlo.py

from enum import Enum
from dataclasses import dataclass

class ScalingMode(Enum):
    """Position sizing strategy"""
    FIXED = "fixed"
    KELLY = "kelly"
    AGGRESSIVE_KELLY = "aggressive_kelly"
    ANTI_MARTINGALE = "anti_martingale"
    THETA_BAYESIAN = "theta_bayesian"
    VOLATILITY_ADJUSTED = "volatility_adjusted"

@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation"""
    # Strategy
    scaling_mode: ScalingMode = ScalingMode.FIXED
    base_bet_size: float = 0.001  # SOL
    num_bets_per_game: int = 4

    # Kelly parameters
    kelly_fraction: float = 0.25  # Fractional Kelly
    assumed_win_rate: float = 0.185

    # Anti-martingale parameters
    win_streak_multiplier: float = 1.5
    max_streak_multiplier: float = 4.0

    # Theta-Bayesian parameters
    theta_base: float = 0.5
    theta_max: float = 2.0
    theta_scale: int = 100  # Games for theta to reach midpoint

    # Volatility adjustment
    use_volatility_scaling: bool = False
    volatility_base: float = 0.102917  # Historical average

    # Risk controls
    initial_bankroll: float = 0.1
    drawdown_halt: float = 0.15  # 15% drawdown circuit breaker
    take_profit_target: float | None = None
```

### 2. Strategy Definitions

```python
# src/recording_ui/services/monte_carlo_service.py

STRATEGY_DESCRIPTIONS = {
    "fixed_conservative": {
        "name": "Fixed Conservative",
        "description": "Fixed 0.001 SOL per bet",
        "risk_level": "Low",
        "category": "Fixed",
    },
    "fixed_aggressive": {
        "name": "Fixed Aggressive",
        "description": "Fixed 0.005 SOL per bet",
        "risk_level": "Medium",
        "category": "Fixed",
    },
    "kelly_conservative": {
        "name": "Kelly Conservative",
        "description": "0.25 Kelly fraction",
        "risk_level": "Medium",
        "category": "Kelly",
    },
    "kelly_aggressive": {
        "name": "Kelly Aggressive",
        "description": "0.50 Kelly fraction",
        "risk_level": "High",
        "category": "Kelly",
    },
    "anti_martingale": {
        "name": "Anti-Martingale",
        "description": "Increase on win streak",
        "risk_level": "High",
        "category": "Progressive",
    },
    "theta_bayesian_conservative": {
        "name": "Theta-Bayesian Conservative",
        "description": "Adaptive theta (0.5-2.0)",
        "risk_level": "Medium",
        "category": "Adaptive",
    },
    "theta_bayesian_aggressive": {
        "name": "Theta-Bayesian Aggressive",
        "description": "Adaptive theta (0.8-3.0)",
        "risk_level": "High",
        "category": "Adaptive",
    },
    "volatility_adjusted": {
        "name": "Volatility-Adjusted",
        "description": "Scale by game volatility",
        "risk_level": "Medium",
        "category": "Adaptive",
    },
}

def create_strategy_configs(num_iterations: int = 10000) -> dict[str, MonteCarloConfig]:
    """Create configurations for all 8 strategies"""
    return {
        "fixed_conservative": MonteCarloConfig(
            scaling_mode=ScalingMode.FIXED,
            base_bet_size=0.001,
        ),
        "fixed_aggressive": MonteCarloConfig(
            scaling_mode=ScalingMode.FIXED,
            base_bet_size=0.005,
        ),
        "kelly_conservative": MonteCarloConfig(
            scaling_mode=ScalingMode.KELLY,
            kelly_fraction=0.25,
        ),
        "kelly_aggressive": MonteCarloConfig(
            scaling_mode=ScalingMode.AGGRESSIVE_KELLY,
            kelly_fraction=0.50,
        ),
        "anti_martingale": MonteCarloConfig(
            scaling_mode=ScalingMode.ANTI_MARTINGALE,
            win_streak_multiplier=1.5,
            max_streak_multiplier=4.0,
        ),
        "theta_bayesian_conservative": MonteCarloConfig(
            scaling_mode=ScalingMode.THETA_BAYESIAN,
            theta_base=0.5,
            theta_max=2.0,
            theta_scale=100,
        ),
        "theta_bayesian_aggressive": MonteCarloConfig(
            scaling_mode=ScalingMode.THETA_BAYESIAN,
            theta_base=0.8,
            theta_max=3.0,
            theta_scale=50,
        ),
        "volatility_adjusted": MonteCarloConfig(
            scaling_mode=ScalingMode.VOLATILITY_ADJUSTED,
            use_volatility_scaling=True,
        ),
    }
```

### 3. Monte Carlo Simulation Core

```python
# src/recording_ui/services/monte_carlo.py

import numpy as np

class MonteCarloSimulator:
    """Run Monte Carlo simulation for a single strategy"""

    def __init__(self, config: MonteCarloConfig):
        self.config = config
        self.rng = np.random.default_rng()

    def run(self, num_iterations: int = 10000, num_games: int = 500,
            win_rate: float = 0.185) -> dict:
        """
        Run Monte Carlo simulation.

        Args:
            num_iterations: Number of simulation runs
            num_games: Games per simulation
            win_rate: Probability of winning each bet

        Returns:
            Dict with final bankrolls and statistics
        """
        final_bankrolls = []
        max_drawdowns = []
        games_to_ruin = []  # How many games until bankrupt

        for _ in range(num_iterations):
            bankroll = self.config.initial_bankroll
            peak = bankroll
            max_dd = 0.0
            win_streak = 0
            games_played = 0
            ruined = False

            for game in range(num_games):
                if bankroll <= 0.001:  # Effectively bankrupt
                    ruined = True
                    games_to_ruin.append(games_played)
                    break

                games_played += 1

                # Sample volatility for this game
                game_volatility = self.rng.lognormal(
                    np.log(self.config.volatility_base), 0.3
                )

                # Place bets for this game
                for bet_num in range(1, self.config.num_bets_per_game + 1):
                    # Calculate bet size
                    bet_size = self._calculate_bet_size(
                        bankroll, win_streak, games_played, game_volatility
                    )
                    bet_size = min(bet_size, bankroll)

                    if bet_size <= 0:
                        continue

                    # Sample outcome
                    won = self.rng.random() < win_rate

                    if won:
                        bankroll += bet_size * 4  # 5:1 payout (net +4)
                        win_streak += 1
                    else:
                        bankroll -= bet_size
                        win_streak = 0

                    # Update peak/drawdown
                    if bankroll > peak:
                        peak = bankroll
                    dd = (peak - bankroll) / peak if peak > 0 else 0
                    max_dd = max(max_dd, dd)

                    # Circuit breaker
                    if dd >= self.config.drawdown_halt:
                        break

            if not ruined:
                final_bankrolls.append(bankroll)
            max_drawdowns.append(max_dd)

        return self._aggregate_results(final_bankrolls, max_drawdowns, games_to_ruin)

    def _calculate_bet_size(self, bankroll: float, win_streak: int,
                            games_played: int, volatility: float) -> float:
        """Calculate bet size based on strategy"""
        base = self.config.base_bet_size

        if self.config.scaling_mode == ScalingMode.FIXED:
            return base

        elif self.config.scaling_mode == ScalingMode.KELLY:
            kelly = self._kelly_fraction(self.config.assumed_win_rate)
            return bankroll * kelly * self.config.kelly_fraction

        elif self.config.scaling_mode == ScalingMode.AGGRESSIVE_KELLY:
            kelly = self._kelly_fraction(self.config.assumed_win_rate)
            return bankroll * kelly * self.config.kelly_fraction

        elif self.config.scaling_mode == ScalingMode.ANTI_MARTINGALE:
            multiplier = min(
                self.config.win_streak_multiplier ** win_streak,
                self.config.max_streak_multiplier
            )
            return base * multiplier

        elif self.config.scaling_mode == ScalingMode.THETA_BAYESIAN:
            # Theta increases with experience
            theta = self.config.theta_base + (
                (self.config.theta_max - self.config.theta_base) *
                (1 - 1 / (1 + games_played / self.config.theta_scale))
            )
            return base * theta

        elif self.config.scaling_mode == ScalingMode.VOLATILITY_ADJUSTED:
            vol_ratio = volatility / self.config.volatility_base
            # Reduce bet in high volatility, increase in low
            vol_adj = 1 / vol_ratio if vol_ratio > 0 else 1
            return base * min(2.0, max(0.5, vol_adj))

        return base

    def _kelly_fraction(self, win_rate: float) -> float:
        """Calculate Kelly fraction for 5:1 payout"""
        p = win_rate
        q = 1 - p
        b = 4  # Net odds (5:1 = +4 on win)
        kelly = (p * b - q) / b
        return max(0, kelly)  # Never negative

    def _aggregate_results(self, final_bankrolls, max_drawdowns, games_to_ruin) -> dict:
        """Aggregate simulation results"""
        fb = np.array(final_bankrolls) if final_bankrolls else np.array([0])
        dd = np.array(max_drawdowns)

        return {
            "summary": {
                "mean_final_bankroll": float(np.mean(fb)),
                "median_final_bankroll": float(np.median(fb)),
                "std_final_bankroll": float(np.std(fb)),
                "min_final_bankroll": float(np.min(fb)),
                "max_final_bankroll": float(np.max(fb)),
            },
            "risk_metrics": {
                "probability_profit": float(np.mean(fb > self.config.initial_bankroll)),
                "probability_2x": float(np.mean(fb > self.config.initial_bankroll * 2)),
                "probability_ruin": float(len(games_to_ruin) / (len(fb) + len(games_to_ruin))),
            },
            "drawdown": {
                "mean_max_drawdown": float(np.mean(dd)),
                "median_max_drawdown": float(np.median(dd)),
            },
            "performance": {
                "sharpe_ratio": self._calc_sharpe(fb),
                "sortino_ratio": self._calc_sortino(fb),
                "calmar_ratio": self._calc_calmar(fb, dd),
            },
            "var_metrics": {
                "var_95": float(np.percentile(fb, 5)),
                "var_99": float(np.percentile(fb, 1)),
                "cvar_95": float(np.mean(fb[fb <= np.percentile(fb, 5)])) if len(fb) > 20 else 0,
            },
            "distribution": {
                "p10": float(np.percentile(fb, 10)),
                "p25": float(np.percentile(fb, 25)),
                "p50": float(np.percentile(fb, 50)),
                "p75": float(np.percentile(fb, 75)),
                "p90": float(np.percentile(fb, 90)),
            },
        }
```

### 4. Strategy Comparison Service

```python
# src/recording_ui/services/monte_carlo_service.py

def run_strategy_comparison(num_iterations: int = 10000,
                            initial_bankroll: float = 0.1,
                            win_rate: float = 0.185,
                            num_games: int = 500) -> dict:
    """
    Run Monte Carlo comparison across all 8 strategies.

    Returns:
        Dict with results for each strategy plus ranking
    """
    import time
    start_time = time.time()

    configs = create_strategy_configs()
    results = {}

    for strategy_key, config in configs.items():
        config.initial_bankroll = initial_bankroll

        simulator = MonteCarloSimulator(config)
        strategy_results = simulator.run(
            num_iterations=num_iterations,
            num_games=num_games,
            win_rate=win_rate,
        )

        results[strategy_key] = {
            **strategy_results,
            "meta": STRATEGY_DESCRIPTIONS[strategy_key],
        }

    # Rank strategies
    rankings = calculate_rankings(results)

    return {
        "strategies": results,
        "rankings": rankings,
        "config": {
            "num_iterations": num_iterations,
            "initial_bankroll": initial_bankroll,
            "win_rate": win_rate,
            "num_games": num_games,
        },
        "computation_time_seconds": time.time() - start_time,
    }

def calculate_rankings(results: dict) -> dict:
    """Rank strategies by multiple criteria"""
    rankings = {
        "by_median_return": [],
        "by_sharpe": [],
        "by_probability_profit": [],
        "by_lowest_drawdown": [],
    }

    # Sort by median final bankroll
    rankings["by_median_return"] = sorted(
        results.keys(),
        key=lambda k: results[k]["summary"]["median_final_bankroll"],
        reverse=True
    )

    # Sort by Sharpe ratio
    rankings["by_sharpe"] = sorted(
        results.keys(),
        key=lambda k: results[k]["performance"]["sharpe_ratio"],
        reverse=True
    )

    # Sort by probability of profit
    rankings["by_probability_profit"] = sorted(
        results.keys(),
        key=lambda k: results[k]["risk_metrics"]["probability_profit"],
        reverse=True
    )

    # Sort by lowest drawdown
    rankings["by_lowest_drawdown"] = sorted(
        results.keys(),
        key=lambda k: results[k]["drawdown"]["mean_max_drawdown"]
    )

    return rankings
```

### 5. API Endpoint

```python
# src/recording_ui/app.py

@app.route("/api/explorer/monte-carlo", methods=["POST"])
def api_explorer_monte_carlo():
    """Run Monte Carlo comparison across all strategies."""
    data = request.get_json() or {}

    # Validate iterations (only 1k, 10k, 100k)
    num_iterations = data.get("num_iterations", 10000)
    if num_iterations not in [1000, 10000, 100000]:
        num_iterations = 10000

    results = run_strategy_comparison(
        num_iterations=num_iterations,
        initial_bankroll=data.get("initial_bankroll", 0.1),
        win_rate=data.get("win_rate", 0.185),
        num_games=data.get("num_games", 500),
    )

    return jsonify(results)
```

## The 8 Strategies

| Strategy | Description | Risk Level | Best For |
|----------|-------------|------------|----------|
| Fixed Conservative | 0.001 SOL/bet | Low | Preservation |
| Fixed Aggressive | 0.005 SOL/bet | Medium | Moderate growth |
| Kelly Conservative | 0.25 Kelly | Medium | Optimal growth |
| Kelly Aggressive | 0.50 Kelly | High | Aggressive growth |
| Anti-Martingale | 1.5x on win | High | Trend capture |
| Theta-Bayesian Cons | 0.5-2.0 theta | Medium | Adaptive growth |
| Theta-Bayesian Aggr | 0.8-3.0 theta | High | Fast adaptation |
| Volatility-Adjusted | Vol scaling | Medium | Stability |

## Critical Constants

| Constant | Value | Source |
|----------|-------|--------|
| Sidebet payout | 5:1 | rugs.fun |
| Breakeven win rate | 16.67% | 1/6 |
| Historical win rate | ~18.5% | 568-game study |
| Volatility baseline | 0.102917 | Historical |
| Circuit breaker | 15% drawdown | Risk management |

## Gotchas

1. **Kelly Negative**: If win rate < 16.67%, Kelly is negative. Return 0.

2. **Iteration Count**: 1k for quick tests, 10k for production, 100k for research.

3. **Win Streak Reset**: Reset to 0 on any loss (anti-martingale).

4. **Volatility Sampling**: Log-normal distribution for realistic game variation.

5. **Circuit Breaker**: 15% drawdown halt per game sequence.

6. **Bankrupt Detection**: Bankroll <= 0.001 SOL considered ruined.

7. **Computation Time**: 100k iterations takes ~30 seconds. Cache results.
