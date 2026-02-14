"""
Monte Carlo Strategy Comparison Service

Runs all 8 scaling strategies and returns comparison data for the
Game Explorer UI. Supports 1k, 10k, and 100k iteration modes.
"""

import time
from dataclasses import dataclass

from .monte_carlo import (
    MonteCarloResults,
    MonteCarloSimulator,
    ScalingMode,
    SimulationConfig,
    results_to_dict,
)

# =============================================================================
# STRATEGY CONFIGURATIONS
# =============================================================================


def create_strategy_configs(
    num_iterations: int = 10000,
    initial_bankroll: float = 0.1,
    win_rate: float = 0.185,
    num_games: int = 500,
) -> dict[str, SimulationConfig]:
    """
    Create all 8 strategy configurations for comparison.

    Returns dict mapping strategy name to SimulationConfig.
    """
    base = {
        "initial_bankroll": initial_bankroll,
        "base_bet_size": 0.001,
        "win_rate": win_rate,
        "num_games": num_games,
        "num_iterations": num_iterations,
        "num_bets_per_game": 4,
        "use_volatility_scaling": True,
    }

    return {
        "fixed_baseline": SimulationConfig(
            **base,
            scaling_mode=ScalingMode.FIXED,
            kelly_fraction=0.25,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "quarter_kelly": SimulationConfig(
            **base,
            scaling_mode=ScalingMode.KELLY,
            kelly_fraction=0.25,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "half_kelly_aggressive": SimulationConfig(
            **base,
            scaling_mode=ScalingMode.KELLY,
            kelly_fraction=0.5,
            drawdown_halt=0.20,
            take_profit_target=2.0,
        ),
        "anti_martingale": SimulationConfig(
            **base,
            scaling_mode=ScalingMode.ANTI_MARTINGALE,
            win_streak_multiplier=1.5,
            max_streak_multiplier=3.0,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "theta_bayesian_aggressive": SimulationConfig(
            **base,
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
            **base,
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
            initial_bankroll=initial_bankroll,
            base_bet_size=0.001,
            win_rate=win_rate,
            num_games=num_games,
            num_iterations=num_iterations,
            num_bets_per_game=4,
            scaling_mode=ScalingMode.VOLATILITY_ADJUSTED,
            use_volatility_scaling=True,
            drawdown_halt=0.15,
            take_profit_target=1.5,
        ),
        "ultra_aggressive": SimulationConfig(
            initial_bankroll=initial_bankroll,
            base_bet_size=0.002,  # 2% base
            win_rate=win_rate,
            num_games=num_games,
            num_iterations=num_iterations,
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


# =============================================================================
# STRATEGY METADATA
# =============================================================================

STRATEGY_DESCRIPTIONS = {
    "fixed_baseline": {
        "name": "Fixed Baseline",
        "description": "Same bet size every game - conservative baseline",
        "risk_level": "Low",
        "color": "#a6e3a1",  # Green
    },
    "quarter_kelly": {
        "name": "Quarter Kelly",
        "description": "25% Kelly Criterion - balanced risk/reward",
        "risk_level": "Low-Medium",
        "color": "#94e2d5",  # Teal
    },
    "half_kelly_aggressive": {
        "name": "Half Kelly",
        "description": "50% Kelly with 20% drawdown halt",
        "risk_level": "Medium-High",
        "color": "#f9e2af",  # Yellow
    },
    "anti_martingale": {
        "name": "Anti-Martingale",
        "description": "Scale up 1.5x after each win (max 3x)",
        "risk_level": "Low",
        "color": "#89b4fa",  # Blue
    },
    "theta_bayesian_aggressive": {
        "name": "Theta Aggressive",
        "description": "Theta 1.0→4.0 + Half Kelly - high upside",
        "risk_level": "High",
        "color": "#fab387",  # Peach
    },
    "theta_bayesian_conservative": {
        "name": "Theta Conservative ★",
        "description": "Theta 0.5→2.0 + Quarter Kelly - best Sortino",
        "risk_level": "Medium",
        "color": "#cba6f7",  # Mauve (highlighted)
    },
    "volatility_focused": {
        "name": "Volatility Adjusted",
        "description": "Size inversely to game volatility",
        "risk_level": "Low",
        "color": "#74c7ec",  # Sapphire
    },
    "ultra_aggressive": {
        "name": "Ultra Aggressive",
        "description": "75% Kelly + 2x win multiplier - max ceiling",
        "risk_level": "Very High",
        "color": "#f38ba8",  # Red
    },
}


# =============================================================================
# COMPARISON SERVICE
# =============================================================================


@dataclass
class ComparisonResult:
    """Container for strategy comparison results."""

    strategies: dict[str, dict]
    best_by_metric: dict[str, str]
    computation_time_ms: int
    num_iterations: int
    win_rate: float
    initial_bankroll: float


def run_strategy_comparison(
    num_iterations: int = 10000,
    initial_bankroll: float = 0.1,
    win_rate: float = 0.185,
    num_games: int = 500,
    progress_callback=None,
) -> dict:
    """
    Run all 8 Monte Carlo strategies and return comparison data.

    Args:
        num_iterations: 1000, 10000, or 100000
        initial_bankroll: Starting balance in SOL
        win_rate: Expected win rate (0.0 to 1.0)
        num_games: Games per simulation
        progress_callback: Optional callback(strategy_name, progress_pct)

    Returns:
        Dict with strategies, best_by_metric, computation_time_ms
    """
    start_time = time.time()

    # Create all strategy configs
    configs = create_strategy_configs(
        num_iterations=num_iterations,
        initial_bankroll=initial_bankroll,
        win_rate=win_rate,
        num_games=num_games,
    )

    # Run each strategy
    results: dict[str, MonteCarloResults] = {}
    strategy_names = list(configs.keys())

    for i, (name, config) in enumerate(configs.items()):
        if progress_callback:
            progress_callback(name, i / len(configs))

        simulator = MonteCarloSimulator(config)
        results[name] = simulator.run()

    # Format results for frontend
    formatted = {}
    for name, result in results.items():
        base = results_to_dict(result)
        # Add metadata
        base["metadata"] = STRATEGY_DESCRIPTIONS.get(name, {})
        # Add sample equity curves (limit to 5 for bandwidth)
        base["sample_equity_curves"] = (
            result.sample_equity_curves[:5] if result.sample_equity_curves else []
        )
        formatted[name] = base

    # Find best performers
    best_by_metric = {
        "highest_mean": max(results.items(), key=lambda x: x[1].mean_final_bankroll)[0],
        "highest_median": max(results.items(), key=lambda x: x[1].median_final_bankroll)[0],
        "highest_profit_prob": max(results.items(), key=lambda x: x[1].probability_profit)[0],
        "highest_2x_prob": max(results.items(), key=lambda x: x[1].probability_2x)[0],
        "lowest_drawdown": min(results.items(), key=lambda x: x[1].mean_max_drawdown)[0],
        "best_sharpe": max(results.items(), key=lambda x: x[1].sharpe_ratio)[0],
        "best_sortino": max(results.items(), key=lambda x: x[1].sortino_ratio)[0],
        "best_calmar": max(results.items(), key=lambda x: x[1].calmar_ratio)[0],
    }

    computation_time_ms = int((time.time() - start_time) * 1000)

    return {
        "strategies": formatted,
        "best_by_metric": best_by_metric,
        "strategy_order": strategy_names,  # Preserve order for table
        "computation_time_ms": computation_time_ms,
        "config": {
            "num_iterations": num_iterations,
            "win_rate": win_rate,
            "initial_bankroll": initial_bankroll,
            "num_games": num_games,
        },
    }


def get_strategy_summary_table(comparison_result: dict) -> list[dict]:
    """
    Format results as a simple table for display.

    Returns list of dicts with key metrics for each strategy.
    """
    table = []
    strategies = comparison_result["strategies"]
    best = comparison_result["best_by_metric"]

    for name in comparison_result["strategy_order"]:
        data = strategies[name]
        summary = data.get("summary", {})
        risk = data.get("risk_metrics", {})
        perf = data.get("performance", {})
        meta = data.get("metadata", {})

        row = {
            "key": name,
            "name": meta.get("name", name),
            "description": meta.get("description", ""),
            "risk_level": meta.get("risk_level", "Unknown"),
            "color": meta.get("color", "#cdd6f4"),
            "mean": summary.get("mean_final_bankroll", 0),
            "median": summary.get("median_final_bankroll", 0),
            "probability_profit": risk.get("probability_profit", 0),
            "probability_2x": risk.get("probability_2x", 0),
            "mean_max_drawdown": data.get("drawdown", {}).get("mean_max_drawdown", 0),
            "sharpe_ratio": perf.get("sharpe_ratio", 0),
            "sortino_ratio": perf.get("sortino_ratio", 0),
            "calmar_ratio": perf.get("calmar_ratio", 0),
            "var_95": data.get("var_metrics", {}).get("var_95", 0),
            "cvar_95": data.get("var_metrics", {}).get("cvar_95", 0),
            # Highlight best performers
            "is_best_mean": name == best.get("highest_mean"),
            "is_best_profit": name == best.get("highest_profit_prob"),
            "is_best_2x": name == best.get("highest_2x_prob"),
            "is_best_sortino": name == best.get("best_sortino"),
            "is_best_drawdown": name == best.get("lowest_drawdown"),
        }
        table.append(row)

    return table


# =============================================================================
# PROFILE <-> CONFIG CONVERSION
# =============================================================================


def profile_to_config(
    profile,  # TradingProfile - avoid circular import
    num_iterations: int = 10000,
    num_games: int = 500,
) -> SimulationConfig:
    """
    Convert a TradingProfile to a SimulationConfig for Monte Carlo simulation.

    This enables running MC simulations on user-defined profiles to calculate
    risk metrics (Sortino, VaR, etc.) before live testing.

    Args:
        profile: TradingProfile v2 object
        num_iterations: Number of MC iterations
        num_games: Number of games to simulate per iteration

    Returns:
        SimulationConfig ready for MonteCarloSimulator
    """
    # Map profile scaling.mode string to ScalingMode enum
    mode_map = {
        "fixed": ScalingMode.FIXED,
        "kelly": ScalingMode.KELLY,
        "anti_martingale": ScalingMode.ANTI_MARTINGALE,
        "theta_bayesian": ScalingMode.THETA_BAYESIAN,
        "volatility_adjusted": ScalingMode.VOLATILITY_ADJUSTED,
    }

    scaling_mode = mode_map.get(profile.scaling.mode, ScalingMode.FIXED)

    # Calculate base bet size from profile bet_sizes (average or first)
    bet_sizes = profile.execution.bet_sizes
    base_bet = bet_sizes[0] if bet_sizes else 0.001

    return SimulationConfig(
        # Basic parameters
        initial_bankroll=profile.execution.initial_balance,
        base_bet_size=base_bet,
        win_rate=0.185,  # Empirical optimal zone rate
        num_games=num_games,
        num_iterations=num_iterations,
        # Scaling mode
        scaling_mode=scaling_mode,
        # Kelly parameters
        kelly_fraction=profile.scaling.kelly_fraction,
        # Anti-martingale parameters
        win_streak_multiplier=profile.scaling.win_streak_multiplier,
        max_streak_multiplier=profile.scaling.max_streak_multiplier,
        # Theta Bayesian parameters
        theta_base=profile.scaling.theta_base,
        theta_max=profile.scaling.theta_max,
        # Volatility
        use_volatility_scaling=profile.scaling.use_volatility_scaling,
        # Drawdown controls - derive from max_drawdown_pct
        drawdown_halt=profile.risk_controls.max_drawdown_pct,
        drawdown_warning=profile.risk_controls.max_drawdown_pct * 0.33,
        drawdown_caution=profile.risk_controls.max_drawdown_pct * 0.66,
        # Profit target
        take_profit_target=profile.risk_controls.take_profit_target,
        # Daily limit
        daily_loss_limit=profile.risk_controls.daily_loss_limit or 0.03,
        # Multi-bet config
        num_bets_per_game=profile.execution.num_bets,
    )
