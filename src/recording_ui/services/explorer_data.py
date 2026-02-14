"""
Game Explorer Data Service.

Provides game data analysis for the Game Explorer visualization tool.
Supports multi-bet martingale strategy analysis with 5-tick cooldowns.

Sidebet Mechanics (from rugs-expert):
- Window: 40 ticks from placement (N through N+39 inclusive)
- Payout: 5:1 (400% profit + bet returned)
- Cooldown: 5 ticks between bets
- Breakeven: 20% win rate
"""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Constants from rugs.fun sidebet mechanics
SIDEBET_WINDOW = 40  # Ticks covered by each bet
SIDEBET_COOLDOWN = 5  # Ticks to wait between bets
SIDEBET_PAYOUT = 5  # 5:1 payout ratio
BREAKEVEN_RATE = 1 / SIDEBET_PAYOUT  # 20%


def get_training_data_path() -> Path:
    """Get path to training data parquet file."""
    return (
        Path(__file__).parent.parent.parent.parent
        / "Machine Learning"
        / "models"
        / "sidebet-v1"
        / "training_data"
        / "games_with_prices.parquet"
    )


def load_games_df() -> pd.DataFrame:
    """Load games dataframe from parquet."""
    path = get_training_data_path()
    if not path.exists():
        raise FileNotFoundError(f"Training data not found: {path}")
    return pd.read_parquet(path)


def calculate_bet_windows(entry_tick: int, num_bets: int = 4) -> list[dict]:
    """
    Calculate bet windows for a multi-bet strategy.

    Args:
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets (default 4)

    Returns:
        List of dicts with start/end ticks for each bet window
    """
    windows = []
    current_tick = entry_tick

    for i in range(num_bets):
        window = {
            "bet_num": i + 1,
            "start_tick": current_tick,
            "end_tick": current_tick + SIDEBET_WINDOW - 1,  # Inclusive
        }
        windows.append(window)
        # Next bet starts after window ends + cooldown
        current_tick = current_tick + SIDEBET_WINDOW + SIDEBET_COOLDOWN

    return windows


def analyze_game_outcome(duration: int, entry_tick: int, num_bets: int = 4) -> dict[str, Any]:
    """
    Analyze outcome for a single game with multi-bet strategy.

    Args:
        duration: Game duration in ticks (when it rugged)
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets

    Returns:
        Dict with outcome analysis
    """
    windows = calculate_bet_windows(entry_tick, num_bets)

    # Check if game even reached entry tick
    if duration < entry_tick:
        return {
            "outcome": "early_rug",
            "rugged_at": duration,
            "entry_tick": entry_tick,
            "winning_bet": None,
            "bets_placed": 0,
            "total_cost": 0,
            "payout": 0,
            "profit": 0,
        }

    # Check each bet window
    winning_bet = None
    bets_placed = 0

    for window in windows:
        # Can we place this bet? (game still running at start tick)
        if duration >= window["start_tick"]:
            bets_placed += 1
            # Did the game rug within this window?
            if duration <= window["end_tick"]:
                winning_bet = window["bet_num"]
                break

    if winning_bet:
        return {
            "outcome": "win",
            "rugged_at": duration,
            "entry_tick": entry_tick,
            "winning_bet": winning_bet,
            "bets_placed": bets_placed,
            "total_cost": bets_placed,  # Assuming unit bets
            "payout": SIDEBET_PAYOUT,
            "profit": SIDEBET_PAYOUT - bets_placed,
        }
    else:
        return {
            "outcome": "loss",
            "rugged_at": duration,
            "entry_tick": entry_tick,
            "winning_bet": None,
            "bets_placed": bets_placed,
            "total_cost": bets_placed,
            "payout": 0,
            "profit": -bets_placed,
        }


def calculate_strategy_stats(
    games_df: pd.DataFrame, entry_tick: int, num_bets: int = 4
) -> dict[str, Any]:
    """
    Calculate strategy statistics across all games.

    Args:
        games_df: DataFrame with game data
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets

    Returns:
        Dict with strategy statistics
    """
    windows = calculate_bet_windows(entry_tick, num_bets)

    # Analyze each game
    results = []
    for _, row in games_df.iterrows():
        result = analyze_game_outcome(
            duration=int(row["duration_ticks"]),
            entry_tick=entry_tick,
            num_bets=num_bets,
        )
        results.append(result)

    results_df = pd.DataFrame(results)

    # Calculate cumulative stats for 1, 2, 3, 4 bets
    cumulative_stats = []
    for n in range(1, num_bets + 1):
        # Re-analyze with only n bets
        n_results = []
        for _, row in games_df.iterrows():
            n_result = analyze_game_outcome(
                duration=int(row["duration_ticks"]),
                entry_tick=entry_tick,
                num_bets=n,
            )
            n_results.append(n_result)

        n_df = pd.DataFrame(n_results)
        playable = n_df[n_df["outcome"] != "early_rug"]
        wins = n_df[n_df["outcome"] == "win"]

        win_rate = len(wins) / len(playable) if len(playable) > 0 else 0
        total_games = len(games_df)
        playable_games = len(playable)

        # Expected value per sequence (unit bets)
        # If win: profit = 5 - bets_placed (avg)
        # If loss: profit = -n (all bets lost)
        avg_win_cost = wins["bets_placed"].mean() if len(wins) > 0 else n
        ev_per_sequence = win_rate * (SIDEBET_PAYOUT - avg_win_cost) + (1 - win_rate) * (-n)

        cumulative_stats.append(
            {
                "num_bets": n,
                "win_rate": round(win_rate * 100, 1),
                "profitable": win_rate > BREAKEVEN_RATE,
                "playable_games": playable_games,
                "total_games": total_games,
                "ev_per_sequence": round(ev_per_sequence, 3),
                "coverage_end_tick": windows[n - 1]["end_tick"],
            }
        )

    # Overall summary
    playable = results_df[results_df["outcome"] != "early_rug"]

    return {
        "entry_tick": entry_tick,
        "num_bets": num_bets,
        "windows": windows,
        "cumulative_stats": cumulative_stats,
        "total_games": len(games_df),
        "playable_games": len(playable),
        "early_rug_rate": round((len(games_df) - len(playable)) / len(games_df) * 100, 1),
    }


def get_games_for_chart(
    games_df: pd.DataFrame, entry_tick: int, num_bets: int = 4, limit: int = 50
) -> list[dict]:
    """
    Get games formatted for Chart.js visualization.

    Args:
        games_df: DataFrame with game data
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets
        limit: Maximum games to return

    Returns:
        List of game dicts with prices and outcome
    """
    windows = calculate_bet_windows(entry_tick, num_bets)
    final_end = windows[-1]["end_tick"]

    games_list = []

    for _, row in games_df.head(limit).iterrows():
        duration = int(row["duration_ticks"])
        prices = row["prices"]

        if isinstance(prices, np.ndarray):
            prices = prices.tolist()

        # Analyze outcome
        outcome = analyze_game_outcome(duration, entry_tick, num_bets)

        # Determine color category
        if outcome["outcome"] == "early_rug":
            color_category = "gray"  # Rugged before entry
        elif outcome["outcome"] == "win":
            color_category = "green"  # Won
        else:
            color_category = "red"  # Lost all bets

        games_list.append(
            {
                "game_id": row["game_id"],
                "duration": duration,
                "prices": prices,
                "peak": float(row["peak_multiplier"]),
                "peak_tick": int(row["peak_tick"]),
                "color_category": color_category,
                "outcome": outcome,
            }
        )

    return games_list


def get_duration_histogram(
    games_df: pd.DataFrame, bins: int = 50, max_tick: int = 500
) -> dict[str, list]:
    """
    Get duration histogram data for Chart.js.

    Returns:
        Dict with bin edges and counts
    """
    durations = games_df["duration_ticks"].clip(upper=max_tick)
    counts, edges = np.histogram(durations, bins=bins, range=(0, max_tick))

    return {
        "bin_edges": edges.tolist(),
        "counts": counts.tolist(),
        "bin_centers": ((edges[:-1] + edges[1:]) / 2).tolist(),
    }


def get_explorer_data(
    entry_tick: int = 200, num_bets: int = 4, game_limit: int = 50
) -> dict[str, Any]:
    """
    Get complete data for Game Explorer visualization.

    Args:
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets (1-4)
        game_limit: Maximum games to include for price curves

    Returns:
        Complete data dict for frontend
    """
    games_df = load_games_df()

    return {
        "strategy": calculate_strategy_stats(games_df, entry_tick, num_bets),
        "games": get_games_for_chart(games_df, entry_tick, num_bets, game_limit),
        "histogram": get_duration_histogram(games_df),
        "config": {
            "sidebet_window": SIDEBET_WINDOW,
            "sidebet_cooldown": SIDEBET_COOLDOWN,
            "sidebet_payout": SIDEBET_PAYOUT,
            "breakeven_rate": BREAKEVEN_RATE,
        },
    }
