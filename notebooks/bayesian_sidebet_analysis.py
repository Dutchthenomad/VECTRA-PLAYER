#!/usr/bin/env python3
"""
Bayesian & Probabilistic Sidebet Optimization Analysis

This module provides analysis functions for optimizing sidebet placement timing
using Bayesian inference, survival analysis, and expected value calculations.

Focus: 70% WHEN to place (optimal tick), 30% WHETHER to place (game selection)

Data Source: ~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet
- gameHistory[] with tick-by-tick prices
- globalSidebets with placed/payout events
- 568 deduplicated games (median: 150 ticks, range: 2-1815)
"""

import json
from dataclasses import dataclass

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

# ==============================================================================
# Data Loading & Preprocessing
# ==============================================================================


def load_game_data(min_ticks: int = 10) -> pd.DataFrame:
    """
    Load complete game data from parquet files.

    Args:
        min_ticks: Minimum tick count to include (filters out very short games)

    Returns:
        DataFrame with columns:
        - game_id: Unique game identifier
        - prices: List of tick-by-tick prices
        - peak_multiplier: Maximum price reached
        - tick_count: Total ticks in game
        - rug_tick: Tick where rug occurred (largest drop)
        - global_sidebets: List of all sidebets in this game
    """
    conn = duckdb.connect()

    df = conn.execute("""
        SELECT
            json_extract_string(raw_json, '$.id') as game_id,
            raw_json
        FROM read_parquet('~/rugs_data/events_parquet/doc_type=complete_game/**/*.parquet')
    """).df()

    # Deduplicate (same game captured in both rug emissions)
    df = df.drop_duplicates(subset=["game_id"], keep="first")

    # Parse JSON and extract fields
    games = []
    for _, row in df.iterrows():
        game = json.loads(row["raw_json"])
        prices = game.get("prices", [])

        if len(prices) < min_ticks:
            continue

        # Find rug tick (largest single drop)
        rug_tick = find_rug_tick(prices)

        games.append(
            {
                "game_id": game.get("id"),
                "prices": prices,
                "peak_multiplier": game.get("peakMultiplier", 0),
                "tick_count": len(prices),
                "rug_tick": rug_tick,
                "global_sidebets": game.get("globalSidebets", []),
                "timestamp": game.get("timestamp"),
                "server_seed_hash": game.get("provablyFair", {}).get("serverSeedHash"),
            }
        )

    return pd.DataFrame(games)


def find_rug_tick(prices: list[float]) -> int:
    """Find the tick where the rug occurred (largest single-tick drop)."""
    if len(prices) < 2:
        return len(prices) - 1

    max_drop = 0
    max_drop_idx = len(prices) - 1

    for i in range(1, len(prices)):
        drop = prices[i - 1] - prices[i]
        if drop > max_drop:
            max_drop = drop
            max_drop_idx = i

    return max_drop_idx


# ==============================================================================
# Feature Engineering
# ==============================================================================


@dataclass
class GameFeatures:
    """Features extracted from game state at a specific tick."""

    tick: int
    price: float
    age: int  # Ticks since game start
    distance_from_peak: float  # How far below peak price
    volatility_5: float  # 5-tick rolling volatility
    volatility_10: float  # 10-tick rolling volatility
    momentum_3: float  # 3-tick momentum (price change rate)
    momentum_5: float  # 5-tick momentum
    price_acceleration: float  # Second derivative (rate of momentum change)
    is_rising: bool  # Price trending up
    is_falling: bool  # Price trending down
    rapid_rise: bool  # Price increased >20% in last 3 ticks
    rapid_fall: bool  # Price decreased >20% in last 3 ticks
    peak_so_far: float  # Highest price seen so far
    ticks_since_peak: int  # How long since peak
    mean_reversion: float  # Distance from recent mean (10-tick)


def extract_features(prices: list[float], tick: int) -> GameFeatures:
    """
    Extract features from game state at a specific tick.

    These features are designed to predict P(rug in next 40 ticks | current_state).
    """
    # Ensure we have enough history
    if tick < 1:
        tick = 1

    current_price = prices[tick]
    price_history = prices[: tick + 1]
    peak_so_far = max(price_history)
    peak_tick = price_history.index(peak_so_far)

    # Volatility (standard deviation of price changes)
    def calc_volatility(window: int) -> float:
        if tick < window:
            return 0.0
        returns = np.diff(prices[max(0, tick - window) : tick + 1])
        return np.std(returns) if len(returns) > 0 else 0.0

    # Momentum (rate of price change)
    def calc_momentum(window: int) -> float:
        if tick < window:
            return 0.0
        return (prices[tick] - prices[tick - window]) / window

    vol_5 = calc_volatility(5)
    vol_10 = calc_volatility(10)
    mom_3 = calc_momentum(3)
    mom_5 = calc_momentum(5)

    # Price acceleration (second derivative)
    if tick >= 2:
        vel_current = prices[tick] - prices[tick - 1]
        vel_previous = prices[tick - 1] - prices[tick - 2]
        acceleration = vel_current - vel_previous
    else:
        acceleration = 0.0

    # Trend detection
    recent_prices = prices[max(0, tick - 3) : tick + 1]
    is_rising = len(recent_prices) > 1 and all(
        recent_prices[i] <= recent_prices[i + 1] for i in range(len(recent_prices) - 1)
    )
    is_falling = len(recent_prices) > 1 and all(
        recent_prices[i] >= recent_prices[i + 1] for i in range(len(recent_prices) - 1)
    )

    # Rapid changes
    if tick >= 3:
        change_3_tick = (
            (prices[tick] - prices[tick - 3]) / prices[tick - 3] if prices[tick - 3] > 0 else 0
        )
        rapid_rise = change_3_tick > 0.20
        rapid_fall = change_3_tick < -0.20
    else:
        rapid_rise = False
        rapid_fall = False

    # Mean reversion
    if tick >= 10:
        recent_mean = np.mean(prices[tick - 10 : tick + 1])
        mean_reversion = (current_price - recent_mean) / recent_mean if recent_mean > 0 else 0
    else:
        mean_reversion = 0.0

    return GameFeatures(
        tick=tick,
        price=current_price,
        age=tick,
        distance_from_peak=(peak_so_far - current_price) / peak_so_far if peak_so_far > 0 else 0,
        volatility_5=vol_5,
        volatility_10=vol_10,
        momentum_3=mom_3,
        momentum_5=mom_5,
        price_acceleration=acceleration,
        is_rising=is_rising,
        is_falling=is_falling,
        rapid_rise=rapid_rise,
        rapid_fall=rapid_fall,
        peak_so_far=peak_so_far,
        ticks_since_peak=tick - peak_tick,
        mean_reversion=mean_reversion,
    )


def create_training_dataset(games_df: pd.DataFrame, sidebet_window: int = 40) -> pd.DataFrame:
    """
    Create training dataset with features and target labels.

    For each tick in each game, extract features and label whether
    the rug occurred within the next 40 ticks (sidebet window).

    Args:
        games_df: DataFrame from load_game_data()
        sidebet_window: Sidebet duration in ticks (default 40)

    Returns:
        DataFrame with features + 'rug_in_window' target column
    """
    training_data = []

    for idx, game in games_df.iterrows():
        prices = game["prices"]
        rug_tick = game["rug_tick"]

        # Sample ticks (don't need every tick for training)
        # Sample every 5 ticks + always include critical points
        sample_ticks = set(range(0, len(prices), 5))
        sample_ticks.add(rug_tick)
        if rug_tick > 40:
            sample_ticks.add(rug_tick - 40)

        for tick in sorted(sample_ticks):
            if tick >= len(prices) - 1:
                continue

            features = extract_features(prices, tick)

            # Target: will rug occur in next 40 ticks?
            rug_in_window = (rug_tick > tick) and (rug_tick <= tick + sidebet_window)

            # Convert features to dict
            feature_dict = {
                "game_id": game["game_id"],
                "tick": features.tick,
                "price": features.price,
                "age": features.age,
                "distance_from_peak": features.distance_from_peak,
                "volatility_5": features.volatility_5,
                "volatility_10": features.volatility_10,
                "momentum_3": features.momentum_3,
                "momentum_5": features.momentum_5,
                "price_acceleration": features.price_acceleration,
                "is_rising": features.is_rising,
                "is_falling": features.is_falling,
                "rapid_rise": features.rapid_rise,
                "rapid_fall": features.rapid_fall,
                "peak_so_far": features.peak_so_far,
                "ticks_since_peak": features.ticks_since_peak,
                "mean_reversion": features.mean_reversion,
                "rug_in_window": rug_in_window,
                "ticks_to_rug": rug_tick - tick if rug_tick > tick else 0,
            }

            training_data.append(feature_dict)

    return pd.DataFrame(training_data)


# ==============================================================================
# 1. Bayesian Survival Analysis
# ==============================================================================


class BayesianSurvivalModel:
    """
    Bayesian survival analysis for rug prediction.

    Models P(rug in next N ticks | game_age, price_features) using:
    - Prior: Historical rug timing distribution
    - Likelihood: Feature-conditional rug probability
    - Posterior: Updated beliefs as game progresses
    """

    def __init__(self, games_df: pd.DataFrame):
        self.games_df = games_df
        self.hazard_rates = self._compute_baseline_hazard()

    def _compute_baseline_hazard(self) -> np.ndarray:
        """
        Compute baseline hazard function h(t) = P(rug at tick t | survived to t).

        This is the unconditional probability of rugging at each tick,
        given the game has survived that long.
        """
        max_tick = int(self.games_df["tick_count"].max())
        rug_counts = np.zeros(max_tick)
        survival_counts = np.zeros(max_tick)

        for _, game in self.games_df.iterrows():
            rug_tick = game["rug_tick"]
            tick_count = game["tick_count"]

            for t in range(tick_count):
                survival_counts[t] += 1
                if t == rug_tick:
                    rug_counts[t] += 1

        # Hazard rate = (rugs at t) / (games surviving to t)
        hazard = np.divide(
            rug_counts, survival_counts, out=np.zeros_like(rug_counts), where=survival_counts > 0
        )

        # Smooth with moving average to reduce noise
        window = 10
        hazard_smooth = np.convolve(hazard, np.ones(window) / window, mode="same")

        return hazard_smooth

    def survival_function(self, max_tick: int) -> np.ndarray:
        """
        Compute survival function S(t) = P(game survives past tick t).

        S(t) = exp(-∫[0,t] h(u) du) where h is hazard rate
        """
        cumulative_hazard = np.cumsum(self.hazard_rates[:max_tick])
        return np.exp(-cumulative_hazard)

    def predict_rug_probability(
        self, current_tick: int, window: int = 40, features: GameFeatures | None = None
    ) -> float:
        """
        Predict P(rug in next `window` ticks | current_tick, features).

        Args:
            current_tick: Current game age
            window: Prediction window (40 ticks for sidebet)
            features: Optional game features for conditional probability

        Returns:
            Probability of rug in next `window` ticks
        """
        if current_tick >= len(self.hazard_rates):
            return 1.0  # Already past observed data

        # Base probability from survival analysis
        S_now = self.survival_function(len(self.hazard_rates))[current_tick]
        S_future = self.survival_function(len(self.hazard_rates))[
            min(current_tick + window, len(self.hazard_rates) - 1)
        ]

        base_prob = 1 - (S_future / S_now) if S_now > 0 else 0.5

        # If features provided, apply conditional adjustment
        if features is not None:
            adjustment = self._feature_adjustment(features)
            return min(1.0, base_prob * adjustment)

        return base_prob

    def _feature_adjustment(self, features: GameFeatures) -> float:
        """
        Bayesian update based on features.

        Empirical rules based on observed patterns:
        - Rapid fall increases rug probability
        - High volatility increases rug probability
        - Long time since peak increases rug probability
        - Rapid rise slightly decreases rug probability (momentum)
        """
        adjustment = 1.0

        # Rapid fall is a strong rug signal
        if features.rapid_fall:
            adjustment *= 2.0

        # High volatility suggests instability
        if features.volatility_10 > 0.1:  # Threshold TBD from data
            adjustment *= 1.5

        # Time since peak matters
        if features.ticks_since_peak > 20:
            adjustment *= 1.3

        # Rapid rise suggests continued momentum
        if features.rapid_rise:
            adjustment *= 0.7

        # Distance from peak (mean reversion)
        if features.distance_from_peak > 0.3:  # >30% below peak
            adjustment *= 1.2

        return adjustment

    def plot_hazard_and_survival(self, ax=None):
        """Visualize hazard rate and survival function."""
        if ax is None:
            _fig, ax = plt.subplots(1, 2, figsize=(14, 5))

        ticks = np.arange(len(self.hazard_rates))
        survival = self.survival_function(len(self.hazard_rates))

        # Hazard rate
        ax[0].plot(ticks, self.hazard_rates, label="Hazard Rate h(t)", color="red")
        ax[0].set_xlabel("Tick")
        ax[0].set_ylabel("P(rug at tick t | survived to t)")
        ax[0].set_title("Baseline Hazard Function")
        ax[0].grid(True, alpha=0.3)
        ax[0].legend()

        # Survival function
        ax[1].plot(ticks, survival, label="Survival Function S(t)", color="blue")
        ax[1].set_xlabel("Tick")
        ax[1].set_ylabel("P(game survives past tick t)")
        ax[1].set_title("Survival Function")
        ax[1].grid(True, alpha=0.3)
        ax[1].legend()

        plt.tight_layout()
        return ax


# ==============================================================================
# 2. Expected Value Functions (Simplified Interface)
# ==============================================================================


def expected_value(p_win: float, payout_multiplier: int = 5, bet_amount: float = 0.001) -> float:
    """
    Compute EV of a sidebet.

    EV = P(win) × (payout) - P(lose) × (bet_amount)
       = P(win) × (bet × multiplier) - (1 - P(win)) × bet
       = bet × [P(win) × multiplier - (1 - P(win))]
       = bet × [P(win) × (multiplier + 1) - 1]

    Args:
        p_win: Probability of winning (rug in 40 ticks)
        payout_multiplier: Payout multiplier (5x, 10x, etc.)
        bet_amount: Bet size in SOL

    Returns:
        Expected value in SOL
    """
    return bet_amount * (p_win * (payout_multiplier + 1) - 1)


def breakeven_probability(payout_multiplier: int = 5) -> float:
    """
    Compute breakeven win probability.

    EV = 0 when P(win) × (multiplier + 1) - 1 = 0
    => P(win) = 1 / (multiplier + 1)

    For 5x payout: breakeven is 1/6 = 16.67%
    """
    return 1.0 / (payout_multiplier + 1)


def kelly_criterion(p_win: float, payout_multiplier: int = 5) -> float:
    """
    Compute Kelly Criterion for optimal bet sizing.

    f* = (p × b - q) / b
    where:
        f* = fraction of bankroll to bet
        p = win probability
        q = 1 - p (lose probability)
        b = net payout odds (e.g., 4 for 5x payout)

    Args:
        p_win: Probability of winning
        payout_multiplier: Payout multiplier (5x, 10x, etc.)

    Returns:
        Optimal fraction of bankroll to bet (0-1)
    """
    b = payout_multiplier - 1  # Net odds (5x payout = 4 net)
    p = p_win
    q = 1 - p

    kelly = (p * b - q) / b

    # Never bet negative (Kelly says "don't bet")
    return max(0.0, kelly)


# ==============================================================================
# Main Analysis Function
# ==============================================================================


def run_quick_analysis():
    """Quick analysis to verify everything works."""
    print("=" * 70)
    print("BAYESIAN SIDEBET ANALYSIS - QUICK TEST")
    print("=" * 70)

    # Load data
    print("\n[1/3] Loading game data...")
    games_df = load_game_data(min_ticks=10)
    print(f"  Loaded {len(games_df)} games")

    # Create training set
    print("\n[2/3] Creating training dataset...")
    training_df = create_training_dataset(games_df, sidebet_window=40)
    print(f"  Generated {len(training_df)} samples")
    print(f"  Base rug rate: {training_df['rug_in_window'].mean():.1%}")

    # Fit survival model
    print("\n[3/3] Fitting survival model...")
    model = BayesianSurvivalModel(games_df)

    # Test prediction
    test_tick = 250
    p_win = model.predict_rug_probability(test_tick, window=40)
    ev = expected_value(p_win, payout_multiplier=5)

    print(f"\n  Test Prediction at tick {test_tick}:")
    print(f"    P(win) = {p_win:.2%}")
    print(f"    EV = {ev:.6f} SOL")
    print(f"    Breakeven = {breakeven_probability(5):.2%}")
    print(f"    Kelly fraction = {kelly_criterion(p_win, 5):.2%}")

    print("\n" + "=" * 70)
    print("SUCCESS - Ready for full analysis")
    print("=" * 70)

    return games_df, training_df, model


if __name__ == "__main__":
    # Run quick test
    games_df, training_df, model = run_quick_analysis()
