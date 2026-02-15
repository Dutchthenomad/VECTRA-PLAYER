# 08 - Strategy Analysis (Explorer Tab)

## Purpose

The Explorer tab provides visual analysis of sidebet strategies:
1. Win rate by cumulative bet position
2. Duration/peak histograms
3. Price curve overlays
4. Bet window visualization

## Dependencies

```python
# Internal services
from recording_ui.services.explorer_data import (
    load_games_df,
    calculate_strategy_stats,
    get_explorer_data,
)

# Data processing
import pandas as pd
import numpy as np
```

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          Explorer Tab                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────┐     ┌────────────────────────────────────────────┐│
│  │  Strategy Controls │     │              Visualizations                 ││
│  │                    │     │                                            ││
│  │  Entry Tick: [200] │     │  ┌────────────────┐  ┌────────────────┐   ││
│  │  Num Bets:  [4]    │     │  │ Bet Windows    │  │ Duration       │   ││
│  │                    │     │  │ (Price Curves) │  │ Histogram      │   ││
│  │  [Run Analysis]    │     │  └────────────────┘  └────────────────┘   ││
│  └────────────────────┘     │                                            ││
│                             │  ┌────────────────┐  ┌────────────────┐   ││
│                             │  │ Win Rate by    │  │ Peak           │   ││
│                             │  │ Cumulative Bet │  │ Histogram      │   ││
│                             │  └────────────────┘  └────────────────┘   ││
│                             └────────────────────────────────────────────┘│
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                       Statistics Summary                                ││
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  ││
│  │  │ Games        │ │ Win Rate     │ │ Expected Val │ │ Kelly %      │  ││
│  │  │ 2,835        │ │ 18.5%        │ │ -7.5%        │ │ -7.5%        │  ││
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  ││
│  └────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────┘
```

## Key Patterns

### 1. Strategy Stats Calculation

```python
# src/recording_ui/services/explorer_data.py

def calculate_strategy_stats(games_df: pd.DataFrame, entry_tick: int,
                              num_bets: int) -> dict:
    """
    Calculate win/loss statistics for a sidebet strategy.

    Strategy: Place num_bets consecutive bets starting at entry_tick.
    Each bet window is 40 ticks.
    Win if game rugs during ANY bet window.

    Args:
        games_df: DataFrame with game data
        entry_tick: Tick to place first bet
        num_bets: Number of consecutive bets (1-4)

    Returns:
        Dict with statistics and per-bet breakdown
    """
    # Filter games that reached entry tick
    playable = games_df[games_df["duration_ticks"] >= entry_tick].copy()

    if len(playable) == 0:
        return {"error": "No games reached entry tick"}

    stats = {
        "total_games": len(games_df),
        "playable_games": len(playable),
        "entry_tick": entry_tick,
        "num_bets": num_bets,
        "bet_windows": [],
        "cumulative": [],
    }

    # Calculate per-bet statistics
    cumulative_wins = 0
    for bet_num in range(1, num_bets + 1):
        bet_start = entry_tick + (bet_num - 1) * 45  # 40 tick window + 5 tick cooldown
        bet_end = bet_start + 40

        # Win if game duration < bet_end (rugged during window)
        wins = playable[
            (playable["duration_ticks"] >= bet_start) &
            (playable["duration_ticks"] < bet_end)
        ]

        win_count = len(wins)
        cumulative_wins += win_count

        # Games that could have had this bet
        eligible = playable[playable["duration_ticks"] >= bet_start]
        eligible_count = len(eligible)

        bet_stats = {
            "bet_number": bet_num,
            "start_tick": bet_start,
            "end_tick": bet_end,
            "wins": win_count,
            "eligible": eligible_count,
            "win_rate": win_count / eligible_count if eligible_count > 0 else 0,
        }
        stats["bet_windows"].append(bet_stats)

        # Cumulative statistics
        cumulative_eligible = len(playable[playable["duration_ticks"] >= entry_tick])
        cumulative_rate = cumulative_wins / cumulative_eligible if cumulative_eligible > 0 else 0

        stats["cumulative"].append({
            "after_bet": bet_num,
            "total_wins": cumulative_wins,
            "win_rate": cumulative_rate,
            "expected_value": calculate_ev(cumulative_rate, bet_num),
        })

    # Overall statistics
    final_win_rate = stats["cumulative"][-1]["win_rate"]
    stats["overall"] = {
        "win_rate": final_win_rate,
        "expected_value": calculate_ev(final_win_rate, num_bets),
        "kelly_fraction": kelly_criterion(final_win_rate),
        "breakeven_rate": 1/6,  # 16.67% for 5:1 payout
        "edge": final_win_rate - 1/6,
    }

    return stats

def calculate_ev(win_rate: float, num_bets: int) -> float:
    """
    Calculate expected value per bet sequence.

    EV = P(win) * 4 - P(loss) * num_bets
    (5:1 payout = +4 profit on win, -1 per losing bet)
    """
    return win_rate * 4 - (1 - win_rate) * num_bets

def kelly_criterion(win_rate: float, payout: float = 5.0) -> float:
    """
    Calculate Kelly fraction.

    f* = (p * b - q) / b
    where p = win rate, q = 1-p, b = payout odds
    """
    q = 1 - win_rate
    b = payout - 1  # Net odds
    return (win_rate * b - q) / b
```

### 2. Bet Window Visualization Data

```python
def get_bet_window_games(games_df: pd.DataFrame, entry_tick: int,
                          num_bets: int, limit: int = 50) -> list[dict]:
    """
    Get games with bet window annotations for visualization.

    Returns:
        List of games with prices and outcome markers
    """
    # Filter games that reached entry tick
    playable = games_df[games_df["duration_ticks"] >= entry_tick]

    # Sample for visualization
    sampled = playable.sample(min(limit, len(playable)))

    games = []
    for _, row in sampled.iterrows():
        prices = row["prices"]
        duration = row["duration_ticks"]

        # Determine outcome for each bet window
        bet_outcomes = []
        for bet_num in range(1, num_bets + 1):
            bet_start = entry_tick + (bet_num - 1) * 45
            bet_end = bet_start + 40

            if duration >= bet_start and duration < bet_end:
                outcome = "win"
            elif duration < bet_start:
                outcome = "never_placed"
            else:
                outcome = "loss"

            bet_outcomes.append({
                "bet_number": bet_num,
                "start_tick": bet_start,
                "end_tick": bet_end,
                "outcome": outcome,
            })

        games.append({
            "game_id": row["game_id"],
            "prices": prices[:duration + 10],  # Include some after-rug
            "duration": duration,
            "peak": row["peak_multiplier"],
            "bet_windows": bet_outcomes,
            "overall_outcome": "win" if any(b["outcome"] == "win" for b in bet_outcomes) else "loss",
        })

    return games
```

### 3. Duration Histogram Data

```python
def get_duration_histogram(games_df: pd.DataFrame, bins: int = 50) -> dict:
    """
    Get histogram data for game duration distribution.

    Returns:
        Dict with bins and counts
    """
    durations = games_df["duration_ticks"]

    counts, bin_edges = np.histogram(durations, bins=bins)

    return {
        "bins": [
            {"start": int(bin_edges[i]), "end": int(bin_edges[i+1]),
             "count": int(counts[i])}
            for i in range(len(counts))
        ],
        "stats": {
            "mean": float(durations.mean()),
            "median": float(durations.median()),
            "std": float(durations.std()),
            "min": int(durations.min()),
            "max": int(durations.max()),
        }
    }
```

### 4. API Endpoints

```python
# src/recording_ui/app.py

@app.route("/api/explorer/data")
def api_explorer_data():
    """Get complete data for Explorer visualization."""
    entry_tick = request.args.get("entry_tick", 200, type=int)
    num_bets = request.args.get("num_bets", 4, type=int)
    limit = request.args.get("limit", 50, type=int)

    # Clamp values
    entry_tick = max(0, min(entry_tick, 1000))
    num_bets = max(1, min(num_bets, 4))
    limit = max(10, min(limit, 200))

    data = explorer_data.get_explorer_data(entry_tick, num_bets, limit)
    return jsonify(data)

@app.route("/api/explorer/strategy")
def api_explorer_strategy():
    """Get strategy stats only (lightweight)."""
    entry_tick = request.args.get("entry_tick", 200, type=int)
    num_bets = request.args.get("num_bets", 4, type=int)

    games_df = explorer_data.load_games_df()
    stats = explorer_data.calculate_strategy_stats(games_df, entry_tick, num_bets)
    return jsonify(stats)
```

## Data Schema

### Games DataFrame

```python
# Required columns
games_df = pd.DataFrame({
    "game_id": str,           # Unique identifier
    "duration_ticks": int,    # Ticks until rug
    "peak_multiplier": float, # Maximum price reached
    "peak_tick": int,         # Tick when peak occurred
    "prices": list[float],    # Tick-by-tick prices
})
```

### Strategy Stats Response

```json
{
  "total_games": 2835,
  "playable_games": 1856,
  "entry_tick": 200,
  "num_bets": 4,
  "bet_windows": [
    {"bet_number": 1, "start_tick": 200, "end_tick": 240, "wins": 89, "eligible": 1856, "win_rate": 0.048},
    {"bet_number": 2, "start_tick": 245, "end_tick": 285, "wins": 102, "eligible": 1767, "win_rate": 0.058},
    {"bet_number": 3, "start_tick": 290, "end_tick": 330, "wins": 95, "eligible": 1665, "win_rate": 0.057},
    {"bet_number": 4, "start_tick": 335, "end_tick": 375, "wins": 81, "eligible": 1570, "win_rate": 0.052}
  ],
  "cumulative": [
    {"after_bet": 1, "total_wins": 89, "win_rate": 0.048, "expected_value": -0.76},
    {"after_bet": 2, "total_wins": 191, "win_rate": 0.103, "expected_value": -1.39},
    {"after_bet": 3, "total_wins": 286, "win_rate": 0.154, "expected_value": -1.92},
    {"after_bet": 4, "total_wins": 367, "win_rate": 0.198, "expected_value": -2.01}
  ],
  "overall": {
    "win_rate": 0.198,
    "expected_value": -2.01,
    "kelly_fraction": -0.10,
    "breakeven_rate": 0.167,
    "edge": 0.031
  }
}
```

## Frontend Visualization

### Chart.js Configuration

```javascript
// static/js/explorer.js

// Win Rate by Cumulative Bet Chart
const winRateChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['After Bet 1', 'After Bet 2', 'After Bet 3', 'After Bet 4'],
        datasets: [{
            label: 'Cumulative Win Rate',
            data: cumulativeWinRates,
            backgroundColor: 'rgba(75, 192, 192, 0.5)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
        }, {
            label: 'Breakeven (16.67%)',
            data: [16.67, 16.67, 16.67, 16.67],
            type: 'line',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderDash: [5, 5],
            fill: false
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true,
                max: 30,
                title: { display: true, text: 'Win Rate (%)' }
            }
        }
    }
});

// Price Curve with Bet Windows
const priceChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: tickLabels,
        datasets: gamePriceDatasets.concat(betWindowAnnotations)
    },
    options: {
        plugins: {
            annotation: {
                annotations: {
                    bet1: {
                        type: 'box',
                        xMin: 200, xMax: 240,
                        backgroundColor: 'rgba(0, 255, 0, 0.1)',
                        borderColor: 'green',
                        label: { content: 'Bet 1' }
                    },
                    // ... more bet windows
                }
            }
        }
    }
});
```

## Integration Points

### With Dashboard

```python
# Explorer is a Flask route
@app.route("/explorer")
def explorer():
    return render_template("explorer.html")
```

### With Simulation

```python
# Explorer can trigger bankroll simulation
@app.route("/api/explorer/simulate", methods=["POST"])
def api_explorer_simulate():
    # Use position_sizing service
    result = position_sizing.run_simulation(games_df, config)
    return jsonify(result)
```

## Gotchas

1. **Bet Window Overlap**: 40-tick window + 5-tick cooldown = 45 ticks between bet starts.

2. **Eligibility**: A game is only eligible for a bet if it survives to that bet's start tick.

3. **Early Rug**: If game rugs before entry_tick, it's excluded from playable games.

4. **Cumulative vs Per-Bet**: Cumulative win rate includes all prior bets, not just the current one.

5. **Kelly Negative**: Negative Kelly means negative edge - don't bet.

6. **Price Array Length**: Price array may be shorter than duration if rug happens mid-tick.

7. **Sample Size**: Limit games shown in price chart to prevent browser slowdown.
