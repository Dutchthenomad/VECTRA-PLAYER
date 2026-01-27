"""
Survival Analysis for Sidebet Timing

Statistical analysis of game duration and rug timing using
survival analysis techniques.

Usage:
    from survival_analysis import (
        compute_survival_curve,
        compute_hazard_rate,
        compute_conditional_probability,
        find_optimal_entry_window,
    )

    durations = np.array([150, 200, 180, 300, 250, ...])  # Game durations

    survival = compute_survival_curve(durations)
    hazard = compute_hazard_rate(durations)
    cond_prob = compute_conditional_probability(durations, window_size=40)
    optimal = find_optimal_entry_window(durations)
"""

import numpy as np


def compute_survival_curve(durations: np.ndarray) -> dict:
    """
    Compute Kaplan-Meier survival curve.

    S(t) = P(T > t) = probability of surviving past time t

    For rugs.fun: S(t) = probability game lasts beyond tick t

    Args:
        durations: Array of game durations in ticks

    Returns:
        Dict with time points, survival probabilities, and at-risk counts

    Example:
        durations = np.array([100, 150, 200, 250, 300])
        curve = compute_survival_curve(durations)
        # curve['survival'][idx] = P(game lasts > curve['times'][idx])
    """
    sorted_durations = np.sort(durations)
    n = len(sorted_durations)

    # Get unique times and counts
    unique_times, counts = np.unique(sorted_durations, return_counts=True)

    # Kaplan-Meier estimator
    survival_probs = []
    at_risk_counts = []
    at_risk = n

    for t, d in zip(unique_times, counts):
        at_risk_counts.append(at_risk)
        # P(survive past t | at risk) = (at_risk - events) / at_risk
        survival_prob = (at_risk - d) / at_risk if at_risk > 0 else 0
        survival_probs.append(survival_prob)
        at_risk -= d

    # Cumulative survival: S(t) = product of conditional survivals up to t
    cumulative_survival = np.cumprod(survival_probs)

    return {
        "times": unique_times,
        "survival": cumulative_survival,
        "n_at_risk": np.array(at_risk_counts),
        "events": counts,
    }


def compute_hazard_rate(durations: np.ndarray, bandwidth: int = 10) -> dict:
    """
    Compute hazard rate h(t) = f(t) / S(t).

    Hazard rate is the instantaneous risk of rugging given survival to time t.

    For rugs.fun: h(t) = P(rug at tick t | game reached tick t)

    Args:
        durations: Array of game durations
        bandwidth: Smoothing window size for rolling average

    Returns:
        Dict with time grid, raw hazard, smoothed hazard, and at-risk counts

    Example:
        hazard = compute_hazard_rate(durations, bandwidth=5)
        # hazard['hazard_smooth'][200] = smoothed rug risk at tick 200
    """
    max_time = int(np.max(durations))
    time_grid = np.arange(0, max_time + 1)

    # Count events at each time
    event_counts = np.zeros(max_time + 1)
    for d in durations:
        event_counts[int(d)] += 1

    # Count at risk at each time
    at_risk = np.zeros(max_time + 1)
    for t in range(max_time + 1):
        at_risk[t] = np.sum(durations >= t)

    # Hazard rate: h(t) = events at t / at risk at t
    hazard = np.zeros(max_time + 1)
    for t in range(max_time + 1):
        if at_risk[t] > 0:
            hazard[t] = event_counts[t] / at_risk[t]

    # Smooth with rolling average
    if bandwidth > 1:
        kernel = np.ones(bandwidth) / bandwidth
        hazard_smooth = np.convolve(hazard, kernel, mode="same")
    else:
        hazard_smooth = hazard.copy()

    return {
        "times": time_grid,
        "hazard": hazard,
        "hazard_smooth": hazard_smooth,
        "at_risk": at_risk,
        "events": event_counts,
    }


def compute_conditional_probability(
    durations: np.ndarray, window_size: int = 40, max_tick: int = 500
) -> np.ndarray:
    """
    Compute P(rug in next w ticks | survived to tick t).

    This is the key metric for sidebet timing decisions.

    Args:
        durations: Array of game durations
        window_size: Sidebet window (40 ticks default)
        max_tick: Maximum tick to compute

    Returns:
        Array where index t = P(rug in [t, t+window] | survived to t)

    Example:
        cond_probs = compute_conditional_probability(durations)
        # cond_probs[200] = probability of rug in ticks 200-240 given game reached 200
    """
    conditional_probs = np.zeros(max_tick + 1)

    for t in range(max_tick + 1):
        # Games that survived to tick t
        survived_to_t = durations[durations >= t]
        n_survived = len(survived_to_t)

        if n_survived == 0:
            conditional_probs[t] = 1.0  # All games ended before t
            continue

        # Games that rugged within window [t, t + window_size)
        rugged_in_window = np.sum((survived_to_t >= t) & (survived_to_t < t + window_size))

        # P(rug in window | survived to t)
        conditional_probs[t] = rugged_in_window / n_survived

    return conditional_probs


def survival_analysis_report(durations: np.ndarray) -> dict:
    """
    Generate comprehensive survival analysis report.

    Args:
        durations: Array of game durations

    Returns:
        Dict with all survival metrics
    """
    # Basic statistics
    stats_dict = {
        "count": len(durations),
        "mean": float(np.mean(durations)),
        "median": float(np.median(durations)),
        "std": float(np.std(durations)),
        "min": float(np.min(durations)),
        "max": float(np.max(durations)),
    }

    # Percentiles
    percentiles = {
        "p10": float(np.percentile(durations, 10)),
        "p25": float(np.percentile(durations, 25)),
        "p50": float(np.percentile(durations, 50)),
        "p75": float(np.percentile(durations, 75)),
        "p90": float(np.percentile(durations, 90)),
        "p95": float(np.percentile(durations, 95)),
    }

    # Survival at key ticks
    survival_curve = compute_survival_curve(durations)
    survival_at_ticks = {}
    for tick in [50, 100, 150, 200, 250, 300, 400, 500]:
        idx = np.searchsorted(survival_curve["times"], tick)
        if idx < len(survival_curve["survival"]):
            survival_at_ticks[f"S({tick})"] = float(survival_curve["survival"][idx])
        else:
            survival_at_ticks[f"S({tick})"] = 0.0

    # Conditional probabilities at key ticks
    cond_probs = compute_conditional_probability(durations)
    conditional_at_ticks = {}
    for tick in [50, 100, 150, 200, 250, 300]:
        if tick < len(cond_probs):
            conditional_at_ticks[f"P(rug|t>{tick})"] = float(cond_probs[tick])

    return {
        "statistics": stats_dict,
        "percentiles": percentiles,
        "survival_at_ticks": survival_at_ticks,
        "conditional_probabilities": conditional_at_ticks,
    }


def find_optimal_entry_window(
    durations: np.ndarray,
    window_size: int = 40,
    min_edge: float = 0.02,  # 2% above breakeven
    kelly_fraction: float = 0.25,
) -> dict:
    """
    Find optimal tick range for sidebet entry.

    Optimal = where conditional probability exceeds breakeven
    and expected value is maximized.

    Args:
        durations: Game durations
        window_size: Sidebet window (40 ticks)
        min_edge: Minimum edge required above breakeven
        kelly_fraction: Kelly fraction for sizing

    Returns:
        Dict with optimal entry recommendations

    Example:
        optimal = find_optimal_entry_window(durations)
        # optimal['optimal_entry_tick'] = best tick to start betting
        # optimal['positive_edge_range'] = (start, end) ticks with edge
    """
    cond_probs = compute_conditional_probability(durations, window_size)
    breakeven = 1 / 6  # 16.67% for 5:1 payout

    # Find ticks with positive edge
    edge = cond_probs - breakeven
    positive_edge_ticks = np.where(edge > min_edge)[0]

    if len(positive_edge_ticks) == 0:
        return {
            "optimal_entry_tick": None,
            "message": "No ticks with positive edge found",
        }

    # Find maximum edge tick
    max_edge_tick = int(np.argmax(edge))
    max_edge = float(edge[max_edge_tick])

    # Kelly calculation
    win_rate = cond_probs[max_edge_tick]
    kelly = (win_rate * 4 - (1 - win_rate)) / 4
    recommended_bet = kelly * kelly_fraction

    return {
        "optimal_entry_tick": max_edge_tick,
        "win_rate_at_optimal": float(cond_probs[max_edge_tick]),
        "edge_at_optimal": max_edge,
        "kelly_fraction": float(max(0, kelly)),
        "recommended_bet_pct": float(max(0, recommended_bet * 100)),
        "positive_edge_range": (
            int(positive_edge_ticks[0]),
            int(positive_edge_ticks[-1]),
        ),
        "ev_per_bet": float(max_edge * 4),  # Expected value per unit bet
    }


def should_place_sidebet(
    current_tick: int,
    durations: np.ndarray,
    window_size: int = 40,
    min_edge: float = 0.02,
) -> dict:
    """
    Decide whether to place sidebet based on survival analysis.

    Args:
        current_tick: Current game tick
        durations: Historical game durations
        window_size: Sidebet window (40 ticks)
        min_edge: Minimum edge threshold

    Returns:
        Decision dict with recommendation
    """
    cond_probs = compute_conditional_probability(durations, window_size)
    breakeven = 1 / 6  # 16.67%

    if current_tick >= len(cond_probs):
        win_rate = 0.96  # Very late in game
    else:
        win_rate = cond_probs[current_tick]

    edge = win_rate - breakeven

    return {
        "tick": current_tick,
        "win_rate": float(win_rate),
        "breakeven": breakeven,
        "edge": float(edge),
        "should_bet": edge > min_edge,
        "confidence": "high" if edge > 0.10 else "medium" if edge > 0.05 else "low",
    }
