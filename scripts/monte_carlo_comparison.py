#!/usr/bin/env python3
"""
Monte Carlo Comparison Study

Compares different scaling strategies to find optimal balance between
profit maximization and drawdown minimization.

Strategies tested:
1. Fixed sizing (baseline)
2. Quarter Kelly
3. Half Kelly (aggressive)
4. Anti-Martingale only
5. Theta Bayesian (combined)
6. Conservative Theta Bayesian
"""

import sys

sys.path.insert(0, "/home/devops/Desktop/VECTRA-PLAYER/src")

import json
from pathlib import Path

from recording_ui.services.monte_carlo import (
    MonteCarloSimulator,
    ScalingMode,
    SimulationConfig,
    results_to_dict,
)


def create_scenarios() -> dict:
    """Create different scenario configurations."""
    base_config = {
        "initial_bankroll": 0.1,
        "base_bet_size": 0.001,
        "win_rate": 0.185,
        "num_games": 500,
        "num_iterations": 100000,  # 100k iterations for statistical robustness
        "num_bets_per_game": 4,
        "use_volatility_scaling": True,
    }

    scenarios = {
        "fixed_baseline": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.FIXED,
            kelly_fraction=0.25,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "quarter_kelly": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.KELLY,
            kelly_fraction=0.25,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "half_kelly_aggressive": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.KELLY,
            kelly_fraction=0.5,
            drawdown_halt=0.20,
            take_profit_target=2.0,
        ),
        "anti_martingale": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.ANTI_MARTINGALE,
            win_streak_multiplier=1.5,
            max_streak_multiplier=3.0,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "theta_bayesian_aggressive": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.THETA_BAYESIAN,
            kelly_fraction=0.5,
            win_streak_multiplier=1.5,
            max_streak_multiplier=3.0,
            theta_base=1.0,
            theta_max=4.0,
            drawdown_halt=0.20,
            take_profit_target=2.0,
        ),
        "theta_bayesian_conservative": SimulationConfig(
            **base_config,
            scaling_mode=ScalingMode.THETA_BAYESIAN,
            kelly_fraction=0.25,
            win_streak_multiplier=1.3,
            max_streak_multiplier=2.0,
            theta_base=0.5,
            theta_max=2.0,
            drawdown_halt=0.10,
            take_profit_target=1.3,
        ),
        "volatility_focused": SimulationConfig(
            initial_bankroll=0.1,
            base_bet_size=0.001,
            win_rate=0.185,
            num_games=500,
            num_iterations=100000,
            num_bets_per_game=4,
            scaling_mode=ScalingMode.VOLATILITY_ADJUSTED,
            use_volatility_scaling=True,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "ultra_aggressive": SimulationConfig(
            initial_bankroll=0.1,
            base_bet_size=0.002,  # 2% base
            win_rate=0.185,
            num_games=500,
            num_iterations=100000,
            num_bets_per_game=4,
            use_volatility_scaling=True,
            scaling_mode=ScalingMode.THETA_BAYESIAN,
            kelly_fraction=0.75,  # 3/4 Kelly
            win_streak_multiplier=2.0,
            max_streak_multiplier=4.0,
            theta_base=1.0,
            theta_max=5.0,
            drawdown_halt=0.25,
            take_profit_target=3.0,
        ),
    }

    return scenarios


def run_comparison():
    """Run all scenarios and compare."""
    print("=" * 80)
    print("MONTE CARLO COMPARISON STUDY - 100,000 Iterations per Scenario")
    print("=" * 80)

    scenarios = create_scenarios()
    results = {}

    for name, config in scenarios.items():
        print(f"\nRunning: {name}...")
        simulator = MonteCarloSimulator(config)
        result = simulator.run()
        results[name] = result
        print(
            f"  Done. Mean: {result.mean_final_bankroll:.4f}, P(Profit): {result.probability_profit:.1%}"
        )

    # Summary comparison
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    headers = ["Scenario", "Mean", "Median", "P(Profit)", "P(2x)", "MDD", "Sharpe", "Sortino"]
    print(
        f"\n{headers[0]:<30} {headers[1]:>8} {headers[2]:>8} {headers[3]:>10} {headers[4]:>8} {headers[5]:>8} {headers[6]:>8} {headers[7]:>8}"
    )
    print("-" * 100)

    for name, r in results.items():
        print(
            f"{name:<30} {r.mean_final_bankroll:>8.4f} {r.median_final_bankroll:>8.4f} "
            f"{r.probability_profit:>9.1%} {r.probability_2x:>7.1%} "
            f"{r.mean_max_drawdown:>7.1%} {r.sharpe_ratio:>8.3f} {r.sortino_ratio:>8.3f}"
        )

    # Detailed analysis
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)

    # Best for each metric
    metrics = {
        "Highest Mean": max(results.items(), key=lambda x: x[1].mean_final_bankroll),
        "Highest Median": max(results.items(), key=lambda x: x[1].median_final_bankroll),
        "Highest P(Profit)": max(results.items(), key=lambda x: x[1].probability_profit),
        "Highest P(2x)": max(results.items(), key=lambda x: x[1].probability_2x),
        "Lowest Drawdown": min(results.items(), key=lambda x: x[1].mean_max_drawdown),
        "Best Sharpe": max(results.items(), key=lambda x: x[1].sharpe_ratio),
        "Best Sortino": max(results.items(), key=lambda x: x[1].sortino_ratio),
        "Best Calmar": max(results.items(), key=lambda x: x[1].calmar_ratio),
    }

    print("\n--- BEST PERFORMERS BY METRIC ---")
    for metric, (name, result) in metrics.items():
        if "Mean" in metric:
            value = f"{result.mean_final_bankroll:.4f}"
        elif "Median" in metric:
            value = f"{result.median_final_bankroll:.4f}"
        elif "P(" in metric:
            if "2x" in metric:
                value = f"{result.probability_2x:.1%}"
            else:
                value = f"{result.probability_profit:.1%}"
        elif "Drawdown" in metric:
            value = f"{result.mean_max_drawdown:.1%}"
        else:
            if "Sharpe" in metric:
                value = f"{result.sharpe_ratio:.3f}"
            elif "Sortino" in metric:
                value = f"{result.sortino_ratio:.3f}"
            else:
                value = f"{result.calmar_ratio:.3f}"
        print(f"  {metric:<25}: {name} ({value})")

    # Risk/Reward tradeoff analysis
    print("\n--- RISK/REWARD ANALYSIS ---")
    for name, r in sorted(results.items(), key=lambda x: x[1].sortino_ratio, reverse=True):
        score = (
            r.probability_profit * 0.3
            + r.probability_2x * 0.2
            + (1 - r.mean_max_drawdown) * 0.2
            + min(r.sortino_ratio / 2, 1) * 0.3
        )
        print(
            f"  {name:<30}: Score={score:.3f} "
            f"(P={r.probability_profit:.0%}, DD={r.mean_max_drawdown:.0%}, Sortino={r.sortino_ratio:.2f})"
        )

    # Save detailed results
    output = {name: results_to_dict(r) for name, r in results.items()}
    output_path = Path(
        "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/monte_carlo_comparison.json"
    )
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n\nDetailed results saved to: {output_path}")

    return results


if __name__ == "__main__":
    run_comparison()
