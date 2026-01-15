"""
Position Sizing & Bankroll Management Service.

Implements position sizing strategies for sidebet multi-bet sequences.
Supports Kelly Criterion, fixed fractional, and progressive (martingale) sizing.

Key Concepts (from RISK_MANAGEMENT_SOURCES.md):
- Kelly Criterion: K% = W - (1-W)/R for optimal growth
- Fractional Kelly: Use 0.25-0.5x Kelly for reduced volatility
- Drawdown Control: Reduce size when in drawdown
- Risk of Ruin: Monte Carlo simulation for ruin probability

SOL Units:
- All amounts in SOL (Solana native token)
- Default wallet: 0.1 SOL
- Default bet: 0.001 SOL
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd

# Constants
SIDEBET_WINDOW = 40
SIDEBET_COOLDOWN = 5
SIDEBET_PAYOUT = 5  # 5:1


class SizingStrategy(Enum):
    """Position sizing strategies."""

    FIXED = "fixed"  # Same size for all bets
    PROGRESSIVE = "progressive"  # Increase each bet (martingale-lite)
    KELLY = "kelly"  # Kelly criterion based
    DRAWDOWN_ADJUSTED = "drawdown_adjusted"  # Reduce on drawdown


@dataclass
class BetConfig:
    """Configuration for a single bet in the sequence."""

    size: float  # SOL amount
    enabled: bool = True


@dataclass
class WalletConfig:
    """Wallet and position sizing configuration."""

    initial_balance: float = 0.1  # Starting SOL

    # Bet sizes for each position (up to 4 bets)
    bet_sizes: list[float] = field(default_factory=lambda: [0.001, 0.001, 0.001, 0.001])

    # Entry tick
    entry_tick: int = 200

    # Risk controls
    max_drawdown_pct: float = 0.50  # 50% max drawdown = wallet halved = failure
    daily_loss_limit: float = 0.10  # 10% daily loss limit

    # Position sizing strategy
    strategy: SizingStrategy = SizingStrategy.FIXED

    # Advanced: Dynamic sizing based on probability
    use_dynamic_sizing: bool = False
    high_confidence_threshold: float = 0.60  # 60%+ = high confidence
    high_confidence_multiplier: float = 2.0  # 2x bet on high confidence

    # Take-profit target (wallet growth goal)
    take_profit_target: float | None = None  # e.g., 1.5 = stop at 150% of initial

    # Drawdown-adjusted sizing
    reduce_on_drawdown: bool = False
    drawdown_reduction_start: float = 0.05  # Start reducing at 5% drawdown

    # Kelly-based sizing that scales with current balance
    use_kelly_sizing: bool = False  # Recalculate bet sizes based on current balance
    kelly_fraction: float = 0.25  # Use 25% of full Kelly (conservative)

    def total_risk_per_game(self) -> float:
        """Maximum loss if all bets lose."""
        return sum(self.bet_sizes)

    def risk_pct_per_game(self) -> float:
        """Risk as percentage of initial balance."""
        return self.total_risk_per_game() / self.initial_balance * 100


@dataclass
class GameResult:
    """Result of a single game simulation."""

    game_id: str
    duration: int
    entry_tick: int

    # Betting outcome
    bets_placed: int
    winning_bet: int | None  # 1-4 or None
    outcome: str  # "win", "loss", "early_rug", "skipped"

    # Financials (SOL)
    total_wagered: float
    payout: float
    profit: float

    # Wallet state after game
    balance_before: float
    balance_after: float

    # Risk metrics
    drawdown: float  # Current drawdown from peak
    peak_balance: float


@dataclass
class SimulationResult:
    """Complete simulation result across all games."""

    config: WalletConfig
    games: list[GameResult]

    # Summary stats
    total_games: int
    games_played: int  # Excluding early rugs and skips
    wins: int
    losses: int
    early_rugs: int
    skipped: int  # Due to risk limits

    # Financial summary
    starting_balance: float
    ending_balance: float
    total_profit: float
    total_wagered: float
    roi_pct: float

    # Risk metrics
    max_drawdown_pct: float
    max_drawdown_sol: float
    sharpe_ratio: float
    win_rate: float

    # Equity curve data (for charting)
    equity_curve: list[float]
    drawdown_curve: list[float]


def calculate_bet_windows(entry_tick: int, num_bets: int = 4) -> list[dict]:
    """Calculate bet windows for multi-bet strategy."""
    windows = []
    current_tick = entry_tick

    for i in range(num_bets):
        windows.append(
            {
                "bet_num": i + 1,
                "start_tick": current_tick,
                "end_tick": current_tick + SIDEBET_WINDOW - 1,
            }
        )
        current_tick = current_tick + SIDEBET_WINDOW + SIDEBET_COOLDOWN

    return windows


def estimate_win_probability(games_df: pd.DataFrame, entry_tick: int, num_bets: int = 4) -> float:
    """
    Estimate win probability for a given entry tick and number of bets.

    Based on historical game data - what % of games that reach entry_tick
    will rug within the betting windows?
    """
    windows = calculate_bet_windows(entry_tick, num_bets)
    final_end = windows[-1]["end_tick"]

    # Games that reach the entry tick
    playable = games_df[games_df["duration_ticks"] >= entry_tick]
    if len(playable) == 0:
        return 0.0

    # Games that rug within any window
    wins = 0
    for _, row in playable.iterrows():
        duration = int(row["duration_ticks"])
        for window in windows:
            if window["start_tick"] <= duration <= window["end_tick"]:
                wins += 1
                break

    return wins / len(playable)


def calculate_dynamic_bet_size(
    base_size: float,
    win_probability: float,
    current_drawdown: float,
    balance: float,
    config: "WalletConfig",
) -> float:
    """
    Calculate dynamic bet size based on probability and drawdown.

    Strategy:
    1. If probability > threshold, multiply bet size
    2. If in drawdown, reduce bet size proportionally
    3. Cap at maximum safe bet (respecting max drawdown limit)

    Args:
        base_size: Base bet size in SOL
        win_probability: Estimated probability of winning (0-1)
        current_drawdown: Current drawdown as fraction (0-1)
        balance: Current wallet balance
        config: Wallet configuration

    Returns:
        Adjusted bet size in SOL
    """
    adjusted_size = base_size

    # 1. High confidence multiplier
    if config.use_dynamic_sizing and win_probability >= config.high_confidence_threshold:
        # Scale multiplier based on how much above threshold
        excess_prob = win_probability - config.high_confidence_threshold
        # Linear scale: at threshold = 1x, at 80% = full multiplier
        scale = 1 + (excess_prob / 0.20) * (config.high_confidence_multiplier - 1)
        scale = min(scale, config.high_confidence_multiplier)
        adjusted_size *= scale

    # 2. Drawdown reduction
    if config.reduce_on_drawdown and current_drawdown > config.drawdown_reduction_start:
        # Linear reduction from start to max drawdown
        reduction_range = config.max_drawdown_pct - config.drawdown_reduction_start
        if reduction_range > 0:
            reduction_factor = (
                current_drawdown - config.drawdown_reduction_start
            ) / reduction_range
            reduction_factor = min(reduction_factor, 0.9)  # Never reduce more than 90%
            adjusted_size *= 1 - reduction_factor

    # 3. Cap at safe maximum (no single bet should exceed remaining drawdown budget)
    max_safe_bet = balance * (config.max_drawdown_pct - current_drawdown)
    adjusted_size = min(adjusted_size, max_safe_bet * 0.25)  # 25% of remaining budget per bet

    # Ensure minimum bet
    adjusted_size = max(0.0001, adjusted_size)

    return round(adjusted_size, 6)


def optimal_kelly_for_probability(
    win_probability: float, max_drawdown: float = 0.15, kelly_fraction: float = 0.25
) -> float:
    """
    Calculate optimal Kelly fraction constrained by max drawdown.

    For high probability bets, Kelly suggests larger bets, but we cap
    based on max acceptable drawdown.
    """
    # Full Kelly
    kelly = kelly_criterion(win_probability)

    if kelly <= 0:
        return 0.0

    # Fractional Kelly
    safe_kelly = kelly * kelly_fraction

    # Cap based on max drawdown (4 bets means max 4x single bet loss)
    max_per_bet = max_drawdown / 4

    return min(safe_kelly, max_per_bet)


def kelly_criterion(win_rate: float, payout_ratio: float = SIDEBET_PAYOUT) -> float:
    """
    Calculate Kelly Criterion fraction.

    K% = W - (1-W)/R
    where W = win rate, R = win/loss ratio (payout)

    Returns fraction of bankroll to bet.
    """
    if payout_ratio <= 0:
        return 0.0

    kelly = win_rate - (1 - win_rate) / payout_ratio
    return max(0.0, kelly)


def fractional_kelly(
    win_rate: float, payout_ratio: float = SIDEBET_PAYOUT, fraction: float = 0.25
) -> float:
    """
    Calculate fractional Kelly for reduced volatility.

    Standard practice: use 0.25-0.5x Kelly.
    """
    return kelly_criterion(win_rate, payout_ratio) * fraction


def calculate_progressive_sizes(
    base_size: float, num_bets: int = 4, multiplier: float = 2.0
) -> list[float]:
    """
    Calculate progressive bet sizes (martingale-style).

    Args:
        base_size: First bet size in SOL
        num_bets: Number of bets
        multiplier: Size increase factor (default 2x = classic martingale)

    Returns:
        List of bet sizes
    """
    sizes = []
    current = base_size
    for _ in range(num_bets):
        sizes.append(round(current, 6))
        current *= multiplier
    return sizes


def simulate_game(
    duration: int, entry_tick: int, bet_sizes: list[float], balance: float, peak_balance: float
) -> tuple[str, int, int | None, float, float, float]:
    """
    Simulate a single game with position sizing.

    Returns:
        outcome, bets_placed, winning_bet, total_wagered, payout, new_balance
    """
    windows = calculate_bet_windows(entry_tick, len(bet_sizes))

    # Early rug - game ended before entry
    if duration < entry_tick:
        return "early_rug", 0, None, 0.0, 0.0, balance

    # Simulate betting through windows
    total_wagered = 0.0
    bets_placed = 0
    winning_bet = None

    for i, (window, bet_size) in enumerate(zip(windows, bet_sizes)):
        # Can we place this bet? (game still running)
        if duration >= window["start_tick"]:
            # Check if we can afford the bet
            if balance >= bet_size:
                bets_placed += 1
                total_wagered += bet_size
                balance -= bet_size

                # Did we win? (game rugged in this window)
                if duration <= window["end_tick"]:
                    winning_bet = i + 1
                    payout = bet_size * SIDEBET_PAYOUT
                    balance += payout
                    return "win", bets_placed, winning_bet, total_wagered, payout, balance
            else:
                # Can't afford bet - stop
                break

    # If we get here, we lost all bets or couldn't afford more
    if bets_placed > 0:
        return "loss", bets_placed, None, total_wagered, 0.0, balance
    else:
        return "skipped", 0, None, 0.0, 0.0, balance


def run_simulation(
    games_df: pd.DataFrame, config: WalletConfig, estimate_probability: bool = True
) -> SimulationResult:
    """
    Run full bankroll simulation across all games.

    Args:
        games_df: DataFrame with game_id, duration_ticks columns
        config: Wallet and position sizing configuration
        estimate_probability: If True, pre-calculate win probability for dynamic sizing

    Returns:
        SimulationResult with full analysis
    """
    balance = config.initial_balance
    peak_balance = balance

    game_results = []
    equity_curve = [balance]
    drawdown_curve = [0.0]

    wins = 0
    losses = 0
    early_rugs = 0
    skipped = 0
    total_wagered = 0.0
    take_profit_reached = False
    max_drawdown_reached = False

    # Track metrics for exit analysis
    games_before_exit = 0  # Games played before take-profit or max-drawdown
    max_drawdown_before_exit = 0.0  # Max drawdown during active play
    exit_triggered_at_game = None  # Game index when exit was triggered

    # Pre-calculate win probability for dynamic sizing
    win_probability = 0.0
    if (config.use_dynamic_sizing or config.use_kelly_sizing) and estimate_probability:
        win_probability = estimate_win_probability(
            games_df, config.entry_tick, len(config.bet_sizes)
        )

    for _, row in games_df.iterrows():
        duration = int(row["duration_ticks"])
        game_id = row["game_id"]

        balance_before = balance

        # Check take-profit target
        if config.take_profit_target is not None:
            target_balance = config.initial_balance * config.take_profit_target
            if balance >= target_balance:
                if not take_profit_reached:
                    take_profit_reached = True
                    exit_triggered_at_game = len(
                        [g for g in game_results if g.outcome in ("win", "loss")]
                    )
                # Skip remaining games - goal achieved
                game_results.append(
                    GameResult(
                        game_id=game_id,
                        duration=duration,
                        entry_tick=config.entry_tick,
                        bets_placed=0,
                        winning_bet=None,
                        outcome="take_profit",
                        total_wagered=0.0,
                        payout=0.0,
                        profit=0.0,
                        balance_before=balance_before,
                        balance_after=balance,
                        drawdown=0.0,
                        peak_balance=peak_balance,
                    )
                )
                skipped += 1
                equity_curve.append(balance)
                drawdown_curve.append(0.0)
                continue

        # Check risk limits
        current_drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
        if current_drawdown >= config.max_drawdown_pct:
            if not max_drawdown_reached:
                max_drawdown_reached = True
                exit_triggered_at_game = len(
                    [g for g in game_results if g.outcome in ("win", "loss")]
                )
            # Skip due to risk limits
            game_results.append(
                GameResult(
                    game_id=game_id,
                    duration=duration,
                    entry_tick=config.entry_tick,
                    bets_placed=0,
                    winning_bet=None,
                    outcome="max_drawdown",
                    total_wagered=0.0,
                    payout=0.0,
                    profit=0.0,
                    balance_before=balance_before,
                    balance_after=balance,
                    drawdown=current_drawdown,
                    peak_balance=peak_balance,
                )
            )
            skipped += 1
            equity_curve.append(balance)
            drawdown_curve.append(current_drawdown)
            continue

        # Track max drawdown during active play (before any exit)
        if not take_profit_reached and not max_drawdown_reached:
            max_drawdown_before_exit = max(max_drawdown_before_exit, current_drawdown)

        # Calculate bet sizes based on strategy
        if config.use_kelly_sizing and win_probability > 0.20:
            # Kelly-based sizing: recalculate bet sizes based on current balance
            kelly_full = kelly_criterion(win_probability)
            kelly_adjusted = kelly_full * config.kelly_fraction

            # Total Kelly bet per sequence, distributed across 4 bets
            total_kelly_bet = balance * kelly_adjusted
            per_bet = max(0.0001, total_kelly_bet / len(config.bet_sizes))

            bet_sizes = [round(per_bet, 6)] * len(config.bet_sizes)

            # Apply dynamic adjustments on top of Kelly
            if config.use_dynamic_sizing:
                adjusted_sizes = []
                for base_size in bet_sizes:
                    adjusted = calculate_dynamic_bet_size(
                        base_size=base_size,
                        win_probability=win_probability,
                        current_drawdown=current_drawdown,
                        balance=balance,
                        config=config,
                    )
                    adjusted_sizes.append(adjusted)
                bet_sizes = adjusted_sizes

        elif config.use_dynamic_sizing:
            # Dynamic sizing only (no Kelly-based scaling)
            dynamic_sizes = []
            for base_size in config.bet_sizes:
                adjusted = calculate_dynamic_bet_size(
                    base_size=base_size,
                    win_probability=win_probability,
                    current_drawdown=current_drawdown,
                    balance=balance,
                    config=config,
                )
                dynamic_sizes.append(adjusted)
            bet_sizes = dynamic_sizes
        else:
            # Fixed bet sizes
            bet_sizes = config.bet_sizes

        # Simulate the game
        outcome, bets_placed, winning_bet, wagered, payout, new_balance = simulate_game(
            duration=duration,
            entry_tick=config.entry_tick,
            bet_sizes=bet_sizes,
            balance=balance,
            peak_balance=peak_balance,
        )

        balance = new_balance
        profit = balance - balance_before
        total_wagered += wagered

        # Update peak
        if balance > peak_balance:
            peak_balance = balance

        # Calculate drawdown
        current_drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0

        # Track outcomes
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        elif outcome == "early_rug":
            early_rugs += 1
        else:
            skipped += 1

        game_results.append(
            GameResult(
                game_id=game_id,
                duration=duration,
                entry_tick=config.entry_tick,
                bets_placed=bets_placed,
                winning_bet=winning_bet,
                outcome=outcome,
                total_wagered=wagered,
                payout=payout,
                profit=profit,
                balance_before=balance_before,
                balance_after=balance,
                drawdown=current_drawdown,
                peak_balance=peak_balance,
            )
        )

        equity_curve.append(balance)
        drawdown_curve.append(current_drawdown)

    # Calculate summary metrics
    total_games = len(games_df)
    games_played = wins + losses
    total_profit = balance - config.initial_balance
    roi_pct = (total_profit / config.initial_balance * 100) if config.initial_balance > 0 else 0
    win_rate = wins / games_played if games_played > 0 else 0

    # Max drawdown
    max_dd_pct = max(drawdown_curve) if drawdown_curve else 0
    max_dd_sol = max_dd_pct * peak_balance

    # Sharpe ratio (simplified - using game returns)
    if len(game_results) > 1:
        returns = [g.profit for g in game_results if g.outcome in ("win", "loss")]
        if returns and np.std(returns) > 0:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(len(returns))
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0

    return SimulationResult(
        config=config,
        games=game_results,
        total_games=total_games,
        games_played=games_played,
        wins=wins,
        losses=losses,
        early_rugs=early_rugs,
        skipped=skipped,
        starting_balance=config.initial_balance,
        ending_balance=balance,
        total_profit=total_profit,
        total_wagered=total_wagered,
        roi_pct=roi_pct,
        max_drawdown_pct=max_dd_pct * 100,
        max_drawdown_sol=max_dd_sol,
        sharpe_ratio=sharpe,
        win_rate=win_rate * 100,
        equity_curve=equity_curve,
        drawdown_curve=[d * 100 for d in drawdown_curve],  # Convert to %
    )


def suggest_kelly_sizing(
    win_rate: float, initial_balance: float = 0.1, num_bets: int = 4, kelly_fraction: float = 0.25
) -> list[float]:
    """
    Suggest bet sizes based on Kelly Criterion.

    Uses fractional Kelly for safety.
    """
    kelly = fractional_kelly(win_rate / 100, SIDEBET_PAYOUT, kelly_fraction)

    if kelly <= 0:
        # Negative Kelly = don't bet
        return [0.001] * num_bets

    # Total risk per sequence
    total_risk = initial_balance * kelly

    # Distribute across bets (equal for now)
    per_bet = total_risk / num_bets

    # Ensure minimum bet
    per_bet = max(0.001, round(per_bet, 4))

    return [per_bet] * num_bets


def simulation_to_dict(result: SimulationResult) -> dict[str, Any]:
    """Convert SimulationResult to JSON-serializable dict."""
    # Count special outcomes
    take_profit_games = sum(1 for g in result.games if g.outcome == "take_profit")
    max_dd_games = sum(1 for g in result.games if g.outcome == "max_drawdown")

    # Calculate games played before exit (wins + losses before any exit outcome)
    games_before_exit = 0
    max_drawdown_during_play = 0.0
    peak_during_play = result.starting_balance
    for g in result.games:
        if g.outcome in ("take_profit", "max_drawdown"):
            break
        if g.outcome in ("win", "loss"):
            games_before_exit += 1
            # Track drawdown during active play
            if g.balance_after > peak_during_play:
                peak_during_play = g.balance_after
            dd = (
                (peak_during_play - g.balance_after) / peak_during_play
                if peak_during_play > 0
                else 0
            )
            max_drawdown_during_play = max(max_drawdown_during_play, dd)

    # Build exit analysis section
    exit_analysis = {
        "games_to_exit": games_before_exit,
        "max_drawdown_during_play": round(max_drawdown_during_play * 100, 2),
        "take_profit_reached": take_profit_games > 0,
        "max_drawdown_reached": max_dd_games > 0,
    }

    # Add exit-specific details
    if take_profit_games > 0:
        exit_analysis["exit_type"] = "take_profit"
        exit_analysis["target_reached"] = result.config.take_profit_target
        # Find the balance when target was reached
        for g in result.games:
            if g.outcome == "take_profit":
                exit_analysis["balance_at_exit"] = round(g.balance_before, 6)
                break
    elif max_dd_games > 0:
        exit_analysis["exit_type"] = "max_drawdown"
        exit_analysis["drawdown_limit"] = result.config.max_drawdown_pct * 100

    return {
        "config": {
            "initial_balance": result.config.initial_balance,
            "bet_sizes": result.config.bet_sizes,
            "entry_tick": result.config.entry_tick,
            "total_risk_per_game": result.config.total_risk_per_game(),
            "risk_pct_per_game": round(result.config.risk_pct_per_game(), 2),
            "max_drawdown_pct": result.config.max_drawdown_pct * 100,
            # Dynamic sizing config
            "use_dynamic_sizing": result.config.use_dynamic_sizing,
            "use_kelly_sizing": result.config.use_kelly_sizing,
            "kelly_fraction": result.config.kelly_fraction,
            "high_confidence_threshold": result.config.high_confidence_threshold * 100,
            "high_confidence_multiplier": result.config.high_confidence_multiplier,
            "take_profit_target": result.config.take_profit_target,
            "reduce_on_drawdown": result.config.reduce_on_drawdown,
        },
        "summary": {
            "total_games": result.total_games,
            "games_played": result.games_played,
            "wins": result.wins,
            "losses": result.losses,
            "early_rugs": result.early_rugs,
            "skipped": result.skipped,
            "take_profit_exits": take_profit_games,
            "max_drawdown_exits": max_dd_games,
            "win_rate": round(result.win_rate, 1),
        },
        "financials": {
            "starting_balance": result.starting_balance,
            "ending_balance": round(result.ending_balance, 6),
            "total_profit": round(result.total_profit, 6),
            "total_wagered": round(result.total_wagered, 6),
            "roi_pct": round(result.roi_pct, 2),
        },
        "risk_metrics": {
            "max_drawdown_pct": round(result.max_drawdown_pct, 2),
            "max_drawdown_sol": round(result.max_drawdown_sol, 6),
            "sharpe_ratio": round(result.sharpe_ratio, 3),
            "take_profit_reached": take_profit_games > 0,
            "max_drawdown_reached": max_dd_games > 0,
        },
        "exit_analysis": exit_analysis,
        "curves": {
            "equity": [round(e, 6) for e in result.equity_curve],
            "drawdown": [round(d, 2) for d in result.drawdown_curve],
        },
        "kelly_suggestion": {
            "win_rate_used": round(result.win_rate, 1),
            "kelly_fraction": round(kelly_criterion(result.win_rate / 100), 4),
            "quarter_kelly": round(fractional_kelly(result.win_rate / 100), 4),
            "suggested_bet": round(
                result.starting_balance * fractional_kelly(result.win_rate / 100) / 4, 4
            ),
        },
    }
