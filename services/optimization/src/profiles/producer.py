"""Strategy Profile Producer - generates profiles from completed games."""

import uuid
from datetime import datetime

import numpy as np

from ..analyzers.bayesian import BASE_PROBABILITY_CURVE
from ..analyzers.monte_carlo import MonteCarloConfig, MonteCarloSimulator
from ..analyzers.survival import find_optimal_entry_window
from .models import StrategyProfile


class ProfileProducer:
    """
    Produces Strategy Profiles from completed game data.

    Workflow:
    1. Extract durations from games
    2. Run survival analysis → optimal entry window
    3. Run Monte Carlo (10k iterations) → risk metrics
    4. Generate profile with all parameters
    """

    def __init__(
        self,
        kelly_fraction: float = 0.25,
        min_edge_threshold: float = 0.02,
        monte_carlo_iterations: int = 10000,
    ):
        """
        Initialize producer.

        Args:
            kelly_fraction: Kelly fraction for sizing (0.25 = quarter Kelly)
            min_edge_threshold: Minimum edge required (0.02 = 2%)
            monte_carlo_iterations: Number of MC iterations
        """
        self.kelly_fraction = kelly_fraction
        self.min_edge_threshold = min_edge_threshold
        self.monte_carlo_iterations = monte_carlo_iterations

    def generate_profile(
        self,
        games: list[dict],
        profile_id: str | None = None,
    ) -> StrategyProfile:
        """
        Generate a strategy profile from completed games.

        Args:
            games: List of game dicts with 'duration' field
            profile_id: Optional profile ID (auto-generated if None)

        Returns:
            StrategyProfile with all analysis results
        """
        if not profile_id:
            profile_id = f"profile-{uuid.uuid4().hex[:8]}"

        # Extract durations
        durations = self._extract_durations(games)

        # Run survival analysis
        optimal = find_optimal_entry_window(
            durations,
            window_size=40,
            min_edge=self.min_edge_threshold,
        )

        optimal_tick = optimal.get("optimal_entry_tick", 200)
        if optimal_tick is None:
            optimal_tick = 200  # Default if no edge found

        win_rate = optimal.get("win_rate_at_optimal", 0.185)

        # Run Monte Carlo simulation
        mc_config = MonteCarloConfig(
            kelly_fraction=self.kelly_fraction,
            assumed_win_rate=win_rate,
        )
        mc_sim = MonteCarloSimulator(mc_config, seed=42)
        mc_results = mc_sim.run(
            num_iterations=self.monte_carlo_iterations,
            num_games=500,
            win_rate=win_rate,
        )

        return StrategyProfile(
            profile_id=profile_id,
            created_at=datetime.utcnow(),
            kelly_variant=self._kelly_variant_name(),
            min_edge_threshold=self.min_edge_threshold,
            optimal_entry_tick=optimal_tick,
            expected_return=mc_results["summary"]["mean_final_bankroll"] - 0.1,
            probability_profit=mc_results["risk_metrics"]["probability_profit"],
            probability_ruin=mc_results["risk_metrics"]["probability_ruin"],
            var_95=mc_results["var_metrics"]["var_95"],
            sharpe_ratio=mc_results["performance"]["sharpe_ratio"],
            base_probability_curve=list(BASE_PROBABILITY_CURVE),
            gap_signal_thresholds={
                "warning_ms": 350,
                "high_alert_ms": 450,
                "detected_ms": 500,
            },
        )

    def _extract_durations(self, games: list[dict]) -> np.ndarray:
        """Extract duration array from games."""
        durations = []
        for game in games:
            duration = game.get("duration") or game.get("ticks") or game.get("length")
            if duration:
                durations.append(int(duration))
        return np.array(durations) if durations else np.array([200])

    def _kelly_variant_name(self) -> str:
        """Get Kelly variant name from fraction."""
        if self.kelly_fraction <= 0.125:
            return "eighth"
        elif self.kelly_fraction <= 0.25:
            return "quarter"
        elif self.kelly_fraction <= 0.5:
            return "half"
        elif self.kelly_fraction <= 0.75:
            return "three_quarter"
        else:
            return "full"
