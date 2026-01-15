#!/usr/bin/env python3
"""
Risk Metrics Dashboard

Comprehensive risk-adjusted performance metrics:
1. Sharpe Ratio - Risk-adjusted returns
2. Sortino Ratio - Downside deviation only
3. Calmar Ratio - Return / max drawdown
4. Value at Risk (VaR) at 95%, 99%
5. Expected Shortfall (CVaR) - Tail risk
6. Win/loss streak analysis
7. Profit Factor - Gross profit / gross loss

Provides a complete risk profile for sidebet strategy evaluation.
"""

import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sys.path.insert(0, "/home/devops/Desktop/VECTRA-PLAYER/notebooks")

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (14, 6)


# ==============================================================================
# Risk-Adjusted Performance Metrics
# ==============================================================================


def sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
    """
    Sharpe Ratio = (Mean Return - Risk-Free Rate) / Std Dev of Returns

    Measures excess return per unit of total risk (volatility).

    Interpretation:
    - < 1.0: Poor
    - 1.0-2.0: Good
    - > 2.0: Excellent
    - > 3.0: Exceptional

    Args:
        returns: Array of returns (can be % or absolute)
        risk_free_rate: Risk-free rate (default 0 for crypto)

    Returns:
        Sharpe ratio
    """
    if len(returns) == 0:
        return 0.0

    excess_returns = returns - risk_free_rate

    if np.std(returns) == 0:
        return 0.0

    return np.mean(excess_returns) / np.std(returns)


def sortino_ratio(returns: np.ndarray, target_return: float = 0.0) -> float:
    """
    Sortino Ratio = (Mean Return - Target) / Downside Deviation

    Like Sharpe, but only penalizes downside volatility.
    More appropriate for asymmetric return distributions.

    Args:
        returns: Array of returns
        target_return: Minimum acceptable return (default 0)

    Returns:
        Sortino ratio
    """
    if len(returns) == 0:
        return 0.0

    excess_returns = returns - target_return

    # Downside deviation (only negative returns)
    downside_returns = returns[returns < target_return]

    if len(downside_returns) == 0:
        return float("inf") if np.mean(excess_returns) > 0 else 0.0

    downside_std = np.std(downside_returns)

    if downside_std == 0:
        return 0.0

    return np.mean(excess_returns) / downside_std


def calmar_ratio(total_return_pct: float, max_drawdown_pct: float, years: float = 1.0) -> float:
    """
    Calmar Ratio = Annual Return / Maximum Drawdown

    Measures return per unit of maximum risk.

    Interpretation:
    - < 1.0: Poor (not compensated for drawdown risk)
    - 1.0-3.0: Good
    - > 3.0: Excellent

    Args:
        total_return_pct: Total return percentage
        max_drawdown_pct: Maximum drawdown percentage
        years: Time period in years

    Returns:
        Calmar ratio
    """
    if max_drawdown_pct == 0:
        return float("inf") if total_return_pct > 0 else 0.0

    annual_return = total_return_pct / years
    return annual_return / max_drawdown_pct


def value_at_risk(returns: np.ndarray, confidence: float = 0.95) -> float:
    """
    Value at Risk (VaR) - Maximum expected loss at given confidence level.

    VaR(95%) = "95% of the time, losses won't exceed this amount"

    Args:
        returns: Array of returns
        confidence: Confidence level (0.95 = 95%)

    Returns:
        VaR as a positive number (loss magnitude)

    Examples:
        >>> returns = np.array([0.05, -0.02, 0.03, -0.10, 0.01])
        >>> var_95 = value_at_risk(returns, 0.95)
        # "95% of the time, losses won't exceed var_95"
    """
    if len(returns) == 0:
        return 0.0

    return -np.percentile(returns, (1 - confidence) * 100)


def expected_shortfall(returns: np.ndarray, confidence: float = 0.95) -> float:
    """
    Expected Shortfall (CVaR, Conditional VaR) - Expected loss beyond VaR.

    CVaR(95%) = "When VaR is exceeded, average loss is CVaR"

    More conservative than VaR, captures tail risk better.

    Args:
        returns: Array of returns
        confidence: Confidence level

    Returns:
        Expected shortfall as positive number
    """
    if len(returns) == 0:
        return 0.0

    var = value_at_risk(returns, confidence)

    # Average of all returns worse than VaR
    tail_losses = returns[returns < -var]

    if len(tail_losses) == 0:
        return var

    return -np.mean(tail_losses)


def profit_factor(wins: list[float], losses: list[float]) -> float:
    """
    Profit Factor = Gross Profit / Gross Loss

    Measures total winning vs total losing.

    Interpretation:
    - < 1.0: Losing system
    - 1.0-1.5: Marginal
    - 1.5-2.0: Good
    - > 2.0: Excellent

    Args:
        wins: List of winning trade P&Ls (positive)
        losses: List of losing trade P&Ls (negative)

    Returns:
        Profit factor
    """
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0

    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def expectancy(wins: list[float], losses: list[float], num_wins: int, num_losses: int) -> float:
    """
    Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)

    Average profit/loss per trade.

    Args:
        wins: List of winning trade P&Ls
        losses: List of losing trade P&Ls
        num_wins: Number of wins
        num_losses: Number of losses

    Returns:
        Expected P&L per trade
    """
    total_trades = num_wins + num_losses

    if total_trades == 0:
        return 0.0

    win_rate = num_wins / total_trades
    loss_rate = num_losses / total_trades

    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = abs(np.mean(losses)) if losses else 0.0

    return (win_rate * avg_win) - (loss_rate * avg_loss)


# ==============================================================================
# Streak Analysis
# ==============================================================================


@dataclass
class StreakAnalysis:
    """Win/loss streak statistics."""

    longest_win_streak: int
    longest_loss_streak: int
    avg_win_streak: float
    avg_loss_streak: float
    current_streak: int  # Current streak (+ = wins, - = losses)
    streak_distribution: dict[str, list[int]]  # Histogram of streaks


def analyze_streaks(outcomes: list[bool]) -> StreakAnalysis:
    """
    Analyze win/loss streaks.

    Args:
        outcomes: List of outcomes (True = win, False = loss)

    Returns:
        StreakAnalysis object
    """
    if not outcomes:
        return StreakAnalysis(0, 0, 0.0, 0.0, 0, {"wins": [], "losses": []})

    win_streaks = []
    loss_streaks = []

    current_streak = 1
    current_type = outcomes[0]

    for outcome in outcomes[1:]:
        if outcome == current_type:
            current_streak += 1
        else:
            # Streak ended
            if current_type:
                win_streaks.append(current_streak)
            else:
                loss_streaks.append(current_streak)

            current_streak = 1
            current_type = outcome

    # Add final streak
    if current_type:
        win_streaks.append(current_streak)
    else:
        loss_streaks.append(current_streak)

    return StreakAnalysis(
        longest_win_streak=max(win_streaks) if win_streaks else 0,
        longest_loss_streak=max(loss_streaks) if loss_streaks else 0,
        avg_win_streak=np.mean(win_streaks) if win_streaks else 0.0,
        avg_loss_streak=np.mean(loss_streaks) if loss_streaks else 0.0,
        current_streak=current_streak if current_type else -current_streak,
        streak_distribution={"wins": win_streaks, "losses": loss_streaks},
    )


# ==============================================================================
# Comprehensive Dashboard
# ==============================================================================


@dataclass
class RiskMetricsDashboard:
    """Complete risk metrics profile."""

    # Performance
    total_return_pct: float
    total_trades: int
    win_rate_pct: float

    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Risk measures
    max_drawdown_pct: float
    var_95: float
    var_99: float
    cvar_95: float
    cvar_99: float

    # Trade quality
    profit_factor: float
    expectancy: float
    avg_win: float
    avg_loss: float

    # Streaks
    longest_win_streak: int
    longest_loss_streak: int
    avg_win_streak: float
    avg_loss_streak: float


def calculate_risk_dashboard(
    equity_curve: list[float],
    trade_returns: list[float],
    outcomes: list[bool],
    initial_bankroll: float = 1.0,
) -> RiskMetricsDashboard:
    """
    Calculate comprehensive risk metrics dashboard.

    Args:
        equity_curve: Bankroll over time
        trade_returns: Returns per trade (as fractions)
        outcomes: Win/loss outcomes
        initial_bankroll: Starting bankroll

    Returns:
        RiskMetricsDashboard
    """
    # Performance
    final_bankroll = equity_curve[-1] if equity_curve else initial_bankroll
    total_return_pct = ((final_bankroll - initial_bankroll) / initial_bankroll) * 100

    total_trades = len(outcomes)
    num_wins = sum(outcomes)
    num_losses = total_trades - num_wins
    win_rate_pct = (num_wins / total_trades * 100) if total_trades > 0 else 0.0

    # Risk-adjusted returns
    returns_array = np.array(trade_returns)
    sharpe = sharpe_ratio(returns_array)
    sortino = sortino_ratio(returns_array)

    # Max drawdown
    from risk_management.drawdown_analysis import maximum_drawdown

    max_dd_pct, _, _ = maximum_drawdown(equity_curve)

    calmar = calmar_ratio(total_return_pct, max_dd_pct) if max_dd_pct > 0 else 0.0

    # VaR and CVaR
    var95 = value_at_risk(returns_array, 0.95)
    var99 = value_at_risk(returns_array, 0.99)
    cvar95 = expected_shortfall(returns_array, 0.95)
    cvar99 = expected_shortfall(returns_array, 0.99)

    # Trade quality
    wins = [r for r in trade_returns if r > 0]
    losses = [r for r in trade_returns if r < 0]

    pf = profit_factor(wins, losses)
    exp = expectancy(wins, losses, num_wins, num_losses)
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0

    # Streaks
    streak_analysis = analyze_streaks(outcomes)

    return RiskMetricsDashboard(
        total_return_pct=total_return_pct,
        total_trades=total_trades,
        win_rate_pct=win_rate_pct,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        max_drawdown_pct=max_dd_pct,
        var_95=var95 * 100,  # Convert to %
        var_99=var99 * 100,
        cvar_95=cvar95 * 100,
        cvar_99=cvar99 * 100,
        profit_factor=pf,
        expectancy=exp,
        avg_win=avg_win,
        avg_loss=avg_loss,
        longest_win_streak=streak_analysis.longest_win_streak,
        longest_loss_streak=streak_analysis.longest_loss_streak,
        avg_win_streak=streak_analysis.avg_win_streak,
        avg_loss_streak=streak_analysis.avg_loss_streak,
    )


def print_risk_dashboard(dashboard: RiskMetricsDashboard):
    """Pretty-print risk metrics dashboard."""
    print("=" * 70)
    print("RISK METRICS DASHBOARD")
    print("=" * 70)

    print("\n📊 PERFORMANCE SUMMARY")
    print(f"  Total Return:      {dashboard.total_return_pct:>8.2f}%")
    print(f"  Total Trades:      {dashboard.total_trades:>8}")
    print(f"  Win Rate:          {dashboard.win_rate_pct:>8.1f}%")

    print("\n📈 RISK-ADJUSTED RETURNS")
    print(
        f"  Sharpe Ratio:      {dashboard.sharpe_ratio:>8.2f}  {'✅' if dashboard.sharpe_ratio > 1.0 else '⚠️'}"
    )
    print(
        f"  Sortino Ratio:     {dashboard.sortino_ratio:>8.2f}  {'✅' if dashboard.sortino_ratio > 1.5 else '⚠️'}"
    )
    print(
        f"  Calmar Ratio:      {dashboard.calmar_ratio:>8.2f}  {'✅' if dashboard.calmar_ratio > 1.0 else '⚠️'}"
    )

    print("\n⚠️  RISK MEASURES")
    print(f"  Max Drawdown:      {dashboard.max_drawdown_pct:>8.1f}%")
    print(f"  VaR (95%):         {dashboard.var_95:>8.1f}%")
    print(f"  VaR (99%):         {dashboard.var_99:>8.1f}%")
    print(f"  CVaR (95%):        {dashboard.cvar_95:>8.1f}%")
    print(f"  CVaR (99%):        {dashboard.cvar_99:>8.1f}%")

    print("\n💰 TRADE QUALITY")
    print(
        f"  Profit Factor:     {dashboard.profit_factor:>8.2f}  {'✅' if dashboard.profit_factor > 1.5 else '⚠️'}"
    )
    print(f"  Expectancy:        {dashboard.expectancy:>8.4f}")
    print(f"  Avg Win:           {dashboard.avg_win:>8.4f}")
    print(f"  Avg Loss:          {dashboard.avg_loss:>8.4f}")

    print("\n🎲 WIN/LOSS STREAKS")
    print(f"  Longest Win:       {dashboard.longest_win_streak:>8}")
    print(f"  Longest Loss:      {dashboard.longest_loss_streak:>8}")
    print(f"  Avg Win Streak:    {dashboard.avg_win_streak:>8.1f}")
    print(f"  Avg Loss Streak:   {dashboard.avg_loss_streak:>8.1f}")

    print("\n" + "=" * 70)


def plot_risk_dashboard(dashboard: RiskMetricsDashboard, equity_curve: list[float]):
    """Visualize risk metrics dashboard."""
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. Equity curve
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(equity_curve, linewidth=2, color="blue")
    ax1.set_title("Equity Curve", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Trade #")
    ax1.set_ylabel("Bankroll")
    ax1.grid(True, alpha=0.3)

    # 2. Risk-adjusted returns (bar chart)
    ax2 = fig.add_subplot(gs[1, 0])
    metrics = ["Sharpe", "Sortino", "Calmar"]
    values = [dashboard.sharpe_ratio, dashboard.sortino_ratio, dashboard.calmar_ratio]
    colors = ["green" if v > 1.0 else "orange" if v > 0 else "red" for v in values]
    ax2.bar(metrics, values, color=colors, alpha=0.7)
    ax2.axhline(1.0, color="black", linestyle="--", alpha=0.5, label="Good (>1.0)")
    ax2.set_title("Risk-Adjusted Returns")
    ax2.set_ylabel("Ratio")
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")

    # 3. VaR comparison
    ax3 = fig.add_subplot(gs[1, 1])
    var_metrics = ["VaR\n95%", "VaR\n99%", "CVaR\n95%", "CVaR\n99%"]
    var_values = [dashboard.var_95, dashboard.var_99, dashboard.cvar_95, dashboard.cvar_99]
    ax3.barh(var_metrics, var_values, color="red", alpha=0.7)
    ax3.set_title("Value at Risk & CVaR")
    ax3.set_xlabel("Loss (%)")
    ax3.invert_xaxis()
    ax3.grid(True, alpha=0.3, axis="x")

    # 4. Trade quality
    ax4 = fig.add_subplot(gs[1, 2])
    quality_text = f"""
    Profit Factor: {dashboard.profit_factor:.2f}
    Expectancy: {dashboard.expectancy:.4f}

    Avg Win: {dashboard.avg_win:.4f}
    Avg Loss: {dashboard.avg_loss:.4f}

    Win Rate: {dashboard.win_rate_pct:.1f}%
    Total Trades: {dashboard.total_trades}
    """
    ax4.text(
        0.1,
        0.5,
        quality_text,
        fontsize=11,
        family="monospace",
        verticalalignment="center",
        transform=ax4.transAxes,
    )
    ax4.axis("off")
    ax4.set_title("Trade Quality")

    # 5. Streak distribution (wins)
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.text(
        0.5,
        0.5,
        f"Longest Win Streak:\n{dashboard.longest_win_streak} trades\n\n"
        f"Avg Win Streak:\n{dashboard.avg_win_streak:.1f} trades",
        fontsize=12,
        ha="center",
        va="center",
        transform=ax5.transAxes,
        bbox={"boxstyle": "round", "facecolor": "green", "alpha": 0.3},
    )
    ax5.axis("off")
    ax5.set_title("Win Streaks")

    # 6. Streak distribution (losses)
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.text(
        0.5,
        0.5,
        f"Longest Loss Streak:\n{dashboard.longest_loss_streak} trades\n\n"
        f"Avg Loss Streak:\n{dashboard.avg_loss_streak:.1f} trades",
        fontsize=12,
        ha="center",
        va="center",
        transform=ax6.transAxes,
        bbox={"boxstyle": "round", "facecolor": "red", "alpha": 0.3},
    )
    ax6.axis("off")
    ax6.set_title("Loss Streaks")

    # 7. Summary scorecard
    ax7 = fig.add_subplot(gs[2, 2])
    grade_text = f"""
    📊 OVERALL GRADE

    Sharpe > 1.0:    {"✅" if dashboard.sharpe_ratio > 1.0 else "❌"}
    Sortino > 1.5:   {"✅" if dashboard.sortino_ratio > 1.5 else "❌"}
    PF > 1.5:        {"✅" if dashboard.profit_factor > 1.5 else "❌"}
    MDD < 30%:       {"✅" if dashboard.max_drawdown_pct < 30 else "❌"}
    Positive EV:     {"✅" if dashboard.expectancy > 0 else "❌"}
    """
    ax7.text(
        0.1,
        0.5,
        grade_text,
        fontsize=11,
        family="monospace",
        verticalalignment="center",
        transform=ax7.transAxes,
    )
    ax7.axis("off")

    plt.suptitle("Risk Metrics Dashboard", fontsize=16, fontweight="bold")

    return fig


# ==============================================================================
# Main Analysis
# ==============================================================================


def run_risk_metrics_analysis(save_plots: bool = True):
    """Run comprehensive risk metrics analysis."""
    print("Running risk metrics analysis...")

    # Simulate a trading sequence
    np.random.seed(42)

    # Parameters
    p_win = 0.20
    payout_multiplier = 5
    bet_fraction = 0.025  # Quarter Kelly
    initial_bankroll = 1.0
    num_trades = 200

    # Simulate
    bankroll = initial_bankroll
    equity_curve = [bankroll]
    trade_returns = []
    outcomes = []

    for _ in range(num_trades):
        bet_size = bankroll * bet_fraction

        if np.random.random() < p_win:
            # Win
            ret = bet_size * (payout_multiplier - 1) / bankroll
            bankroll += bet_size * (payout_multiplier - 1)
            outcomes.append(True)
        else:
            # Loss
            ret = -bet_size / bankroll
            bankroll -= bet_size
            outcomes.append(False)

        equity_curve.append(bankroll)
        trade_returns.append(ret)

    # Calculate dashboard
    dashboard = calculate_risk_dashboard(equity_curve, trade_returns, outcomes, initial_bankroll)

    # Print
    print_risk_dashboard(dashboard)

    # Plot
    if save_plots:
        fig = plot_risk_dashboard(dashboard, equity_curve)
        output_path = "/home/devops/rugs_data/analysis/risk_metrics_dashboard.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"\n✅ Saved: {output_path}")
        plt.close()

    return dashboard


if __name__ == "__main__":
    dashboard = run_risk_metrics_analysis(save_plots=True)
