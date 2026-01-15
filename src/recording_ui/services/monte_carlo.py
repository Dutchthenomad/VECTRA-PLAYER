"""
Advanced Monte Carlo Bankroll Simulation

Features:
- 10,000 iteration simulations
- Aggressive anti-martingale scaling
- Volatility-based position adjustments
- Bayesian win rate updates with theta acceleration
- Comprehensive risk metrics (VaR, CVaR, Risk of Ruin)
- Drawdown circuit breakers

Based on volatility study findings:
- Baseline return volatility: 0.103
- Optimal zone games are 26% less volatile
- Position sizing inversely proportional to volatility
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

# =============================================================================
# CONSTANTS FROM VOLATILITY STUDY
# =============================================================================

VOLATILITY_BASELINE = 0.102917  # Median return_std from study
VOLATILITY_THRESHOLDS = {
    "very_low": 0.090968,  # 25th percentile -> 1.5x position
    "low": 0.102917,  # 50th percentile -> 1.25x position
    "normal": 0.123005,  # 75th percentile -> 1.0x position
    "high": 0.144899,  # 90th percentile -> 0.75x position
    "very_high": 0.173078,  # 99th percentile -> 0.5x position
}

# Sidebet economics
SIDEBET_PAYOUT = 5.0  # 5:1 payout ratio
BREAKEVEN_WIN_RATE = 1 / (SIDEBET_PAYOUT + 1)  # 16.67%


# =============================================================================
# DATA STRUCTURES
# =============================================================================


class ScalingMode(Enum):
    """Position scaling strategies."""

    FIXED = "fixed"  # Same size every bet
    KELLY = "kelly"  # Kelly criterion
    AGGRESSIVE_KELLY = "aggressive_kelly"  # Full Kelly (risky)
    ANTI_MARTINGALE = "anti_martingale"  # Scale up after wins
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    THETA_BAYESIAN = "theta_bayesian"  # Theta-accelerated Bayesian


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation."""

    # Basic parameters
    initial_bankroll: float = 0.1
    base_bet_size: float = 0.001
    win_rate: float = 0.185  # Empirical optimal zone rate
    num_games: int = 500
    num_iterations: int = 10000

    # Scaling mode
    scaling_mode: ScalingMode = ScalingMode.THETA_BAYESIAN

    # Kelly parameters
    kelly_fraction: float = 0.25  # Quarter Kelly default

    # Anti-martingale parameters
    win_streak_multiplier: float = 1.5
    max_streak_multiplier: float = 3.0

    # Volatility adjustment
    use_volatility_scaling: bool = True

    # Theta Bayesian parameters
    theta_base: float = 1.0  # Base acceleration (increases with confidence)
    theta_max: float = 4.0  # Maximum theta acceleration
    prior_alpha: float = 1.0  # Beta distribution prior (wins)
    prior_beta: float = 1.0  # Beta distribution prior (losses)

    # Drawdown controls
    drawdown_warning: float = 0.05  # 5% - reduce size
    drawdown_caution: float = 0.10  # 10% - half size
    drawdown_halt: float = 0.15  # 15% - stop trading

    # Daily/session limits
    daily_loss_limit: float = 0.03  # 3% max daily loss
    session_loss_limit: float = 0.05  # 5% max session loss

    # Profit targets
    take_profit_target: float | None = None  # e.g., 1.5 for 50% profit

    # Multi-bet (martingale recovery)
    num_bets_per_game: int = 4
    bet_window_ticks: int = 40
    bet_cooldown_ticks: int = 5


@dataclass
class SimulationResult:
    """Results from a single simulation run."""

    final_bankroll: float
    peak_bankroll: float
    max_drawdown: float
    max_drawdown_duration: int  # Games to recover
    total_bets: int
    wins: int
    losses: int
    skips: int
    equity_curve: list[float]
    drawdown_curve: list[float]
    hit_take_profit: bool = False
    hit_drawdown_halt: bool = False
    hit_daily_limit: bool = False
    games_played: int = 0


@dataclass
class MonteCarloResults:
    """Aggregated results from all simulation iterations."""

    config: SimulationConfig
    num_iterations: int

    # Central tendency
    mean_final_bankroll: float
    median_final_bankroll: float
    std_final_bankroll: float

    # Risk metrics
    risk_of_ruin: float  # Probability of losing all capital
    probability_profit: float  # Probability of any profit
    probability_2x: float  # Probability of doubling
    probability_target: float  # Probability of hitting take_profit

    # Drawdown analysis
    mean_max_drawdown: float
    median_max_drawdown: float
    worst_max_drawdown: float
    mean_recovery_time: float

    # VaR and CVaR
    var_95: float  # 95% Value at Risk
    var_99: float  # 99% Value at Risk
    cvar_95: float  # Conditional VaR (Expected Shortfall)

    # Sharpe-like metrics
    expected_return: float
    return_std: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Distribution
    percentiles: dict[str, float]
    final_bankrolls: list[float]  # All outcomes for histogram

    # Equity curves (sample)
    sample_equity_curves: list[list[float]]


# =============================================================================
# BAYESIAN WIN RATE ESTIMATION WITH THETA ACCELERATION
# =============================================================================


class ThetaBayesianEstimator:
    """
    Bayesian win rate estimator with theta acceleration.

    Theta function accelerates learning as confidence grows:
    - Early games: Conservative estimates (theta ≈ 1)
    - More data: Faster convergence to true rate (theta increases)

    Formula: theta = base + (max - base) * (1 - 1/(1 + n/scale))
    Where n = number of observations
    """

    def __init__(
        self,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
        theta_base: float = 1.0,
        theta_max: float = 4.0,
        theta_scale: float = 50.0,
    ):
        self.alpha = prior_alpha
        self.beta = prior_beta
        self.theta_base = theta_base
        self.theta_max = theta_max
        self.theta_scale = theta_scale
        self.observations = 0

    def update(self, win: bool):
        """Update posterior after observing a bet outcome."""
        self.observations += 1
        theta = self._calculate_theta()

        if win:
            self.alpha += theta
        else:
            self.beta += theta

    def _calculate_theta(self) -> float:
        """
        Calculate theta acceleration factor.

        Starts at theta_base, asymptotically approaches theta_max.
        """
        progress = 1 - 1 / (1 + self.observations / self.theta_scale)
        return self.theta_base + (self.theta_max - self.theta_base) * progress

    @property
    def mean(self) -> float:
        """Expected win rate (posterior mean)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Posterior variance."""
        total = self.alpha + self.beta
        return (self.alpha * self.beta) / (total**2 * (total + 1))

    @property
    def std(self) -> float:
        """Posterior standard deviation."""
        return np.sqrt(self.variance)

    def credible_interval(self, confidence: float = 0.95) -> tuple[float, float]:
        """Calculate credible interval for win rate."""
        from scipy.stats import beta

        lower = beta.ppf((1 - confidence) / 2, self.alpha, self.beta)
        upper = beta.ppf(1 - (1 - confidence) / 2, self.alpha, self.beta)
        return (lower, upper)

    def kelly_fraction(self, payout_ratio: float = SIDEBET_PAYOUT) -> float:
        """Calculate Kelly criterion based on current posterior."""
        w = self.mean
        r = payout_ratio
        kelly = w - (1 - w) / r
        return max(0, kelly)

    def reset(self, prior_alpha: float = None, prior_beta: float = None):
        """Reset estimator with optional new priors."""
        self.alpha = prior_alpha if prior_alpha else self.alpha
        self.beta = prior_beta if prior_beta else self.beta
        self.observations = 0


# =============================================================================
# POSITION SIZING ENGINE
# =============================================================================


class PositionSizer:
    """Multi-factor position sizing with all scaling modes."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.bayesian = ThetaBayesianEstimator(
            prior_alpha=config.prior_alpha,
            prior_beta=config.prior_beta,
            theta_base=config.theta_base,
            theta_max=config.theta_max,
        )

    def calculate_size(
        self,
        current_bankroll: float,
        peak_bankroll: float,
        current_volatility: float = VOLATILITY_BASELINE,
    ) -> float:
        """Calculate position size based on all factors."""
        base_size = self.config.base_bet_size

        # 1. Scaling mode base calculation
        if self.config.scaling_mode == ScalingMode.FIXED:
            size = base_size

        elif self.config.scaling_mode == ScalingMode.KELLY:
            kelly_f = self.bayesian.kelly_fraction()
            size = current_bankroll * kelly_f * self.config.kelly_fraction

        elif self.config.scaling_mode == ScalingMode.AGGRESSIVE_KELLY:
            kelly_f = self.bayesian.kelly_fraction()
            size = current_bankroll * kelly_f  # Full Kelly

        elif self.config.scaling_mode == ScalingMode.ANTI_MARTINGALE:
            multiplier = min(
                self.config.win_streak_multiplier**self.consecutive_wins,
                self.config.max_streak_multiplier,
            )
            size = base_size * multiplier

        elif self.config.scaling_mode == ScalingMode.THETA_BAYESIAN:
            # Combine Kelly with anti-martingale and volatility
            kelly_f = self.bayesian.kelly_fraction()
            kelly_size = current_bankroll * kelly_f * self.config.kelly_fraction

            # Anti-martingale boost for winning streaks
            streak_multiplier = min(
                self.config.win_streak_multiplier**self.consecutive_wins,
                self.config.max_streak_multiplier,
            )
            size = max(base_size, kelly_size) * streak_multiplier

        else:  # VOLATILITY_ADJUSTED
            size = base_size

        # 2. Volatility adjustment
        if self.config.use_volatility_scaling and current_volatility > 0:
            vol_multiplier = VOLATILITY_BASELINE / current_volatility
            vol_multiplier = np.clip(vol_multiplier, 0.5, 1.5)
            size *= vol_multiplier

        # 3. Drawdown adjustment
        current_drawdown = (
            (peak_bankroll - current_bankroll) / peak_bankroll if peak_bankroll > 0 else 0
        )

        if current_drawdown > self.config.drawdown_halt:
            return 0.0  # HALT
        elif current_drawdown > self.config.drawdown_caution:
            size *= 0.5
        elif current_drawdown > self.config.drawdown_warning:
            size *= 0.8

        # 4. Ensure we don't bet more than we have
        max_bet = current_bankroll * 0.25  # Never risk more than 25%
        size = min(size, max_bet, current_bankroll)

        return max(0, size)

    def record_outcome(self, won: bool):
        """Record bet outcome for streak tracking and Bayesian update."""
        self.bayesian.update(won)

        if won:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

    def reset(self):
        """Reset for new simulation."""
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.bayesian.reset()


# =============================================================================
# MONTE CARLO SIMULATION ENGINE
# =============================================================================


class MonteCarloSimulator:
    """
    Advanced Monte Carlo simulation for bankroll analysis.

    Runs configurable number of iterations, each simulating a full
    trading session with position sizing, drawdown controls, and
    Bayesian updates.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = np.random.default_rng()

        # Load volatility data if available
        self.volatility_distribution = self._load_volatility_distribution()

    def _load_volatility_distribution(self) -> np.ndarray | None:
        """Load per-game volatility from study."""
        vol_path = Path(
            "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/volatility_metrics.parquet"
        )
        if vol_path.exists():
            import pandas as pd

            df = pd.read_parquet(vol_path)
            # Filter to playable games
            playable = df[df["duration_ticks"] >= 40]
            return playable["return_std"].values
        return None

    def _sample_volatility(self) -> float:
        """Sample a volatility value for current game."""
        if self.volatility_distribution is not None:
            return self.rng.choice(self.volatility_distribution)
        return VOLATILITY_BASELINE

    def _simulate_game(self, win_rate: float) -> bool:
        """Simulate a single game bet outcome."""
        return self.rng.random() < win_rate

    def run_single_simulation(self) -> SimulationResult:
        """Run a single simulation iteration."""
        bankroll = self.config.initial_bankroll
        peak_bankroll = bankroll
        sizer = PositionSizer(self.config)

        equity_curve = [bankroll]
        drawdown_curve = [0.0]

        total_bets = 0
        wins = 0
        losses = 0
        skips = 0
        max_drawdown = 0.0
        max_drawdown_duration = 0
        current_dd_duration = 0

        daily_loss = 0.0
        session_start_bankroll = bankroll

        hit_take_profit = False
        hit_drawdown_halt = False
        hit_daily_limit = False
        games_played = 0

        for game_idx in range(self.config.num_games):
            games_played = game_idx + 1

            # Sample volatility for this game
            game_volatility = self._sample_volatility()

            # Check take profit
            if self.config.take_profit_target:
                if bankroll >= self.config.initial_bankroll * self.config.take_profit_target:
                    hit_take_profit = True
                    break

            # Check drawdown halt
            current_dd = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else 0
            if current_dd > self.config.drawdown_halt:
                hit_drawdown_halt = True
                break

            # Check daily loss limit
            if daily_loss > self.config.initial_bankroll * self.config.daily_loss_limit:
                hit_daily_limit = True
                break

            # Simulate multiple bets per game (martingale sequence)
            game_won = False
            for bet_num in range(self.config.num_bets_per_game):
                bet_size = sizer.calculate_size(bankroll, peak_bankroll, game_volatility)

                if bet_size <= 0 or bankroll <= 0:
                    skips += 1
                    continue

                total_bets += 1
                won = self._simulate_game(self.config.win_rate)

                if won:
                    wins += 1
                    profit = bet_size * SIDEBET_PAYOUT
                    bankroll += profit
                    game_won = True
                    break  # Exit martingale sequence on win
                else:
                    losses += 1
                    bankroll -= bet_size
                    daily_loss += bet_size

                sizer.record_outcome(won)

            # Update peak and drawdown
            if bankroll > peak_bankroll:
                peak_bankroll = bankroll
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_dd_duration)

            current_dd = (peak_bankroll - bankroll) / peak_bankroll if peak_bankroll > 0 else 0
            max_drawdown = max(max_drawdown, current_dd)

            equity_curve.append(bankroll)
            drawdown_curve.append(current_dd)

            # Check for ruin
            if bankroll <= 0:
                break

        return SimulationResult(
            final_bankroll=bankroll,
            peak_bankroll=peak_bankroll,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            total_bets=total_bets,
            wins=wins,
            losses=losses,
            skips=skips,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            hit_take_profit=hit_take_profit,
            hit_drawdown_halt=hit_drawdown_halt,
            hit_daily_limit=hit_daily_limit,
            games_played=games_played,
        )

    def run(self, progress_callback=None) -> MonteCarloResults:
        """Run full Monte Carlo simulation."""
        results: list[SimulationResult] = []

        for i in range(self.config.num_iterations):
            result = self.run_single_simulation()
            results.append(result)

            if progress_callback and i % 1000 == 0:
                progress_callback(i / self.config.num_iterations)

        return self._aggregate_results(results)

    def _aggregate_results(self, results: list[SimulationResult]) -> MonteCarloResults:
        """Aggregate individual simulation results."""
        final_bankrolls = np.array([r.final_bankroll for r in results])
        max_drawdowns = np.array([r.max_drawdown for r in results])
        recovery_times = np.array([r.max_drawdown_duration for r in results])

        # Calculate returns
        returns = (final_bankrolls - self.config.initial_bankroll) / self.config.initial_bankroll

        # Risk of Ruin (bankroll <= 0 or hit halt)
        ruined = np.sum(final_bankrolls <= 0) / len(results)

        # Profit probabilities
        prob_profit = np.mean(final_bankrolls > self.config.initial_bankroll)
        prob_2x = np.mean(final_bankrolls >= self.config.initial_bankroll * 2)

        if self.config.take_profit_target:
            prob_target = np.mean([r.hit_take_profit for r in results])
        else:
            prob_target = 0.0

        # VaR and CVaR
        var_95 = np.percentile(returns, 5)  # 5th percentile = 95% VaR
        var_99 = np.percentile(returns, 1)  # 1st percentile = 99% VaR
        cvar_95 = returns[returns <= var_95].mean() if np.any(returns <= var_95) else var_95

        # Sharpe and related
        expected_return = returns.mean()
        return_std = returns.std()
        sharpe = expected_return / return_std if return_std > 0 else 0

        # Sortino (downside deviation only)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else return_std
        sortino = expected_return / downside_std if downside_std > 0 else 0

        # Calmar
        mean_max_dd = max_drawdowns.mean()
        calmar = expected_return / mean_max_dd if mean_max_dd > 0 else 0

        # Percentiles
        percentiles = {
            "1": float(np.percentile(final_bankrolls, 1)),
            "5": float(np.percentile(final_bankrolls, 5)),
            "10": float(np.percentile(final_bankrolls, 10)),
            "25": float(np.percentile(final_bankrolls, 25)),
            "50": float(np.percentile(final_bankrolls, 50)),
            "75": float(np.percentile(final_bankrolls, 75)),
            "90": float(np.percentile(final_bankrolls, 90)),
            "95": float(np.percentile(final_bankrolls, 95)),
            "99": float(np.percentile(final_bankrolls, 99)),
        }

        # Sample equity curves (10 random)
        sample_indices = self.rng.choice(len(results), min(10, len(results)), replace=False)
        sample_curves = [results[i].equity_curve for i in sample_indices]

        return MonteCarloResults(
            config=self.config,
            num_iterations=self.config.num_iterations,
            mean_final_bankroll=float(final_bankrolls.mean()),
            median_final_bankroll=float(np.median(final_bankrolls)),
            std_final_bankroll=float(final_bankrolls.std()),
            risk_of_ruin=float(ruined),
            probability_profit=float(prob_profit),
            probability_2x=float(prob_2x),
            probability_target=float(prob_target),
            mean_max_drawdown=float(mean_max_dd),
            median_max_drawdown=float(np.median(max_drawdowns)),
            worst_max_drawdown=float(max_drawdowns.max()),
            mean_recovery_time=float(recovery_times.mean()),
            var_95=float(var_95),
            var_99=float(var_99),
            cvar_95=float(cvar_95),
            expected_return=float(expected_return),
            return_std=float(return_std),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            calmar_ratio=float(calmar),
            percentiles=percentiles,
            final_bankrolls=final_bankrolls.tolist(),
            sample_equity_curves=sample_curves,
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def run_aggressive_simulation(
    initial_bankroll: float = 0.1,
    win_rate: float = 0.185,
    num_games: int = 500,
    num_iterations: int = 10000,
) -> MonteCarloResults:
    """
    Run aggressive scaling simulation to find the ceiling.

    Uses:
    - Theta Bayesian updates
    - Anti-martingale scaling
    - Volatility adjustments
    - Aggressive Kelly (0.5x instead of 0.25x)
    """
    config = SimulationConfig(
        initial_bankroll=initial_bankroll,
        base_bet_size=initial_bankroll * 0.01,  # 1% base bet
        win_rate=win_rate,
        num_games=num_games,
        num_iterations=num_iterations,
        scaling_mode=ScalingMode.THETA_BAYESIAN,
        kelly_fraction=0.5,  # Half Kelly (aggressive)
        win_streak_multiplier=1.5,
        max_streak_multiplier=3.0,
        use_volatility_scaling=True,
        theta_base=1.0,
        theta_max=4.0,
        drawdown_warning=0.05,
        drawdown_caution=0.10,
        drawdown_halt=0.20,  # Higher tolerance for aggressive
        take_profit_target=2.0,  # 100% profit target
        num_bets_per_game=4,
    )

    simulator = MonteCarloSimulator(config)
    return simulator.run()


def results_to_dict(results: MonteCarloResults) -> dict:
    """Convert results to JSON-serializable dict."""
    return {
        "config": {
            "initial_bankroll": results.config.initial_bankroll,
            "base_bet_size": results.config.base_bet_size,
            "win_rate": results.config.win_rate,
            "num_games": results.config.num_games,
            "num_iterations": results.config.num_iterations,
            "scaling_mode": results.config.scaling_mode.value,
            "kelly_fraction": results.config.kelly_fraction,
            "take_profit_target": results.config.take_profit_target,
        },
        "summary": {
            "mean_final_bankroll": results.mean_final_bankroll,
            "median_final_bankroll": results.median_final_bankroll,
            "std_final_bankroll": results.std_final_bankroll,
        },
        "risk_metrics": {
            "risk_of_ruin": results.risk_of_ruin,
            "probability_profit": results.probability_profit,
            "probability_2x": results.probability_2x,
            "probability_target": results.probability_target,
        },
        "drawdown": {
            "mean_max_drawdown": results.mean_max_drawdown,
            "median_max_drawdown": results.median_max_drawdown,
            "worst_max_drawdown": results.worst_max_drawdown,
            "mean_recovery_time": results.mean_recovery_time,
        },
        "var_metrics": {
            "var_95": results.var_95,
            "var_99": results.var_99,
            "cvar_95": results.cvar_95,
        },
        "performance": {
            "expected_return": results.expected_return,
            "return_std": results.return_std,
            "sharpe_ratio": results.sharpe_ratio,
            "sortino_ratio": results.sortino_ratio,
            "calmar_ratio": results.calmar_ratio,
        },
        "percentiles": results.percentiles,
    }


# =============================================================================
# MAIN - Run study
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MONTE CARLO BANKROLL SIMULATION - AGGRESSIVE SCALING")
    print("=" * 70)

    print("\nRunning 10,000 iterations with aggressive scaling...")
    print("  - Theta Bayesian updates (theta_max=4.0)")
    print("  - Anti-martingale (1.5x per win, max 3x)")
    print("  - Half Kelly (0.5x)")
    print("  - Volatility-adjusted sizing")
    print("  - 20% drawdown halt")
    print("  - 100% profit target")
    print()

    results = run_aggressive_simulation()

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    print(f"\n--- FINAL BANKROLL (starting at {results.config.initial_bankroll} SOL) ---")
    print(f"  Mean:   {results.mean_final_bankroll:.4f} SOL")
    print(f"  Median: {results.median_final_bankroll:.4f} SOL")
    print(f"  Std:    {results.std_final_bankroll:.4f} SOL")

    print("\n--- RISK METRICS ---")
    print(f"  Risk of Ruin:        {results.risk_of_ruin:.2%}")
    print(f"  Probability Profit:  {results.probability_profit:.2%}")
    print(f"  Probability 2x:      {results.probability_2x:.2%}")
    print(f"  Probability Target:  {results.probability_target:.2%}")

    print("\n--- DRAWDOWN ANALYSIS ---")
    print(f"  Mean Max Drawdown:   {results.mean_max_drawdown:.2%}")
    print(f"  Median Max Drawdown: {results.median_max_drawdown:.2%}")
    print(f"  Worst Max Drawdown:  {results.worst_max_drawdown:.2%}")
    print(f"  Mean Recovery Time:  {results.mean_recovery_time:.1f} games")

    print("\n--- VALUE AT RISK ---")
    print(f"  95% VaR:  {results.var_95:.2%} (5% chance of worse)")
    print(f"  99% VaR:  {results.var_99:.2%} (1% chance of worse)")
    print(f"  95% CVaR: {results.cvar_95:.2%} (expected loss in worst 5%)")

    print("\n--- PERFORMANCE RATIOS ---")
    print(f"  Expected Return: {results.expected_return:.2%}")
    print(f"  Return Std Dev:  {results.return_std:.2%}")
    print(f"  Sharpe Ratio:    {results.sharpe_ratio:.3f}")
    print(f"  Sortino Ratio:   {results.sortino_ratio:.3f}")
    print(f"  Calmar Ratio:    {results.calmar_ratio:.3f}")

    print("\n--- FINAL BANKROLL PERCENTILES ---")
    for p, v in results.percentiles.items():
        print(f"  {p}th: {v:.4f} SOL")

    # Save results
    output_path = Path(
        "/home/devops/Desktop/VECTRA-PLAYER/Machine Learning/models/sidebet-v1/monte_carlo_results.json"
    )
    with open(output_path, "w") as f:
        json.dump(results_to_dict(results), f, indent=2)
    print(f"\n\nResults saved to: {output_path}")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)
