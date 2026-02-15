"""
Kelly Criterion Position Sizing

Implements all 8 Kelly variants used in VECTRA-PLAYER for
optimal bet sizing in sidebet strategies.

Usage:
    from kelly_sizing import (
        kelly_criterion,
        fractional_kelly,
        calculate_all_variants,
        recommend_bet_size,
    )

    # Basic Kelly
    fraction = kelly_criterion(win_rate=0.20, payout=5.0)

    # Recommended: Quarter Kelly
    fraction = fractional_kelly(win_rate=0.20, fraction=0.25)

    # Get all variants
    variants = calculate_all_variants(win_rate=0.20, bankroll=0.1)
"""

from dataclasses import dataclass


@dataclass
class KellyResult:
    """Result of Kelly calculation."""

    name: str
    fraction: float
    bet_size: float
    risk_level: str
    growth_rate: float  # Relative to full Kelly
    variance: float  # Relative to full Kelly


def kelly_criterion(win_rate: float, payout: float = 5.0) -> float:
    """
    Calculate full Kelly fraction.

    The Kelly Criterion maximizes long-term geometric growth rate.

    Formula:
        f* = (p × b - q) / b

    Where:
        p = probability of winning
        q = probability of losing (1 - p)
        b = net odds (payout - 1)

    For 5:1 sidebet payout:
        b = 4 (you win 4x your bet, plus return of original)
        Breakeven: p = 1/6 = 16.67%

    Args:
        win_rate: Probability of winning (0 to 1)
        payout: Total payout multiplier (5.0 for 5:1)

    Returns:
        Kelly fraction (fraction of bankroll to bet)
        Returns 0 if no edge (negative Kelly)

    Example:
        >>> kelly_criterion(0.20, 5.0)  # 20% win rate, 5:1 payout
        0.05  # Bet 5% of bankroll
    """
    p = win_rate
    q = 1 - p
    b = payout - 1  # Net odds

    if b <= 0:
        return 0.0

    kelly = (p * b - q) / b

    # Don't bet with negative edge
    return max(0.0, kelly)


def fractional_kelly(
    win_rate: float,
    fraction: float = 0.25,
    payout: float = 5.0,
) -> float:
    """
    Calculate fractional Kelly for reduced variance.

    Full Kelly is theoretically optimal but has high variance.
    Fractional Kelly trades some growth for stability.

    Growth vs Variance tradeoff:
        Fraction | Growth | Variance
        1.00     | 100%   | 100%
        0.75     | 93.8%  | 56.3%
        0.50     | 75%    | 25%
        0.25     | 43.8%  | 6.3%
        0.125    | 23.4%  | 1.6%

    Args:
        win_rate: Probability of winning
        fraction: Kelly fraction (0.25 = quarter Kelly)
        payout: Total payout multiplier

    Returns:
        Bet size as fraction of bankroll
    """
    full_kelly = kelly_criterion(win_rate, payout)
    return full_kelly * fraction


# Kelly variant configurations
KELLY_VARIANTS = {
    "full_kelly": {
        "fraction": 1.0,
        "growth_rate": 1.0,
        "variance": 1.0,
        "risk_level": "Extreme",
        "description": "Maximum growth, maximum risk",
    },
    "three_quarter_kelly": {
        "fraction": 0.75,
        "growth_rate": 0.938,
        "variance": 0.563,
        "risk_level": "High",
        "description": "94% growth, 44% less variance",
    },
    "half_kelly": {
        "fraction": 0.50,
        "growth_rate": 0.75,
        "variance": 0.25,
        "risk_level": "Medium",
        "description": "75% growth, 75% less variance",
    },
    "quarter_kelly": {
        "fraction": 0.25,
        "growth_rate": 0.438,
        "variance": 0.063,
        "risk_level": "Low (Recommended)",
        "description": "44% growth, 94% less variance",
    },
    "eighth_kelly": {
        "fraction": 0.125,
        "growth_rate": 0.234,
        "variance": 0.016,
        "risk_level": "Very Low",
        "description": "23% growth, minimal variance",
    },
    "sixteenth_kelly": {
        "fraction": 0.0625,
        "growth_rate": 0.121,
        "variance": 0.004,
        "risk_level": "Minimal",
        "description": "12% growth, near-zero variance",
    },
    "aggressive_kelly": {
        "fraction": 1.5,
        "growth_rate": 0.875,  # Actually decreases!
        "variance": 2.25,
        "risk_level": "Extreme+",
        "description": "OVER-BETTING: Less growth, more risk!",
    },
    "double_kelly": {
        "fraction": 2.0,
        "growth_rate": 0.0,  # Zero long-term growth
        "variance": 4.0,
        "risk_level": "Ruin",
        "description": "GUARANTEED RUIN: Never do this",
    },
}


def calculate_all_variants(
    win_rate: float,
    bankroll: float,
    payout: float = 5.0,
) -> dict[str, KellyResult]:
    """
    Calculate all Kelly variants for comparison.

    Args:
        win_rate: Probability of winning
        bankroll: Current bankroll
        payout: Total payout multiplier

    Returns:
        Dict of variant name to KellyResult
    """
    full = kelly_criterion(win_rate, payout)
    results = {}

    for name, config in KELLY_VARIANTS.items():
        fraction = full * config["fraction"]
        results[name] = KellyResult(
            name=name,
            fraction=fraction,
            bet_size=bankroll * fraction,
            risk_level=config["risk_level"],
            growth_rate=config["growth_rate"],
            variance=config["variance"],
        )

    return results


def calculate_edge(win_rate: float, payout: float = 5.0) -> dict:
    """
    Calculate the mathematical edge for a betting opportunity.

    Edge = Expected Value per unit bet

    Args:
        win_rate: Probability of winning
        payout: Total return multiplier

    Returns:
        Dict with edge metrics
    """
    p = win_rate
    q = 1 - p
    profit_on_win = payout - 1

    # Expected value per unit bet
    ev = p * profit_on_win - q

    # Breakeven win rate
    breakeven = 1 / payout

    # Edge as percentage
    edge_pct = (win_rate - breakeven) / breakeven if breakeven > 0 else 0

    # Kelly fraction
    kelly = kelly_criterion(win_rate, payout)

    return {
        "expected_value": ev,
        "expected_value_pct": ev * 100,
        "breakeven_win_rate": breakeven,
        "actual_win_rate": win_rate,
        "edge_exists": ev > 0,
        "edge_pct": edge_pct * 100,
        "kelly_fraction": kelly,
        "recommended_bet": fractional_kelly(win_rate, 0.25, payout),
        "verdict": "BET" if ev > 0 else "NO BET",
    }


def recommend_bet_size(
    win_rate: float,
    bankroll: float,
    payout: float = 5.0,
    risk_tolerance: str = "moderate",
) -> dict:
    """
    Get practical bet size recommendation.

    Args:
        win_rate: Estimated probability of winning
        bankroll: Current bankroll
        payout: Payout multiplier
        risk_tolerance: "low", "moderate", "high", "aggressive"

    Returns:
        Dict with recommendation
    """
    fraction_map = {
        "low": 0.125,  # Eighth Kelly
        "moderate": 0.25,  # Quarter Kelly (default)
        "high": 0.50,  # Half Kelly
        "aggressive": 0.75,  # Three-quarter Kelly
    }

    fraction = fraction_map.get(risk_tolerance, 0.25)
    kelly_frac = fractional_kelly(win_rate, fraction, payout)
    bet_size = bankroll * kelly_frac

    edge = calculate_edge(win_rate, payout)

    # Cap at 5% of bankroll for safety
    max_bet = bankroll * 0.05
    safe_bet = min(bet_size, max_bet)

    return {
        "kelly_fraction": kelly_frac,
        "raw_bet_size": bet_size,
        "recommended_bet_size": safe_bet,
        "pct_of_bankroll": safe_bet / bankroll * 100 if bankroll > 0 else 0,
        "edge": edge,
        "risk_tolerance": risk_tolerance,
        "capped": bet_size > max_bet,
        "warnings": (
            [
                "Win rate estimation is crucial - small errors compound",
                "Use conservative estimates when uncertain",
            ]
            if kelly_frac > 0.02
            else []
        ),
    }


def suggest_kelly_sizing(
    win_rate: float,
    initial_balance: float,
    num_bets: int,
    kelly_fraction: float = 0.25,
) -> list[float]:
    """
    Suggest Kelly-based bet sizes for a multi-bet strategy.

    Divides fractional Kelly across multiple bet windows.

    Args:
        win_rate: Win rate as percentage (e.g., 20 for 20%)
        initial_balance: Starting bankroll
        num_bets: Number of bets in sequence
        kelly_fraction: Kelly fraction to use (0.25 = quarter)

    Returns:
        List of suggested bet sizes
    """
    # Convert percentage to decimal if needed
    if win_rate > 1:
        win_rate = win_rate / 100

    kelly = fractional_kelly(win_rate, fraction=kelly_fraction)

    if kelly <= 0:
        return [0.0] * num_bets

    # Divide Kelly fraction across bets
    per_bet_fraction = kelly / num_bets
    per_bet_size = initial_balance * per_bet_fraction

    return [per_bet_size] * num_bets
