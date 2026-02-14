#!/usr/bin/env python3
"""
Volatility Study for Bankroll Simulation Enhancement

Analyzes game-level volatility characteristics from recorded games to establish:
- Min/Max/Median volatility baselines
- Volatility distribution percentiles
- Correlation between volatility and game outcomes
- Optimal position sizing adjustments based on volatility

Usage:
    python scripts/volatility_study.py
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class VolatilityMetrics:
    """Per-game volatility metrics."""

    game_id: str
    duration_ticks: int

    # Core volatility measures
    price_std: float  # Standard deviation of prices
    return_std: float  # Standard deviation of tick-to-tick returns
    log_return_std: float  # Standard deviation of log returns

    # Range-based volatility
    price_range: float  # (max - min) / mean
    high_low_ratio: float  # max / min

    # Spike detection
    spike_count: int  # Number of 2x+ volatility spikes
    max_spike_magnitude: float  # Largest single-tick move
    avg_spike_magnitude: float  # Average spike size

    # Trend volatility
    volatility_of_volatility: float  # How much volatility changes over time

    # Game outcome
    peak_multiplier: float
    final_price: float
    is_profitable_sidebet_zone: bool  # Duration >= 200


def calculate_game_volatility(game_row: pd.Series) -> VolatilityMetrics:
    """Calculate comprehensive volatility metrics for a single game."""
    prices = np.array(game_row["prices"])
    game_id = game_row["game_id"]
    duration = len(prices)

    if duration < 10:
        # Too short for meaningful volatility
        return VolatilityMetrics(
            game_id=game_id,
            duration_ticks=duration,
            price_std=0.0,
            return_std=0.0,
            log_return_std=0.0,
            price_range=0.0,
            high_low_ratio=1.0,
            spike_count=0,
            max_spike_magnitude=0.0,
            avg_spike_magnitude=0.0,
            volatility_of_volatility=0.0,
            peak_multiplier=game_row.get("peak_multiplier", max(prices)),
            final_price=prices[-1] if len(prices) > 0 else 0.0,
            is_profitable_sidebet_zone=duration >= 200,
        )

    # Basic price volatility
    price_std = np.std(prices)
    price_mean = np.mean(prices)

    # Tick-to-tick returns
    returns = np.diff(prices) / prices[:-1]
    returns = returns[np.isfinite(returns)]  # Remove inf/nan
    return_std = np.std(returns) if len(returns) > 0 else 0.0

    # Log returns (more stable for multiplicative processes)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_prices = np.log(prices[prices > 0])
        log_returns = np.diff(log_prices)
        log_returns = log_returns[np.isfinite(log_returns)]
    log_return_std = np.std(log_returns) if len(log_returns) > 0 else 0.0

    # Range-based volatility
    price_min = np.min(prices)
    price_max = np.max(prices)
    price_range = (price_max - price_min) / price_mean if price_mean > 0 else 0.0
    high_low_ratio = price_max / price_min if price_min > 0 else 1.0

    # Spike detection (2x+ volatility spikes)
    if len(returns) > 0:
        baseline_vol = np.percentile(np.abs(returns), 50)  # Median absolute return
        spike_threshold = baseline_vol * 2 if baseline_vol > 0 else 0.01
        spikes = np.abs(returns) > spike_threshold
        spike_count = np.sum(spikes)
        spike_magnitudes = np.abs(returns[spikes]) if spike_count > 0 else np.array([0.0])
        max_spike_magnitude = np.max(spike_magnitudes)
        avg_spike_magnitude = np.mean(spike_magnitudes)
    else:
        spike_count = 0
        max_spike_magnitude = 0.0
        avg_spike_magnitude = 0.0

    # Volatility of volatility (rolling window std dev of returns)
    if len(returns) >= 20:
        window = 10
        rolling_vol = pd.Series(returns).rolling(window).std().dropna()
        volatility_of_volatility = np.std(rolling_vol) if len(rolling_vol) > 0 else 0.0
    else:
        volatility_of_volatility = 0.0

    return VolatilityMetrics(
        game_id=game_id,
        duration_ticks=duration,
        price_std=price_std,
        return_std=return_std,
        log_return_std=log_return_std,
        price_range=price_range,
        high_low_ratio=high_low_ratio,
        spike_count=spike_count,
        max_spike_magnitude=max_spike_magnitude,
        avg_spike_magnitude=avg_spike_magnitude,
        volatility_of_volatility=volatility_of_volatility,
        peak_multiplier=game_row.get("peak_multiplier", price_max),
        final_price=prices[-1] if len(prices) > 0 else 0.0,
        is_profitable_sidebet_zone=duration >= 200,
    )


def analyze_volatility_distribution(metrics: list[VolatilityMetrics]) -> dict:
    """Analyze the distribution of volatility across all games."""
    df = pd.DataFrame([m.__dict__ for m in metrics])

    # Filter to playable games (duration >= 40)
    playable = df[df["duration_ticks"] >= 40]

    result = {
        "total_games": len(df),
        "playable_games": len(playable),
        "optimal_zone_games": len(df[df["is_profitable_sidebet_zone"]]),
    }

    # Key volatility metrics
    vol_columns = [
        "return_std",
        "log_return_std",
        "price_range",
        "spike_count",
        "max_spike_magnitude",
        "volatility_of_volatility",
    ]

    for col in vol_columns:
        values = playable[col].dropna()
        if len(values) == 0:
            continue

        result[col] = {
            "min": float(values.min()),
            "max": float(values.max()),
            "median": float(values.median()),
            "mean": float(values.mean()),
            "std": float(values.std()),
            "percentiles": {
                "5": float(np.percentile(values, 5)),
                "10": float(np.percentile(values, 10)),
                "25": float(np.percentile(values, 25)),
                "50": float(np.percentile(values, 50)),
                "75": float(np.percentile(values, 75)),
                "90": float(np.percentile(values, 90)),
                "95": float(np.percentile(values, 95)),
                "99": float(np.percentile(values, 99)),
            },
        }

    # Correlation analysis
    correlations = {}
    target_cols = ["duration_ticks", "peak_multiplier"]
    for vol_col in vol_columns:
        for target in target_cols:
            if vol_col in playable.columns and target in playable.columns:
                corr = playable[vol_col].corr(playable[target])
                if not np.isnan(corr):
                    correlations[f"{vol_col}_vs_{target}"] = float(corr)

    result["correlations"] = correlations

    # Volatility regimes (low/medium/high)
    return_std_values = playable["return_std"]
    result["volatility_regimes"] = {
        "low": {
            "threshold": float(np.percentile(return_std_values, 33)),
            "description": "Bottom third of volatility",
        },
        "medium": {
            "threshold": float(np.percentile(return_std_values, 67)),
            "description": "Middle third of volatility",
        },
        "high": {
            "threshold": float(np.percentile(return_std_values, 100)),
            "description": "Top third of volatility",
        },
    }

    return result


def analyze_volatility_by_zone(metrics: list[VolatilityMetrics]) -> dict:
    """Compare volatility characteristics between optimal and non-optimal zones."""
    df = pd.DataFrame([m.__dict__ for m in metrics])
    playable = df[df["duration_ticks"] >= 40]

    optimal = playable[playable["is_profitable_sidebet_zone"]]
    non_optimal = playable[~playable["is_profitable_sidebet_zone"]]

    comparison = {}
    vol_columns = ["return_std", "log_return_std", "spike_count", "max_spike_magnitude"]

    for col in vol_columns:
        opt_vals = optimal[col].dropna()
        non_opt_vals = non_optimal[col].dropna()

        if len(opt_vals) > 0 and len(non_opt_vals) > 0:
            comparison[col] = {
                "optimal_zone": {
                    "median": float(opt_vals.median()),
                    "mean": float(opt_vals.mean()),
                },
                "non_optimal_zone": {
                    "median": float(non_opt_vals.median()),
                    "mean": float(non_opt_vals.mean()),
                },
                "ratio": float(opt_vals.median() / non_opt_vals.median())
                if non_opt_vals.median() > 0
                else 1.0,
            }

    return comparison


def generate_position_sizing_recommendations(distribution: dict) -> dict:
    """Generate position sizing multipliers based on volatility analysis."""

    # Extract return_std thresholds
    return_std = distribution.get("return_std", {})
    percentiles = return_std.get("percentiles", {})

    if not percentiles:
        return {"error": "Insufficient volatility data"}

    # Define volatility-based sizing tiers
    recommendations = {
        "baseline_volatility": return_std.get("median", 0.0),
        "sizing_tiers": {
            "very_low_vol": {
                "threshold": percentiles.get("25", 0.0),
                "position_multiplier": 1.5,
                "description": "Below 25th percentile volatility - increase position",
            },
            "low_vol": {
                "threshold": percentiles.get("50", 0.0),
                "position_multiplier": 1.25,
                "description": "25th-50th percentile - slightly larger position",
            },
            "normal_vol": {
                "threshold": percentiles.get("75", 0.0),
                "position_multiplier": 1.0,
                "description": "50th-75th percentile - standard position",
            },
            "high_vol": {
                "threshold": percentiles.get("90", 0.0),
                "position_multiplier": 0.75,
                "description": "75th-90th percentile - reduce position",
            },
            "very_high_vol": {
                "threshold": percentiles.get("99", 0.0),
                "position_multiplier": 0.5,
                "description": "Above 90th percentile - half position or skip",
            },
        },
        "spike_warning_threshold": distribution.get("spike_count", {})
        .get("percentiles", {})
        .get("90", 5),
        "formula": "position_size = base_size * (baseline_vol / current_vol)",
    }

    return recommendations


def main():
    """Run complete volatility analysis."""
    print("=" * 70)
    print("VOLATILITY STUDY FOR BANKROLL SIMULATION")
    print("=" * 70)

    # Load data
    data_path = Path(
        "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/training_data/games_with_prices.parquet"
    )

    if not data_path.exists():
        print(f"ERROR: Data file not found at {data_path}")
        return

    print(f"\nLoading games from: {data_path}")
    games = pd.read_parquet(data_path)
    print(f"Loaded {len(games)} games")

    # Calculate volatility for each game
    print("\nCalculating per-game volatility metrics...")
    metrics = []
    for _, row in games.iterrows():
        m = calculate_game_volatility(row)
        metrics.append(m)

    print(f"Processed {len(metrics)} games")

    # Analyze distribution
    print("\n" + "=" * 70)
    print("VOLATILITY DISTRIBUTION ANALYSIS")
    print("=" * 70)

    distribution = analyze_volatility_distribution(metrics)

    print(f"\nTotal games: {distribution['total_games']}")
    print(f"Playable games (>=40 ticks): {distribution['playable_games']}")
    print(f"Optimal zone games (>=200 ticks): {distribution['optimal_zone_games']}")

    # Print key metrics
    for metric_name in ["return_std", "log_return_std", "price_range", "spike_count"]:
        if metric_name in distribution:
            m = distribution[metric_name]
            print(f"\n--- {metric_name.upper()} ---")
            print(f"  Min:    {m['min']:.6f}")
            print(f"  Max:    {m['max']:.6f}")
            print(f"  Median: {m['median']:.6f}")
            print(f"  Mean:   {m['mean']:.6f}")
            print(f"  Std:    {m['std']:.6f}")
            print("  Percentiles:")
            for p, v in m["percentiles"].items():
                print(f"    {p}th: {v:.6f}")

    # Zone comparison
    print("\n" + "=" * 70)
    print("VOLATILITY BY GAME ZONE")
    print("=" * 70)

    zone_comparison = analyze_volatility_by_zone(metrics)
    for metric_name, data in zone_comparison.items():
        print(f"\n{metric_name}:")
        print(f"  Optimal zone median:     {data['optimal_zone']['median']:.6f}")
        print(f"  Non-optimal zone median: {data['non_optimal_zone']['median']:.6f}")
        print(f"  Ratio (opt/non-opt):     {data['ratio']:.3f}")

    # Correlations
    print("\n" + "=" * 70)
    print("VOLATILITY CORRELATIONS")
    print("=" * 70)

    for corr_name, value in distribution.get("correlations", {}).items():
        print(f"  {corr_name}: {value:.4f}")

    # Position sizing recommendations
    print("\n" + "=" * 70)
    print("POSITION SIZING RECOMMENDATIONS")
    print("=" * 70)

    recommendations = generate_position_sizing_recommendations(distribution)
    print(
        f"\nBaseline volatility (median return_std): {recommendations.get('baseline_volatility', 0):.6f}"
    )
    print("\nSizing tiers:")
    for tier_name, tier_data in recommendations.get("sizing_tiers", {}).items():
        print(f"  {tier_name}:")
        print(f"    Threshold: {tier_data['threshold']:.6f}")
        print(f"    Multiplier: {tier_data['position_multiplier']}x")
        print(f"    {tier_data['description']}")

    print(
        f"\nSpike warning threshold: {recommendations.get('spike_warning_threshold', 'N/A')} spikes"
    )
    print(f"Formula: {recommendations.get('formula', 'N/A')}")

    # Save results
    output_path = Path(
        "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/volatility_analysis.json"
    )
    results = {
        "distribution": distribution,
        "zone_comparison": zone_comparison,
        "recommendations": recommendations,
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n\nResults saved to: {output_path}")

    # Create DataFrame for further analysis
    df = pd.DataFrame([m.__dict__ for m in metrics])
    df_path = output_path.parent / "volatility_metrics.parquet"
    df.to_parquet(df_path)
    print(f"Per-game metrics saved to: {df_path}")

    print("\n" + "=" * 70)
    print("STUDY COMPLETE")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
