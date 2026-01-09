#!/usr/bin/env python3
"""
Position Sizing Strategies for Sidebet Optimization

Implements and compares multiple position sizing methodologies:
1. Kelly Criterion (full, half, quarter)
2. Fixed fractional betting
3. Anti-martingale / progressive sizing
4. Optimal f calculation
5. Risk-adjusted Kelly with volatility scaling

Key Metrics:
- Expected growth rate
- Variance of returns
- Maximum drawdown
- Ruin probability
- Sharpe ratio

Data: Uses Bayesian win probability estimates from bayesian_sidebet_analysis.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.optimize import minimize_scalar
import sys

# Import Bayesian analysis
sys.path.insert(0, '/home/devops/Desktop/VECTRA-PLAYER/notebooks')
from bayesian_sidebet_analysis import load_game_data, BayesianSurvivalModel

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 6)


# ==============================================================================
# Position Sizing Formulas
# ==============================================================================

def kelly_criterion(p_win: float, payout_multiplier: int = 5, fraction: float = 1.0) -> float:
    """
    Kelly Criterion for optimal bet sizing.
    
    Formula: f* = (p × b - q) / b
    where:
        p = win probability
        q = 1 - p (lose probability)
        b = net payout odds (e.g., 4 for 5x payout)
        fraction = Kelly fraction (1.0 = full Kelly, 0.5 = half Kelly, etc.)
    
    Args:
        p_win: Probability of winning
        payout_multiplier: Payout multiplier (5x, 10x, etc.)
        fraction: Kelly fraction to use (default 1.0 = full Kelly)
    
    Returns:
        Optimal fraction of bankroll to bet (0-1)
    
    Examples:
        >>> kelly_criterion(0.25, 5, 1.0)  # Full Kelly at 25% win rate
        0.0625  # 6.25% of bankroll
        
        >>> kelly_criterion(0.25, 5, 0.5)  # Half Kelly
        0.03125  # 3.125% of bankroll
    """
    b = payout_multiplier - 1  # Net odds (5x payout = 4 net)
    p = p_win
    q = 1 - p
    
    kelly = (p * b - q) / b
    
    # Never bet negative (Kelly says "don't bet")
    kelly = max(0.0, kelly)
    
    return kelly * fraction


def fixed_fractional(bankroll: float, fraction: float = 0.02) -> float:
    """
    Fixed fractional betting - bet constant % of bankroll.
    
    Simple, conservative approach:
    - 1-2%: Very conservative (slow growth, low variance)
    - 3-5%: Moderate (balanced growth/risk)
    - 5-10%: Aggressive (fast growth, high variance)
    
    Args:
        bankroll: Current bankroll
        fraction: Fixed fraction to bet (default 0.02 = 2%)
    
    Returns:
        Bet size
    """
    return bankroll * fraction


def anti_martingale(base_bet: float, consecutive_wins: int, multiplier: float = 1.5) -> float:
    """
    Anti-martingale (reverse martingale) - increase bet after wins.
    
    Bet more when winning, reset to base after loss.
    Capitalizes on winning streaks while limiting downside.
    
    Args:
        base_bet: Base bet amount
        consecutive_wins: Number of consecutive wins
        multiplier: Multiplier per win (default 1.5)
    
    Returns:
        Current bet size
    
    Examples:
        >>> anti_martingale(0.001, 0)  # Start
        0.001
        >>> anti_martingale(0.001, 1)  # After 1 win
        0.0015
        >>> anti_martingale(0.001, 2)  # After 2 wins
        0.00225
    """
    return base_bet * (multiplier ** consecutive_wins)


def optimal_f(trades: List[float]) -> float:
    """
    Optimal f - maximize geometric growth rate.
    
    Ralph Vince's fixed fractional position sizing method.
    Finds the fraction that maximizes Terminal Wealth Relative (TWR).
    
    Formula: TWR = ∏(1 + f × return_i)
    
    Args:
        trades: List of trade returns (as fractions, e.g., 4.0 for 5x win, -1.0 for loss)
    
    Returns:
        Optimal fraction
    
    Reference: "Portfolio Management Formulas" by Ralph Vince
    """
    if not trades or len(trades) == 0:
        return 0.0
    
    # Find largest loss (for normalization)
    largest_loss = abs(min(trades))
    if largest_loss == 0:
        largest_loss = 1.0
    
    # Objective: maximize geometric mean
    def twr(f: float) -> float:
        """Terminal Wealth Relative"""
        if f <= 0:
            return 0.0
        product = 1.0
        for trade in trades:
            hpr = 1 + f * (trade / largest_loss)
            if hpr <= 0:
                return 0.0
            product *= hpr
        return product ** (1.0 / len(trades))
    
    # Maximize TWR by minimizing -TWR
    result = minimize_scalar(lambda f: -twr(f), bounds=(0.0, 1.0), method='bounded')
    
    return result.x if result.success else 0.0


def volatility_adjusted_kelly(p_win: float, 
                               payout_multiplier: int, 
                               volatility: float,
                               base_vol: float = 0.3) -> float:
    """
    Kelly Criterion adjusted for volatility.
    
    Reduces position size when volatility is high (uncertainty).
    
    Formula: f_adjusted = f_kelly × (base_vol / current_vol)
    
    Args:
        p_win: Win probability
        payout_multiplier: Payout multiplier
        volatility: Current win rate volatility (std dev)
        base_vol: Baseline volatility (default 0.3)
    
    Returns:
        Volatility-adjusted Kelly fraction
    """
    kelly = kelly_criterion(p_win, payout_multiplier, fraction=1.0)
    
    if volatility <= 0 or base_vol <= 0:
        return kelly
    
    vol_adjustment = min(1.0, base_vol / volatility)
    
    return kelly * vol_adjustment


# ==============================================================================
# Simulation & Comparison
# ==============================================================================

@dataclass
class PositionSizingResult:
    """Results from position sizing simulation."""
    strategy_name: str
    final_bankroll: float
    total_return: float  # %
    max_drawdown: float  # %
    sharpe_ratio: float
    num_wins: int
    num_losses: int
    win_rate: float  # %
    avg_bet_size: float
    max_bet_size: float
    ruin_occurred: bool  # Did bankroll hit zero?
    bankroll_history: List[float]
    bet_history: List[float]


def simulate_betting_strategy(
    strategy_func,
    win_probabilities: List[float],
    actual_outcomes: List[bool],
    payout_multiplier: int = 5,
    initial_bankroll: float = 1.0,
    ruin_threshold: float = 0.01,
    **strategy_kwargs
) -> PositionSizingResult:
    """
    Simulate a betting strategy over historical outcomes.
    
    Args:
        strategy_func: Function(bankroll, p_win, **kwargs) -> bet_size
        win_probabilities: Predicted win probabilities for each bet
        actual_outcomes: Actual outcomes (True = win, False = loss)
        payout_multiplier: Payout multiplier (5x, 10x, etc.)
        initial_bankroll: Starting bankroll
        ruin_threshold: Bankroll % below which we're "ruined"
        **strategy_kwargs: Additional args for strategy_func
    
    Returns:
        PositionSizingResult with metrics
    """
    bankroll = initial_bankroll
    bankroll_history = [bankroll]
    bet_history = []
    num_wins = 0
    num_losses = 0
    ruin_occurred = False
    
    for p_win, outcome in zip(win_probabilities, actual_outcomes):
        # Determine bet size
        if 'p_win' in strategy_func.__code__.co_varnames:
            bet_size = strategy_func(bankroll=bankroll, p_win=p_win, **strategy_kwargs)
        else:
            bet_size = strategy_func(bankroll=bankroll, **strategy_kwargs)
        
        # Cap bet size at current bankroll
        bet_size = min(bet_size, bankroll)
        bet_history.append(bet_size)
        
        # Execute bet
        if outcome:
            # Win: get back bet + payout
            bankroll += bet_size * (payout_multiplier - 1)
            num_wins += 1
        else:
            # Loss: lose bet
            bankroll -= bet_size
            num_losses += 1
        
        bankroll_history.append(bankroll)
        
        # Check for ruin
        if bankroll <= initial_bankroll * ruin_threshold:
            ruin_occurred = True
            break
    
    # Calculate metrics
    final_bankroll = bankroll
    total_return = ((final_bankroll - initial_bankroll) / initial_bankroll) * 100
    
    # Max drawdown
    peak = initial_bankroll
    max_dd = 0.0
    for b in bankroll_history:
        if b > peak:
            peak = b
        dd = ((peak - b) / peak) * 100
        if dd > max_dd:
            max_dd = dd
    
    # Sharpe ratio (simplified: mean return / std return)
    returns = np.diff(bankroll_history) / bankroll_history[:-1]
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(len(returns))
    else:
        sharpe = 0.0
    
    total_bets = num_wins + num_losses
    win_rate = (num_wins / total_bets * 100) if total_bets > 0 else 0.0
    avg_bet = np.mean(bet_history) if bet_history else 0.0
    max_bet = max(bet_history) if bet_history else 0.0
    
    return PositionSizingResult(
        strategy_name=strategy_kwargs.get('name', 'Unknown'),
        final_bankroll=final_bankroll,
        total_return=total_return,
        max_drawdown=max_dd,
        sharpe_ratio=sharpe,
        num_wins=num_wins,
        num_losses=num_losses,
        win_rate=win_rate,
        avg_bet_size=avg_bet,
        max_bet_size=max_bet,
        ruin_occurred=ruin_occurred,
        bankroll_history=bankroll_history,
        bet_history=bet_history
    )


def compare_strategies(
    win_probabilities: List[float],
    actual_outcomes: List[bool],
    payout_multiplier: int = 5,
    initial_bankroll: float = 1.0
) -> pd.DataFrame:
    """
    Compare multiple position sizing strategies.
    
    Strategies tested:
    1. Full Kelly
    2. Half Kelly
    3. Quarter Kelly
    4. Fixed 2%
    5. Fixed 5%
    6. Volatility-adjusted Kelly
    
    Args:
        win_probabilities: Predicted win probabilities
        actual_outcomes: Actual outcomes
        payout_multiplier: Payout multiplier
        initial_bankroll: Starting bankroll
    
    Returns:
        DataFrame with comparison metrics
    """
    results = []
    
    # 1. Full Kelly
    results.append(simulate_betting_strategy(
        lambda bankroll, p_win: kelly_criterion(p_win, payout_multiplier, 1.0) * bankroll,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Full Kelly'
    ))
    
    # 2. Half Kelly
    results.append(simulate_betting_strategy(
        lambda bankroll, p_win: kelly_criterion(p_win, payout_multiplier, 0.5) * bankroll,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Half Kelly'
    ))
    
    # 3. Quarter Kelly
    results.append(simulate_betting_strategy(
        lambda bankroll, p_win: kelly_criterion(p_win, payout_multiplier, 0.25) * bankroll,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Quarter Kelly'
    ))
    
    # 4. Fixed 2%
    results.append(simulate_betting_strategy(
        lambda bankroll: bankroll * 0.02,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Fixed 2%'
    ))
    
    # 5. Fixed 5%
    results.append(simulate_betting_strategy(
        lambda bankroll: bankroll * 0.05,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Fixed 5%'
    ))
    
    # 6. Volatility-adjusted Kelly (estimate volatility from win prob variance)
    win_prob_vol = np.std(win_probabilities) if len(win_probabilities) > 1 else 0.3
    results.append(simulate_betting_strategy(
        lambda bankroll, p_win: volatility_adjusted_kelly(p_win, payout_multiplier, win_prob_vol) * bankroll,
        win_probabilities, actual_outcomes, payout_multiplier, initial_bankroll,
        name='Vol-Adjusted Kelly'
    ))
    
    # Convert to DataFrame
    df = pd.DataFrame([{
        'Strategy': r.strategy_name,
        'Final Bankroll': r.final_bankroll,
        'Total Return (%)': r.total_return,
        'Max Drawdown (%)': r.max_drawdown,
        'Sharpe Ratio': r.sharpe_ratio,
        'Win Rate (%)': r.win_rate,
        'Avg Bet (% of init)': (r.avg_bet_size / initial_bankroll) * 100,
        'Max Bet (% of init)': (r.max_bet_size / initial_bankroll) * 100,
        'Ruined': r.ruin_occurred
    } for r in results])
    
    return df, results


# ==============================================================================
# Visualization
# ==============================================================================

def plot_strategy_comparison(results: List[PositionSizingResult], 
                              initial_bankroll: float = 1.0):
    """Plot bankroll evolution for all strategies."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # 1. Bankroll evolution
    ax = axes[0, 0]
    for r in results:
        ax.plot(r.bankroll_history, label=r.strategy_name, linewidth=2, alpha=0.8)
    ax.axhline(initial_bankroll, color='black', linestyle='--', alpha=0.5, label='Initial')
    ax.set_xlabel('Bet Number')
    ax.set_ylabel('Bankroll')
    ax.set_title('Bankroll Evolution by Strategy')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # 2. Returns comparison
    ax = axes[0, 1]
    strategies = [r.strategy_name for r in results]
    returns = [r.total_return for r in results]
    colors = ['green' if r > 0 else 'red' for r in returns]
    ax.barh(strategies, returns, color=colors, alpha=0.7)
    ax.axvline(0, color='black', linestyle='-', linewidth=1)
    ax.set_xlabel('Total Return (%)')
    ax.set_title('Final Returns by Strategy')
    ax.grid(True, alpha=0.3, axis='x')
    
    # 3. Risk metrics
    ax = axes[1, 0]
    x = np.arange(len(strategies))
    width = 0.35
    ax.bar(x - width/2, [r.max_drawdown for r in results], width, label='Max Drawdown (%)', alpha=0.7)
    ax.bar(x + width/2, [r.win_rate for r in results], width, label='Win Rate (%)', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.set_ylabel('Percentage')
    ax.set_title('Risk Metrics')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 4. Risk-adjusted returns (Sharpe ratio)
    ax = axes[1, 1]
    sharpe_ratios = [r.sharpe_ratio for r in results]
    colors = ['green' if s > 0 else 'red' for s in sharpe_ratios]
    ax.barh(strategies, sharpe_ratios, color=colors, alpha=0.7)
    ax.axvline(0, color='black', linestyle='-', linewidth=1)
    ax.axvline(1.0, color='orange', linestyle='--', alpha=0.5, label='Good (>1.0)')
    ax.axvline(2.0, color='green', linestyle='--', alpha=0.5, label='Excellent (>2.0)')
    ax.set_xlabel('Sharpe Ratio')
    ax.set_title('Risk-Adjusted Returns (Sharpe Ratio)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    return fig


# ==============================================================================
# Main Analysis
# ==============================================================================

def run_position_sizing_analysis(save_plots: bool = True):
    """Run comprehensive position sizing analysis."""
    print("=" * 70)
    print("POSITION SIZING ANALYSIS")
    print("=" * 70)
    
    # Load data and fit survival model
    print("\n[1/4] Loading data...")
    games_df = load_game_data(min_ticks=10)
    print(f"  Loaded {len(games_df)} games")
    
    print("\n[2/4] Fitting Bayesian survival model...")
    model = BayesianSurvivalModel(games_df)
    
    # Generate test scenarios (simulate 100 bets at various ticks)
    print("\n[3/4] Generating test scenarios...")
    np.random.seed(42)
    
    test_ticks = np.random.choice(range(200, 500), size=100)  # Late-game bets
    win_probabilities = [model.predict_rug_probability(t, window=40) for t in test_ticks]
    
    # Simulate actual outcomes based on probabilities
    actual_outcomes = [np.random.random() < p for p in win_probabilities]
    
    actual_win_rate = sum(actual_outcomes) / len(actual_outcomes)
    print(f"  Simulated {len(actual_outcomes)} bets")
    print(f"  Actual win rate: {actual_win_rate:.1%}")
    print(f"  Avg predicted win prob: {np.mean(win_probabilities):.1%}")
    
    # Compare strategies
    print("\n[4/4] Comparing position sizing strategies...")
    comparison_df, results = compare_strategies(
        win_probabilities, actual_outcomes,
        payout_multiplier=5,
        initial_bankroll=1.0
    )
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(comparison_df.to_string(index=False))
    
    # Plot
    if save_plots:
        fig = plot_strategy_comparison(results, initial_bankroll=1.0)
        output_path = '/home/devops/rugs_data/analysis/position_sizing_comparison.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ Saved plot: {output_path}")
    
    plt.show()
    
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("""
    1. CONSERVATIVE (Low Risk): Quarter Kelly or Fixed 2%
       - Best for: Learning phase, limited bankroll
       - Pros: Low drawdown, steady growth
       - Cons: Slow growth, underutilizes edge
    
    2. BALANCED (Moderate Risk): Half Kelly
       - Best for: Most traders, proven edge
       - Pros: Good growth, acceptable drawdown
       - Cons: Still significant variance
    
    3. AGGRESSIVE (High Risk): Full Kelly or Fixed 5%
       - Best for: High confidence, large bankroll
       - Pros: Maximum growth rate
       - Cons: High drawdown, can be uncomfortable
    
    4. ADAPTIVE: Volatility-Adjusted Kelly
       - Best for: Changing market conditions
       - Pros: Adjusts to uncertainty
       - Cons: More complex implementation
    
    For RL bot implementation: Start with Quarter Kelly, increase to Half Kelly
    after proven profitable performance over 100+ trades.
    """)
    
    return comparison_df, results


if __name__ == "__main__":
    comparison_df, results = run_position_sizing_analysis(save_plots=True)
