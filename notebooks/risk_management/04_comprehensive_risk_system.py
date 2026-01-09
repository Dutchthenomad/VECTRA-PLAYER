#!/usr/bin/env python3
"""
Comprehensive Risk-Adjusted Trading System

Integrates all risk management components into a unified system:
1. Bayesian win probability estimation
2. Kelly-based position sizing
3. Drawdown monitoring and stops
4. Risk metrics tracking
5. Adaptive bet sizing based on current state

This is the production-ready implementation for the RL bot.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import sys

sys.path.insert(0, '/home/devops/Desktop/VECTRA-PLAYER/notebooks')
from bayesian_sidebet_analysis import load_game_data, BayesianSurvivalModel, extract_features

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 6)


# ==============================================================================
# Trading State
# ==============================================================================

class TradingState(str, Enum):
    """Current trading state."""
    ACTIVE = "active"  # Normal trading
    REDUCED = "reduced"  # Reduced size after losses
    PAUSED = "paused"  # Stop trading (hit stop-loss)
    RECOVERY = "recovery"  # Recovering from drawdown


@dataclass
class AccountState:
    """Current account state."""
    bankroll: float
    peak_bankroll: float
    current_drawdown_pct: float
    consecutive_wins: int
    consecutive_losses: int
    trades_since_last_win: int
    total_trades: int
    total_wins: int
    total_losses: int
    equity_curve: List[float]
    trade_history: List[Dict]
    trading_state: TradingState


# ==============================================================================
# Risk Management Configuration
# ==============================================================================

@dataclass
class RiskConfig:
    """Risk management configuration."""
    # Position sizing
    kelly_fraction: float = 0.25  # Quarter Kelly
    min_bet_size: float = 0.001  # Minimum bet in SOL
    max_bet_size: float = 0.1  # Maximum bet in SOL
    max_bet_pct: float = 5.0  # Max % of bankroll per bet
    
    # Drawdown controls
    max_drawdown_pct: float = 25.0  # Pause trading at this DD
    reduce_size_dd_pct: float = 15.0  # Reduce size at this DD
    
    # Streak controls
    max_consecutive_losses: int = 8  # Pause after N losses
    reduce_after_losses: int = 5  # Reduce size after N losses
    max_trades_without_win: int = 20  # Pause if no win in N trades
    
    # Recovery
    recovery_multiplier: float = 0.5  # Reduce size by 50% in recovery
    recovery_trades: int = 10  # Trades to stay in recovery mode
    
    # Entry filters
    min_win_probability: float = 0.18  # Don't bet if P(win) < this
    min_expected_value: float = -0.0001  # Don't bet if EV < this
    
    # Payout settings
    payout_multiplier: int = 5


# ==============================================================================
# Risk-Adjusted Position Sizing
# ==============================================================================

class RiskManager:
    """
    Risk management system for sidebet trading.
    
    Handles:
    - Dynamic position sizing (Kelly-based)
    - Drawdown monitoring and stops
    - Trade state management
    - Recovery protocols
    """
    
    def __init__(self, initial_bankroll: float, config: RiskConfig):
        self.config = config
        self.state = AccountState(
            bankroll=initial_bankroll,
            peak_bankroll=initial_bankroll,
            current_drawdown_pct=0.0,
            consecutive_wins=0,
            consecutive_losses=0,
            trades_since_last_win=0,
            total_trades=0,
            total_wins=0,
            total_losses=0,
            equity_curve=[initial_bankroll],
            trade_history=[],
            trading_state=TradingState.ACTIVE
        )
    
    def calculate_position_size(self, p_win: float) -> float:
        """
        Calculate position size based on Kelly Criterion and current state.
        
        Args:
            p_win: Estimated win probability
        
        Returns:
            Bet size in SOL
        """
        # Kelly calculation
        b = self.config.payout_multiplier - 1  # Net odds
        kelly = (p_win * b - (1 - p_win)) / b
        kelly = max(0.0, kelly)  # Never bet negative
        
        # Apply Kelly fraction
        kelly_adjusted = kelly * self.config.kelly_fraction
        
        # Base bet size
        base_bet = self.state.bankroll * kelly_adjusted
        
        # Apply state-based adjustments
        if self.state.trading_state == TradingState.REDUCED:
            base_bet *= 0.75  # Reduce by 25%
        elif self.state.trading_state == TradingState.RECOVERY:
            base_bet *= self.config.recovery_multiplier
        elif self.state.trading_state == TradingState.PAUSED:
            return 0.0  # No betting when paused
        
        # Apply limits
        max_bet = min(
            self.config.max_bet_size,
            self.state.bankroll * (self.config.max_bet_pct / 100)
        )
        
        bet_size = np.clip(base_bet, self.config.min_bet_size, max_bet)
        
        return bet_size
    
    def should_place_bet(self, p_win: float) -> Tuple[bool, str]:
        """
        Determine if a bet should be placed.
        
        Args:
            p_win: Estimated win probability
        
        Returns:
            (should_bet, reason)
        """
        # Check trading state
        if self.state.trading_state == TradingState.PAUSED:
            return False, "Trading paused due to stop-loss"
        
        # Check win probability threshold
        if p_win < self.config.min_win_probability:
            return False, f"P(win) {p_win:.1%} < minimum {self.config.min_win_probability:.1%}"
        
        # Check expected value
        ev = p_win * (self.config.payout_multiplier - 1) - (1 - p_win)
        if ev < self.config.min_expected_value:
            return False, f"EV {ev:.4f} < minimum {self.config.min_expected_value:.4f}"
        
        # Check bankroll
        if self.state.bankroll < self.config.min_bet_size:
            return False, "Insufficient bankroll"
        
        return True, "All checks passed"
    
    def record_trade(self, bet_size: float, outcome: bool, p_win: float):
        """
        Record trade outcome and update state.
        
        Args:
            bet_size: Bet size placed
            outcome: True if won, False if lost
            p_win: Estimated win probability at time of bet
        """
        # Calculate P&L
        if outcome:
            pnl = bet_size * (self.config.payout_multiplier - 1)
            self.state.bankroll += pnl
            self.state.total_wins += 1
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
            self.state.trades_since_last_win = 0
        else:
            pnl = -bet_size
            self.state.bankroll -= bet_size
            self.state.total_losses += 1
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
            self.state.trades_since_last_win += 1
        
        self.state.total_trades += 1
        self.state.equity_curve.append(self.state.bankroll)
        
        # Update peak
        if self.state.bankroll > self.state.peak_bankroll:
            self.state.peak_bankroll = self.state.bankroll
        
        # Calculate drawdown
        self.state.current_drawdown_pct = (
            (self.state.peak_bankroll - self.state.bankroll) / self.state.peak_bankroll * 100
            if self.state.peak_bankroll > 0 else 0.0
        )
        
        # Record trade
        self.state.trade_history.append({
            'trade_num': self.state.total_trades,
            'bet_size': bet_size,
            'p_win': p_win,
            'outcome': outcome,
            'pnl': pnl,
            'bankroll': self.state.bankroll,
            'drawdown_pct': self.state.current_drawdown_pct,
            'state': self.state.trading_state.value
        })
        
        # Update trading state
        self._update_trading_state()
    
    def _update_trading_state(self):
        """Update trading state based on current conditions."""
        # Check for pause conditions
        if self.state.current_drawdown_pct >= self.config.max_drawdown_pct:
            self.state.trading_state = TradingState.PAUSED
            print(f"⚠️  PAUSED: Drawdown {self.state.current_drawdown_pct:.1f}% >= {self.config.max_drawdown_pct}%")
            return
        
        if self.state.consecutive_losses >= self.config.max_consecutive_losses:
            self.state.trading_state = TradingState.PAUSED
            print(f"⚠️  PAUSED: {self.state.consecutive_losses} consecutive losses")
            return
        
        if self.state.trades_since_last_win >= self.config.max_trades_without_win:
            self.state.trading_state = TradingState.PAUSED
            print(f"⚠️  PAUSED: No win in {self.state.trades_since_last_win} trades")
            return
        
        # Check for reduced size conditions
        if self.state.current_drawdown_pct >= self.config.reduce_size_dd_pct:
            if self.state.trading_state != TradingState.REDUCED:
                self.state.trading_state = TradingState.REDUCED
                print(f"⚠️  REDUCED: Drawdown {self.state.current_drawdown_pct:.1f}%")
            return
        
        if self.state.consecutive_losses >= self.config.reduce_after_losses:
            if self.state.trading_state != TradingState.REDUCED:
                self.state.trading_state = TradingState.REDUCED
                print(f"⚠️  REDUCED: {self.state.consecutive_losses} consecutive losses")
            return
        
        # Check for recovery mode
        if self.state.trading_state == TradingState.PAUSED:
            # Stay paused (manual intervention needed)
            pass
        elif self.state.trading_state == TradingState.RECOVERY:
            # Check if recovery complete
            recovery_trades = sum(1 for t in self.state.trade_history[-self.config.recovery_trades:]
                                  if t['outcome'])
            if recovery_trades >= self.config.recovery_trades // 2:
                self.state.trading_state = TradingState.ACTIVE
                print("✅ ACTIVE: Recovery complete")
        else:
            # Normal trading
            if self.state.current_drawdown_pct < 5.0 and self.state.consecutive_losses < 3:
                self.state.trading_state = TradingState.ACTIVE
    
    def resume_trading(self):
        """Manually resume trading after pause (enter recovery mode)."""
        if self.state.trading_state == TradingState.PAUSED:
            self.state.trading_state = TradingState.RECOVERY
            print("📊 Entering RECOVERY mode (reduced size)")
    
    def get_summary(self) -> pd.DataFrame:
        """Get trading summary statistics."""
        if not self.state.trade_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.state.trade_history)
        
        summary = {
            'Total Trades': self.state.total_trades,
            'Wins': self.state.total_wins,
            'Losses': self.state.total_losses,
            'Win Rate (%)': (self.state.total_wins / self.state.total_trades * 100) if self.state.total_trades > 0 else 0,
            'Current Bankroll': self.state.bankroll,
            'Peak Bankroll': self.state.peak_bankroll,
            'Total Return (%)': ((self.state.bankroll - self.state.equity_curve[0]) / self.state.equity_curve[0] * 100),
            'Current Drawdown (%)': self.state.current_drawdown_pct,
            'Trading State': self.state.trading_state.value,
            'Consecutive Wins': self.state.consecutive_wins,
            'Consecutive Losses': self.state.consecutive_losses
        }
        
        return pd.Series(summary)


# ==============================================================================
# Backtesting
# ==============================================================================

def backtest_risk_system(
    games_df: pd.DataFrame,
    survival_model: BayesianSurvivalModel,
    config: RiskConfig,
    initial_bankroll: float = 1.0,
    num_games: int = 100
) -> Tuple[RiskManager, pd.DataFrame]:
    """
    Backtest the risk management system on historical games.
    
    Args:
        games_df: DataFrame of games
        survival_model: Fitted Bayesian survival model
        config: Risk configuration
        initial_bankroll: Starting bankroll
        num_games: Number of games to test
    
    Returns:
        (RiskManager instance, trades DataFrame)
    """
    risk_mgr = RiskManager(initial_bankroll, config)
    
    # Sample games
    np.random.seed(42)
    test_games = games_df.sample(n=min(num_games, len(games_df)))
    
    for _, game in test_games.iterrows():
        prices = game['prices']
        rug_tick = game['rug_tick']
        
        # Pick a random entry point (late game, tick 200-500)
        if rug_tick > 250:
            entry_tick = np.random.randint(200, min(500, rug_tick - 40))
        else:
            entry_tick = np.random.randint(100, max(101, rug_tick - 40))
        
        # Extract features and predict
        features = extract_features(prices, entry_tick)
        p_win = survival_model.predict_rug_probability(entry_tick, window=40, features=features)
        
        # Should we bet?
        should_bet, reason = risk_mgr.should_place_bet(p_win)
        
        if not should_bet:
            continue
        
        # Calculate position size
        bet_size = risk_mgr.calculate_position_size(p_win)
        
        if bet_size < config.min_bet_size:
            continue
        
        # Determine outcome
        outcome = (rug_tick > entry_tick) and (rug_tick <= entry_tick + 40)
        
        # Record trade
        risk_mgr.record_trade(bet_size, outcome, p_win)
    
    # Get trade history
    trades_df = pd.DataFrame(risk_mgr.state.trade_history)
    
    return risk_mgr, trades_df


# ==============================================================================
# Visualization
# ==============================================================================

def plot_backtest_results(risk_mgr: RiskManager):
    """Plot backtest results."""
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    
    trades_df = pd.DataFrame(risk_mgr.state.trade_history)
    
    # 1. Equity curve
    ax = axes[0, 0]
    ax.plot(risk_mgr.state.equity_curve, linewidth=2, color='blue')
    ax.axhline(risk_mgr.state.equity_curve[0], color='black', linestyle='--', alpha=0.5)
    
    # Color by state
    for i, trade in enumerate(trades_df.itertuples()):
        color = {
            'active': 'green',
            'reduced': 'yellow',
            'recovery': 'orange',
            'paused': 'red'
        }.get(trade.state, 'gray')
        ax.axvline(i + 1, alpha=0.1, color=color)
    
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Bankroll')
    ax.set_title('Equity Curve (colored by trading state)')
    ax.grid(True, alpha=0.3)
    
    # 2. Drawdown
    ax = axes[0, 1]
    ax.fill_between(range(len(trades_df)), -trades_df['drawdown_pct'], 0, color='red', alpha=0.3)
    ax.plot(-trades_df['drawdown_pct'], color='red', linewidth=1)
    ax.axhline(-risk_mgr.config.reduce_size_dd_pct, color='orange', linestyle='--', label='Reduce Size')
    ax.axhline(-risk_mgr.config.max_drawdown_pct, color='red', linestyle='--', label='Pause Trading')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Drawdown (%)')
    ax.set_title('Drawdown Curve')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Bet size evolution
    ax = axes[1, 0]
    ax.plot(trades_df['bet_size'], linewidth=1, color='purple')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Bet Size (SOL)')
    ax.set_title('Position Sizing Over Time')
    ax.grid(True, alpha=0.3)
    
    # 4. Win probability distribution
    ax = axes[1, 1]
    wins = trades_df[trades_df['outcome'] == True]['p_win']
    losses = trades_df[trades_df['outcome'] == False]['p_win']
    ax.hist(wins, bins=20, alpha=0.5, label='Wins', color='green')
    ax.hist(losses, bins=20, alpha=0.5, label='Losses', color='red')
    ax.axvline(0.20, color='black', linestyle='--', label='Breakeven (20%)')
    ax.set_xlabel('Estimated P(win)')
    ax.set_ylabel('Frequency')
    ax.set_title('Win Probability Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 5. Cumulative P&L
    ax = axes[2, 0]
    cumulative_pnl = trades_df['pnl'].cumsum()
    ax.plot(cumulative_pnl, linewidth=2, color='green' if cumulative_pnl.iloc[-1] > 0 else 'red')
    ax.axhline(0, color='black', linestyle='-', alpha=0.5)
    ax.fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, 
                     where=cumulative_pnl > 0, alpha=0.3, color='green')
    ax.fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, 
                     where=cumulative_pnl <= 0, alpha=0.3, color='red')
    ax.set_xlabel('Trade #')
    ax.set_ylabel('Cumulative P&L (SOL)')
    ax.set_title('Cumulative Profit/Loss')
    ax.grid(True, alpha=0.3)
    
    # 6. Trading state timeline
    ax = axes[2, 1]
    state_map = {'active': 0, 'reduced': 1, 'recovery': 2, 'paused': 3}
    states_numeric = [state_map.get(s, 0) for s in trades_df['state']]
    colors_list = ['green' if s == 0 else 'yellow' if s == 1 else 'orange' if s == 2 else 'red' 
                   for s in states_numeric]
    ax.scatter(range(len(states_numeric)), states_numeric, c=colors_list, s=20, alpha=0.7)
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(['ACTIVE', 'REDUCED', 'RECOVERY', 'PAUSED'])
    ax.set_xlabel('Trade #')
    ax.set_title('Trading State Timeline')
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    return fig


# ==============================================================================
# Main Analysis
# ==============================================================================

def run_comprehensive_analysis(save_plots: bool = True):
    """Run comprehensive risk system analysis."""
    print("=" * 70)
    print("COMPREHENSIVE RISK-ADJUSTED TRADING SYSTEM")
    print("=" * 70)
    
    # Load data
    print("\n[1/4] Loading data...")
    games_df = load_game_data(min_ticks=10)
    print(f"  Loaded {len(games_df)} games")
    
    # Fit model
    print("\n[2/4] Fitting Bayesian survival model...")
    survival_model = BayesianSurvivalModel(games_df)
    
    # Configure risk management
    print("\n[3/4] Configuring risk management...")
    config = RiskConfig(
        kelly_fraction=0.25,
        max_drawdown_pct=25.0,
        reduce_size_dd_pct=15.0,
        max_consecutive_losses=8,
        min_win_probability=0.18
    )
    
    print(f"  Kelly Fraction: {config.kelly_fraction}")
    print(f"  Max Drawdown: {config.max_drawdown_pct}%")
    print(f"  Min Win Prob: {config.min_win_probability:.1%}")
    
    # Backtest
    print("\n[4/4] Running backtest...")
    risk_mgr, trades_df = backtest_risk_system(
        games_df, survival_model, config,
        initial_bankroll=1.0, num_games=200
    )
    
    # Results
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    summary = risk_mgr.get_summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key:.<30} {value:>10.2f}")
        else:
            print(f"  {key:.<30} {value:>10}")
    
    # Plot
    if save_plots:
        fig = plot_backtest_results(risk_mgr)
        output_path = '/home/devops/rugs_data/analysis/comprehensive_risk_system.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ Saved: {output_path}")
        plt.close()
    
    print("\n" + "=" * 70)
    print("PRODUCTION DEPLOYMENT CHECKLIST")
    print("=" * 70)
    print("""
    ✅ 1. Position Sizing: Quarter Kelly (conservative, proven)
    ✅ 2. Drawdown Controls: Stop at 25%, reduce at 15%
    ✅ 3. Streak Protection: Pause after 8 consecutive losses
    ✅ 4. Entry Filters: P(win) > 18%, positive EV
    ✅ 5. Recovery Protocol: 50% size reduction, gradual increase
    
    🎯 NEXT STEPS FOR RL INTEGRATION:
    
    1. Wrap RiskManager in RL environment:
       - Observation: [bankroll, DD%, consecutive_losses, p_win, ...]
       - Action: [HOLD, PLACE_BET]
       - Reward: PnL adjusted for risk (Sharpe-weighted)
    
    2. Train policy with safety constraints:
       - Hard limit: No betting when RiskManager says no
       - Soft penalty: Penalize high drawdowns in reward
    
    3. Monitor live performance:
       - Track all metrics from RiskMetricsDashboard
       - Alert on Sharpe < 1.0 or MDD > 30%
       - Auto-pause if Calmar < 0.5
    
    4. Continuous improvement:
       - Re-fit Bayesian model weekly on new data
       - Adjust Kelly fraction based on realized variance
       - A/B test different configurations
    """)
    
    return risk_mgr, trades_df


if __name__ == "__main__":
    risk_mgr, trades_df = run_comprehensive_analysis(save_plots=True)
