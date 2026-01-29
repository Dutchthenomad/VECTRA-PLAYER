"""
Monte Carlo Simulation Engine

Core simulation engine for testing sidebet strategies with
10,000+ iterations for statistical reliability.

Usage:
    from monte_carlo_sim import MonteCarloSimulator, MonteCarloConfig

    config = MonteCarloConfig(
        initial_bankroll=0.1,
        base_bet_size=0.001,
        drawdown_halt=0.15,
    )

    simulator = MonteCarloSimulator(config, seed=42)
    results = simulator.run(num_iterations=10000, num_games=500, win_rate=0.185)

    print(f"Mean final: {results['summary']['mean_final_bankroll']:.4f}")
    print(f"P(profit): {results['risk_metrics']['probability_profit']:.1%}")
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class ScalingMode(Enum):
    """Bet sizing strategy modes."""

    FIXED = "fixed"
    KELLY = "kelly"
    AGGRESSIVE_KELLY = "aggressive_kelly"
    ANTI_MARTINGALE = "anti_martingale"
    THETA_BAYESIAN = "theta_bayesian"
    VOLATILITY_ADJUSTED = "volatility_adjusted"


@dataclass
class MonteCarloConfig:
    """
    Configuration for Monte Carlo simulation.

    Attributes:
        initial_bankroll: Starting balance (SOL)
        base_bet_size: Base bet size (SOL)
        num_bets_per_game: Number of sidebets per game
        scaling_mode: Bet sizing strategy
        drawdown_halt: Circuit breaker threshold (e.g., 0.15 = 15%)
        kelly_fraction: Fraction of Kelly to use
        assumed_win_rate: Win rate for Kelly calculation
        win_streak_multiplier: Anti-martingale multiplier
        max_streak_multiplier: Cap for streak multiplier
        theta_base: Bayesian starting theta
        theta_max: Bayesian max theta
        theta_scale: Games for theta midpoint
        volatility_base: Baseline volatility for adjustment
    """

    initial_bankroll: float = 0.1
    base_bet_size: float = 0.001
    num_bets_per_game: int = 4
    scaling_mode: ScalingMode = ScalingMode.FIXED
    drawdown_halt: float = 0.15
    kelly_fraction: float = 0.25
    assumed_win_rate: float = 0.185
    win_streak_multiplier: float = 1.5
    max_streak_multiplier: float = 4.0
    theta_base: float = 0.5
    theta_max: float = 2.0
    theta_scale: int = 100
    volatility_base: float = 0.102917


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine for sidebet strategies.

    Simulates thousands of trading sessions to estimate:
    - Expected final bankroll distribution
    - Risk metrics (VaR, max drawdown)
    - Probability of various outcomes (profit, 2x, ruin)

    Example:
        config = MonteCarloConfig(scaling_mode=ScalingMode.THETA_BAYESIAN)
        sim = MonteCarloSimulator(config, seed=42)
        results = sim.run(10000, 500, 0.185)
    """

    def __init__(self, config: MonteCarloConfig, seed: int | None = None):
        self.config = config
        self.rng = np.random.default_rng(seed)

    def run(
        self,
        num_iterations: int = 10000,
        num_games: int = 500,
        win_rate: float = 0.185,
    ) -> dict:
        """
        Run Monte Carlo simulation.

        Args:
            num_iterations: Number of simulation runs (10k recommended)
            num_games: Games per simulation (500 default)
            win_rate: Probability of winning each bet

        Returns:
            Dict with results and statistics
        """
        final_bankrolls = []
        max_drawdowns = []
        games_to_ruin = []

        for _ in range(num_iterations):
            result = self._run_single_simulation(num_games, win_rate)

            if result["ruined"]:
                games_to_ruin.append(result["games_until_ruin"])
            else:
                final_bankrolls.append(result["final_bankroll"])

            max_drawdowns.append(result["max_drawdown"])

        return self._aggregate_results(
            final_bankrolls, max_drawdowns, games_to_ruin, num_iterations
        )

    def _run_single_simulation(self, num_games: int, win_rate: float) -> dict:
        """Run a single simulation of num_games games."""
        bankroll = self.config.initial_bankroll
        peak = bankroll
        max_dd = 0.0
        win_streak = 0
        games_played = 0
        ruined = False
        halted = False

        for game in range(num_games):
            if bankroll <= 0.001:  # Effectively bankrupt
                ruined = True
                break

            games_played += 1

            # Sample volatility for this game
            game_volatility = self._sample_game_volatility()

            # Simulate bet sequence for this game
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

                # Update bankroll
                if won:
                    bankroll += bet_size * 4  # 5:1 payout, net profit = 4x
                    win_streak += 1
                else:
                    bankroll -= bet_size
                    win_streak = 0

                # Update peak and drawdown
                if bankroll > peak:
                    peak = bankroll
                current_dd = (peak - bankroll) / peak if peak > 0 else 0
                max_dd = max(max_dd, current_dd)

                # Circuit breaker
                if current_dd >= self.config.drawdown_halt:
                    halted = True
                    break

            if halted:
                break

        return {
            "final_bankroll": bankroll,
            "max_drawdown": max_dd,
            "games_until_ruin": games_played if ruined else None,
            "ruined": ruined,
            "halted": halted,
        }

    def _sample_game_volatility(self) -> float:
        """
        Sample volatility for a single game.

        Uses log-normal distribution to model volatility clustering.
        """
        return self.rng.lognormal(
            mean=np.log(self.config.volatility_base),
            sigma=0.3,  # Empirical volatility of volatility
        )

    def _calculate_bet_size(
        self,
        bankroll: float,
        win_streak: int,
        games_played: int,
        volatility: float,
    ) -> float:
        """Calculate bet size based on strategy configuration."""
        base = self.config.base_bet_size
        mode = self.config.scaling_mode

        if mode == ScalingMode.FIXED:
            return base

        elif mode == ScalingMode.KELLY:
            kelly = self._kelly_fraction(self.config.assumed_win_rate)
            return bankroll * kelly * self.config.kelly_fraction

        elif mode == ScalingMode.AGGRESSIVE_KELLY:
            kelly = self._kelly_fraction(self.config.assumed_win_rate)
            return bankroll * kelly * min(0.75, self.config.kelly_fraction * 1.5)

        elif mode == ScalingMode.ANTI_MARTINGALE:
            multiplier = min(
                self.config.win_streak_multiplier**win_streak,
                self.config.max_streak_multiplier,
            )
            return base * multiplier

        elif mode == ScalingMode.THETA_BAYESIAN:
            theta = self._calculate_theta(games_played)
            return base * theta

        elif mode == ScalingMode.VOLATILITY_ADJUSTED:
            vol_ratio = volatility / self.config.volatility_base
            vol_adj = 1 / vol_ratio if vol_ratio > 0 else 1
            return base * min(2.0, max(0.5, vol_adj))

        return base

    def _kelly_fraction(self, win_rate: float) -> float:
        """Calculate Kelly fraction for 5:1 payout."""
        p = win_rate
        q = 1 - p
        b = 4  # Net odds for 5:1 payout
        kelly = (p * b - q) / b
        return max(0, kelly)

    def _calculate_theta(self, games_played: int) -> float:
        """Calculate theta multiplier for Bayesian sizing."""
        return self.config.theta_base + (
            (self.config.theta_max - self.config.theta_base)
            * (1 - 1 / (1 + games_played / self.config.theta_scale))
        )

    def _aggregate_results(
        self,
        final_bankrolls: list,
        max_drawdowns: list,
        games_to_ruin: list,
        num_iterations: int,
    ) -> dict:
        """Aggregate simulation results into statistics."""
        fb = np.array(final_bankrolls) if final_bankrolls else np.array([0])
        dd = np.array(max_drawdowns)
        initial = self.config.initial_bankroll

        num_ruined = len(games_to_ruin)

        return {
            "summary": {
                "mean_final_bankroll": float(np.mean(fb)),
                "median_final_bankroll": float(np.median(fb)),
                "std_final_bankroll": float(np.std(fb)),
                "min_final_bankroll": float(np.min(fb)),
                "max_final_bankroll": float(np.max(fb)),
            },
            "risk_metrics": {
                "probability_profit": float(np.mean(fb > initial)),
                "probability_2x": float(np.mean(fb > initial * 2)),
                "probability_5x": float(np.mean(fb > initial * 5)),
                "probability_ruin": float(num_ruined / num_iterations),
            },
            "drawdown": {
                "mean_max_drawdown": float(np.mean(dd)),
                "median_max_drawdown": float(np.median(dd)),
                "max_max_drawdown": float(np.max(dd)),
            },
            "performance": {
                "sharpe_ratio": self._calc_sharpe(fb, initial),
                "sortino_ratio": self._calc_sortino(fb, initial),
                "calmar_ratio": self._calc_calmar(fb, dd, initial),
            },
            "var_metrics": {
                "var_95": float(np.percentile(fb, 5)),
                "var_99": float(np.percentile(fb, 1)),
                "cvar_95": self._calc_cvar(fb, 5),
                "cvar_99": self._calc_cvar(fb, 1),
            },
            "distribution": {
                "p5": float(np.percentile(fb, 5)),
                "p10": float(np.percentile(fb, 10)),
                "p25": float(np.percentile(fb, 25)),
                "p50": float(np.percentile(fb, 50)),
                "p75": float(np.percentile(fb, 75)),
                "p90": float(np.percentile(fb, 90)),
                "p95": float(np.percentile(fb, 95)),
            },
            "ruin_analysis": {
                "num_ruined": num_ruined,
                "mean_games_to_ruin": (float(np.mean(games_to_ruin)) if games_to_ruin else None),
                "median_games_to_ruin": (
                    float(np.median(games_to_ruin)) if games_to_ruin else None
                ),
            },
            "iteration_count": num_iterations,
        }

    def _calc_sharpe(self, final_bankrolls: np.ndarray, initial: float) -> float:
        """Calculate Sharpe ratio (returns / std)."""
        returns = (final_bankrolls - initial) / initial
        if np.std(returns) == 0:
            return 0
        return float(np.mean(returns) / np.std(returns))

    def _calc_sortino(self, final_bankrolls: np.ndarray, initial: float) -> float:
        """Calculate Sortino ratio (returns / downside std)."""
        returns = (final_bankrolls - initial) / initial
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0 or np.std(negative_returns) == 0:
            return float(np.mean(returns))
        return float(np.mean(returns) / np.std(negative_returns))

    def _calc_calmar(
        self,
        final_bankrolls: np.ndarray,
        max_drawdowns: np.ndarray,
        initial: float,
    ) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        mean_return = np.mean(final_bankrolls - initial) / initial
        mean_dd = np.mean(max_drawdowns)
        if mean_dd == 0:
            return 0
        return float(mean_return / mean_dd)

    def _calc_cvar(self, data: np.ndarray, percentile: float) -> float:
        """Calculate Conditional VaR (Expected Shortfall)."""
        var_threshold = np.percentile(data, percentile)
        below_var = data[data <= var_threshold]
        if len(below_var) == 0:
            return float(var_threshold)
        return float(np.mean(below_var))
