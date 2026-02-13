# 09 - Bankroll Simulation (Explorer Tab)

## Purpose

Simulate trading strategies over historical games:
1. Equity curve generation
2. Drawdown tracking
3. Risk controls (halt, take profit)
4. Multiple position sizing modes

## Dependencies

```python
# Internal modules
from recording_ui.services.position_sizing import (
    WalletConfig,
    SimulationResult,
    run_simulation,
    kelly_criterion,
    fractional_kelly,
)
from recording_ui.services.explorer_data import load_games_df
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       Bankroll Simulation Engine                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │  WalletConfig    │                                                        │
│  │  - initial_bal   │                                                        │
│  │  - bet_sizes     │                                                        │
│  │  - entry_tick    │                                                        │
│  │  - max_drawdown  │                                                        │
│  │  - kelly_frac    │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                   │
│           ▼                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        Simulation Loop                                  │ │
│  │  for game in games_df:                                                 │ │
│  │      if game.duration < entry_tick: skip                               │ │
│  │      for bet_num in 1..num_bets:                                       │ │
│  │          if halted: break                                               │ │
│  │          bet_size = calculate_bet_size(config, state)                  │ │
│  │          outcome = simulate_bet(game, bet_num)                         │ │
│  │          update_wallet(outcome, bet_size)                              │ │
│  │          check_risk_controls()                                          │ │
│  │          record_equity_point()                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│           │                                                                   │
│           ▼                                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                       SimulationResult                                │   │
│  │  - equity_curve: [(game_idx, balance), ...]                          │   │
│  │  - trades: [TradeRecord, ...]                                         │   │
│  │  - risk_metrics: {sharpe, sortino, max_dd, ...}                      │   │
│  │  - final_balance                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Wallet Configuration

```python
# src/recording_ui/services/position_sizing.py

from dataclasses import dataclass, field

@dataclass
class WalletConfig:
    """Configuration for bankroll simulation"""

    # Core settings
    initial_balance: float = 0.1  # SOL
    bet_sizes: list[float] = field(default_factory=lambda: [0.001, 0.001, 0.001, 0.001])
    entry_tick: int = 200
    num_bets: int = 4

    # Risk controls
    max_drawdown_pct: float = 0.50  # Halt at 50% drawdown
    take_profit_target: float | None = None  # e.g., 1.5 = stop at +50%

    # Dynamic sizing
    use_dynamic_sizing: bool = False
    high_confidence_threshold: float = 0.60
    high_confidence_multiplier: float = 2.0
    reduce_on_drawdown: bool = False

    # Kelly sizing
    use_kelly_sizing: bool = False
    kelly_fraction: float = 0.25  # Fractional Kelly (safer)
```

### 2. Simulation Engine

```python
@dataclass
class SimulationResult:
    """Results from bankroll simulation"""
    equity_curve: list[tuple[int, float]]  # (game_idx, balance)
    trades: list[dict]
    final_balance: float
    peak_balance: float
    max_drawdown: float
    max_drawdown_pct: float
    total_bets: int
    wins: int
    losses: int
    halted_at: int | None  # Game index where halted
    halt_reason: str | None
    risk_metrics: dict

def run_simulation(games_df: pd.DataFrame, config: WalletConfig) -> SimulationResult:
    """
    Run bankroll simulation over historical games.

    Args:
        games_df: DataFrame with game data (must have duration_ticks, peak_multiplier)
        config: Wallet configuration

    Returns:
        SimulationResult with equity curve and statistics
    """
    balance = config.initial_balance
    peak_balance = balance
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    equity_curve = [(0, balance)]
    trades = []
    wins = 0
    losses = 0
    total_bets = 0
    halted = False
    halt_reason = None
    halted_at = None

    # Filter playable games
    playable = games_df[games_df["duration_ticks"] >= config.entry_tick]

    for game_idx, (_, game) in enumerate(playable.iterrows()):
        if halted:
            break

        duration = game["duration_ticks"]

        # Place bets for this game
        for bet_num in range(1, config.num_bets + 1):
            if halted:
                break

            bet_start = config.entry_tick + (bet_num - 1) * 45
            bet_end = bet_start + 40

            # Skip if game already rugged before this bet
            if duration < bet_start:
                break

            # Calculate bet size
            bet_size = calculate_bet_size(config, balance, bet_num, game_idx)
            bet_size = min(bet_size, balance)  # Can't bet more than have

            if bet_size <= 0:
                continue

            total_bets += 1

            # Determine outcome
            won = bet_start <= duration < bet_end

            if won:
                payout = bet_size * 5  # 5:1 payout
                balance += payout - bet_size  # Net profit
                wins += 1
            else:
                balance -= bet_size
                losses += 1

            # Record trade
            trades.append({
                "game_idx": game_idx,
                "game_id": game.get("game_id", ""),
                "bet_num": bet_num,
                "bet_size": bet_size,
                "won": won,
                "balance_after": balance,
            })

            # Update peak and drawdown
            if balance > peak_balance:
                peak_balance = balance

            current_dd = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
            if current_dd > max_drawdown_pct:
                max_drawdown_pct = current_dd
                max_drawdown = peak_balance - balance

            # Check risk controls
            if current_dd >= config.max_drawdown_pct:
                halted = True
                halt_reason = f"Drawdown halt ({current_dd:.1%})"
                halted_at = game_idx
                break

            if config.take_profit_target and balance >= config.initial_balance * config.take_profit_target:
                halted = True
                halt_reason = f"Take profit ({balance/config.initial_balance:.1%})"
                halted_at = game_idx
                break

        # Record equity after each game
        equity_curve.append((game_idx + 1, balance))

    # Calculate risk metrics
    risk_metrics = calculate_risk_metrics(equity_curve, trades, config.initial_balance)

    return SimulationResult(
        equity_curve=equity_curve,
        trades=trades,
        final_balance=balance,
        peak_balance=peak_balance,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
        total_bets=total_bets,
        wins=wins,
        losses=losses,
        halted_at=halted_at,
        halt_reason=halt_reason,
        risk_metrics=risk_metrics,
    )
```

### 3. Dynamic Bet Sizing

```python
def calculate_bet_size(config: WalletConfig, balance: float,
                       bet_num: int, game_idx: int) -> float:
    """
    Calculate bet size based on configuration.

    Supports:
    - Fixed sizing (default)
    - Kelly criterion
    - Dynamic sizing with confidence
    """
    # Base bet size from config
    base_size = config.bet_sizes[bet_num - 1] if bet_num <= len(config.bet_sizes) else config.bet_sizes[-1]

    if config.use_kelly_sizing:
        # Kelly-based sizing
        # Assume historical win rate (could be parameterized)
        win_rate = 0.185  # ~18.5% empirical
        kelly = fractional_kelly(win_rate, fraction=config.kelly_fraction)

        if kelly > 0:
            base_size = balance * kelly
        else:
            base_size = 0  # No edge

    if config.use_dynamic_sizing:
        # Confidence-based sizing
        # Later bets in sequence have higher confidence
        confidence = 0.50 + (bet_num - 1) * 0.10  # 50%, 60%, 70%, 80%

        if confidence >= config.high_confidence_threshold:
            base_size *= config.high_confidence_multiplier

    if config.reduce_on_drawdown:
        # Reduce bets when in drawdown
        drawdown_pct = (config.initial_balance - balance) / config.initial_balance
        if drawdown_pct > 0.10:  # 10% drawdown
            reduction = 1 - (drawdown_pct - 0.10) * 2  # Linear reduction
            base_size *= max(0.25, reduction)  # Floor at 25%

    return max(0.0001, base_size)  # Minimum bet
```

### 4. Risk Metrics Calculation

```python
def calculate_risk_metrics(equity_curve: list, trades: list,
                           initial_balance: float) -> dict:
    """Calculate comprehensive risk metrics"""
    import numpy as np

    balances = [b for _, b in equity_curve]
    returns = []
    for i in range(1, len(balances)):
        if balances[i-1] > 0:
            returns.append((balances[i] - balances[i-1]) / balances[i-1])

    if not returns:
        return {}

    returns = np.array(returns)

    # Basic metrics
    total_return = (balances[-1] - initial_balance) / initial_balance
    win_rate = sum(1 for t in trades if t["won"]) / len(trades) if trades else 0

    # Sharpe ratio (assuming risk-free rate = 0)
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(len(returns)) if np.std(returns) > 0 else 0

    # Sortino ratio (downside deviation)
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 0.0001
    sortino = np.mean(returns) / downside_std * np.sqrt(len(returns)) if downside_std > 0 else 0

    # Maximum drawdown (already calculated)
    max_dd = calculate_max_drawdown(balances)

    # Calmar ratio
    calmar = total_return / max_dd if max_dd > 0 else 0

    # VaR (Value at Risk) 95%
    var_95 = np.percentile(returns, 5) if len(returns) > 20 else 0

    # CVaR / Expected Shortfall
    cvar_95 = np.mean(returns[returns <= var_95]) if len(returns[returns <= var_95]) > 0 else var_95

    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "max_drawdown_pct": max_dd,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "num_trades": len(trades),
    }
```

### 5. API Endpoint

```python
# src/recording_ui/app.py

@app.route("/api/explorer/simulate", methods=["POST"])
def api_explorer_simulate():
    """Run bankroll simulation with position sizing."""
    data = request.get_json() or {}

    # Parse configuration
    config = WalletConfig(
        initial_balance=float(data.get("initial_balance", 0.1)),
        entry_tick=int(data.get("entry_tick", 200)),
        bet_sizes=data.get("bet_sizes", [0.001, 0.001, 0.001, 0.001]),
        max_drawdown_pct=float(data.get("max_drawdown_pct", 0.50)),
        use_dynamic_sizing=bool(data.get("use_dynamic_sizing", False)),
        high_confidence_threshold=float(data.get("high_confidence_threshold", 60)) / 100,
        high_confidence_multiplier=float(data.get("high_confidence_multiplier", 2.0)),
        reduce_on_drawdown=bool(data.get("reduce_on_drawdown", False)),
        take_profit_target=data.get("take_profit_target"),
        use_kelly_sizing=bool(data.get("use_kelly_sizing", False)),
        kelly_fraction=float(data.get("kelly_fraction", 0.25)),
    )

    # Load games and run simulation
    games_df = explorer_data.load_games_df()
    result = run_simulation(games_df, config)

    return jsonify(simulation_to_dict(result))

def simulation_to_dict(result: SimulationResult) -> dict:
    """Convert SimulationResult to JSON-serializable dict"""
    return {
        "equity_curve": result.equity_curve,
        "final_balance": result.final_balance,
        "peak_balance": result.peak_balance,
        "max_drawdown": result.max_drawdown,
        "max_drawdown_pct": result.max_drawdown_pct,
        "total_bets": result.total_bets,
        "wins": result.wins,
        "losses": result.losses,
        "win_rate": result.wins / result.total_bets if result.total_bets > 0 else 0,
        "halted_at": result.halted_at,
        "halt_reason": result.halt_reason,
        "risk_metrics": result.risk_metrics,
        "trades": result.trades[-50:],  # Last 50 trades for review
    }
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `initial_balance` | float | 0.1 | Starting SOL |
| `bet_sizes` | list[float] | [0.001]*4 | Per-bet sizes |
| `entry_tick` | int | 200 | First bet tick |
| `num_bets` | int | 4 | Bets per game |
| `max_drawdown_pct` | float | 0.50 | Halt threshold |
| `take_profit_target` | float | None | Exit multiplier |
| `use_kelly_sizing` | bool | False | Kelly-based sizing |
| `kelly_fraction` | float | 0.25 | Kelly multiplier |
| `use_dynamic_sizing` | bool | False | Confidence-based |
| `high_confidence_threshold` | float | 0.60 | Multiplier trigger |
| `high_confidence_multiplier` | float | 2.0 | Bet multiplier |
| `reduce_on_drawdown` | bool | False | Reduce in drawdown |

## Frontend Integration

```javascript
// static/js/explorer.js

async function runSimulation() {
    const config = {
        initial_balance: parseFloat(document.getElementById('initial-balance').value),
        entry_tick: parseInt(document.getElementById('entry-tick').value),
        bet_sizes: [
            parseFloat(document.getElementById('bet1-size').value),
            parseFloat(document.getElementById('bet2-size').value),
            parseFloat(document.getElementById('bet3-size').value),
            parseFloat(document.getElementById('bet4-size').value),
        ],
        max_drawdown_pct: parseFloat(document.getElementById('max-drawdown').value) / 100,
        use_kelly_sizing: document.getElementById('use-kelly').checked,
        kelly_fraction: parseFloat(document.getElementById('kelly-fraction').value),
    };

    const response = await fetch('/api/explorer/simulate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(config)
    });

    const result = await response.json();
    updateEquityChart(result.equity_curve);
    updateMetricsDisplay(result.risk_metrics);
}

function updateEquityChart(equityCurve) {
    equityChart.data.labels = equityCurve.map(([idx, _]) => idx);
    equityChart.data.datasets[0].data = equityCurve.map(([_, bal]) => bal);
    equityChart.update();
}
```

## Gotchas

1. **Bet Sequence**: Each game has up to 4 bets. Break loop if game rugs before bet start.

2. **Cooldown**: 5-tick cooldown between bets (45 total between bet starts).

3. **Kelly Negative**: If Kelly fraction is negative, there's no edge. Don't bet.

4. **Drawdown Halt**: Halt is permanent for simulation. Real trading may resume.

5. **Balance Floor**: Can't bet more than current balance.

6. **Returns Calculation**: Per-game returns, not per-trade, for portfolio metrics.

7. **Sample Size**: Need sufficient games for meaningful risk metrics.
