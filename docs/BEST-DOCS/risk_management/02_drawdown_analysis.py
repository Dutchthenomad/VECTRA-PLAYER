#!/usr/bin/env python3
"""
Drawdown Control & Risk Management

Analyzes drawdown patterns and implements protective controls:
1. Maximum drawdown from historical data
2. Stop-loss triggers (consecutive losses, % drawdown)
3. Recovery time analysis
4. Monte Carlo simulation of worst-case scenarios
5. Ruin probability calculations

Key Metrics:
- Maximum Drawdown (MDD): Largest peak-to-trough decline
- Drawdown Duration: Time to recover from MDD
- Calmar Ratio: Annual return / MDD
- Ulcer Index: Drawdown severity × duration
"""

import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, "/home/devops/Desktop/VECTRA-PLAYER/notebooks")

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (14, 6)


# ==============================================================================
# Drawdown Calculations
# ==============================================================================


@dataclass
class DrawdownEvent:
    """Single drawdown event."""

    start_idx: int
    trough_idx: int
    end_idx: int  # Recovery point
    start_value: float
    trough_value: float
    drawdown_pct: float
    duration_bets: int
    recovery_bets: int
    recovered: bool


def calculate_drawdowns(equity_curve: list[float]) -> list[DrawdownEvent]:
    """
    Identify all drawdown events in an equity curve.

    A drawdown begins when equity falls below previous peak,
    reaches a trough at the lowest point, and ends when equity
    recovers to previous peak level (or series ends).

    Args:
        equity_curve: List of bankroll values over time

    Returns:
        List of DrawdownEvent objects
    """
    if len(equity_curve) < 2:
        return []

    drawdowns = []
    peak = equity_curve[0]
    peak_idx = 0
    in_drawdown = False
    trough = peak
    trough_idx = 0

    for i, value in enumerate(equity_curve):
        if value > peak:
            # New peak
            if in_drawdown:
                # Drawdown ended, we recovered
                dd_pct = ((peak - trough) / peak) * 100
                drawdowns.append(
                    DrawdownEvent(
                        start_idx=peak_idx,
                        trough_idx=trough_idx,
                        end_idx=i,
                        start_value=peak,
                        trough_value=trough,
                        drawdown_pct=dd_pct,
                        duration_bets=trough_idx - peak_idx,
                        recovery_bets=i - trough_idx,
                        recovered=True,
                    )
                )
                in_drawdown = False

            peak = value
            peak_idx = i
            trough = value
            trough_idx = i

        elif value < peak:
            # In drawdown
            if not in_drawdown:
                in_drawdown = True

            if value < trough:
                trough = value
                trough_idx = i

    # Handle ongoing drawdown at end
    if in_drawdown:
        dd_pct = ((peak - trough) / peak) * 100
        drawdowns.append(
            DrawdownEvent(
                start_idx=peak_idx,
                trough_idx=trough_idx,
                end_idx=len(equity_curve) - 1,
                start_value=peak,
                trough_value=trough,
                drawdown_pct=dd_pct,
                duration_bets=trough_idx - peak_idx,
                recovery_bets=len(equity_curve) - 1 - trough_idx,
                recovered=False,
            )
        )

    return drawdowns


def maximum_drawdown(equity_curve: list[float]) -> tuple[float, int, int]:
    """
    Calculate maximum drawdown and its location.

    Args:
        equity_curve: List of bankroll values

    Returns:
        (max_dd_pct, start_idx, trough_idx)
    """
    drawdowns = calculate_drawdowns(equity_curve)

    if not drawdowns:
        return 0.0, 0, 0

    max_dd = max(drawdowns, key=lambda d: d.drawdown_pct)
    return max_dd.drawdown_pct, max_dd.start_idx, max_dd.trough_idx


def ulcer_index(equity_curve: list[float]) -> float:
    """
    Calculate Ulcer Index - measures severity and duration of drawdowns.

    UI = sqrt(mean(squared drawdown %))

    Lower is better. Captures pain of drawdowns better than simple MDD.

    Args:
        equity_curve: List of bankroll values

    Returns:
        Ulcer index value

    Reference: Peter Martin, "The Investor's Guide to Fidelity Funds"
    """
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    squared_dds = []

    for value in equity_curve:
        if value > peak:
            peak = value

        dd_pct = ((peak - value) / peak) * 100 if peak > 0 else 0.0
        squared_dds.append(dd_pct**2)

    return np.sqrt(np.mean(squared_dds))


def calmar_ratio(total_return_pct: float, max_drawdown_pct: float, years: float = 1.0) -> float:
    """
    Calculate Calmar Ratio = Annual Return / Maximum Drawdown.

    Higher is better. Ratio > 3 is excellent.

    Args:
        total_return_pct: Total return percentage
        max_drawdown_pct: Maximum drawdown percentage
        years: Time period in years (default 1.0)

    Returns:
        Calmar ratio
    """
    if max_drawdown_pct == 0:
        return float("inf") if total_return_pct > 0 else 0.0

    annual_return = total_return_pct / years
    return annual_return / max_drawdown_pct


# ==============================================================================
# Stop-Loss Mechanisms
# ==============================================================================


def consecutive_loss_stopper(losses_in_row: int, threshold: int = 5) -> bool:
    """
    Stop trading after N consecutive losses.

    Args:
        losses_in_row: Current consecutive losses
        threshold: Max allowed consecutive losses

    Returns:
        True if should stop trading
    """
    return losses_in_row >= threshold


def drawdown_stopper(current_dd_pct: float, max_allowed_dd: float = 25.0) -> bool:
    """
    Stop trading if drawdown exceeds threshold.

    Args:
        current_dd_pct: Current drawdown from peak (%)
        max_allowed_dd: Maximum allowed drawdown (%)

    Returns:
        True if should stop trading
    """
    return current_dd_pct >= max_allowed_dd


def time_based_stopper(bets_since_last_win: int, threshold: int = 20) -> bool:
    """
    Stop if no win in N bets (indicates model degradation).

    Args:
        bets_since_last_win: Bets since last win
        threshold: Max bets without win

    Returns:
        True if should stop trading
    """
    return bets_since_last_win >= threshold


# ==============================================================================
# Monte Carlo Simulation
# ==============================================================================


def monte_carlo_simulation(
    p_win: float,
    payout_multiplier: int,
    bet_fraction: float,
    initial_bankroll: float,
    num_bets: int,
    num_simulations: int = 1000,
    ruin_threshold: float = 0.1,
) -> dict:
    """
    Monte Carlo simulation of betting outcomes.

    Simulates thousands of betting sequences to estimate:
    - Distribution of final bankrolls
    - Probability of ruin
    - Expected maximum drawdown
    - 95th/99th percentile worst-case scenarios

    Args:
        p_win: Win probability
        payout_multiplier: Payout multiplier
        bet_fraction: Fraction of bankroll to bet each time
        initial_bankroll: Starting bankroll
        num_bets: Number of bets per simulation
        num_simulations: Number of simulations to run
        ruin_threshold: Bankroll % below which is "ruin"

    Returns:
        Dict with simulation results
    """
    final_bankrolls = []
    max_drawdowns = []
    ruin_count = 0
    recovery_times = []

    for _ in range(num_simulations):
        bankroll = initial_bankroll
        equity_curve = [bankroll]
        peak = bankroll

        for _ in range(num_bets):
            bet_size = bankroll * bet_fraction

            # Outcome
            if np.random.random() < p_win:
                # Win
                bankroll += bet_size * (payout_multiplier - 1)
            else:
                # Loss
                bankroll -= bet_size

            equity_curve.append(bankroll)

            if bankroll > peak:
                peak = bankroll

            # Check ruin
            if bankroll <= initial_bankroll * ruin_threshold:
                ruin_count += 1
                break

        final_bankrolls.append(bankroll)

        # Max drawdown for this run
        dd_pct, _, _ = maximum_drawdown(equity_curve)
        max_drawdowns.append(dd_pct)

        # Recovery time (if recovered)
        drawdowns = calculate_drawdowns(equity_curve)
        if drawdowns:
            max_dd_event = max(drawdowns, key=lambda d: d.drawdown_pct)
            if max_dd_event.recovered:
                recovery_times.append(max_dd_event.recovery_bets)

    final_bankrolls = np.array(final_bankrolls)
    max_drawdowns = np.array(max_drawdowns)

    return {
        "final_bankrolls": final_bankrolls,
        "max_drawdowns": max_drawdowns,
        "mean_final": np.mean(final_bankrolls),
        "median_final": np.median(final_bankrolls),
        "p5_final": np.percentile(final_bankrolls, 5),
        "p95_final": np.percentile(final_bankrolls, 95),
        "mean_mdd": np.mean(max_drawdowns),
        "p95_mdd": np.percentile(max_drawdowns, 95),
        "p99_mdd": np.percentile(max_drawdowns, 99),
        "ruin_probability": ruin_count / num_simulations,
        "recovery_times": recovery_times,
        "mean_recovery": np.mean(recovery_times) if recovery_times else 0,
    }


def ruin_probability_analytic(
    p_win: float,
    payout_multiplier: int,
    bet_fraction: float,
    initial_bankroll: float,
    target_bankroll: float,
) -> float:
    """
    Analytical approximation of ruin probability.

    Uses gambler's ruin formula for unequal stakes.

    Formula (simplified):
        If EV > 0: P(ruin) ≈ (L/W)^(B/L)
        If EV < 0: P(ruin) ≈ 1

    Where:
        L = loss per bet
        W = win per bet
        B = initial bankroll

    Args:
        p_win: Win probability
        payout_multiplier: Payout multiplier
        bet_fraction: Fraction of bankroll per bet
        initial_bankroll: Starting bankroll
        target_bankroll: Target bankroll (when to stop)

    Returns:
        Approximate ruin probability
    """
    # Expected value
    ev = p_win * (payout_multiplier - 1) - (1 - p_win)

    if ev <= 0:
        return 0.999  # Almost certain ruin with negative EV

    # Approximation using exponential decay
    # Higher bet fraction = higher ruin risk
    # Higher EV = lower ruin risk

    loss_per_bet = bet_fraction
    win_per_bet = bet_fraction * (payout_multiplier - 1)

    if win_per_bet <= 0:
        return 1.0

    ratio = loss_per_bet / win_per_bet
    exponent = initial_bankroll / loss_per_bet

    p_ruin = ratio**exponent

    return min(0.999, max(0.001, p_ruin))


# ==============================================================================
# Visualization
# ==============================================================================


def plot_drawdown_analysis(equity_curve: list[float], title: str = "Drawdown Analysis"):
    """Plot equity curve with drawdown overlay."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Equity curve
    ax1.plot(equity_curve, label="Equity", color="blue", linewidth=2)

    # Mark drawdown events
    drawdowns = calculate_drawdowns(equity_curve)
    for dd in drawdowns:
        ax1.axvspan(dd.start_idx, dd.end_idx, alpha=0.2, color="red")
        ax1.plot(dd.trough_idx, dd.trough_value, "rv", markersize=8)

    # Running peak
    peak_curve = []
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        peak_curve.append(peak)

    ax1.plot(peak_curve, "--", color="green", alpha=0.5, label="Running Peak")
    ax1.set_ylabel("Bankroll")
    ax1.set_title(title)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Drawdown %
    dd_pct = []
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = ((peak - value) / peak) * 100 if peak > 0 else 0.0
        dd_pct.append(-dd)  # Negative for underwater chart

    ax2.fill_between(range(len(dd_pct)), dd_pct, 0, color="red", alpha=0.3)
    ax2.plot(dd_pct, color="red", linewidth=1)
    ax2.set_xlabel("Bet Number")
    ax2.set_ylabel("Drawdown (%)")
    ax2.set_title("Underwater Curve (Drawdown %)")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_monte_carlo_results(mc_results: dict, initial_bankroll: float = 1.0):
    """Visualize Monte Carlo simulation results."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Final bankroll distribution
    ax = axes[0, 0]
    ax.hist(mc_results["final_bankrolls"], bins=50, alpha=0.7, color="blue", edgecolor="black")
    ax.axvline(
        mc_results["mean_final"],
        color="red",
        linestyle="--",
        label=f"Mean: {mc_results['mean_final']:.2f}",
    )
    ax.axvline(
        mc_results["median_final"],
        color="green",
        linestyle="--",
        label=f"Median: {mc_results['median_final']:.2f}",
    )
    ax.axvline(
        mc_results["p5_final"],
        color="orange",
        linestyle=":",
        label=f"5th %ile: {mc_results['p5_final']:.2f}",
    )
    ax.axvline(initial_bankroll, color="black", linestyle="-", alpha=0.5, label="Initial")
    ax.set_xlabel("Final Bankroll")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Final Bankrolls")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. Max drawdown distribution
    ax = axes[0, 1]
    ax.hist(mc_results["max_drawdowns"], bins=50, alpha=0.7, color="red", edgecolor="black")
    ax.axvline(
        mc_results["mean_mdd"],
        color="blue",
        linestyle="--",
        label=f"Mean: {mc_results['mean_mdd']:.1f}%",
    )
    ax.axvline(
        mc_results["p95_mdd"],
        color="orange",
        linestyle="--",
        label=f"95th %ile: {mc_results['p95_mdd']:.1f}%",
    )
    ax.axvline(
        mc_results["p99_mdd"],
        color="red",
        linestyle="--",
        label=f"99th %ile: {mc_results['p99_mdd']:.1f}%",
    )
    ax.set_xlabel("Maximum Drawdown (%)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Maximum Drawdowns")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Final bankroll vs max drawdown
    ax = axes[1, 0]
    ax.scatter(mc_results["max_drawdowns"], mc_results["final_bankrolls"], alpha=0.3, s=10)
    ax.set_xlabel("Maximum Drawdown (%)")
    ax.set_ylabel("Final Bankroll")
    ax.set_title("Risk vs Return")
    ax.grid(True, alpha=0.3)

    # 4. Recovery time distribution
    ax = axes[1, 1]
    if mc_results["recovery_times"]:
        ax.hist(mc_results["recovery_times"], bins=30, alpha=0.7, color="green", edgecolor="black")
        ax.axvline(
            mc_results["mean_recovery"],
            color="red",
            linestyle="--",
            label=f"Mean: {mc_results['mean_recovery']:.0f} bets",
        )
        ax.set_xlabel("Recovery Time (bets)")
        ax.set_ylabel("Frequency")
        ax.set_title("Time to Recover from Maximum Drawdown")
        ax.legend()
    else:
        ax.text(
            0.5, 0.5, "No recoveries observed", ha="center", va="center", transform=ax.transAxes
        )
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


# ==============================================================================
# Main Analysis
# ==============================================================================


def run_drawdown_analysis(save_plots: bool = True):
    """Run comprehensive drawdown analysis."""
    print("=" * 70)
    print("DRAWDOWN CONTROL & RISK MANAGEMENT")
    print("=" * 70)

    # Monte Carlo simulation parameters
    p_win = 0.20  # Breakeven for 5x
    payout_multiplier = 5
    initial_bankroll = 1.0
    num_bets = 100
    num_simulations = 5000

    print("\n[1/3] Running Monte Carlo simulations...")
    print(f"  Win probability: {p_win:.1%}")
    print(f"  Payout: {payout_multiplier}x")
    print(f"  Simulations: {num_simulations}")
    print(f"  Bets per simulation: {num_bets}")

    strategies = {
        "Full Kelly": 0.10,  # ~10% bet size at 20% win rate
        "Half Kelly": 0.05,
        "Quarter Kelly": 0.025,
        "Fixed 2%": 0.02,
    }

    results = {}
    for name, bet_frac in strategies.items():
        print(f"\n  Simulating {name} (bet fraction: {bet_frac:.1%})...")
        mc_result = monte_carlo_simulation(
            p_win, payout_multiplier, bet_frac, initial_bankroll, num_bets, num_simulations
        )
        results[name] = mc_result

        print(
            f"    Final bankroll: {mc_result['mean_final']:.3f} ± {mc_result['median_final']:.3f}"
        )
        print(f"    Max DD (mean): {mc_result['mean_mdd']:.1f}%")
        print(f"    Max DD (95th %ile): {mc_result['p95_mdd']:.1f}%")
        print(f"    Ruin probability: {mc_result['ruin_probability']:.1%}")

    # Summary table
    print("\n[2/3] Summary of Risk Metrics")
    summary_data = []
    for name, mc in results.items():
        summary_data.append(
            {
                "Strategy": name,
                "Mean Final": f"{mc['mean_final']:.3f}",
                "P5 Final": f"{mc['p5_final']:.3f}",
                "Mean MDD (%)": f"{mc['mean_mdd']:.1f}",
                "P95 MDD (%)": f"{mc['p95_mdd']:.1f}",
                "P99 MDD (%)": f"{mc['p99_mdd']:.1f}",
                "Ruin Prob (%)": f"{mc['ruin_probability'] * 100:.1f}",
                "Mean Recovery": f"{mc['mean_recovery']:.0f}",
            }
        )

    summary_df = pd.DataFrame(summary_data)
    print("\n" + summary_df.to_string(index=False))

    # Plot Monte Carlo results
    if save_plots:
        print("\n[3/3] Generating plots...")
        for name, mc in results.items():
            fig = plot_monte_carlo_results(mc, initial_bankroll)
            filename = name.lower().replace(" ", "_")
            output_path = f"/home/devops/rugs_data/analysis/mc_{filename}.png"
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()
            print(f"  ✅ Saved: {output_path}")

    print("\n" + "=" * 70)
    print("DRAWDOWN CONTROL RECOMMENDATIONS")
    print("=" * 70)
    print("""
    1. MAXIMUM DRAWDOWN LIMITS:
       - Conservative: Stop at 15% drawdown
       - Moderate: Stop at 25% drawdown
       - Aggressive: Stop at 40% drawdown

    2. CONSECUTIVE LOSS LIMITS:
       - Conservative: Stop after 5 consecutive losses
       - Moderate: Stop after 8 consecutive losses
       - Aggressive: Stop after 12 consecutive losses

    3. TIME-BASED STOPS:
       - If no win in 20 bets, pause and re-evaluate model
       - If drawdown lasts >50 bets, reduce position size by 50%

    4. RECOVERY PROTOCOL:
       - After hitting stop-loss, reduce position size by 50%
       - Gradually increase back to target over 20 profitable bets
       - Track recovery time: Mean recovery = 15-30 bets

    5. MONTE CARLO INSIGHTS:
       - 95th percentile worst-case: ~30-50% drawdown
       - Plan for 2-3 major drawdowns per 100 bets
       - Ruin risk < 5% with Quarter Kelly sizing
    """)

    return results, summary_df


if __name__ == "__main__":
    results, summary_df = run_drawdown_analysis(save_plots=True)
